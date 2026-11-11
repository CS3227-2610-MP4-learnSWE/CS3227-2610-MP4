"""ADM-01 endpoints: usage, generation reliability, quality and the AI grading run. Admin only."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from errors import ApiError
from feature_analytics import config, jobs, periods, queries, privacy
from feature_analytics.models import AnalyticsGradingItem as Item, AnalyticsGradingRun as Run
from feature_analytics.schemas import GradingRunIn
from llm_client import LlmClient, get_llm_client

log = logging.getLogger("feature_analytics")
router = APIRouter(prefix="/api/admin/analytics", tags=["feature-analytics"])
admin_user = current_user(role="admin")
_MAX_ID = 2**63 - 1


def _read(db: Session, read, failed):
    """One metric: if reading it raises, it is reported unavailable/read_failed and the rest of the response stands."""
    try:
        return read()
    except Exception as exc:  # noqa: BLE001
        log.warning("analytics read failed, class=%s", type(exc).__name__)
        db.rollback()
        return failed


def _sweep() -> None:
    try:
        jobs.sweep_stuck_runs()
    except Exception as exc:  # noqa: BLE001 - reading must not depend on the sweep
        log.warning("analytics sweep failed, class=%s", type(exc).__name__)


def _header(window: periods.Window, db: Session) -> dict:
    return {"period_start": window.period_start.isoformat(), "period_end": window.period_end.isoformat(),
            "recording_started_on": queries.recording_started_on(db).isoformat()}


@router.get("/usage")
def usage(period_start: str | None = None, period_end: str | None = None, include_rows: str | None = None,
          _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    rows = periods.parse_include_rows(include_rows)
    chatbot = _read(db, lambda: queries.chat_counts(db, window, rows), queries.chatbot_unavailable("read_failed"))
    practice = _read(db, lambda: queries.practice_completion(db, window), queries.practice_unavailable("read_failed"))
    return {
        **_header(window, db),
        "data_starts_on": queries.latest_start(chatbot["student"], practice),
        "chatbot": chatbot,
        "practice_completion": practice,
    }


@router.get("/generation")
def generation(period_start: str | None = None, period_end: str | None = None, _: AuthUser = Depends(admin_user),
               db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    workflows = _read(db, lambda: queries.generation_rates(db, window), queries.generation_unavailable("read_failed"))
    return {**_header(window, db), "data_starts_on": queries.latest_start(*workflows), "workflows": workflows}


@router.get("/quality")
def quality(workflow: str | None = None, period_start: str | None = None, period_end: str | None = None,
            limit: str | None = None, offset: str | None = None, _: AuthUser = Depends(admin_user),
            db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    kind = periods.parse_workflow(workflow)
    page_limit, page_offset = periods.parse_paging(limit, offset)
    _sweep()
    page = _read(db, lambda: queries.quality_grades(db, kind, window, page_limit, page_offset),
                 {"grades": queries.grades_unavailable("read_failed"), "items": queries.items_empty(page_limit, page_offset)})
    response_time = _read(db, lambda: queries.response_times(db, kind, window),
                          queries.response_time_unavailable("read_failed"))
    sessions = _read(db, lambda: queries.session_stats(db, kind, window), queries.sessions_unavailable("read_failed"))
    activity = _read(db, lambda: queries.activity_time_stats(db, kind, window),
                     queries.activity_unavailable("read_failed"))
    return {
        "workflow": kind, **_header(window, db),
        "data_starts_on": queries.latest_start(page["grades"], response_time, sessions, activity),
        "grades": page["grades"], "response_time": response_time, "sessions": sessions, "activity_time": activity,
        "items": page["items"],
        "active_run": _read(db, lambda: queries.active_run(db), None),
    }


@router.get("/health")
def health(period_start: str | None = None, period_end: str | None = None, _: AuthUser = Depends(admin_user),
           db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    as_of = queries.begin_request()
    tiles = {
        "chatbot_failure": _read(db, lambda: queries.health_chatbot(db, window),
                                 queries.failure_unavailable("read_failed")),
        "generation_failure": _read(db, lambda: queries.health_generation(db, window),
                                    queries.failure_unavailable("read_failed", includes_rate_limited=True)),
        "rate_limited": _read(db, lambda: queries.health_rate_limited(db, window),
                              queries.rate_limited_unavailable("read_failed")),
        "chatbot_response_time": _read(db, lambda: queries.health_chatbot_response_time(db, window),
                                       queries.response_time_tile_unavailable("read_failed")),
        "generation_response_time": _read(db, lambda: queries.health_generation_response_time(db, window),
                                          queries.response_time_tile_unavailable("read_failed")),
        "practice_completion": _read(db, lambda: queries.practice_completion(db, window),
                                     queries.practice_unavailable("read_failed")),
    }
    return {**_header(window, db), "data_starts_on": queries.latest_start(*tiles.values()),
            "as_of": queries.iso(as_of), "low_sample_threshold": config.LOW_SAMPLE_REQUESTS, **tiles}


@router.get("/hourly")
def hourly(period_start: str | None = None, period_end: str | None = None, _: AuthUser = Depends(admin_user),
           db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    as_of = queries.begin_request()
    body = _read(db, lambda: queries.hourly(db, window), queries.hourly_unavailable("read_failed"))
    return {**_header(window, db), "as_of": queries.iso(as_of), **body}


@router.get("/daily")
def daily(period_start: str | None = None, period_end: str | None = None, _: AuthUser = Depends(admin_user),
          db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    return {
        **_header(window, db),
        "logins": _read(db, lambda: queries.daily_logins(db, window),
                        queries.daily_series_unavailable("logins", "read_failed")),
        "practice_drafts_started": _read(db, lambda: queries.daily_practice_drafts_started(db, window),
                                         queries.daily_series_unavailable("practice_drafts_started", "read_failed")),
        "practice_published": _read(db, lambda: queries.daily_practice_published(db, window),
                                    queries.daily_series_unavailable("practice_published", "read_failed")),
        "attempts_funnel": _read(db, lambda: queries.daily_attempts_funnel(db, window),
                                 queries.funnel_unavailable("read_failed")),
        "attempts_per_student": _read(db, lambda: queries.daily_attempts_per_student(db, window),
                                      queries.per_student_unavailable("read_failed")),
    }


@router.get("/chatbot-users")
def chatbot_users(period_start: str | None = None, period_end: str | None = None, role: str | None = None,
                  sort: str | None = None, order: str | None = None, limit: str | None = None,
                  offset: str | None = None, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    window = periods.parse_period(period_start, period_end)
    kind, column, direction, page_limit, page_offset = periods.parse_chatbot_users_query(role, sort, order, limit, offset)
    as_of = queries.begin_request()
    body = _read(db, lambda: queries.chatbot_users(db, window, kind, column, direction, page_limit, page_offset),
                 queries.chatbot_users_unavailable("read_failed", kind, column, direction, page_limit, page_offset))
    return {**_header(window, db), "as_of": queries.iso(as_of), **body}


@router.post("/grading-runs", status_code=202)
def create_grading_run(body: GradingRunIn, admin: AuthUser = Depends(admin_user),
                       llm: LlmClient = Depends(get_llm_client), db: Session = Depends(get_session)):
    window = periods.parse_period(body.period_start, body.period_end)
    workflow = periods.parse_workflow(body.workflow)
    if privacy.privacy_mode() == "strict":
        raise ApiError(409, "privacy_grading_disabled", "AI grading is disabled because free-text privacy protection has not been approved.")
    if not privacy.privacy_ready():
        raise ApiError(503, "privacy_scanner_unavailable", "AI grading is unavailable because the local privacy scanner is not ready. Try again later.")
    _sweep()
    # Serialize admission as well as insertion: an empty first run can finish before
    # another insert, so the active-run index alone cannot enforce the hourly quota.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('analytics-grading-admission'))"))
    if db.scalar(select(Run.id).where(Run.status.in_(queries.ACTIVE_STATUSES)).limit(1)) is not None:
        raise ApiError(409, "grading_run_active", "A grading run is already in progress.")
    now = datetime.now(timezone.utc)
    recent = db.scalar(select(func.count()).select_from(Run).where(Run.created_at > now - timedelta(hours=1)))
    if recent >= config.GRADING_RUNS_PER_HOUR:
        raise ApiError(429, "grading_quota", "Grading run limit reached. Try again later.")
    # Stored text of ungraded items past retention is dropped; nothing else changes.
    db.execute(update(Item).where(Item.status.in_(queries.GRADABLE_STATUSES),
                                  Item.created_at < now - timedelta(days=config.CONTENT_RETENTION_DAYS))
               .values(request_text=None, response_text=None, context_text=None))
    eligible = (select(Item.id).where(*queries.eligible_clauses(workflow, window, now))
                .order_by(Item.received_at.desc(), Item.id.desc()).limit(config.GRADING_MAX_ITEMS).subquery())
    run = Run(workflow=workflow, period_start=window.period_start, period_end=window.period_end, status="queued",
              items_total=db.scalar(select(func.count()).select_from(eligible)), requested_by=admin.id)
    db.add(run)
    try:
        db.flush()
        db.commit()
    except IntegrityError:  # the partial unique index: another start won the race
        db.rollback()
        raise ApiError(409, "grading_run_active", "A grading run is already in progress.") from None
    db.refresh(run)
    payload = queries.run_object(run)
    jobs.start(run.id, llm, admin.id)
    return payload


@router.get("/grading-runs/{run_id}")
def get_grading_run(run_id: int, _: AuthUser = Depends(admin_user), db: Session = Depends(get_session)):
    _sweep()
    row = db.get(Run, run_id) if 0 < run_id <= _MAX_ID else None
    if row is None:
        raise ApiError(404, "run_not_found", "Grading run not found.")
    return queries.run_object(row)
