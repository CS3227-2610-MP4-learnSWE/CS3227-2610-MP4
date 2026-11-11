"""ADM-07 AC1 (access, no-store), AC2 (validation and its order), AC4 (privacy), cross-role tests.

Contract: workflow/specs/ADM-07/plan.md "API endpoints" and "Errors". Phase 2 only.
"""
import json

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, analytics_student, analytics_teacher, disabled_admin, tracked_users  # noqa: F401
from adm01_grading_helpers import chat_item, new_window
from adm01_helpers import day, url
from adm02_helpers import actor, uid
from adm07_helpers import (DAILY, HEALTH, HOURLY, NEW_ENDPOINTS, USERS, all_keys, err, get, ok)
from auth_helpers import call

BASE = "/api/admin/analytics"
USAGE = BASE + "/usage"
DATA_KEYS = ("period_start", "buckets", "rows", "chatbot_failure", "attempts_funnel", "totals", "recording_started_on")


def params():
    return {"period_start": day(5), "period_end": day(0)}


def users_params(**extra):
    return {**params(), "role": "student", **extra}


def p_for(path, **extra):
    return users_params(**extra) if path == USERS else {**params(), **extra}


# ------------------------------------------------------------------ AC1

@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac1_unauthenticated_gets_401_and_no_data(path):
    r = call("GET", url(path, **p_for(path)), None)
    assert r.status_code == 401, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    assert not any(k in r.text for k in DATA_KEYS)


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac1_student_and_teacher_get_403_and_no_data(path, analytics_student, analytics_teacher):
    for who in (analytics_student, analytics_teacher):
        r = call("GET", url(path, **p_for(path)), who)
        assert r.status_code == 403, (path, r.text)
        assert "no-store" in r.headers.get("cache-control", ""), r.headers
        assert not any(k in r.text for k in DATA_KEYS)


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac1_disabled_admin_is_rejected(path, disabled_admin):
    r = call("GET", url(path, **p_for(path)), disabled_admin)
    assert r.status_code in (401, 403), r.text
    assert not any(k in r.text for k in DATA_KEYS)


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac1_admin_gets_200_with_no_store(path, analytics_admin):
    r = call("GET", url(path, **p_for(path)), analytics_admin)
    assert r.status_code == 200, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    assert r.json()["period_start"] == day(5) and r.json()["period_end"] == day(0)


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac1_authentication_and_role_are_checked_before_validation(path, analytics_student):
    bad = {"period_start": "garbage", "period_end": "garbage", "role": "x", "sort": "x", "limit": "x"}
    assert call("GET", url(path, **bad), None).status_code == 401
    assert call("GET", url(path, **bad), analytics_student).status_code == 403


def test_adm07_ac1_non_admin_of_every_role_cannot_use_usage_include_rows_either(analytics_student, analytics_teacher):
    for who in (analytics_student, analytics_teacher):
        assert call("GET", url(USAGE, **params(), include_rows="false"), who).status_code == 403
        assert call("GET", url(USAGE, **params(), include_rows="garbage"), who).status_code == 403


def test_adm07_cross_user_a_second_admin_sees_the_same_report_and_no_session_state_leaks(analytics_admin):
    other = actor("admin")
    a = call("GET", url(HEALTH, **params()), analytics_admin).json()
    b = call("GET", url(HEALTH, **params()), other).json()
    a.pop("as_of"), b.pop("as_of")
    assert a == b


# ------------------------------------------------------------------ AC2 period validation

INVALID_DATES = ["", "   ", "2026-1-05", "2026/11/09", "20261109", "2026-13-01", "2026-02-30", "2026-11-09T00:00:00Z",
                 "tomorrow", "2026-11-09x"]


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
@pytest.mark.parametrize("bad", INVALID_DATES)
def test_adm07_ac2_malformed_dates_are_invalid_date(path, bad, analytics_admin):
    err(call("GET", url(path, **p_for(path, period_start=bad)), analytics_admin), "invalid_date")
    err(call("GET", url(path, **p_for(path, period_end=bad)), analytics_admin), "invalid_date")


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
@pytest.mark.parametrize("missing", ["period_start", "period_end"])
def test_adm07_ac2_missing_date_is_invalid_date(path, missing, analytics_admin):
    err(call("GET", url(path, **p_for(path, **{missing: None})), analytics_admin), "invalid_date")


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac2_dates_are_trimmed_and_echoed(path, analytics_admin):
    r = call("GET", url(path, **p_for(path, period_start=f"  {day(5)} ", period_end=f"\t{day(0)}  ")), analytics_admin)
    assert r.status_code == 200, r.text
    assert (r.json()["period_start"], r.json()["period_end"]) == (day(5), day(0))


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_ac2_period_order_and_length(path, analytics_admin):
    err(call("GET", url(path, **p_for(path, period_start=day(0), period_end=day(1))), analytics_admin), "period_order")
    ok_366 = call("GET", url(path, **p_for(path, period_start=day(365), period_end=day(0))), analytics_admin)
    assert ok_366.status_code == 200, ok_366.text
    err(call("GET", url(path, **p_for(path, period_start=day(366), period_end=day(0))), analytics_admin),
        "period_too_long")


@pytest.mark.parametrize("path", [HOURLY, HEALTH, DAILY])
def test_adm07_ac2_single_day_period_is_valid(path, analytics_admin):
    assert call("GET", url(path, **p_for(path, period_start=day(2), period_end=day(2))), analytics_admin).status_code == 200


# ------------------------------------------------------------------ AC2 chatbot-users parameters

@pytest.mark.parametrize("role", [None, "", "admin", "students", "all", "  "])
def test_adm07_ac2_invalid_or_missing_role(role, analytics_admin):
    err(call("GET", url(USERS, **params(), role=role), analytics_admin), "invalid_role")


@pytest.mark.parametrize("role", [" Student ", "STUDENT", "teacher", " TEACHER\t"])
def test_adm07_ac2_role_is_trimmed_and_case_insensitive(role, analytics_admin):
    r = call("GET", url(USERS, **params(), role=role), analytics_admin)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == role.strip().lower()


@pytest.mark.parametrize("extra", [{"sort": "email"}, {"sort": ""}, {"order": "up"}, {"order": ""},
                                   {"sort": "name", "order": "sideways"}])
def test_adm07_ac2_invalid_sort_or_order(extra, analytics_admin):
    err(call("GET", url(USERS, **users_params(**extra)), analytics_admin), "invalid_sort")


@pytest.mark.parametrize("sort", ["unsuccessful", "successful", "name", "failure_rate", " Failure_Rate ", "NAME"])
@pytest.mark.parametrize("order", ["asc", "desc", " DESC "])
def test_adm07_ac2_valid_sort_and_order_are_normalised(sort, order, analytics_admin):
    r = call("GET", url(USERS, **users_params(sort=sort, order=order)), analytics_admin)
    assert r.status_code == 200, r.text
    assert (r.json()["sort"], r.json()["order"]) == (sort.strip().lower(), order.strip().lower())


@pytest.mark.parametrize("extra", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"limit": "abc"}, {"limit": "1.5"},
                                   {"offset": -1}, {"offset": "x"}, {"limit": ""}])
def test_adm07_ac2_invalid_paging(extra, analytics_admin):
    err(call("GET", url(USERS, **users_params(**extra)), analytics_admin), "invalid_paging")


def test_adm07_ac2_paging_bounds_are_accepted_and_defaults_apply(analytics_admin):
    one = call("GET", url(USERS, **users_params(limit=1, offset=0)), analytics_admin)
    big = call("GET", url(USERS, **users_params(limit=100, offset=5)), analytics_admin)
    assert one.status_code == 200 and big.status_code == 200
    default = call("GET", url(USERS, **users_params()), analytics_admin).json()
    assert (default["limit"], default["offset"], default["sort"], default["order"]) == (10, 0, "unsuccessful", "desc")


def test_adm07_ac2_validation_order_dates_then_order_then_span_then_role_then_sort_then_paging(analytics_admin):
    bad_all = {"role": "x", "sort": "x", "limit": 0}
    err(call("GET", url(USERS, period_start="bad", period_end=day(0), **bad_all), analytics_admin), "invalid_date")
    err(call("GET", url(USERS, period_start=day(0), period_end=day(1), **bad_all), analytics_admin), "period_order")
    err(call("GET", url(USERS, period_start=day(400), period_end=day(0), **bad_all), analytics_admin),
        "period_too_long")
    err(call("GET", url(USERS, **params(), **bad_all), analytics_admin), "invalid_role")
    err(call("GET", url(USERS, **params(), role="student", sort="x", limit=0), analytics_admin), "invalid_sort")
    err(call("GET", url(USERS, **params(), role="student", limit=0), analytics_admin), "invalid_paging")


@pytest.mark.parametrize("value", ["true", "false"])
def test_adm07_ac2_include_rows_accepts_true_false(value, analytics_admin):
    r = call("GET", url(USAGE, **params(), include_rows=value), analytics_admin)
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("value", ["yes", "1", "0", "", "null", "maybe"])
def test_adm07_ac2_include_rows_other_values_are_invalid(value, analytics_admin):
    err(call("GET", url(USAGE, **params(), include_rows=value), analytics_admin), "invalid_include_rows")


def test_adm07_ac2_include_rows_is_validated_after_the_period(analytics_admin):
    err(call("GET", url(USAGE, period_start="bad", period_end=day(0), include_rows="x"), analytics_admin),
        "invalid_date")


# ------------------------------------------------------------------ AC4 privacy

def test_adm07_ac4_no_endpoint_response_contains_chat_text_email_or_ip_fields(analytics_admin, tracked_users):
    w = new_window()
    s = actor("student")
    tracked_users.append(s)
    marker = "PRIVATE-MARKER-" + uid()
    chat_item(s, w.at(1), request_text=marker + "-req", response_text=marker + "-resp", context_text=marker + "-ctx")
    texts = []
    for path in (HEALTH, HOURLY, DAILY, USERS):
        extra = {"role": "student"} if path == USERS else {}
        r = get(path, analytics_admin, w, **extra)
        assert r.status_code == 200, r.text
        texts.append(r.text)
        assert marker not in r.text
        banned = [k for k in all_keys(r.json()) if k.lower() in {"email", "ip", "ip_address", "request_text",
                                                                "response_text", "context_text", "prompt", "reply",
                                                                "password", "token", "cookie"}]
        assert banned == [], (path, banned)
        assert s.email not in r.text
    assert "@" not in json.dumps([t for t in texts])


def test_adm07_ac4_only_chatbot_users_returns_user_ids(analytics_admin, tracked_users):
    w = new_window()
    s = actor("student")
    tracked_users.append(s)
    from adm01_grading_helpers import chat_row
    chat_row(s, w.at(1))
    for path in (HEALTH, HOURLY, DAILY):
        assert str(s) not in get(path, analytics_admin, w).text, path
    assert str(s) in get(USERS, analytics_admin, w, role="student").text
