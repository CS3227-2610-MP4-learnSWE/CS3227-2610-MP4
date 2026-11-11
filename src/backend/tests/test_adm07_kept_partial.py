"""ADM-07 AC39 on the kept endpoints /generation and /quality (and /usage), which gain `data_starts_on`.

Contract: plan.md "Window rule and coverage". Phase 2: the rate-limited fields of /generation are not
collected yet, so each workflow entry carries `rate_limited` null and `rate_limited_state` unavailable.
"""
from datetime import timedelta

from adm01_fixtures import privacy_scanner, analytics_admin, recording_start, tracked_users  # noqa: F401
from adm01_grading_helpers import chat_item, gen_row, new_window
from adm02_helpers import actor
from adm07_helpers import ok

BASE = "/api/admin/analytics"


def test_adm07_ac39_generation_counts_only_the_covered_part_and_sets_data_starts_on(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    t = actor("teacher")
    tracked_users.append(t)
    recording_start.set(w.start_dt + timedelta(days=1, hours=6))
    gen_row(t, "study_notes", w.at(60), "failure")  # before recording: excluded
    gen_row(t, "study_notes", w.start_dt + timedelta(days=1, hours=1), "success")
    gen_row(t, "study_notes", w.start_dt + timedelta(days=2, hours=1), "failure")
    body = ok(BASE + "/generation", analytics_admin, w)
    assert body["data_starts_on"] == (w.first + timedelta(days=1)).isoformat()
    notes = {x["workflow"]: x for x in body["workflows"]}["study_notes"]
    assert notes["state"] == "available"
    assert (notes["attempts"], notes["successful"], notes["unsuccessful"]) == (2, 1, 1)


def test_adm07_ac39_generation_whole_period_before_recording_stays_unavailable(analytics_admin, recording_start):
    w = new_window(2)
    recording_start.set(w.end_dt + timedelta(days=3))
    body = ok(BASE + "/generation", analytics_admin, w)
    for row in body["workflows"]:
        assert row["state"] == "unavailable" and row["reason"] == "period_before_recording"


def test_adm07_phase2_generation_rate_limited_is_not_collected(analytics_admin):
    w = new_window()
    for row in ok(BASE + "/generation", analytics_admin, w)["workflows"]:
        assert row["rate_limited"] is None
        assert row["rate_limited_state"] == {"state": "unavailable", "reason": "not_collected"}
        assert row["requests"] == row["attempts"]


def test_adm07_ac39_quality_counts_only_the_covered_part_and_sets_data_starts_on(analytics_admin, tracked_users, recording_start):
    w = new_window(3)
    s = actor("student")
    tracked_users.append(s)
    recording_start.set(w.start_dt + timedelta(days=1, hours=6))
    chat_item(s, w.at(60))  # before recording: excluded
    chat_item(s, w.start_dt + timedelta(days=1, hours=1))
    chat_item(s, w.start_dt + timedelta(days=2, hours=1))
    body = ok(BASE + "/quality", analytics_admin, w, workflow="student_exercise")
    assert body["data_starts_on"] == (w.first + timedelta(days=1)).isoformat()
    assert body["items"]["total"] == 2 and body["grades"]["pending_count"] == 2
    assert body["grades"]["state"] in ("available", "not_applicable")


def test_adm07_ac39_quality_whole_period_before_recording_stays_unavailable(analytics_admin, recording_start):
    w = new_window(2)
    recording_start.set(w.end_dt + timedelta(days=3))
    body = ok(BASE + "/quality", analytics_admin, w, workflow="student_exercise")
    assert body["grades"]["state"] == "unavailable" and body["grades"]["reason"] == "period_before_recording"
    assert body["response_time"]["state"] == "unavailable"


def test_adm07_ac39_kept_endpoints_report_null_data_starts_on_when_fully_covered(analytics_admin):
    w = new_window()
    for path, extra in (("/usage", {}), ("/generation", {}), ("/quality", {"workflow": "student_exercise"})):
        assert ok(BASE + path, analytics_admin, w, **extra)["data_starts_on"] is None, path
