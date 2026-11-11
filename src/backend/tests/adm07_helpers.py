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


def get(path, user, win=None, **extra):
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
