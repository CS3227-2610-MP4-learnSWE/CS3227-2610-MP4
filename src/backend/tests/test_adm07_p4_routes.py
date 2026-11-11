"""ADM-07 phase 4 host call sites (AC3, AC22, AC33, AC34): companion, TEA-02, sign-in, draft save and publish.

Contract: workflow/specs/ADM-07/plan.md "Hook contract [P4]" last bullet. Host responses must not change.
The SoC LLM is a fake injected through the dependency override; nothing networks.

Contract ambiguity recorded for the orchestrator: the plan names the practice-set save and publish call sites
but not which id is `practice_set_id` (the TEA-02/TEA-03 draft batch id or the published set id). The route
tests below therefore accept either id for the stored row, and require exactly one row per set and the
signed-in teacher's id.
"""
import pytest

import llm_client
from adm01_fixtures import privacy_scanner, tracked_users  # noqa: F401
from adm01_tea02 import WORKFLOWS, generate, prepare, tea, upload  # noqa: F401
from adm07_p4_helpers import event_cleanup, login_events, max_log_id, new_log_rows  # noqa: F401
from auth_helpers import call, login, new_student, sql
from adm02_helpers import actor
from companion_helpers import BENIGN, SET_ID, ask, start

pytestmark = pytest.mark.usefixtures("fake_provider")

KIND = {"study_notes": "generation_notes", "mcq_batch": "generation_mcq"}


def pupil(tracked):
    s = new_student("p4route")
    tracked.append(s)
    return s


def practice_msg(s, **kw):
    return ask(s, "Give me a hint please", page="practice", set_id=SET_ID, **kw)


def chat_id(user):
    return sql("SELECT id FROM analytics_chat_request WHERE user_id=%s ORDER BY id DESC LIMIT 1", (str(user),))[0][0]


# ================================================================== AC33/AC34: companion route

@pytest.mark.parametrize("exception,category", [
    (llm_client.LlmTimeout("x"), "timeout"),
    (llm_client.LlmUpstreamError("x"), "upstream"),
    (llm_client.LlmBadResponse("x"), "invalid_output"),
    (llm_client.LlmNotConfigured("x"), "upstream"),
    (llm_client.LlmRateLimited("student_minute", 12), "rate_limited"),
    (llm_client.LlmBusy(7), "rate_limited"),
], ids=["timeout", "upstream", "bad_response", "not_configured", "rate_limited", "busy"])
def test_adm07_ac34_companion_failure_is_logged_with_the_mapped_category(exception, category, fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    fake.raises = exception
    since = max_log_id()
    practice_msg(s, attempt_id=aid)
    assert new_log_rows(since) == [("chatbot", chat_id(s), "failure", category)]


def test_adm07_ac33_companion_success_is_logged_once_without_a_category(fake, tracked_users):
    s = pupil(tracked_users)
    aid = start(s)
    since = max_log_id()
    r = practice_msg(s, attempt_id=aid)
    assert r.status_code == 200 and r.json()["reply"] == BENIGN
    assert new_log_rows(since) == [("chatbot", chat_id(s), "success", None)]
    ((duration,),) = sql("SELECT duration_ms FROM analytics_request_log WHERE id > %s", (since,))
    assert duration is not None and duration >= 0


def test_adm07_ac33_companion_requests_rejected_before_processing_log_nothing(fake, tracked_users):
    s = pupil(tracked_users)
    since = max_log_id()
    assert ask(s, "x", page="practice", set_id=SET_ID, attempt_id="not-an-attempt").status_code >= 400
    assert new_log_rows(since) == []


@pytest.mark.parametrize("exception,status", [(llm_client.LlmTimeout("x"), 503), (llm_client.LlmRateLimited("s", 12), 429)])
def test_adm07_ac3_companion_responses_are_unchanged_when_the_analytics_database_is_down(
        exception, status, fake, tracked_users, monkeypatch):
    from feature_analytics import recording

    s = pupil(tracked_users)
    aid = start(s)
    healthy_ok = practice_msg(s, attempt_id=aid)
    fake.raises = exception
    healthy_fail = practice_msg(s, attempt_id=aid)
    fake.raises = None

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(recording, "open_session", boom)
    down_ok = practice_msg(s, attempt_id=aid)
    fake.raises = exception
    down_fail = practice_msg(s, attempt_id=aid)
    assert healthy_ok.status_code == down_ok.status_code == 200 and set(healthy_ok.json()) == set(down_ok.json())
    assert healthy_fail.status_code == down_fail.status_code == status
    assert healthy_fail.json() == down_fail.json()


# ================================================================== AC33/AC34: TEA-02 routes

@pytest.mark.parametrize("workflow", WORKFLOWS)
@pytest.mark.parametrize("name,category", [("LlmTimeout", "timeout"), ("LlmUpstreamError", "upstream"),
                                           ("LlmNotConfigured", "upstream"), ("LlmBadResponse", "invalid_output"),
                                           ("LlmError", "upstream")])
def test_adm07_ac34_generation_failure_is_logged_against_its_attempt_with_the_mapped_category(workflow, name, category, tea):
    app, fake, since = tea
    source = upload(app)
    fake.error = getattr(llm_client, name)("sentinel-secret")
    mark = max_log_id()
    generate(app, workflow, source)
    ((attempt_id, _, _),) = sql("SELECT id, workflow, outcome FROM analytics_generation_attempt WHERE id > %s", (since,))
    assert new_log_rows(mark) == [(KIND[workflow], attempt_id, "failure", category)]


@pytest.mark.parametrize("workflow,bad_text", [("study_notes", ""), ("mcq_batch", "not json at all")])
def test_adm07_ac34_unusable_model_output_is_logged_as_invalid_output(workflow, bad_text, tea):
    app, fake, since = tea
    source = upload(app)
    fake.text = bad_text
    mark = max_log_id()
    assert generate(app, workflow, source).status_code == 502
    ((kind, source_id, outcome, category),) = new_log_rows(mark)
    assert (kind, outcome, category) == (KIND[workflow], "failure", "invalid_output") and source_id is not None


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm07_ac33_generation_success_is_logged_once_without_a_category(workflow, tea):
    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    mark = max_log_id()
    assert generate(app, workflow, source).status_code == 201
    ((attempt_id,),) = sql("SELECT id FROM analytics_generation_attempt WHERE id > %s", (since,))
    assert new_log_rows(mark) == [(KIND[workflow], attempt_id, "success", None)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
@pytest.mark.parametrize("make", [lambda: llm_client.LlmRateLimited("minute", 17), lambda: llm_client.LlmBusy(17)],
                         ids=["rate_limited", "busy"])
def test_adm07_ac33_a_refused_generation_request_is_one_log_row_and_no_attempt_or_item(workflow, make, tea):
    app, fake, since = tea
    source = upload(app)
    fake.error = make()
    mark = max_log_id()
    r = generate(app, workflow, source)
    assert r.status_code == 429 and r.json()["detail"]["retry_after_seconds"] == 17  # response unchanged
    assert new_log_rows(mark) == [(KIND[workflow], None, "failure", "rate_limited")]
    assert sql("SELECT count(*) FROM analytics_generation_attempt WHERE id > %s", (since,)) == [(0,)]
    assert sql("SELECT count(*) FROM analytics_grading_item i JOIN analytics_generation_attempt a "
               "ON i.source_type='generation_attempt' AND i.source_id=a.id WHERE a.id > %s", (since,)) == [(0,)]


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm07_ac33_rejected_generation_requests_log_nothing(workflow, tea):
    from test_tea02_notes import call as tea_call

    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    path = f"/api/teacher/materials/{source['id']}/{'note-drafts' if workflow == 'study_notes' else 'mcq-drafts'}"
    mark = max_log_id()
    assert tea_call(app, "POST", path, user=None).status_code == 401
    assert tea_call(app, "POST", path, user="demo-student").status_code == 403
    assert tea_call(app, "POST", path, user="demo-teacher-other").status_code == 404
    assert new_log_rows(mark) == []


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_adm07_ac3_generation_responses_are_unchanged_when_the_analytics_database_is_down(workflow, tea, monkeypatch):
    from feature_analytics import recording

    app, fake, since = tea
    source = upload(app)
    prepare(fake, workflow)
    healthy = generate(app, workflow, source)

    def boom(*a, **k):
        raise RuntimeError("down")

    with monkeypatch.context() as m:
        m.setattr(recording, "open_session", boom)
        down = generate(app, workflow, source)
        fake.error = llm_client.LlmTimeout("x")
        down_error = generate(app, workflow, source)
        fake.error = llm_client.LlmRateLimited("minute", 4)
        down_limited = generate(app, workflow, source)
    assert healthy.status_code == down.status_code == 201 and set(healthy.json()) == set(down.json())
    assert down_error.status_code == 504 and down_error.json()["detail"]["code"] == "llm_timeout"
    assert down_limited.status_code == 429 and down_limited.json()["detail"]["code"] == "llm_rate_limited"


# ================================================================== AC22: sign-in call site

def test_adm07_ac22_a_successful_student_sign_in_records_one_login_event(event_cleanup):
    s = actor("student")  # actor() signs in once
    event_cleanup["users"].append(s)
    assert [r for r, _ in login_events(s)] == ["student"]
    assert login(s.email, s.password).status_code == 200
    assert [r for r, _ in login_events(s)] == ["student", "student"]


def test_adm07_ac22_a_successful_teacher_sign_in_records_a_teacher_event(event_cleanup):
    t = actor("teacher")
    event_cleanup["users"].append(t)
    assert [r for r, _ in login_events(t)] == ["teacher"]


def test_adm07_ac22_admin_sign_in_records_no_event(event_cleanup):
    a = actor("admin")
    event_cleanup["users"].append(a)
    assert login(a.email, a.password).status_code == 200
    assert login_events(a) == []


def test_adm07_ac22_failed_sign_in_session_bootstrap_and_logout_record_nothing(event_cleanup):
    s = actor("student")
    event_cleanup["users"].append(s)
    before = len(login_events(s))
    assert login(s.email, "definitely-wrong-password").status_code in (401, 403, 422)
    assert call("GET", "/api/auth/me", s).status_code == 200
    assert call("GET", "/api/auth/me", s).status_code == 200
    assert len(login_events(s)) == before
    assert call("POST", "/api/auth/logout", s).status_code in (200, 204)
    assert len(login_events(s)) == before


def test_adm07_ac22_a_disabled_account_sign_in_records_nothing(event_cleanup):
    s = actor("student")
    event_cleanup["users"].append(s)
    sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(s),))
    before = len(login_events(s))
    assert login(s.email, s.password).status_code != 200
    assert len(login_events(s)) == before


def test_adm07_ac3_sign_in_still_succeeds_with_the_same_response_when_the_analytics_database_is_down(
        event_cleanup, monkeypatch):
    from feature_analytics import recording

    s = actor("student")
    event_cleanup["users"].append(s)
    healthy = login(s.email, s.password)

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(recording, "open_session", boom)
    down = login(s.email, s.password)
    assert healthy.status_code == down.status_code == 200
    assert set(healthy.json()) == set(down.json())
    assert call("GET", "/api/auth/me", Student_from(down, s)).status_code == 200


def Student_from(response, s):
    from auth_helpers import student_from_login

    return student_from_login(response, s.email, s.password)


# ================================================================== AC22: practice-set save and publish call sites

def test_adm07_ac22_saving_and_publishing_a_practice_set_records_draft_started_and_published_once(mcqs, event_cleanup):
    from test_tea03_publications import post, prepared

    app, fake, source, draft = prepared(mcqs, "practice_set")
    ids = {draft["id"]}
    event_cleanup["sets"].append(draft["id"])
    saved = post(app, draft, "practice_set").json()
    ids.add(saved["id"])
    event_cleanup["sets"].append(saved["id"])
    again = post(app, draft, "practice_set")  # idempotent retry of the same publication
    assert again.status_code == 200
    drafts = sql("SELECT practice_set_id, teacher_id FROM analytics_practice_draft_started "
                 "WHERE practice_set_id = ANY(%s)", (list(ids),))
    published = sql("SELECT practice_set_id, teacher_id FROM analytics_practice_published "
                    "WHERE practice_set_id = ANY(%s)", (list(ids),))
    assert len(drafts) == 1 and drafts[0][1] == "demo-teacher"
    assert len(published) == 1 and published[0][1] == "demo-teacher"


def test_adm07_ac22_publishing_a_note_is_not_a_practice_set_event(mcqs, event_cleanup):
    from test_tea03_publications import post, prepared

    app, fake, source, draft = prepared(mcqs, "note")
    before = sql("SELECT count(*) FROM analytics_practice_published")[0][0]
    assert post(app, draft, "note").status_code == 201
    assert sql("SELECT count(*) FROM analytics_practice_published")[0][0] == before


def test_adm07_ac3_publishing_still_works_when_the_analytics_database_is_down(mcqs, event_cleanup, monkeypatch):
    from feature_analytics import recording
    from test_tea03_publications import post, prepared

    app, fake, source, draft = prepared(mcqs, "practice_set")

    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(recording, "open_session", boom)
    r = post(app, draft, "practice_set")
    assert r.status_code == 201, r.text
    event_cleanup["sets"].extend([draft["id"], r.json()["id"]])


from test_tea02_mcqs import mcqs  # noqa: E402,F401  (fixture)
