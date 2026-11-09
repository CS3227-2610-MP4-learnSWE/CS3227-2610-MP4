"""ADM-01 recording-hook contract tests (task 20; AC2, AC4, AC15, AC16, AC39).

Contract: workflow/specs/ADM-01/plan.md "Recording hooks", "Where the hooks are called" (incl. the TEA-02
pseudocode) and decisions 4, 5 and 8.

  * hooks never raise and never change the host route's response, even when their own database session fails
    (simulated by replacing `feature_analytics.recording.open_session`, as the plan's test plan says);
  * the companion route records one outcome on every exit after validation (a rate-limited chat request is
    recorded as unsuccessful); rejected requests record nothing;
  * the practice-attempt hooks fire only after the host commit; the user id is the signed-in session's id;
  * TEA-02: every exit after validation is exactly one attempt with one outcome, except a call refused by the AI
    service's rate or busy limiter, which records nothing; no outcome-less attempts from route paths;
  * MCQ grading text never carries the answer key or the explanation.
The SoC LLM is always a fake injected through `app.dependency_overrides[get_llm_client]`.
"""
import logging
import time

import pytest

import llm_client
from adm01_fixtures import analytics_admin, tracked_users  # noqa: F401
from adm01_tea02 import (ROUTE, TEACHER, WORKFLOWS, cleanup, generate, max_attempt_id, mcq_with, new_attempts,  # noqa: F401
                         new_items, prepare, tea, upload)
from adm02_helpers import uid
from auth_helpers import call, new_student, sql
from companion_helpers import (BENIGN, CHOICE_TEXTS, CORRECT, EXPLANATIONS, SET_ID, ask, save, start, submit)
from test_tea02_notes import replace_bytes

pytestmark = pytest.mark.usefixtures("fake_provider")

SECRET = "PRIVATE-HOOK-MARKER-"


# ------------------------------------------------------------------ helpers

def boom(*args, **kwargs):
    raise RuntimeError("analytics database is down")


@pytest.fixture
def broken_analytics(monkeypatch):
    """The hooks' own session can no longer be opened (AC2)."""
    from feature_analytics import recording

    monkeypatch.setattr(recording, "open_session", boom)
    return recording


def pupil(tracked):
    s = new_student("adm01hook")
    tracked.append(s)
    return s


def chat_rows(user):
    return sql("SELECT id, outcome, activity_type, activity_ref, session_id, completed_at, duration_ms "
               "FROM analytics_chat_request WHERE user_id=%s ORDER BY id", (str(user),))


def chat_items(user):
    return sql("SELECT i.id, i.workflow, i.source_type, i.request_text, i.response_text, i.context_text, i.status "
               "FROM analytics_grading_item i JOIN analytics_chat_request c "
               "ON i.source_type='chat_request' AND i.source_id=c.id WHERE c.user_id=%s ORDER BY i.id", (str(user),))


def attempt_rows(user):
    return sql("SELECT attempt_ref, user_id, practice_set_id, started_at, submitted_at FROM analytics_practice_attempt "
               "WHERE user_id=%s ORDER BY started_at", (str(user),))


def practice_msg(s, message="Give me a hint please", **kw):
    return ask(s, message, page="practice", set_id=SET_ID, **kw)


# ================================================================== AC2: hooks never raise (direct calls)

def all_hook_calls(user_id, content):
    """Each documented hook once, with valid arguments."""
    from feature_analytics import recording

    return {
        "record_chat_request_received": lambda: recording.record_chat_request_received(
            user_id=user_id, activity_type="practice_attempt", activity_ref="att-x"),
        "record_chat_request_outcome": lambda: recording.record_chat_request_outcome(7, success=True, grading=content),
        "record_practice_attempt_started": lambda: recording.record_practice_attempt_started(
            user_id=user_id, practice_set_id="set-1", attempt_ref="att-x"),
        "record_practice_attempt_submitted": lambda: recording.record_practice_attempt_submitted(attempt_ref="att-x"),
        "record_generation_accepted": lambda: recording.record_generation_accepted(workflow="study_notes", user_id=user_id),
        "record_generation_outcome": lambda: recording.record_generation_outcome(7, success=True, grading=content),
    }


@pytest.mark.parametrize("name", ["record_chat_request_received", "record_chat_request_outcome",
                                  "record_practice_attempt_started", "record_practice_attempt_submitted",
                                  "record_generation_accepted", "record_generation_outcome"])
def test_adm01_ac2_a_hook_with_an_unavailable_analytics_database_returns_none_and_logs_no_content(
        name, broken_analytics, caplog, tracked_users):
    from feature_analytics.grading_text import GradingContent

    caplog.set_level(logging.DEBUG)
    content = GradingContent(request_text=SECRET + "request", response_text=SECRET + "response",
                             context_text=SECRET + "context")
    result = all_hook_calls("u-someone", content)[name]()
    assert result is None  # no id, no exception
    assert SECRET not in caplog.text and "u-someone" not in caplog.text  # a failed write is logged without content
    assert name in caplog.text  # ... but it is logged, with the hook name


def test_adm01_ac2_a_failed_outcome_never_turns_into_a_partial_row(tracked_users, monkeypatch):
    """The received row exists; its outcome write fails; the row stays pending and nothing is raised."""
    from feature_analytics import recording

    s = pupil(tracked_users)
    rid = recording.record_chat_request_received(user_id=str(s))
    monkeypatch.setattr(recording, "open_session", boom)
    assert recording.record_chat_request_outcome(rid, success=True) is None
    monkeypatch.undo()
    assert sql("SELECT outcome FROM analytics_chat_request WHERE id=%s", (rid,)) == [("pending",)]


@pytest.mark.parametrize("kwargs", [
    {"user_id": "u-no-such-user-" + "z" * 20},  # foreign key violation
    {"user_id": "x" * 200},  # longer than the column
])
def test_adm01_ac2_bad_arguments_or_constraint_violations_are_swallowed(kwargs):
    from feature_analytics import recording

    before = sql("SELECT count(*) FROM analytics_chat_request")[0][0]
    assert recording.record_chat_request_received(**kwargs) is None
    assert recording.record_generation_accepted(workflow="mcq_batch", **kwargs) is None
    assert recording.record_practice_attempt_started(practice_set_id="s", attempt_ref="att-" + uid(), **kwargs) is None
    assert sql("SELECT count(*) FROM analytics_chat_request")[0][0] == before


def test_adm01_ac2_an_overlong_attempt_reference_is_swallowed_without_a_row(tracked_users):
    from feature_analytics import recording

    s = pupil(tracked_users)
    assert recording.record_practice_attempt_started(user_id=str(s), practice_set_id="s", attempt_ref="a" * 101) is None
    assert attempt_rows(s) == []


def test_adm01_ac2_a_failed_write_inside_one_hook_does_not_break_the_next_call(tracked_users, monkeypatch):
    from feature_analytics import recording

    s = pupil(tracked_users)
    with monkeypatch.context() as m:
        m.setattr(recording, "open_session", boom)
        assert recording.record_chat_request_received(user_id=str(s)) is None
    assert isinstance(recording.record_chat_request_received(user_id=str(s)), int)  # recovers once the database is back


def test_adm01_ac4_ac16_the_chat_outcome_is_idempotent_and_the_first_one_wins(tracked_users):
    from feature_analytics import recording

    s = pupil(tracked_users)
    first = recording.record_chat_request_received(user_id=str(s))
    recording.record_chat_request_outcome(first, success=False)
    recording.record_chat_request_outcome(first, success=True)
    second = recording.record_chat_request_received(user_id=str(s))
    recording.record_chat_request_outcome(second, success=True)
    recording.record_chat_request_outcome(second, success=False)
    assert dict(sql("SELECT id, outcome FROM analytics_chat_request WHERE user_id=%s", (str(s),))) == {
        first: "failure", second: "success"}


def test_adm01_ac4_a_successful_practice_reply_stores_one_redacted_grading_item_and_other_requests_none(tracked_users):
    from feature_analytics import recording
    from feature_analytics.grading_text import GradingContent

    s = pupil(tracked_users)
    content = GradingContent(request_text="hint? mail me x@y.example.com", response_text="Think about loops.",
                             context_text="Stem only")
    practice = recording.record_chat_request_received(user_id=str(s), activity_type="practice_attempt", activity_ref="att-" + uid())
    lesson = recording.record_chat_request_received(user_id=str(s), activity_type="lesson", activity_ref="lesson-1")
    plain = recording.record_chat_request_received(user_id=str(s))
    failed = recording.record_chat_request_received(user_id=str(s), activity_type="practice_attempt", activity_ref="att-" + uid())
    for rid, ok in ((practice, True), (lesson, True), (plain, True), (failed, False)):
        recording.record_chat_request_outcome(rid, success=ok, grading=content)
    items = chat_items(s)
    assert len(items) == 1
    _, workflow, source_type, req, resp, ctx, status = items[0]
    assert (workflow, source_type, status) == ("student_exercise", "chat_request", "pending")
    assert "x@y.example.com" not in req and resp == "Think about loops." and ctx == "Stem only"
    assert sql("SELECT source_id FROM analytics_grading_item WHERE id=%s", (items[0][0],)) == [(practice,)]


# ================================================================== companion route: one outcome on every exit

def test_adm01_ac4_a_valid_practice_reply_records_received_before_the_ai_call_and_one_success(fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    during = []
    fake.reply = lambda messages: (during.append(chat_rows(s)), BENIGN)[1]
    r = practice_msg(s, attempt_id=aid)
    assert r.status_code == 200 and r.json()["reply"] == BENIGN
    assert len(during) == 1 and [x[1] for x in during[0]] == ["pending"]  # recorded before the model was called
    rows = chat_rows(s)
    assert len(rows) == 1
    _, outcome, activity_type, activity_ref, _, completed, duration = rows[0]
    assert (outcome, activity_type, activity_ref) == ("success", "practice_attempt", str(aid))
    assert completed is not None and duration is not None and duration >= 0
    (item,) = chat_items(s)
    assert item[1] == "student_exercise" and item[6] == "pending"
    assert "Give me a hint please" in item[3] and BENIGN in item[4]


@pytest.mark.parametrize("mode", ["hint", "explain"])
def test_adm01_ac23_the_stored_grading_context_never_carries_answer_keys_or_explanations(mode, fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    if mode == "explain":
        save(aid, s, CORRECT)
        submit(aid, s)
    assert practice_msg(s, "Why?", attempt_id=aid).status_code == 200
    (item,) = chat_items(s)
    stored = " ".join(t or "" for t in item[3:6])
    for explanation in EXPLANATIONS:
        assert explanation not in stored, explanation
    if mode == "hint":
        for choice in CHOICE_TEXTS:
            assert choice not in stored, choice


@pytest.mark.parametrize("exception,status", [
    (llm_client.LlmTimeout("x"), 503), (llm_client.LlmUpstreamError("x"), 503), (llm_client.LlmBadResponse("x"), 502),
    (llm_client.LlmNotConfigured("x"), 503), (llm_client.LlmRateLimited("student_minute", 12), 429),
    (llm_client.LlmBusy(7), 429),
], ids=["timeout", "upstream", "bad_response", "not_configured", "rate_limited", "busy"])
def test_adm01_ac4_every_failed_exit_records_exactly_one_unsuccessful_request_and_no_grading_item(
        exception, status, fake, tracked_users):
    """Unlike TEA-02, a rate-limited or busy chat request IS recorded (as unsuccessful): open question 4."""
    s = pupil(tracked_users)
    aid = start(s)
    fake.raises = exception
    assert practice_msg(s, attempt_id=aid).status_code == status
    rows = chat_rows(s)
    assert len(rows) == 1 and rows[0][1] == "failure" and rows[0][2] == "practice_attempt"
    assert chat_items(s) == []


def test_adm01_ac4_each_request_is_one_row_and_a_later_success_after_a_failure_is_its_own_row(fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    fake.raises = llm_client.LlmTimeout("x")
    practice_msg(s, attempt_id=aid)
    fake.raises = None
    practice_msg(s, attempt_id=aid)
    practice_msg(s, attempt_id=aid)
    assert [r[1] for r in chat_rows(s)] == ["failure", "success", "success"]
    assert len(chat_items(s)) == 2


def test_adm01_ac4_general_and_set_only_requests_are_counted_but_never_graded_or_given_a_session(fake, tracked_users):
    s = pupil(tracked_users)
    assert ask(s, "how do I use this app?", page="other").status_code == 200
    assert practice_msg(s).status_code == 200  # practice page without an attempt
    rows = chat_rows(s)
    assert [r[1] for r in rows] == ["success", "success"]
    assert all(r[4] is None for r in rows)  # no session
    assert chat_items(s) == []


def test_adm01_ac4_requests_rejected_before_the_chatbot_record_nothing(fake, tracked_users):
    s, other = pupil(tracked_users), pupil(tracked_users)
    foreign_attempt = start(other)
    before = sql("SELECT count(*) FROM analytics_chat_request")[0][0]
    rejected = [
        ask(s, "", page="practice", set_id=SET_ID),  # 422 invalid_message
        ask(s, "x" * 10_000, page="practice", set_id=SET_ID),  # 422 too long
        ask(s, "hi", page="practice", set_id=SET_ID, history=[{"role": "system", "text": "x"}]),  # 422 history
        ask(s, "hi", page="practice", attempt_id="no-such-attempt"),  # 404 unknown attempt
        ask(s, "hi", page="practice", attempt_id=foreign_attempt),  # 404 someone else's attempt
        call("POST", "/api/companion/messages", None, {"message": "hi", "history": [],
                                                       "context": {"page": "other", "set_id": None, "attempt_id": None, "label": None}}),
    ]
    assert [r.status_code for r in rejected][:2] == [422, 422] and rejected[-1].status_code == 401
    assert all(r.status_code >= 400 for r in rejected)
    assert chat_rows(s) == [] and chat_rows(other) == []
    assert sql("SELECT count(*) FROM analytics_chat_request")[0][0] == before
    assert fake.calls == []


def test_adm01_ac39_the_recorded_user_is_the_signed_in_student_whatever_the_body_says(fake, tracked_users):
    s, other = pupil(tracked_users), pupil(tracked_users)
    r = practice_msg(s, extra={"user_id": str(other), "student_id": str(other)})
    assert r.status_code in (200, 422)
    assert chat_rows(other) == []
    assert len(chat_rows(s)) == (1 if r.status_code == 200 else 0)
    assert sql("SELECT count(*) FROM analytics_chat_request WHERE user_id=%s", (str(other),)) == [(0,)]


def test_adm01_ac2_the_companion_response_is_identical_when_the_analytics_database_is_down(fake, tracked_users, broken_analytics):
    s = pupil(tracked_users)
    aid = start(s)
    r = practice_msg(s, attempt_id=aid)
    assert r.status_code == 200
    assert r.json() == {"reply": BENIGN, "mode": "hint", "withheld": False, "sources": []}
    fake.raises = llm_client.LlmTimeout("x")  # an error response is unchanged too
    err = practice_msg(s, attempt_id=aid)
    assert err.status_code == 503 and err.json()["detail"]["code"] == "llm_unavailable"
    assert chat_rows(s) == []  # nothing could be recorded


# ================================================================== practice attempt hooks

def test_adm01_ac15_starting_an_attempt_records_it_once_with_the_session_user_after_the_commit(fake, tracked_users, monkeypatch):
    from feature_analytics import recording

    s = pupil(tracked_users)
    seen = []
    real_open = recording.open_session

    def spy(*a, **k):
        seen.append(sql("SELECT count(*) FROM practice_attempt WHERE student_id=%s", (str(s),))[0][0])
        return real_open(*a, **k)

    monkeypatch.setattr(recording, "open_session", spy)
    aid = start(s)
    assert seen and all(n == 1 for n in seen), seen  # the attempt row was already committed when the hook ran
    ((ref, user_id, set_id, started, submitted),) = attempt_rows(s)
    assert (ref, user_id, set_id, submitted) == (str(aid), str(s), SET_ID, None)
    assert started is not None


def test_adm01_ac4_submitting_records_the_end_after_the_commit_with_the_stored_submission_time(fake, tracked_users, monkeypatch):
    from feature_analytics import recording

    s = pupil(tracked_users)
    aid = start(s)
    save(aid, s, CORRECT)
    seen = []
    real_open = recording.open_session

    def spy(*a, **k):
        seen.append(sql("SELECT status FROM practice_attempt WHERE id=%s", (aid,))[0][0])
        return real_open(*a, **k)

    monkeypatch.setattr(recording, "open_session", spy)
    submit(aid, s)
    assert seen and all(status == "submitted" for status in seen), seen  # fired only after the real commit
    (row,) = attempt_rows(s)
    stored = sql("SELECT submitted_at FROM practice_attempt WHERE id=%s", (aid,))[0][0]
    assert row[4] is not None and abs((row[4] - stored).total_seconds()) < 1


def test_adm01_ac15_a_rejected_submission_leaves_the_analytics_attempt_open(fake, tracked_users):
    owner, other = pupil(tracked_users), pupil(tracked_users)
    aid = start(owner)
    r = call("POST", f"/api/attempts/{aid}/submit", other)  # not the owner
    assert r.status_code in (403, 404)
    assert call("POST", "/api/attempts/no-such-attempt/submit", owner).status_code in (404, 422)
    assert attempt_rows(owner)[0][4] is None and attempt_rows(other) == []


def test_adm01_ac27_the_whole_flow_start_ask_submit_closes_the_session_and_later_chat_opens_none(fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    practice_msg(s, attempt_id=aid)
    practice_msg(s, attempt_id=aid)
    save(aid, s, CORRECT)
    submit(aid, s)
    practice_msg(s, "Why was I wrong?", attempt_id=aid)  # explain mode after submission
    rows = chat_rows(s)
    assert len(rows) == 3 and rows[0][4] is not None and rows[0][4] == rows[1][4] and rows[2][4] is None
    sessions = sql("SELECT activity_ref, end_reason, ended_at IS NOT NULL FROM analytics_session WHERE user_id=%s", (str(s),))
    assert sessions == [(str(aid), "activity_ended", True)]
    assert attempt_rows(s)[0][4] is not None


def test_adm01_ac2_start_and_submit_respond_exactly_as_before_when_the_analytics_database_is_down(
        fake, tracked_users, broken_analytics):
    s = pupil(tracked_users)
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", s)
    assert r.status_code == 201 and "attempt_id" in r.json()
    aid = r.json()["attempt_id"]
    save(aid, s, CORRECT)
    done = call("POST", f"/api/attempts/{aid}/submit", s)
    assert done.status_code == 200
    assert attempt_rows(s) == [] and chat_rows(s) == []  # nothing recorded, nothing raised


def test_adm01_ac2_the_practice_response_bodies_match_between_a_healthy_and_a_broken_recorder(fake, tracked_users, monkeypatch):
    from feature_analytics import recording

    def play(student):
        r1 = call("POST", f"/api/practice-sets/{SET_ID}/attempts", student)
        aid = r1.json()["attempt_id"]
        save(aid, student, CORRECT)
        r2 = call("POST", f"/api/attempts/{aid}/submit", student)
        return r1, r2

    ok1, ok2 = play(pupil(tracked_users))
    with monkeypatch.context() as m:
        m.setattr(recording, "open_session", boom)
        bad1, bad2 = play(pupil(tracked_users))
    assert (ok1.status_code, ok2.status_code) == (bad1.status_code, bad2.status_code) == (201, 200)
    assert set(ok1.json()) == set(bad1.json()) and set(ok2.json()) == set(bad2.json())
    for key in ("score_correct", "score_total", "status"):
        if key in ok2.json():
            assert ok2.json()[key] == bad2.json()[key]


# ================================================================== TEA-02: every exit after validation is one attempt + one outcome

@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac15_ac16_a_successful_generation_is_one_attempt_recorded_after_the_call_with_its_duration(workflow, tea):
    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    during = []

    def slow_call():
        during.append(new_attempts(since))  # nothing is recorded while the AI call is running (decision 8)
        time.sleep(0.3)

    fake.hook = slow_call
    r = generate(app, workflow, source)
    assert r.status_code == 201, r.text
    assert during == [[]]
    (row,) = new_attempts(since)
    assert row[1] == workflow and row[2] == "success"
    duration = sql("SELECT duration_ms FROM analytics_generation_attempt WHERE id=%s", (row[0],))[0][0]
    assert duration >= 250  # the accepted timestamp was taken before the call, so the duration covers it
    (item,) = new_items(since)
    assert item[1] == workflow
    assert item[3]  # the generated text is stored for grading (bounded and redacted)


FAILURES = [("LlmTimeout", 504), ("LlmUpstreamError", 502), ("LlmNotConfigured", 503), ("LlmBadResponse", 502),
            ("LlmInputTooLarge", 422), ("LlmError", 503)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
@pytest.mark.parametrize("name,status", FAILURES)
def test_adm01_ac16_every_other_error_of_the_call_is_one_unsuccessful_attempt_with_no_grading_item(workflow, name, status, tea):
    app, fake, since = tea
    source = upload(app)
    cls = getattr(llm_client, name)
    fake.error = cls("sentinel-secret private failure")
    assert generate(app, workflow, source).status_code == status
    rows = new_attempts(since)
    assert [(r[1], r[2]) for r in rows] == [(workflow, "failure")]
    assert new_items(since) == []


@pytest.mark.parametrize("workflow,bad_text", [("study_notes", ""), ("study_notes", "x" * 2001),
                                               ("mcq_batch", "not json at all"), ("mcq_batch", '{"questions": []}')])
def test_adm01_ac16_unusable_model_output_is_a_failure_never_a_success(workflow, bad_text, tea):
    app, fake, since = tea
    source = upload(app)
    fake.text = bad_text
    assert generate(app, workflow, source).status_code == 502
    assert [(r[1], r[2]) for r in new_attempts(since)] == [(workflow, "failure")]
    assert new_items(since) == []


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac16_a_save_failure_after_a_good_reply_is_an_unsuccessful_attempt(workflow, tea, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import Session

    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    real_commit = Session.commit
    state = {"failed": False}

    def fail_once(self, *a, **k):  # the host's save fails; the hooks' own later commits must work
        if not state["failed"]:
            state["failed"] = True
            raise SQLAlchemyError("sentinel-secret")
        return real_commit(self, *a, **k)

    monkeypatch.setattr(Session, "commit", fail_once)
    r = generate(app, workflow, source)
    monkeypatch.undo()
    assert r.status_code == 503, r.text
    assert [(row[1], row[2]) for row in new_attempts(since)] == [(workflow, "failure")]
    assert new_items(since) == []  # nothing was saved, so nothing is graded


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac15_requests_rejected_before_generation_create_no_attempt(workflow, tea, tea01_database):
    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    path = f"/api/teacher/materials/{source['id']}/{ROUTE[workflow]}"
    from test_tea02_notes import call as tea_call

    assert tea_call(app, "POST", path, user=None).status_code == 401
    assert tea_call(app, "POST", path, user="demo-student").status_code == 403
    assert tea_call(app, "POST", path, user="demo-teacher-other").status_code == 404
    assert tea_call(app, "POST", path.replace(source["id"], "00000000-0000-4000-8000-000000000000")).status_code == 404
    assert tea_call(app, "POST", path.replace(source["id"], "bad-id")).status_code == 422
    for label, data, status in (("not utf8", b"\xff", 422), ("empty", b" \r\n\t ", 422), ("too long", ("é" * 8001).encode(), 422)):
        bad_source = upload(app)
        replace_bytes(tea01_database, bad_source, data)
        assert generate(app, workflow, bad_source).status_code == status, label
    assert fake.calls == [] and new_attempts(since) == [] and new_items(since) == []


@pytest.mark.parametrize("workflow", WORKFLOWS)
@pytest.mark.parametrize("name,make", [("LlmRateLimited", lambda: llm_client.LlmRateLimited("minute", 17)),
                                       ("LlmBusy", lambda: llm_client.LlmBusy(17))], ids=["rate_limited", "busy"])
def test_adm01_decision8_a_rate_limited_or_busy_tea02_call_records_no_attempt_and_no_outcome(workflow, name, make, tea):
    """Explicit test of plan decision 8: the limiter acts inside the AI call, so the refusal is not an attempt."""
    app, fake, since = tea
    source = upload(app)
    fake.error = make()
    r = generate(app, workflow, source)
    assert r.status_code == 429 and r.json()["detail"]["retry_after_seconds"] == 17  # route answer unchanged
    assert len(fake.calls) == 1
    assert new_attempts(since) == [] and new_items(since) == []
    # every attempt row of the teacher, anywhere, still has an outcome: no outcome-less row from the refusal
    assert sql("SELECT count(*) FROM analytics_generation_attempt WHERE id > %s AND outcome='pending'", (since,)) == [(0,)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac16_after_any_mix_of_requests_no_route_path_leaves_a_pending_attempt(workflow, tea):
    app, fake, since = tea
    source = upload(app)
    for error in (None, llm_client.LlmTimeout("x"), llm_client.LlmBusy(3), llm_client.LlmUpstreamError("x"), None,
                  llm_client.LlmRateLimited("minute", 3)):
        prepare(fake, workflow)
        fake.error = error
        generate(app, workflow, source)
    rows = new_attempts(since)
    assert [r[2] for r in rows] == ["success", "failure", "failure", "success"]
    assert sql("SELECT count(*) FROM analytics_generation_attempt WHERE id > %s AND outcome='pending'", (since,)) == [(0,)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac39_the_recorded_user_is_the_signed_in_teacher_whatever_the_body_says(workflow, tea):
    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    r = generate(app, workflow, source, json={"created_by": "demo-teacher-other", "user_id": "demo-teacher-other"})
    assert r.status_code == 201
    assert sql("SELECT user_id FROM analytics_generation_attempt WHERE id > %s", (since,)) == [(TEACHER,)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm01_ac2_generation_responds_exactly_as_before_when_the_analytics_database_is_down(workflow, tea, monkeypatch):
    from feature_analytics import recording

    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    healthy = generate(app, workflow, source)
    with monkeypatch.context() as m:
        m.setattr(recording, "open_session", boom)
        down = generate(app, workflow, source)
        fake.error = llm_client.LlmTimeout("x")
        down_error = generate(app, workflow, source)
        fake.error = llm_client.LlmRateLimited("minute", 4)
        down_limited = generate(app, workflow, source)
    assert healthy.status_code == down.status_code == 201
    assert set(healthy.json()) == set(down.json())
    assert down_error.status_code == 504 and down_error.json()["detail"]["code"] == "llm_timeout"
    assert down_limited.status_code == 429 and down_limited.json()["detail"]["code"] == "llm_rate_limited"
    assert len(new_attempts(since)) == 1  # only the healthy request was recorded


# ---- AC23 / SHR-02: MCQ grading text carries stems and choices only

def test_adm01_ac23_an_mcq_generation_stores_stems_and_choices_but_never_the_key_or_explanation(tea):
    app, fake, since = tea
    source = upload(app)
    marker = "KEYMARK" + uid()[:8]
    fake.text, rows = mcq_with(marker)
    assert generate(app, "mcq_batch", source).status_code == 201
    (item,) = new_items(since)
    stored = " ".join(t or "" for t in item[2:5])
    assert item[1] == "mcq_batch"
    for row in rows:
        assert row["question"] in stored
        assert all(choice in stored for choice in row["choices"])
    assert marker not in stored and "explanation" not in stored.lower()
    assert "correct_choice_index" not in stored and "correct answer" not in stored.lower()


def test_adm01_ac23_a_study_notes_generation_is_stored_for_grading_with_its_own_workflow(tea):
    app, fake, since = tea
    source = upload(app, b"Functions should do one thing.")
    fake.text = "Core ideas\n- Give each function one responsibility."
    assert generate(app, "study_notes", source).status_code == 201
    (item,) = new_items(since)
    assert item[1] == "study_notes" and "one responsibility" in item[3]
