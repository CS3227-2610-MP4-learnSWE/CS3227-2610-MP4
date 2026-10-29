"""STU-02 fixes after the workflow comparison: save/submit race and student id trimming."""
import asyncio
import threading
import time
import uuid

import httpx
import practice_logic
from main import app

SET_ID = "intro-se-1"
CORRECT = {"q1": "a", "q2": "b", "q3": "c"}


def call(method, path, student=None, body=None):
    headers = {"X-Student-Id": student} if student is not None else {}

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            return await client.request(method, path, headers=headers, json=body)

    return asyncio.run(send())


def sid():
    return "student-" + uuid.uuid4().hex


def start(student):
    response = call("POST", f"/api/practice-sets/{SET_ID}/attempts", student)
    assert response.status_code == 201
    return response.json()["attempt_id"]


def test_stu02_save_racing_submit_cannot_change_a_submitted_attempt(monkeypatch):
    """A save that passed its 'still in progress' check must not land after a submit (AC6)."""
    student = sid()
    attempt = start(student)
    call("PUT", f"/api/attempts/{attempt}/answers", student, {"answers": {"q1": "b", "q2": "b", "q3": "c"}})

    real_validate = practice_logic.validate_answers

    def slow_validate(*args, **kwargs):
        time.sleep(0.3)  # widen the gap between the state check and the write
        return real_validate(*args, **kwargs)

    monkeypatch.setattr(practice_logic, "validate_answers", slow_validate)
    results = {}
    save = threading.Thread(
        target=lambda: results.__setitem__(
            "save", call("PUT", f"/api/attempts/{attempt}/answers", student, {"answers": {"q1": "a"}})
        )
    )
    submit = threading.Thread(
        target=lambda: results.__setitem__("submit", call("POST", f"/api/attempts/{attempt}/submit", student))
    )
    save.start()
    time.sleep(0.1)  # the save is now between its check and its write
    submit.start()
    save.join()
    submit.join()

    assert results["save"].status_code in (200, 409), results["save"].text
    submitted_score = results["submit"].json()["score"]
    final = call("GET", f"/api/attempts/{attempt}/results", student).json()
    assert final["score"] == submitted_score
    if results["save"].status_code == 200:
        assert submitted_score == {"correct": 3, "total": 3}


def test_stu02_padded_and_plain_student_id_are_the_same_student():
    name = sid()
    attempt = start(f"  {name} ")
    response = call("GET", f"/api/attempts/{attempt}", name)
    assert response.status_code == 200
    call("PUT", f"/api/attempts/{attempt}/answers", name, {"answers": CORRECT})
    assert call("POST", f"/api/attempts/{attempt}/submit", f"{name}  ").json()["score"]["correct"] == 3
