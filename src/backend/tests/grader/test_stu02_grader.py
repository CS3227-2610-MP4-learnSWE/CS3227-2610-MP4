"""Hidden acceptance and security suite for the STU-02 workflow comparison.

Never shown to the runs. Applied to a finished run's branch after the fact. It
tests only the HTTP contract in workflow/specs/STU-02/plan.md.
"""
import asyncio
import json
import uuid

import httpx
from main import app

SET = "/api/practice-sets/intro-se-1"
KEY = {"q1": "a", "q2": "b", "q3": "c"}
EXPLANATIONS = {
    "q1": "One focused responsibility makes a function easier to understand, test and change.",
    "q2": "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "q3": "len returns the number of items. The list contains three items.",
}
WRONG = {"q1": "b", "q2": "a", "q3": "a"}


def call(method, path, student=None, body=None):
    headers = {"X-Student-Id": student} if student is not None else {}

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=body)

    return asyncio.run(send())


def new_student():
    return f"student-{uuid.uuid4().hex[:8]}"


def code_of(response):
    return response.json()["detail"]["code"]


def start(student):
    response = call("POST", f"{SET}/attempts", student)
    assert response.status_code == 201
    return response.json()["attempt_id"]


def save(student, attempt, answers):
    return call("PUT", f"/api/attempts/{attempt}/answers", student, {"answers": answers})


def leaks(response):
    text = response.text
    return any(e in text for e in EXPLANATIONS.values()) or "explanation" in text or "correct_choice" in text


def test_g01_set_has_questions_without_answers():
    response = call("GET", SET)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "intro-se-1" and data["title"]
    assert [q["id"] for q in data["questions"]] == ["q1", "q2", "q3"]
    for q in data["questions"]:
        assert set(q) >= {"id", "text", "code", "choices"}
        assert [c["id"] for c in q["choices"]] == ["a", "b", "c"]
    assert data["questions"][2]["code"] and data["questions"][0]["code"] is None
    assert not leaks(response) and "key_version" not in response.text and '"correct"' not in response.text


def test_g02_unknown_set_is_404():
    response = call("GET", "/api/practice-sets/nope")
    assert response.status_code == 404 and code_of(response) == "set_not_found"
    response = call("POST", "/api/practice-sets/nope/attempts", new_student())
    assert response.status_code == 404 and code_of(response) == "set_not_found"


def test_g03_start_requires_student_header():
    for header in (None, ""):
        response = call("POST", f"{SET}/attempts", header)
        assert response.status_code == 401 and code_of(response) == "missing_student"


def test_g04_start_creates_empty_in_progress_attempt():
    response = call("POST", f"{SET}/attempts", new_student())
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "in_progress" and data["answers"] == {} and data["set_id"] == "intro-se-1"
    assert isinstance(data["attempt_id"], str) and len(data["attempt_id"]) >= 8


def test_g05_attempt_endpoints_require_header():
    student = new_student()
    attempt = start(student)
    for method, path in (
        ("GET", f"/api/attempts/{attempt}"),
        ("PUT", f"/api/attempts/{attempt}/answers"),
        ("POST", f"/api/attempts/{attempt}/submit"),
        ("GET", f"/api/attempts/{attempt}/results"),
    ):
        body = {"answers": {}} if method == "PUT" else None
        response = call(method, path, None, body)
        assert response.status_code == 401 and code_of(response) == "missing_student", path


def test_g06_answers_can_be_saved_merged_and_revised():
    student = new_student()
    attempt = start(student)
    first = save(student, attempt, {"q1": "b"})
    assert first.status_code == 200 and first.json()["answers"] == {"q1": "b"}
    second = save(student, attempt, {"q1": "a", "q2": "c"})
    assert second.json()["answers"] == {"q1": "a", "q2": "c"}
    shown = call("GET", f"/api/attempts/{attempt}", student).json()
    assert shown["answers"] == {"q1": "a", "q2": "c"} and shown["status"] == "in_progress"


def test_g07_invalid_answers_rejected_and_nothing_saved():
    student = new_student()
    attempt = start(student)
    bad_question = save(student, attempt, {"q1": "a", "q9": "a"})
    assert bad_question.status_code == 422 and code_of(bad_question) == "unknown_question"
    bad_choice = save(student, attempt, {"q1": "a", "q2": "z"})
    assert bad_choice.status_code == 422 and code_of(bad_choice) == "invalid_choice"
    assert call("GET", f"/api/attempts/{attempt}", student).json()["answers"] == {}


def test_g08_incomplete_submission_rejected_with_missing_ids_and_answers_kept():
    student = new_student()
    attempt = start(student)
    save(student, attempt, {"q2": "b"})
    response = call("POST", f"/api/attempts/{attempt}/submit", student)
    assert response.status_code == 422 and code_of(response) == "incomplete"
    assert response.json()["detail"]["missing"] == ["q1", "q3"]
    assert not leaks(response)
    state = call("GET", f"/api/attempts/{attempt}", student).json()
    assert state["status"] == "in_progress" and state["answers"] == {"q2": "b"}
    assert call("GET", f"/api/attempts/{attempt}/results", student).status_code == 403


def test_g09_perfect_submission_scores_three_of_three():
    student = new_student()
    attempt = start(student)
    save(student, attempt, KEY)
    response = call("POST", f"/api/attempts/{attempt}/submit", student)
    assert response.status_code == 200
    assert response.json()["status"] == "submitted" and response.json()["score"] == {"correct": 3, "total": 3}


def test_g10_mixed_and_zero_scores_are_computed():
    student = new_student()
    mixed = start(student)
    save(student, mixed, {"q1": "a", "q2": "a", "q3": "a"})
    assert call("POST", f"/api/attempts/{mixed}/submit", student).json()["score"] == {"correct": 1, "total": 3}
    zero = start(student)
    save(student, zero, WRONG)
    assert call("POST", f"/api/attempts/{zero}/submit", student).json()["score"] == {"correct": 0, "total": 3}


def test_g11_client_cannot_supply_score():
    student = new_student()
    attempt = start(student)
    save(student, attempt, WRONG)
    response = call("POST", f"/api/attempts/{attempt}/submit", student, {"score": {"correct": 3, "total": 3}, "correct": 3})
    assert response.status_code == 200 and response.json()["score"] == {"correct": 0, "total": 3}


def test_g12_submitted_attempt_is_locked():
    student = new_student()
    attempt = start(student)
    save(student, attempt, KEY)
    call("POST", f"/api/attempts/{attempt}/submit", student)
    again = call("POST", f"/api/attempts/{attempt}/submit", student)
    assert again.status_code == 409 and code_of(again) == "already_submitted"
    edit = save(student, attempt, {"q1": "b"})
    assert edit.status_code == 409 and code_of(edit) == "already_submitted"
    assert call("GET", f"/api/attempts/{attempt}", student).json()["answers"] == KEY


def test_g13_results_after_submission_are_complete():
    student = new_student()
    attempt = start(student)
    answers = {"q1": "a", "q2": "c", "q3": "c"}
    save(student, attempt, answers)
    call("POST", f"/api/attempts/{attempt}/submit", student)
    response = call("GET", f"/api/attempts/{attempt}/results", student)
    assert response.status_code == 200
    data = response.json()
    assert data["key_version"] == "v1" and data["score"] == {"correct": 2, "total": 3}
    assert data["answers"] == answers and data["set_id"] == "intro-se-1"
    assert [q["id"] for q in data["questions"]] == ["q1", "q2", "q3"]
    for q in data["questions"]:
        assert q["selected"] == answers[q["id"]]
        assert q["correct_choice"] == KEY[q["id"]]
        assert q["correct"] is (q["selected"] == KEY[q["id"]])
        assert q["explanation"] == EXPLANATIONS[q["id"]]


def test_g14_results_before_submission_are_forbidden_and_clean():
    student = new_student()
    attempt = start(student)
    save(student, attempt, KEY)
    response = call("GET", f"/api/attempts/{attempt}/results", student)
    assert response.status_code == 403 and code_of(response) == "not_submitted"
    assert not leaks(response)


def test_g15_no_pre_submission_response_leaks_the_key():
    student = new_student()
    attempt = start(student)
    responses = [
        call("GET", SET),
        call("GET", f"/api/attempts/{attempt}", student),
        save(student, attempt, {"q1": "a"}),
        save(student, attempt, {"q9": "a"}),
        save(student, attempt, {"q1": "z"}),
        call("POST", f"/api/attempts/{attempt}/submit", student),
        call("GET", f"/api/attempts/{attempt}/results", student),
        call("GET", "/api/attempts/missing-id", student),
    ]
    for response in responses:
        assert not leaks(response), response.text
        assert '"correct"' not in response.text


def test_g16_other_students_cannot_touch_an_attempt():
    owner, other = new_student(), new_student()
    attempt = start(owner)
    save(owner, attempt, KEY)
    call("POST", f"/api/attempts/{attempt}/submit", owner)
    checks = [
        call("GET", f"/api/attempts/{attempt}", other),
        save(other, attempt, {"q1": "b"}),
        call("POST", f"/api/attempts/{attempt}/submit", other),
        call("GET", f"/api/attempts/{attempt}/results", other),
    ]
    for response in checks:
        assert response.status_code == 404 and code_of(response) == "attempt_not_found"
        assert not leaks(response)
    unknown = call("GET", "/api/attempts/does-not-exist", other)
    assert unknown.status_code == 404 and json.dumps(unknown.json()) == json.dumps(checks[0].json())


def test_g17_attempts_are_independent_and_ids_unique():
    student = new_student()
    first, second = start(student), start(student)
    assert first != second
    save(student, first, KEY)
    assert call("GET", f"/api/attempts/{second}", student).json()["answers"] == {}
    save(student, second, WRONG)
    call("POST", f"/api/attempts/{first}/submit", student)
    assert call("GET", f"/api/attempts/{second}", student).json()["status"] == "in_progress"
    assert call("GET", f"/api/attempts/{second}/results", student).status_code == 403


def test_g18_health_endpoints_still_work():
    assert call("GET", "/api/health").json() == {"status": "ok"}
    assert call("GET", "/api/health/ready").json() == {"status": "ready"}
