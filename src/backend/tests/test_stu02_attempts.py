"""STU-02 practice attempt API tests, written from the plan contract only."""
import asyncio
import json
import uuid

import httpx
from main import app

SET_ID = "intro-se-1"
QIDS = ["q1", "q2", "q3"]
CORRECT = {"q1": "a", "q2": "b", "q3": "c"}
EXPLANATIONS = [
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
]
LEAK_KEYS = {"correct_choice", "explanation", "key_version", "correct", "is_correct"}


def call(method, path, student=None, body=None, headers=None):
    hdrs = dict(headers or {})
    if student is not None:
        hdrs["X-Student-Id"] = student

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            kwargs = {"headers": hdrs}
            if body is not None:
                kwargs["json"] = body
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def sid():
    return "student-" + uuid.uuid4().hex


def start(student, set_id=SET_ID):
    r = call("POST", f"/api/practice-sets/{set_id}/attempts", student)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


def save(student, aid, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", student, {"answers": answers})


def submit(student, aid, body=None):
    return call("POST", f"/api/attempts/{aid}/submit", student, body)


def results(student, aid):
    return call("GET", f"/api/attempts/{aid}/results", student)


def full_correct():
    return dict(CORRECT)


def assert_no_leak(response):
    text = response.text
    for e in EXPLANATIONS:
        assert e not in text
    assert "explanation" not in text.lower()
    assert "correct_choice" not in text
    assert "key_version" not in text
    assert "v1" not in text


def keys_deep(obj):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k)
            out |= keys_deep(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= keys_deep(v)
    return out


def err_code(r):
    return r.json()["detail"]["code"]


# ---- AC1 ----
def test_stu02_ac1_read_set_shape_and_order():
    r = call("GET", f"/api/practice-sets/{SET_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == SET_ID
    assert body["title"] == "Software engineering basics"
    assert [q["id"] for q in body["questions"]] == QIDS
    for q in body["questions"]:
        assert set(q.keys()) == {"id", "text", "code", "choices"}
        assert [c["id"] for c in q["choices"]] == ["a", "b", "c"]
        for c in q["choices"]:
            assert set(c.keys()) == {"id", "text"}
    qs = {q["id"]: q for q in body["questions"]}
    assert qs["q1"]["code"] is None and qs["q2"]["code"] is None
    assert qs["q3"]["code"] == "values = [1, 2, 3]\nprint(len(values))"
    assert qs["q1"]["text"] == "What should a well-designed function have?"
    assert qs["q3"]["choices"][2]["text"] == "3"


def test_stu02_ac1_read_set_does_not_leak_key():
    r = call("GET", f"/api/practice-sets/{SET_ID}")
    assert_no_leak(r)
    assert not (keys_deep(r.json()) & LEAK_KEYS)


def test_stu02_ac1_read_set_needs_no_header_and_unknown_is_404():
    assert call("GET", f"/api/practice-sets/{SET_ID}").status_code == 200
    r = call("GET", "/api/practice-sets/nope")
    assert r.status_code == 404
    assert err_code(r) == "set_not_found"


# ---- AC2 ----
def test_stu02_ac2_start_attempt():
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", sid())
    assert r.status_code == 201
    b = r.json()
    assert b["set_id"] == SET_ID
    assert b["status"] == "in_progress"
    assert b["answers"] == {}
    assert isinstance(b["attempt_id"], str) and len(b["attempt_id"]) >= 8


def test_stu02_ac2_start_requires_header():
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts")
    assert r.status_code == 401
    assert err_code(r) == "missing_student"
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", "")
    assert r.status_code == 401
    assert err_code(r) == "missing_student"


def test_stu02_ac2_start_unknown_set():
    r = call("POST", "/api/practice-sets/nope/attempts", sid())
    assert r.status_code == 404
    assert err_code(r) == "set_not_found"


def test_stu02_ac2_get_attempt_and_header_required():
    s = sid()
    aid = start(s)
    r = call("GET", f"/api/attempts/{aid}", s)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid, "set_id": SET_ID, "status": "in_progress", "answers": {}
    }
    r = call("GET", f"/api/attempts/{aid}")
    assert r.status_code == 401
    assert err_code(r) == "missing_student"


def test_stu02_ac2_all_attempt_endpoints_require_header():
    s = sid()
    aid = start(s)
    for method, path, body in [
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "a"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]:
        r = call(method, path, None, body)
        assert r.status_code == 401, path
        assert err_code(r) == "missing_student"
        r = call(method, path, "", body)
        assert r.status_code == 401, path


# ---- AC3 ----
def test_stu02_ac3_save_and_revise_answers():
    s = sid()
    aid = start(s)
    r = save(s, aid, {"q1": "b"})
    assert r.status_code == 200
    assert r.json() == {"attempt_id": aid, "status": "in_progress", "answers": {"q1": "b"}}
    r = save(s, aid, {"q1": "a", "q2": "c"})
    assert r.json()["answers"] == {"q1": "a", "q2": "c"}
    r = save(s, aid, {"q2": "b"})
    assert r.json()["answers"] == {"q1": "a", "q2": "b"}
    g = call("GET", f"/api/attempts/{aid}", s)
    assert g.json()["answers"] == {"q1": "a", "q2": "b"}


def test_stu02_ac3_unknown_question_rejected():
    s = sid()
    aid = start(s)
    r = save(s, aid, {"q99": "a"})
    assert r.status_code == 422
    assert err_code(r) == "unknown_question"
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {}


def test_stu02_ac3_invalid_choice_rejected():
    s = sid()
    aid = start(s)
    for bad in ("z", "", "A", "ab"):
        r = save(s, aid, {"q1": bad})
        assert r.status_code == 422
        assert err_code(r) == "invalid_choice"
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {}


def test_stu02_ac3_rejected_request_saves_nothing():
    s = sid()
    aid = start(s)
    save(s, aid, {"q1": "a"})
    r = save(s, aid, {"q2": "b", "q3": "zzz"})
    assert r.status_code == 422
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {"q1": "a"}
    r = save(s, aid, {"q2": "b", "q77": "a"})
    assert r.status_code == 422
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {"q1": "a"}


# ---- AC4 ----
def test_stu02_ac4_incomplete_submit_rejected_with_missing_in_order():
    s = sid()
    aid = start(s)
    save(s, aid, {"q2": "b"})
    r = submit(s, aid)
    assert r.status_code == 422
    assert err_code(r) == "incomplete"
    assert r.json()["detail"]["missing"] == ["q1", "q3"]
    g = call("GET", f"/api/attempts/{aid}", s).json()
    assert g["status"] == "in_progress"
    assert g["answers"] == {"q2": "b"}


def test_stu02_ac4_nothing_answered_lists_all_in_order():
    s = sid()
    aid = start(s)
    r = submit(s, aid)
    assert r.status_code == 422
    assert r.json()["detail"]["missing"] == QIDS


def test_stu02_ac4_incomplete_unlocks_nothing_and_does_not_leak():
    s = sid()
    aid = start(s)
    save(s, aid, {"q1": "a"})
    r = submit(s, aid)
    assert_no_leak(r)
    r2 = results(s, aid)
    assert r2.status_code == 403
    assert err_code(r2) == "not_submitted"
    assert_no_leak(r2)
    # still editable and then submittable
    assert save(s, aid, {"q2": "b", "q3": "c"}).status_code == 200
    assert submit(s, aid).status_code == 200


# ---- AC5 ----
def test_stu02_ac5_submit_complete_scores():
    s = sid()
    aid = start(s)
    save(s, aid, full_correct())
    r = submit(s, aid)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid, "status": "submitted", "score": {"correct": 3, "total": 3}
    }
    assert call("GET", f"/api/attempts/{aid}", s).json()["status"] == "submitted"


def test_stu02_ac5_partial_score():
    s = sid()
    aid = start(s)
    save(s, aid, {"q1": "b", "q2": "b", "q3": "a"})
    assert submit(s, aid).json()["score"] == {"correct": 1, "total": 3}
    aid2 = start(s)
    save(s, aid2, {"q1": "c", "q2": "c", "q3": "a"})
    assert submit(s, aid2).json()["score"] == {"correct": 0, "total": 3}


def test_stu02_ac5_client_supplied_score_ignored():
    s = sid()
    aid = start(s)
    save(s, aid, {"q1": "b", "q2": "c", "q3": "a"})
    r = submit(s, aid, {"score": {"correct": 3, "total": 3}, "correct": 3, "answers": full_correct()})
    assert r.status_code == 200
    assert r.json()["score"] == {"correct": 0, "total": 3}
    res = results(s, aid).json()
    assert res["score"] == {"correct": 0, "total": 3}
    assert res["answers"] == {"q1": "b", "q2": "c", "q3": "a"}


def test_stu02_ac5_submit_body_cannot_fill_missing_answers():
    s = sid()
    aid = start(s)
    r = submit(s, aid, {"answers": full_correct()})
    assert r.status_code == 422
    assert err_code(r) == "incomplete"


# ---- AC6 ----
def test_stu02_ac6_no_changes_after_submit():
    s = sid()
    aid = start(s)
    save(s, aid, full_correct())
    submit(s, aid)
    r = save(s, aid, {"q1": "b"})
    assert r.status_code == 409
    assert err_code(r) == "already_submitted"
    assert results(s, aid).json()["answers"] == full_correct()


def test_stu02_ac6_no_resubmit():
    s = sid()
    aid = start(s)
    save(s, aid, full_correct())
    assert submit(s, aid).status_code == 200
    r = submit(s, aid)
    assert r.status_code == 409
    assert err_code(r) == "already_submitted"
    assert results(s, aid).json()["score"] == {"correct": 3, "total": 3}


def test_stu02_ac6_rejected_edit_after_submit_prefers_state_over_validation():
    s = sid()
    aid = start(s)
    save(s, aid, full_correct())
    submit(s, aid)
    r = save(s, aid, {"q99": "zz"})
    assert r.status_code == 409
    assert err_code(r) == "already_submitted"


# ---- AC7 ----
def test_stu02_ac7_results_content():
    s = sid()
    aid = start(s)
    answers = {"q1": "a", "q2": "c", "q3": "c"}
    save(s, aid, answers)
    submit(s, aid)
    r = results(s, aid)
    assert r.status_code == 200
    b = r.json()
    assert b["attempt_id"] == aid
    assert b["set_id"] == SET_ID
    assert b["key_version"] == "v1"
    assert b["score"] == {"correct": 2, "total": 3}
    assert b["answers"] == answers
    assert [q["id"] for q in b["questions"]] == QIDS
    expected = [
        {"id": "q1", "selected": "a", "correct_choice": "a", "correct": True, "explanation": EXPLANATIONS[0]},
        {"id": "q2", "selected": "c", "correct_choice": "b", "correct": False, "explanation": EXPLANATIONS[1]},
        {"id": "q3", "selected": "c", "correct_choice": "c", "correct": True, "explanation": EXPLANATIONS[2]},
    ]
    assert b["questions"] == expected


def test_stu02_ac7_results_before_submit_forbidden():
    s = sid()
    aid = start(s)
    r = results(s, aid)
    assert r.status_code == 403
    assert err_code(r) == "not_submitted"


# ---- AC8 ----
def test_stu02_ac8_no_leak_in_any_unsubmitted_response():
    s = sid()
    aid = start(s)
    responses = [
        call("POST", f"/api/practice-sets/{SET_ID}/attempts", s),
        call("GET", f"/api/practice-sets/{SET_ID}"),
        call("GET", f"/api/attempts/{aid}", s),
        save(s, aid, {"q1": "a"}),
        save(s, aid, {"q1": "zzz"}),
        save(s, aid, {"q99": "a"}),
        submit(s, aid),
        results(s, aid),
        call("GET", f"/api/attempts/{aid}"),
        call("GET", "/api/attempts/does-not-exist-123", s),
        call("GET", "/api/practice-sets/nope"),
    ]
    for r in responses:
        assert_no_leak(r)
        try:
            body = r.json()
        except ValueError:
            continue
        assert not (keys_deep(body) & LEAK_KEYS), r.text


def test_stu02_ac8_422_validation_errors_do_not_echo_key():
    s = sid()
    aid = start(s)
    r = call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": "not-a-dict"})
    assert r.status_code == 422
    assert_no_leak(r)
    r = call("PUT", f"/api/attempts/{aid}/answers", s, {})
    assert_no_leak(r)


def test_stu02_ac8_invalid_choice_error_does_not_reveal_correct_choice():
    s = sid()
    aid = start(s)
    r = save(s, aid, {"q1": "zzz"})
    detail = json.dumps(r.json()["detail"])
    assert "explanation" not in detail.lower()
    # message must not name a valid/correct choice for the question
    assert "correct_choice" not in detail


def test_stu02_ac8_failed_submit_attempt_does_not_release_results():
    s = sid()
    aid = start(s)
    save(s, aid, {"q1": "a", "q2": "b"})
    for _ in range(3):
        assert submit(s, aid).status_code == 422
    r = results(s, aid)
    assert r.status_code == 403
    assert_no_leak(r)


# ---- AC9 ----
def test_stu02_ac9_other_student_gets_404_everywhere():
    owner, other = sid(), sid()
    aid = start(owner)
    save(owner, aid, {"q1": "a"})
    for method, path, body in [
        ("GET", f"/api/attempts/{aid}", None),
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "b"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]:
        r = call(method, path, other, body)
        assert r.status_code == 404, (method, path)
        assert err_code(r) == "attempt_not_found"
    # owner's state untouched
    g = call("GET", f"/api/attempts/{aid}", owner).json()
    assert g["status"] == "in_progress" and g["answers"] == {"q1": "a"}


def test_stu02_ac9_cannot_tell_existing_from_nonexistent():
    owner, other = sid(), sid()
    aid = start(owner)
    submit_ready = start(owner)
    save(owner, submit_ready, full_correct())
    submit(owner, submit_ready)
    fake = "nonexistent-" + uuid.uuid4().hex
    for real in (aid, submit_ready):
        for method, suffix, body in [
            ("GET", "", None),
            ("PUT", "/answers", {"answers": {"q1": "a"}}),
            ("POST", "/submit", None),
            ("GET", "/results", None),
        ]:
            a = call(method, f"/api/attempts/{real}{suffix}", other, body)
            b = call(method, f"/api/attempts/{fake}{suffix}", other, body)
            assert a.status_code == b.status_code == 404
            assert a.json() == b.json()


def test_stu02_ac9_other_student_cannot_see_submitted_results():
    owner, other = sid(), sid()
    aid = start(owner)
    save(owner, aid, full_correct())
    submit(owner, aid)
    r = results(other, aid)
    assert r.status_code == 404
    assert_no_leak(r)
    assert "v1" not in r.text


def test_stu02_ac9_other_student_cannot_submit_or_edit_submitted():
    owner, other = sid(), sid()
    aid = start(owner)
    save(owner, aid, full_correct())
    submit(owner, aid)
    # state error (409) must not be revealed to non-owner
    assert save(other, aid, {"q1": "a"}).status_code == 404
    assert submit(other, aid).status_code == 404


def test_stu02_ac9_ownership_checked_before_validation_and_state():
    owner, other = sid(), sid()
    aid = start(owner)
    r = save(other, aid, {"q99": "zzz"})
    assert r.status_code == 404
    r = submit(other, aid)  # owner's attempt is incomplete; must be 404 not 422 w/ missing
    assert r.status_code == 404
    assert "missing" not in r.json()["detail"]


def test_stu02_ac9_header_checked_before_existence():
    r = call("GET", "/api/attempts/does-not-exist-123")
    assert r.status_code == 401


def test_stu02_ac9_attempt_ids_opaque_and_unique():
    s = sid()
    ids = [start(s) for _ in range(5)]
    assert len(set(ids)) == 5
    for i in ids:
        assert isinstance(i, str) and len(i) >= 8 and not i.isdigit()


def test_stu02_ac9_student_id_case_and_prefix_not_confused():
    owner = sid()
    aid = start(owner)
    for other in (owner.upper(), owner + "x", owner[:-1], " " + owner):
        assert call("GET", f"/api/attempts/{aid}", other).status_code == 404


# ---- AC10 ----
def test_stu02_ac10_attempts_independent():
    s = sid()
    a1, a2 = start(s), start(s)
    assert a1 != a2
    save(s, a1, full_correct())
    submit(s, a1)
    g2 = call("GET", f"/api/attempts/{a2}", s).json()
    assert g2["status"] == "in_progress" and g2["answers"] == {}
    assert save(s, a2, {"q1": "b"}).status_code == 200
    assert results(s, a1).json()["answers"] == full_correct()
    assert results(s, a2).status_code == 403


def test_stu02_ac10_different_students_same_set_independent():
    s1, s2 = sid(), sid()
    a1, a2 = start(s1), start(s2)
    save(s1, a1, {"q1": "a"})
    assert call("GET", f"/api/attempts/{a2}", s2).json()["answers"] == {}


# ---- AC11 ----
def test_stu02_ac11_health_still_works():
    r = call("GET", "/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    r = call("GET", "/api/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready"}
