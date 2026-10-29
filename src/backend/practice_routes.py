"""HTTP routes for practice sets and attempts."""
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException

import practice_logic as logic
from attempt_store import Attempt, store
from practice_data import PracticeSet, get_set
from practice_schemas import (
    AnswersIn,
    AnswersSavedOut,
    AttemptOut,
    PracticeSetOut,
    ResultsOut,
    SubmitOut,
)

router = APIRouter(prefix="/api")


def fail(status: int, code: str, message: str, **extra: object) -> NoReturn:
    raise HTTPException(status, {"code": code, "message": message, **extra})


def student_id(x_student_id: Annotated[str | None, Header()] = None) -> str:
    """Placeholder identity until SHR-01."""
    student = (x_student_id or "").strip()
    if not student:
        fail(401, "missing_student", "Student identity is required.")
    return student


Student = Annotated[str, Depends(student_id)]


def require_set(set_id: str) -> PracticeSet:
    practice_set = get_set(set_id)
    if practice_set is None:
        fail(404, "set_not_found", "Practice set not found.")
    return practice_set


def require_attempt(attempt_id: str, student: str) -> Attempt:
    attempt = store.get_owned(attempt_id, student)
    if attempt is None:
        fail(404, "attempt_not_found", "Attempt not found.")
    return attempt


def require_open(attempt: Attempt) -> None:
    if attempt.status == "submitted":
        fail(409, "already_submitted", "Attempt has already been submitted.")


def attempt_out(attempt: Attempt) -> dict:
    return {
        "attempt_id": attempt.attempt_id,
        "set_id": attempt.set_id,
        "status": attempt.status,
        "answers": dict(attempt.answers),
    }


@router.get("/practice-sets/{set_id}", response_model=PracticeSetOut)
def read_set(set_id: str) -> PracticeSetOut:
    return PracticeSetOut.model_validate(require_set(set_id), from_attributes=True)


@router.post("/practice-sets/{set_id}/attempts", status_code=201, response_model=AttemptOut)
def start_attempt(set_id: str, student: Student) -> dict:
    require_set(set_id)
    return attempt_out(store.create(student, set_id))


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def read_attempt(attempt_id: str, student: Student) -> dict:
    return attempt_out(require_attempt(attempt_id, student))


@router.put("/attempts/{attempt_id}/answers", response_model=AnswersSavedOut)
def save_answers(attempt_id: str, body: AnswersIn, student: Student) -> dict:
    require_attempt(attempt_id, student)
    with store.lock(attempt_id):
        attempt = require_attempt(attempt_id, student)
        require_open(attempt)
        try:
            logic.validate_answers(require_set(attempt.set_id), body.answers)
        except logic.AnswerError as e:
            fail(422, e.code, e.message)
        attempt.answers.update(body.answers)
        store.save(attempt)
        return attempt_out(attempt)


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit(attempt_id: str, student: Student) -> dict:
    require_attempt(attempt_id, student)
    with store.lock(attempt_id):
        attempt = require_attempt(attempt_id, student)
        require_open(attempt)
        practice_set = require_set(attempt.set_id)
        missing = logic.missing_questions(practice_set, attempt.answers)
        if missing:
            fail(422, "incomplete", "Answer every question before submitting.", missing=missing)
        attempt.status = "submitted"
        store.save(attempt)
        score = logic.score(practice_set, attempt.answers)
    return {"attempt_id": attempt.attempt_id, "status": "submitted", "score": score}


@router.get("/attempts/{attempt_id}/results", response_model=ResultsOut)
def results(attempt_id: str, student: Student) -> dict:
    attempt = require_attempt(attempt_id, student)
    if attempt.status != "submitted":
        fail(403, "not_submitted", "Results are available after submission.")
    return {
        "attempt_id": attempt.attempt_id,
        "set_id": attempt.set_id,
        **logic.build_results(require_set(attempt.set_id), attempt.answers),
    }
