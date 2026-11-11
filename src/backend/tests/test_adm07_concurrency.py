"""ADM-07 concurrent-request and cross-user tests for the new read endpoints (task P2-3).

Two Refresh-style loads at the same instant must return consistent data; a non-admin of every role
must never receive data, even while an admin load runs at the same time.
"""
from datetime import timedelta

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, analytics_student, analytics_teacher, tracked_users  # noqa: F401
from adm01_grading_helpers import attempt_row, chat_row, gen_row, new_window
from adm01_helpers import url
from adm02_helpers import actor, race, uid
from adm07_helpers import DAILY, HEALTH, HOURLY, NEW_ENDPOINTS, USERS, fixed_now  # noqa: F401
from auth_helpers import call


def seed(tracked):
    w = new_window()
    s, t = actor("student"), actor("teacher")
    tracked.extend([s, t])
    for i in range(6):
        chat_row(s, w.at(i + 1), "success" if i % 3 else "failure")
    gen_row(t, "study_notes", w.at(10), "success")
    gen_row(t, "mcq_batch", w.at(11), "failure")
    attempt_row(s, "att-" + uid(), w.at(20), w.at(30))
    return w


def req(path, w, user):
    extra = {"role": "student"} if path == USERS else {}
    return lambda: call("GET", url(path, **w.params, **extra), user)


@pytest.mark.parametrize("path", NEW_ENDPOINTS)
def test_adm07_concurrent_loads_of_one_endpoint_return_identical_data(path, analytics_admin, tracked_users, fixed_now):
    w = seed(tracked_users)
    fixed_now(w.at(600))
    results = race(*[req(path, w, analytics_admin) for _ in range(6)])
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    bodies = [r.json() for r in results]
    assert all(b == bodies[0] for b in bodies)
    assert all("no-store" in r.headers.get("cache-control", "") for r in results)


def test_adm07_concurrent_two_admins_loading_the_whole_hub_see_the_same_report(analytics_admin, tracked_users, fixed_now):
    w = seed(tracked_users)
    fixed_now(w.at(600))
    other = actor("admin")
    ops = [req(p, w, who) for p in NEW_ENDPOINTS for who in (analytics_admin, other)]
    results = race(*ops)
    assert all(r.status_code == 200 for r in results)
    by_path = {}
    for r, op_path in zip(results, [p for p in NEW_ENDPOINTS for _ in range(2)]):
        by_path.setdefault(op_path, []).append(r.json())
    assert all(a == b for a, b in by_path.values())


def test_adm07_concurrent_tile_and_chart_totals_agree_in_one_instant(analytics_admin, tracked_users, fixed_now):
    w = seed(tracked_users)
    fixed_now(w.at(600))
    health, hourly = race(req(HEALTH, w, analytics_admin), req(HOURLY, w, analytics_admin))
    h, c = health.json(), hourly.json()
    assert h["as_of"] == c["as_of"]
    assert c["totals"]["total"] == h["chatbot_failure"]["total"] + h["generation_failure"]["total"]
    assert c["totals"]["failed"] == h["chatbot_failure"]["failed"] + h["generation_failure"]["failed"]


def test_adm07_cross_user_non_admins_get_403_while_an_admin_load_runs(analytics_admin, analytics_student, analytics_teacher, tracked_users):
    w = seed(tracked_users)
    ops, expected = [], []
    for path in NEW_ENDPOINTS:
        for who, status in ((analytics_admin, 200), (analytics_student, 403), (analytics_teacher, 403), (None, 401)):
            ops.append(req(path, w, who))
            expected.append(status)
    results = race(*ops)
    for r, status in zip(results, expected):
        assert r.status_code == status, (r.status_code, status, r.text)
        if status != 200:
            assert "period_start" not in r.text and "buckets" not in r.text and "rows" not in r.text


def test_adm07_cross_user_a_student_cannot_see_another_students_chatbot_row(analytics_student, tracked_users):
    w = seed(tracked_users)
    other_student = actor("student")
    tracked_users.append(other_student)
    chat_row(other_student, w.at(5), "failure")
    r = call("GET", url(USERS, **w.params, role="student"), analytics_student)
    assert r.status_code == 403 and str(other_student) not in r.text
