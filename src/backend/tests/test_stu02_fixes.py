"""STU-02 fixes after the workflow comparison: save/submit race and student id trimming."""
import threading
import time

import practice_logic
from test_stu02_attempts import CORRECT, SET_ID, call, sid


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

    def slow_validate(practice_set, answers):
        time.sleep(0.3)  # widen the gap between the state check and the write
        return real_validate(practice_set, answers)

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

    submitted_score = results["submit"].json()["score"]
    final = call("GET", f"/api/attempts/{attempt}/results", student).json()
    assert final["score"] == submitted_score
    if results["save"].status_code == 200:
        assert submitted_score == {"correct": 3, "total": 3}
    else:
        assert results["save"].status_code == 409


def test_stu02_padded_and_plain_student_id_are_the_same_student():
    name = sid()
    attempt = start(f"  {name} ")
    response = call("GET", f"/api/attempts/{attempt}", name)
    assert response.status_code == 200
    call("PUT", f"/api/attempts/{attempt}/answers", name, {"answers": CORRECT})
    assert call("POST", f"/api/attempts/{attempt}/submit", f"{name}  ").json()["score"]["correct"] == 3
