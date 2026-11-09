"""Durable recording and snapshot aggregation, independent of feature transactions."""
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from auth.db import engine_for
from auth.settings import load_settings
from ai_usage.models import ServiceAttempt, UsageCoverage

FEATURES = ("STU-03", "TEA-02", "ADM-03", "ADM-01")
TOKEN_FIELDS = ("input_tokens", "output_tokens", "total_tokens")
COUNT_FIELDS = ("requests", "failures", "rate_limit_failures", "other_failures")
MAX_TOKEN = 2**63 - 1
MAX_SAFE_INTEGER = 2**53 - 1


def valid_token(value: object) -> int | None:
    return value if type(value) is int and 0 <= value <= MAX_TOKEN else None


def _engine():
    return engine_for(load_settings().database_url)


def reserve_attempt(feature: str) -> UUID:
    if feature not in FEATURES:
        raise ValueError("Unsupported AI feature.")
    attempt_id = uuid4()
    with Session(_engine()) as db, db.begin():
        db.add(ServiceAttempt(id=attempt_id, feature=feature, started_at=func.clock_timestamp(), outcome="pending"))
    return attempt_id


def finish_attempt(attempt_id: UUID, outcome: str, *, input_tokens: int | None = None,
                   output_tokens: int | None = None, total_tokens: int | None = None) -> bool:
    if outcome not in ("success", "rate_limit", "other_failure"):
        raise ValueError("A terminal AI service outcome is required.")
    tokens = dict(zip(TOKEN_FIELDS, map(valid_token, (input_tokens, output_tokens, total_tokens))))
    with Session(_engine()) as db, db.begin():
        changed = db.execute(update(ServiceAttempt).where(
            ServiceAttempt.id == attempt_id, ServiceAttempt.outcome == "pending",
        ).values(outcome=outcome, finished_at=func.clock_timestamp(), **tokens).returning(ServiceAttempt.id)).first()
        if changed:
            return True
        row = db.get(ServiceAttempt, attempt_id)
        return bool(row and row.outcome == outcome and all(getattr(row, key) == value for key, value in tokens.items()))


def activate_coverage(features: list[str]) -> None:
    if not features or any(feature not in ("STU-03", "TEA-02") for feature in features):
        raise ValueError("Only integrated AI features may be activated.")
    with Session(_engine()) as db, db.begin():
        for feature in sorted(set(features)):
            db.execute(insert(UsageCoverage).values(feature=feature, enabled=False).on_conflict_do_nothing())
            row = db.scalar(select(UsageCoverage).where(UsageCoverage.feature == feature).with_for_update())
            if not row.enabled:
                # An existing historical start or gap must never be erased.
                # Obtain the timestamp before making the row dirty: a SELECT can
                # autoflush, and enabled coverage must already have a start.
                if row.covered_since is None:
                    row.covered_since = db.scalar(select(func.clock_timestamp()))
                row.enabled = True


def _timestamp(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None


def _metric(value: int | None = None, reason: str | None = None) -> dict:
    if value is not None and not 0 <= value <= MAX_SAFE_INTEGER:
        return {"value": None, "reason": "missing_measurement"}
    return {"value": value, "reason": reason}


def read_usage_report(feature: str, start_date: date, end_date: date) -> dict:
    wanted = FEATURES if feature == "all" else (feature,)
    if feature != "all" and feature not in FEATURES:
        raise ValueError("Unsupported AI feature.")
    start = datetime.combine(start_date, time.min, timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, timezone.utc)
    # A new connection establishes isolation before any query (auth uses a separate session).
    with _engine().connect().execution_options(isolation_level="REPEATABLE READ") as conn, conn.begin():
        as_of = conn.scalar(select(func.clock_timestamp()))
        end = min(end, as_of)
        coverage = {row.feature: row for row in conn.execute(select(UsageCoverage))}
        pending = or_(ServiceAttempt.outcome == "pending", ServiceAttempt.finished_at > as_of,
                      ServiceAttempt.finished_at.is_(None))
        columns = [ServiceAttempt.feature, func.count().label("requests"),
                   func.sum(case((pending, 1), else_=0)).label("pending"),
                   func.sum(case((ServiceAttempt.outcome == "rate_limit", 1), else_=0)).label("rate_limit_failures"),
                   func.sum(case((ServiceAttempt.outcome == "other_failure", 1), else_=0)).label("other_failures")]
        for field in TOKEN_FIELDS:
            column = getattr(ServiceAttempt, field)
            columns.extend([func.count(column).label(field + "_count"), func.sum(column).label(field)])
        aggregates = {row.feature: row for row in conn.execute(select(*columns).where(
            ServiceAttempt.feature.in_(wanted), ServiceAttempt.started_at >= start,
            ServiceAttempt.started_at < end,
        ).group_by(ServiceAttempt.feature))}
        rows = []
        for name in wanted:
            covered = coverage.get(name)
            counts = aggregates.get(name)
            row = {"feature": name, "coverage_start": _timestamp(covered.covered_since) if covered else None}
            reason = None
            if covered is None or not covered.enabled:
                reason = "not_enabled"
            elif covered.covered_since is None or start < covered.covered_since or (
                covered.incomplete_since is not None and covered.incomplete_since < end
            ):
                reason = "incomplete_coverage"
            elif counts and counts.pending:
                reason = "pending_attempts"
            if reason:
                row.update({key: _metric(reason=reason) for key in (*COUNT_FIELDS, *TOKEN_FIELDS)})
            else:
                requests = counts.requests if counts else 0
                limited = counts.rate_limit_failures if counts else 0
                other = counts.other_failures if counts else 0
                row.update({key: _metric(value) for key, value in zip(COUNT_FIELDS, (requests, limited + other, limited, other))})
                for field in TOKEN_FIELDS:
                    if not requests:
                        metric = _metric(reason="no_measurements")
                    elif getattr(counts, field + "_count") != requests:
                        metric = _metric(reason="missing_measurement")
                    else:
                        metric = _metric(int(getattr(counts, field)))
                    row[field] = metric
            rows.append(row)
        return {"feature": feature, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
                "timezone": "UTC", "as_of": _timestamp(as_of), "rows": rows}
