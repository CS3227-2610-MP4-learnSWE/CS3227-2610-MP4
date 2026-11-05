"""Shared helpers for the ADM-01 analytics tests (contract: workflow/specs/ADM-01/plan.md).

Only the HTTP contract and the `analytics_event` table are used. Fixture rows live in
2022 so they never mix with events recorded "now" by the hooks.
"""
from urllib.parse import urlencode

import pytest
from auth_helpers import call, seeded, sql

URL = "/api/admin/analytics/summary"
INVALID_MESSAGE = ("Provide a valid reporting period: start and end dates as YYYY-MM-DD, "
                   "start not after end, at most 366 days.")
ALL_TYPES = [
    "chatbot_request", "practice_completed",
    "notes_generation_requested", "notes_generation_succeeded", "notes_generation_failed",
    "mcq_generation_requested", "mcq_generation_succeeded", "mcq_generation_failed",
]
FIXTURE_RANGE = ("2022-01-01T00:00:00Z", "2023-01-01T00:00:00Z")


def clean_fixture_rows():
    sql("DELETE FROM analytics_event WHERE occurred_at >= %s AND occurred_at < %s", FIXTURE_RANGE)


@pytest.fixture
def adm_clean():
    from auth_helpers import require_db

    require_db()
    clean_fixture_rows()
    yield
    clean_fixture_rows()


def insert(event_type, at, n=1):
    for _ in range(n):
        sql("INSERT INTO analytics_event(event_type, occurred_at) VALUES (%s, %s)", (event_type, at))


def seed_day(day, **counts):
    """counts keyed by event type; rows at 12:00Z of `day` (YYYY-MM-DD)."""
    for etype, n in counts.items():
        insert(etype, f"{day}T12:00:00Z", n)


def report(start=None, end=None, user=None, raw_query=None, role="admin"):
    who = user if user is not None else seeded(role)
    if raw_query is None:
        q = {k: v for k, v in (("start", start), ("end", end)) if v is not None}
        raw_query = urlencode(q)
    return call("GET", URL + ("?" + raw_query if raw_query else ""), who)


def ok_report(start, end):
    r = report(start, end)
    assert r.status_code == 200, r.text
    return r.json()


def max_id():
    return sql("SELECT coalesce(max(id), 0) FROM analytics_event")[0][0]


def events_since(last_id):
    return sql("SELECT id, event_type, occurred_at FROM analytics_event WHERE id > %s ORDER BY id",
               (last_id,))


def types_since(last_id):
    return [row[1] for row in events_since(last_id)]
