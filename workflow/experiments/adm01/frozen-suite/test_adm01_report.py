"""ADM-01 report endpoint: counting, periods, rates, access, availability (no LLM involved)."""
import re
from datetime import date, datetime, timedelta, timezone

import pytest
from adm01_helpers import (ALL_TYPES, INVALID_MESSAGE, URL, adm_clean, call, insert, ok_report,  # noqa: F401
                           report, seed_day, sql)
from auth_helpers import code_of, new_student, seeded


# ---------------------------------------------------------------- AC1
def test_adm01_ac1_events_in_period_map_to_fields(adm_clean):
    seed_day("2022-05-10", chatbot_request=1, practice_completed=2,
             notes_generation_requested=5, notes_generation_succeeded=3, notes_generation_failed=2,
             mcq_generation_requested=4, mcq_generation_succeeded=1, mcq_generation_failed=3)
    seed_day("2022-05-11", chatbot_request=2)
    body = ok_report("2022-05-10", "2022-05-11")
    assert body["period"] == {"start": "2022-05-10", "end": "2022-05-11", "days": 2, "timezone": "UTC"}
    assert body["status"] == "available"
    assert body["usage"] == {"chatbot_requests": 3, "practice_completions": 2, "has_activity": True}
    assert body["generation"]["notes"] == {"requested": 5, "succeeded": 3, "failed": 2, "success_rate_percent": 60.0}
    assert body["generation"]["mcq"] == {"requested": 4, "succeeded": 1, "failed": 3, "success_rate_percent": 25.0}
    assert set(body) == {"period", "status", "usage", "generation"}
    assert set(body["generation"]) == {"notes", "mcq"}


def test_adm01_ac1_period_boundaries_inclusive_start_and_end_exclusive_outside(adm_clean):
    insert("chatbot_request", "2022-05-10T00:00:00Z")          # in: start 00:00:00Z
    insert("chatbot_request", "2022-05-09T23:59:59Z")          # out
    insert("chatbot_request", "2022-05-12T23:59:59.999Z")      # in: end 23:59:59.999Z
    insert("chatbot_request", "2022-05-13T00:00:00Z")          # out: end+1 00:00:00Z
    body = ok_report("2022-05-10", "2022-05-12")
    assert body["usage"]["chatbot_requests"] == 2
    assert body["period"]["days"] == 3


def test_adm01_ac1_only_selected_period_is_counted(adm_clean):
    seed_day("2022-06-01", practice_completed=4)
    seed_day("2022-06-20", practice_completed=7)
    assert ok_report("2022-06-01", "2022-06-01")["usage"]["practice_completions"] == 4
    assert ok_report("2022-06-02", "2022-06-19")["usage"]["practice_completions"] == 0
    assert ok_report("2022-06-01", "2022-06-20")["usage"]["practice_completions"] == 11


def test_adm01_ac1_timestamps_with_offsets_are_bucketed_by_utc_day(adm_clean):
    # 2022-07-02T01:00+08:00 is 2022-07-01T17:00Z: belongs to July 1 UTC.
    insert("chatbot_request", "2022-07-02T01:00:00+08:00")
    assert ok_report("2022-07-01", "2022-07-01")["usage"]["chatbot_requests"] == 1
    assert ok_report("2022-07-02", "2022-07-02")["usage"]["chatbot_requests"] == 0


# ---------------------------------------------------------------- AC2
def test_adm01_ac2_no_activity_is_available_with_zeros(adm_clean):
    body = ok_report("2022-08-01", "2022-08-07")
    assert body["status"] == "available"
    assert body["usage"] == {"chatbot_requests": 0, "practice_completions": 0, "has_activity": False}
    zero = {"requested": 0, "succeeded": 0, "failed": 0, "success_rate_percent": None}
    assert body["generation"] == {"notes": zero, "mcq": zero}


def test_adm01_ac2_has_activity_true_for_practice_only(adm_clean):
    seed_day("2022-08-01", practice_completed=1)
    assert ok_report("2022-08-01", "2022-08-01")["usage"]["has_activity"] is True


def test_adm01_ac2_has_activity_false_when_only_generation_events(adm_clean):
    seed_day("2022-08-01", notes_generation_requested=2)
    body = ok_report("2022-08-01", "2022-08-01")
    assert body["usage"]["has_activity"] is False


def test_adm01_ac2_unavailable_when_event_data_cannot_be_read(adm_clean, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    def boom(*a, **k):
        raise SQLAlchemyError("sentinel-internal-db-detail")

    monkeypatch.setattr("analytics.service.count_events", boom)
    r = report("2022-08-01", "2022-08-07")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["usage"] is None and body["generation"] is None
    assert body["period"] == {"start": "2022-08-01", "end": "2022-08-07", "days": 7, "timezone": "UTC"}
    assert "sentinel-internal-db-detail" not in r.text


def test_adm01_ac2_only_sqlalchemy_errors_become_unavailable(adm_clean, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("programming error")

    monkeypatch.setattr("analytics.service.count_events", boom)
    assert report("2022-08-01", "2022-08-07").status_code == 500


# ---------------------------------------------------------------- AC4
@pytest.mark.parametrize("req,ok,fail,expected", [
    (3, 2, 1, 66.7),
    (3, 1, 2, 33.3),
    (8, 1, 7, 12.5),
    (16, 1, 15, 6.3),      # 6.25 rounds half-up (float/banker rounding would give 6.2)
    (1, 1, 0, 100.0),
    (3, 0, 3, 0.0),
    (200, 1, 199, 0.5),
])
@pytest.mark.parametrize("kind", ["notes", "mcq"])
def test_adm01_ac4_success_rate_half_up_one_decimal(adm_clean, kind, req, ok, fail, expected):
    seed_day("2022-09-01", **{f"{kind}_generation_requested": req, f"{kind}_generation_succeeded": ok,
                              f"{kind}_generation_failed": fail})
    row = ok_report("2022-09-01", "2022-09-01")["generation"][kind]
    assert row["requested"] == req and row["succeeded"] == ok and row["failed"] == fail
    assert row["success_rate_percent"] == expected
    assert isinstance(row["success_rate_percent"], (int, float)) and not isinstance(row["success_rate_percent"], bool)


def test_adm01_ac4_unresolved_requests_count_against_rate(adm_clean):
    seed_day("2022-09-02", notes_generation_requested=4, notes_generation_succeeded=1)
    assert ok_report("2022-09-02", "2022-09-02")["generation"]["notes"]["success_rate_percent"] == 25.0


def test_adm01_ac4_rate_uses_selected_period_only(adm_clean):
    seed_day("2022-09-03", notes_generation_requested=2, notes_generation_succeeded=2)
    seed_day("2022-09-10", notes_generation_requested=2, notes_generation_failed=2)
    assert ok_report("2022-09-03", "2022-09-03")["generation"]["notes"]["success_rate_percent"] == 100.0
    assert ok_report("2022-09-10", "2022-09-10")["generation"]["notes"]["success_rate_percent"] == 0.0
    assert ok_report("2022-09-03", "2022-09-10")["generation"]["notes"]["success_rate_percent"] == 50.0


def test_adm01_ac4_success_rate_unit():
    from analytics.service import success_rate

    assert success_rate(2, 3) == 66.7
    assert success_rate(1, 3) == 33.3
    assert success_rate(1, 8) == 12.5
    assert success_rate(1, 16) == 6.3
    assert success_rate(3, 3) == 100.0
    assert success_rate(0, 5) == 0.0
    assert success_rate(0, 0) is None
    assert success_rate(5, 0) is None


# ---------------------------------------------------------------- AC5
def test_adm01_ac5_no_requests_for_kind_gives_null_not_zero_or_hundred(adm_clean):
    seed_day("2022-09-05", notes_generation_requested=2, notes_generation_succeeded=1, notes_generation_failed=1)
    gen = ok_report("2022-09-05", "2022-09-05")["generation"]
    assert gen["notes"]["success_rate_percent"] == 50.0
    assert gen["mcq"]["success_rate_percent"] is None
    assert gen["mcq"]["requested"] == 0


def test_adm01_ac5_succeeded_without_requested_gives_no_percentage(adm_clean):
    seed_day("2022-09-06", notes_generation_succeeded=2, mcq_generation_failed=1)
    gen = ok_report("2022-09-06", "2022-09-06")["generation"]
    assert gen["notes"]["success_rate_percent"] is None
    assert gen["notes"]["succeeded"] == 2 and gen["notes"]["requested"] == 0
    assert gen["mcq"]["success_rate_percent"] is None


# ---------------------------------------------------------------- AC6 + SHR-01
def test_adm01_ac6_no_cookie_is_401(adm_clean):
    r = call("GET", URL)
    assert r.status_code == 401
    assert r.json()["detail"] == {"code": "unauthenticated", "message": "Sign in to continue."}


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_adm01_ac6_non_admin_is_403(adm_clean, role):
    r = report(role=role)
    assert r.status_code == 403
    assert r.json()["detail"] == {"code": "forbidden", "message": "You do not have access to this."}


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_adm01_ac6_403_precedes_date_validation(adm_clean, role):
    r = report("not-a-date", "2022-01-01", role=role)
    assert r.status_code == 403 and code_of(r) == "forbidden"


def test_adm01_ac6_401_precedes_date_validation(adm_clean):
    r = call("GET", URL + "?start=bad&end=worse")
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


def test_adm01_ac6_admin_gets_200_and_no_store(adm_clean):
    r = report()
    assert r.status_code == 200
    assert "no-store" in r.headers.get("cache-control", "")


def test_adm01_ac6_new_student_signup_is_not_admin(adm_clean):
    r = report(user=new_student())
    assert r.status_code == 403


def test_adm01_sec_identity_headers_and_params_cannot_elevate(adm_clean):
    student = seeded("student")
    for headers in ({"X-Student-Id": "demo-admin"}, {"X-User-Id": "demo-admin"}, {"X-Role": "admin"}):
        r = call("GET", URL + "?role=admin&user_id=demo-admin", student, headers=headers)
        assert r.status_code == 403
    r = call("GET", URL, None, headers={"X-Student-Id": "demo-admin"})
    assert r.status_code == 401


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_adm01_sec_no_write_endpoint_for_events(adm_clean, method):
    before = sql("SELECT count(*) FROM analytics_event")[0][0]
    r = call(method, URL, seeded("admin"), json={"event_type": "chatbot_request"})
    assert r.status_code in (404, 405)
    r2 = call(method, "/api/admin/analytics/events", seeded("admin"), json={"event_type": "chatbot_request"})
    assert r2.status_code in (404, 405)
    assert sql("SELECT count(*) FROM analytics_event")[0][0] == before


# ---------------------------------------------------------------- AC7
@pytest.mark.parametrize("start,end", [
    ("2022-05-12", "2022-05-10"),                     # reversed
    ("2026-02-30", "2026-03-01"),                     # not a real date
    ("2022-13-01", "2022-13-02"),
    ("2026-1-5", "2026-1-6"),                         # not zero padded
    ("2026-11-05T00:00:00Z", "2026-11-06"),           # time part
    ("2026-11-05", "2026-11-06T00:00:00Z"),
    ("2026/11/05", "2026/11/06"),
    ("20261105", "20261106"),
    ("２０２６-11-05", "2026-11-06"),  # full-width digits
    ("٢٠٢٦-11-05", "2026-11-06"),  # Arabic-Indic digits
    ("abc", "def"),
    ("2024-01-01", "2025-01-01"),                     # 367 days inclusive
    ("2022-01-01", "2024-01-01"),
    ("2023-01-01", "2024-01-02"),                     # 367 days inclusive
    ("2019-12-31", "2020-01-02"),                     # starts before 2020-01-01
    ("2101-01-01", "2101-01-02"),                     # after 2100-12-31
    ("2100-12-31", "2101-01-01"),
    ("2019-12-30", "2019-12-31"),
])
def test_adm01_ac7_invalid_period_is_422(adm_clean, start, end):
    r = report(start, end)
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == {"code": "invalid_period", "message": INVALID_MESSAGE}


@pytest.mark.parametrize("raw", [
    "start=2026-11-01",                                  # only start
    "end=2026-11-05",                                    # only end
    "start=&end=2026-11-05",                             # empty
    "start=2026-11-01&end=",
    "start=&end=",
    "start=2026-11-01&start=2026-11-02&end=2026-11-05",  # repeated start
    "start=2026-11-01&end=2026-11-05&end=2026-11-06",    # repeated end
    "start=2026-11-01&start=2026-11-01&end=2026-11-05",  # identical repeats still rejected
    "start=%20&end=2026-11-05",                          # blank after trim
    "start=2026-11-01%00&end=2026-11-05",                # NUL suffix
    "start=2026-11-01&end=2026-11-05%0a2026-11-06",
])
def test_adm01_ac7_missing_empty_or_repeated_parameters_are_422(adm_clean, raw):
    r = report(raw_query=raw)
    assert r.status_code == 422, r.text
    assert code_of(r) == "invalid_period"


def test_adm01_ac7_sql_injection_text_is_422_and_harmless(adm_clean):
    r = report("2022-01-01'; DROP TABLE analytics_event;--", "2022-01-02")
    assert r.status_code == 422
    assert sql("SELECT count(*) FROM analytics_event") is not None


def test_adm01_ac7_366_days_ok_367_rejected(adm_clean):
    assert ok_report("2024-01-01", "2024-12-31")["period"]["days"] == 366    # leap year
    assert ok_report("2023-01-01", "2024-01-01")["period"]["days"] == 366    # 365 + 1 inclusive
    assert report("2023-01-01", "2024-01-02").status_code == 422             # 367


def test_adm01_ac7_whitespace_is_trimmed(adm_clean):
    seed_day("2022-05-10", chatbot_request=1)
    r = report(raw_query="start=%202022-05-10%20&end=%202022-05-10%20")
    assert r.status_code == 200, r.text
    assert r.json()["usage"]["chatbot_requests"] == 1


def test_adm01_ac7_edge_dates_accepted(adm_clean):
    assert ok_report("2020-01-01", "2020-01-02")["period"]["days"] == 2
    assert ok_report("2100-12-30", "2100-12-31")["status"] == "available"
    assert ok_report("2022-02-28", "2022-02-28")["period"]["days"] == 1
    assert ok_report("2024-02-29", "2024-02-29")["period"]["days"] == 1


def test_adm01_ac7_unknown_params_ignored_and_future_end_allowed(adm_clean):
    r = report(raw_query="start=2099-01-01&end=2099-01-03&foo=bar&user_id=x")
    assert r.status_code == 200
    body = r.json()
    assert body["usage"] == {"chatbot_requests": 0, "practice_completions": 0, "has_activity": False}
    assert body["period"]["days"] == 3


def test_adm01_ac7_invalid_period_does_not_query_events(adm_clean, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("count_events must not run for an invalid period")

    monkeypatch.setattr("analytics.service.count_events", boom)
    assert report("2022-05-12", "2022-05-10").status_code == 422


# ---------------------------------------------------------------- AC8
def test_adm01_ac8_default_period_is_last_7_utc_days():
    r = report()
    assert r.status_code == 200, r.text
    p = r.json()["period"]
    today = datetime.now(timezone.utc).date()
    assert p["days"] == 7 and p["timezone"] == "UTC"
    assert p["end"] in {today.isoformat(), (today - timedelta(days=1)).isoformat()}  # tolerate midnight race
    end = date.fromisoformat(p["end"])
    assert p["start"] == (end - timedelta(days=6)).isoformat()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["start"])


def test_adm01_ac8_parse_period_default_with_injected_today():
    from analytics.period import parse_period

    p = parse_period(None, None, today=date(2026, 11, 5))
    assert (p.start, p.end, p.days) == (date(2026, 10, 30), date(2026, 11, 5), 7)


def test_adm01_ac8_parse_period_unit_bounds_and_properties():
    from analytics.period import Period, parse_period
    from errors import ApiError

    p = parse_period("2026-11-05", "2026-11-07")
    assert isinstance(p, Period) and p.days == 3
    assert p.start_utc == datetime(2026, 11, 5, tzinfo=timezone.utc)
    assert p.end_exclusive_utc == datetime(2026, 11, 8, tzinfo=timezone.utc)
    assert parse_period(" 2026-11-05 ", "2026-11-05\t").days == 1
    for bad in [("2026-11-05", None), (None, "2026-11-05"), ("", "2026-11-05"), ("2026-02-30", "2026-03-01"),
                ("2026-11-06", "2026-11-05"), ("2024-01-01", "2025-01-01"), ("2019-12-31", "2020-01-01"),
                ("2100-12-31", "2101-01-01")]:
        with pytest.raises(ApiError):
            parse_period(*bad)
    with pytest.raises(Exception):
        p.start = date(2020, 1, 1)  # frozen dataclass


def test_adm01_ac8_count_events_returns_all_eight_keys(adm_clean):
    from analytics.period import parse_period
    from analytics.service import count_events
    from auth.db import engine_for
    from auth.settings import load_settings
    from sqlalchemy.orm import Session

    seed_day("2022-10-01", chatbot_request=2)
    with Session(engine_for(load_settings().database_url)) as db:
        counts = count_events(db, parse_period("2022-10-01", "2022-10-01"))
    assert set(counts) == set(ALL_TYPES)
    assert counts["chatbot_request"] == 2
    assert all(v == 0 for k, v in counts.items() if k != "chatbot_request")
