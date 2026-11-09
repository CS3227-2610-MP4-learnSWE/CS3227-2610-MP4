"""Read side of ADM-01: each function returns one metric object as in plan.md. No stored text is ever selected for output."""
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, or_

from feature_analytics import config, privacy
from feature_analytics.models import (
    AnalyticsChatRequest as Chat,
    AnalyticsGenerationAttempt as Generation,
    AnalyticsGrade as Grade,
    AnalyticsGradingItem as Item,
    AnalyticsGradingRun as Run,
    AnalyticsMeta,
    AnalyticsPracticeAttempt as Attempt,
    AnalyticsSession as Session,
)
from feature_analytics.periods import Window
from teacher_materials.models import User
from timestamps import utc_timestamp

BEFORE_RECORDING = "period_before_recording"
GENERATION_LABELS = {"study_notes": "Study notes", "mcq_batch": "MCQ batches"}
ACTIVE_STATUSES = ("queued", "running")
GRADABLE_STATUSES = ("pending", "grading_failed")


def metric(state: str, reason: str | None, **fields) -> dict:
    return {"state": state, "reason": reason, **fields}


def iso(value: datetime | None) -> str | None:
    return None if value is None else utc_timestamp(value)


def _half_up(value) -> int:
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _in_window(column, window: Window) -> list:
    return [column >= window.start_utc, column < window.end_utc_exclusive]


def recording_started_on(db) -> date:
    """The UTC date of the first recording (analytics_meta); a missing row counts as 'always recorded'."""
    value = db.scalar(select(AnalyticsMeta.value).where(AnalyticsMeta.key == "recording_started_at"))
    if value is None:
        return date.min
    parsed = datetime.fromisoformat(value)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()


def _before_recording(db, window: Window) -> bool:
    return window.period_start < recording_started_on(db)


# ---- unavailable shapes (also used by the routes for read_failed) ----

def chatbot_unavailable(reason: str) -> dict:
    group = metric("unavailable", reason, successful=None, unsuccessful=None, rows=[], rows_truncated=False)
    total = metric("unavailable", reason, successful=None, unsuccessful=None)
    return {"student": dict(group), "teacher": dict(group), "total": total}


def practice_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, started=None, submitted=None, percentage=None)


def generation_unavailable(reason: str) -> list[dict]:
    return [metric("unavailable", reason, workflow=w, label=label, attempts=None, successful=None,
                   unsuccessful=None, rate_percent=None) for w, label in GENERATION_LABELS.items()]


def grades_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, assessed_count=None, pending_count=None, grading_failed_count=None,
                  content_expired_count=None, privacy_blocked_count=None, privacy_mode=privacy.privacy_mode(), dimensions=[])


def response_time_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, successful_count=None, mean_ms=None, median_ms=None,
                  failed_or_incomplete_count=None)


def sessions_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, session_count=None, average_messages_per_session=None,
                  user_messages=None, ai_messages=None)


def activity_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, linked_session_count=None, distinct_activity_count=None,
                  excluded_session_count=None, average_messages_per_session=None, average_activity_seconds=None,
                  start_event=None, end_event=None)


def items_empty(limit: int, offset: int) -> dict:
    return {"total": 0, "limit": limit, "offset": offset, "rows": []}


# ---- usage ----

def _display_names(db, user_ids: list[str]) -> dict[str, str | None]:
    if not user_ids:
        return {}
    try:
        return dict(db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids))).all())
    except Exception:  # noqa: BLE001 - names are optional; the counts stand
        db.rollback()
        return {}


def chat_counts(db, window: Window) -> dict:
    if _before_recording(db, window):
        return chatbot_unavailable(BEFORE_RECORDING)
    ok = func.count().filter(Chat.outcome == "success")
    rows = db.execute(
        select(Chat.user_id, ok, func.count())
        .where(Chat.role == "student", *_in_window(Chat.received_at, window)).group_by(Chat.user_id)
    ).all()
    names = _display_names(db, [r[0] for r in rows])
    entries = [{"user_id": u, "name": names.get(u), "successful": s, "unsuccessful": n - s} for u, s, n in rows]
    entries.sort(key=lambda e: (e["name"] is None, (e["name"] or "").casefold(), e["user_id"]))
    student = metric("available", None, successful=sum(e["successful"] for e in entries),
                     unsuccessful=sum(e["unsuccessful"] for e in entries),
                     rows=entries[:config.ROW_CAP_PER_ROLE], rows_truncated=len(entries) > config.ROW_CAP_PER_ROLE)
    teacher = metric("unavailable", "no_source", successful=None, unsuccessful=None, rows=[], rows_truncated=False)
    first = next((g for g in (student, teacher) if g["state"] != "available"), None)
    if first is None:
        total = metric("available", None, successful=student["successful"] + teacher["successful"],
                       unsuccessful=student["unsuccessful"] + teacher["unsuccessful"])
    else:
        total = metric(first["state"], first["reason"], successful=None, unsuccessful=None)
    return {"student": student, "teacher": teacher, "total": total}


def practice_completion(db, window: Window) -> dict:
    if _before_recording(db, window):
        return practice_unavailable(BEFORE_RECORDING)
    started, submitted = db.execute(
        select(func.count(),
               func.count().filter(Attempt.submitted_at.isnot(None), Attempt.submitted_at < window.end_utc_exclusive))
        .where(*_in_window(Attempt.started_at, window))
    ).one()
    if started == 0:
        return metric("not_applicable", "no_practice_attempts", started=0, submitted=0, percentage=None)
    return metric("available", None, started=started, submitted=submitted,
                  percentage=round(submitted / started * 100, 1))


# ---- generation ----

def generation_rates(db, window: Window) -> list[dict]:
    if _before_recording(db, window):
        return generation_unavailable(BEFORE_RECORDING)
    found = {
        w: (n, ok) for w, n, ok in db.execute(
            select(Generation.workflow, func.count(), func.count().filter(Generation.outcome == "success"))
            .where(*_in_window(Generation.accepted_at, window)).group_by(Generation.workflow)
        ).all()
    }
    result = []
    for workflow, label in GENERATION_LABELS.items():
        attempts, successful = found.get(workflow, (0, 0))
        if attempts == 0:
            result.append(metric("not_applicable", "no_generation_attempts", workflow=workflow, label=label,
                                 attempts=0, successful=0, unsuccessful=0, rate_percent=None))
        else:
            result.append(metric("available", None, workflow=workflow, label=label, attempts=attempts,
                                 successful=successful, unsuccessful=attempts - successful,
                                 rate_percent=round(successful / attempts * 100, 1)))
    return result


# ---- quality ----

def _item_scope(workflow: str, window: Window) -> list:
    return [Item.workflow == workflow, *_in_window(Item.received_at, window)]


def eligible_clauses(workflow: str, window: Window, now: datetime) -> list:
    """Items a grading run may send: in scope, ungraded, text still stored, not past retention."""
    return [*_item_scope(workflow, window), Item.status.in_(GRADABLE_STATUSES), Item.privacy_policy_version == privacy.POLICY_VERSION, Item.request_text.isnot(None),
            Item.response_text.isnot(None), Item.created_at >= now - timedelta(days=config.CONTENT_RETENTION_DAYS)]


def _item_rows(db, scope: list, expiry: datetime, limit: int, offset: int) -> dict:
    total = db.scalar(select(func.count()).select_from(Item).where(*scope))
    page = db.execute(
        select(Item.id, Item.received_at, Item.status, Item.duration_ms, Item.failure_code, Item.graded_at,
               Item.created_at, Item.privacy_policy_version)
        .where(*scope).order_by(Item.received_at.desc(), Item.id.desc()).limit(limit).offset(offset)
    ).all()
    graded_ids = [r.id for r in page if r.status == "graded" and r.privacy_policy_version == privacy.POLICY_VERSION]
    grades: dict[int, dict[str, dict]] = {}
    if graded_ids:
        for g in db.execute(select(Grade.item_id, Grade.dimension, Grade.state, Grade.score, Grade.reason)
                            .where(Grade.item_id.in_(graded_ids))).all():
            grades.setdefault(g.item_id, {})[g.dimension] = {
                "dimension": g.dimension, "state": g.state, "score": g.score, "reason": g.reason}
    rows = []
    for r in page:
        expired = r.status in GRADABLE_STATUSES and r.created_at < expiry
        status = ("privacy_blocked" if r.privacy_policy_version != privacy.POLICY_VERSION
                  else "content_expired" if expired else r.status)
        by_dimension = grades.get(r.id, {})
        rows.append({
            "item_id": r.id, "received_at": iso(r.received_at), "status": status, "response_time_ms": r.duration_ms,
            "failure_code": r.failure_code if status in ("grading_failed", "privacy_blocked") else None, "graded_at": iso(r.graded_at),
            "grades": [by_dimension[d] for d in config.DIMENSIONS if d in by_dimension] if status == "graded" else [],
        })
    return {"total": total, "limit": limit, "offset": offset, "rows": rows}


def quality_grades(db, workflow: str, window: Window, limit: int, offset: int) -> dict:
    """{"grades": ..., "items": ...} for one workflow and period."""
    if _before_recording(db, window):
        return {"grades": grades_unavailable(BEFORE_RECORDING), "items": items_empty(limit, offset)}
    scope = _item_scope(workflow, window)
    expiry = datetime.now(timezone.utc) - timedelta(days=config.CONTENT_RETENTION_DAYS)
    fresh, old = Item.created_at >= expiry, Item.created_at < expiry
    current = Item.privacy_policy_version == privacy.POLICY_VERSION
    assessed, pending, failed, expired, blocked = db.execute(
        select(func.count().filter(Item.status == "graded", current),
               func.count().filter(Item.status == "pending", fresh, current),
               func.count().filter(Item.status == "grading_failed", fresh, current),
               func.count().filter(Item.status.in_(GRADABLE_STATUSES), old, current),
               func.count().filter(or_(Item.status == "privacy_blocked", Item.privacy_policy_version.is_distinct_from(privacy.POLICY_VERSION))))
        .where(*scope)
    ).one()
    stats = {}
    for dimension, state, n, total in db.execute(
        select(Grade.dimension, Grade.state, func.count(), func.coalesce(func.sum(Grade.score), 0))
        .join(Item, Item.id == Grade.item_id).where(*scope, Item.status == "graded", current)
        .group_by(Grade.dimension, Grade.state)
    ).all():
        stats[(dimension, state)] = (n, total)
    dimensions = []
    for dimension in config.DIMENSIONS:
        graded, score_sum = stats.get((dimension, "graded"), (0, 0))
        dimensions.append({
            "dimension": dimension, "average": round(score_sum / graded, 2) if graded else None,
            "graded_count": graded, "unassessable_count": stats.get((dimension, "unassessable"), (0, 0))[0]})
    counts = dict(assessed_count=assessed, pending_count=pending, grading_failed_count=failed,
                  content_expired_count=expired, privacy_blocked_count=blocked, privacy_mode=privacy.privacy_mode(), dimensions=dimensions)
    grades = metric("available", None, **counts) if assessed else metric("not_applicable", "none_graded", **counts)
    return {"grades": grades, "items": _item_rows(db, scope, expiry, limit, offset)}


def response_times(db, workflow: str, window: Window) -> dict:
    if _before_recording(db, window):
        return response_time_unavailable(BEFORE_RECORDING)
    if workflow == "student_exercise":
        model = Chat
        scope = [Chat.role == "student", Chat.activity_type == "practice_attempt",
                 *_in_window(Chat.received_at, window)]
    else:
        model = Generation
        scope = _in_window(Generation.accepted_at, window)
    done = [model.outcome == "success", model.duration_ms.isnot(None)]
    count, mean, median, failed = db.execute(
        select(func.count().filter(*done), func.avg(model.duration_ms).filter(*done),
               func.percentile_cont(0.5).within_group(model.duration_ms).filter(*done),
               func.count().filter(model.outcome.in_(("failure", "pending"))))
        .where(*scope)
    ).one()
    if not count:
        return metric("not_applicable", "no_eligible_records", successful_count=0, mean_ms=None, median_ms=None,
                      failed_or_incomplete_count=failed)
    return metric("available", None, successful_count=count, mean_ms=_half_up(mean), median_ms=_half_up(median),
                  failed_or_incomplete_count=failed)


def _student_sessions(window: Window) -> list:
    return [Session.role == "student", *_in_window(Session.started_at, window)]


def session_stats(db, workflow: str, window: Window) -> dict:
    if workflow != "student_exercise":
        return sessions_unavailable("no_source")
    if _before_recording(db, window):
        return sessions_unavailable(BEFORE_RECORDING)
    sessions = db.scalar(select(func.count()).select_from(Session).where(*_student_sessions(window)))
    if not sessions:
        return metric("not_applicable", "no_eligible_records", session_count=0, average_messages_per_session=None,
                      user_messages=0, ai_messages=0)
    user_messages, ai_messages = db.execute(
        select(func.count(), func.count().filter(Chat.outcome == "success"))
        .where(Chat.session_id.in_(select(Session.id).where(*_student_sessions(window))))
    ).one()
    return metric("available", None, session_count=sessions,
                  average_messages_per_session=round((user_messages + ai_messages) / sessions, 2),
                  user_messages=user_messages, ai_messages=ai_messages)


def activity_time_stats(db, workflow: str, window: Window) -> dict:
    if workflow != "student_exercise":
        return activity_unavailable("no_source")
    if _before_recording(db, window):
        return activity_unavailable(BEFORE_RECORDING)
    events = {"start_event": "Practice attempt started", "end_event": "Practice attempt submitted"}
    rows = db.execute(
        select(Session.id, Session.activity_ref, Attempt.started_at, Attempt.submitted_at)
        .select_from(Session)
        .outerjoin(Attempt, Attempt.attempt_ref == Session.activity_ref).where(*_student_sessions(window))
    ).all()
    included = [r for r in rows if r.started_at is not None and r.submitted_at is not None]
    excluded = len(rows) - len(included)
    if not included:
        return metric("not_applicable", "no_eligible_records", linked_session_count=0, distinct_activity_count=0,
                      excluded_session_count=excluded, average_messages_per_session=None,
                      average_activity_seconds=None, **events)
    per_session = {
        sid: n + ok for sid, n, ok in db.execute(
            select(Chat.session_id, func.count(), func.count().filter(Chat.outcome == "success"))
            .where(Chat.session_id.in_(select(Session.id).where(*_student_sessions(window))))
            .group_by(Chat.session_id)
        ).all()
    }
    seconds = {r.activity_ref: (r.submitted_at - r.started_at).total_seconds() for r in included}
    return metric("available", None, linked_session_count=len(included), distinct_activity_count=len(seconds),
                  excluded_session_count=excluded,
                  average_messages_per_session=round(sum(per_session.get(r.id, 0) for r in included) / len(included), 2),
                  average_activity_seconds=round(sum(seconds.values()) / len(seconds), 1), **events)


# ---- grading runs ----

def run_object(row) -> dict:
    return {
        "run_id": row.id, "workflow": row.workflow, "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(), "status": row.status, "items_total": row.items_total,
        "items_graded": row.items_graded, "items_failed": row.items_failed, "failure_code": row.failure_code,
        "created_at": iso(row.created_at), "started_at": iso(row.started_at), "finished_at": iso(row.finished_at),
    }


def active_run(db) -> dict | None:
    row = db.scalars(select(Run).where(Run.status.in_(ACTIVE_STATUSES)).order_by(Run.id.desc()).limit(1)).first()
    return None if row is None else run_object(row)
