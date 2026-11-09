"""ADM-01 AC1 (access, no-store) and AC3 (period validation), Phase A.

Contract: workflow/specs/ADM-01/plan.md "API endpoints". Only the HTTP contract and the documented
tables are used; the SoC LLM seam is always blocked (adm01_fixtures.no_ai), so no test can spend quota.

TODO(phase B, after plan.md "Decisions" records developer checks 2/6): confirm the wrong-role bodies
match the shared admin dependency exactly (this file only checks status, no-store and absence of data).
"""
import pytest

from adm01_fixtures import analytics_admin, analytics_student, analytics_teacher, disabled_admin, no_ai  # noqa: F401
from adm01_helpers import (GENERATION, QUALITY, RUN_KEYS, RUNS, USAGE, day, error_body, run_count, send, url,
                           wipe_runs)
from auth_helpers import call

PERIOD_KINDS = ["usage", "generation", "quality", "start"]
GET_KINDS = ["usage", "generation", "quality"]
DATA_KEYS = ("chatbot", "workflows", "grades", "run_id", "practice_completion", "recording_started_on")

INVALID_DATES = [
    ("empty", ""), ("spaces", "   "), ("one_digit_month", "2026-1-05"), ("one_digit_day", "2026-11-9"),
    ("slashes", "2026/11/09"), ("day_first", "09-11-2026"), ("compact", "20261109"), ("month_13", "2026-13-01"),
    ("day_32", "2026-11-32"), ("feb_30", "2026-02-30"), ("feb_29_non_leap", "2026-02-29"), ("month_0", "2026-00-10"),
    ("year_0", "0000-01-01"), ("iso_datetime", "2026-11-09T00:00:00Z"), ("date_and_time", "2026-11-09 10:00"),
    ("word", "tomorrow"), ("fullwidth_digits", "２０２６-１１-０９"), ("trailing_text", "2026-11-09x"),
    ("signed", "+2026-11-09"),
]


def standard_422(r):
    """FastAPI's own validation body (the only 422 shape that is not the feature shape)."""
    return r.status_code == 422 and isinstance(r.json().get("detail"), list)


# ---------------------------------------------------------------- AC1: access

def all_requests(valid_run_id=1):
    p = {"period_start": day(5), "period_end": day(0)}
    return [("GET", url(USAGE, **p), None), ("GET", url(GENERATION, **p), None),
            ("GET", url(QUALITY, workflow="student_exercise", **p), None),
            ("POST", RUNS, {"workflow": "student_exercise", **p}), ("GET", f"{RUNS}/{valid_run_id}", None)]


def test_adm01_ac1_every_endpoint_rejects_unauthenticated_student_teacher_and_disabled_admin(
        analytics_student, analytics_teacher, disabled_admin, no_ai):
    before = run_count()
    callers = [("anonymous", None, (401,)), ("student", analytics_student, (403,)),
               ("teacher", analytics_teacher, (403,)), ("disabled_admin", disabled_admin, (401, 403))]
    for who, user, statuses in callers:
        for method, path, body in all_requests():
            r = call(method, path, user, body)
            assert r.status_code in statuses, (who, method, path, r.status_code, r.text)
            assert "no-store" in r.headers.get("cache-control", ""), (who, method, path, r.headers)
            assert not any(k in r.text for k in DATA_KEYS), (who, method, path, r.text)
    assert run_count() == before and not no_ai.calls  # rejected before any work


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac1_authentication_is_checked_before_validation(kind, analytics_student, no_ai):
    anonymous = send(None, kind, period_start="garbage", period_end="garbage", workflow="nope")
    assert anonymous.status_code == 401, anonymous.text
    student = send(analytics_student, kind, period_start="garbage", period_end="garbage", workflow="nope")
    assert student.status_code == 403, student.text


def test_adm01_ac1_unknown_run_is_also_guarded_before_lookup(analytics_student, no_ai):
    assert call("GET", f"{RUNS}/999999999", None).status_code == 401
    assert call("GET", f"{RUNS}/999999999", analytics_student).status_code == 403


def test_adm01_ac1_admin_gets_usage_with_no_store(analytics_admin, no_ai):
    r = send(analytics_admin, "usage", period_start=day(5), period_end=day(0))
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    body = r.json()
    assert {"period_start", "period_end", "recording_started_on", "chatbot", "practice_completion"} <= set(body)
    assert (body["period_start"], body["period_end"]) == (day(5), day(0))
    assert {"student", "teacher", "total"} <= set(body["chatbot"])


def test_adm01_ac1_admin_gets_generation_with_both_workflows_in_order(analytics_admin, no_ai):
    r = send(analytics_admin, "generation", period_start=day(5), period_end=day(0))
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    body = r.json()
    assert (body["period_start"], body["period_end"]) == (day(5), day(0)) and "recording_started_on" in body
    assert [w["workflow"] for w in body["workflows"]] == ["study_notes", "mcq_batch"]


@pytest.mark.parametrize("workflow", ["student_exercise", "teacher_lesson_planning"])
def test_adm01_ac1_admin_gets_quality_for_each_workflow(workflow, analytics_admin, no_ai):
    r = send(analytics_admin, "quality", period_start=day(5), period_end=day(0), workflow=workflow)
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    body = r.json()
    assert body["workflow"] == workflow and (body["period_start"], body["period_end"]) == (day(5), day(0))
    assert {"grades", "response_time", "sessions", "activity_time", "items", "active_run"} <= set(body)
    assert (body["items"]["limit"], body["items"]["offset"]) == (25, 0)  # documented defaults


def test_adm01_ac1_admin_start_returns_202_with_the_run_object_and_get_reads_it_back(analytics_admin, no_ai):
    r = send(analytics_admin, "start", period_start=day(5), period_end=day(0))
    assert r.status_code == 202, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    run = r.json()
    assert set(run) == RUN_KEYS and run["workflow"] == "student_exercise"
    assert (run["period_start"], run["period_end"]) == (day(5), day(0))
    got = call("GET", f"{RUNS}/{run['run_id']}", analytics_admin)
    assert got.status_code == 200 and set(got.json()) == RUN_KEYS, got.text
    assert got.json()["run_id"] == run["run_id"]
    assert "no-store" in got.headers.get("cache-control", ""), got.headers
    assert not no_ai.calls


def test_adm01_ac1_unknown_run_is_404_run_not_found_with_no_store(analytics_admin, no_ai):
    error_body(call("GET", f"{RUNS}/999999999", analytics_admin), 404, "run_not_found")


def test_adm01_ac1_non_integer_run_id_is_not_a_server_error(analytics_admin, no_ai):
    r = call("GET", f"{RUNS}/not-a-number", analytics_admin)
    assert r.status_code in (404, 422), r.text  # plan: FastAPI's 422 is acceptable for a non-integer path


# ---------------------------------------------------------------- AC3: period validation

@pytest.mark.parametrize("kind", PERIOD_KINDS)
@pytest.mark.parametrize("label,bad", INVALID_DATES, ids=[i[0] for i in INVALID_DATES])
def test_adm01_ac3_malformed_start_date_is_invalid_date(kind, label, bad, analytics_admin, no_ai):
    before = run_count()
    r = send(analytics_admin, kind, period_start=bad, period_end=day(0))
    error_body(r, 422, "invalid_date")
    assert run_count() == before and not no_ai.calls


@pytest.mark.parametrize("kind", PERIOD_KINDS)
@pytest.mark.parametrize("label,bad", INVALID_DATES, ids=[i[0] for i in INVALID_DATES])
def test_adm01_ac3_malformed_end_date_is_invalid_date(kind, label, bad, analytics_admin, no_ai):
    before = run_count()
    r = send(analytics_admin, kind, period_start=day(5), period_end=bad)
    error_body(r, 422, "invalid_date")
    assert run_count() == before and not no_ai.calls


@pytest.mark.parametrize("kind", GET_KINDS)
@pytest.mark.parametrize("missing", ["period_start", "period_end"])
def test_adm01_ac3_missing_date_in_the_query_is_invalid_date(kind, missing, analytics_admin, no_ai):
    params = {"period_start": day(5), "period_end": day(0), missing: None}
    error_body(send(analytics_admin, kind, **params), 422, "invalid_date")


@pytest.mark.parametrize("missing", ["period_start", "period_end"])
def test_adm01_ac3_missing_date_in_the_post_body_is_rejected_without_a_run(missing, analytics_admin, no_ai):
    # Plan: a missing key is invalid_date; a missing field in a JSON body may also surface as FastAPI's
    # standard 422. Either way it is a 422 and nothing is started.
    r = send(analytics_admin, "start", **{"period_start": day(5), "period_end": day(0), missing: None})
    assert standard_422(r) or (r.status_code == 422 and r.json()["detail"]["code"] == "invalid_date"), r.text
    assert run_count() == 0 and not no_ai.calls


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac3_both_dates_invalid_is_invalid_date(kind, analytics_admin, no_ai):
    error_body(send(analytics_admin, kind, period_start="x", period_end="y"), 422, "invalid_date")


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac3_dates_are_trimmed_before_validation(kind, analytics_admin, no_ai):
    r = send(analytics_admin, kind, period_start=f"  {day(5)} ", period_end=f"\t{day(0)}  ")
    assert r.status_code == (202 if kind == "start" else 200), r.text
    body = r.json()
    assert (body["period_start"], body["period_end"]) == (day(5), day(0))  # echoed trimmed


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac3_start_after_end_is_period_order(kind, analytics_admin, no_ai):
    before = run_count()
    error_body(send(analytics_admin, kind, period_start=day(0), period_end=day(1)), 422, "period_order")
    error_body(send(analytics_admin, kind, period_start="2026-11-09", period_end="2026-11-08"), 422, "period_order")
    assert run_count() == before and not no_ai.calls


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac3_single_day_period_is_valid(kind, analytics_admin, no_ai):
    r = send(analytics_admin, kind, period_start=day(3), period_end=day(3))
    assert r.status_code == (202 if kind == "start" else 200), r.text


@pytest.mark.parametrize("kind", PERIOD_KINDS)
def test_adm01_ac3_366_days_inclusive_is_valid_and_367_is_too_long(kind, analytics_admin, no_ai):
    ok = send(analytics_admin, kind, period_start=day(365), period_end=day(0))  # 366 calendar days inclusive
    assert ok.status_code == (202 if kind == "start" else 200), ok.text
    if kind == "start":
        wipe_runs()
    before = run_count()
    error_body(send(analytics_admin, kind, period_start=day(366), period_end=day(0)), 422, "period_too_long")
    assert run_count() == before and not no_ai.calls


@pytest.mark.parametrize("kind", GET_KINDS)
def test_adm01_ac3_leap_year_366_days_valid_367_too_long(kind, analytics_admin, no_ai):
    assert send(analytics_admin, kind, period_start="2024-01-01", period_end="2024-12-31").status_code == 200
    error_body(send(analytics_admin, kind, period_start="2024-01-01", period_end="2025-01-01"), 422, "period_too_long")
    assert send(analytics_admin, kind, period_start="2024-02-29", period_end="2024-02-29").status_code == 200


@pytest.mark.parametrize("kind", GET_KINDS)
def test_adm01_ac3_future_and_pre_recording_periods_are_valid_requests(kind, analytics_admin, no_ai):
    assert send(analytics_admin, kind, period_start=day(-1), period_end=day(-3)).status_code == 200
    assert send(analytics_admin, kind, period_start="2020-01-01", period_end="2020-01-31").status_code == 200


# validation order: date format, order, span, workflow, paging; the first failing rule is reported

@pytest.mark.parametrize("kind", ["quality", "start"])
def test_adm01_ac3_invalid_workflow_values(kind, analytics_admin, no_ai):
    for bad in ("", "   ", "student", "Student_Exercise", "teacher", "student_exercise,teacher_lesson_planning", "all"):
        before = run_count()
        error_body(send(analytics_admin, kind, period_start=day(5), period_end=day(0), workflow=bad),
                   422, "invalid_workflow")
        assert run_count() == before and not no_ai.calls, bad


def test_adm01_ac3_missing_workflow_on_quality_is_invalid_workflow(analytics_admin, no_ai):
    error_body(send(analytics_admin, "quality", period_start=day(5), period_end=day(0), workflow=None),
               422, "invalid_workflow")


def test_adm01_ac3_missing_workflow_in_the_post_body_is_rejected_without_a_run(analytics_admin, no_ai):
    r = send(analytics_admin, "start", period_start=day(5), period_end=day(0), workflow=None)
    assert standard_422(r) or (r.status_code == 422 and r.json()["detail"]["code"] == "invalid_workflow"), r.text
    assert run_count() == 0 and not no_ai.calls


@pytest.mark.parametrize("kind", ["quality", "start"])
def test_adm01_ac3_workflow_is_trimmed(kind, analytics_admin, no_ai):
    r = send(analytics_admin, kind, period_start=day(5), period_end=day(0), workflow=" teacher_lesson_planning ")
    assert r.status_code == (202 if kind == "start" else 200), r.text
    assert r.json()["workflow"] == "teacher_lesson_planning"


@pytest.mark.parametrize("kind", ["quality", "start"])
def test_adm01_ac3_first_failing_rule_wins(kind, analytics_admin, no_ai):
    bad_workflow = {"workflow": "nope"}
    # format beats order, span, workflow and paging
    error_body(send(analytics_admin, kind, period_start="x", period_end="2020-01-01", **bad_workflow),
               422, "invalid_date")
    # order beats workflow
    error_body(send(analytics_admin, kind, period_start=day(0), period_end=day(5), **bad_workflow),
               422, "period_order")
    # span beats workflow
    error_body(send(analytics_admin, kind, period_start="2020-01-01", period_end="2022-01-01", **bad_workflow),
               422, "period_too_long")
    assert run_count() == 0 and not no_ai.calls


# paging (quality only)

@pytest.mark.parametrize("extra", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"limit": "abc"}, {"limit": ""},
                                   {"offset": -1}, {"offset": "abc"}, {"limit": 1000000, "offset": 0},
                                   {"limit": 10, "offset": -5}, {"limit": 2.5}])
def test_adm01_ac3_invalid_paging_is_invalid_paging(extra, analytics_admin, no_ai):
    error_body(send(analytics_admin, "quality", period_start=day(5), period_end=day(0), **extra),
               422, "invalid_paging")


def test_adm01_ac3_workflow_error_beats_paging_error(analytics_admin, no_ai):
    error_body(send(analytics_admin, "quality", period_start=day(5), period_end=day(0), workflow="nope", limit=0),
               422, "invalid_workflow")


@pytest.mark.parametrize("limit,offset", [(1, 0), (100, 0), (25, 0), (10, 3), (50, 1000)])
def test_adm01_ac3_valid_paging_is_echoed(limit, offset, analytics_admin, no_ai):
    r = send(analytics_admin, "quality", period_start=day(5), period_end=day(0), limit=limit, offset=offset)
    assert r.status_code == 200, r.text
    assert (r.json()["items"]["limit"], r.json()["items"]["offset"]) == (limit, offset)


# POST body shape

def test_adm01_ac3_unknown_post_field_is_rejected_with_the_standard_422_and_no_run(analytics_admin, no_ai):
    body = {"workflow": "student_exercise", "period_start": day(5), "period_end": day(0), "user_id": "someone"}
    r = call("POST", RUNS, analytics_admin, body)
    assert standard_422(r), r.text
    assert run_count() == 0 and not no_ai.calls


def test_adm01_ac3_missing_or_malformed_post_body_is_the_standard_422(analytics_admin, no_ai):
    assert standard_422(call("POST", RUNS, analytics_admin)), "missing body"
    r = call("POST", RUNS, analytics_admin, content=b"{not json", headers={"Content-Type": "application/json"})
    assert standard_422(r), r.text
    assert run_count() == 0 and not no_ai.calls


def test_adm01_ac3_errors_are_the_feature_shape_with_exactly_two_keys(analytics_admin, no_ai):
    r = send(analytics_admin, "usage", period_start="x", period_end=day(0))
    detail = r.json()["detail"]
    assert set(detail) == {"code", "message"} and set(r.json()) == {"detail"}


# ---------------------------------------------------------------- AC3: periods.parse_period (unit, no database)

def test_adm01_ac3_parse_period_builds_the_utc_half_open_window():
    from datetime import datetime, timedelta, timezone
    from feature_analytics.periods import parse_period

    w = parse_period(" 2026-11-09 ", "2026-11-09")
    assert str(w.period_start) == "2026-11-09" and str(w.period_end) == "2026-11-09"
    assert w.start_utc == datetime(2026, 11, 9, tzinfo=timezone.utc)
    assert w.end_utc_exclusive == datetime(2026, 11, 10, tzinfo=timezone.utc)
    w = parse_period("2024-12-31", "2025-01-01")
    assert w.end_utc_exclusive - w.start_utc == timedelta(days=2)
    assert w.start_utc.utcoffset() == timedelta(0)


@pytest.mark.parametrize("start,end", [("", "2026-11-09"), ("2026-11-9", "2026-11-09"), ("2026-02-30", "2026-03-01"),
                                       ("2026-11-10", "2026-11-09"), ("2024-01-01", "2025-01-01")])
def test_adm01_ac3_parse_period_raises_for_invalid_periods(start, end):
    from feature_analytics.periods import parse_period

    with pytest.raises(Exception):
        parse_period(start, end)


def test_adm01_ac3_parse_period_accepts_exactly_366_days():
    from feature_analytics.periods import parse_period

    parse_period("2025-11-09", "2026-11-09")  # 366 calendar days inclusive
    with pytest.raises(Exception):
        parse_period("2025-11-08", "2026-11-09")
