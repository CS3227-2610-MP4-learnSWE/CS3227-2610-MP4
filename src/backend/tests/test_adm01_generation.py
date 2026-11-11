"""ADM-01 AC14-AC19: generation reliability report and the TEA-02 attempt rule (task 18).

Contract: workflow/specs/ADM-01/plan.md "GET /generation", hook signatures, decision 8 (a rate-limited or
busy AI call is not an attempt; every other exit after validation is exactly one attempt with one outcome).
Report tests seed `analytics_generation_attempt` in their own far-future window. Route tests drive the real
TEA-02 routes with the fake client (no quota) and read the attempt table.
"""
from datetime import timedelta

import pytest

import llm_client
from adm01_fixtures import privacy_scanner, analytics_admin, no_ai, recording_start, tracked_users  # noqa: F401
from adm01_grading_helpers import gen_row, get_json, new_window
from adm01_helpers import GENERATION, url
from adm01_tea02 import WORKFLOWS, generate, tea, upload  # noqa: F401
from adm02_helpers import actor, uid
from auth_helpers import call, sql

FORBIDDEN_KEYS = ("chatbot", "student", "teacher", "tokens", "category", "categories", "retry", "retries", "rate_limit",
                  "ai_calls", "service_calls", "failure_category")


def teacher(tracked):
    user = actor("teacher")
    tracked.append(user)
    return user


def generation(admin, win):
    body = get_json(admin, "generation", win)
    return body, {w["workflow"]: w for w in body["workflows"]}


# ---------------------------------------------------------------- AC14, AC18: both rows, always

def test_adm01_ac14_ac18_both_workflows_are_always_listed_in_order_even_with_no_data(analytics_admin):
    w = new_window()
    body, by = generation(analytics_admin, w)
    assert [x["workflow"] for x in body["workflows"]] == ["study_notes", "mcq_batch"]
    assert [x["label"] for x in body["workflows"]] == ["Study notes", "MCQ batches"]
    assert (body["period_start"], body["period_end"]) == (w.start, w.end)  # the period behind every rate
    # ADM-07 P2-5: the kept endpoint gains `data_starts_on` (partial coverage); no other top-level change.
    assert set(body) == {"period_start", "period_end", "recording_started_on", "data_starts_on", "workflows"}
    assert body["data_starts_on"] is None
    for row in body["workflows"]:
        assert row["state"] == "not_applicable" and row["reason"] == "no_generation_attempts"
        assert row["attempts"] == 0 and row["successful"] == 0 and row["unsuccessful"] == 0  # counts are 0, not null
        assert row["rate_percent"] is None  # never 0 % and never 100 %


def test_adm01_ac14_each_row_has_exactly_the_documented_fields(analytics_admin, tracked_users):
    w = new_window()
    gen_row(teacher(tracked_users), "study_notes", w.at(1))
    body, by = generation(analytics_admin, w)
    for row in body["workflows"]:
        # ADM-07 P2-5: phase 2 adds requests, rate_limited, rate_limited_state and data_starts_on (plan.md);
        # every ADM-01 field is still required with its old meaning.
        assert set(row) == {"workflow", "label", "state", "reason", "attempts", "successful", "unsuccessful",
                            "rate_percent", "requests", "rate_limited", "rate_limited_state", "data_starts_on"}


# ---------------------------------------------------------------- AC16, AC17: counting and rate

def test_adm01_ac16_ac17_successful_failed_and_outcome_less_attempts(analytics_admin, tracked_users):
    w = new_window()
    t = teacher(tracked_users)
    for i in range(6):
        gen_row(t, "study_notes", w.at(i + 1), "success")
    gen_row(t, "study_notes", w.at(10), "failure")
    gen_row(t, "study_notes", w.at(11), "pending")  # an attempt that never got an outcome is unsuccessful
    gen_row(t, "study_notes", w.at(12), "failure")
    gen_row(t, "mcq_batch", w.at(20), "success")
    gen_row(t, "mcq_batch", w.at(21), "failure")
    gen_row(t, "mcq_batch", w.at(22), "failure")
    body, by = generation(analytics_admin, w)
    notes, mcq = by["study_notes"], by["mcq_batch"]
    assert notes["state"] == "available" and notes["reason"] is None
    assert (notes["attempts"], notes["successful"], notes["unsuccessful"], notes["rate_percent"]) == (9, 6, 3, 66.7)
    assert (mcq["attempts"], mcq["successful"], mcq["unsuccessful"], mcq["rate_percent"]) == (3, 1, 2, 33.3)


@pytest.mark.parametrize("attempts,successes,expected", [
    (3, 1, 33.3), (3, 2, 66.7), (6, 5, 83.3), (8, 7, 87.5), (1, 0, 0.0), (5, 5, 100.0), (7, 1, 14.3),
])
def test_adm01_ac17_the_rate_is_a_percentage_rounded_to_one_decimal(attempts, successes, expected, analytics_admin, tracked_users):
    w = new_window()
    t = teacher(tracked_users)
    for i in range(attempts):
        gen_row(t, "mcq_batch", w.at(i + 1), "success" if i < successes else "failure")
    _, by = generation(analytics_admin, w)
    row = by["mcq_batch"]
    assert row["state"] == "available" and row["attempts"] == attempts and row["successful"] == successes
    assert row["rate_percent"] == expected
    assert by["study_notes"]["state"] == "not_applicable"  # the other workflow is unaffected


def test_adm01_ac17_a_workflow_with_only_failures_has_a_real_zero_rate(analytics_admin, tracked_users):
    w = new_window()
    t = teacher(tracked_users)
    gen_row(t, "study_notes", w.at(1), "failure")
    gen_row(t, "study_notes", w.at(2), "pending")
    row = generation(analytics_admin, w)[1]["study_notes"]
    assert row["state"] == "available" and (row["attempts"], row["successful"], row["unsuccessful"]) == (2, 0, 2)
    assert row["rate_percent"] == 0.0


def test_adm01_ac17_attempts_are_counted_by_accepted_at_inside_the_period(analytics_admin, tracked_users):
    w = new_window()
    t = teacher(tracked_users)
    gen_row(t, "study_notes", w.start_dt - timedelta(seconds=1), "success")  # before From: excluded
    gen_row(t, "study_notes", w.start_dt, "success")  # From 00:00:00 included
    gen_row(t, "study_notes", w.end_dt - timedelta(seconds=1), "failure", duration_ms=10_000)  # included, ends after
    gen_row(t, "study_notes", w.end_dt, "success")  # To + 1 day 00:00:00: excluded
    row = generation(analytics_admin, w)[1]["study_notes"]
    assert (row["attempts"], row["successful"], row["unsuccessful"], row["rate_percent"]) == (2, 1, 1, 50.0)


def test_adm01_ac18_one_workflow_without_attempts_is_not_applicable_while_the_other_has_a_rate(analytics_admin, tracked_users):
    w = new_window()
    gen_row(teacher(tracked_users), "study_notes", w.at(1), "success")
    _, by = generation(analytics_admin, w)
    assert by["study_notes"]["rate_percent"] == 100.0
    mcq = by["mcq_batch"]
    assert mcq["state"] == "not_applicable" and mcq["reason"] == "no_generation_attempts"
    assert mcq["rate_percent"] is None and mcq["attempts"] == 0


def test_adm01_ac18_attempts_of_every_teacher_are_combined(analytics_admin, tracked_users):
    w = new_window()
    a, b = teacher(tracked_users), teacher(tracked_users)
    gen_row(a, "mcq_batch", w.at(1), "success")
    gen_row(b, "mcq_batch", w.at(2), "failure")
    row = generation(analytics_admin, w)[1]["mcq_batch"]
    assert (row["attempts"], row["successful"]) == (2, 1)


# ---------------------------------------------------------------- AC19: no chatbot, no AI-service metrics

def test_adm01_ac19_the_generation_report_has_no_chatbot_outcomes_or_ai_service_counts(analytics_admin, tracked_users):
    from adm01_grading_helpers import chat_row

    w = new_window()
    t, s = teacher(tracked_users), actor("student")
    tracked_users.append(s)
    gen_row(t, "study_notes", w.at(1), "success")
    for i in range(5):  # chatbot traffic in the same period must not leak into the rates
        chat_row(s, w.at(i + 2), "success")
    r = call("GET", url(GENERATION, **w.params), analytics_admin)
    assert r.status_code == 200
    text = r.text.lower()
    for key in FORBIDDEN_KEYS:
        assert f'"{key}"' not in text, key
    notes = {x["workflow"]: x for x in r.json()["workflows"]}["study_notes"]
    assert notes["attempts"] == 1  # the five chat requests are not generation attempts


# ---------------------------------------------------------------- AC12 for this panel

def test_adm01_ac12_a_period_before_recording_marks_every_workflow_unavailable(analytics_admin):
    r = call("GET", url(GENERATION, period_start="2000-01-01", period_end="2000-01-31"), analytics_admin)
    assert r.status_code == 200, r.text
    rows = r.json()["workflows"]
    assert [x["workflow"] for x in rows] == ["study_notes", "mcq_batch"]
    for row in rows:
        assert row["state"] == "unavailable" and row["reason"] == "period_before_recording"
        assert row["attempts"] is None and row["successful"] is None and row["unsuccessful"] is None
        assert row["rate_percent"] is None


def test_adm01_ac12_a_failed_read_is_unavailable_read_failed_never_zero(analytics_admin, monkeypatch):
    from feature_analytics import queries

    def boom(*args, **kwargs):
        raise RuntimeError("simulated read failure")

    monkeypatch.setattr(queries, "generation_rates", boom)
    r = call("GET", url(GENERATION, **new_window().params), analytics_admin)
    assert r.status_code == 200, r.text
    rows = r.json()["workflows"]
    assert [x["workflow"] for x in rows] == ["study_notes", "mcq_batch"]
    for row in rows:
        assert row["state"] == "unavailable" and row["reason"] == "read_failed"
        assert row["attempts"] is None and row["rate_percent"] is None
    assert "simulated read failure" not in r.text


# ---------------------------------------------------------------- AC15, AC16: the recording hooks (direct calls)

def test_adm01_ac15_ac16_hooks_record_one_attempt_and_one_outcome_each(analytics_admin, tracked_users):
    from feature_analytics import recording

    w = new_window()
    t = teacher(tracked_users)
    ok = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(1))
    bad = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(2))
    silent = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(3))
    assert all(isinstance(i, int) for i in (ok, bad, silent)) and len({ok, bad, silent}) == 3
    recording.record_generation_outcome(ok, success=True, completed_at=w.at(1, 2))
    recording.record_generation_outcome(bad, success=False, completed_at=w.at(2, 2))
    row = generation(analytics_admin, w)[1]["study_notes"]
    assert (row["attempts"], row["successful"], row["unsuccessful"], row["rate_percent"]) == (3, 1, 2, 33.3)
    states = dict(sql("SELECT id, outcome FROM analytics_generation_attempt WHERE user_id=%s", (str(t),)))
    assert states == {ok: "success", bad: "failure", silent: "pending"}


def test_adm01_ac16_only_the_first_outcome_of_an_attempt_counts(tracked_users):
    from feature_analytics import recording

    w = new_window()
    t = teacher(tracked_users)
    first = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t), accepted_at=w.at(1))
    recording.record_generation_outcome(first, success=True, completed_at=w.at(1, 3))
    recording.record_generation_outcome(first, success=False, completed_at=w.at(1, 9))
    second = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t), accepted_at=w.at(2))
    recording.record_generation_outcome(second, success=False, completed_at=w.at(2, 3))
    recording.record_generation_outcome(second, success=True, completed_at=w.at(2, 9))
    rows = dict(sql("SELECT id, outcome FROM analytics_generation_attempt WHERE user_id=%s", (str(t),)))
    assert rows == {first: "success", second: "failure"}


def test_adm01_ac16_duration_is_the_elapsed_time_and_never_negative(tracked_users):
    from feature_analytics import recording

    w = new_window()
    t = teacher(tracked_users)
    a = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(1))
    recording.record_generation_outcome(a, success=True, completed_at=w.at(1) + timedelta(milliseconds=2500))
    b = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(5))
    recording.record_generation_outcome(b, success=False, completed_at=w.at(4))  # clock skew: completed before accepted
    d = dict(sql("SELECT id, duration_ms FROM analytics_generation_attempt WHERE user_id=%s", (str(t),)))
    assert d[a] == 2500 and d[b] == 0


@pytest.mark.parametrize("bad", ["", "notes", "STUDY_NOTES", "study_notes ", "mcq", None, "student_exercise"])
def test_adm01_ac15_an_invalid_workflow_records_nothing_and_does_not_raise(bad, tracked_users):
    from feature_analytics import recording

    t = teacher(tracked_users)
    before = sql("SELECT count(*) FROM analytics_generation_attempt")[0][0]
    assert recording.record_generation_accepted(workflow=bad, user_id=str(t)) is None
    assert sql("SELECT count(*) FROM analytics_generation_attempt")[0][0] == before


def test_adm01_ac16_an_outcome_for_no_attempt_is_a_no_op(tracked_users):
    from feature_analytics import recording

    before = sql("SELECT count(*) FROM analytics_generation_attempt")[0][0]
    assert recording.record_generation_outcome(None, success=True) is None
    assert recording.record_generation_outcome(2 ** 40, success=True) is None
    assert sql("SELECT count(*) FROM analytics_generation_attempt")[0][0] == before


def test_adm01_ac16_an_oversize_success_keeps_metrics_but_excludes_grading_text(tracked_users):
    from feature_analytics import recording
    from feature_analytics.grading_text import GradingContent

    w = new_window()
    t = teacher(tracked_users)
    token = "Tk" + "x9" * 25  # a 52-character token-like string
    content = GradingContent(request_text="Contact owner@example.com " + token + " " + "word " * 1000,
                             response_text="Reply " + "text " * 3000, context_text="Source " + "line " * 2000)
    aid = recording.record_generation_accepted(workflow="study_notes", user_id=str(t), accepted_at=w.at(1))
    recording.record_generation_outcome(aid, success=True, grading=content, completed_at=w.at(1, 2), source="teacher_notes")
    items = sql("SELECT workflow, source_type, generation_workflow, status, request_text, response_text, context_text, "
                "duration_ms FROM analytics_grading_item WHERE source_type='generation_attempt' AND source_id=%s", (aid,))
    assert len(items) == 1
    workflow, source_type, gen_wf, status, req, resp, ctx, duration = items[0]
    assert (workflow, source_type, gen_wf, status) == ("teacher_lesson_planning", "generation_attempt",
                                                       "study_notes", "privacy_blocked")
    assert req is None and resp is None and ctx is None
    assert duration == 2000


def test_adm01_ac16_a_failed_outcome_or_missing_content_stores_no_grading_item(tracked_users):
    from feature_analytics import recording
    from feature_analytics.grading_text import GradingContent

    t = teacher(tracked_users)
    content = GradingContent(request_text="r", response_text="p", context_text=None)
    failed = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t))
    recording.record_generation_outcome(failed, success=False, grading=content)
    plain = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t))
    recording.record_generation_outcome(plain, success=True)
    count = sql("SELECT count(*) FROM analytics_grading_item WHERE source_type='generation_attempt' "
                "AND source_id = ANY(%s)", ([failed, plain],))[0][0]
    assert count == 0


# ---------------------------------------------------------------- AC15, plan decision 8: rate-limited or busy is NOT an attempt

LIMITERS = [("LlmRateLimited", lambda: llm_client.LlmRateLimited("minute", 17)),
            ("LlmBusy", lambda: llm_client.LlmBusy(17))]


@pytest.mark.parametrize("workflow", WORKFLOWS)
@pytest.mark.parametrize("name,make", LIMITERS, ids=[n for n, _ in LIMITERS])
def test_adm01_ac15_decision8_refused_calls_do_not_move_the_report(workflow, name, make, tea, analytics_admin):
    from datetime import datetime, timezone

    app, fake, since = tea
    today = datetime.now(timezone.utc).date().isoformat()

    def attempts():
        r = call("GET", url(GENERATION, period_start=today, period_end=today), analytics_admin)
        assert r.status_code == 200, r.text
        return {x["workflow"]: x["attempts"] for x in r.json()["workflows"]}

    source = upload(app)
    before = attempts()
    fake.error = make()
    for _ in range(3):
        assert generate(app, workflow, source).status_code == 429
    assert attempts() == before
