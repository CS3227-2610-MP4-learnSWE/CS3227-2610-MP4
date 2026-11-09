"""Background grading run, in the style of feedback_analysis/jobs.py: a daemon thread with its own database sessions,
conditional writes only, a monotonic start cutoff, an overall bound and a sweep for runs whose thread died."""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, update

from auth.db import open_session
from feature_analytics import config, grading, queries
from feature_analytics.grading import GradingInput, InvalidGraderOutput
from feature_analytics.models import AnalyticsGrade, AnalyticsGradingItem as Item, AnalyticsGradingRun as Run
from feature_analytics.periods import window_for
from llm_client import (
    LlmBadResponse, LlmBusy, LlmClient, LlmError, LlmInputTooLarge, LlmRateLimited, LlmTimeout, get_llm_client,
)

log = logging.getLogger("feature_analytics")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> float:
    """The job's clock (monotonic seconds). Tests may replace it to drive the time limits."""
    return time.monotonic()


def start(run_id: int, llm: LlmClient | None, admin_id: str) -> None:
    """Run the grading in a daemon thread so the POST returns at once."""
    threading.Thread(target=run_grading, args=(run_id, llm, admin_id), daemon=True, name=f"grading-{run_id}").start()


def _write_run(run_id: int, allowed: tuple[str, ...], **values) -> bool:
    """Conditional update: False means the run is no longer in one of the allowed states (for example swept)."""
    with open_session() as db:
        result = db.execute(update(Run).where(Run.id == run_id, Run.status.in_(allowed)).values(**values))
        db.commit()
        return result.rowcount > 0


def _end(run_id: int, status: str, failure_code: str | None = None) -> None:
    _write_run(run_id, queries.ACTIVE_STATUSES, status=status, failure_code=failure_code, finished_at=_utcnow())


def sweep_stuck_runs() -> None:
    """A queued or running run older than GRADING_RUN_EXPIRY_S has lost its thread: fail it with run_expired."""
    cutoff = _utcnow() - timedelta(seconds=config.GRADING_RUN_EXPIRY_S)
    with open_session() as db:
        db.execute(update(Run).where(Run.status.in_(queries.ACTIVE_STATUSES), Run.created_at < cutoff)
                   .values(status="failed", failure_code="run_expired", finished_at=_utcnow()))
        db.commit()


def _load(run_id: int) -> list[GradingInput] | None:
    """The run's eligible items (newest first, at most GRADING_MAX_ITEMS), or None if the run is gone."""
    with open_session() as db:
        run = db.get(Run, run_id)
        if run is None:
            return None
        window = window_for(run.period_start, run.period_end)
        rows = db.execute(
            select(Item.id, Item.workflow, Item.generation_workflow, Item.request_text, Item.response_text,
                   Item.context_text)
            .where(*queries.eligible_clauses(run.workflow, window, _utcnow()))
            .order_by(Item.received_at.desc(), Item.id.desc()).limit(config.GRADING_MAX_ITEMS)
        ).all()
        return [GradingInput(r.id, r.workflow, r.generation_workflow, r.request_text, r.response_text, r.context_text)
                for r in rows]


def _store_grades(item_id: int, grades) -> bool:
    """Grades and the status change in one transaction; the item's text is dropped with it."""
    with open_session() as db:
        done = db.execute(
            update(Item).where(Item.id == item_id, Item.status.in_(queries.GRADABLE_STATUSES))
            .values(status="graded", failure_code=None, graded_at=_utcnow(), request_text=None, response_text=None,
                    context_text=None)
        )
        if done.rowcount == 0:
            db.rollback()
            return False
        db.execute(insert(AnalyticsGrade), [
            {"item_id": item_id, "dimension": g.dimension, "state": g.state, "score": g.score, "reason": g.reason}
            for g in grades
        ])
        db.commit()
        return True


def _mark_failed(item_id: int) -> None:
    with open_session() as db:
        db.execute(update(Item).where(Item.id == item_id, Item.status.in_(queries.GRADABLE_STATUSES))
                   .values(status="grading_failed", failure_code="invalid_ai_output"))
        db.commit()


def _stop_code(exc: LlmError) -> str:
    if isinstance(exc, (LlmRateLimited, LlmBusy)):
        return "ai_rate_limited"
    if isinstance(exc, LlmTimeout):
        return "ai_timeout"
    return "ai_unavailable"


def run_grading(run_id: int, llm: LlmClient | None, admin_id: str) -> None:
    """Thread body: always ends the run in a stored state."""
    phase = {"code": "context_load_failed"}
    try:
        _run(run_id, llm, admin_id, phase)
    except Exception as exc:  # noqa: BLE001 - the run must end in a stored state
        log.warning("grading run %s failed, class=%s", run_id, type(exc).__name__)
        try:
            _end(run_id, "failed", phase["code"])
        except Exception:  # noqa: BLE001
            log.error("grading run %s could not store its failure", run_id)


def _run(run_id: int, llm: LlmClient | None, admin_id: str, phase: dict) -> None:
    started = _now()
    if not _write_run(run_id, ("queued",), status="running", started_at=_utcnow()):
        return
    items = _load(run_id)
    if items is None:
        return
    if not _write_run(run_id, ("running",), items_total=len(items)):
        return
    llm = llm or get_llm_client()
    graded = failed = 0
    for item in items:
        elapsed = _now() - started
        if elapsed >= config.GRADING_JOB_BOUND_S:
            _end(run_id, "failed", "run_expired")
            return
        if elapsed >= config.GRADING_AI_START_LIMIT_S:
            break  # no call may start this late; the remaining items stay for the next run
        phase["code"] = "ai_unavailable"
        try:
            grades = grading.grade_one(llm, item, admin_id)
        except (InvalidGraderOutput, LlmBadResponse, LlmInputTooLarge):  # LlmReplyCutOff is a LlmBadResponse
            outcome = None
        except LlmError as exc:
            _end(run_id, "failed", _stop_code(exc))
            return
        else:
            outcome = grades
        phase["code"] = "save_failed"
        if outcome is None:
            _mark_failed(item.id)
            failed += 1
        elif _store_grades(item.id, outcome):
            graded += 1
        if not _write_run(run_id, ("running",), items_graded=graded, items_failed=failed):
            return
    _end(run_id, "completed")
