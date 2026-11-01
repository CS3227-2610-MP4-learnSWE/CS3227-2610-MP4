"""HTTP routes for practice sets and attempts."""
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

import practice_logic as logic
from attempt_store import Attempt, store
from errors import ApiError
from practice_data import PracticeSet, get_set
from practice_schemas import (
    AnswersIn,
    AnswersSaved,
    AttemptOut,
    PracticeSetOut,
    ResultsOut,
    SubmitOut,
)

router = APIRouter(prefix="/api")


def error_response(_: Request, exc: ApiError) -> JSONResponse:
    detail = {"code": exc.code, "message": exc.message, **exc.extra}
    retry_after = exc.extra.get("retry_after_seconds")
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(status_code=exc.status, content={"detail": detail}, headers=headers)


def require_student(x_student_id: str | None = Header(default=None)) -> str:
    student = (x_student_id or "").strip()
    if not student:
        raise ApiError(401, "missing_student", "X-Student-Id header is required.")
    return student


def _set_or_404(set_id: str) -> PracticeSet:
    practice_set = get_set(set_id)
    if practice_set is None:
        raise ApiError(404, "set_not_found", "Practice set not found.")
    return practice_set


def owned_attempt(attempt_id: str, student: str = Depends(require_student)) -> Attempt:
    attempt = store.get_owned(attempt_id, student)
    if attempt is None:
        raise ApiError(404, "attempt_not_found", "Attempt not found.")
    return attempt


def _require_open(attempt: Attempt) -> None:
    if attempt.status == "submitted":
        raise ApiError(409, "already_submitted", "Attempt is already submitted.")


def _attempt_out(a: Attempt) -> AttemptOut:
    return AttemptOut(attempt_id=a.id, set_id=a.set_id, status=a.status, answers=dict(a.answers))


@router.get("/practice-sets/{set_id}", response_model=PracticeSetOut)
def read_set(set_id: str) -> PracticeSetOut:
    s = _set_or_404(set_id)
    return PracticeSetOut.model_validate(
        {
            "id": s.id,
            "title": s.title,
            "questions": [
                {
                    "id": q.id,
                    "text": q.text,
                    "code": q.code,
                    "choices": [{"id": c, "text": t} for c, t in q.choices],
                }
                for q in s.questions
            ],
        }
    )


@router.post("/practice-sets/{set_id}/attempts", status_code=201, response_model=AttemptOut)
def start_attempt(set_id: str, student: str = Depends(require_student)) -> AttemptOut:
    _set_or_404(set_id)
    return _attempt_out(store.create(student, set_id))


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def read_attempt(attempt: Attempt = Depends(owned_attempt)) -> AttemptOut:
    return _attempt_out(attempt)


@router.put("/attempts/{attempt_id}/answers", response_model=AnswersSaved)
def save_answers(body: AnswersIn, attempt: Attempt = Depends(owned_attempt)) -> AnswersSaved:
    with store.lock(attempt.id):
        _require_open(attempt)
        logic.validate_answers(_set_or_404(attempt.set_id), body.answers)
        attempt.answers.update(body.answers)
        return AnswersSaved(attempt_id=attempt.id, status=attempt.status, answers=dict(attempt.answers))


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit(attempt: Attempt = Depends(owned_attempt)) -> SubmitOut:
    with store.lock(attempt.id):
        _require_open(attempt)
        practice_set = _set_or_404(attempt.set_id)
        missing = logic.missing_questions(practice_set, attempt.answers)
        if missing:
            raise ApiError(
                422, "incomplete", "All questions must be answered before submitting.", missing=missing
            )
        attempt.status = "submitted"
    return SubmitOut(
        attempt_id=attempt.id,
        status=attempt.status,
        score=logic.score(practice_set, attempt.answers),
    )


@router.get("/attempts/{attempt_id}/results", response_model=ResultsOut)
def results(attempt: Attempt = Depends(owned_attempt)) -> ResultsOut:
    if attempt.status != "submitted":
        raise ApiError(403, "not_submitted", "Results are available after submission.")
    return logic.build_results(
        attempt.id, attempt.set_id, _set_or_404(attempt.set_id), dict(attempt.answers)
    )
