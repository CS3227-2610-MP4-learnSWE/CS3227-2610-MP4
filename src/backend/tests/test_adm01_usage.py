"""ADM-01 AC4-AC13: feature usage report (task 18).

Contract: workflow/specs/ADM-01/plan.md "GET /usage", "Common metric states", "Window rule", "Coverage rule".
Each test uses its own far-future UTC window (adm01_grading_helpers.Window) and users it creates, so the
counts asserted are exact. Rows are seeded through the documented tables (not through hooks) unless the
test is about a hook.
"""
import json
import re

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, no_ai, recording_start, tracked_users  # noqa: F401
from adm01_grading_helpers import (attempt_row, bulk_users, chat_item, chat_row, drop_users, get_json, new_window,
                                   set_name)
from adm01_helpers import USAGE, day, send, url, wipe_user_rows
from adm02_helpers import actor, uid
from auth_helpers import call

TEXT_KEYS = re.compile(r"request_text|response_text|context_text|prompt|reply|message|content|token|categor|latency|"
                       r"resource|ai_call|failure_code", re.I)


def student(tracked, name=None):
    user = actor("student")
    tracked.append(user)
    if name:
        set_name(user, name)
    return user


def usage(admin, win, **extra):
    return get_json(admin, "usage", win, **extra)


def rows_by_user(body, group="student"):
    return {r["user_id"]: r for r in body["chatbot"][group]["rows"]}


def all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from all_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from all_keys(v)


# ---------------------------------------------------------------- AC4, AC5: counts per user, role totals

def test_adm01_ac4_ac5_counts_per_user_with_role_totals_for_every_chat_mode(analytics_admin, tracked_users):
    w = new_window()
    a, b = student(tracked_users, "Alice Tan " + uid()[:6]), student(tracked_users, "Bob Lim " + uid()[:6])
    # a: 2 successes (practice + lesson), 1 failure, 1 request that never got an outcome (pending)
    chat_row(a, w.at(1), "success")
    chat_row(a, w.at(2), "success", activity_type="lesson", activity_ref="lesson-1")
    chat_row(a, w.at(3), "failure", activity_type=None)
    chat_row(a, w.at(4), "pending")
    chat_row(b, w.at(5), "success", activity_type=None)
    body = usage(analytics_admin, w)
    rows = rows_by_user(body)
    assert set(rows) == {str(a), str(b)}
    assert (rows[str(a)]["successful"], rows[str(a)]["unsuccessful"]) == (2, 2)  # pending is unsuccessful (AC4)
    assert (rows[str(b)]["successful"], rows[str(b)]["unsuccessful"]) == (1, 0)
    student_group = body["chatbot"]["student"]
    assert student_group["state"] == "available" and student_group["reason"] is None
    assert (student_group["successful"], student_group["unsuccessful"]) == (3, 2)
    assert student_group["rows_truncated"] is False


def test_adm01_ac4_a_request_with_no_outcome_is_unsuccessful_through_the_hooks(analytics_admin, tracked_users):
    from feature_analytics import recording

    w = new_window()
    a = student(tracked_users)
    recording.record_chat_request_received(user_id=str(a), received_at=w.at(1))  # never completed
    rid = recording.record_chat_request_received(user_id=str(a), received_at=w.at(2))
    recording.record_chat_request_outcome(rid, success=True, completed_at=w.at(2, 1))
    rid2 = recording.record_chat_request_received(user_id=str(a), received_at=w.at(3))
    recording.record_chat_request_outcome(rid2, success=False, completed_at=w.at(3, 1))
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (1, 2)


def test_adm01_ac5_the_usage_report_has_exactly_the_documented_top_level_shape(analytics_admin, tracked_users):
    w = new_window()
    chat_row(student(tracked_users), w.at(1))
    body = usage(analytics_admin, w)
    # ADM-07 P2-5: the kept endpoint gains `data_starts_on` (partial coverage); no other top-level change.
    assert set(body) == {"period_start", "period_end", "recording_started_on", "data_starts_on", "chatbot",
                         "practice_completion"}
    assert body["data_starts_on"] is None
    assert set(body["chatbot"]) == {"student", "teacher", "total"}
    assert (body["period_start"], body["period_end"]) == (w.start, w.end)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", body["recording_started_on"])
    assert set(body["chatbot"]["student"]) >= {"state", "reason", "successful", "unsuccessful", "rows", "rows_truncated"}
    assert set(body["chatbot"]["total"]) >= {"state", "reason", "successful", "unsuccessful"}
    assert set(body["practice_completion"]) >= {"state", "reason", "started", "submitted", "percentage"}
    row = body["chatbot"]["student"]["rows"][0]
    assert set(row) == {"user_id", "name", "successful", "unsuccessful"}


def test_adm01_ac5_rows_are_sorted_by_name_case_insensitively_then_user_id(analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    users = {n: student(tracked_users, f"{n} {tag}") for n in ("bob", "Alice", "carol", "Dave")}
    twin_a, twin_b = student(tracked_users, f"Zed {tag}"), student(tracked_users, f"Zed {tag}")
    for u in [*users.values(), twin_a, twin_b]:
        chat_row(u, w.at(1))
    rows = usage(analytics_admin, w)["chatbot"]["student"]["rows"]
    assert [r["name"] for r in rows[:4]] == [f"Alice {tag}", f"bob {tag}", f"carol {tag}", f"Dave {tag}"]
    assert [r["user_id"] for r in rows[4:]] == sorted([str(twin_a), str(twin_b)])


def test_adm01_ac5_names_are_display_names_never_emails(analytics_admin, tracked_users):
    w = new_window()
    a = student(tracked_users, "Display Name " + uid()[:6])
    chat_row(a, w.at(1))
    r = call("GET", url(USAGE, **w.params), analytics_admin)
    row = rows_by_user(r.json())[str(a)]
    assert row["name"].startswith("Display Name ")
    assert a.email not in r.text and "@" not in json.dumps(r.json()["chatbot"]["student"]["rows"])


def test_adm01_ac5_each_role_total_counts_users_outside_the_row_cap(analytics_admin):
    """More than 500 users in a period: first 500 by name as rows, totals over all, rows_truncated true."""
    w = new_window()
    ids = bulk_users(501)
    try:
        for i, user_id in enumerate(ids):
            chat_row(user_id, w.at(1), "success" if i % 3 else "failure", activity_type=None)
        group = usage(analytics_admin, w)["chatbot"]["student"]
        failures = sum(1 for i in range(501) if not i % 3)
        assert len(group["rows"]) == 500 and group["rows_truncated"] is True
        assert (group["successful"], group["unsuccessful"]) == (501 - failures, failures)
        assert [r["name"] for r in group["rows"]] == [f"ADM01 bulk {i:04d}" for i in range(500)]
    finally:
        wipe_user_rows(ids)
        drop_users(ids)


def test_adm01_ac5_exactly_500_users_is_not_truncated(analytics_admin):
    w = new_window()
    ids = bulk_users(500)
    try:
        for user_id in ids:
            chat_row(user_id, w.at(1), "success", activity_type=None)
        group = usage(analytics_admin, w)["chatbot"]["student"]
        assert len(group["rows"]) == 500 and group["rows_truncated"] is False and group["successful"] == 500
    finally:
        wipe_user_rows(ids)
        drop_users(ids)


# ---------------------------------------------------------------- AC6: period boundaries on received_at

def test_adm01_ac6_requests_at_the_period_edges(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    a = student(tracked_users)
    chat_row(a, w.start_dt - timedelta(seconds=1), "failure")  # 1 s before From 00:00:00 UTC: excluded
    chat_row(a, w.start_dt, "success")  # exactly From 00:00:00: included
    chat_row(a, w.end_dt - timedelta(seconds=1), "success")  # To 23:59:59: included
    chat_row(a, w.end_dt, "failure")  # To + 1 day 00:00:00: excluded
    chat_row(a, w.end_dt + timedelta(seconds=1), "failure")  # after: excluded
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (2, 0)


def test_adm01_ac6_a_multi_day_period_covers_every_day_to_the_last_second(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window(3)
    a = student(tracked_users)
    chat_row(a, w.start_dt - timedelta(seconds=1), "failure")
    for offset in (timedelta(0), timedelta(days=1, hours=12), timedelta(days=3) - timedelta(seconds=1)):
        chat_row(a, w.start_dt + offset, "success")
    chat_row(a, w.start_dt + timedelta(days=3), "failure")
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (3, 0)


def test_adm01_ac6_a_single_day_period_is_one_whole_utc_day(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window(1)
    a = student(tracked_users)
    chat_row(a, w.start_dt + timedelta(hours=23, minutes=59, seconds=59), "success")
    chat_row(a, w.start_dt + timedelta(days=1), "success")
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (1, 0)


def test_adm01_ac6_a_request_is_counted_by_when_it_was_received_not_when_it_finished(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    a = student(tracked_users)
    # received in the last second of the period, completed after the period ended: still in this period
    chat_row(a, w.end_dt - timedelta(seconds=1), "success", duration_ms=5000)
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (1, 0)


# ---------------------------------------------------------------- AC7: who gets a row, zero versus absent

def test_adm01_ac7_only_users_with_a_request_in_the_period_get_a_row(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    active, idle, elsewhere = (student(tracked_users) for _ in range(3))
    chat_row(active, w.at(1))
    chat_row(elsewhere, w.start_dt - timedelta(days=2))
    assert set(rows_by_user(usage(analytics_admin, w))) == {str(active)}
    assert str(idle) not in call("GET", url(USAGE, **w.params), analytics_admin).text


def test_adm01_ac7_a_role_with_data_available_and_no_requests_shows_zero_and_no_rows(analytics_admin):
    w = new_window()
    group = usage(analytics_admin, w)["chatbot"]["student"]
    assert group["state"] == "available" and group["reason"] is None
    assert group["successful"] == 0 and group["unsuccessful"] == 0  # a real zero, not null
    assert group["rows"] == [] and group["rows_truncated"] is False


def test_adm01_ac7_a_user_whose_only_requests_failed_still_gets_a_row_with_zero_successful(analytics_admin, tracked_users):
    w = new_window()
    a = student(tracked_users)
    chat_row(a, w.at(1), "failure")
    row = rows_by_user(usage(analytics_admin, w))[str(a)]
    assert (row["successful"], row["unsuccessful"]) == (0, 1)


# ---------------------------------------------------------------- AC13: teacher group and grand total

def test_adm01_ac13_teacher_counts_and_the_grand_total_are_unavailable_no_source(analytics_admin, tracked_users):
    w = new_window()
    chat_row(student(tracked_users), w.at(1))
    chatbot = usage(analytics_admin, w)["chatbot"]
    teacher, total = chatbot["teacher"], chatbot["total"]
    assert teacher["state"] == "unavailable" and teacher["reason"] == "no_source"
    assert teacher["successful"] is None and teacher["unsuccessful"] is None
    assert teacher["rows"] == [] and teacher["rows_truncated"] is False
    assert total["state"] == "unavailable" and total["reason"] == "no_source"
    assert total["successful"] is None and total["unsuccessful"] is None
    assert chatbot["student"]["state"] == "available"  # the student half is still reported


def test_adm01_ac13_teacher_is_unavailable_even_when_the_period_has_no_requests_at_all(analytics_admin):
    chatbot = usage(analytics_admin, new_window())["chatbot"]
    assert chatbot["teacher"]["reason"] == "no_source" and chatbot["total"]["state"] == "unavailable"
    assert chatbot["student"]["successful"] == 0  # zero, not unavailable


# ---------------------------------------------------------------- AC8-AC10: practice-set completion

def completion(admin, w):
    return usage(admin, w)["practice_completion"]


def test_adm01_ac8_ac9_completion_counts_attempts_started_in_the_period_submitted_by_its_end(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.at(seconds=-1), w.at(10))  # started before the period: not counted at all
    attempt_row(s, "att-" + uid(), w.at(10), w.at(20))  # started and submitted in the period
    attempt_row(s, "att-" + uid(), w.at(30), w.end_dt - timedelta(seconds=1))  # submitted in the last second
    attempt_row(s, "att-" + uid(), w.at(40), w.end_dt)  # submitted at the exclusive end: not complete
    attempt_row(s, "att-" + uid(), w.at(50))  # never submitted
    attempt_row(s, "att-" + uid(), w.at(), w.at(60))  # started exactly at From: counted
    attempt_row(s, "att-" + uid(), w.end_dt, w.end_dt + timedelta(minutes=5))  # started at the exclusive end: not counted
    c = completion(analytics_admin, w)
    assert c["state"] == "available" and c["reason"] is None
    assert (c["started"], c["submitted"], c["percentage"]) == (5, 3, 60.0)


def test_adm01_ac9_an_attempt_submitted_after_the_period_is_started_but_not_complete(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.at(10), w.end_dt + timedelta(days=30))
    c = completion(analytics_admin, w)
    assert c["state"] == "available" and (c["started"], c["submitted"], c["percentage"]) == (1, 0, 0.0)


def test_adm01_ac9_an_attempt_started_before_the_period_and_submitted_inside_it_is_ignored(analytics_admin, tracked_users):
    from datetime import timedelta

    w = new_window()
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.start_dt - timedelta(days=2), w.at(10))
    c = completion(analytics_admin, w)
    assert c["state"] == "not_applicable" and c["reason"] == "no_practice_attempts"


@pytest.mark.parametrize("started,submitted,expected", [
    (3, 1, 33.3), (3, 2, 66.7), (6, 1, 16.7), (6, 5, 83.3), (8, 7, 87.5), (4, 0, 0.0), (4, 4, 100.0), (1, 1, 100.0),
])
def test_adm01_ac8_percentage_is_rounded_to_one_decimal(started, submitted, expected, analytics_admin, tracked_users):
    w = new_window()
    s = student(tracked_users)
    for i in range(started):
        attempt_row(s, "att-" + uid(), w.at(i + 1), w.at(i + 100) if i < submitted else None)
    c = completion(analytics_admin, w)
    assert c["state"] == "available" and (c["started"], c["submitted"]) == (started, submitted)
    assert c["percentage"] == expected


def test_adm01_ac10_no_attempt_started_is_not_applicable_with_no_percentage(analytics_admin):
    c = completion(analytics_admin, new_window())
    assert c["state"] == "not_applicable" and c["reason"] == "no_practice_attempts"
    assert c["started"] == 0 and c["submitted"] == 0
    assert c["percentage"] is None  # never 0 and never 100


def test_adm01_ac10_every_user_counts_toward_the_one_completion_figure(analytics_admin, tracked_users):
    w = new_window()
    a, b = student(tracked_users), student(tracked_users)
    attempt_row(a, "att-" + uid(), w.at(1), w.at(5))
    attempt_row(b, "att-" + uid(), w.at(2))
    c = completion(analytics_admin, w)
    assert (c["started"], c["submitted"], c["percentage"]) == (2, 1, 50.0)


# ---------------------------------------------------------------- AC11: no private text, no AI-service metrics

def test_adm01_ac11_the_usage_response_holds_no_message_text_and_no_ai_call_metrics(analytics_admin, tracked_users):
    w = new_window()
    a = student(tracked_users, "Private Reader " + uid()[:6])
    marker = "PRIVATE-MARKER-" + uid()
    chat_item(a, w.at(1), request_text=marker + "-req", response_text=marker + "-resp", context_text=marker + "-ctx")
    attempt_row(a, "att-" + uid(), w.at(1), w.at(9))
    r = call("GET", url(USAGE, **w.params), analytics_admin)
    assert r.status_code == 200
    assert marker not in r.text
    banned = [k for k in all_keys(r.json()) if TEXT_KEYS.search(k)]
    assert banned == [], banned
    assert "completed_at" not in r.text and "duration" not in r.text  # no timing or resource measurements here


# ---------------------------------------------------------------- AC12: unavailable is never zero

UNAVAILABLE_NUMBERS = ("successful", "unsuccessful")


def test_adm01_ac12_a_period_starting_before_recording_is_unavailable_for_every_metric(analytics_admin):
    r = call("GET", url(USAGE, period_start="2000-01-01", period_end="2000-01-31"), analytics_admin)
    assert r.status_code == 200, r.text
    body = r.json()
    for group in ("student", "teacher", "total"):
        g = body["chatbot"][group]
        assert g["state"] == "unavailable" and g["reason"] == "period_before_recording", (group, g)
        assert g["successful"] is None and g["unsuccessful"] is None  # never 0
    assert body["chatbot"]["student"]["rows"] == []
    pc = body["practice_completion"]
    assert pc["state"] == "unavailable" and pc["reason"] == "period_before_recording"
    assert pc["started"] is None and pc["submitted"] is None and pc["percentage"] is None


def test_adm01_ac12_the_recording_date_itself_is_covered_and_the_day_before_is_partly_covered(analytics_admin, tracked_users, recording_start):
    """ADM-07 P2-5 update. Reason: ADM-07 AC39 (decided partial coverage) replaces the whole-metric
    `period_before_recording` rule of ADM-01 AC12 when only the START of the period precedes recording.
    The period starting one day before recording is now computed from the recording date and carries
    `data_starts_on`; a period ENDING before recording is still `unavailable` (kept below)."""
    from datetime import timedelta

    w = new_window(2)
    recording_start.set(w.start_dt + timedelta(hours=12))
    a = student(tracked_users)
    chat_row(a, w.at(60), "success", activity_type=None)
    inside = usage(analytics_admin, w)
    assert inside["recording_started_on"] == w.start
    assert inside["chatbot"]["student"]["state"] == "available"
    assert inside["chatbot"]["student"]["successful"] == 1
    assert inside["data_starts_on"] is None
    day_before = (w.first - timedelta(days=1)).isoformat()
    chat_row(a, w.start_dt - timedelta(hours=2), "failure", activity_type=None)  # before recording: not counted
    partial = call("GET", url(USAGE, period_start=day_before, period_end=w.end), analytics_admin).json()
    assert partial["recording_started_on"] == w.start and partial["data_starts_on"] == w.start
    assert partial["chatbot"]["student"]["state"] == "available"
    assert (partial["chatbot"]["student"]["successful"], partial["chatbot"]["student"]["unsuccessful"]) == (1, 0)
    assert partial["practice_completion"]["state"] in ("available", "not_applicable")
    before_all = call("GET", url(USAGE, period_start=(w.first - timedelta(days=5)).isoformat(),
                                 period_end=day_before), analytics_admin).json()
    assert before_all["chatbot"]["student"]["state"] == "unavailable"
    assert before_all["chatbot"]["student"]["reason"] == "period_before_recording"
    assert before_all["practice_completion"]["state"] == "unavailable"


@pytest.mark.parametrize("failing,still_ok", [("chat_counts", "practice_completion"),
                                              ("practice_completion", "chatbot")])
def test_adm01_ac12_one_metric_failing_to_read_leaves_the_others(failing, still_ok, analytics_admin, tracked_users, monkeypatch):
    from feature_analytics import queries

    w = new_window()
    a = student(tracked_users)
    chat_row(a, w.at(1))
    attempt_row(a, "att-" + uid(), w.at(1), w.at(2))

    def boom(*args, **kwargs):
        raise RuntimeError("simulated read failure")

    monkeypatch.setattr(queries, failing, boom)
    r = call("GET", url(USAGE, **w.params), analytics_admin)
    assert r.status_code == 200, r.text  # the report is still returned
    body = r.json()
    if failing == "chat_counts":
        student_group = body["chatbot"]["student"]
        assert student_group["state"] == "unavailable" and student_group["reason"] == "read_failed"
        assert student_group["successful"] is None and student_group["unsuccessful"] is None
        assert body["chatbot"]["total"]["state"] == "unavailable"
        assert body["chatbot"]["total"]["reason"] == "read_failed"
        assert body["practice_completion"]["state"] == "available"
        assert body["practice_completion"]["started"] == 1
    else:
        pc = body["practice_completion"]
        assert pc["state"] == "unavailable" and pc["reason"] == "read_failed"
        assert pc["started"] is None and pc["percentage"] is None
        assert body["chatbot"]["student"]["state"] == "available"
        assert body["chatbot"]["student"]["successful"] == 1
    assert "simulated read failure" not in r.text  # the cause is never shown


def test_adm01_ac12_a_failed_read_is_never_reported_as_zero(analytics_admin, monkeypatch):
    from feature_analytics import queries

    monkeypatch.setattr(queries, "chat_counts", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    group = usage(analytics_admin, new_window())["chatbot"]["student"]
    assert group["successful"] is None and group["unsuccessful"] is None and group["state"] != "available"


# ---------------------------------------------------------------- isolation between periods

def test_adm01_ac6_two_periods_report_their_own_requests(analytics_admin, tracked_users):
    w1, w2 = new_window(), new_window()
    a = student(tracked_users)
    chat_row(a, w1.at(1), "success")
    chat_row(a, w2.at(1), "failure")
    chat_row(a, w2.at(2), "failure")
    r1 = rows_by_user(usage(analytics_admin, w1))[str(a)]
    r2 = rows_by_user(usage(analytics_admin, w2))[str(a)]
    assert (r1["successful"], r1["unsuccessful"]) == (1, 0)
    assert (r2["successful"], r2["unsuccessful"]) == (0, 2)
