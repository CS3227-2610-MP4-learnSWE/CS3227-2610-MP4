"""ADM-07 phase 4 helpers. Contract: workflow/specs/ADM-07/plan.md "[P4]" sections only.

Rows are written through the documented hooks (`feature_analytics.recording`) or inserted directly into the
four new tables; reports are read through the HTTP endpoints. Every report test works in its own far-future
UTC window (adm01_grading_helpers.Window), so counts are exact. No test reaches the SoC LLM.
"""
import pytest

from auth_helpers import sql

NEW_TABLES = ("analytics_request_log", "analytics_login_event", "analytics_practice_draft_started",
              "analytics_practice_published")
META_KEYS = ("request_log_started_at", "login_events_started_at", "practice_draft_started_started_at",
             "practice_published_started_at", "request_log_categories_started_at")
CATEGORIES = ("timeout", "rate_limited", "invalid_output", "upstream", "unclassified")


@pytest.fixture
def meta():
    """`meta.set(key, datetime)` moves an analytics_meta key; every key touched is restored afterwards."""
    old = {}

    class Meta:
        def set(self, key, when):
            if key not in old:
                rows = sql("SELECT value FROM analytics_meta WHERE key=%s", (key,))
                old[key] = rows[0][0] if rows else None
            sql("UPDATE analytics_meta SET value=%s WHERE key=%s", (when.isoformat(), key))

        def get(self, key):
            return sql("SELECT value FROM analytics_meta WHERE key=%s", (key,))[0][0]

    yield Meta()
    for key, value in old.items():
        if value is not None:
            sql("UPDATE analytics_meta SET value=%s WHERE key=%s", (value, key))


def max_log_id():
    return sql("SELECT coalesce(max(id),0) FROM analytics_request_log")[0][0]


def new_log_rows(since):
    """[(kind, source_id, outcome, failure_category)] of request-log rows created after `since`, oldest first."""
    return sql("SELECT kind, source_id, outcome, failure_category FROM analytics_request_log WHERE id > %s "
               "ORDER BY id", (since,))


def log_row(kind, source_id):
    rows = sql("SELECT outcome, failure_category, duration_ms, occurred_at FROM analytics_request_log "
               "WHERE kind=%s AND source_id=%s", (kind, source_id))
    return rows


def insert_log(kind, at, outcome="failure", category="rate_limited", duration_ms=None, source_id=None):
    sql("INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms) "
        "VALUES (%s,%s,%s,%s,%s,%s)", (kind, source_id, at, outcome, category, duration_ms))


def login_events(user):
    return sql("SELECT role, occurred_at FROM analytics_login_event WHERE user_id=%s ORDER BY id", (str(user),))


def drop_events(users=(), sets=()):
    if users:
        sql("DELETE FROM analytics_login_event WHERE user_id = ANY(%s)", ([str(u) for u in users],))
    if sets:
        sql("DELETE FROM analytics_practice_draft_started WHERE practice_set_id = ANY(%s)", (list(sets),))
        sql("DELETE FROM analytics_practice_published WHERE practice_set_id = ANY(%s)", (list(sets),))


@pytest.fixture
def event_cleanup():
    """Tests append users and practice-set ids; their login/draft/published rows are removed afterwards."""
    box = {"users": [], "sets": []}
    yield box
    drop_events(box["users"], box["sets"])
