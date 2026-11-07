"""STU-02-published-sets: practice on teacher-published sets, real DbSetProvider through the HTTP API.

Contract: workflow/specs/STU-02-published-sets/plan.md. Sets are inserted with SQL (published_sets.py);
no fake provider is installed. Covers AC1 to AC7, AC9 to AC14, AC17 to AC21, AC24.
"""
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from auth_helpers import call, code_of, new_student, seeded
from published_sets import QUESTIONS, delete_published_set, insert_published_set, question_rows, question_set, world
from stu01_helpers import enroll, enrolled_student, make_course, make_topic, sql, unenroll
from stu04_helpers import insert_attempt

NOT_FOUND = {"detail": {"code": "set_not_found", "message": "Practice set not found."}}
BAD_UUID = {"detail": {"code": "validation_error", "message": "A valid UUID is required."}}
LETTERS = "abcd"


def read(s, sid):
    return call("GET", f"/api/practice-sets/{sid}", s)


def start(s, sid):
    r = call("POST", f"/api/practice-sets/{sid}/attempts", s)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


def save(aid, s, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": answers})


def submit(aid, s):
    return call("POST", f"/api/attempts/{aid}/submit", s)


def results(aid, s):
    return call("GET", f"/api/attempts/{aid}/results", s)


def qids(sid):
    return [r[0] for r in question_rows(sid)]


def full_answers(sid, letters):
    return dict(zip(qids(sid), letters))


def member_world(**kw):
    cid, tid, sid = world(**kw)
    return cid, tid, sid, enrolled_student(cid)


# ---------------------------------------------------------------- AC1 to AC6 on a published set
def test_stu02ps_db_full_flow_on_a_real_published_set_with_four_choices():
    cid, tid, sid, s = member_world()
    body = read(s, sid).json()
    assert body["id"] == sid and body["title"] == "Testing basics"
    assert len(body["questions"]) == 3
    aid = start(s, sid)
    a = qids(sid)
    # AC1: an incomplete submit is rejected with the missing questions identified
    assert save(aid, s, {a[0]: "a"}).status_code == 200
    r = submit(aid, s)
    assert r.status_code == 422 and code_of(r) == "incomplete"
    assert r.json()["detail"]["missing"] == [a[1], a[2]]
    # AC3: revise freely, no feedback on save
    assert save(aid, s, {a[0]: "b"}).status_code == 200
    assert save(aid, s, {a[0]: "a", a[1]: "b", a[2]: "d"}).status_code == 200
    # AC6/AC7: no results before submit
    r = results(aid, s)
    assert r.status_code == 403 and code_of(r) == "not_submitted"
    # AC4: submit saves the whole attempt, score and key version
    r = submit(aid, s)
    assert r.status_code == 200, r.text
    assert r.json()["score"] == {"correct": 2, "total": 3}
    res = results(aid, s).json()
    assert res["key_version"] == "v1" and res["score"] == {"correct": 2, "total": 3}
    row = sql("SELECT status, score_correct, score_total, key_version, set_id FROM practice_attempt WHERE id = %s", (aid,))[0]
    assert row == ("submitted", 2, 3, "v1", sid)
    assert submit(aid, s).status_code == 409


def test_stu02ps_db_failed_submit_keeps_answers_and_unlocks_nothing():
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    a = qids(sid)
    save(aid, s, {a[0]: "a"})
    assert submit(aid, s).status_code == 422
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {a[0]: "a"}
    assert results(aid, s).status_code == 403


def test_stu02ps_db_ac2_one_choice_per_question_and_no_free_text():
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    q = qids(sid)[0]
    for bad in ("e", "A", "", "free text answer"):
        r = save(aid, s, {q: bad})
        assert r.status_code == 422 and code_of(r) == "invalid_choice", (bad, r.text)
    for bad in (None, 3):  # not a string: rejected (the spec names no code)
        assert save(aid, s, {q: bad}).status_code == 422
    r = save(aid, s, {str(uuid.uuid4()): "a"})
    assert r.status_code == 422 and code_of(r) == "unknown_question"


# ---------------------------------------------------------------- AC7 answer release
def _walk(v):
    if isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from _walk(x)
    elif isinstance(v, list):
        for x in v:
            yield from _walk(x)
    else:
        yield v


def test_stu02ps_db_ac7_set_read_has_only_the_answer_free_keys_and_no_explanation():
    qs = question_set((0, 1, 2), tag="LEAKCHECK-")
    cid, tid, sid, s = member_world(questions=qs)
    r = read(s, sid)
    body = r.json()
    assert set(body) == {"id", "title", "questions"}
    for q in body["questions"]:
        assert set(q) == {"id", "text", "code", "choices"} and q["code"] is None
        for c in q["choices"]:
            assert set(c) == {"id", "text"}
    flat = [x for x in _walk(body) if isinstance(x, str)]
    assert not any("Explanation" in x for x in flat)
    for k in ("correct", "explanation", "correct_choice", "correct_choice_index", "key_version"):
        assert k not in r.text


def test_stu02ps_db_ac7_error_bodies_and_pre_submit_reads_hold_no_key_or_explanation():
    qs = question_set((3, 2, 1), tag="SECRET-")
    cid, tid, sid, s = member_world(questions=qs)
    aid = start(s, sid)
    save(aid, s, {qids(sid)[0]: "a"})
    other = new_student()
    texts = [
        results(aid, s).text,                       # 403 not_submitted
        submit(aid, s).text,                        # 422 incomplete
        save(aid, s, {"nope": "a"}).text,           # 422 unknown_question
        save(aid, s, {qids(sid)[0]: "z"}).text,     # 422 invalid_choice
        read(other, sid).text,                      # 404
        read(s, "intro-se-1").text,                 # 422
        call("GET", f"/api/attempts/{aid}", s).text,
        call("GET", f"/api/attempts/{aid}", other).text,
    ]
    for t in texts:
        assert "SECRET-Explanation" not in t and "correct_choice" not in t and "explanation" not in t
    assert save(aid, s, full_answers(sid, "dcb")).status_code == 200
    assert submit(aid, s).status_code == 200
    after = results(aid, s)
    assert after.status_code == 200 and "SECRET-Explanation 1" in after.text


# ---------------------------------------------------------------- AC8 other students' attempts
def test_stu02ps_db_ac8_another_students_attempt_is_attempt_not_found_on_every_attempt_endpoint():
    cid, tid, sid, owner = member_world()
    mate = enrolled_student(cid)
    aid = start(owner, sid)
    save(aid, owner, full_answers(sid, "abc"))
    submit(aid, owner)
    unknown = {"detail": {"code": "attempt_not_found", "message": "Attempt not found."}}
    for r in (call("GET", f"/api/attempts/{aid}", mate), save(aid, mate, {"x": "a"}), submit(aid, mate), results(aid, mate)):
        assert r.status_code == 404 and r.json() == unknown


# ---------------------------------------------------------------- AC9 provider access
def test_stu02ps_db_ac9_the_fixture_id_is_not_a_uuid_and_not_served():
    s = new_student()
    for r in (read(s, "intro-se-1"), call("POST", "/api/practice-sets/intro-se-1/attempts", s)):
        assert r.status_code == 422 and r.json() == BAD_UUID


def test_stu02ps_db_ac9_member_sees_set_non_member_and_unknown_get_the_same_404():
    cid, tid, sid, member = member_world()
    stranger = new_student()
    assert read(member, sid).status_code == 200
    unknown = read(stranger, str(uuid.uuid4()))
    assert unknown.status_code == 404 and unknown.json() == NOT_FOUND
    assert read(stranger, sid).json() == NOT_FOUND
    assert call("POST", f"/api/practice-sets/{sid}/attempts", stranger).json() == NOT_FOUND


# ---------------------------------------------------------------- AC10
def _scenario(kind):
    """Returns (student, set_id, attempt_id) for a set the student cannot resolve."""
    if kind == "unknown":
        s = new_student()
        sid = str(uuid.uuid4())
        return s, sid, insert_attempt(s, answers={}, correct_ids=[], status="in_progress", set_id=sid)
    if kind == "other_course":
        _, _, sid = world()
        s = new_student()
        return s, sid, insert_attempt(s, answers={}, correct_ids=[], status="in_progress", set_id=sid)
    cid, _, sid, s = member_world()
    aid = start(s, sid)
    unenroll(s, cid)
    return s, sid, aid


ENDPOINTS = {
    "read_set": lambda s, sid, aid: read(s, sid),
    "start": lambda s, sid, aid: call("POST", f"/api/practice-sets/{sid}/attempts", s),
    "read_attempt": lambda s, sid, aid: call("GET", f"/api/attempts/{aid}", s),
    "save": lambda s, sid, aid: save(aid, s, {"q": "a"}),
    "submit": lambda s, sid, aid: submit(aid, s),
    "results": lambda s, sid, aid: results(aid, s),
}


@pytest.mark.parametrize("endpoint", list(ENDPOINTS))
@pytest.mark.parametrize("kind", ["unknown", "other_course", "membership_deleted"])
def test_stu02ps_db_ac10_inaccessible_sets_give_one_identical_404_on_every_endpoint(kind, endpoint):
    s, sid, aid = _scenario(kind)
    r = ENDPOINTS[endpoint](s, sid, aid)
    assert r.status_code == 404
    assert r.json() == NOT_FOUND


def test_stu02ps_db_ac10_an_old_attempt_on_a_non_uuid_set_id_is_set_not_found():
    s = new_student()
    aid = insert_attempt(s, answers={}, correct_ids=[], status="in_progress", set_id="intro-se-1")
    for r in (call("GET", f"/api/attempts/{aid}", s), save(aid, s, {"q1": "a"}), submit(aid, s), results(aid, s)):
        assert r.status_code == 404 and r.json() == NOT_FOUND


# ---------------------------------------------------------------- AC11 hostile and alternative ids
HOSTILE = ["intro-se-1", "%20" + "a" * 8, "%20", "a" * 5000, "%00", "a%00b", "%0d%0a", "%27%20OR%201%3D1%3B--",
           "1%27%3B%20DROP%20TABLE%20x%3B--", "a0000000-0000-4000-8000-00000000000",  # 35 characters
           "a0000000-0000-4000-8000-0000000000012", "not%20a%20uuid", "%E2%80%AE", "0", "null"]


@pytest.fixture
def spy(monkeypatch):
    """Counts provider lookups; a 422 must come before any of them."""
    import set_provider

    calls = []
    for name in ("get_for_student", "get_many_for_student", "catalog_for_student", "accessible_sets"):
        real = getattr(set_provider.DbSetProvider, name)

        def wrapper(self, *a, __real=real, __name=name, **k):
            calls.append(__name)
            return __real(self, *a, **k)

        monkeypatch.setattr(set_provider.DbSetProvider, name, wrapper)
    return calls


@pytest.mark.parametrize("bad", HOSTILE)
def test_stu02ps_db_ac11_malformed_ids_give_422_never_500_and_no_lookup(bad, spy):
    s = new_student()
    r = call("GET", f"/api/practice-sets/{bad}", s)
    p = call("POST", f"/api/practice-sets/{bad}/attempts", s)
    for x in (r, p):
        assert x.status_code == 422, (bad, x.status_code, x.text[:200])
        assert x.json() == BAD_UUID
    assert spy == []


def test_stu02ps_db_ac11_the_422_body_equals_the_tea03_route_body_for_the_same_input():
    s = new_student()
    for bad in ("intro-se-1", "a%00b", "%20", "a" * 300):
        mine = call("GET", f"/api/practice-sets/{bad}", s)
        theirs = call("GET", f"/api/study/practice-sets/{bad}", s)
        assert mine.status_code == theirs.status_code == 422
        assert mine.json() == theirs.json()


@pytest.mark.parametrize("raw", ["..%2F", "a%2Fb", "%2F", "a%2Fb%2Fc"])
def test_stu02ps_db_ac11_encoded_slashes_are_not_routed(raw):
    s = new_student()
    r = call("GET", f"/api/practice-sets/{raw}", s)  # the framework may answer 404 or a 307 normalisation
    assert r.status_code in (307, 404)
    assert "set_not_found" not in r.text and "validation_error" not in r.text
    assert "questions" not in r.text and "explanation" not in r.text


def test_stu02ps_db_ac11_alternative_spellings_of_a_real_id_find_the_same_set():
    cid, tid, sid, s = member_world()
    canonical = read(s, sid).json()
    forms = [sid.upper(), "%7B" + sid + "%7D", "urn:uuid:" + sid, sid.replace("-", ""), sid.upper().replace("-", "")]
    for form in forms:
        r = read(s, form)
        assert r.status_code == 200, (form, r.text)
        assert r.json() == canonical
        a = call("POST", f"/api/practice-sets/{form}/attempts", s)
        assert a.status_code == 201 and a.json()["set_id"] == sid
    stranger = new_student()
    for form in forms:
        assert read(stranger, form).json() == NOT_FOUND


def test_stu02ps_db_ac11_401_and_403_come_before_422():
    assert call("GET", "/api/practice-sets/intro-se-1").status_code == 401
    assert call("POST", "/api/practice-sets/intro-se-1/attempts").status_code == 401
    t = seeded("teacher")
    for r in (call("GET", "/api/practice-sets/intro-se-1", t), call("POST", "/api/practice-sets/intro-se-1/attempts", t)):
        assert r.status_code == 403 and code_of(r) == "forbidden"


# ---------------------------------------------------------------- AC12 role gate
def _all_calls(sid, aid, who):
    return [
        call("GET", "/api/practice-sets", who),
        call("GET", f"/api/practice-sets/{sid}", who),
        call("POST", f"/api/practice-sets/{sid}/attempts", who),
        call("GET", f"/api/attempts/{aid}", who),
        call("PUT", f"/api/attempts/{aid}/answers", who, {"answers": {}}),
        call("POST", f"/api/attempts/{aid}/submit", who),
        call("GET", f"/api/attempts/{aid}/results", who),
    ]


def test_stu02ps_db_ac12_no_session_is_401_teacher_and_admin_are_403_on_every_endpoint():
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    for r in _all_calls(sid, aid, None):
        assert r.status_code == 401 and code_of(r) == "unauthenticated", r.text
    for role in ("teacher", "admin"):
        who = seeded(role)
        if role == "teacher":  # a teacher who is a member of the course is still not a student
            enroll(who, cid)
        try:
            for r in _all_calls(sid, aid, who):
                assert r.status_code == 403 and code_of(r) == "forbidden", (role, r.text)
        finally:
            if role == "teacher":  # older tests list the teacher's courses
                unenroll(who, cid)


def test_stu02ps_db_ac12_identity_headers_and_query_parameters_are_ignored():
    cid, tid, sid, member = member_world()
    stranger = new_student()
    hdrs = {"X-Student-Id": str(member), "X-Demo-User-Id": str(member)}
    r = call("GET", f"/api/practice-sets/{sid}?student_id={member}", stranger, headers=hdrs)
    assert r.status_code == 404
    assert call("GET", f"/api/practice-sets?student_id={member}", stranger, headers=hdrs).json() == {"courses": []}
    assert call("GET", f"/api/practice-sets/{sid}", None, headers=hdrs).status_code == 401


# ---------------------------------------------------------------- AC13 mapping
def test_stu02ps_db_ac13_read_lists_questions_by_position_with_snapshot_ids_and_a_to_d():
    cid, tid, sid, s = member_world(questions=QUESTIONS)
    body = read(s, sid).json()
    rows = question_rows(sid)
    assert [q["id"] for q in body["questions"]] == [r[0] for r in rows]
    for q, (text, choices, _, _) in zip(body["questions"], QUESTIONS):
        assert q["text"] == text and q["code"] is None
        assert [c["id"] for c in q["choices"]] == list("abcd")
        assert [c["text"] for c in q["choices"]] == choices


@pytest.mark.parametrize("index", [0, 1, 2, 3])
def test_stu02ps_db_ac13_correct_choice_index_maps_to_a_to_d(index):
    cid, tid, sid, s = member_world(questions=question_set((index, index, index)))
    aid = start(s, sid)
    save(aid, s, full_answers(sid, LETTERS[index] * 3))
    assert submit(aid, s).json()["score"] == {"correct": 3, "total": 3}
    res = results(aid, s).json()
    assert res["key_version"] == "v1"
    assert json.dumps(res).count(f'"correct_choice": "{LETTERS[index]}"') >= 3
    wrong = LETTERS[(index + 1) % 4]
    aid2 = start(s, sid)
    save(aid2, s, full_answers(sid, wrong * 3))
    assert submit(aid2, s).json()["score"] == {"correct": 0, "total": 3}


# ---------------------------------------------------------------- AC14 picker
def _picker(s):
    r = call("GET", "/api/practice-sets", s)
    assert r.status_code == 200, r.text
    return r.json()


def test_stu02ps_db_ac14_picker_orders_courses_and_sets_and_has_exact_keys():
    s = new_student()
    c2, c1, c3 = make_course("zz Course"), make_course("Aa course"), make_course("Empty course")
    for c in (c1, c2, c3):
        enroll(s, c)
    t1, t2 = make_topic(c1, "Topic one"), make_topic(c2, "Topic two")
    old = insert_published_set(c1, t1, "Old set", published_at="2026-01-01T00:00:00Z")
    new = insert_published_set(c1, t1, "New set", published_at="2026-03-01T00:00:00Z")
    other = insert_published_set(c2, t2, "Other course set")
    elsewhere = world()[2]
    body = _picker(s)
    assert list(body) == ["courses"]
    assert [c["title"] for c in body["courses"]] == ["Aa course", "Empty course", "zz Course"]
    first, empty, last = body["courses"]
    assert set(first) == {"id", "title", "sets"} and first["id"] == c1
    assert [x["id"] for x in first["sets"]] == [new, old]
    assert empty["sets"] == []
    assert [x["id"] for x in last["sets"]] == [other]
    one = first["sets"][0]
    assert set(one) == {"id", "title", "topic", "published_at", "question_count", "best"}
    assert one["topic"] == {"id": t1, "name": "Topic one"} and one["question_count"] == 3 and one["best"] is None
    assert one["published_at"].endswith("Z") and one["published_at"].startswith("2026-03-01")
    assert elsewhere not in json.dumps(body)


def test_stu02ps_db_ac14_a_student_without_membership_gets_an_empty_list():
    assert _picker(new_student()) == {"courses": []}


def test_stu02ps_db_ac14_best_is_the_highest_submitted_score_and_only_the_callers():
    cid, tid, sid, s = member_world()
    mate = enrolled_student(cid)
    a = qids(sid)
    for letters, expected in (("dad", 0), ("abd", 2), ("add", 1)):  # key is a, b, c
        aid = start(s, sid)
        save(aid, s, dict(zip(a, letters)))
        assert submit(aid, s).json()["score"]["correct"] == expected
    start(s, sid)  # in progress: never counts
    assert _picker(s)["courses"][0]["sets"][0]["best"] == {"correct": 2, "total": 3}
    assert _picker(mate)["courses"][0]["sets"][0]["best"] is None
    assert str(s) not in json.dumps(_picker(mate))


def test_stu02ps_db_ac14_picker_has_no_answer_data_and_no_foreign_course_set():
    qs = question_set((0, 1, 2), tag="PICKSECRET-")
    cid, tid, sid, s = member_world(questions=qs)
    foreign = world(questions=question_set((0, 0, 0), tag="FOREIGN-"))[2]
    text = json.dumps(_picker(s))
    for forbidden in ("PICKSECRET", "FOREIGN", foreign, "explanation", "correct", "choices", "attempt_id", "source_draft"):
        assert forbidden not in text


def test_stu02ps_db_ac14_at_most_100_sets_per_course_newest_first():
    cid = make_course("Big course")
    s = enrolled_student(cid)
    tid = make_topic(cid, "T")
    ids = [insert_published_set(cid, tid, f"S{i:03d}", published_at=f"2026-01-01T{i // 3600:02d}:{(i // 60) % 60:02d}:{i % 60:02d}Z")
           for i in range(103)]
    sets = _picker(s)["courses"][0]["sets"]
    assert len(sets) == 100
    assert [x["id"] for x in sets] == ids[::-1][:100]


# ---------------------------------------------------------------- AC17 membership removed mid-attempt
def test_stu02ps_db_ac17_membership_removed_blocks_every_attempt_endpoint_and_restoring_unblocks():
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    save(aid, s, full_answers(sid, "abc"))
    assert submit(aid, s).status_code == 200
    aid2 = start(s, sid)
    save(aid2, s, full_answers(sid, "ab"))
    before = sql("SELECT answers::text, status FROM practice_attempt WHERE id = %s", (aid2,))
    unenroll(s, cid)
    for r in (call("GET", f"/api/attempts/{aid2}", s), save(aid2, s, full_answers(sid, "abc")), submit(aid2, s),
              results(aid, s), call("GET", f"/api/attempts/{aid}", s)):
        assert r.status_code == 404 and r.json() == NOT_FOUND
    assert sql("SELECT answers::text, status FROM practice_attempt WHERE id = %s", (aid2,)) == before
    enroll(s, cid)
    assert results(aid, s).status_code == 200
    assert save(aid2, s, full_answers(sid, "abc")).status_code == 200
    assert submit(aid2, s).status_code == 200


# ---------------------------------------------------------------- AC18 set removed
def test_stu02ps_db_ac18_a_set_deleted_in_the_database_gives_404_keeps_the_attempt_and_progress_skips_it():
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    save(aid, s, full_answers(sid, "abc"))
    submit(aid, s)
    aid2 = start(s, sid)
    row = sql("SELECT answers::text, status, score_correct FROM practice_attempt WHERE id = %s", (aid2,))
    delete_published_set(sid)
    for r in (call("GET", f"/api/attempts/{aid2}", s), save(aid2, s, {"q": "a"}), submit(aid2, s), results(aid, s),
              read(s, sid)):
        assert r.status_code == 404 and r.json() == NOT_FOUND
    assert sql("SELECT answers::text, status, score_correct FROM practice_attempt WHERE id = %s", (aid2,)) == row
    p = call("GET", "/api/progress", s)
    assert p.status_code == 200 and p.json()["practice"]["sets"] == []


# ---------------------------------------------------------------- AC19 companion
def test_stu02ps_db_ac19_companion_hint_on_a_real_published_set_and_404_without_a_model_call(fake):
    qs = question_set((0, 1, 2), tag="COMP-")
    cid, tid, sid, s = member_world(questions=qs)
    stranger = new_student()
    body = {"message": "I need a hint", "history": [],
            "context": {"page": "practice", "set_id": sid, "attempt_id": None, "label": None}}
    r = call("POST", "/api/companion/messages", s, body)
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "hint"
    assert len(fake.calls) == 1
    assert "COMP-Explanation" not in fake.last.all_text
    n = len(fake.calls)
    r = call("POST", "/api/companion/messages", stranger, body)
    assert r.status_code == 404 and code_of(r) == "set_not_found"
    bad = dict(body, context=dict(body["context"], set_id="intro-se-1"))
    r = call("POST", "/api/companion/messages", s, bad)
    assert r.status_code == 422 and r.json() == BAD_UUID
    assert len(fake.calls) == n


def test_stu02ps_db_ac19_a_pasted_question_of_an_inaccessible_set_is_not_matched(fake):
    world(questions=question_set((0, 1, 2), tag="FOREIGNQ-"))
    s = new_student()
    body = {"message": "FOREIGNQ-Question number 1?", "history": [],
            "context": {"page": "other", "set_id": None, "attempt_id": None, "label": None}}
    r = call("POST", "/api/companion/messages", s, body)
    assert r.status_code == 200
    assert "FOREIGNQ-Explanation" not in fake.last.all_text and "FOREIGNQ-Q1 choice" not in fake.last.all_text


# ---------------------------------------------------------------- AC20 / AC21 progress
def test_stu02ps_db_ac20_progress_reports_the_sets_topic_name_for_every_question():
    cid = make_course()
    tid = make_topic(cid, "Seed style topic")
    sid = insert_published_set(cid, tid, "Topic set", questions=question_set((0, 1, 2)))
    s = enrolled_student(cid)
    aid = start(s, sid)
    save(aid, s, full_answers(sid, "aaa"))
    submit(aid, s)
    items = call("GET", "/api/progress", s).json()["topics"]["items"]
    assert [i["topic"]["name"] for i in items] == ["Seed style topic"]
    assert items[0]["topic"]["id"] == tid and items[0]["answered"] == 3 and items[0]["correct"] == 1
    assert items[0]["status"] == "needs_practice"


def test_stu02ps_db_ac20_old_fixture_attempts_are_skipped_and_left_courses_hide_their_sets():
    cid, tid, sid, s = member_world()
    insert_attempt(s, answers={"q1": "a", "q2": "b", "q3": "c"}, correct_ids=["q1", "q2", "q3"], set_id="intro-se-1")
    p = call("GET", "/api/progress", s)
    assert p.status_code == 200 and p.json()["practice"]["sets"] == []
    aid = start(s, sid)
    save(aid, s, full_answers(sid, "abc"))
    submit(aid, s)
    assert len(call("GET", "/api/progress", s).json()["practice"]["sets"]) == 1
    unenroll(s, cid)
    assert call("GET", "/api/progress", s).json()["practice"]["sets"] == []
    enroll(s, cid)
    assert len(call("GET", "/api/progress", s).json()["practice"]["sets"]) == 1


def test_stu02ps_db_ac21_retakes_are_unlimited_and_counted():
    cid, tid, sid, s = member_world()
    for letters in ("add", "abd", "abc"):
        aid = start(s, sid)
        save(aid, s, full_answers(sid, letters))
        assert submit(aid, s).status_code == 200
    row = call("GET", "/api/progress", s).json()["practice"]["sets"][0]
    assert row["attempts_submitted"] == 3
    assert row["best"] == {"correct": 3, "total": 3} and row["latest"]["correct"] == 3
    assert _picker(s)["courses"][0]["sets"][0]["best"] == {"correct": 3, "total": 3}


# ---------------------------------------------------------------- AC24 no migration
def test_stu02ps_db_ac24_a_single_alembic_head_and_a_uuid_set_id_is_stored():
    backend = Path(__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-m", "alembic", "heads"], cwd=backend, env=os.environ.copy(),
                         capture_output=True, text=True, check=True).stdout
    heads = re.findall(r"^(\S+) \(head\)", out, flags=re.M)
    assert len(heads) == 1, out  # one head; its name changes as other features add revisions
    cid, tid, sid, s = member_world()
    aid = start(s, sid)
    assert len(sid) == 36
    assert sql("SELECT set_id FROM practice_attempt WHERE id = %s", (aid,)) == [(sid,)]
    assert call("GET", f"/api/attempts/{aid}", s).json()["set_id"] == sid
