"""STU-02 adversarial security tests: answer leakage, cross-student access, score tampering.

Written by the security reviewer from the spec, plan and threat model. Assertions compare
exact JSON keys and values; the only substring checks are against the long, fixed
explanation sentences, which random ids cannot contain.
"""
import asyncio
import json
import uuid

import httpx
from main import app

SET = "intro-se-1"
KEY = {"q1": "a", "q2": "b", "q3": "c"}
WRONG = {"q1": "b", "q2": "c", "q3": "a"}
EXPLANATIONS = (
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
)
SECRET_KEYS = {"correct_choice", "explanation", "key_version", "correct", "score"}


def sid() -> str:
    return "sec-" + uuid.uuid4().hex


def call(method, path, student=None, json_body=None, content=None):
    headers = {}
    if student is not None:
        headers["X-Student-Id"] = student
    if content is not None:
        headers["Content-Type"] = "application/json"

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            kw = {"headers": headers}
            if json_body is not None:
                kw["json"] = json_body
            if content is not None:
                kw["content"] = content
            return await c.request(method, path, **kw)

    return asyncio.run(send())


def start(student):
    r = call("POST", f"/api/practice-sets/{SET}/attempts", student)
    assert r.status_code == 201
    return r.json()["attempt_id"]


def save(aid, student, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", student, {"answers": answers})


def all_keys(obj) -> set:
    """Every dict key at any depth of a JSON value."""
    found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            found |= all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= all_keys(v)
    return found


def assert_no_key_leak(r):
    text = r.text
    for e in EXPLANATIONS:
        assert e not in text
    try:
        body = r.json()
    except json.JSONDecodeError:
        return
    assert not (all_keys(body) & SECRET_KEYS), all_keys(body) & SECRET_KEYS


# --- Answer leakage before submission (AC1, AC8) ---------------------------------------


def test_stu02_sec_no_key_in_any_response_before_submission():
    s = sid()
    aid = start(s)
    other = sid()
    responses = [
        call("GET", f"/api/practice-sets/{SET}"),
        call("GET", "/api/practice-sets/nope"),
        call("POST", f"/api/practice-sets/{SET}/attempts", None),
        call("GET", f"/api/attempts/{aid}", s),
        call("GET", f"/api/attempts/{aid}", other),
        save(aid, s, {"q1": "a"}),
        save(aid, s, {"q1": "z"}),
        save(aid, s, {"q9": "a"}),
        save(aid, s, {"q1": 1}),
        call("PUT", f"/api/attempts/{aid}/answers", s, content=b"{not json"),
        call("POST", f"/api/attempts/{aid}/submit", s),
        call("GET", f"/api/attempts/{aid}/results", s),
        call("GET", f"/api/attempts/{aid}/results", other),
        call("POST", f"/api/attempts/{aid}/submit", other),
    ]
    for r in responses:
        assert_no_key_leak(r)


def test_stu02_sec_save_is_not_a_correctness_oracle():
    """Saving the right and a wrong choice must give indistinguishable responses."""
    s = sid()
    aid = start(s)
    for qid, right in KEY.items():
        bodies = []
        for choice in ("a", "b", "c"):
            r = save(aid, s, {qid: choice})
            assert r.status_code == 200
            body = r.json()
            assert body["answers"][qid] == choice
            body["answers"].pop(qid)
            bodies.append(body)
        assert bodies[0] == bodies[1] == bodies[2], right


def test_stu02_sec_incomplete_submit_reveals_nothing_and_unlocks_nothing():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "b"})
    r = call("POST", f"/api/attempts/{aid}/submit", s)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "incomplete"
    assert r.json()["detail"]["missing"] == ["q3"]
    assert_no_key_leak(r)
    res = call("GET", f"/api/attempts/{aid}/results", s)
    assert res.status_code == 403
    assert_no_key_leak(res)


# --- Score tampering (AC5, AC6) --------------------------------------------------------


def test_stu02_sec_submit_ignores_client_score_and_answers():
    s = sid()
    aid = start(s)
    assert save(aid, s, WRONG).status_code == 200
    forged = {"score": {"correct": 3, "total": 3}, "answers": KEY, "status": "submitted"}
    r = call("POST", f"/api/attempts/{aid}/submit", s, forged)
    assert r.status_code == 200
    assert r.json()["score"] == {"correct": 0, "total": 3}
    res = call("GET", f"/api/attempts/{aid}/results", s).json()
    assert res["score"] == {"correct": 0, "total": 3}
    assert res["answers"] == WRONG
    assert [q["correct"] for q in res["questions"]] == [False, False, False]


def test_stu02_sec_submit_body_answers_do_not_complete_an_incomplete_attempt():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "a"})
    r = call("POST", f"/api/attempts/{aid}/submit", s, {"answers": KEY})
    assert r.status_code == 422
    assert r.json()["detail"]["missing"] == ["q2", "q3"]
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {"q1": "a"}


def test_stu02_sec_save_cannot_set_status_or_score():
    s = sid()
    aid = start(s)
    r = call(
        "PUT",
        f"/api/attempts/{aid}/answers",
        s,
        {"answers": {"q1": "a"}, "status": "submitted", "score": {"correct": 3, "total": 3}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert call("GET", f"/api/attempts/{aid}", s).json()["status"] == "in_progress"
    assert call("GET", f"/api/attempts/{aid}/results", s).status_code == 403


def test_stu02_sec_cannot_change_answers_after_seeing_results():
    s = sid()
    aid = start(s)
    save(aid, s, WRONG)
    assert call("POST", f"/api/attempts/{aid}/submit", s).status_code == 200
    before = call("GET", f"/api/attempts/{aid}/results", s).json()
    r = save(aid, s, KEY)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "already_submitted"
    again = call("POST", f"/api/attempts/{aid}/submit", s)
    assert again.status_code == 409
    after = call("GET", f"/api/attempts/{aid}/results", s).json()
    assert after == before
    assert after["score"]["correct"] == 0


def test_stu02_sec_non_string_or_bogus_answers_rejected_and_nothing_saved():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "a"})
    bad_bodies = [
        {"answers": {"q2": 1}},
        {"answers": {"q2": ["b"]}},
        {"answers": {"q2": None}},
        {"answers": {"q2": {"id": "b"}}},
        {"answers": {"q2": "b", "__proto__": "a"}},
        {"answers": {"q2": "b", "constructor": "a"}},
        {"answers": {"q2": "b", "q1 ": "a"}},
        {"answers": {"q2": "B"}},
        {"answers": {"q2": " b"}},
        {"answers": {"q2": ""}},
        {"answers": ["q2", "b"]},
        {"answers": None},
    ]
    for body in bad_bodies:
        r = call("PUT", f"/api/attempts/{aid}/answers", s, body)
        assert r.status_code == 422, body
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {"q1": "a"}


# --- Cross-student access (AC9) --------------------------------------------------------


def test_stu02_sec_other_student_gets_same_404_as_unknown_attempt():
    owner = sid()
    aid = start(owner)
    save(aid, owner, {"q1": "a"})
    intruder = sid()
    unknown = "x" + uuid.uuid4().hex
    for method, suffix, body in [
        ("GET", "", None),
        ("PUT", "/answers", {"answers": {"q2": "b"}}),
        ("POST", "/submit", None),
        ("GET", "/results", None),
    ]:
        real = call(method, f"/api/attempts/{aid}{suffix}", intruder, body)
        fake = call(method, f"/api/attempts/{unknown}{suffix}", intruder, body)
        assert real.status_code == fake.status_code == 404
        assert real.json() == fake.json()
        assert real.json()["detail"]["code"] == "attempt_not_found"


def test_stu02_sec_other_student_cannot_mutate_or_submit():
    owner = sid()
    aid = start(owner)
    save(aid, owner, {"q1": "a", "q2": "b"})
    intruder = sid()
    save(aid, intruder, {"q3": "c"})
    call("POST", f"/api/attempts/{aid}/submit", intruder)
    state = call("GET", f"/api/attempts/{aid}", owner).json()
    assert state["status"] == "in_progress"
    assert state["answers"] == {"q1": "a", "q2": "b"}


def test_stu02_sec_other_student_cannot_read_results_of_submitted_attempt():
    owner = sid()
    aid = start(owner)
    save(aid, owner, KEY)
    assert call("POST", f"/api/attempts/{aid}/submit", owner).status_code == 200
    r = call("GET", f"/api/attempts/{aid}/results", sid())
    assert r.status_code == 404
    assert_no_key_leak(r)


def test_stu02_sec_identity_variants_do_not_match_owner():
    owner = sid()
    aid = start(owner)
    # Surrounding whitespace is trimmed (same student); see test_stu02_fixes.py.
    for variant in (owner.upper(), owner[:-1]):
        r = call("GET", f"/api/attempts/{aid}", variant)
        assert r.status_code == 404, repr(variant)


def test_stu02_sec_blank_identity_rejected_everywhere():
    owner = sid()
    aid = start(owner)
    for student in (None, "", "   "):
        for method, path in [
            ("POST", f"/api/practice-sets/{SET}/attempts"),
            ("GET", f"/api/attempts/{aid}"),
            ("PUT", f"/api/attempts/{aid}/answers"),
            ("POST", f"/api/attempts/{aid}/submit"),
            ("GET", f"/api/attempts/{aid}/results"),
        ]:
            r = call(method, path, student, {"answers": {"q1": "a"}})
            assert r.status_code == 401, (method, path, repr(student))
            assert r.json()["detail"]["code"] == "missing_student"


def test_stu02_sec_malformed_body_does_not_reveal_attempt_existence():
    owner = sid()
    aid = start(owner)
    intruder = sid()
    unknown = "x" + uuid.uuid4().hex
    real = call("PUT", f"/api/attempts/{aid}/answers", intruder, content=b"{not json")
    fake = call("PUT", f"/api/attempts/{unknown}/answers", intruder, content=b"{not json")
    assert real.status_code == fake.status_code
    assert real.json() == fake.json()
    # Unauthenticated callers get 401 for a schema-invalid body.
    anon = call("PUT", f"/api/attempts/{aid}/answers", None, {"answers": 1})
    assert anon.status_code == 401
    # Unparseable JSON is rejected by FastAPI before the header check (finding STU02-SEC-L1).
    # It must still not distinguish an existing attempt from an unknown one.
    anon_real = call("PUT", f"/api/attempts/{aid}/answers", None, content=b"{not json")
    anon_fake = call("PUT", f"/api/attempts/{unknown}/answers", None, content=b"{not json")
    assert anon_real.status_code == anon_fake.status_code
    assert anon_real.json() == anon_fake.json()


def test_stu02_sec_attempt_ids_are_opaque_and_unique():
    s = sid()
    ids = [start(s) for _ in range(50)]
    assert len(set(ids)) == len(ids)
    for aid in ids:
        assert len(aid) >= 16
        assert not aid.isdigit()


def test_stu02_sec_odd_set_ids_return_clean_404():
    for set_id in ("..", "intro-se-1%00", "INTRO-SE-1", "intro-se-1 ", "%2e%2e%2fmain"):
        r = call("GET", f"/api/practice-sets/{set_id}")
        assert r.status_code == 404, set_id
        r = call("POST", f"/api/practice-sets/{set_id}/attempts", sid())
        assert r.status_code == 404, set_id
