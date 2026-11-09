"""ADM-01 AC38 concurrency tests, Phase A: two grading starts, duplicate attempt start, two first chat messages.

Contract: workflow/specs/ADM-01/plan.md ("analytics_session" / "analytics_practice_attempt" /
"analytics_grading_run" constraints, `POST /grading-runs`, the recording hook signatures).
The SoC LLM seam is blocked in every test that can reach a grading run (adm01_fixtures.no_ai).

TODO(phase B): add the HTTP-level variants (two simultaneous companion messages, two simultaneous
practice attempt starts through the host routes) once developer check 4 records the route paths.
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

import psycopg
import pytest

from adm01_fixtures import analytics_admin, no_ai, tracked_users  # noqa: F401
from adm01_helpers import (RUN_KEYS, active_run_count, day, error_body, run_count, seed_student_response, send)
from adm02_helpers import actor, race, uid
from auth_helpers import sql

POOL = ThreadPoolExecutor(max_workers=16)


@pytest.fixture
def student(tracked_users):
    user = actor("student")
    tracked_users.append(user)
    return user


@pytest.fixture
def eligible(student):
    """Three ungraded student responses received now, so a run started for today has items and stays active."""
    for n in range(3):
        seed_student_response(student, request_text=f"adm01 concurrency request {n}",
                              response_text=f"adm01 concurrency reply {n}", ref=f"att-{uid()}")
    return 3


def start_together(admin, n, client):
    """Fire n identical start requests at once; release the AI gate only after the losers answered."""
    client.gate = threading.Event()
    barrier = threading.Barrier(n)

    def go():
        barrier.wait(10)
        return send(admin, "start", period_start=day(0), period_end=day(0))

    futures = [POOL.submit(go) for _ in range(n)]
    end = time.monotonic() + 30
    while sum(f.done() for f in futures) < n - 1 and time.monotonic() < end:
        time.sleep(0.02)
    client.gate.set()
    return [f.result(60) for f in futures]


# ---------------------------------------------------------------- AC38: grading starts

def test_adm01_ac38_two_simultaneous_grading_starts_give_one_202_and_one_409(analytics_admin, eligible, no_ai):
    replies = start_together(analytics_admin, 2, no_ai)
    assert sorted(r.status_code for r in replies) == [202, 409], [(r.status_code, r.text) for r in replies]
    winner = next(r for r in replies if r.status_code == 202).json()
    loser = next(r for r in replies if r.status_code == 409)
    error_body(loser, 409, "grading_run_active")
    assert set(winner) == RUN_KEYS and winner["workflow"] == "student_exercise"
    assert eligible <= winner["items_total"] <= 20
    assert run_count() == 1  # the loser created no run row


def test_adm01_ac38_many_simultaneous_grading_starts_still_give_exactly_one_202(analytics_admin, eligible, no_ai):
    replies = start_together(analytics_admin, 6, no_ai)
    statuses = sorted(r.status_code for r in replies)
    assert statuses == [202] + [409] * 5, [(r.status_code, r.text) for r in replies]
    assert run_count() == 1


def test_adm01_ac33_ac38_quick_completed_competing_runs_cannot_exceed_the_hourly_quota(
        analytics_admin, no_ai, monkeypatch):
    import os

    from sqlalchemy import event

    from auth.db import engine_for
    from feature_analytics import jobs

    sql("INSERT INTO analytics_grading_run (workflow, period_start, period_end, status, requested_by, finished_at) "
        "SELECT 'student_exercise', current_date, current_date, 'completed', %s, now() FROM generate_series(1, 9)",
        (str(analytics_admin),))
    first_counted, release_first, second_counted, first_finished = [threading.Event() for _ in range(4)]
    count_lock = threading.Lock()
    count_calls = 0

    def finish_immediately(run_id, *args):
        sql("UPDATE analytics_grading_run SET status='completed', finished_at=now() WHERE id=%s", (run_id,))
        first_finished.set()

    def hold_quota_reads(conn, cursor, statement, parameters, context, executemany):
        nonlocal count_calls
        if "count(" not in statement.lower() or "FROM analytics_grading_run" not in statement:
            return
        with count_lock:
            count_calls += 1
            ordinal = count_calls
        if ordinal == 1:
            first_counted.set()
            assert release_first.wait(5)
        elif ordinal == 2:
            second_counted.set()
            assert first_finished.wait(5)

    monkeypatch.setattr(jobs, "start", finish_immediately)
    engine = engine_for(os.environ["DATABASE_URL"])
    event.listen(engine, "after_cursor_execute", hold_quota_reads)
    futures = []
    try:
        futures.append(POOL.submit(send, analytics_admin, "start", period_start=day(0), period_end=day(0)))
        assert first_counted.wait(5)
        futures.append(POOL.submit(send, analytics_admin, "start", period_start=day(0), period_end=day(0)))
        # Without serialized admission the second caller reads the stale count of nine.
        second_counted.wait(0.2)
        release_first.set()
        replies = [future.result(5) for future in futures]
    finally:
        release_first.set()
        first_finished.set()
        for future in futures:
            future.result(5)
        event.remove(engine, "after_cursor_execute", hold_quota_reads)

    assert sum(reply.status_code == 202 for reply in replies) == 1, [(r.status_code, r.text) for r in replies]
    assert {r.status_code for r in replies} <= {202, 409, 429}
    assert run_count() == 10
    error_body(send(analytics_admin, "start", period_start=day(0), period_end=day(0)), 429, "grading_quota")


def test_adm01_ac38_the_active_run_blocks_the_next_start_until_it_ends(analytics_admin, eligible, no_ai):
    first = send(analytics_admin, "start", period_start=day(0), period_end=day(0))
    assert first.status_code == 202, first.text
    error_body(send(analytics_admin, "start", period_start=day(0), period_end=day(0)), 409, "grading_run_active")
    # a different workflow or period does not bypass the single active-run rule
    error_body(send(analytics_admin, "start", period_start=day(9), period_end=day(8),
                    workflow="teacher_lesson_planning"), 409, "grading_run_active")
    assert run_count() == 1
    sql("UPDATE analytics_grading_run SET status='completed', finished_at=now() WHERE id=%s",
        (first.json()["run_id"],))
    again = send(analytics_admin, "start", period_start=day(0), period_end=day(0))
    assert again.status_code == 202, again.text
    assert again.json()["run_id"] != first.json()["run_id"]


@pytest.mark.parametrize("ended", ["completed", "failed"])
def test_adm01_ac38_a_finished_run_does_not_block_a_new_start(ended, analytics_admin, eligible, no_ai):
    first = send(analytics_admin, "start", period_start=day(0), period_end=day(0))
    assert first.status_code == 202, first.text
    sql("UPDATE analytics_grading_run SET status=%s, finished_at=now() WHERE id=%s",
        (ended, first.json()["run_id"]))
    assert active_run_count() == 0
    assert send(analytics_admin, "start", period_start=day(0), period_end=day(0)).status_code == 202


def test_adm01_ac38_the_database_allows_only_one_queued_or_running_run(analytics_admin, no_ai):
    """The partial unique index is the guard (plan: 'at most one active run')."""
    admin_id = str(analytics_admin)
    insert = ("INSERT INTO analytics_grading_run (workflow, period_start, period_end, status, requested_by) "
              "VALUES ('student_exercise', %s, %s, %s, %s)")
    sql(insert, (day(1), day(0), "queued", admin_id))
    for status in ("queued", "running"):
        with pytest.raises(psycopg.errors.UniqueViolation):
            sql(insert, (day(1), day(0), status, admin_id))
    sql(insert, (day(1), day(0), "completed", admin_id))  # finished runs are unlimited
    sql(insert, (day(1), day(0), "failed", admin_id))
    assert active_run_count() == 1


# ---------------------------------------------------------------- AC38: duplicate practice-attempt start

@pytest.mark.parametrize("n", [2, 6])
def test_adm01_ac38_simultaneous_attempt_starts_for_one_attempt_give_one_row(n, student):
    from feature_analytics import recording

    ref = "att-" + uid()
    results = race(*[lambda: recording.record_practice_attempt_started(
        user_id=str(student), practice_set_id="set-1", attempt_ref=ref)] * n)
    assert all(r is None for r in results)  # hooks return None and never raise
    rows = sql("SELECT user_id, practice_set_id, submitted_at FROM analytics_practice_attempt WHERE attempt_ref=%s", (ref,))
    assert rows == [(str(student), "set-1", None)]


def test_adm01_ac38_a_repeated_attempt_start_later_does_not_change_the_first_record(student):
    from feature_analytics import recording
    from datetime import datetime, timedelta, timezone

    ref = "att-" + uid()
    first = datetime.now(timezone.utc) - timedelta(minutes=5)
    recording.record_practice_attempt_started(user_id=str(student), practice_set_id="set-1", attempt_ref=ref,
                                              started_at=first)
    recording.record_practice_attempt_started(user_id=str(student), practice_set_id="set-1", attempt_ref=ref)
    rows = sql("SELECT started_at FROM analytics_practice_attempt WHERE attempt_ref=%s", (ref,))
    assert len(rows) == 1 and abs((rows[0][0] - first).total_seconds()) < 1  # insert-if-absent keeps the first


def test_adm01_ac38_simultaneous_starts_of_different_attempts_each_get_a_row(student):
    from feature_analytics import recording

    refs = ["att-" + uid() for _ in range(4)]
    race(*[(lambda r=r: recording.record_practice_attempt_started(user_id=str(student), practice_set_id="set-1",
                                                                   attempt_ref=r)) for r in refs])
    assert sql("SELECT count(*) FROM analytics_practice_attempt WHERE user_id=%s", (str(student),))[0][0] == 4


# ---------------------------------------------------------------- AC38: first chat messages and sessions

def attempt(student):
    """Record a started practice attempt for the student and return its reference."""
    from feature_analytics import recording

    ref = "att-" + uid()
    recording.record_practice_attempt_started(user_id=str(student), practice_set_id="set-1", attempt_ref=ref)
    return ref


def chat(student, ref, **kw):
    from feature_analytics import recording

    return recording.record_chat_request_received(user_id=str(student),
                                                  activity_type="practice_attempt", activity_ref=ref, **kw)


def test_adm01_ac27_ac38_submission_cannot_leave_a_concurrent_first_chat_session_open(student):
    """Pause the first session insert after its attempt read; submission must serialize with it."""
    import os

    from sqlalchemy import event

    from auth.db import engine_for
    from feature_analytics import recording

    ref = attempt(student)
    entered, release = threading.Event(), threading.Event()
    engine = engine_for(os.environ["DATABASE_URL"])

    def hold_first_session(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("INSERT INTO analytics_session"):
            entered.set()
            assert release.wait(5), "the test did not release the session insert"

    event.listen(engine, "before_cursor_execute", hold_first_session)
    first_chat = POOL.submit(chat, student, ref)
    submitted = None
    try:
        assert entered.wait(5), "the chat did not reach its first session insert"
        submitted = POOL.submit(recording.record_practice_attempt_submitted, attempt_ref=ref)
        with pytest.raises(TimeoutError):
            submitted.result(timeout=0.2)
    finally:
        release.set()
        first_chat.result(timeout=5)
        if submitted is not None:
            submitted.result(timeout=5)
        event.remove(engine, "before_cursor_execute", hold_first_session)

    assert sql("SELECT ended_at IS NOT NULL, end_reason FROM analytics_session WHERE activity_ref=%s", (ref,)) == [
        (True, "activity_ended")
    ]


def test_adm01_ac27_a_delayed_pre_submission_message_never_reopens_a_completed_activity(student):
    from datetime import datetime, timedelta, timezone

    from feature_analytics import recording

    submitted_at = datetime.now(timezone.utc)
    ref = attempt(student)
    recording.record_practice_attempt_submitted(attempt_ref=ref, submitted_at=submitted_at)
    later_activity = attempt(student)
    assert isinstance(chat(student, later_activity, received_at=submitted_at + timedelta(seconds=1)), int)
    assert isinstance(chat(student, ref, received_at=submitted_at - timedelta(seconds=1)), int)
    assert sql("SELECT activity_ref FROM analytics_session WHERE user_id=%s AND ended_at IS NULL", (str(student),)) == [
        (later_activity,)
    ]
    assert sql("SELECT ended_at, end_reason FROM analytics_session WHERE activity_ref=%s", (ref,)) == [
        (submitted_at, "activity_ended")
    ]


@pytest.mark.parametrize("n", [2, 8])
def test_adm01_ac38_simultaneous_first_chat_messages_create_one_open_session(n, student):
    ref = attempt(student)
    ids = race(*[lambda: chat(student, ref)] * n)
    # Every message is recorded (the advisory lock serialises the session assignment, nobody loses a row) ...
    assert all(isinstance(i, int) for i in ids) and len(set(ids)) == n, ids
    # ... and they all share the single open session.
    open_sessions = sql("SELECT id, activity_ref FROM analytics_session WHERE user_id=%s AND ended_at IS NULL",
                        (str(student),))
    assert len(open_sessions) == 1 and open_sessions[0][1] == ref
    assert sql("SELECT count(*) FROM analytics_session WHERE user_id=%s", (str(student),))[0][0] == 1
    session_ids = {r[0] for r in sql("SELECT session_id FROM analytics_chat_request WHERE user_id=%s", (str(student),))}
    assert session_ids == {open_sessions[0][0]}
    assert sql("SELECT count(*) FROM analytics_chat_request WHERE user_id=%s", (str(student),))[0][0] == n


def test_adm01_ac38_first_messages_of_two_users_get_separate_sessions(student, tracked_users):
    other = actor("student")
    tracked_users.append(other)
    ref_a, ref_b = attempt(student), attempt(other)
    ids = race(lambda: chat(student, ref_a), lambda: chat(other, ref_b), lambda: chat(student, ref_a),
               lambda: chat(other, ref_b))
    assert all(isinstance(i, int) for i in ids)
    for user, ref in ((student, ref_a), (other, ref_b)):
        rows = sql("SELECT activity_ref FROM analytics_session WHERE user_id=%s AND ended_at IS NULL", (str(user),))
        assert rows == [(ref,)]


def test_adm01_ac38_simultaneous_messages_for_two_different_attempts_leave_one_open_session(student):
    ref_a, ref_b = attempt(student), attempt(student)
    ids = race(lambda: chat(student, ref_a), lambda: chat(student, ref_b))
    assert all(isinstance(i, int) for i in ids)
    open_sessions = sql("SELECT activity_ref FROM analytics_session WHERE user_id=%s AND ended_at IS NULL",
                        (str(student),))
    assert len(open_sessions) == 1 and open_sessions[0][0] in (ref_a, ref_b)
    closed = sql("SELECT end_reason FROM analytics_session WHERE user_id=%s AND ended_at IS NOT NULL", (str(student),))
    assert closed == [("new_activity",)]  # whichever arrived second closed the first (different attempt)


def test_adm01_ac38_a_message_after_the_idle_limit_opens_a_new_session_once(student):
    from datetime import datetime, timedelta, timezone

    ref = attempt(student)
    old = datetime.now(timezone.utc) - timedelta(minutes=45)
    assert isinstance(chat(student, ref, received_at=old), int)
    ids = race(lambda: chat(student, ref), lambda: chat(student, ref))
    assert all(isinstance(i, int) for i in ids)
    assert len(sql("SELECT 1 FROM analytics_session WHERE user_id=%s AND ended_at IS NULL", (str(student),))) == 1
    assert sql("SELECT end_reason FROM analytics_session WHERE user_id=%s AND ended_at IS NOT NULL",
               (str(student),)) == [("inactivity",)]
