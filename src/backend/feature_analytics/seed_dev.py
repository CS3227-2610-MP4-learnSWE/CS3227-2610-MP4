"""Development-only analytics seed: about a week of activity for the Feature Analytics hub.

Run after migrations and the other seeds:  uv run --env-file .env python -m feature_analytics.seed_dev
Refuses unless APP_ENV=development. Rows go through the real recording hooks with explicit past timestamps, so they
look exactly like recorded data. Applied once per database (marker in analytics_meta); `--force` adds another week.
The data is made up for local viewing only and is never created in any other environment.
"""
import os
import random
import sys
from collections.abc import Mapping
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from feature_analytics import recording
from feature_analytics.models import AnalyticsMeta
from feature_analytics.recording import (
    record_chat_request_outcome,
    record_chat_request_received,
    record_generation_accepted,
    record_generation_outcome,
    record_generation_rate_limited,
    record_login,
    record_practice_attempt_started,
    record_practice_attempt_submitted,
    record_practice_draft_started,
    record_practice_published,
)

MARKER = "dev_seed_applied_at"
STUDENT, TEACHER = "demo-student", "demo-teacher"
DAYS = 7
START_KEYS = ("recording_started_at", "request_log_started_at", "request_log_categories_started_at",
              "login_events_started_at", "practice_draft_started_started_at", "practice_published_started_at")
FAIL_CATEGORIES = ("timeout", "upstream", "invalid_output", "unclassified")
SET_ID = "77777777-7777-4777-8777-777777777774"  # the dev practice set of teacher_publications.seed


def _at(day: datetime, rng: random.Random) -> datetime:
    """A time on `day` between 01:00 and 14:00 UTC (09:00 to 22:00 in Singapore), never in the future."""
    return day + timedelta(hours=rng.randint(1, 14), minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))


def _move_start_keys(db: Session, window_start: datetime) -> None:
    """Let reports cover the seeded week: move each recording start back to the window start if it is later."""
    for key in START_KEYS:
        current = db.scalar(select(AnalyticsMeta.value).where(AnalyticsMeta.key == key))
        parsed = datetime.fromisoformat(current) if current else None
        if parsed is not None and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed is None or parsed > window_start:
            db.execute(pg_insert(AnalyticsMeta).values(key=key, value=window_start.isoformat())
                       .on_conflict_do_update(index_elements=["key"], set_={"value": window_start.isoformat()}))
    db.commit()


def _chat(rng: random.Random, when: datetime, activity_ref: str | None) -> None:
    request_id = record_chat_request_received(
        user_id=STUDENT, activity_type="practice_attempt" if activity_ref else None, activity_ref=activity_ref,
        received_at=when)
    ok = rng.random() < 0.96
    seconds = rng.uniform(1.5, 9.0) if ok else rng.choice((120.0, rng.uniform(3.0, 20.0)))
    category = None if ok else ("timeout" if seconds >= 120 else rng.choice(FAIL_CATEGORIES))
    record_chat_request_outcome(request_id, success=ok, completed_at=when + timedelta(seconds=seconds),
                                failure_category=category)


def _generation(rng: random.Random, when: datetime) -> None:
    workflow = rng.choice(recording.GENERATION_WORKFLOWS)
    if rng.random() < 0.02:
        record_generation_rate_limited(workflow=workflow, occurred_at=when)
        return
    attempt_id = record_generation_accepted(workflow=workflow, user_id=TEACHER, accepted_at=when)
    ok = rng.random() < 0.97
    seconds = rng.uniform(8.0, 40.0) if ok else rng.uniform(5.0, 60.0)
    record_generation_outcome(attempt_id, success=ok, completed_at=when + timedelta(seconds=seconds),
                              failure_category=None if ok else rng.choice(FAIL_CATEGORIES))


def seed_week(now: datetime, rng: random.Random) -> None:
    today = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    for offset in range(DAYS - 1, -1, -1):
        day = today - timedelta(days=offset)
        stamps = lambda n: sorted(t for t in (_at(day, rng) for _ in range(n)) if t < now)  # noqa: E731
        for when in stamps(rng.randint(2, 6)):
            record_login(user_id=STUDENT, role="student", occurred_at=when)
        for when in stamps(rng.randint(1, 3)):
            record_login(user_id=TEACHER, role="teacher", occurred_at=when)
        for index, started in enumerate(stamps(rng.randint(4, 8))):
            ref = f"dev-seed-attempt-{day:%Y%m%d}-{index}"
            record_practice_attempt_started(user_id=STUDENT, practice_set_id=SET_ID, attempt_ref=ref, started_at=started)
            for turn in range(rng.randint(0, 3)):
                _chat(rng, started + timedelta(minutes=2 + turn * 3), ref)
            if rng.random() < 0.7:
                record_practice_attempt_submitted(attempt_ref=ref, submitted_at=started + timedelta(minutes=rng.randint(6, 25)))
        for when in stamps(rng.randint(6, 16)):
            _chat(rng, when, None)
        for when in stamps(rng.randint(3, 9)):
            _generation(rng, when)
    for number, (started, published) in enumerate(((5, 4), (3, 2), (1, None)), start=1):
        set_id = f"dev-seed-set-{number}"
        record_practice_draft_started(practice_set_id=set_id, teacher_id=TEACHER,
                                      started_at=today - timedelta(days=started) + timedelta(hours=3))
        if published is not None:
            record_practice_published(practice_set_id=set_id, teacher_id=TEACHER,
                                      published_at=today - timedelta(days=published) + timedelta(hours=5))


def main(env: Mapping[str, str] = os.environ, argv: list[str] | None = None) -> int:
    if env.get("APP_ENV") != "development":
        print("The analytics seed is for development databases only (set APP_ENV=development).")
        return 1
    force = "--force" in (sys.argv[1:] if argv is None else argv)
    now = datetime.now(timezone.utc)
    with Session(create_engine(env["DATABASE_URL"])) as db:
        if not force and db.get(AnalyticsMeta, MARKER) is not None:
            print("analytics dev seed: already applied (use --force to add another week)")
            return 0
        _move_start_keys(db, datetime.combine(now.date() - timedelta(days=DAYS - 1), time.min, tzinfo=timezone.utc))
        seed_week(now, random.Random(now.date().toordinal()))
        db.execute(pg_insert(AnalyticsMeta).values(key=MARKER, value=now.isoformat())
                   .on_conflict_do_update(index_elements=["key"], set_={"value": now.isoformat()}))
        db.commit()
    print(f"analytics dev seed: added {DAYS} days of activity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
