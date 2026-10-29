"""HTTP routes for practice sets and attempts."""
from fastapi import APIRouter, Depends, Header, HTTPException

import practice_logic
from attempt_store import Attempt, store
from practice_data import KEY_VERSION, PracticeSet, get_set
from practice_schemas import (
    AnswersIn,
    AnswersSavedOut,
    AttemptOut,
    PracticeSetOut,
    ResultsOut,
    SubmitOut,
)

router = APIRouter(prefix="/api")


def _error(status: int, code: str, message: str, **extra: object) -> HTTPException:
    return HTTPException(status, {"code": code, "message": message, **extra})


def current_student(x_student_id: str | None = Header(default=None)) -> str:
    student = (x_student_id or "").strip()
    if not student:
        raise _error(401, "missing_student", "X-Student-Id header is required.")
    return student


def _set_or_404(set_id: str) -> PracticeSet:
    practice_set = get_set(set_id)
    if practice_set is None:
        raise _error(404, "set_not_found", "Practice set not found.")
    return practice_set


def _owned_attempt(attempt_id: str, student: str) -> Attempt:
    attempt = store.get_owned(attempt_id, student)
    if attempt is None:
        raise _error(404, "attempt_not_found", "Attempt not found.")
    return attempt


def _require_in_progress(attempt: Attempt) -> None:
    if attempt.status == "submitted":
        raise _error(409, "already_submitted", "Attempt has already been submitted.")


def _attempt_out(attempt: Attempt) -> AttemptOut:
    return AttemptOut(
        attempt_id=attempt.id,
        set_id=attempt.set_id,
        status=attempt.status,
        answers=dict(attempt.answers),
    )


@router.get("/practice-sets/{set_id}", response_model=PracticeSetOut)
def read_set(set_id: str) -> dict:
    practice_set = _set_or_404(set_id)
    return {
        "id": practice_set.id,
        "title": practice_set.title,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "code": q.code,
                "choices": [{"id": cid, "text": text} for cid, text in q.choices],
            }
            for q in practice_set.questions
        ],
    }


@router.post("/practice-sets/{set_id}/attempts", status_code=201, response_model=AttemptOut)
def start_attempt(set_id: str, student: str = Depends(current_student)) -> AttemptOut:
    practice_set = _set_or_404(set_id)
    return _attempt_out(store.create(student, practice_set.id))


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def read_attempt(attempt_id: str, student: str = Depends(current_student)) -> AttemptOut:
    return _attempt_out(_owned_attempt(attempt_id, student))


@router.put("/attempts/{attempt_id}/answers", response_model=AnswersSavedOut)
def save_answers(
    attempt_id: str, body: AnswersIn, student: str = Depends(current_student)
) -> AnswersSavedOut:
    _owned_attempt(attempt_id, student)
    with store.lock(attempt_id):
        attempt = _owned_attempt(attempt_id, student)
        _require_in_progress(attempt)
        problem = practice_logic.validate_answers(_set_or_404(attempt.set_id), body.answers)
        if problem:
            raise _error(422, problem[0], problem[1])
        attempt.answers.update(body.answers)
        store.save(attempt)
    return AnswersSavedOut(
        attempt_id=attempt.id, status=attempt.status, answers=dict(attempt.answers)
    )


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit_attempt(attempt_id: str, student: str = Depends(current_student)) -> dict:
    _owned_attempt(attempt_id, student)
    with store.lock(attempt_id):
        attempt = _owned_attempt(attempt_id, student)
        _require_in_progress(attempt)
        practice_set = _set_or_404(attempt.set_id)
        missing = practice_logic.missing_questions(practice_set, attempt.answers)
        if missing:
            raise _error(
                422,
                "incomplete",
                "All questions must be answered before submitting.",
                missing=missing,
            )
        attempt.status = "submitted"
        store.save(attempt)
        score = practice_logic.score(practice_set, attempt.answers)
    return {"attempt_id": attempt.id, "status": attempt.status, "score": score}


@router.get("/attempts/{attempt_id}/results", response_model=ResultsOut)
def read_results(attempt_id: str, student: str = Depends(current_student)) -> dict:
    attempt = _owned_attempt(attempt_id, student)
    if attempt.status != "submitted":
        raise _error(403, "not_submitted", "Results are available after submission.")
    practice_set = _set_or_404(attempt.set_id)
    return {
        "attempt_id": attempt.id,
        "set_id": attempt.set_id,
        "key_version": KEY_VERSION,
        "score": practice_logic.score(practice_set, attempt.answers),
        "answers": dict(attempt.answers),
        "questions": [
            {
                "id": q.id,
                "selected": attempt.answers[q.id],
                "correct_choice": q.correct,
                "correct": attempt.answers[q.id] == q.correct,
                "explanation": q.explanation,
            }
            for q in practice_set.questions
        ],
    }
