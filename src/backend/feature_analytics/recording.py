"""Recording hooks called by the companion, practice and TEA-02 routes.

Every hook is synchronous, uses its own short database session, never raises and never logs request or response text.
A failed hook returns None and leaves the host request untouched.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from auth.db import open_session
from feature_analytics import config
from feature_analytics.grading_text import GradingContent, prepare_for_storage
from feature_analytics.models import (
    AnalyticsChatRequest,
    AnalyticsGenerationAttempt,
    AnalyticsGradingItem,
    AnalyticsPracticeAttempt,
    AnalyticsSession,
)

log = logging.getLogger("feature_analytics")
ACTIVITY_TYPES = ("practice_attempt", "lesson")
GENERATION_WORKFLOWS = ("study_notes", "mcq_batch")
# TEA-02 error codes of a request the AI service's limiter refused: not a generation attempt (plan decision 8).
REFUSED_BY_LIMITER = ("llm_rate_limited", "llm_busy")


def _failed(hook: str, exc: Exception) -> None:
    log.warning("analytics hook %s failed, class=%s", hook, type(exc).__name__)


def _when(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _elapsed_ms(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() * 1000))


def _assign_session(db, user_id: str, activity_ref: str, received_at: datetime) -> int | None:
    """The open session of this user for this attempt, or a new one. Serialised per user by an advisory lock."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"analytics-session:{user_id}"})
    attempt = db.get(AnalyticsPracticeAttempt, activity_ref)
    if attempt is not None and attempt.submitted_at is not None and attempt.submitted_at <= received_at:
        return None  # a chat after submission is not part of the practice activity
    current = db.scalar(
        select(AnalyticsSession).where(AnalyticsSession.user_id == user_id, AnalyticsSession.ended_at.is_(None))
        .with_for_update()
    )
    if current is not None:
        same = current.activity_ref == activity_ref
        if same and received_at - current.last_message_at <= timedelta(minutes=config.SESSION_IDLE_MINUTES):
            current.last_message_at = max(current.last_message_at, received_at)
            return current.id
        current.ended_at = current.last_message_at
        current.end_reason = "inactivity" if same else "new_activity"
        db.flush()  # the one-open-session index needs the old row closed before the new row is inserted
    opened = AnalyticsSession(
        user_id=user_id, role="student", activity_type="practice_attempt", activity_ref=activity_ref,
        started_at=received_at, last_message_at=received_at,
    )
    db.add(opened)
    db.flush()
    return opened.id


def record_chat_request_received(*, user_id: str, activity_type: str | None = None,
                                 activity_ref: str | None = None,
                                 received_at: datetime | None = None) -> int | None:
    try:
        received = _when(received_at)
        kind = activity_type if activity_type in ACTIVITY_TYPES else None
        ref = str(activity_ref) if kind is not None and activity_ref is not None else None
        with open_session() as db:
            session_id = _assign_session(db, user_id, ref, received) if kind == "practice_attempt" and ref else None
            row = AnalyticsChatRequest(user_id=user_id, role="student", activity_type=kind, activity_ref=ref,
                                       session_id=session_id, received_at=received, outcome="pending")
            db.add(row)
            db.flush()
            request_id = row.id
            db.commit()
            return request_id
    except Exception as exc:  # noqa: BLE001 - a hook never breaks the host request
        _failed("record_chat_request_received", exc)
        return None


def _add_item(db, *, workflow: str, source_type: str, source_id: int, generation_workflow: str | None,
              received_at: datetime, duration_ms: int, content: GradingContent) -> None:
    stored = prepare_for_storage(content)
    db.add(AnalyticsGradingItem(
        workflow=workflow, source_type=source_type, source_id=source_id, generation_workflow=generation_workflow,
        received_at=received_at, duration_ms=duration_ms, request_text=stored.request_text,
        response_text=stored.response_text, context_text=stored.context_text, status="pending",
    ))


def _finish(row, success: bool, completed_at: datetime | None, started_field: str) -> None:
    done = _when(completed_at)
    row.completed_at = done
    row.duration_ms = _elapsed_ms(getattr(row, started_field), done)
    row.outcome = "success" if success else "failure"


def record_chat_request_outcome(request_id: int | None, *, success: bool, grading: GradingContent | None = None,
                                completed_at: datetime | None = None) -> None:
    if request_id is None:
        return
    try:
        with open_session() as db:
            row = db.get(AnalyticsChatRequest, request_id, with_for_update=True)
            if row is None or row.outcome != "pending":
                return  # only the first outcome counts
            _finish(row, success, completed_at, "received_at")
            wanted = success and grading is not None and row.activity_type == "practice_attempt"
            received_at, duration = row.received_at, row.duration_ms
            db.commit()
            if wanted:
                try:  # a failed grading item must not undo the recorded outcome
                    _add_item(db, workflow="student_exercise", source_type="chat_request", source_id=request_id,
                              generation_workflow=None, received_at=received_at, duration_ms=duration, content=grading)
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    _failed("record_chat_request_outcome.item", exc)
    except Exception as exc:  # noqa: BLE001
        _failed("record_chat_request_outcome", exc)


def record_practice_attempt_started(*, user_id: str, practice_set_id: str, attempt_ref: str,
                                    started_at: datetime | None = None) -> None:
    try:
        with open_session() as db:
            db.execute(pg_insert(AnalyticsPracticeAttempt).values(
                attempt_ref=str(attempt_ref), user_id=user_id, practice_set_id=str(practice_set_id),
                started_at=_when(started_at),
            ).on_conflict_do_nothing(index_elements=["attempt_ref"]))
            db.commit()
    except Exception as exc:  # noqa: BLE001
        _failed("record_practice_attempt_started", exc)


def record_practice_attempt_submitted(*, attempt_ref: str, submitted_at: datetime | None = None) -> None:
    try:
        done = _when(submitted_at)
        with open_session() as db:
            row = db.get(AnalyticsPracticeAttempt, str(attempt_ref), with_for_update=True)
            if row is None or row.submitted_at is not None:
                return
            row.submitted_at = done
            for opened in db.scalars(select(AnalyticsSession).where(
                    AnalyticsSession.user_id == row.user_id, AnalyticsSession.activity_ref == row.attempt_ref,
                    AnalyticsSession.ended_at.is_(None)).with_for_update()):
                opened.ended_at = done
                opened.end_reason = "activity_ended"
            db.commit()
    except Exception as exc:  # noqa: BLE001
        _failed("record_practice_attempt_submitted", exc)


def record_generation_accepted(*, workflow: str, user_id: str, accepted_at: datetime | None = None) -> int | None:
    try:
        if workflow not in GENERATION_WORKFLOWS:
            return None
        with open_session() as db:
            row = AnalyticsGenerationAttempt(workflow=workflow, user_id=user_id, accepted_at=_when(accepted_at),
                                             outcome="pending")
            db.add(row)
            db.flush()
            attempt_id = row.id
            db.commit()
            return attempt_id
    except Exception as exc:  # noqa: BLE001
        _failed("record_generation_accepted", exc)
        return None


def record_generation_outcome(attempt_id: int | None, *, success: bool, grading: GradingContent | None = None,
                              completed_at: datetime | None = None) -> None:
    if attempt_id is None:
        return
    try:
        with open_session() as db:
            row = db.get(AnalyticsGenerationAttempt, attempt_id, with_for_update=True)
            if row is None or row.outcome != "pending":
                return
            _finish(row, success, completed_at, "accepted_at")
            wanted = success and grading is not None
            accepted_at, duration, workflow = row.accepted_at, row.duration_ms, row.workflow
            db.commit()
            if wanted:
                try:
                    _add_item(db, workflow="teacher_lesson_planning", source_type="generation_attempt",
                              source_id=attempt_id, generation_workflow=workflow, received_at=accepted_at,
                              duration_ms=duration, content=grading)
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    db.rollback()
                    _failed("record_generation_outcome.item", exc)
    except Exception as exc:  # noqa: BLE001
        _failed("record_generation_outcome", exc)
