"""STU-02 practice attempt API tests, written from the plan contract only."""
import asyncio
import uuid

import httpx
from main import app

SET = "intro-se-1"
KEY = {"q1": "a", "q2": "b", "q3": "c"}
EXPLANATIONS = [
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
]


def sid():
    return "s-" + uuid.uuid4().hex


def call(method, path, student="default", json_body=None):
    headers = {}
    if student == "default":
        student = sid()
    if student is not None:
        headers["X-Student-Id"] = student

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as c:
            kw = {"headers": headers}
            if json_body is not None:
                kw["json"] = json_body
            return await c.request(method, path, **kw)

    return asyncio.run(send())


def start(student):
    r = call("POST", f"/api/practice-sets/{SET}/attempts", student)
    assert r.status_code == 201
    return r.json()["attempt_id"]


def save(aid, student, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", student, {"answers": answers})


def submit(aid, student, body=None):
    return call("POST", f"/api/attempts/{aid}/submit", student, body)


def results(aid, student):
    return call("GET", f"/api/attempts/{aid}/results", student)


def get_attempt(aid, student):
    return call("GET", f"/api/attempts/{aid}", student)


def code_of(r):
    return r.json()["detail"]["code"]


def assert_no_leak(r):
    for e in EXPLANATIONS:
        assert e not in r.text
    assert "correct_choice" not in r.text
    assert "explanation" not in r.text
    assert "key_version" not in r.text


# AC1
def test_stu02_ac1_read_set():
    r = call("GET", f"/api/practice-sets/{SET}", None)
    assert r.status_code == 200
    b = r.json()
    assert b["id"] == SET
    assert b["title"] == "Software engineering basics"
    assert [q["id"] for q in b["questions"]] == ["q1", "q2", "q3"]
    assert b["questions"][0]["code"] is None
    q3 = b["questions"][2]
    assert q3["code"] == "values = [1, 2, 3]\nprint(len(values))"
    assert [c["id"] for c in q3["choices"]] == ["a", "b", "c"]
    assert q3["choices"][2]["text"] == "3"
    assert_no_leak(r)


def test_stu02_ac1_unknown_set_404():
    r = call("GET", "/api/practice-sets/nope", None)
    assert r.status_code == 404
    assert code_of(r) == "set_not_found"


# AC2
def test_stu02_ac2_start_attempt():
    r = call("POST", f"/api/practice-sets/{SET}/attempts")
    assert r.status_code == 201
    b = r.json()
    assert b["set_id"] == SET
    assert b["status"] == "in_progress"
    assert b["answers"] == {}
    assert isinstance(b["attempt_id"], str) and len(b["attempt_id"]) >= 8


def test_stu02_ac2_start_requires_header():
    for s in (None, ""):
        r = call("POST", f"/api/practice-sets/{SET}/attempts", s)
        assert r.status_code == 401
        assert code_of(r) == "missing_student"


def test_stu02_ac2_start_unknown_set():
    r = call("POST", "/api/practice-sets/nope/attempts")
    assert r.status_code == 404
    assert code_of(r) == "set_not_found"


def test_stu02_ac2_get_attempt():
    s = sid()
    aid = start(s)
    r = get_attempt(aid, s)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid, "set_id": SET, "status": "in_progress", "answers": {}
    }


def test_stu02_ac2_attempt_endpoints_require_header():
    s = sid()
    aid = start(s)
    for method, path, body in [
        ("GET", f"/api/attempts/{aid}", None),
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "a"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]:
        for hdr in (None, ""):
            r = call(method, path, hdr, body)
            assert r.status_code == 401, path
            assert code_of(r) == "missing_student"


# AC3
def test_stu02_ac3_save_merge_and_revise():
    s = sid()
    aid = start(s)
    r = save(aid, s, {"q1": "b"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["answers"] == {"q1": "b"}
    assert save(aid, s, {"q2": "a"}).json()["answers"] == {"q1": "b", "q2": "a"}
    assert save(aid, s, {"q1": "c"}).json()["answers"] == {"q1": "c", "q2": "a"}
    assert get_attempt(aid, s).json()["answers"] == {"q1": "c", "q2": "a"}


def test_stu02_ac3_unknown_question_rejected():
    s = sid()
    r = save(start(s), s, {"q9": "a"})
    assert r.status_code == 422
    assert code_of(r) == "unknown_question"


def test_stu02_ac3_invalid_choice_rejected():
    s = sid()
    r = save(start(s), s, {"q1": "z"})
    assert r.status_code == 422
    assert code_of(r) == "invalid_choice"


def test_stu02_ac3_rejected_request_saves_nothing():
    s = sid()
    aid = start(s)
    assert save(aid, s, {"q1": "a", "q2": "zzz"}).status_code == 422
    assert get_attempt(aid, s).json()["answers"] == {}
    assert save(aid, s, {"q1": "a", "q9": "a"}).status_code == 422
    assert get_attempt(aid, s).json()["answers"] == {}


# AC4
def test_stu02_ac4_incomplete_submit_rejected():
    s = sid()
    aid = start(s)
    save(aid, s, {"q2": "b"})
    r = submit(aid, s)
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["code"] == "incomplete"
    assert d["missing"] == ["q1", "q3"]
    assert_no_leak(r)
    g = get_attempt(aid, s).json()
    assert g["status"] == "in_progress"
    assert g["answers"] == {"q2": "b"}
    r = results(aid, s)
    assert r.status_code == 403
    assert code_of(r) == "not_submitted"


def test_stu02_ac4_nothing_answered_lists_all():
    s = sid()
    r = submit(start(s), s)
    assert r.status_code == 422
    assert r.json()["detail"]["missing"] == ["q1", "q2", "q3"]


# AC5
def test_stu02_ac5_submit_scores_server_side():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "a", "q3": "c"})
    r = submit(aid, s)
    assert r.status_code == 200
    assert r.json() == {
        "attempt_id": aid, "status": "submitted",
        "score": {"correct": 2, "total": 3},
    }
    assert get_attempt(aid, s).json()["status"] == "submitted"


def test_stu02_ac5_all_correct_and_all_wrong():
    s = sid()
    a1 = start(s)
    save(a1, s, dict(KEY))
    assert submit(a1, s).json()["score"] == {"correct": 3, "total": 3}
    a2 = start(s)
    save(a2, s, {"q1": "b", "q2": "c", "q3": "a"})
    assert submit(a2, s).json()["score"] == {"correct": 0, "total": 3}


def test_stu02_ac5_client_score_ignored():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "b", "q2": "c", "q3": "a"})
    r = submit(aid, s, {"score": {"correct": 3, "total": 3}, "correct": 3})
    assert r.status_code == 200
    assert r.json()["score"] == {"correct": 0, "total": 3}


# AC6
def test_stu02_ac6_no_change_after_submit():
    s = sid()
    aid = start(s)
    save(aid, s, dict(KEY))
    submit(aid, s)
    r = save(aid, s, {"q1": "b"})
    assert r.status_code == 409
    assert code_of(r) == "already_submitted"
    assert get_attempt(aid, s).json()["answers"] == KEY


def test_stu02_ac6_no_resubmit():
    s = sid()
    aid = start(s)
    save(aid, s, dict(KEY))
    submit(aid, s)
    r = submit(aid, s)
    assert r.status_code == 409
    assert code_of(r) == "already_submitted"


def test_stu02_ac6_state_checked_before_validation():
    s = sid()
    aid = start(s)
    save(aid, s, dict(KEY))
    submit(aid, s)
    assert save(aid, s, {"q9": "zz"}).status_code == 409


# AC7
def test_stu02_ac7_results_after_submit():
    s = sid()
    aid = start(s)
    ans = {"q1": "a", "q2": "c", "q3": "c"}
    save(aid, s, ans)
    submit(aid, s)
    r = results(aid, s)
    assert r.status_code == 200
    b = r.json()
    assert b["attempt_id"] == aid
    assert b["set_id"] == SET
    assert b["key_version"] == "v1"
    assert b["score"] == {"correct": 2, "total": 3}
    assert b["answers"] == ans
    assert b["questions"] == [
        {"id": "q1", "selected": "a", "correct_choice": "a", "correct": True,
         "explanation": EXPLANATIONS[0]},
        {"id": "q2", "selected": "c", "correct_choice": "b", "correct": False,
         "explanation": EXPLANATIONS[1]},
        {"id": "q3", "selected": "c", "correct_choice": "c", "correct": True,
         "explanation": EXPLANATIONS[2]},
    ]


def test_stu02_ac7_results_not_submitted_403():
    s = sid()
    r = results(start(s), s)
    assert r.status_code == 403
    assert code_of(r) == "not_submitted"


def test_stu02_ac7_results_unknown_attempt():
    r = results("doesnotexist123", sid())
    assert r.status_code == 404
    assert code_of(r) == "attempt_not_found"


# AC8 adversarial: answer leakage before submission
def test_stu02_ac8_no_leak_before_submission():
    s = sid()
    aid = start(s)
    responses = [
        call("GET", f"/api/practice-sets/{SET}", None),
        get_attempt(aid, s),
        save(aid, s, {"q1": "a"}),
        save(aid, s, {"q1": "z"}),
        save(aid, s, {"q9": "a"}),
        submit(aid, s),
        results(aid, s),
        get_attempt("nope-nope-nope", s),
        get_attempt(aid, None),
        call("POST", f"/api/practice-sets/{SET}/attempts", None),
        call("GET", "/api/practice-sets/nope", None),
    ]
    for r in responses:
        assert_no_leak(r)


def test_stu02_ac8_no_leak_after_partial_answers():
    s = sid()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "b"})
    for r in (submit(aid, s), results(aid, s), get_attempt(aid, s)):
        assert_no_leak(r)


# AC9 adversarial: cross-student access
def test_stu02_ac9_cross_student_all_endpoints_404_and_indistinguishable():
    owner, other = sid(), sid()
    aid = start(owner)
    save(aid, owner, dict(KEY))
    submit(aid, owner)
    unknown = get_attempt("unknown-id-123", other)
    assert unknown.status_code == 404
    for r in (
        get_attempt(aid, other),
        save(aid, other, {"q1": "a"}),
        submit(aid, other),
        results(aid, other),
    ):
        assert r.status_code == 404
        assert code_of(r) == "attempt_not_found"
        assert r.json() == unknown.json()
        assert_no_leak(r)


def test_stu02_ac9_cross_student_cannot_modify():
    owner, other = sid(), sid()
    aid = start(owner)
    save(aid, owner, {"q1": "a"})
    assert save(aid, other, {"q1": "c"}).status_code == 404
    assert submit(aid, other).status_code == 404
    g = get_attempt(aid, owner).json()
    assert g["answers"] == {"q1": "a"}
    assert g["status"] == "in_progress"


def test_stu02_ac9_ownership_checked_before_state_and_validation():
    owner, other = sid(), sid()
    aid = start(owner)
    assert results(aid, other).status_code == 404  # not 403
    assert save(aid, other, {"q9": "zz"}).status_code == 404  # not 422
    assert submit(aid, other).status_code == 404  # not 422
    save(aid, owner, dict(KEY))
    submit(aid, owner)
    assert save(aid, other, {"q1": "a"}).status_code == 404  # not 409
    assert submit(aid, other).status_code == 404  # not 409


def test_stu02_ac9_header_checked_before_existence():
    assert get_attempt("unknown-id-123", None).status_code == 401


def test_stu02_ac9_attempt_ids_opaque_and_unique():
    s = sid()
    ids = {start(s) for _ in range(5)}
    assert len(ids) == 5
    for i in ids:
        assert len(i) >= 8
        assert not i.isdigit()


# AC10
def test_stu02_ac10_independent_attempts():
    s = sid()
    a1, a2 = start(s), start(s)
    assert a1 != a2
    save(a1, s, dict(KEY))
    submit(a1, s)
    g2 = get_attempt(a2, s).json()
    assert g2["status"] == "in_progress"
    assert g2["answers"] == {}
    assert save(a2, s, {"q1": "b"}).status_code == 200
    assert results(a2, s).status_code == 403
    assert results(a1, s).status_code == 200


# AC11
def test_stu02_ac11_health_still_works():
    r = call("GET", "/api/health", None)
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    r = call("GET", "/api/health/ready", None)
    assert r.status_code == 200 and r.json() == {"status": "ready"}
