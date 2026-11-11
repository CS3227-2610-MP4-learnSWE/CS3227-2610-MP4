"""ADM-07 phase 4 reports switch from not_collected to real values (AC10, AC13, AC23, AC35, AC38, AC40, AC41).

Contract: workflow/specs/ADM-07/plan.md "[P4]" rows of /health, /hourly, /daily, /generation, "Window rule and
coverage", "In-progress rule", "Retention". Each test uses its own far-future window; rows are written by the
documented hooks or inserted into the new tables directly. No AI call is made.
"""
from datetime import datetime, timedelta, timezone

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, tracked_users  # noqa: F401
from adm01_grading_helpers import chat_row, gen_row, new_window
from adm02_helpers import actor, uid
from adm07_helpers import DAILY, HEALTH, HOURLY, fixed_now, ok  # noqa: F401
from adm07_p4_helpers import CATEGORIES, event_cleanup, insert_log, meta  # noqa: F401
from auth_helpers import sql

GENERATION = "/api/admin/analytics/generation"
UTC = timezone.utc


def student(tracked):
    u = actor("student")
    tracked.append(u)
    return u


def teacher(tracked):
    u = actor("teacher")
    tracked.append(u)
    return u


def dates(w, n):
    return [(w.first + timedelta(days=i)).isoformat() for i in range(n)]


# ================================================================== AC10 / AC40 rate-limited in /health and /generation

def seed_rate_limited(w, tracked):
    from feature_analytics import recording

    t = teacher(tracked)
    gen_row(t, "study_notes", w.at(1), "success")
    gen_row(t, "study_notes", w.at(2), "failure")
    gen_row(t, "mcq_batch", w.at(3), "success")
    recording.record_generation_rate_limited(workflow="study_notes", occurred_at=w.at(4))
    recording.record_generation_rate_limited(workflow="mcq_batch", occurred_at=w.at(5))
    recording.record_generation_rate_limited(workflow="mcq_batch", occurred_at=w.at(6))


def test_adm07_ac10_rate_limited_tile_counts_request_log_rows_with_the_category(analytics_admin, tracked_users):
    w = new_window()
    seed_rate_limited(w, tracked_users)
    rl = ok(HEALTH, analytics_admin, w)["rate_limited"]
    assert rl["state"] == "available" and rl["reason"] is None
    assert rl["count"] == 3
    assert rl["total_requests"] == 6  # 3 attempts + 3 refused
    assert rl["since"] == datetime.fromisoformat(
        sql("SELECT value FROM analytics_meta WHERE key='request_log_categories_started_at'")[0][0]).astimezone(UTC).date().isoformat()


def test_adm07_ac10_chatbot_rate_limited_rows_count_too(analytics_admin):
    w = new_window()
    insert_log("chatbot", w.at(1), "failure", "rate_limited", 40)
    insert_log("chatbot", w.at(2), "failure", "timeout", 120000)
    insert_log("chatbot", w.at(3), "success", None, 900)
    rl = ok(HEALTH, analytics_admin, w)["rate_limited"]
    assert (rl["count"], rl["total_requests"]) == (1, 3)


def test_adm07_ac10_a_category_other_than_rate_limited_is_not_counted(analytics_admin):
    w = new_window()
    for cat in ("timeout", "invalid_output", "upstream", "unclassified"):
        insert_log("generation_notes", w.at(5), "failure", cat, 100)
    rl = ok(HEALTH, analytics_admin, w)["rate_limited"]
    assert rl["state"] == "available" and rl["count"] == 0 and rl["total_requests"] == 4


def test_adm07_ac10_rows_at_the_window_edges(analytics_admin):
    w = new_window()
    insert_log("generation_mcq", w.start_dt - timedelta(seconds=1))
    insert_log("generation_mcq", w.start_dt)
    insert_log("generation_mcq", w.end_dt - timedelta(seconds=1))
    insert_log("generation_mcq", w.end_dt)
    rl = ok(HEALTH, analytics_admin, w)["rate_limited"]
    assert (rl["count"], rl["total_requests"]) == (2, 2)


def test_adm07_ac10_a_period_starting_before_the_category_start_counts_only_the_part_from_that_date(
        analytics_admin, meta):
    w = new_window(3)
    meta.set("request_log_categories_started_at", w.start_dt + timedelta(days=1, hours=6))
    insert_log("generation_notes", w.at(60))  # day 0: before the start, not counted
    insert_log("generation_notes", w.start_dt + timedelta(days=1, hours=1))  # day 1 (covered date, earlier hour)
    insert_log("generation_notes", w.start_dt + timedelta(days=2, hours=1))
    body = ok(HEALTH, analytics_admin, w)
    rl = body["rate_limited"]
    assert rl["state"] == "available"
    assert rl["since"] == (w.first + timedelta(days=1)).isoformat()
    assert rl["data_starts_on"] == (w.first + timedelta(days=1)).isoformat()
    assert rl["count"] == 2  # coverage is by whole UTC date: the date itself is covered (ADM-01 recording rule)
    assert body["data_starts_on"] is not None


def test_adm07_ac10_a_period_wholly_before_the_category_start_is_unavailable_period_before_recording(analytics_admin, meta):
    w = new_window(2)
    meta.set("request_log_categories_started_at", w.end_dt + timedelta(days=3))
    rl = ok(HEALTH, analytics_admin, w)["rate_limited"]
    assert rl["state"] == "unavailable" and rl["reason"] == "period_before_recording"
    assert rl["count"] is None and rl["total_requests"] is None


def test_adm07_ac10_a_period_wholly_beyond_retention_is_unavailable_beyond_retention(analytics_admin, meta):
    meta.set("request_log_categories_started_at", datetime(2000, 1, 1, tzinfo=UTC))
    today = datetime.now(UTC).date()
    r = ok(HEALTH, analytics_admin, type("W", (), {"params": {"period_start": (today - timedelta(days=100)).isoformat(),
                                                              "period_end": (today - timedelta(days=60)).isoformat()}})())
    assert r["rate_limited"]["state"] == "unavailable" and r["rate_limited"]["reason"] == "beyond_retention"


def test_adm07_ac35_reads_ignore_request_log_rows_older_than_the_retention_floor_even_if_unpurged(analytics_admin, meta):
    meta.set("request_log_categories_started_at", datetime(2000, 1, 1, tzinfo=UTC))
    today = datetime.now(UTC).date()
    params = type("W", (), {"params": {"period_start": (today - timedelta(days=40)).isoformat(),
                                       "period_end": today.isoformat()}})()
    before = ok(HEALTH, analytics_admin, params)["rate_limited"]
    insert_log("generation_notes", datetime.now(UTC) - timedelta(days=30, hours=2))
    after = ok(HEALTH, analytics_admin, params)["rate_limited"]
    assert (after["count"], after["total_requests"]) == (before["count"], before["total_requests"])


def test_adm07_ac40_health_generation_failure_includes_rate_limited_requests(analytics_admin, tracked_users):
    w = new_window()
    seed_rate_limited(w, tracked_users)
    g = ok(HEALTH, analytics_admin, w)["generation_failure"]
    assert g["state"] == "available" and g["includes_rate_limited"] is True
    assert (g["total"], g["failed"], g["in_progress"]) == (6, 4, 0)  # 1 failed attempt + 3 refused of 6 requests
    assert g["rate_percent"] == 66.7 and g["severity"] == "low_sample"


def test_adm07_ac40_generation_only_refused_requests_is_a_real_zero_success_rate_not_not_applicable(analytics_admin):
    from feature_analytics import recording

    w = new_window()
    recording.record_generation_rate_limited(workflow="study_notes", occurred_at=w.at(3))
    g = ok(HEALTH, analytics_admin, w)["generation_failure"]
    assert g["state"] == "available" and (g["total"], g["failed"]) == (1, 1) and g["rate_percent"] == 100.0


def test_adm07_ac40_generation_table_requests_equal_attempts_plus_rate_limited(analytics_admin, tracked_users):
    w = new_window()
    seed_rate_limited(w, tracked_users)
    rows = {x["workflow"]: x for x in ok(GENERATION, analytics_admin, w)["workflows"]}
    notes, mcq = rows["study_notes"], rows["mcq_batch"]
    assert (notes["attempts"], notes["rate_limited"], notes["requests"]) == (2, 1, 3)
    assert (notes["successful"], notes["unsuccessful"]) == (1, 2)
    assert notes["rate_percent"] == 33.3
    assert (mcq["attempts"], mcq["rate_limited"], mcq["requests"]) == (1, 2, 3)
    assert (mcq["successful"], mcq["unsuccessful"]) == (1, 2)
    assert mcq["rate_percent"] == 33.3
    assert notes["rate_limited_state"]["state"] == "available"


def test_adm07_ac40_refused_requests_create_no_attempt_rows_even_after_reports(analytics_admin, tracked_users):
    w = new_window()
    before = sql("SELECT count(*) FROM analytics_generation_attempt")[0][0]
    from feature_analytics import recording

    recording.record_generation_rate_limited(workflow="mcq_batch", occurred_at=w.at(3))
    ok(GENERATION, analytics_admin, w)
    assert sql("SELECT count(*) FROM analytics_generation_attempt")[0][0] == before


def test_adm07_ac40_a_workflow_with_only_refused_requests_has_requests_and_a_zero_rate(analytics_admin):
    from feature_analytics import recording

    w = new_window()
    recording.record_generation_rate_limited(workflow="mcq_batch", occurred_at=w.at(3))
    mcq = {x["workflow"]: x for x in ok(GENERATION, analytics_admin, w)["workflows"]}["mcq_batch"]
    assert mcq["state"] == "available"
    assert (mcq["attempts"], mcq["requests"], mcq["successful"], mcq["unsuccessful"]) == (0, 1, 0, 1)
    assert mcq["rate_percent"] == 0.0


# ================================================================== AC13 / AC33 hourly categories

def test_adm07_ac13_hourly_category_breakdown_is_available_and_counts_each_category(analytics_admin):
    w = new_window()
    for cat, n in (("timeout", 2), ("rate_limited", 3), ("invalid_output", 1), ("upstream", 4), ("unclassified", 5)):
        for i in range(n):
            insert_log("chatbot", w.at(60 + i), "failure", cat, 500)
    insert_log("generation_notes", w.at(61), "success", None, 3000)
    body = ok(HOURLY, analytics_admin, w)
    assert body["category_breakdown"]["state"] == "available"
    b = body["buckets"][1]
    assert b["failed_by_category"] == {"timeout": 2, "rate_limited": 3, "invalid_output": 1, "upstream": 4,
                                       "unclassified": 5}
    assert (b["failed"], b["successful"], b["total"]) == (15, 1, 16) and b["failure_rate_percent"] == 93.8
    assert sum(b["failed_by_category"].values()) == b["failed"]
    assert body["totals"] == {"successful": 1, "failed": 15, "total": 16}


def test_adm07_ac33_hourly_includes_rate_limited_generation_requests(analytics_admin):
    from feature_analytics import recording

    w = new_window()
    recording.record_generation_rate_limited(workflow="study_notes", occurred_at=w.at(125))
    body = ok(HOURLY, analytics_admin, w)
    b = body["buckets"][2]
    assert (b["failed"], b["total"]) == (1, 1) and b["failed_by_category"]["rate_limited"] == 1


def test_adm07_ac13_before_the_category_start_the_breakdown_is_still_available_but_old_failures_are_unclassified(
        analytics_admin, meta, tracked_users):
    """Rows from the migration backfill are `unclassified`; the endpoint keeps counting them in `failed`."""
    w = new_window()
    meta.set("request_log_categories_started_at", w.end_dt + timedelta(days=1))
    insert_log("chatbot", w.at(5), "failure", "unclassified", 100)
    body = ok(HOURLY, analytics_admin, w)
    assert body["buckets"][0]["failed_by_category"]["unclassified"] == 1
    assert body["totals"]["failed"] == 1


def test_adm07_ac35_hourly_ignores_unpurged_rows_beyond_the_retention_floor(analytics_admin, meta):
    meta.set("request_log_started_at", datetime(2000, 1, 1, tzinfo=UTC))
    today = datetime.now(UTC).date()
    params = type("W", (), {"params": {"period_start": (today - timedelta(days=40)).isoformat(),
                                       "period_end": today.isoformat()}})()
    before = ok(HOURLY, analytics_admin, params)["totals"]
    insert_log("chatbot", datetime.now(UTC) - timedelta(days=30, hours=3), "failure", "timeout", 120000)
    assert ok(HOURLY, analytics_admin, params)["totals"] == before


# ================================================================== AC38 in progress, phase 4 (hook-written rows)

def test_adm07_ac38_phase4_in_progress_at_119_s_and_timeout_category_at_120_s(analytics_admin, tracked_users, fixed_now):
    from feature_analytics import recording

    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(10 * 60))
    recording.record_chat_request_received(user_id=str(s), received_at=now - timedelta(seconds=119))
    old = recording.record_chat_request_received(user_id=str(s), received_at=now - timedelta(seconds=120))
    body = ok(HOURLY, analytics_admin, w)
    assert body["in_progress"] == 1 and body["totals"] == {"successful": 0, "failed": 1, "total": 1}
    assert body["buckets"][9]["failed_by_category"]["timeout"] == 1  # real `timeout`, not `unclassified`
    h = ok(HEALTH, analytics_admin, w)
    assert h["chatbot_failure"]["in_progress"] == 1 and h["chatbot_failure"]["failed"] == 1
    assert sql("SELECT outcome FROM analytics_request_log WHERE kind='chatbot' AND source_id=%s", (old,)) == [("pending",)]  # never written


def test_adm07_ac38_phase4_a_late_outcome_replaces_the_timeout_in_the_log(analytics_admin, tracked_users, fixed_now):
    from feature_analytics import recording

    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(10 * 60))
    rid = recording.record_chat_request_received(user_id=str(s), received_at=now - timedelta(seconds=400))
    assert ok(HOURLY, analytics_admin, w)["totals"]["failed"] == 1
    recording.record_chat_request_outcome(rid, success=True, completed_at=now - timedelta(seconds=300))
    body = ok(HOURLY, analytics_admin, w)
    assert body["totals"] == {"successful": 1, "failed": 0, "total": 1}


def test_adm07_ac38_phase4_expired_pending_request_is_failed_at_120000_ms_in_the_response_time(
        analytics_admin, tracked_users, fixed_now):
    from feature_analytics import recording

    w = new_window()
    s = student(tracked_users)
    now = fixed_now(w.at(10 * 60))
    recording.record_chat_request_received(user_id=str(s), received_at=now - timedelta(seconds=500))
    rt = ok(HEALTH, analytics_admin, w)["chatbot_response_time"]
    assert rt["failed"] == {"count": 1, "median_ms": 120000, "p95_ms": 120000}
    assert rt["all"]["count"] == 1 and rt["successful"]["count"] == 0


def test_adm07_ac38_phase4_refused_generation_has_no_duration_and_is_in_no_response_time_set(analytics_admin):
    from feature_analytics import recording

    w = new_window()
    recording.record_generation_rate_limited(workflow="study_notes", occurred_at=w.at(2))
    rt = ok(HEALTH, analytics_admin, w)["generation_response_time"]
    for name in ("all", "successful", "failed"):
        assert rt[name]["count"] == 0 and rt[name]["median_ms"] is None


# ================================================================== AC23 / AC41 daily

def test_adm07_ac22_ac41_logins_count_roles_totals_and_distinct_users_per_day(analytics_admin, event_cleanup):
    from feature_analytics import recording

    w = new_window(2)
    s1, s2, t1 = actor("student"), actor("student"), actor("teacher")
    event_cleanup["users"].extend([s1, s2, t1])
    sql("DELETE FROM analytics_login_event WHERE user_id = ANY(%s)", ([str(s1), str(s2), str(t1)],))
    day0, day1 = w.start_dt + timedelta(hours=3), w.start_dt + timedelta(days=1, hours=3)
    for u, role, at in ((s1, "student", day0), (s1, "student", day0 + timedelta(hours=1)), (s2, "student", day0),
                        (t1, "teacher", day0), (s1, "student", day1), (t1, "teacher", day1), (t1, "teacher", day1)):
        recording.record_login(user_id=str(u), role=role, occurred_at=at)
    recording.record_login(user_id=str(s1), role="admin", occurred_at=day0)  # no-op
    m = ok(DAILY, analytics_admin, w)["logins"]
    assert m["state"] == "available" and m["reason"] is None
    d0, d1 = m["per_day"]
    assert d0 == {"date": w.first.isoformat(), "student_logins": 3, "teacher_logins": 1, "total_logins": 4,
                  "active_students": 2, "active_teachers": 1, "active_users_total": 3}
    assert d1 == {"date": (w.first + timedelta(days=1)).isoformat(), "student_logins": 1, "teacher_logins": 2,
                  "total_logins": 3, "active_students": 1, "active_teachers": 1, "active_users_total": 2}
    assert m["total_logins"] == 7


def test_adm07_ac22_logins_boundaries_belong_to_the_correct_utc_day(analytics_admin, event_cleanup):
    from feature_analytics import recording

    w = new_window(2)
    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    for at in (w.start_dt - timedelta(seconds=1), w.start_dt, w.start_dt + timedelta(days=1) - timedelta(seconds=1),
               w.start_dt + timedelta(days=1), w.end_dt - timedelta(seconds=1), w.end_dt):
        recording.record_login(user_id=str(u), role="student", occurred_at=at)
    m = ok(DAILY, analytics_admin, w)["logins"]
    assert [d["student_logins"] for d in m["per_day"]] == [2, 2] and m["total_logins"] == 4


def test_adm07_ac41_drafts_started_and_published_are_two_independent_series(analytics_admin, event_cleanup):
    from feature_analytics import recording

    w = new_window(3)
    t = actor("teacher")
    ids = ["p4-" + uid() for _ in range(4)]
    event_cleanup["sets"].extend(ids)
    d0, d1, d2 = (w.start_dt + timedelta(days=i, hours=5) for i in range(3))
    recording.record_practice_draft_started(practice_set_id=ids[0], teacher_id=str(t), started_at=d0)
    recording.record_practice_draft_started(practice_set_id=ids[1], teacher_id=str(t), started_at=d0)
    recording.record_practice_draft_started(practice_set_id=ids[2], teacher_id=str(t), started_at=d1)
    recording.record_practice_published(practice_set_id=ids[0], teacher_id=str(t), published_at=d1)
    recording.record_practice_published(practice_set_id=ids[0], teacher_id=str(t), published_at=d2)  # republish
    recording.record_practice_published(practice_set_id=ids[3], teacher_id=str(t), published_at=d2)  # saved published
    recording.record_practice_draft_started(practice_set_id=ids[3], teacher_id=str(t), started_at=d2)
    body = ok(DAILY, analytics_admin, w)
    drafts, pub = body["practice_drafts_started"], body["practice_published"]
    assert drafts["state"] == pub["state"] == "available"
    assert [x["drafts_started"] for x in drafts["per_day"]] == [2, 1, 1] and drafts["total"] == 4
    assert [x["published"] for x in pub["per_day"]] == [0, 1, 1] and pub["total"] == 2
    assert [x["date"] for x in drafts["per_day"]] == dates(w, 3)
    assert [x["date"] for x in pub["per_day"]] == dates(w, 3)


@pytest.mark.parametrize("key,start_key,seed_total", [
    ("logins", "login_events_started_at", "total_logins"),
    ("practice_drafts_started", "practice_draft_started_started_at", "total"),
    ("practice_published", "practice_published_started_at", "total"),
])
def test_adm07_ac23_each_series_has_its_own_start_with_partial_coverage_and_data_starts_on(
        key, start_key, seed_total, analytics_admin, meta):
    w = new_window(3)
    meta.set(start_key, w.start_dt + timedelta(days=1, hours=6))
    m = ok(DAILY, analytics_admin, w)[key]
    assert m["state"] == "available"
    assert m["data_starts_on"] == (w.first + timedelta(days=1)).isoformat()
    assert m["since"] == (w.first + timedelta(days=1)).isoformat()
    assert [d["date"] for d in m["per_day"]] == dates(w, 3)[1:]  # arrays start at the effective start
    assert m[seed_total] == 0
    others = [k for k in ("logins", "practice_drafts_started", "practice_published") if k != key]
    for other in others:
        assert ok(DAILY, analytics_admin, w)[other]["data_starts_on"] is None  # their own start is unaffected


@pytest.mark.parametrize("key,start_key", [("logins", "login_events_started_at"),
                                            ("practice_drafts_started", "practice_draft_started_started_at"),
                                            ("practice_published", "practice_published_started_at")])
def test_adm07_ac23_a_period_wholly_before_the_series_start_is_unavailable_period_before_recording(
        key, start_key, analytics_admin, meta):
    w = new_window(2)
    meta.set(start_key, w.end_dt + timedelta(days=2))
    m = ok(DAILY, analytics_admin, w)[key]
    assert m["state"] == "unavailable" and m["reason"] == "period_before_recording"
    assert m["per_day"] == []


def test_adm07_ac23_login_events_before_the_start_date_are_excluded_from_the_covered_part(analytics_admin, event_cleanup, meta):
    from feature_analytics import recording

    w = new_window(2)
    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    meta.set("login_events_started_at", w.start_dt + timedelta(days=1, hours=2))
    recording.record_login(user_id=str(u), role="student", occurred_at=w.start_dt + timedelta(hours=4))
    recording.record_login(user_id=str(u), role="student", occurred_at=w.start_dt + timedelta(days=1, hours=4))
    m = ok(DAILY, analytics_admin, w)["logins"]
    assert [d["student_logins"] for d in m["per_day"]] == [1] and m["total_logins"] == 1


def test_adm07_ac22_login_retention_is_400_days_reads_include_old_events_within_it(analytics_admin, event_cleanup, meta):
    from feature_analytics import recording

    meta.set("login_events_started_at", datetime(2000, 1, 1, tzinfo=UTC))
    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    day = (datetime.now(UTC) - timedelta(days=300)).replace(hour=12, minute=0, second=0, microsecond=0)
    recording.record_login(user_id=str(u), role="student", occurred_at=day)
    d = day.date().isoformat()
    body = ok(DAILY, analytics_admin, type("W", (), {"params": {"period_start": d, "period_end": d}})())
    assert body["logins"]["state"] == "available" and body["logins"]["total_logins"] >= 1


# ================================================================== AC35 purge and retention

def test_adm07_ac35_purge_deletes_request_log_rows_older_than_30_days_only():
    from feature_analytics import retention

    now = datetime.now(UTC)
    insert_log("chatbot", now - timedelta(days=29, hours=23), "failure", "timeout", 7771)
    insert_log("chatbot", now - timedelta(days=30, hours=1), "failure", "timeout", 7772)
    retention.purge_expired(now)
    durations = [r[0] for r in sql("SELECT duration_ms FROM analytics_request_log WHERE duration_ms IN (7771,7772)")]
    assert 7771 in durations and 7772 not in durations
    sql("DELETE FROM analytics_request_log WHERE duration_ms IN (7771,7772) AND kind='chatbot'")


def test_adm07_ac35_purge_deletes_login_events_older_than_400_days_only(event_cleanup):
    from feature_analytics import recording, retention

    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    now = datetime.now(UTC)
    recording.record_login(user_id=str(u), role="student", occurred_at=now - timedelta(days=399, hours=23))
    recording.record_login(user_id=str(u), role="student", occurred_at=now - timedelta(days=400, hours=1))
    retention.purge_expired(now)
    ((_, kept),) = sql("SELECT role, occurred_at FROM analytics_login_event WHERE user_id=%s", (str(u),))
    assert kept == now - timedelta(days=399, hours=23)


def test_adm07_ac35_purge_keeps_draft_started_and_published_rows_of_any_age(event_cleanup):
    from feature_analytics import recording, retention

    t = actor("teacher")
    sid = "p4-old-" + uid()
    event_cleanup["sets"].append(sid)
    old = datetime.now(UTC) - timedelta(days=900)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t), started_at=old)
    recording.record_practice_published(practice_set_id=sid, teacher_id=str(t), published_at=old)
    retention.purge_expired(datetime.now(UTC))
    assert sql("SELECT count(*) FROM analytics_practice_draft_started WHERE practice_set_id=%s", (sid,)) == [(1,)]
    assert sql("SELECT count(*) FROM analytics_practice_published WHERE practice_set_id=%s", (sid,)) == [(1,)]


def test_adm07_ac35_purge_never_touches_the_source_tables(tracked_users):
    from feature_analytics import retention

    s = student(tracked_users)
    old = datetime.now(UTC) - timedelta(days=60)
    rid = chat_row(s, old, "failure")
    gid = gen_row(teacher(tracked_users), "study_notes", old, "failure")
    retention.purge_expired(datetime.now(UTC))
    assert sql("SELECT count(*) FROM analytics_chat_request WHERE id=%s", (rid,)) == [(1,)]
    assert sql("SELECT count(*) FROM analytics_generation_attempt WHERE id=%s", (gid,)) == [(1,)]


def test_adm07_ac35_purge_works_in_batches_and_removes_every_expired_row():
    from feature_analytics import retention

    now = datetime.now(UTC)
    sql("INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms) "
        "SELECT 'chatbot', NULL, %s::timestamptz - make_interval(secs => g), 'failure', 'timeout', 424242 "
        "FROM generate_series(0, 5499) g", (now - timedelta(days=31),))
    retention.purge_expired(now)  # PURGE_BATCH = 5000: more than one batch
    assert sql("SELECT count(*) FROM analytics_request_log WHERE duration_ms=424242") == [(0,)]


def test_adm07_ac35_the_purge_wrapper_returns_the_number_of_request_log_rows_deleted():
    from feature_analytics import recording

    now = datetime.now(UTC)
    insert_log("chatbot", now - timedelta(days=45), "failure", "timeout", 31313)
    insert_log("chatbot", now - timedelta(days=46), "failure", "timeout", 31313)
    assert recording.purge_expired_request_log(now) >= 2
    assert sql("SELECT count(*) FROM analytics_request_log WHERE duration_ms=31313") == [(0,)]


def test_adm07_ac35_outcome_hooks_run_the_purge_at_most_once_per_interval(monkeypatch, tracked_users):
    from feature_analytics import recording, retention

    calls = []
    real = retention.purge_expired
    monkeypatch.setattr(retention, "purge_expired", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    s = student(tracked_users)
    for _ in range(8):
        rid = recording.record_chat_request_received(user_id=str(s))
        recording.record_chat_request_outcome(rid, success=True)
    assert len(calls) <= 1  # PURGE_INTERVAL_S = 3600 per process (monotonic)
