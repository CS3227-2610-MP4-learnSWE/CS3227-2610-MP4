"""ADM-07 AC5-AC9, AC38, AC39 for GET /api/admin/analytics/health (phase 2, existing tables).

Contract: workflow/specs/ADM-07/plan.md "GET /health", "In-progress rule", "Window rule and coverage".
"""
from datetime import timedelta
from decimal import Decimal

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, tracked_users  # noqa: F401
from adm01_grading_helpers import attempt_row, chat_row, gen_row, new_window
from adm02_helpers import actor, uid
from adm07_helpers import (HEALTH, recording_start, mirror_all, bulk_chat, chat_null_duration_failure, fixed_now, get, ok, stamp)  # noqa: F401
from auth_helpers import call, sql


def student(tracked):
    u = actor("student")
    tracked.append(u)
    return u


def teacher(tracked):
    u = actor("teacher")
    tracked.append(u)
    return u


def health(admin, w, **extra):
    return ok(HEALTH, admin, w, **extra)


# ------------------------------------------------------------------ AC6 severity (unit and HTTP)

SEVERITY_CASES = [(19, 19, "low_sample"), (20, 0, "ok"), (20, 1, "warning"), (20, 2, "critical"), (50, 1, "warning"),
                  (51, 1, "ok"), (100, 5, "warning"), (100, 6, "critical"), (19, 0, "low_sample"), (20, 20, "critical")]


@pytest.mark.parametrize("total,failed,expected", SEVERITY_CASES)
def test_adm07_ac6_severity_unit(total, failed, expected):
    from feature_analytics.health import severity

    assert severity(failed, total) == expected


def test_adm07_ac6_severity_zero_total_is_none_and_threshold_is_a_parameter():
    from feature_analytics.health import severity

    assert severity(0, 0) is None
    assert severity(0, 5, 5) == "ok" and severity(0, 4, 5) == "low_sample"


@pytest.mark.parametrize("total,failed,expected", SEVERITY_CASES[:8])
def test_adm07_ac6_chatbot_severity_over_http(total, failed, expected, analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    if failed:
        bulk_chat(s, w.at(1), "failure", failed)
    if total - failed:
        bulk_chat(s, w.at(300), "success", total - failed)
    tile = health(analytics_admin, w)["chatbot_failure"]
    assert tile["state"] == "available" and tile["reason"] is None
    assert (tile["total"], tile["failed"], tile["in_progress"]) == (total, failed, 0)
    assert tile["severity"] == expected
    assert tile["rate_percent"] == round(failed * 100 / total + 1e-9, 1)


def test_adm07_ac6_exact_counts_not_the_rounded_percentage_decide_severity(analytics_admin, tracked_users):
    """51 requests with 1 failure is 1.96% (ok); 50 with 1 is exactly 2.0% (warning)."""
    w = new_window()
    s = student(tracked_users)
    bulk_chat(s, w.at(1), "failure", 1)
    bulk_chat(s, w.at(300), "success", 50)
    tile = health(analytics_admin, w)["chatbot_failure"]
    assert tile["total"] == 51 and tile["severity"] == "ok" and tile["rate_percent"] == 2.0


def test_adm07_ac6_rate_is_rounded_half_up_to_one_decimal(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    bulk_chat(s, w.at(1), "failure", 1)
    bulk_chat(s, w.at(300), "success", 15)  # 1/16 = 6.25 -> 6.3 (half up, not banker's)
    assert health(analytics_admin, w)["chatbot_failure"]["rate_percent"] == 6.3


def test_adm07_ac6_round_half_up_unit():
    from feature_analytics.health import round_half_up

    assert round_half_up(6.25, 1) == 6.3
    assert round_half_up(Decimal("2.25"), 1) == 2.3
    assert round_half_up(0.0, 1) == 0.0
    assert round_half_up(1.2, 0) == 1.0 and round_half_up(1.5, 0) == 2.0


# ------------------------------------------------------------------ percentile unit (AC8)

@pytest.mark.parametrize("n,expected_index", [(1, 0), (2, 1), (20, 18), (21, 19), (100, 94), (101, 95)])
def test_adm07_ac8_nearest_rank_percentile_unit(n, expected_index):
    from feature_analytics.health import percentile_nearest_rank

    values = list(range(1, n + 1))
    assert percentile_nearest_rank(values, 95) == values[expected_index]


def test_adm07_ac8_percentile_of_nothing_is_none():
    from feature_analytics.health import percentile_nearest_rank

    assert percentile_nearest_rank([], 95) is None
    assert percentile_nearest_rank([7], 95) == 7 and percentile_nearest_rank([7], 50) == 7


# ------------------------------------------------------------------ AC5 shape, states, per-metric failure

TOP = {"period_start", "period_end", "recording_started_on", "data_starts_on", "as_of", "low_sample_threshold",
       "chatbot_failure", "generation_failure", "rate_limited", "chatbot_response_time", "generation_response_time",
       "practice_completion"}


def test_adm07_ac5_exact_top_level_shape_and_empty_period_states(analytics_admin):
    w = new_window()
    body = health(analytics_admin, w)
    assert set(body) == TOP, set(body) ^ TOP
    assert body["low_sample_threshold"] == 20 and body["data_starts_on"] is None
    assert (body["period_start"], body["period_end"]) == (w.start, w.end)
    c, g = body["chatbot_failure"], body["generation_failure"]
    assert c["state"] == "not_applicable" and c["reason"] == "no_chat_requests"
    assert c["severity"] is None and c["rate_percent"] is None and c["total"] == 0 and c["failed"] == 0
    assert g["state"] == "not_applicable" and g["reason"] == "no_generation_attempts"
    assert g["severity"] is None and g["rate_percent"] is None and g["includes_rate_limited"] is True  # PHASE 4 CHANGE (was False)
    pc = body["practice_completion"]
    assert pc["state"] == "not_applicable" and pc["reason"] == "no_practice_attempts" and pc["percentage"] is None
    for key, reason in (("chatbot_response_time", "no_chat_requests"), ("generation_response_time", "no_generation_attempts")):
        rt = body[key]
        assert rt["state"] == "not_applicable" and rt["reason"] == reason
        for name in ("all", "successful", "failed"):
            assert rt[name] == {"count": 0, "median_ms": None, "p95_ms": None}


def test_adm07_ac10_phase4_rate_limited_with_no_requests_is_available_zero(analytics_admin):
    """PHASE 4 CHANGE (was unavailable/not_collected): a collected metric with nothing to count is a real 0."""
    w = new_window()
    rl = health(analytics_admin, w)["rate_limited"]
    assert rl["state"] == "available" and rl["reason"] is None
    assert rl["count"] == 0 and rl["total_requests"] == 0 and rl["since"] is not None


def test_adm07_ac5_generation_failure_without_rate_limited_requests_reports_includes_rate_limited_true(analytics_admin, tracked_users):
    w = new_window()
    t = teacher(tracked_users)
    gen_row(t, "study_notes", w.at(1), "success")
    gen_row(t, "mcq_batch", w.at(2), "failure")
    gen_row(t, "mcq_batch", w.at(3), "success")
    g = health(analytics_admin, w)["generation_failure"]
    assert g["state"] == "available"
    assert (g["total"], g["failed"], g["in_progress"]) == (3, 1, 0)
    assert g["includes_rate_limited"] is True  # PHASE 4 CHANGE (was False) and g["severity"] == "low_sample" and g["rate_percent"] == 33.3


def test_adm07_ac5_practice_completion_equals_the_usage_report_definition(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.at(10), w.at(20))
    attempt_row(s, "att-" + uid(), w.at(11))
    attempt_row(s, "att-" + uid(), w.at(12), w.end_dt + timedelta(hours=1))  # submitted after the period
    pc = health(analytics_admin, w)["practice_completion"]
    usage = ok("/api/admin/analytics/usage", analytics_admin, w)["practice_completion"]
    for key in ("state", "reason", "started", "submitted", "percentage"):
        assert pc[key] == usage[key], key
    assert (pc["started"], pc["submitted"], pc["percentage"]) == (3, 1, 33.3)


@pytest.mark.parametrize("failing,key", [("health_chatbot", "chatbot_failure"), ("health_generation", "generation_failure"),
                                         ("health_rate_limited", "rate_limited"),
                                         ("health_chatbot_response_time", "chatbot_response_time"),
                                         ("health_generation_response_time", "generation_response_time"),
                                         ("practice_completion", "practice_completion")])
def test_adm07_ac5_one_failing_read_makes_only_that_metric_read_failed(failing, key, analytics_admin, tracked_users, monkeypatch):
    from feature_analytics import queries

    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.at(1))
    gen_row(teacher(tracked_users), "study_notes", w.at(2))
    attempt_row(s, "att-" + uid(), w.at(1), w.at(2))

    def boom(*a, **k):
        raise RuntimeError("simulated read failure")

    monkeypatch.setattr(queries, failing, boom)
    mirror_all()
    r = call("GET", f"/api/admin/analytics/health?period_start={w.start}&period_end={w.end}", analytics_admin)
    assert r.status_code == 200, r.text
    assert "simulated read failure" not in r.text
    body = r.json()
    assert body[key]["state"] == "unavailable" and body[key]["reason"] == "read_failed"
    for other in ("chatbot_failure", "generation_failure", "chatbot_response_time", "generation_response_time",
                  "practice_completion"):
        if other != key:
            assert body[other]["state"] in ("available", "not_applicable"), other
    if key == "chatbot_failure":
        assert body[key]["total"] is None and body[key]["failed"] is None and body[key]["rate_percent"] is None
    if key == "practice_completion":
        assert body[key]["started"] is None and body[key]["percentage"] is None


# ------------------------------------------------------------------ AC8 response times

def test_adm07_ac8_three_sets_with_median_and_p95_and_all_is_their_union(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    for i, ms in enumerate((1000, 2000, 3000, 4000)):
        chat_row(s, w.at(i + 1), "success", duration_ms=ms)
    chat_row(s, w.at(10), "failure", duration_ms=500)
    chat_row(s, w.at(11), "failure", duration_ms=700)
    rt = health(analytics_admin, w)["chatbot_response_time"]
    assert rt["state"] == "available" and rt["reason"] is None
    assert rt["successful"] == {"count": 4, "median_ms": 2500, "p95_ms": 4000}
    assert rt["failed"] == {"count": 2, "median_ms": 600, "p95_ms": 700}
    assert rt["all"]["count"] == 6 == rt["successful"]["count"] + rt["failed"]["count"]
    assert rt["all"]["median_ms"] == 1500 and rt["all"]["p95_ms"] == 4000  # sorted 500 700 1000 2000 3000 4000


def test_adm07_ac8_median_rounds_half_up_to_whole_milliseconds(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.at(1), "success", duration_ms=1000)
    chat_row(s, w.at(2), "success", duration_ms=1001)
    assert health(analytics_admin, w)["chatbot_response_time"]["successful"]["median_ms"] == 1001


@pytest.mark.parametrize("n,median,p95", [(1, 100, 100), (20, 1050, 1900), (21, 1100, 2000), (100, 5050, 9500)])
def test_adm07_ac8_nearest_rank_p95_over_http(n, median, p95, analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    if n <= 21:
        for i in range(n):
            chat_row(s, w.at(i + 1), "success", duration_ms=(i + 1) * 100)
    else:
        sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, "
            "completed_at, duration_ms, outcome) SELECT %s,'student','practice_attempt','att-seed', "
            "%s::timestamptz + make_interval(secs => g), %s::timestamptz + make_interval(secs => g + 1), "
            "(g + 1) * 100, 'success' FROM generate_series(0, 99) g", (str(s), w.at(1), w.at(1)))
    got = health(analytics_admin, w)["chatbot_response_time"]["successful"]
    assert got == {"count": n, "median_ms": median, "p95_ms": p95}


def test_adm07_ac8_workflows_are_never_mixed(analytics_admin, tracked_users):
    w = new_window()
    s, t = student(tracked_users), teacher(tracked_users)
    chat_row(s, w.at(1), "success", duration_ms=1000)
    gen_row(t, "study_notes", w.at(2), "success", duration_ms=60000)
    gen_row(t, "mcq_batch", w.at(3), "failure", duration_ms=90000)
    body = health(analytics_admin, w)
    assert body["chatbot_response_time"]["all"] == {"count": 1, "median_ms": 1000, "p95_ms": 1000}
    g = body["generation_response_time"]
    assert g["successful"] == {"count": 1, "median_ms": 60000, "p95_ms": 60000}
    assert g["failed"] == {"count": 1, "median_ms": 90000, "p95_ms": 90000}
    assert g["all"]["count"] == 2 and g["all"]["median_ms"] == 75000
    assert body["chatbot_failure"]["total"] == 1 and body["generation_failure"]["total"] == 2


def test_adm07_ac8_failure_without_a_duration_counts_as_failed_request_but_is_in_no_time_set(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.at(1), "success", duration_ms=2000)
    chat_null_duration_failure(s, w.at(2))
    body = health(analytics_admin, w)
    assert (body["chatbot_failure"]["total"], body["chatbot_failure"]["failed"]) == (2, 1)
    rt = body["chatbot_response_time"]
    assert rt["failed"] == {"count": 0, "median_ms": None, "p95_ms": None}
    assert rt["all"]["count"] == 1 == rt["successful"]["count"]


def test_adm07_ac8_an_empty_selected_set_has_null_times_not_zero(analytics_admin, tracked_users):
    w = new_window()
    chat_row(student(tracked_users), w.at(1), "success", duration_ms=1500)
    rt = health(analytics_admin, w)["chatbot_response_time"]
    assert rt["failed"] == {"count": 0, "median_ms": None, "p95_ms": None}
    assert rt["state"] == "available"


# ------------------------------------------------------------------ AC38 in-progress rule

def test_adm07_ac38_pending_under_120s_is_in_progress_and_at_120s_is_a_timeout_failure(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(600))
    chat_row(s, now - timedelta(seconds=119), "pending")
    chat_row(s, now - timedelta(seconds=120), "pending")
    chat_row(s, now - timedelta(seconds=500), "pending")
    chat_row(s, now - timedelta(seconds=900), "success", duration_ms=2000)
    body = health(analytics_admin, w)
    assert body["as_of"] == stamp(now)
    c = body["chatbot_failure"]
    assert (c["total"], c["failed"], c["in_progress"]) == (3, 2, 1)
    rt = body["chatbot_response_time"]
    assert rt["failed"] == {"count": 2, "median_ms": 120000, "p95_ms": 120000}
    assert rt["successful"]["count"] == 1 and rt["all"]["count"] == 3


def test_adm07_ac38_in_progress_only_period_is_not_applicable_but_reports_the_count(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    now = fixed_now(w.at(600))
    chat_row(student(tracked_users), now - timedelta(seconds=10), "pending")
    c = health(analytics_admin, w)["chatbot_failure"]
    assert c["total"] == 0 and c["in_progress"] == 1 and c["state"] == "not_applicable"
    assert c["severity"] is None


def test_adm07_ac38_a_late_outcome_replaces_the_read_time_timeout(analytics_admin, tracked_users, fixed_now):
    from feature_analytics import recording

    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(600))
    rid = recording.record_chat_request_received(user_id=str(s), received_at=now - timedelta(seconds=300))
    assert health(analytics_admin, w)["chatbot_failure"]["failed"] == 1  # shown as timeout
    recording.record_chat_request_outcome(rid, success=True, completed_at=now - timedelta(seconds=200))
    c = health(analytics_admin, w)["chatbot_failure"]
    assert (c["total"], c["failed"]) == (1, 0)


def test_adm07_ac38_the_read_path_never_writes_the_timeout(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    now = fixed_now(w.at(600))
    rid = chat_row(student(tracked_users), now - timedelta(seconds=500), "pending")
    health(analytics_admin, w)
    assert sql("SELECT outcome FROM analytics_chat_request WHERE id=%s", (rid,))[0][0] == "pending"


def test_adm07_ac38_generation_in_progress_is_always_zero(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    now = fixed_now(w.at(600))
    gen_row(teacher(tracked_users), "study_notes", now - timedelta(seconds=5), "success")
    g = health(analytics_admin, w)["generation_failure"]
    assert g["in_progress"] == 0 and g["total"] == 1


def test_adm07_ac38_as_of_is_taken_once_and_returned(analytics_admin, fixed_now):
    w = new_window()
    now = fixed_now(w.at(61, 7))
    assert health(analytics_admin, w)["as_of"] == stamp(now)


# ------------------------------------------------------------------ AC9 / boundaries

def test_adm07_ac11_health_counts_by_received_time_with_start_inclusive_and_end_exclusive(analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    chat_row(s, w.start_dt - timedelta(seconds=1), "failure")
    chat_row(s, w.start_dt, "success")
    chat_row(s, w.end_dt - timedelta(seconds=1), "failure")
    chat_row(s, w.end_dt, "failure")
    c = health(analytics_admin, w)["chatbot_failure"]
    assert (c["total"], c["failed"]) == (2, 1)


# ------------------------------------------------------------------ AC39 partial coverage

def test_adm07_ac39_period_starting_before_recording_is_computed_over_the_covered_part(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    s = student(tracked_users)
    t = teacher(tracked_users)
    recording_start.set(w.start_dt + timedelta(days=1, hours=5))  # recording began on day 2 of 3
    covered = (w.first + timedelta(days=1)).isoformat()
    chat_row(s, w.at(60), "failure")  # day 1: before the recording date, must be excluded
    chat_row(s, w.start_dt + timedelta(days=1, hours=1), "success")  # day 2 (before 05:00 but same UTC date): covered
    chat_row(s, w.start_dt + timedelta(days=2, hours=1), "success")
    gen_row(t, "study_notes", w.at(61), "failure")  # excluded
    attempt_row(s, "att-" + uid(), w.at(30), w.at(40))  # excluded
    attempt_row(s, "att-" + uid(), w.start_dt + timedelta(days=1, hours=2), None)
    body = health(analytics_admin, w)
    assert body["recording_started_on"] == covered and body["data_starts_on"] == covered
    c = body["chatbot_failure"]
    assert c["state"] == "available" and (c["total"], c["failed"]) == (2, 0)
    assert c["data_starts_on"] == covered
    assert body["generation_failure"]["state"] == "not_applicable"
    assert body["practice_completion"]["started"] == 1


def test_adm07_ac39_no_data_starts_on_when_the_period_is_fully_covered(analytics_admin):
    w = new_window()
    body = health(analytics_admin, w)
    assert body["data_starts_on"] is None and body["chatbot_failure"].get("data_starts_on") is None


def test_adm07_ac39_whole_period_before_recording_is_unavailable_period_before_recording(analytics_admin, recording_start):
    w = new_window(2)
    recording_start.set(w.end_dt + timedelta(days=10))
    body = health(analytics_admin, w)
    for key in ("chatbot_failure", "generation_failure", "chatbot_response_time", "generation_response_time",
                "practice_completion"):
        assert body[key]["state"] == "unavailable" and body[key]["reason"] == "period_before_recording", key
    c = body["chatbot_failure"]
    assert c["total"] is None and c["failed"] is None and c["rate_percent"] is None and c["severity"] is None
    for key in ("chatbot_response_time", "generation_response_time"):
        for name in ("all", "successful", "failed"):
            assert body[key][name]["median_ms"] is None and body[key][name]["p95_ms"] is None, (key, name)
    assert body["practice_completion"]["started"] is None and body["practice_completion"]["percentage"] is None
    assert body["rate_limited"]["state"] == "unavailable"


def test_adm07_ac39_the_recording_date_itself_is_covered(analytics_admin, tracked_users, recording_start):
    w = new_window(2)
    s = student(tracked_users)
    recording_start.set(w.start_dt + timedelta(hours=12))
    chat_row(s, w.at(60), "success")
    body = health(analytics_admin, w)
    assert body["data_starts_on"] is None and body["chatbot_failure"]["total"] == 1
