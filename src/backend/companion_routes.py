"""HTTP route for the study companion: resolves context, calls the model, checks the reply."""
import logging
import time

from fastapi import APIRouter, Depends

import companion_config as config
import companion_service as service
import leak_check
import practice_data
from attempt_store import Attempt, store
from companion_schemas import CompanionMessageIn, CompanionReplyOut, ContextIn
from errors import ApiError
from llm_client import (
    LlmBadResponse,
    LlmBusy,
    LlmClient,
    LlmError,
    LlmInputTooLarge,
    LlmNotConfigured,
    LlmRateLimited,
    get_llm_client,
)
from practice_data import PracticeSet, Question
from practice_routes import require_student
from question_match import find_match

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


def _resolve_context(ctx: ContextIn, student: str) -> tuple[PracticeSet | None, Attempt | None]:
    """Lookups (404), then consistency (422). Page "other" ignores set and attempt ids."""
    practice_set: PracticeSet | None = None
    attempt: Attempt | None = None
    if ctx.page == "practice":
        if ctx.attempt_id is not None:
            attempt = store.get_owned(ctx.attempt_id, student)
            if attempt is None:
                raise ApiError(404, "attempt_not_found", "Attempt not found.")
            if ctx.set_id is not None and ctx.set_id != attempt.set_id:
                raise ApiError(422, "invalid_context", "The page context is not consistent.")
            set_id = attempt.set_id
        else:
            if ctx.set_id is None:
                raise ApiError(422, "invalid_context", "The page context is not consistent.")
            set_id = ctx.set_id
        practice_set = practice_data.get_set(set_id)
        if practice_set is None:
            raise ApiError(404, "set_not_found", "Practice set not found.")
    if ctx.label is not None and len(ctx.label) > config.LABEL_MAX_CHARS:
        raise ApiError(422, "invalid_context", "The page label is too long.")
    return practice_set, attempt


def _leak_scope(plan: service.Plan) -> tuple[Question, ...]:
    """Hint: the questions in context. Help: every question of every set. Explain: no check."""
    if plan.mode == "hint":
        return plan.questions
    if plan.mode == "help":
        return tuple(q for s in practice_data.PRACTICE_SETS.values() for q in s.questions)
    return ()


def _log(
    mode: str, outcome: str, started: float, prompt: int | None = None, completion: int | None = None
) -> None:
    """Metadata only: never the message, history, reply or key."""
    log.info(
        "companion mode=%s outcome=%s latency_ms=%d prompt_tokens=%s completion_tokens=%s",
        mode,
        outcome,
        (time.monotonic() - started) * 1000,
        prompt,
        completion,
    )


@router.post("/companion/messages", response_model=CompanionReplyOut)
def post_message(
    body: CompanionMessageIn,
    student: str = Depends(require_student),
    llm: LlmClient = Depends(get_llm_client),
) -> CompanionReplyOut:
    practice_set, attempt = _resolve_context(body.context, student)
    message = service.validate_message(body.message)
    history = service.validate_history(body.history)
    match = find_match(message, list(practice_data.PRACTICE_SETS.values()))
    attempts = store.list_for_student(student, practice_set.id) if attempt and practice_set else []
    plan = service.select_mode(practice_set, attempt, attempts, match)
    messages = service.build_messages(plan, message, history, body.context.label)

    started = time.monotonic()
    try:
        reply = llm.complete(messages, max_tokens=config.MAX_TOKENS[plan.mode], caller_id=student)
    except LlmError as exc:
        error = _map_error(exc)
        _log(plan.mode, error.code, started)
        raise error from None
    leak = leak_check.find_leak(reply.text, _leak_scope(plan))
    outcome = "withheld" if leak else "ok"
    _log(plan.mode, outcome, started, reply.prompt_tokens, reply.completion_tokens)
    if leak:
        return CompanionReplyOut(reply=config.CANNED_REPLY, mode=plan.mode, withheld=True)
    return CompanionReplyOut(reply=reply.text, mode=plan.mode, withheld=False)
