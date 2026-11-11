"""ADM-07 retention: delete expired request-log rows (30 days) and login events (400 days) in batches. Never raises."""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from auth.db import open_session
from feature_analytics import config
from feature_analytics.models import AnalyticsLoginEvent, AnalyticsRequestLog

log = logging.getLogger("feature_analytics")
_guard = threading.Lock()
_last_run: float | None = None  # time.monotonic() of the last throttled run in this process


def _purge(db, model, column, cutoff: datetime) -> int:
    total = 0
    while True:
        ids = db.scalars(select(model.id).where(column < cutoff).limit(config.PURGE_BATCH)).all()
        if not ids:
            return total
        total += db.execute(delete(model).where(model.id.in_(ids))).rowcount
        db.commit()


def purge_expired(now: datetime | None = None) -> dict[str, int]:
    """Counts deleted per table; empty counts of 0 on failure."""
    now = now or datetime.now(timezone.utc)
    result = {"request_log": 0, "login_events": 0}
    for name, model, column, days in (
            ("request_log", AnalyticsRequestLog, AnalyticsRequestLog.occurred_at, config.PURGE_REQUEST_LOG_DAYS),
            ("login_events", AnalyticsLoginEvent, AnalyticsLoginEvent.occurred_at, config.PURGE_LOGIN_EVENT_DAYS)):
        try:
            with open_session() as db:
                result[name] = _purge(db, model, column, now - timedelta(days=days))
        except Exception as exc:  # noqa: BLE001
            log.warning("analytics purge of %s failed, class=%s", name, type(exc).__name__)
    return result


def purge_if_due() -> None:
    """Called from the outcome hooks: runs purge_expired at most once per PURGE_INTERVAL_S per process."""
    global _last_run
    with _guard:
        current = time.monotonic()
        if _last_run is not None and current - _last_run < config.PURGE_INTERVAL_S:
            return
        _last_run = current
    purge_expired()
