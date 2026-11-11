"""Read side of ADM-01: each function returns one metric object as in plan.md. No stored text is ever selected for output."""
import dataclasses
from collections import Counter
from contextvars import ContextVar
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, func, or_, select

from feature_analytics import config, privacy
from feature_analytics.health import (
    finished_state, median_half_up, median_one_decimal, percentile_nearest_rank, rate_percent, severity)
from feature_analytics.models import (
    AnalyticsChatRequest as Chat,
    AnalyticsGenerationAttempt as Generation,
    AnalyticsGrade as Grade,
    AnalyticsGradingItem as Item,
    AnalyticsGradingRun as Run,
    AnalyticsLoginEvent as Login,
    AnalyticsMeta,
    AnalyticsPracticeAttempt as Attempt,
    AnalyticsPracticeDraftStarted as Draft,
    AnalyticsPracticePublished as Published,
    AnalyticsRequestLog as RequestLog,
    AnalyticsSession as Session,
)
from feature_analytics.periods import Window
from teacher_materials.models import User
from timestamps import utc_timestamp

BEFORE_RECORDING = "period_before_recording"
GENERATION_LABELS = {"study_notes": "Study notes", "mcq_batch": "MCQ batches"}
GENERATION_KIND_OF = {"study_notes": "generation_notes", "mcq_batch": "generation_mcq"}
ACTIVE_STATUSES = ("queued", "running")
GRADABLE_STATUSES = ("pending", "grading_failed")


def metric(state: str, reason: str | None, data_starts_on: str | None = None, **fields) -> dict:
    return {"state": state, "reason": reason, "data_starts_on": data_starts_on, **fields}


def iso(value: datetime | None) -> str | None:
    return None if value is None else utc_timestamp(value)


def _half_up(value) -> int:
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _in_window(column, window: Window) -> list:
    return [column >= window.start_utc, column < window.end_utc_exclusive]


def recording_started_on(db, key: str = "recording_started_at") -> date:
    """The UTC date a source started recording (analytics_meta); a missing row counts as 'always recorded'."""
    value = db.scalar(select(AnalyticsMeta.value).where(AnalyticsMeta.key == key))
    if value is None:
        return date.min
    parsed = datetime.fromisoformat(value)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).date()


@dataclasses.dataclass(frozen=True)
class Cover:
    """What part of a period a source covers: `window` starts at the effective start; `reason` is set when none of it does."""

    window: Window
    starts_on: str | None  # ISO date of the first covered day when the period starts earlier, else None
    reason: str | None


def _cover(db, window: Window, floor: datetime | None = None, key: str = "recording_started_at") -> Cover:
    """Partial coverage (ADM-07): the metric covers [max(period start, source start, floor), period end]."""
    source = datetime.combine(recording_started_on(db, key), time.min, tzinfo=timezone.utc)
    start = max(window.start_utc, source, floor or window.start_utc)
    if start >= window.end_utc_exclusive:
        reason = "beyond_retention" if floor is not None and floor >= source else BEFORE_RECORDING
        return Cover(window, None, reason)
    if start == window.start_utc:
        return Cover(window, None, None)
    return Cover(dataclasses.replace(window, start_utc=start), start.date().isoformat(), None)


def latest_start(*metrics: dict | None) -> str | None:
    """The latest data_starts_on among metric objects (ISO dates compare as text)."""
    found = [m["data_starts_on"] for m in metrics if m and m.get("data_starts_on")]
    return max(found) if found else None


_request_now: ContextVar[datetime | None] = ContextVar("analytics_request_now", default=None)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def begin_request() -> datetime:
    """Take the one server timestamp of this request; every in-progress decision of the request uses it."""
    now = utcnow()
    _request_now.set(now)
    return now


def _now() -> datetime:
    return _request_now.get() or utcnow()


# ---- unavailable shapes (also used by the routes for read_failed) ----

def chatbot_unavailable(reason: str) -> dict:
    group = metric("unavailable", reason, successful=None, unsuccessful=None, rows=[], rows_truncated=False)
    total = metric("unavailable", reason, successful=None, unsuccessful=None)
    return {"student": dict(group), "teacher": dict(group), "total": total}


def practice_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, started=None, submitted=None, percentage=None)


# Shape of an unavailable (not collected) rate-limited count.
RATE_LIMITED_NOT_COLLECTED = {"state": "unavailable", "reason": "not_collected"}


def generation_unavailable(reason: str) -> list[dict]:
    return [metric("unavailable", reason, workflow=w, label=label, attempts=None, requests=None, rate_limited=None,
                   rate_limited_state=RATE_LIMITED_NOT_COLLECTED, successful=None, unsuccessful=None,
                   rate_percent=None) for w, label in GENERATION_LABELS.items()]


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


def chat_counts(db, window: Window, include_rows: bool = True) -> dict:
    cover = _cover(db, window)
    if cover.reason:
        return chatbot_unavailable(cover.reason)
    window = cover.window
    ok = func.count().filter(Chat.outcome == "success")
    rows = db.execute(
        select(Chat.user_id, ok, func.count())
        .where(Chat.role == "student", *_in_window(Chat.received_at, window)).group_by(Chat.user_id)
    ).all()
    names = _display_names(db, [r[0] for r in rows]) if include_rows else {}
    entries = [{"user_id": u, "name": names.get(u), "successful": s, "unsuccessful": n - s} for u, s, n in rows]
    entries.sort(key=lambda e: (e["name"] is None, (e["name"] or "").casefold(), e["user_id"]))
    shown = entries[:config.ROW_CAP_PER_ROLE] if include_rows else []
    student = metric("available", None, cover.starts_on, successful=sum(e["successful"] for e in entries),
                     unsuccessful=sum(e["unsuccessful"] for e in entries),
                     rows=shown, rows_truncated=include_rows and len(entries) > config.ROW_CAP_PER_ROLE)
    teacher = metric("unavailable", "no_source", successful=None, unsuccessful=None, rows=[], rows_truncated=False)
    first = next((g for g in (student, teacher) if g["state"] != "available"), None)
    if first is None:
        total = metric("available", None, cover.starts_on, successful=student["successful"] + teacher["successful"],
                       unsuccessful=student["unsuccessful"] + teacher["unsuccessful"])
    else:
        total = metric(first["state"], first["reason"], successful=None, unsuccessful=None)
    return {"student": student, "teacher": teacher, "total": total}


def practice_completion(db, window: Window) -> dict:
    cover = _cover(db, window)
    if cover.reason:
        return practice_unavailable(cover.reason)
    started, submitted = db.execute(
        select(func.count(),
               func.count().filter(Attempt.submitted_at.isnot(None), Attempt.submitted_at < window.end_utc_exclusive))
        .where(*_in_window(Attempt.started_at, cover.window))
    ).one()
    if started == 0:
        return metric("not_applicable", "no_practice_attempts", cover.starts_on, started=0, submitted=0, percentage=None)
    return metric("available", None, cover.starts_on, started=started, submitted=submitted,
                  percentage=round(submitted / started * 100, 1))


# ---- generation ----

def generation_rates(db, window: Window) -> list[dict]:
    """Accepted attempts plus limiter-refused requests (request log) per workflow; refusals are never attempts."""
    cover = _cover(db, window)
    if cover.reason:
        return generation_unavailable(cover.reason)
    found = {
        w: (n, ok) for w, n, ok in db.execute(
            select(Generation.workflow, func.count(), func.count().filter(Generation.outcome == "success"))
            .where(*_in_window(Generation.accepted_at, cover.window)).group_by(Generation.workflow)
        ).all()
    }
    log_cover = _log_cover(db, window, CATEGORIES_KEY)
    refused: dict[str, int] = {}
    if not log_cover.reason:
        refused = dict(db.execute(
            select(RequestLog.kind, func.count())
            .where(RequestLog.kind.in_(GENERATION_KINDS), RequestLog.failure_category == "rate_limited",
                   *_in_window(RequestLog.occurred_at, log_cover.window)).group_by(RequestLog.kind)).all())
    state = ({"state": "unavailable", "reason": log_cover.reason} if log_cover.reason
             else {"state": "available", "reason": None})
    result = []
    for workflow, label in GENERATION_LABELS.items():
        attempts, successful = found.get(workflow, (0, 0))
        limited = None if log_cover.reason else refused.get(GENERATION_KIND_OF[workflow], 0)
        requests = attempts + (limited or 0)
        fields = dict(workflow=workflow, label=label, attempts=attempts, requests=requests, rate_limited=limited,
                      rate_limited_state=state, successful=successful, unsuccessful=requests - successful)
        if requests == 0:
            result.append(metric("not_applicable", "no_generation_attempts", cover.starts_on, rate_percent=None,
                                 **fields))
        else:
            result.append(metric("available", None, cover.starts_on, rate_percent=round(successful / requests * 100, 1),
                                 **fields))
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
    cover = _cover(db, window)
    if cover.reason:
        return {"grades": grades_unavailable(cover.reason), "items": items_empty(limit, offset)}
    scope = _item_scope(workflow, cover.window)
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
    grades = (metric("available", None, cover.starts_on, **counts) if assessed
              else metric("not_applicable", "none_graded", cover.starts_on, **counts))
    return {"grades": grades, "items": _item_rows(db, scope, expiry, limit, offset)}


def response_times(db, workflow: str, window: Window) -> dict:
    cover = _cover(db, window)
    if cover.reason:
        return response_time_unavailable(cover.reason)
    window = cover.window
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
        return metric("not_applicable", "no_eligible_records", cover.starts_on, successful_count=0, mean_ms=None,
                      median_ms=None, failed_or_incomplete_count=failed)
    return metric("available", None, cover.starts_on, successful_count=count, mean_ms=_half_up(mean), median_ms=_half_up(median),
                  failed_or_incomplete_count=failed)


def _student_sessions(window: Window) -> list:
    return [Session.role == "student", *_in_window(Session.started_at, window)]


def session_stats(db, workflow: str, window: Window) -> dict:
    if workflow != "student_exercise":
        return sessions_unavailable("no_source")
    cover = _cover(db, window)
    if cover.reason:
        return sessions_unavailable(cover.reason)
    window = cover.window
    sessions = db.scalar(select(func.count()).select_from(Session).where(*_student_sessions(window)))
    if not sessions:
        return metric("not_applicable", "no_eligible_records", cover.starts_on, session_count=0,
                      average_messages_per_session=None, user_messages=0, ai_messages=0)
    user_messages, ai_messages = db.execute(
        select(func.count(), func.count().filter(Chat.outcome == "success"))
        .where(Chat.session_id.in_(select(Session.id).where(*_student_sessions(window))))
    ).one()
    return metric("available", None, cover.starts_on, session_count=sessions,
                  average_messages_per_session=round((user_messages + ai_messages) / sessions, 2),
                  user_messages=user_messages, ai_messages=ai_messages)


def activity_time_stats(db, workflow: str, window: Window) -> dict:
    if workflow != "student_exercise":
        return activity_unavailable("no_source")
    cover = _cover(db, window)
    if cover.reason:
        return activity_unavailable(cover.reason)
    window = cover.window
    events = {"start_event": "Practice attempt started", "end_event": "Practice attempt submitted"}
    rows = db.execute(
        select(Session.id, Session.activity_ref, Attempt.started_at, Attempt.submitted_at)
        .select_from(Session)
        .outerjoin(Attempt, Attempt.attempt_ref == Session.activity_ref).where(*_student_sessions(window))
    ).all()
    included = [r for r in rows if r.started_at is not None and r.submitted_at is not None]
    excluded = len(rows) - len(included)
    if not included:
        return metric("not_applicable", "no_eligible_records", cover.starts_on, linked_session_count=0,
                      distinct_activity_count=0,
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
    return metric("available", None, cover.starts_on, linked_session_count=len(included), distinct_activity_count=len(seconds),
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


# ---- ADM-07 hub: health, hourly, daily and per-user reads (request log and event tables) ----

HOUR = timedelta(hours=1)
IN_PROGRESS = "in_progress"


def _utc_date(value: datetime) -> date:
    return value.astimezone(timezone.utc).date()


REQUEST_LOG_KEY = "request_log_started_at"
CATEGORIES_KEY = "request_log_categories_started_at"
CHATBOT_KINDS = ("chatbot",)
GENERATION_KINDS = ("generation_notes", "generation_mcq")


def _retention_floor(now: datetime) -> datetime:
    """Request-log rows older than this are purged, so reads ignore them even before the purge ran."""
    return now.replace(minute=0, second=0, microsecond=0) - timedelta(days=config.PURGE_REQUEST_LOG_DAYS)


def _log_cover(db, window: Window, key: str = REQUEST_LOG_KEY) -> Cover:
    return _cover(db, window, _retention_floor(_now()), key)


def _log_requests(db, kinds: tuple[str, ...], window: Window,
                  now: datetime) -> list[tuple[datetime, str, int | None, str | None]]:
    """(time, state, duration_ms, category) of each logged request, with the in-progress rule applied at `now`.
    An expired pending row is a timeout failure of 120 000 ms; a success has no category."""
    rows = db.execute(
        select(RequestLog.occurred_at, RequestLog.outcome, RequestLog.duration_ms, RequestLog.failure_category)
        .where(RequestLog.kind.in_(kinds), *_in_window(RequestLog.occurred_at, window))
    ).all()
    expired_ms = config.IN_PROGRESS_EXPIRY_S * 1000
    result = []
    for at, outcome, duration, category in rows:
        state = finished_state(outcome, at, now)
        if outcome == "pending" and state == "failure":
            duration, category = expired_ms, "timeout"
        result.append((at, state, duration, category))
    return result


def failure_unavailable(reason: str, **extra) -> dict:
    return metric("unavailable", reason, total=None, failed=None, in_progress=None, rate_percent=None,
                  severity=None, **extra)


def _failure_tile(requests: list, starts_on: str | None, empty_reason: str, **extra) -> dict:
    in_progress = sum(1 for _, state, *_ in requests if state == IN_PROGRESS)
    total = len(requests) - in_progress
    failed = sum(1 for _, state, *_ in requests if state == "failure")
    if total == 0:
        return metric("not_applicable", empty_reason, starts_on, total=0, failed=0, in_progress=in_progress,
                      rate_percent=None, severity=None, **extra)
    return metric("available", None, starts_on, total=total, failed=failed, in_progress=in_progress,
                  rate_percent=rate_percent(failed, total), severity=severity(failed, total), **extra)


def health_chatbot(db, window: Window) -> dict:
    cover = _log_cover(db, window)
    if cover.reason:
        return failure_unavailable(cover.reason)
    return _failure_tile(_log_requests(db, CHATBOT_KINDS, cover.window, _now()), cover.starts_on, "no_chat_requests")


def health_generation(db, window: Window) -> dict:
    cover = _log_cover(db, window)
    if cover.reason:
        return failure_unavailable(cover.reason, includes_rate_limited=True)
    return _failure_tile(_log_requests(db, GENERATION_KINDS, cover.window, _now()), cover.starts_on,
                         "no_generation_attempts", includes_rate_limited=True)


def rate_limited_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, since=None, count=None, total_requests=None)


def health_rate_limited(db, window: Window) -> dict:
    """Limiter refusals among all finished logged requests, from the date categories became real; 0 is available."""
    cover = _log_cover(db, window, CATEGORIES_KEY)
    if cover.reason:
        return rate_limited_unavailable(cover.reason)
    finished = [r for r in _log_requests(db, CHATBOT_KINDS + GENERATION_KINDS, cover.window, _now())
                if r[1] != IN_PROGRESS]
    since = recording_started_on(db, CATEGORIES_KEY)
    return metric("available", None, cover.starts_on, since=since.isoformat() if since != date.min else None,
                  count=sum(1 for r in finished if r[3] == "rate_limited"), total_requests=len(finished))


def _time_set(values: list[int]) -> dict:
    ordered = sorted(values)
    return {"count": len(ordered), "median_ms": median_half_up(ordered), "p95_ms": percentile_nearest_rank(ordered, 95)}


def response_time_tile_unavailable(reason: str) -> dict:
    empty = {"count": None, "median_ms": None, "p95_ms": None}
    return metric("unavailable", reason, **{name: dict(empty) for name in ("all", "successful", "failed")})


def _response_time_tile(requests: list, starts_on: str | None, empty_reason: str) -> dict:
    """Three sets over finished requests with a duration; in-progress rows and rows without a duration are in none."""
    ok = [d for _, state, d, _ in requests if state == "success" and d is not None]
    bad = [d for _, state, d, _ in requests if state == "failure" and d is not None]
    sets = {"all": _time_set(ok + bad), "successful": _time_set(ok), "failed": _time_set(bad)}
    if not ok and not bad:
        return metric("not_applicable", empty_reason, starts_on, **sets)
    return metric("available", None, starts_on, **sets)


def health_chatbot_response_time(db, window: Window) -> dict:
    cover = _log_cover(db, window)
    if cover.reason:
        return response_time_tile_unavailable(cover.reason)
    return _response_time_tile(_log_requests(db, CHATBOT_KINDS, cover.window, _now()), cover.starts_on,
                               "no_chat_requests")


def health_generation_response_time(db, window: Window) -> dict:
    cover = _log_cover(db, window)
    if cover.reason:
        return response_time_tile_unavailable(cover.reason)
    return _response_time_tile(_log_requests(db, GENERATION_KINDS, cover.window, _now()), cover.starts_on,
                               "no_generation_attempts")


# ---- hourly ----

CATEGORIES = ("timeout", "rate_limited", "invalid_output", "upstream", "unclassified")


def hourly_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, in_progress=None, retention_days=config.PURGE_REQUEST_LOG_DAYS,
                  category_breakdown={"state": "unavailable", "reason": "not_collected"}, totals=None, buckets=[])


def hourly(db, window: Window) -> dict:
    """One bucket per UTC hour from the effective start; chatbot and generation requests together, with categories."""
    now = _now()
    cover = _log_cover(db, window)
    if cover.reason:
        return hourly_unavailable(cover.reason)
    start = cover.window.start_utc
    count = (window.end_utc_exclusive - start) // HOUR
    successful, failed = [0] * count, [0] * count
    by_category = [dict.fromkeys(CATEGORIES, 0) for _ in range(count)]
    in_progress = 0
    for at, state, _, category in _log_requests(db, CHATBOT_KINDS + GENERATION_KINDS, cover.window, now):
        if state == IN_PROGRESS:
            in_progress += 1
            continue
        index = (at - start) // HOUR
        if state == "success":
            successful[index] += 1
        else:
            failed[index] += 1
            by_category[index][category if category in CATEGORIES else "unclassified"] += 1
    buckets = []
    for i in range(count):
        total = successful[i] + failed[i]
        buckets.append({"hour_start": iso(start + i * HOUR), "successful": successful[i], "failed": failed[i],
                        "total": total, "failure_rate_percent": rate_percent(failed[i], total),
                        "failed_by_category": by_category[i]})
    return metric("available", None, cover.starts_on, in_progress=in_progress,
                  retention_days=config.PURGE_REQUEST_LOG_DAYS,
                  category_breakdown={"state": "available", "reason": None},
                  totals={"successful": sum(successful), "failed": sum(failed),
                          "total": sum(successful) + sum(failed)},
                  buckets=buckets)


# ---- daily ----

_SERIES_TOTALS = {"logins": "total_logins", "practice_drafts_started": "total", "practice_published": "total"}


def daily_series_unavailable(name: str, reason: str) -> dict:
    return metric("unavailable", reason, since=None, per_day=[], **{_SERIES_TOTALS[name]: None})


def funnel_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, started_total=None, submitted_by_period_end=None, per_day=[])


def per_student_unavailable(reason: str) -> dict:
    return metric("unavailable", reason, per_day=[])


LOGINS_KEY = "login_events_started_at"
DRAFT_KEY = "practice_draft_started_started_at"
PUBLISHED_KEY = "practice_published_started_at"


def _series_days(cover: Cover, window: Window) -> list[date]:
    return _days(_utc_date(cover.window.start_utc), window.period_end)


def _since(db, key: str) -> str | None:
    started = recording_started_on(db, key)
    return None if started == date.min else started.isoformat()


def daily_logins(db, window: Window) -> dict:
    cover = _cover(db, window, key=LOGINS_KEY)
    if cover.reason:
        return daily_series_unavailable("logins", cover.reason)
    rows = db.execute(select(Login.occurred_at, Login.user_id, Login.role)
                      .where(*_in_window(Login.occurred_at, cover.window))).all()
    events: dict[date, list] = {}
    for at, user_id, role in rows:
        events.setdefault(_utc_date(at), []).append((user_id, role))
    per_day = []
    for day in _series_days(cover, window):
        today = events.get(day, [])
        students = {u for u, r in today if r == "student"}
        teachers = {u for u, r in today if r == "teacher"}
        student_logins = sum(1 for _, r in today if r == "student")
        per_day.append({"date": day.isoformat(), "student_logins": student_logins,
                        "teacher_logins": len(today) - student_logins, "total_logins": len(today),
                        "active_students": len(students), "active_teachers": len(teachers),
                        "active_users_total": len(students | teachers)})
    return metric("available", None, cover.starts_on, since=_since(db, LOGINS_KEY), per_day=per_day,
                  total_logins=len(rows))


def _first_event_series(db, window: Window, name: str, key: str, column, field: str) -> dict:
    cover = _cover(db, window, key=key)
    if cover.reason:
        return daily_series_unavailable(name, cover.reason)
    counts = Counter(_utc_date(at) for (at,) in db.execute(select(column).where(*_in_window(column, cover.window))))
    per_day = [{"date": d.isoformat(), field: counts[d]} for d in _series_days(cover, window)]
    return metric("available", None, cover.starts_on, since=_since(db, key), per_day=per_day,
                  total=sum(counts.values()))


def daily_practice_drafts_started(db, window: Window) -> dict:
    return _first_event_series(db, window, "practice_drafts_started", DRAFT_KEY, Draft.started_at, "drafts_started")


def daily_practice_published(db, window: Window) -> dict:
    return _first_event_series(db, window, "practice_published", PUBLISHED_KEY, Published.published_at, "published")


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def daily_attempts_funnel(db, window: Window) -> dict:
    cover = _cover(db, window)
    if cover.reason:
        return funnel_unavailable(cover.reason)
    w = cover.window
    rows = db.execute(
        select(Attempt.started_at, Attempt.submitted_at)
        .where(or_(and_(*_in_window(Attempt.started_at, w)), and_(*_in_window(Attempt.submitted_at, w))))
    ).all()
    started, submitted = Counter(), Counter()
    started_total = submitted_by_end = 0
    for began, finished in rows:
        if w.start_utc <= began < w.end_utc_exclusive:
            started[_utc_date(began)] += 1
            started_total += 1
            submitted_by_end += finished is not None and finished < w.end_utc_exclusive
        if finished is not None and w.start_utc <= finished < w.end_utc_exclusive:
            submitted[_utc_date(finished)] += 1
    per_day = [{"date": d.isoformat(), "started": started[d], "submitted": submitted[d]}
               for d in _days(_utc_date(w.start_utc), window.period_end)]
    fields = dict(started_total=started_total, submitted_by_period_end=submitted_by_end, per_day=per_day)
    if started_total == 0:
        return metric("not_applicable", "no_practice_attempts", cover.starts_on, **fields)
    return metric("available", None, cover.starts_on, **fields)


def daily_attempts_per_student(db, window: Window) -> dict:
    cover = _cover(db, window)
    if cover.reason:
        return per_student_unavailable(cover.reason)
    w = cover.window
    rows = db.execute(select(Attempt.started_at, Attempt.user_id).where(*_in_window(Attempt.started_at, w))).all()
    per_user: dict[date, Counter] = {}
    for began, user_id in rows:
        per_user.setdefault(_utc_date(began), Counter())[user_id] += 1
    per_day = []
    for day in _days(_utc_date(w.start_utc), window.period_end):
        counts = sorted(per_user.get(day, Counter()).values())
        median = median_one_decimal(counts)
        distribution = {str(n): counts.count(n) for n in (1, 2, 3, 4)}
        distribution["5_plus"] = sum(1 for n in counts if n >= 5)
        per_day.append({"date": day.isoformat(), "active_students": len(counts), "median_attempts": median,
                        "distribution": distribution})
    if not rows:
        return metric("not_applicable", "no_practice_attempts", cover.starts_on, per_day=per_day)
    return metric("available", None, cover.starts_on, per_day=per_day)


# ---- chatbot users ----

def chatbot_users_unavailable(reason: str, role: str, sort: str, order: str, limit: int, offset: int) -> dict:
    return metric("unavailable", reason, in_progress=None, role=role, sort=sort, order=order, limit=limit,
                  offset=offset, totals={"successful": None, "unsuccessful": None},
                  all_users_total=metric("unavailable", reason, successful=None, unsuccessful=None),
                  total_users=None, rows=[])


def _sort_users(entries: list[dict], sort: str, order: str) -> list[dict]:
    """Primary column in `order`; ties by name (case-insensitive, nulls last) then user id. Python sorts are stable."""
    reverse = order == "desc"
    entries.sort(key=lambda e: e["user_id"])
    entries.sort(key=lambda e: (e["name"] is None, (e["name"] or "").casefold()))
    if sort == "name":
        named = sorted((e for e in entries if e["name"] is not None), key=lambda e: e["name"].casefold(),
                       reverse=reverse)
        return named + [e for e in entries if e["name"] is None]
    if sort == "failure_rate":
        entries.sort(key=lambda e: -e["unsuccessful"])
        entries.sort(key=lambda e: e["unsuccessful"] / (e["successful"] + e["unsuccessful"]), reverse=reverse)
    else:
        entries.sort(key=lambda e: e[sort], reverse=reverse)
    return entries


def chatbot_users(db, window: Window, role: str, sort: str, order: str, limit: int, offset: int) -> dict:
    shape = (role, sort, order, limit, offset)
    if role == "teacher":
        return chatbot_users_unavailable("no_source", *shape)
    cover = _cover(db, window)
    if cover.reason:
        return chatbot_users_unavailable(cover.reason, *shape)
    now = _now()
    counts: dict[str, list[int]] = {}
    in_progress = 0
    for user_id, at, outcome in db.execute(
        select(Chat.user_id, Chat.received_at, Chat.outcome)
        .where(Chat.role == "student", *_in_window(Chat.received_at, cover.window))
    ).all():
        state = finished_state(outcome, at, now)
        if state == IN_PROGRESS:
            in_progress += 1
        else:
            counts.setdefault(user_id, [0, 0])[state == "failure"] += 1
    names = _display_names(db, list(counts))
    entries = [{"user_id": u, "name": names.get(u), "successful": s, "unsuccessful": f,
                "failure_rate_percent": rate_percent(f, s + f)} for u, (s, f) in counts.items()]
    page = _sort_users(entries, sort, order)[offset:offset + limit]
    return metric("available", None, cover.starts_on, in_progress=in_progress, role=role, sort=sort, order=order,
                  limit=limit, offset=offset,
                  totals={"successful": sum(s for s, _ in counts.values()),
                          "unsuccessful": sum(f for _, f in counts.values())},
                  all_users_total=metric("unavailable", "no_source", successful=None, unsuccessful=None),
                  total_users=len(entries), rows=page)
