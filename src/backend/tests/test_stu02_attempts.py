"""STU-02 practice attempt API, tested through the real ASGI app."""
import asyncio
import uuid

import httpx
from main import app

SET_ID = "intro-se-1"
CORRECT = {"q1": "a", "q2": "b", "q3": "c"}
EXPLANATIONS = [
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
]
LEAK_KEYS = ["correct_choice", "explanation", "key_version"]


def call(method, path, student=None, json=None, headers=None):
    hdrs = dict(headers or {})
    if student is not None:
        hdrs["X-Student-Id"] = student

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, headers=hdrs, json=json)

    return asyncio.run(send())


def new_student():
    return "stu-" + uuid.uuid4().hex


def start(student, set_id=SET_ID):
    r = call("POST", f"/api/practice-sets/{set_id}/attempts", student)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


def save(aid, student, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", student, {"answers": answers})


def submit(aid, student, json=None):
    return call("POST", f"/api/attempts/{aid}/submit", student, json)


def results(aid, student):
    return call("GET", f"/api/attempts/{aid}/results", student)


def code_of(r):
    return r.json()["detail"]["code"]


def assert_no_leak(r):
    text = r.text
    for k in LEAK_KEYS:
        assert k not in text, f"{k} leaked: {text}"
    for e in EXPLANATIONS:
        assert e not in text, f"explanation leaked: {text}"


# AC1
def test_stu02_ac1_read_set_shape_and_order():
    r = call("GET", f"/api/practice-sets/{SET_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == SET_ID
    assert body["title"] == "Software engineering basics"
    qs = body["questions"]
    assert [q["id"] for q in qs] == ["q1", "q2", "q3"]
    assert qs[0]["text"] == "What should a well-designed function have?"
    assert qs[0]["code"] is None
    assert qs[2]["code"] == "values = [1, 2, 3]\nprint(len(values))"
    for q in qs:
        assert set(q.keys()) == {"id", "text", "code", "choices"}
        assert [c["id"] for c in q["choices"]] == ["a", "b", "c"]
        for c in q["choices"]:
            assert set(c.keys()) == {"id", "text"}
    assert qs[1]["choices"][1]["text"] == "To catch regressions when code changes"


def test_stu02_ac1_read_set_has_no_key_or_explanation():
    r = call("GET", f"/api/practice-sets/{SET_ID}")
    assert_no_leak(r)
    assert "correct" not in r.text.lower().replace("incorrect", "")


def test_stu02_ac1_unknown_set_404():
    r = call("GET", "/api/practice-sets/nope")
    assert r.status_code == 404
    assert code_of(r) == "set_not_found"


# AC2
def test_stu02_ac2_start_attempt():
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", new_student())
    assert r.status_code == 201
    body = r.json()
    assert body["set_id"] == SET_ID
    assert body["status"] == "in_progress"
    assert body["answers"] == {}
    assert isinstance(body["attempt_id"], str) and len(body["attempt_id"]) >= 8


def test_stu02_ac2_start_requires_header():
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts")
    assert r.status_code == 401
    assert code_of(r) == "missing_student"


def test_stu02_ac2_start_empty_header_rejected():
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", "")
    assert r.status_code == 401
    assert code_of(r) == "missing_student"


def test_stu02_ac2_start_unknown_set():
    r = call("POST", "/api/practice-sets/nope/attempts", new_student())
    assert r.status_code == 404
    assert code_of(r) == "set_not_found"


def test_stu02_ac2_get_attempt_and_header_required():
    s = new_student()
    aid = start(s)
    r = call("GET", f"/api/attempts/{aid}", s)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid,
        "set_id": SET_ID,
        "status": "in_progress",
        "answers": {},
    }
    r = call("GET", f"/api/attempts/{aid}")
    assert r.status_code == 401
    assert code_of(r) == "missing_student"


def test_stu02_ac2_header_required_on_all_attempt_endpoints():
    s = new_student()
    aid = start(s)
    for method, path, body in [
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "a"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]:
        r = call(method, path, None, body)
        assert r.status_code == 401, path
        assert code_of(r) == "missing_student"


# AC3
def test_stu02_ac3_save_and_revise_merges():
    s = new_student()
    aid = start(s)
    r = save(aid, s, {"q1": "b"})
    assert r.status_code == 200
    assert r.json() == {"attempt_id": aid, "status": "in_progress", "answers": {"q1": "b"}}
    r = save(aid, s, {"q2": "a"})
    assert r.json()["answers"] == {"q1": "b", "q2": "a"}
    r = save(aid, s, {"q1": "a"})
    assert r.json()["answers"] == {"q1": "a", "q2": "a"}
    r = call("GET", f"/api/attempts/{aid}", s)
    assert r.json()["answers"] == {"q1": "a", "q2": "a"}


def test_stu02_ac3_unknown_question_rejected_and_nothing_saved():
    s = new_student()
    aid = start(s)
    r = save(aid, s, {"q1": "a", "q99": "a"})
    assert r.status_code == 422
    assert code_of(r) == "unknown_question"
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {}


def test_stu02_ac3_invalid_choice_rejected_and_nothing_saved():
    s = new_student()
    aid = start(s)
    r = save(aid, s, {"q1": "a", "q2": "z"})
    assert r.status_code == 422
    assert code_of(r) == "invalid_choice"
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {}


def test_stu02_ac3_choice_from_other_question_rejected():
    # Choice ids are shared (a/b/c) in this fixture, so use a non-member id.
    s = new_student()
    aid = start(s)
    r = save(aid, s, {"q1": "d"})
    assert r.status_code == 422
    assert code_of(r) == "invalid_choice"


def test_stu02_ac3_malformed_body_422():
    s = new_student()
    aid = start(s)
    r = call("PUT", f"/api/attempts/{aid}/answers", s, {"nope": 1})
    assert r.status_code == 422


# AC4
def test_stu02_ac4_incomplete_submit_rejected():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q2": "b"})
    r = submit(aid, s)
    assert r.status_code == 422
    body = r.json()
    assert body["detail"]["code"] == "incomplete"
    assert body["detail"]["missing"] == ["q1", "q3"]
    assert_no_leak(r)
    st = call("GET", f"/api/attempts/{aid}", s).json()
    assert st["status"] == "in_progress"
    assert st["answers"] == {"q2": "b"}
    assert results(aid, s).status_code == 403


def test_stu02_ac4_missing_all_listed_in_order():
    s = new_student()
    aid = start(s)
    r = submit(aid, s)
    assert r.status_code == 422
    assert r.json()["detail"]["missing"] == ["q1", "q2", "q3"]


def test_stu02_ac4_can_complete_after_rejection():
    s = new_student()
    aid = start(s)
    assert submit(aid, s).status_code == 422
    save(aid, s, CORRECT)
    assert submit(aid, s).status_code == 200


# AC5
def test_stu02_ac5_submit_full_score():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    r = submit(aid, s)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid,
        "status": "submitted",
        "score": {"correct": 3, "total": 3},
    }
    assert call("GET", f"/api/attempts/{aid}", s).json()["status"] == "submitted"


def test_stu02_ac5_partial_and_zero_score():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "a", "q3": "a"})
    assert submit(aid, s).json()["score"] == {"correct": 1, "total": 3}
    aid = start(s)
    save(aid, s, {"q1": "b", "q2": "c", "q3": "a"})
    assert submit(aid, s).json()["score"] == {"correct": 0, "total": 3}


def test_stu02_ac5_client_supplied_score_ignored():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "b", "q2": "c", "q3": "a"})
    r = submit(aid, s, {"score": {"correct": 3, "total": 3}, "correct": 3, "answers": CORRECT})
    assert r.status_code == 200
    assert r.json()["score"] == {"correct": 0, "total": 3}
    assert results(aid, s).json()["score"] == {"correct": 0, "total": 3}


def test_stu02_ac5_attempt_ids_not_sequential():
    s = new_student()
    ids = {start(s) for _ in range(3)}
    assert len(ids) == 3
    assert not any(i.isdigit() for i in ids)


# AC6
def test_stu02_ac6_no_changes_after_submit():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    submit(aid, s)
    r = save(aid, s, {"q1": "b"})
    assert r.status_code == 409
    assert code_of(r) == "already_submitted"
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == CORRECT


def test_stu02_ac6_no_second_submit():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    submit(aid, s)
    r = submit(aid, s)
    assert r.status_code == 409
    assert code_of(r) == "already_submitted"


def test_stu02_ac6_state_checked_before_validation():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    submit(aid, s)
    r = save(aid, s, {"q99": "zz"})
    assert r.status_code == 409


# AC7
def test_stu02_ac7_results_content():
    s = new_student()
    aid = start(s)
    answers = {"q1": "a", "q2": "c", "q3": "c"}
    save(aid, s, answers)
    submit(aid, s)
    r = results(aid, s)
    assert r.status_code == 200
    body = r.json()
    assert body["attempt_id"] == aid
    assert body["set_id"] == SET_ID
    assert body["key_version"] == "v1"
    assert body["score"] == {"correct": 2, "total": 3}
    assert body["answers"] == answers
    assert body["questions"] == [
        {"id": "q1", "selected": "a", "correct_choice": "a", "correct": True,
         "explanation": EXPLANATIONS[0]},
        {"id": "q2", "selected": "c", "correct_choice": "b", "correct": False,
         "explanation": EXPLANATIONS[1]},
        {"id": "q3", "selected": "c", "correct_choice": "c", "correct": True,
         "explanation": EXPLANATIONS[2]},
    ]


def test_stu02_ac7_results_not_available_before_submit():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    r = results(aid, s)
    assert r.status_code == 403
    assert code_of(r) == "not_submitted"
    assert_no_leak(r)


# AC8 (adversarial)
def test_stu02_ac8_no_leak_from_any_unsubmitted_response():
    s = new_student()
    resps = []
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", s)
    resps.append(r)
    aid = r.json()["attempt_id"]
    resps.append(call("GET", f"/api/practice-sets/{SET_ID}"))
    resps.append(call("GET", f"/api/attempts/{aid}", s))
    resps.append(save(aid, s, CORRECT | {"q3": "a"}))
    resps.append(save(aid, s, {"q1": "zzz"}))
    resps.append(save(aid, s, {"q42": "a"}))
    resps.append(save(aid, s, None))
    resps.append(call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": "bad"}))
    resps.append(results(aid, s))
    resps.append(call("GET", f"/api/attempts/{aid}"))
    resps.append(call("GET", "/api/attempts/nonexistent-attempt", s))
    resps.append(call("GET", "/api/practice-sets/nope"))
    resps.append(call("POST", "/api/practice-sets/nope/attempts", s))
    for resp in resps:
        assert_no_leak(resp)
    # Incomplete submit on a fresh attempt
    aid2 = start(s)
    save(aid2, s, {"q1": "a"})
    assert_no_leak(submit(aid2, s))


def test_stu02_ac8_error_bodies_use_standard_shape_without_key():
    s = new_student()
    aid = start(s)
    r = save(aid, s, {"q1": "zzz"})
    d = r.json()["detail"]
    assert set(d.keys()) >= {"code", "message"}
    assert_no_leak(r)


def test_stu02_ac8_no_leak_after_submit_via_non_results_endpoints():
    s = new_student()
    aid = start(s)
    save(aid, s, CORRECT)
    assert_no_leak(submit(aid, s))
    assert_no_leak(call("GET", f"/api/attempts/{aid}", s))
    assert_no_leak(save(aid, s, {"q1": "a"}))
    assert_no_leak(submit(aid, s))


def test_stu02_ac8_unsubmitted_attempt_never_in_results_by_other_routes():
    s = new_student()
    aid = start(s)
    for path in [f"/api/attempts/{aid}/results/", f"/api/attempts/{aid}?include=results"]:
        r = call("GET", path, s)
        assert_no_leak(r)


# AC9 (adversarial)
def test_stu02_ac9_cross_student_all_endpoints_404():
    owner, other = new_student(), new_student()
    aid = start(owner)
    save(aid, owner, {"q1": "a"})
    attempts = [
        ("GET", f"/api/attempts/{aid}", None),
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "b"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]
    for method, path, body in attempts:
        r = call(method, path, other, body)
        assert r.status_code == 404, path
        assert code_of(r) == "attempt_not_found"
    st = call("GET", f"/api/attempts/{aid}", owner).json()
    assert st["status"] == "in_progress"
    assert st["answers"] == {"q1": "a"}


def test_stu02_ac9_other_student_cannot_see_submitted_results():
    owner, other = new_student(), new_student()
    aid = start(owner)
    save(aid, owner, CORRECT)
    submit(aid, owner)
    r = results(aid, other)
    assert r.status_code == 404
    assert code_of(r) == "attempt_not_found"
    assert_no_leak(r)


def test_stu02_ac9_cannot_submit_foreign_complete_attempt():
    owner, other = new_student(), new_student()
    aid = start(owner)
    save(aid, owner, CORRECT)
    assert submit(aid, other).status_code == 404
    assert call("GET", f"/api/attempts/{aid}", owner).json()["status"] == "in_progress"


def test_stu02_ac9_existence_not_revealed():
    owner, other = new_student(), new_student()
    aid = start(owner)
    real = call("GET", f"/api/attempts/{aid}", other)
    fake = call("GET", "/api/attempts/does-not-exist-123", other)
    assert real.status_code == fake.status_code == 404
    assert real.json() == fake.json()
    for method, suffix, body in [("PUT", "/answers", {"answers": {"q1": "a"}}),
                                 ("POST", "/submit", None), ("GET", "/results", None)]:
        a = call(method, f"/api/attempts/{aid}{suffix}", other, body)
        b = call(method, f"/api/attempts/does-not-exist-123{suffix}", other, body)
        assert a.status_code == b.status_code == 404
        assert a.json() == b.json()


def test_stu02_ac9_ownership_checked_before_validation_and_state():
    owner, other = new_student(), new_student()
    aid = start(owner)
    save(aid, owner, CORRECT)
    submit(aid, owner)
    # Foreign student gets 404, not 409 or 422, so state is not revealed.
    assert save(aid, other, {"q99": "zz"}).status_code == 404
    assert submit(aid, other).status_code == 404


# AC10
def test_stu02_ac10_attempts_independent():
    s = new_student()
    a1, a2 = start(s), start(s)
    assert a1 != a2
    save(a1, s, CORRECT)
    submit(a1, s)
    st2 = call("GET", f"/api/attempts/{a2}", s).json()
    assert st2["status"] == "in_progress"
    assert st2["answers"] == {}
    save(a2, s, {"q1": "b"})
    assert call("GET", f"/api/attempts/{a1}", s).json()["answers"] == CORRECT
    assert results(a2, s).status_code == 403


# AC11
def test_stu02_ac11_health_still_works():
    r = call("GET", "/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    r = call("GET", "/api/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready"}
