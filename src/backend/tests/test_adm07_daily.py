"""ADM-07 AC19-AC21, AC23, AC39, AC41 for GET /api/admin/analytics/daily (phase 2).

Phase 2 sources: analytics_practice_attempt only. Logins, drafts started and published are specified as
`unavailable` / `not_collected` (never zero). Contract: workflow/specs/ADM-07/plan.md "GET /daily".
"""
from datetime import timedelta

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, recording_start, tracked_users  # noqa: F401
from adm01_grading_helpers import attempt_row, new_window
from adm02_helpers import actor, uid
from adm07_helpers import DAILY, ok

TOP = {"period_start", "period_end", "recording_started_on", "logins", "practice_drafts_started",
       "practice_published", "attempts_funnel", "attempts_per_student"}


def student(tracked):
    u = actor("student")
    tracked.append(u)
    return u


def daily(admin, w):
    return ok(DAILY, admin, w)


def at_day(w, d, hours=1):
    return w.start_dt + timedelta(days=d, hours=hours)


def dates(w, n):
    return [(w.first + timedelta(days=i)).isoformat() for i in range(n)]


def test_adm07_ac19_exact_top_level_shape(analytics_admin):
    w = new_window(2)
    body = daily(analytics_admin, w)
    assert set(body) == TOP, set(body) ^ TOP
    assert (body["period_start"], body["period_end"]) == (w.start, w.end)


@pytest.mark.parametrize("key,total_key", [("logins", "total_logins"), ("practice_drafts_started", "total"),
                                           ("practice_published", "total")])
def test_adm07_ac23_phase4_collected_series_with_no_events_are_available_zeros_not_not_collected(key, total_key, analytics_admin):
    """PHASE 4 CHANGE (was unavailable/not_collected): the source exists, so an empty period is real zeros."""
    w = new_window(2)
    m = daily(analytics_admin, w)[key]
    assert m["state"] == "available" and m["reason"] is None
    assert m["since"] is not None and m[total_key] == 0
    assert [d["date"] for d in m["per_day"]] == dates(w, 2)


# ------------------------------------------------------------------ AC20 funnel

def test_adm07_ac20_started_by_start_day_submitted_by_submission_day(analytics_admin, tracked_users):
    w = new_window(3)
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), at_day(w, 0), at_day(w, 1))  # started D0, submitted D1
    attempt_row(s, "att-" + uid(), at_day(w, 0, 2), at_day(w, 0, 3))  # same day
    attempt_row(s, "att-" + uid(), at_day(w, 1), None)  # never submitted
    attempt_row(s, "att-" + uid(), at_day(w, 2), w.end_dt + timedelta(days=2))  # submitted after the period
    attempt_row(s, "att-" + uid(), w.start_dt - timedelta(hours=5), at_day(w, 0, 4))  # started before the period
    f = daily(analytics_admin, w)["attempts_funnel"]
    assert f["state"] == "available" and f["reason"] is None
    assert f["started_total"] == 4
    assert f["submitted_by_period_end"] == 2  # only attempts started in the period and submitted before window end
    assert [d["date"] for d in f["per_day"]] == dates(w, 3)
    assert [(d["started"], d["submitted"]) for d in f["per_day"]] == [(2, 2), (1, 1), (1, 0)]


def test_adm07_ac20_boundary_instants_belong_to_the_correct_day(analytics_admin, tracked_users):
    w = new_window(2)
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.start_dt - timedelta(seconds=1), None)  # before: not counted
    attempt_row(s, "att-" + uid(), w.start_dt, None)
    attempt_row(s, "att-" + uid(), w.start_dt + timedelta(days=1) - timedelta(seconds=1), None)
    attempt_row(s, "att-" + uid(), w.start_dt + timedelta(days=1), None)
    attempt_row(s, "att-" + uid(), w.end_dt, None)  # at the exclusive end: not counted
    f = daily(analytics_admin, w)["attempts_funnel"]
    # P2-13: corrected own miscount (5 rows seeded, 2 outside the window): D0 has two, D1 has one.
    assert f["started_total"] == 3
    assert [d["started"] for d in f["per_day"]] == [2, 1]


def test_adm07_ac20_none_started_is_not_applicable_but_per_day_is_dense_and_keeps_earlier_submissions(analytics_admin, tracked_users):
    w = new_window(2)
    s = student(tracked_users)
    attempt_row(s, "att-" + uid(), w.start_dt - timedelta(days=3), at_day(w, 1))
    f = daily(analytics_admin, w)["attempts_funnel"]
    assert f["state"] == "not_applicable" and f["reason"] == "no_practice_attempts"
    assert [d["date"] for d in f["per_day"]] == dates(w, 2)
    assert [(d["started"], d["submitted"]) for d in f["per_day"]] == [(0, 0), (0, 1)]


# ------------------------------------------------------------------ AC21 attempts per student

def test_adm07_ac21_median_and_distribution_per_day_even_odd_and_empty_days(analytics_admin, tracked_users):
    w = new_window(3)
    a, b, c = student(tracked_users), student(tracked_users), student(tracked_users)
    # day 0: A has 1 attempt, B has 2 -> median 1.5 (even count)
    attempt_row(a, "att-" + uid(), at_day(w, 0))
    for h in (1, 2):
        attempt_row(b, "att-" + uid(), at_day(w, 0, h))
    # day 1: A 1, B 2, C 5 -> median 2.0 (odd count); C lands in 5_plus
    attempt_row(a, "att-" + uid(), at_day(w, 1))
    for h in (1, 2):
        attempt_row(b, "att-" + uid(), at_day(w, 1, h))
    for h in range(1, 6):
        attempt_row(c, "att-" + uid(), at_day(w, 1, h))
    # day 2: nothing
    m = daily(analytics_admin, w)["attempts_per_student"]
    assert m["state"] == "available" and m["reason"] is None
    d0, d1, d2 = m["per_day"]
    assert [d["date"] for d in m["per_day"]] == dates(w, 3)
    assert (d0["active_students"], d0["median_attempts"], d0["distribution"]) == \
        (2, 1.5, {"1": 1, "2": 1, "3": 0, "4": 0, "5_plus": 0})
    assert (d1["active_students"], d1["median_attempts"], d1["distribution"]) == \
        (3, 2.0, {"1": 1, "2": 1, "3": 0, "4": 0, "5_plus": 1})
    assert (d2["active_students"], d2["median_attempts"], d2["distribution"]) == \
        (0, None, {"1": 0, "2": 0, "3": 0, "4": 0, "5_plus": 0})


def test_adm07_ac21_three_and_four_and_many_attempts_fill_their_buckets(analytics_admin, tracked_users):
    w = new_window(1)
    users = [student(tracked_users) for _ in range(3)]
    for user, n in zip(users, (3, 4, 9)):
        for h in range(n):
            attempt_row(user, "att-" + uid(), w.start_dt + timedelta(minutes=h + 1))
    d = daily(analytics_admin, w)["attempts_per_student"]["per_day"][0]
    assert d["distribution"] == {"1": 0, "2": 0, "3": 1, "4": 1, "5_plus": 1} and d["median_attempts"] == 4.0


def test_adm07_ac21_median_has_one_decimal(analytics_admin, tracked_users):
    w = new_window(1)
    a, b = student(tracked_users), student(tracked_users)
    for n, user in ((2, a), (3, b)):
        for h in range(n):
            attempt_row(user, "att-" + uid(), w.start_dt + timedelta(minutes=h + 1))
    assert daily(analytics_admin, w)["attempts_per_student"]["per_day"][0]["median_attempts"] == 2.5


def test_adm07_ac21_no_attempts_started_is_not_applicable(analytics_admin):
    w = new_window(2)
    m = daily(analytics_admin, w)["attempts_per_student"]
    assert m["state"] == "not_applicable" and m["reason"] == "no_practice_attempts"
    assert [d["active_students"] for d in m["per_day"]] == [0, 0]
    assert all(d["median_attempts"] is None for d in m["per_day"])


def test_adm07_ac21_a_attempt_counts_on_its_start_day_only(analytics_admin, tracked_users):
    w = new_window(2)
    a = student(tracked_users)
    attempt_row(a, "att-" + uid(), at_day(w, 0), at_day(w, 1))
    d0, d1 = daily(analytics_admin, w)["attempts_per_student"]["per_day"]
    assert d0["active_students"] == 1 and d1["active_students"] == 0


# ------------------------------------------------------------------ AC39 partial coverage

def test_adm07_ac39_attempt_metrics_cover_only_the_recorded_part(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    a = student(tracked_users)
    recording_start.set(w.start_dt + timedelta(days=1, hours=3))
    attempt_row(a, "att-" + uid(), at_day(w, 0), at_day(w, 1))  # started before recording: excluded
    attempt_row(a, "att-" + uid(), at_day(w, 1), at_day(w, 2))
    body = daily(analytics_admin, w)
    covered = (w.first + timedelta(days=1)).isoformat()
    f, p = body["attempts_funnel"], body["attempts_per_student"]
    assert f["data_starts_on"] == p["data_starts_on"] == covered
    assert [d["date"] for d in f["per_day"]] == dates(w, 3)[1:]
    assert [d["date"] for d in p["per_day"]] == dates(w, 3)[1:]
    assert f["started_total"] == 1


def test_adm07_ac39_whole_period_before_recording_is_unavailable(analytics_admin, recording_start):
    w = new_window(2)
    recording_start.set(w.end_dt + timedelta(days=3))
    body = daily(analytics_admin, w)
    for key in ("attempts_funnel", "attempts_per_student"):
        m = body[key]
        assert m["state"] == "unavailable" and m["reason"] == "period_before_recording" and m["per_day"] == []
    assert body["attempts_funnel"]["started_total"] is None
    assert body["attempts_funnel"]["submitted_by_period_end"] is None


# ------------------------------------------------------------------ AC41 separate series keys

def test_adm07_ac41_drafts_started_and_published_are_two_separate_metrics(analytics_admin):
    body = daily(analytics_admin, new_window(1))
    assert "practice_drafts_started" in body and "practice_published" in body
    assert body["practice_drafts_started"] is not body["practice_published"]
    assert "created" not in str(body.keys())
