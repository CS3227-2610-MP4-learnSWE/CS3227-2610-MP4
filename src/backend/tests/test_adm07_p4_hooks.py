"""ADM-07 phase 4 recording hooks (AC3, AC22, AC33, AC34, AC37 hook level).

Contract: workflow/specs/ADM-07/plan.md "Hook contract [P4]", "Data model [P4]". Hooks are called with keyword
arguments exactly as listed there. The SoC LLM is always a fake (dependency override); nothing networks.
"""
import logging
from datetime import datetime, timedelta, timezone

import pytest

import llm_client
from adm01_fixtures import privacy_scanner, tracked_users  # noqa: F401
from adm01_grading_helpers import new_window
from adm02_helpers import actor, race, uid
from adm07_p4_helpers import (CATEGORIES, event_cleanup, log_row, login_events, max_log_id, new_log_rows)  # noqa: F401
from auth_helpers import sql

UTC = timezone.utc


def boom(*args, **kwargs):
    raise RuntimeError("analytics database is down")


def student(tracked):
    u = actor("student")
    tracked.append(u)
    return u


# ================================================================== AC34 category mapping (pure function)

@pytest.mark.parametrize("make,expected", [
    (lambda: llm_client.LlmRateLimited("minute", 5), "rate_limited"),
    (lambda: llm_client.LlmBusy(5), "rate_limited"),
    (lambda: llm_client.LlmTimeout("x"), "timeout"),
    (lambda: llm_client.LlmBadResponse("x"), "invalid_output"),
    (lambda: llm_client.LlmUpstreamError("x"), "upstream"),
    (lambda: llm_client.LlmNotConfigured("x"), "upstream"),
    (lambda: llm_client.LlmInputTooLarge("x"), "upstream"),  # another LlmError
    (lambda: llm_client.LlmError("x"), "upstream"),
    (lambda: RuntimeError("x"), "unclassified"),
    (lambda: ValueError("x"), "unclassified"),
    (lambda: KeyError("x"), "unclassified"),
], ids=["rate_limited", "busy", "timeout", "bad_response", "upstream", "not_configured", "input_too_large",
        "llm_error", "runtime", "value", "key"])
def test_adm07_ac34_categorize_llm_error_maps_each_exception_class(make, expected):
    from feature_analytics.recording import FAILURE_CATEGORIES, categorize_llm_error

    assert tuple(FAILURE_CATEGORIES) == CATEGORIES
    assert categorize_llm_error(make()) == expected


def test_adm07_ac34_reply_cut_off_is_invalid_output_and_wins_over_its_parent_class():
    from feature_analytics.recording import categorize_llm_error

    cls = llm_client.LlmReplyCutOff
    try:
        exc = cls("cut off")
    except TypeError:  # constructor shape is the client's business; any instance will do
        exc = cls.__new__(cls)
    assert categorize_llm_error(exc) == "invalid_output"


# ================================================================== AC33 chatbot request log

def test_adm07_ac33_received_creates_one_pending_row_and_outcome_updates_it_once(tracked_users):
    from feature_analytics import recording

    s = student(tracked_users)
    since = max_log_id()
    rid = recording.record_chat_request_received(user_id=str(s))
    assert rid is not None
    assert new_log_rows(since) == [("chatbot", rid, "pending", None)]
    recording.record_chat_request_outcome(rid, success=True)
    ((outcome, category, duration, _),) = log_row("chatbot", rid)
    chat_duration = sql("SELECT duration_ms FROM analytics_chat_request WHERE id=%s", (rid,))[0][0]
    assert (outcome, category) == ("success", None) and duration == chat_duration
    assert len(new_log_rows(since)) == 1


@pytest.mark.parametrize("given,stored", [("timeout", "timeout"), ("rate_limited", "rate_limited"),
                                          ("invalid_output", "invalid_output"), ("upstream", "upstream"),
                                          ("unclassified", "unclassified"), (None, "unclassified"),
                                          ("not-a-category", "unclassified")])
def test_adm07_ac33_failure_stores_the_category_and_unknown_or_missing_becomes_unclassified(given, stored, tracked_users):
    from feature_analytics import recording

    s = student(tracked_users)
    rid = recording.record_chat_request_received(user_id=str(s))
    recording.record_chat_request_outcome(rid, success=False, failure_category=given)
    ((outcome, category, _, _),) = log_row("chatbot", rid)
    assert (outcome, category) == ("failure", stored)


def test_adm07_ac34_a_success_ignores_a_category_it_was_given(tracked_users):
    from feature_analytics import recording

    s = student(tracked_users)
    rid = recording.record_chat_request_received(user_id=str(s))
    recording.record_chat_request_outcome(rid, success=True, failure_category="timeout")
    ((outcome, category, _, _),) = log_row("chatbot", rid)
    assert (outcome, category) == ("success", None)


def test_adm07_ac33_the_first_outcome_wins_and_repeats_change_nothing(tracked_users):
    from feature_analytics import recording

    s = student(tracked_users)
    rid = recording.record_chat_request_received(user_id=str(s))
    recording.record_chat_request_outcome(rid, success=False, failure_category="upstream")
    recording.record_chat_request_outcome(rid, success=True)
    recording.record_chat_request_outcome(rid, success=False, failure_category="timeout")
    ((outcome, category, _, _),) = log_row("chatbot", rid)
    assert (outcome, category) == ("failure", "upstream")
    assert sql("SELECT outcome FROM analytics_chat_request WHERE id=%s", (rid,)) == [("failure",)]


def test_adm07_ac33_outcome_for_unknown_or_none_id_writes_nothing():
    from feature_analytics import recording

    since = max_log_id()
    assert recording.record_chat_request_outcome(None, success=True) is None
    assert recording.record_chat_request_outcome(2_000_000_000, success=False, failure_category="timeout") is None
    assert new_log_rows(since) == []


# ================================================================== AC33 generation request log

@pytest.mark.parametrize("workflow,kind", [("study_notes", "generation_notes"), ("mcq_batch", "generation_mcq")])
def test_adm07_ac33_generation_attempt_is_logged_with_its_workflow_kind_and_outcome(workflow, kind, tracked_users):
    from feature_analytics import recording

    t = actor("teacher")
    tracked_users.append(t)
    since = max_log_id()
    aid = recording.record_generation_accepted(workflow=workflow, user_id=str(t))
    assert aid is not None
    assert new_log_rows(since) == [(kind, aid, "pending", None)]
    recording.record_generation_outcome(aid, success=False, failure_category="invalid_output")
    recording.record_generation_outcome(aid, success=True)  # first outcome wins
    ((outcome, category, _, _),) = log_row(kind, aid)
    assert (outcome, category) == ("failure", "invalid_output")


@pytest.mark.parametrize("workflow,kind", [("study_notes", "generation_notes"), ("mcq_batch", "generation_mcq")])
def test_adm07_ac33_rate_limited_generation_writes_one_log_row_and_no_attempt_or_grading_item(workflow, kind):
    from feature_analytics import recording

    attempts = sql("SELECT count(*) FROM analytics_generation_attempt")[0][0]
    items = sql("SELECT count(*) FROM analytics_grading_item")[0][0]
    since = max_log_id()
    at = new_window().at(30)
    assert recording.record_generation_rate_limited(workflow=workflow, occurred_at=at) is None
    assert new_log_rows(since) == [(kind, None, "failure", "rate_limited")]
    assert sql("SELECT occurred_at, duration_ms FROM analytics_request_log WHERE id > %s", (since,)) == [(at, None)]
    assert sql("SELECT count(*) FROM analytics_generation_attempt")[0][0] == attempts
    assert sql("SELECT count(*) FROM analytics_grading_item")[0][0] == items


@pytest.mark.parametrize("workflow", ["bogus", "", None, "STUDY_NOTES", "chat"])
def test_adm07_ac33_rate_limited_with_an_invalid_workflow_writes_nothing(workflow):
    from feature_analytics import recording

    since = max_log_id()
    assert recording.record_generation_rate_limited(workflow=workflow) is None
    assert new_log_rows(since) == []


def test_adm07_ac33_two_rate_limited_requests_are_two_rows():
    from feature_analytics import recording

    since = max_log_id()
    recording.record_generation_rate_limited(workflow="study_notes")
    recording.record_generation_rate_limited(workflow="study_notes")
    assert len(new_log_rows(since)) == 2  # source_id is null, the partial unique index must not merge them


# ================================================================== AC22 login events

@pytest.mark.parametrize("role", ["student", "teacher"])
def test_adm07_ac22_record_login_stores_user_role_and_time_and_each_call_is_one_event(role, event_cleanup):
    from feature_analytics import recording

    u = actor(role)
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))  # actor() signs in once itself
    at = datetime(2040, 5, 5, 8, 0, tzinfo=UTC)
    recording.record_login(user_id=str(u), role=role, occurred_at=at)
    recording.record_login(user_id=str(u), role=role, occurred_at=at)
    assert login_events(u) == [(role, at), (role, at)]


@pytest.mark.parametrize("role", ["admin", "ADMIN", "", "owner", None])
def test_adm07_ac22_record_login_for_any_other_role_including_admin_is_a_no_op(role, event_cleanup):
    from feature_analytics import recording

    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    assert recording.record_login(user_id=str(u), role=role) is None
    assert login_events(u) == []


def test_adm07_ac22_record_login_for_an_unknown_user_is_swallowed():
    from feature_analytics import recording

    assert recording.record_login(user_id="u-no-such-user-" + uid(), role="student") is None


def test_adm07_ac22_login_event_default_time_is_now(event_cleanup):
    from feature_analytics import recording

    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    before = datetime.now(UTC)
    recording.record_login(user_id=str(u), role="student")
    ((_, at),) = login_events(u)
    assert before - timedelta(seconds=5) <= at <= datetime.now(UTC) + timedelta(seconds=5)


# ================================================================== AC22 / AC37 draft started and published

def test_adm07_ac22_draft_started_is_recorded_once_per_set_with_the_first_time(event_cleanup):
    from feature_analytics import recording

    t = actor("teacher")
    sid = "p4-set-" + uid()
    event_cleanup["sets"].append(sid)
    first = datetime(2040, 6, 1, 9, 0, tzinfo=UTC)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t), started_at=first)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t),
                                            started_at=first + timedelta(days=3))  # every later save
    assert sql("SELECT teacher_id, started_at FROM analytics_practice_draft_started WHERE practice_set_id=%s",
               (sid,)) == [(str(t), first)]


def test_adm07_ac22_publish_unpublish_publish_again_leaves_one_row_with_the_first_time(event_cleanup):
    from feature_analytics import recording

    t = actor("teacher")
    sid = "p4-set-" + uid()
    event_cleanup["sets"].append(sid)
    first = datetime(2040, 6, 1, 9, 0, tzinfo=UTC)
    for offset in (0, 2, 5):  # publish, republish after unpublish, publish again: the host calls on every transition
        recording.record_practice_published(practice_set_id=sid, teacher_id=str(t),
                                            published_at=first + timedelta(days=offset))
    assert sql("SELECT teacher_id, published_at FROM analytics_practice_published WHERE practice_set_id=%s",
               (sid,)) == [(str(t), first)]


def test_adm07_ac22_a_set_saved_already_published_counts_once_in_each_series(event_cleanup):
    from feature_analytics import recording

    t = actor("teacher")
    sid = "p4-set-" + uid()
    event_cleanup["sets"].append(sid)
    at = datetime(2040, 6, 1, 9, 0, tzinfo=UTC)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t), started_at=at)
    recording.record_practice_published(practice_set_id=sid, teacher_id=str(t), published_at=at)
    assert sql("SELECT count(*) FROM analytics_practice_draft_started WHERE practice_set_id=%s", (sid,)) == [(1,)]
    assert sql("SELECT count(*) FROM analytics_practice_published WHERE practice_set_id=%s", (sid,)) == [(1,)]


@pytest.mark.parametrize("bad_id", ["", "x" * 101])
def test_adm07_ac22_practice_set_id_must_be_1_to_100_characters(bad_id, event_cleanup):
    from feature_analytics import recording

    t = actor("teacher")
    assert recording.record_practice_draft_started(practice_set_id=bad_id, teacher_id=str(t)) is None
    assert recording.record_practice_published(practice_set_id=bad_id, teacher_id=str(t)) is None
    assert sql("SELECT count(*) FROM analytics_practice_draft_started WHERE practice_set_id=%s", (bad_id,)) == [(0,)]
    assert sql("SELECT count(*) FROM analytics_practice_published WHERE practice_set_id=%s", (bad_id,)) == [(0,)]


def test_adm07_ac22_a_set_that_is_edited_published_or_removed_keeps_its_events(event_cleanup):
    """There is no update or delete path: the hooks never overwrite the stored first time."""
    from feature_analytics import recording

    t = actor("teacher")
    sid = "p4-set-" + uid()
    event_cleanup["sets"].append(sid)
    first = datetime(2040, 7, 1, tzinfo=UTC)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t), started_at=first)
    recording.record_practice_published(practice_set_id=sid, teacher_id=str(t), published_at=first)
    recording.record_practice_draft_started(practice_set_id=sid, teacher_id="demo-teacher-other", started_at=first - timedelta(days=9))
    assert sql("SELECT teacher_id, started_at FROM analytics_practice_draft_started WHERE practice_set_id=%s",
               (sid,)) == [(str(t), first)]


# ================================================================== AC37 concurrency at hook level

def test_adm07_ac37_two_simultaneous_outcomes_leave_one_log_row_with_the_first_outcome(tracked_users):
    from feature_analytics import recording

    s = student(tracked_users)
    for _ in range(5):
        since = max_log_id()
        rid = recording.record_chat_request_received(user_id=str(s))
        race(lambda: recording.record_chat_request_outcome(rid, success=True),
             lambda: recording.record_chat_request_outcome(rid, success=False, failure_category="timeout"))
        rows = new_log_rows(since)
        assert len(rows) == 1 and rows[0][1] == rid
        chat = sql("SELECT outcome FROM analytics_chat_request WHERE id=%s", (rid,))[0][0]
        assert rows[0][2] == chat  # the log row and the chat row agree on the single applied outcome
        assert rows[0][3] == (None if chat == "success" else "timeout")


def test_adm07_ac37_many_simultaneous_generation_outcomes_apply_once(tracked_users):
    from feature_analytics import recording

    t = actor("teacher")
    tracked_users.append(t)
    since = max_log_id()
    aid = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t))
    race(*[(lambda i=i: recording.record_generation_outcome(
        aid, success=(i % 2 == 0), failure_category=None if i % 2 == 0 else "upstream")) for i in range(6)])
    rows = new_log_rows(since)
    assert len(rows) == 1
    attempt = sql("SELECT outcome FROM analytics_generation_attempt WHERE id=%s", (aid,))[0][0]
    assert rows[0][2] == attempt


def test_adm07_ac37_two_simultaneous_login_hooks_create_two_events(event_cleanup):
    from feature_analytics import recording

    u = actor("student")
    event_cleanup["users"].append(u)
    sql("DELETE FROM analytics_login_event WHERE user_id=%s", (str(u),))
    race(lambda: recording.record_login(user_id=str(u), role="student"),
         lambda: recording.record_login(user_id=str(u), role="student"))
    assert len(login_events(u)) == 2


def test_adm07_ac37_simultaneous_draft_started_and_published_hooks_create_one_row_each(event_cleanup):
    from feature_analytics import recording

    t = actor("teacher")
    sid = "p4-set-" + uid()
    event_cleanup["sets"].append(sid)
    race(*([lambda: recording.record_practice_draft_started(practice_set_id=sid, teacher_id=str(t))] * 4
           + [lambda: recording.record_practice_published(practice_set_id=sid, teacher_id=str(t))] * 4))
    assert sql("SELECT count(*) FROM analytics_practice_draft_started WHERE practice_set_id=%s", (sid,)) == [(1,)]
    assert sql("SELECT count(*) FROM analytics_practice_published WHERE practice_set_id=%s", (sid,)) == [(1,)]


# ================================================================== AC3 hooks never raise

def _all_new_hooks(user_id):
    from feature_analytics import recording

    return {
        "record_generation_rate_limited": lambda: recording.record_generation_rate_limited(workflow="study_notes"),
        "record_login": lambda: recording.record_login(user_id=user_id, role="student"),
        "record_practice_draft_started": lambda: recording.record_practice_draft_started(
            practice_set_id="p4-x", teacher_id=user_id),
        "record_practice_published": lambda: recording.record_practice_published(
            practice_set_id="p4-x", teacher_id=user_id),
        "record_chat_request_outcome(category)": lambda: recording.record_chat_request_outcome(
            7, success=False, failure_category="timeout"),
        "record_generation_outcome(category)": lambda: recording.record_generation_outcome(
            7, success=False, failure_category="upstream"),
    }


@pytest.mark.parametrize("name", ["record_generation_rate_limited", "record_login", "record_practice_draft_started",
                                  "record_practice_published", "record_chat_request_outcome(category)",
                                  "record_generation_outcome(category)"])
def test_adm07_ac3_a_new_or_extended_hook_with_an_unavailable_database_returns_none_and_logs_no_content(
        name, monkeypatch, caplog):
    from feature_analytics import recording

    monkeypatch.setattr(recording, "open_session", boom)
    caplog.set_level(logging.DEBUG)
    assert _all_new_hooks("u-someone-private")[name]() is None
    assert "u-someone-private" not in caplog.text and "p4-x" not in caplog.text


def test_adm07_ac3_received_hooks_with_an_unavailable_database_still_return_none(monkeypatch):
    from feature_analytics import recording

    monkeypatch.setattr(recording, "open_session", boom)
    assert recording.record_chat_request_received(user_id="u-someone") is None
    assert recording.record_generation_accepted(workflow="study_notes", user_id="u-someone") is None


def test_adm07_ac3_purge_never_raises_when_the_database_is_unavailable(monkeypatch):
    from feature_analytics import recording, retention

    for module in (recording, retention):
        if hasattr(module, "open_session"):
            monkeypatch.setattr(module, "open_session", boom)
    assert recording.purge_expired_request_log() in (0, None)
    retention.purge_expired()  # must not raise
