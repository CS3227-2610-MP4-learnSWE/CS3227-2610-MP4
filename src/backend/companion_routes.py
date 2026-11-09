"""HTTP route for the study companion: resolves context, calls the model, checks the reply."""
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from auth.db import engine_for, get_session
from auth.dependencies import AuthUser, current_user, session_context, unauthenticated
from auth.settings import load_settings

import companion_config as config
import companion_service as service
import leak_check
from attempt_store import Attempt, store
from companion_schemas import CompanionMessageIn, CompanionReplyOut, ContextIn, SourceOut
from errors import ApiError
from lesson_provider import LessonProvider, LessonText, get_lesson_provider
from llm_client import (
    LlmBadResponse,
    LlmBusy,
    LlmClient,
    LlmError,
    LlmInputTooLarge,
    LlmNotConfigured,
    LlmRateLimited,
    get_llm_client,
    usage_feature,
)
from practice_data import PracticeSet, Question
from question_match import find_match
from set_provider import SetProvider, get_set_provider
from student_identity import require_student, student_user
from teacher_access import parse_uuid

router = APIRouter(prefix="/api")
log = logging.getLogger("companion")


def _map_error(exc: LlmError) -> ApiError:
    """Fixed messages only: nothing from the provider, the student or the key."""
    if isinstance(exc, LlmNotConfigured):
        return ApiError(503, "llm_not_configured", "The study companion is not set up yet.")
    if isinstance(exc, LlmInputTooLarge):
        return ApiError(500, "companion_internal", "The study companion hit an internal error.")
    if isinstance(exc, LlmRateLimited):
        return ApiError(
            429,
            "rate_limited",
            "You have sent too many messages. Please wait a little.",
            scope=exc.scope,
            retry_after_seconds=exc.retry_after_seconds,
        )
    if isinstance(exc, LlmBusy):
        return ApiError(
            429,
            "llm_busy",
            "The study companion is busy. Please try again shortly.",
            retry_after_seconds=exc.retry_after_seconds,
        )
    if isinstance(exc, LlmBadResponse):
        return ApiError(502, "llm_bad_response", "The study companion could not answer.")
    return ApiError(503, "llm_unavailable", "The study companion is unavailable right now.")


def _canonical_set_id(value: str) -> str:
    """Lowercase hyphenated form of a UUID spelling; any other text is returned unchanged."""
    try:
        return str(UUID(value))
    except ValueError:
        return value


def _resolve_context(
    ctx: ContextIn, user: AuthUser, provider: SetProvider, lessons: LessonProvider
) -> tuple[PracticeSet | None, Attempt | None, LessonText | None]:
    """Lookups (404), then consistency (422). Page "other" ignores set, attempt and lesson ids;
    page "lesson" ignores set and attempt ids."""
    student = user.id
    practice_set: PracticeSet | None = None
    attempt: Attempt | None = None
    lesson: LessonText | None = None
    if ctx.page == "lesson":
        if ctx.lesson_id is None:
            raise ApiError(422, "invalid_context", "The page context is not consistent.")
        lesson = lessons.get_visible(ctx.lesson_id, user)
        if lesson is None:
            raise ApiError(404, "lesson_not_found", "Lesson not found.")
    if ctx.page == "practice":
        if ctx.attempt_id is not None:
            attempt = store.get_owned(ctx.attempt_id, student)
            if attempt is None:
                raise ApiError(404, "attempt_not_found", "Attempt not found.")
            if ctx.set_id is not None and _canonical_set_id(ctx.set_id) != attempt.set_id:
                raise ApiError(422, "invalid_context", "The page context is not consistent.")
            set_id = attempt.set_id
        else:
            if ctx.set_id is None:
                raise ApiError(422, "invalid_context", "The page context is not consistent.")
            set_id = str(parse_uuid(ctx.set_id))
        practice_set = provider.get_for_student(set_id, student)
        if practice_set is None:
            raise ApiError(404, "set_not_found", "Practice set not found.")
    if ctx.label is not None and len(ctx.label) > config.LABEL_MAX_CHARS:
        raise ApiError(422, "invalid_context", "The page label is too long.")
    return practice_set, attempt, lesson


def _leak_scope(plan: service.Plan, accessible: list[PracticeSet]) -> tuple[Question, ...]:
    """Hint: the questions in context. Help: every question the student can access. Explain: no check."""
    if plan.mode == "hint":
        return plan.questions + plan.leak_extra
    if plan.mode in ("help", "lesson"):
        return tuple(q for s in accessible for q in s.questions)
    return ()


def _log(
    mode: str,
    outcome: str,
    started: float,
    prompt: int | None = None,
    completion: int | None = None,
    lessons: int = 0,
) -> None:
    """Metadata only: never the message, history, reply, lesson text, title or key."""
    log.info(
        "companion mode=%s outcome=%s latency_ms=%d prompt_tokens=%s completion_tokens=%s lessons=%d",
        mode,
        outcome,
        (time.monotonic() - started) * 1000,
        prompt,
        completion,
        lessons,
    )


@router.post("/companion/messages", response_model=CompanionReplyOut)
def post_message(
    body: CompanionMessageIn,
    request: Request,
    student: str = Depends(require_student),
    user: AuthUser = Depends(student_user),
    llm: LlmClient = Depends(get_llm_client),
    provider: SetProvider = Depends(get_set_provider),
    lessons: LessonProvider = Depends(get_lesson_provider),
    db: Session = Depends(get_session),
) -> CompanionReplyOut:
    # Identity/CSRF checks are complete. Return their read-only connection before
    # independent store reads and the model call, or concurrent requests can each
    # hold one pool slot while waiting for a second. Recheck access after the call.
    db.rollback()
    practice_set, attempt, viewed = _resolve_context(body.context, user, provider, lessons)
    message = service.validate_message(body.message)
    history = service.validate_history(body.history)
    accessible = provider.accessible_sets(student)
    match = find_match(message, accessible)
    attempts = store.list_for_student(student, practice_set.id) if attempt and practice_set else []
    related: list[LessonText] = []
    if body.context.page == "other" and match is None:
        related = lessons.find_related(message, user)
    in_context = [viewed] if viewed is not None else related
    plan = service.select_mode(practice_set, attempt, attempts, match, in_context)
    messages = service.build_messages(plan, message, history, body.context.label)

    started = time.monotonic()
    try:
        with usage_feature("STU-03"):
            reply = llm.complete(messages, max_tokens=config.MAX_TOKENS[plan.mode], caller_id=student)
    except LlmError as exc:
        error = _map_error(exc)
        _log(plan.mode, error.code, started, lessons=len(plan.lessons))
        raise error from None
    # A model call may outlive logout/disable/archive. Use a new transaction
    # rather than the dependency's earlier ORM snapshot before releasing text.
    with Session(engine_for(load_settings().database_url)) as access_db:
        fresh = current_user(role="student")(session_context(request, access_db))
        if fresh.id != student:
            raise unauthenticated()
    if any(lessons.get_visible(l.id, user) is None for l in plan.lessons):
        _log(plan.mode, "lesson_not_found", started, lessons=len(plan.lessons))
        raise ApiError(404, "lesson_not_found", "Lesson not found.")
    # The leak scope covers only the sets this student can access (set_provider).
    # Lesson text is student-visible and may equal a choice text, so Lesson mode skips the text check.
    shown, grounded = reply.text, []
    if plan.mode == "lesson":
        # Marker handling first: the leak check must see exactly the text that would be shown.
        shown, grounded = service.finish_lesson_reply(reply.text, plan.lessons)
    leak = leak_check.find_leak(shown, _leak_scope(plan, accessible), check_text=plan.mode != "lesson")
    outcome = "withheld" if leak else "ok"
    _log(plan.mode, outcome, started, reply.prompt_tokens, reply.completion_tokens, len(plan.lessons))
    if plan.mode == "lesson":
        if leak:
            return CompanionReplyOut(
                reply=config.LESSON_CANNED_REPLY, mode="lesson", withheld=True, sources=[]
            )
        return CompanionReplyOut(
            reply=shown,
            mode="lesson",
            withheld=False,
            sources=[SourceOut(lesson_id=l.id, title=l.title) for l in grounded],
        )
    if leak:
        return CompanionReplyOut(reply=config.CANNED_REPLY, mode=plan.mode, withheld=True)
    return CompanionReplyOut(reply=reply.text, mode=plan.mode, withheld=False)
