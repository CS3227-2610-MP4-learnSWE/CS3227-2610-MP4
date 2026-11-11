"""One-off, destructive, human-approved cleanup of stale `pending` AI usage attempts (ADM-07 plan, AC42).

    uv run python -m ai_usage.cleanup --dry-run
    uv run python -m ai_usage.cleanup --apply --approved-by <name>

Deletes every `pending` row of `ai_service_attempts` that started more than 24 hours ago, permanently (no archive, no
restore), and for each affected feature clears `incomplete_since` and moves `covered_since` to the next UTC midnight
(never earlier). Terminal rows and newer attempts are never touched. Not an Alembic revision.
"""
import argparse
import logging
import sys
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ai_usage.models import ServiceAttempt, UsageCoverage
from auth.db import engine_for
from auth.settings import load_settings

AI_USAGE_STALE_PENDING_HOURS = 24
log = logging.getLogger("ai_usage.cleanup")


def _next_midnight(now: datetime) -> datetime:
    return datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _stale(cutoff: datetime) -> list:
    return [ServiceAttempt.outcome == "pending", ServiceAttempt.started_at < cutoff]


def plan(db: Session, now: datetime) -> list[dict]:
    """Per feature: stale pending count, oldest and newest start, and current versus would-be coverage."""
    cutoff = now - timedelta(hours=AI_USAGE_STALE_PENDING_HOURS)
    found = {f: (n, first, last) for f, n, first, last in db.execute(
        select(ServiceAttempt.feature, func.count(), func.min(ServiceAttempt.started_at),
               func.max(ServiceAttempt.started_at)).where(*_stale(cutoff)).group_by(ServiceAttempt.feature))}
    coverage = {c.feature: c for c in db.scalars(select(UsageCoverage))}
    rows = []
    for feature in sorted(set(found) | set(coverage)):
        count, first, last = found.get(feature, (0, None, None))
        row = coverage.get(feature)
        covered, incomplete = (row.covered_since, row.incomplete_since) if row else (None, None)
        touched = row is not None and (count > 0 or incomplete is not None)
        rows.append({
            "feature": feature, "cutoff": cutoff, "pending_to_delete": count, "oldest": first, "newest": last,
            "covered_since": covered, "incomplete_since": incomplete,
            "new_covered_since": max(filter(None, (covered, _next_midnight(now)))) if touched else covered,
            "new_incomplete_since": None if touched else incomplete,
        })
    return rows


def _show(rows: list[dict]) -> None:
    for r in rows:
        print(f"{r['feature']}: cutoff={r['cutoff'].isoformat()} pending_to_delete={r['pending_to_delete']} "
              f"oldest={r['oldest']} newest={r['newest']} covered_since={r['covered_since']} -> {r['new_covered_since']} "
              f"incomplete_since={r['incomplete_since']} -> {r['new_incomplete_since']}")


def apply(db: Session, now: datetime, approved_by: str) -> dict[str, int]:
    """Delete the stale pending rows and reset coverage in one transaction; returns deleted counts per feature."""
    if not approved_by or not approved_by.strip():
        raise ValueError("--approved-by is required with --apply.")
    try:
        rows = plan(db, now)
        _show(rows)
        deleted: dict[str, int] = {}
        for (feature,) in db.execute(delete(ServiceAttempt).where(*_stale(now - timedelta(hours=AI_USAGE_STALE_PENDING_HOURS)))
                                     .returning(ServiceAttempt.feature)):
            deleted[feature] = deleted.get(feature, 0) + 1
        for r in rows:
            coverage = db.get(UsageCoverage, r["feature"], with_for_update=True)
            if coverage is not None and (deleted.get(r["feature"]) or coverage.incomplete_since is not None):
                coverage.incomplete_since = None
                coverage.covered_since = max(filter(None, (coverage.covered_since, _next_midnight(now))))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="print what would change; change nothing")
    mode.add_argument("--apply", action="store_true", help="delete permanently; needs --approved-by")
    parser.add_argument("--approved-by", default="", help="name of the human who approved the dry-run output")
    args = parser.parse_args(argv)
    if args.apply and not args.approved_by.strip():
        parser.error("--approved-by is required with --apply.")
    now = datetime.now(timezone.utc)
    with Session(engine_for(load_settings().database_url)) as db:
        if args.dry_run:
            _show(plan(db, now))
            return 0
        counts = apply(db, now, args.approved_by.strip())
    print(f"Deleted pending attempts: {counts or 'none'}")
    log.warning("ai usage cleanup applied by %s, deleted=%s", args.approved_by.strip(), counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
