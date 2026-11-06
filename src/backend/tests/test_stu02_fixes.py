"""STU-02 fixes after the workflow comparison: save/submit race and student identity.

SHR-01: sessions replace X-Student-Id. The old padded-header trimming test is replaced by an
equivalent identity test (the header is ignored); the race test is unchanged.
"""
import threading
import time

import practice_logic
from auth_helpers import call, new_student  # session login replaces X-Student-Id (SHR-01)
from fake_sets import FIXTURE_SET_ID  # noqa: F401
import pytest as _pytest

pytestmark = _pytest.mark.usefixtures("fake_provider")

SET_ID = FIXTURE_SET_ID
CORRECT = {"q1": "a", "q2": "b", "q3": "c"}


def start(student):
    response = call("POST", f"/api/practice-sets/{SET_ID}/attempts", student)
    assert response.status_code == 201
    return response.json()["attempt_id"]


def test_stu02_save_racing_submit_cannot_change_a_submitted_attempt(monkeypatch):
    """A save that passed its 'still in progress' check must not land after a submit (AC6)."""
    student = new_student()
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


def test_stu02_x_student_id_header_never_changes_the_session_student():
    """Replaces the placeholder-era trimming test: the session user is the only identity."""
    me = new_student()
    other = new_student()
    attempt = start(me)
    # A header naming another student (padded or plain) neither switches user nor grants access.
    spoof = {"X-Student-Id": f"  {other} "}
    assert call("GET", f"/api/attempts/{attempt}", other, headers=spoof).status_code == 404
    response = call("GET", f"/api/attempts/{attempt}", me, headers={"X-Student-Id": str(other)})
    assert response.status_code == 200
    call("PUT", f"/api/attempts/{attempt}/answers", me, {"answers": CORRECT}, headers=spoof)
    assert call("POST", f"/api/attempts/{attempt}/submit", me, headers=spoof).json()["score"]["correct"] == 3
