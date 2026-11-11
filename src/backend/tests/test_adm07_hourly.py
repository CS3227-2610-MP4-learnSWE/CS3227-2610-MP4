"""ADM-07 AC11-AC13, AC38, AC39 for GET /api/admin/analytics/hourly (phase 2: chat plus generation tables).

Contract: workflow/specs/ADM-07/plan.md "GET /hourly", "Window rule and coverage", "In-progress rule".
"""
from datetime import datetime, timedelta, timezone

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, tracked_users  # noqa: F401
from adm01_grading_helpers import chat_row, gen_row, new_window
from adm02_helpers import actor
from adm07_helpers import HOURLY, fixed_now, recording_start, mirror_all, get, hour_labels, ok, stamp  # noqa: F401
from auth_helpers import call

CATS = {"timeout", "rate_limited", "invalid_output", "upstream", "unclassified"}
UTC = timezone.utc


def student(tracked):
    u = actor("student")
    tracked.append(u)
    return u


def teacher(tracked):
    u = actor("teacher")
    tracked.append(u)
    return u


def hourly(admin, w, **extra):
    return ok(HOURLY, admin, w, **extra)


def bucket(body, w, hour):
    return body["buckets"][hour]


def test_adm07_ac11_shape_dense_zero_filled_ordered_24_buckets_per_day(analytics_admin):
    w = new_window()
    body = hourly(analytics_admin, w)
    assert body["state"] == "available" and body["reason"] is None and body["retention_days"] == 30
    assert body["data_starts_on"] is None and body["in_progress"] == 0
    assert (body["period_start"], body["period_end"]) == (w.start, w.end)
    assert [b["hour_start"] for b in body["buckets"]] == hour_labels(w)
    assert body["totals"] == {"successful": 0, "failed": 0, "total": 0}
    for b in body["buckets"]:
        assert set(b) == {"hour_start", "successful", "failed", "total", "failure_rate_percent", "failed_by_category"}
        assert (b["successful"], b["failed"], b["total"]) == (0, 0, 0) and b["failure_rate_percent"] is None
        assert set(b["failed_by_category"]) == CATS and sum(b["failed_by_category"].values()) == 0


def test_adm07_ac11_three_day_period_has_72_buckets(analytics_admin):
    w = new_window(3)
    body = hourly(analytics_admin, w)
    assert len(body["buckets"]) == 72 and body["buckets"][-1]["hour_start"] == stamp(w.end_dt - timedelta(hours=1))


def test_adm07_ac11_chat_and_generation_are_combined_by_their_request_time(analytics_admin, tracked_users):
    w = new_window()
    s, t = student(tracked_users), teacher(tracked_users)
    chat_row(s, w.at(3 * 60 + 5), "success")
    chat_row(s, w.at(3 * 60 + 59, 59), "failure")
    gen_row(t, "study_notes", w.at(3 * 60 + 30), "success")
    gen_row(t, "mcq_batch", w.at(4 * 60), "failure")  # exactly 04:00:00 belongs to hour 4
    chat_row(s, w.at(23 * 60 + 59, 59), "success")
    body = hourly(analytics_admin, w)
    b3, b4, b23 = body["buckets"][3], body["buckets"][4], body["buckets"][23]
    assert (b3["successful"], b3["failed"], b3["total"], b3["failure_rate_percent"]) == (2, 1, 3, 33.3)
    assert (b4["successful"], b4["failed"], b4["total"], b4["failure_rate_percent"]) == (0, 1, 1, 100.0)
    assert (b23["successful"], b23["total"], b23["failure_rate_percent"]) == (1, 1, 0.0)
    assert body["totals"] == {"successful": 3, "failed": 2, "total": 5}
    assert sum(b["total"] for b in body["buckets"]) == 5


def test_adm07_ac11_rows_at_the_window_edges(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.start_dt - timedelta(seconds=1), "failure")
    chat_row(s, w.start_dt, "success")
    chat_row(s, w.end_dt - timedelta(seconds=1), "success")
    chat_row(s, w.end_dt, "failure")
    body = hourly(analytics_admin, w)
    assert body["totals"] == {"successful": 2, "failed": 0, "total": 2}
    assert body["buckets"][0]["total"] == 1 and body["buckets"][23]["total"] == 1


def test_adm07_ac11_failure_rate_is_rounded_half_up_to_one_decimal(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.at(1), "failure")
    for i in range(15):
        chat_row(s, w.at(2 + i), "success")  # 1/16 = 6.25 -> 6.3
    assert hourly(analytics_admin, w)["buckets"][0]["failure_rate_percent"] == 6.3


def test_adm07_ac13_phase4_category_breakdown_is_available_and_backfilled_style_failures_are_unclassified(analytics_admin, tracked_users):
    w = new_window()
    s, t = student(tracked_users), teacher(tracked_users)
    chat_row(s, w.at(1), "failure")
    chat_row(s, w.at(2), "failure")
    gen_row(t, "study_notes", w.at(3), "failure")
    chat_row(s, w.at(4), "success")
    body = hourly(analytics_admin, w)
    # PHASE 4 CHANGE (was: unavailable/not_collected): categories are real from request_log_categories_started_at.
    # Rows seeded without a hook carry the migration-backfill category `unclassified`, so the counts below stay.
    assert body["category_breakdown"]["state"] == "available" and body["category_breakdown"]["reason"] is None
    b = body["buckets"][0]
    assert b["failed"] == 3 and b["failed_by_category"]["unclassified"] == 3
    assert all(b["failed_by_category"][c] == 0 for c in CATS - {"unclassified"})
    assert sum(b["failed_by_category"].values()) == b["failed"]


# ------------------------------------------------------------------ AC38

def test_adm07_ac38_pending_rows_are_in_progress_then_timeouts_in_their_received_hour(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(10 * 60))  # 10:00:00
    chat_row(s, now - timedelta(seconds=119), "pending")  # 09:58:01, in progress
    chat_row(s, now - timedelta(seconds=120), "pending")  # 09:58:00, timeout failure in hour 9
    chat_row(s, w.at(2 * 60 + 1), "pending")  # long expired, hour 2
    body = hourly(analytics_admin, w)
    assert body["as_of"] == stamp(now) and body["in_progress"] == 1
    assert (body["buckets"][9]["failed"], body["buckets"][9]["total"]) == (1, 1)
    assert (body["buckets"][2]["failed"], body["buckets"][2]["total"]) == (1, 1)
    assert body["totals"] == {"successful": 0, "failed": 2, "total": 2}
    assert sum(b["failed_by_category"]["unclassified"] for b in body["buckets"]) == 2  # phase 2: unclassified


def test_adm07_ac38_tile_hourly_and_users_totals_agree_for_the_same_as_of(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    s, t = student(tracked_users), teacher(tracked_users)
    now = fixed_now(w.at(10 * 60))
    chat_row(s, w.at(30), "success")
    chat_row(s, w.at(31), "failure")
    chat_row(s, now - timedelta(seconds=500), "pending")
    chat_row(s, now - timedelta(seconds=10), "pending")
    gen_row(t, "study_notes", w.at(40), "failure")
    h = hourly(analytics_admin, w)
    hl = ok("/api/admin/analytics/health", analytics_admin, w)
    us = ok("/api/admin/analytics/chatbot-users", analytics_admin, w, role="student")
    assert h["as_of"] == hl["as_of"] == us["as_of"]
    assert h["in_progress"] == hl["chatbot_failure"]["in_progress"] + hl["generation_failure"]["in_progress"] \
        == us["in_progress"] == 1
    assert h["totals"]["total"] == hl["chatbot_failure"]["total"] + hl["generation_failure"]["total"] == 4
    assert h["totals"]["failed"] == hl["chatbot_failure"]["failed"] + hl["generation_failure"]["failed"] == 3
    assert us["totals"] == {"successful": 1, "unsuccessful": 2}


# ------------------------------------------------------------------ AC12 / AC39 coverage and retention

def test_adm07_ac12_whole_period_before_recording_is_unavailable_with_no_buckets(analytics_admin, recording_start):
    w = new_window(2)
    recording_start.set(w.end_dt + timedelta(days=5))
    body = hourly(analytics_admin, w)
    assert body["state"] == "unavailable" and body["reason"] == "period_before_recording"
    assert body["buckets"] == [] and body["totals"] is None


def test_adm07_ac39_period_starting_before_recording_returns_buckets_from_the_recording_date(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    s = student(tracked_users)
    recording_start.set(w.start_dt + timedelta(days=1, hours=7))
    covered_first = w.first + timedelta(days=1)
    chat_row(s, w.at(60), "failure")  # excluded
    chat_row(s, w.start_dt + timedelta(days=1, hours=2), "success")
    body = hourly(analytics_admin, w)
    assert body["state"] == "available" and body["data_starts_on"] == covered_first.isoformat()
    assert len(body["buckets"]) == 48
    assert body["buckets"][0]["hour_start"] == f"{covered_first.isoformat()}T00:00:00Z"
    assert body["totals"] == {"successful": 1, "failed": 0, "total": 1}


def test_adm07_ac12_period_starting_more_than_30_days_ago_starts_at_the_retention_floor(analytics_admin, recording_start):
    recording_start.set(datetime(2000, 1, 1, tzinfo=UTC))
    today = datetime.now(UTC).date()
    before = (datetime.now(UTC) - timedelta(days=30)).replace(minute=0, second=0, microsecond=0)
    r = call("GET", f"{HOURLY}?period_start={today - timedelta(days=40)}&period_end={today}", analytics_admin)
    after = (datetime.now(UTC) - timedelta(days=30)).replace(minute=0, second=0, microsecond=0)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "available"
    first = datetime.strptime(body["buckets"][0]["hour_start"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert before <= first <= after
    assert body["data_starts_on"] == first.date().isoformat()
    assert len(body["buckets"]) <= 744
    assert body["buckets"][-1]["hour_start"] == f"{today}T23:00:00Z"
    hours = [datetime.strptime(b["hour_start"], "%Y-%m-%dT%H:%M:%SZ") for b in body["buckets"]]
    assert all(b - a == timedelta(hours=1) for a, b in zip(hours, hours[1:]))


def test_adm07_ac12_a_period_entirely_older_than_30_days_is_beyond_retention(analytics_admin, recording_start):
    recording_start.set(datetime(2000, 1, 1, tzinfo=UTC))
    today = datetime.now(UTC).date()
    r = call("GET", f"{HOURLY}?period_start={today - timedelta(days=100)}&period_end={today - timedelta(days=60)}",
             analytics_admin)
    body = r.json()
    assert r.status_code == 200, r.text
    assert body["state"] == "unavailable" and body["reason"] == "beyond_retention"
    assert body["buckets"] == [] and body["totals"] is None


def test_adm07_ac12_a_period_entirely_in_the_distant_past_is_unavailable(analytics_admin):
    """Before recording and beyond retention at once: either reason is acceptable, never data or zero."""
    body = call("GET", f"{HOURLY}?period_start=2000-01-01&period_end=2000-01-31", analytics_admin).json()
    assert body["state"] == "unavailable" and body["reason"] in ("period_before_recording", "beyond_retention")
    assert body["buckets"] == [] and body["totals"] is None


def test_adm07_ac12_rows_older_than_the_retention_floor_are_ignored(analytics_admin, tracked_users, recording_start):
    recording_start.set(datetime(2000, 1, 1, tzinfo=UTC))
    s = student(tracked_users)
    today = datetime.now(UTC).date()
    url_ = f"{HOURLY}?period_start={today - timedelta(days=40)}&period_end={today}"
    before = call("GET", url_, analytics_admin).json()["totals"]
    chat_row(s, datetime.now(UTC) - timedelta(days=30, hours=2), "failure")
    mirror_all()  # phase 4 reads the request log; the row is older than the retention floor either way
    assert call("GET", url_, analytics_admin).json()["totals"] == before
