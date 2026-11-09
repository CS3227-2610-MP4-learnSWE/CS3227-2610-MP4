"""HTTP routes for practice sets and attempts."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

import practice_logic as logic
from attempt_store import Attempt, store
from errors import ApiError
from feature_analytics import record_practice_attempt_started, record_practice_attempt_submitted
from practice_data import KEY_VERSION, PracticeSet
from practice_schemas import (
    AnswersIn,
    AnswersSaved,
    AttemptOut,
    BestScoreOut,
    CatalogCourseOut,
    CatalogSetOut,
    PracticeCatalogOut,
    PracticeSetOut,
    ResultsOut,
    SubmitOut,
    TopicRefOut,
    public_set,
)
from set_provider import CATALOG_SETS_PER_COURSE, SetProvider, get_set_provider
from student_identity import require_student
from teacher_access import parse_uuid
from timestamps import utc_timestamp

router = APIRouter(prefix="/api")


def error_response(_: Request, exc: ApiError) -> JSONResponse:
    detail = {"code": exc.code, "message": exc.message, **exc.extra}
    retry_after = exc.extra.get("retry_after_seconds")
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(status_code=exc.status, content={"detail": detail}, headers=headers)


def _set_or_404(provider: SetProvider, set_id: str, student: str) -> PracticeSet:
    practice_set = provider.get_for_student(set_id, student)
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


@router.get("/practice-sets", response_model=PracticeCatalogOut)
def list_sets(
    student: str = Depends(require_student), provider: SetProvider = Depends(get_set_provider)
) -> PracticeCatalogOut:
    catalog = provider.catalog_for_student(student, per_course_limit=CATALOG_SETS_PER_COURSE)
    best = {s.set_id: BestScoreOut(correct=s.best_correct, total=s.best_total) for s in store.submitted_summaries(student)}
    return PracticeCatalogOut(
        courses=[
            CatalogCourseOut(
                id=course.id,
                title=course.title,
                sets=[
                    CatalogSetOut(
                        id=s.id,
                        title=s.title,
                        topic=TopicRefOut(id=s.topic_id, name=s.topic_name),
                        published_at=utc_timestamp(s.published_at),
                        question_count=s.question_count,
                        best=best.get(s.id),
                    )
                    for s in course.sets
                ],
            )
            for course in catalog
        ]
    )


@router.get("/practice-sets/{set_id}", response_model=PracticeSetOut)
def read_set(
    set_id: str, student: str = Depends(require_student), provider: SetProvider = Depends(get_set_provider)
) -> PracticeSetOut:
    return public_set(_set_or_404(provider, str(parse_uuid(set_id)), student))


@router.post("/practice-sets/{set_id}/attempts", status_code=201, response_model=AttemptOut)
def start_attempt(
    set_id: str, student: str = Depends(require_student), provider: SetProvider = Depends(get_set_provider)
) -> AttemptOut:
    key = str(parse_uuid(set_id))
    _set_or_404(provider, key, student)
    attempt = store.create(student, key)
    record_practice_attempt_started(user_id=student, practice_set_id=key, attempt_ref=str(attempt.id))
    return _attempt_out(attempt)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def read_attempt(
    attempt: Attempt = Depends(owned_attempt),
    student: str = Depends(require_student),
    provider: SetProvider = Depends(get_set_provider),
) -> AttemptOut:
    _set_or_404(provider, attempt.set_id, student)
    return _attempt_out(attempt)


@router.put("/attempts/{attempt_id}/answers", response_model=AnswersSaved)
def save_answers(
    body: AnswersIn,
    attempt: Attempt = Depends(owned_attempt),
    student: str = Depends(require_student),
    provider: SetProvider = Depends(get_set_provider),
) -> AnswersSaved:
    practice_set = _set_or_404(provider, attempt.set_id, student)
    with store.lock(attempt.id) as locked:
        _require_open(locked)
        logic.validate_answers(practice_set, body.answers)
        locked.answers.update(body.answers)
        return AnswersSaved(attempt_id=locked.id, status=locked.status, answers=dict(locked.answers))


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitOut)
def submit(
    attempt: Attempt = Depends(owned_attempt),
    student: str = Depends(require_student),
    provider: SetProvider = Depends(get_set_provider),
) -> SubmitOut:
    practice_set = _set_or_404(provider, attempt.set_id, student)
    with store.lock(attempt.id) as locked:
        _require_open(locked)
        missing = logic.missing_questions(practice_set, locked.answers)
        if missing:
            raise ApiError(
                422, "incomplete", "All questions must be answered before submitting.", missing=missing
            )
        result = logic.score(practice_set, locked.answers)
        locked.status = "submitted"
        locked.score_correct = result.correct
        locked.score_total = result.total
        locked.key_version = KEY_VERSION
        locked.correct_question_ids = logic.correct_question_ids(practice_set, locked.answers)
        response = SubmitOut(attempt_id=locked.id, status=locked.status, score=result)
    # ADM-01: after the store's commit; `locked.submitted_at` is filled in by the store when the block exits cleanly.
    record_practice_attempt_submitted(attempt_ref=str(locked.id), submitted_at=locked.submitted_at)
    return response


@router.get("/attempts/{attempt_id}/results", response_model=ResultsOut)
def results(
    attempt: Attempt = Depends(owned_attempt),
    student: str = Depends(require_student),
    provider: SetProvider = Depends(get_set_provider),
) -> ResultsOut:
    practice_set = _set_or_404(provider, attempt.set_id, student)
    if attempt.status != "submitted":
        raise ApiError(403, "not_submitted", "Results are available after submission.")
    return logic.build_results(attempt.id, attempt.set_id, practice_set, dict(attempt.answers))
