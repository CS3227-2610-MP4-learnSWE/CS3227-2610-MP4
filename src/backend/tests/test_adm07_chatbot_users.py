"""ADM-07 AC24-AC26, AC38, AC39 for GET /api/admin/analytics/chatbot-users, and /usage include_rows.

Contract: workflow/specs/ADM-07/plan.md "GET /chatbot-users" and "Kept, extended or new".
"""
from datetime import timedelta

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, recording_start, tracked_users  # noqa: F401
from adm01_grading_helpers import chat_row, new_window, set_name
from adm02_helpers import actor, uid
from adm07_helpers import USERS, fixed_now, ok, stamp  # noqa: F401

ROW_KEYS = {"user_id", "name", "successful", "unsuccessful", "failure_rate_percent"}


def person(tracked, name, ok_n=0, bad_n=0, w=None):
    u = actor("student")
    tracked.append(u)
    set_name(u, name)
    for i in range(ok_n):
        chat_row(u, w.at(1 + i), "success")
    for i in range(bad_n):
        chat_row(u, w.at(100 + i), "failure")
    return u


def users(admin, w, **extra):
    extra.setdefault("role", "student")
    return ok(USERS, admin, w, **extra)


def names(body):
    return [r["name"] for r in body["rows"]]


def test_adm07_ac25_exact_shape_and_defaults(analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    person(tracked_users, f"Alice {tag}", 5, 4, w)
    body = users(analytics_admin, w)
    assert set(body) >= {"period_start", "period_end", "recording_started_on", "data_starts_on", "as_of", "in_progress",
                         "role", "state", "reason", "totals", "all_users_total", "sort", "order", "limit", "offset",
                         "total_users", "rows"}
    assert body["role"] == "student" and body["state"] == "available" and body["reason"] is None
    assert (body["sort"], body["order"], body["limit"], body["offset"]) == ("unsuccessful", "desc", 10, 0)
    assert body["data_starts_on"] is None and body["in_progress"] == 0
    assert set(body["rows"][0]) == ROW_KEYS
    assert body["rows"][0] == {**body["rows"][0], "name": f"Alice {tag}", "successful": 5, "unsuccessful": 4,
                               "failure_rate_percent": 44.4}
    assert body["totals"] == {"successful": 5, "unsuccessful": 4} and body["total_users"] == 1


def test_adm07_ac25_default_order_is_unsuccessful_desc_then_name_ci_then_user_id(analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    person(tracked_users, f"bob {tag}", 1, 2, w)
    person(tracked_users, f"Alice {tag}", 1, 2, w)
    person(tracked_users, f"Zed {tag}", 0, 5, w)
    person(tracked_users, f"Carl {tag}", 3, 0, w)
    t1 = person(tracked_users, f"Twin {tag}", 1, 1, w)
    t2 = person(tracked_users, f"Twin {tag}", 1, 1, w)
    body = users(analytics_admin, w)
    assert names(body)[:3] == [f"Zed {tag}", f"Alice {tag}", f"bob {tag}"]
    assert [r["user_id"] for r in body["rows"][3:5]] == sorted([str(t1), str(t2)])
    assert names(body)[-1] == f"Carl {tag}"


@pytest.mark.parametrize("sort,order", [("name", "asc"), ("name", "desc"), ("successful", "asc"),
                                        ("successful", "desc"), ("unsuccessful", "asc")])
def test_adm07_ac25_each_sort_column_and_direction(sort, order, analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    person(tracked_users, f"anna {tag}", 5, 1, w)
    person(tracked_users, f"Ben {tag}", 2, 4, w)
    person(tracked_users, f"cara {tag}", 9, 0, w)
    body = users(analytics_admin, w, sort=sort, order=order)
    key = {"name": lambda r: r["name"].lower(), "successful": lambda r: r["successful"],
           "unsuccessful": lambda r: r["unsuccessful"]}[sort]
    got = [key(r) for r in body["rows"]]
    assert got == sorted(got, reverse=(order == "desc"))
    assert (body["sort"], body["order"]) == (sort, order)


def test_adm07_ac25_failure_rate_sort_breaks_ties_by_unsuccessful_desc_then_name(analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    person(tracked_users, f"A {tag}", 1, 1, w)  # 50 %, 1 failure
    person(tracked_users, f"B {tag}", 2, 2, w)  # 50 %, 2 failures
    person(tracked_users, f"C {tag}", 0, 1, w)  # 100 %
    person(tracked_users, f"D {tag}", 3, 0, w)  # 0 %
    desc = users(analytics_admin, w, sort="failure_rate", order="desc")
    assert names(desc) == [f"C {tag}", f"B {tag}", f"A {tag}", f"D {tag}"]
    asc = users(analytics_admin, w, sort="failure_rate", order="asc")
    assert names(asc)[0] == f"D {tag}" and names(asc)[-1] == f"C {tag}"
    assert names(asc)[1:3] == [f"B {tag}", f"A {tag}"]  # spec: ties by unsuccessful descending first


def test_adm07_ac25_failure_rate_is_rounded_half_up(analytics_admin, tracked_users):
    w = new_window()
    person(tracked_users, "Half " + uid()[:6], 15, 1, w)  # 1/16 = 6.25 -> 6.3
    person(tracked_users, "Third " + uid()[:6], 2, 1, w)
    rows = {r["name"].split()[0]: r for r in users(analytics_admin, w)["rows"]}
    assert rows["Half"]["failure_rate_percent"] == 6.3 and rows["Third"]["failure_rate_percent"] == 33.3


def test_adm07_ac25_paging_and_totals_cover_all_users_not_just_the_page(analytics_admin, tracked_users):
    w = new_window()
    tag = uid()[:6]
    for i in range(12):
        person(tracked_users, f"User{i:02d} {tag}", 1, 0, w)
    p1 = users(analytics_admin, w, sort="name", order="asc", limit=5, offset=0)
    p2 = users(analytics_admin, w, sort="name", order="asc", limit=5, offset=5)
    p3 = users(analytics_admin, w, sort="name", order="asc", limit=5, offset=10)
    beyond = users(analytics_admin, w, sort="name", order="asc", limit=5, offset=50)
    assert names(p1) == [f"User{i:02d} {tag}" for i in range(5)]
    assert names(p2) == [f"User{i:02d} {tag}" for i in range(5, 10)]
    assert len(p3["rows"]) == 2 and beyond["rows"] == []
    for b in (p1, p2, p3, beyond):
        assert b["total_users"] == 12 and b["totals"] == {"successful": 12, "unsuccessful": 0}
    default = users(analytics_admin, w)
    assert len(default["rows"]) == 10


def test_adm07_ac25_users_without_requests_in_the_period_have_no_row_and_empty_period_is_zero(analytics_admin, tracked_users):
    w, other = new_window(), new_window()
    tag = uid()[:6]
    person(tracked_users, f"Elsewhere {tag}", 3, 0, other)
    idle = actor("student")
    body = users(analytics_admin, w)
    assert body["rows"] == [] and body["total_users"] == 0 and body["state"] == "available"
    assert body["totals"] == {"successful": 0, "unsuccessful": 0}  # a real zero
    assert str(idle) not in str(body)


def test_adm07_ac25_period_boundaries_are_start_inclusive_end_exclusive(analytics_admin, tracked_users):
    w = new_window()
    u = actor("student")
    tracked_users.append(u)
    chat_row(u, w.start_dt - timedelta(seconds=1), "failure")
    chat_row(u, w.start_dt, "success")
    chat_row(u, w.end_dt - timedelta(seconds=1), "success")
    chat_row(u, w.end_dt, "failure")
    r = users(analytics_admin, w)["rows"][0]
    assert (r["successful"], r["unsuccessful"]) == (2, 0)


# ------------------------------------------------------------------ AC26 teachers and totals

def test_adm07_ac26_teacher_role_is_unavailable_no_source_and_returns_no_student_data(analytics_admin, tracked_users):
    # P2-13: the earlier version patched queries.chatbot_users to raise; that assumed the route never calls the
    # query function for teachers, which the plan does not say. Behaviour only is asserted now.
    w = new_window()
    person(tracked_users, "Stu " + uid()[:6], 2, 1, w)
    body = users(analytics_admin, w, role="teacher")
    assert body["role"] == "teacher" and body["state"] == "unavailable" and body["reason"] == "no_source"
    assert body["totals"] == {"successful": None, "unsuccessful": None}
    assert body["rows"] == [] and body["total_users"] is None


def test_adm07_ac26_all_users_total_is_unavailable_no_source_for_both_roles(analytics_admin, tracked_users):
    w = new_window()
    person(tracked_users, "Stu " + uid()[:6], 2, 1, w)
    for role in ("student", "teacher"):
        t = users(analytics_admin, w, role=role)["all_users_total"]
        # P2-13: the plan example lists four keys; a per-metric `data_starts_on` is also allowed (spec: every metric carries it)
        assert {k: v for k, v in t.items() if k != "data_starts_on"} == {
            "state": "unavailable", "reason": "no_source", "successful": None, "unsuccessful": None}


# ------------------------------------------------------------------ AC38 / AC39

def test_adm07_ac38_in_progress_excluded_and_expired_counts_as_unsuccessful(analytics_admin, tracked_users, fixed_now):
    w = new_window()
    now = fixed_now(w.at(10 * 60))
    a, b = actor("student"), actor("student")
    tracked_users.extend([a, b])
    set_name(a, "Has " + uid()[:6])
    set_name(b, "OnlyPending " + uid()[:6])
    chat_row(a, w.at(30), "success")
    chat_row(a, now - timedelta(seconds=120), "pending")  # expired: unsuccessful
    chat_row(a, now - timedelta(seconds=119), "pending")  # in progress
    chat_row(b, now - timedelta(seconds=5), "pending")  # only request in progress: no row
    body = users(analytics_admin, w)
    assert body["in_progress"] == 2 and body["as_of"] == stamp(now)
    assert [(r["user_id"], r["successful"], r["unsuccessful"]) for r in body["rows"]] == [(str(a), 1, 1)]
    assert body["total_users"] == 1 and body["totals"] == {"successful": 1, "unsuccessful": 1}


def test_adm07_ac39_partial_coverage_for_students(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    u = actor("student")
    tracked_users.append(u)
    recording_start.set(w.start_dt + timedelta(days=2, hours=4))
    chat_row(u, w.at(60), "failure")  # excluded
    chat_row(u, w.start_dt + timedelta(days=2, hours=1), "success")
    body = users(analytics_admin, w)
    assert body["data_starts_on"] == (w.first + timedelta(days=2)).isoformat()
    assert body["totals"] == {"successful": 1, "unsuccessful": 0}


def test_adm07_ac39_whole_period_before_recording_is_unavailable(analytics_admin, recording_start):
    w = new_window()
    recording_start.set(w.end_dt + timedelta(days=4))
    body = users(analytics_admin, w)
    assert body["state"] == "unavailable" and body["reason"] == "period_before_recording"
    assert body["rows"] == [] and body["totals"] == {"successful": None, "unsuccessful": None}


# ------------------------------------------------------------------ /usage include_rows (AC24, kept endpoint)

def test_adm07_ac24_usage_include_rows_false_empties_rows_and_changes_nothing_else(analytics_admin, tracked_users):
    w = new_window()
    person(tracked_users, "Row " + uid()[:6], 3, 2, w)
    full = ok("/api/admin/analytics/usage", analytics_admin, w)
    default = ok("/api/admin/analytics/usage", analytics_admin, w, include_rows="true")
    lean = ok("/api/admin/analytics/usage", analytics_admin, w, include_rows="false")
    assert full == default and len(full["chatbot"]["student"]["rows"]) == 1
    group = lean["chatbot"]["student"]
    assert group["rows"] == [] and group["rows_truncated"] is False
    assert (group["successful"], group["unsuccessful"]) == (3, 2)
    for body in (full, lean):
        body["chatbot"]["student"].pop("rows"), body["chatbot"]["student"].pop("rows_truncated")
    assert full == lean
