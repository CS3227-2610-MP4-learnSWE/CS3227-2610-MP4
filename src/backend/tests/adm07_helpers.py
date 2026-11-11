"""ADM-07 independent helpers. Contract only: workflow/specs/ADM-07/plan.md (phase 2 endpoints).

Every test works in its own far-future UTC window (adm01_grading_helpers.Window) so counts are exact.
Rows are seeded through the documented existing tables (analytics_chat_request,
analytics_generation_attempt, analytics_practice_attempt). The clock seam named by the plan is
`feature_analytics.queries.utcnow`; `fixed_now` replaces it so the 120-second in-progress rule is exact.
No test reaches the SoC LLM (these endpoints call no AI; hooks and grading are never started here).
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

from adm01_grading_helpers import chat_row, gen_row, new_window  # noqa: F401  (re-exported)
from adm01_helpers import url
from auth_helpers import call, sql

BASE = "/api/admin/analytics"
HEALTH, HOURLY, DAILY, USERS = BASE + "/health", BASE + "/hourly", BASE + "/daily", BASE + "/chatbot-users"
NEW_ENDPOINTS = [HEALTH, HOURLY, DAILY, USERS]
UTC = timezone.utc

ERRORS = {
    "invalid_date": (422, "Enter dates as YYYY-MM-DD."),
    "period_order": (422, "The start date must be on or before the end date."),
    "period_too_long": (422, "The period can be at most 366 days."),
    "invalid_role": (422, "Choose student or teacher."),
    "invalid_sort": (422, "Choose a valid sort column and order."),
    "invalid_paging": (422, "limit must be 1 to 100 and offset must be 0 or more."),
    "invalid_include_rows": (422, "include_rows must be true or false."),
}

STATES = {"available", "not_applicable", "unavailable"}


def err(r, code):
    status, message = ERRORS[code]
    assert r.status_code == status, (r.status_code, r.text)
    assert r.json() == {"detail": {"code": code, "message": message}}, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers


MIRROR_CHAT = (
    "INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms) "
    "SELECT 'chatbot', id, received_at, outcome, CASE WHEN outcome='failure' THEN 'unclassified' END, duration_ms "
    "FROM analytics_chat_request WHERE received_at >= '2039-01-01' OR received_at > now() - interval '45 days' "
    "ON CONFLICT DO NOTHING")
MIRROR_GEN = (
    "INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms) "
    "SELECT CASE workflow WHEN 'study_notes' THEN 'generation_notes' ELSE 'generation_mcq' END, id, accepted_at, "
    "outcome, CASE WHEN outcome='failure' THEN 'unclassified' END, duration_ms "
    "FROM analytics_generation_attempt WHERE accepted_at >= '2039-01-01' OR accepted_at > now() - interval '45 days' "
    "ON CONFLICT DO NOTHING")


def mirror_all():
    """Phase 4 reads analytics_request_log. Tests that seed the source tables directly (as in phase 2, no hook
    runs) get the equivalent log row, exactly what the migration backfill would write (failures unclassified).
    Idempotent; rows that already have a log row (written by a hook) are left alone."""
    sql(MIRROR_CHAT)
    sql(MIRROR_GEN)


class P4RecordingStart:
    """Moves recording_started_at and the request-log start keys together (phase 4 hourly/health read the log)."""

    KEYS = ("recording_started_at", "request_log_started_at", "request_log_categories_started_at")

    def __init__(self):
        self.old = {k: (sql("SELECT value FROM analytics_meta WHERE key=%s", (k,)) or [[None]])[0][0] for k in self.KEYS}

    def set(self, when):
        for k in self.KEYS:
            sql("UPDATE analytics_meta SET value=%s WHERE key=%s", (when.isoformat(), k))

    def restore(self):
        for k, v in self.old.items():
            if v is not None:
                sql("UPDATE analytics_meta SET value=%s WHERE key=%s", (v, k))


@pytest.fixture
def recording_start():
    holder = P4RecordingStart()
    yield holder
    holder.restore()


def get(path, user, win=None, **extra):
    mirror_all()
    params = dict(win.params) if win is not None else {}
    params.update(extra)
    return call("GET", url(path, **params), user)


def ok(path, user, win, **extra):
    r = get(path, user, win, **extra)
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    return r.json()


def stamp(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def fixed_now(monkeypatch):
    """Returns `set(dt)`; replaces feature_analytics.queries.utcnow (plan: In-progress rule)."""
    from feature_analytics import queries

    def set_now(dt):
        monkeypatch.setattr(queries, "utcnow", lambda: dt)
        return dt

    return set_now


def bulk_chat(user, at, outcome, n, *, duration_ms=1000, step_s=1):
    """n student chat rows starting at `at`, `step_s` seconds apart, one statement."""
    done = outcome != "pending"
    sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, "
        "completed_at, duration_ms, outcome) SELECT %s,'student','practice_attempt','att-seed', "
        "%s::timestamptz + make_interval(secs => g * %s), "
        "CASE WHEN %s THEN %s::timestamptz + make_interval(secs => g * %s) + make_interval(secs => %s / 1000.0) END, "
        "CASE WHEN %s THEN %s END, %s FROM generate_series(0, %s) g",
        (str(user), at, step_s, done, at, step_s, duration_ms, done, duration_ms, outcome, n - 1))


def chat_null_duration_failure(user, at):
    return sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, "
               "completed_at, duration_ms, outcome) VALUES (%s,'student','lesson',NULL,%s,NULL,NULL,'failure') "
               "RETURNING id", (str(user), at))[0][0]


def hour_labels(w, hours=None):
    n = hours if hours is not None else int((w.end_dt - w.start_dt).total_seconds() // 3600)
    return [stamp(w.start_dt + timedelta(hours=i)) for i in range(n)]


def all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from all_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from all_keys(v)


def assert_iso_z(value):
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value), value
