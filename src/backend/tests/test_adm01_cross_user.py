"""ADM-01 cross-user and isolation tests (task 23), Phase A.

Contract: workflow/specs/ADM-01/plan.md ("API endpoints", "Recording hooks"), AC1, AC11, AC19, AC39.
  * student and teacher cannot call any /api/admin/analytics/* endpoint, with or without a user filter;
  * an admin response never contains another source's private text (nor emails, nor answer keys);
  * no admin endpoint accepts a user id for filtering (HTTP behaviour and the published OpenAPI);
  * hooks take the user id only as an explicit keyword and never touch another user's rows.

The hook tests are code-shape/contract tests on the documented signatures plus behaviour through the
documented tables; they do not read any implementation.

TODO(phase B): assert at the host routes (companion, practice attempt, TEA-02) that the recorded
user id is the signed-in session's id even when the request body names another user. That needs the
route paths and call sites from developer check 4.
"""
import inspect
import re
import uuid

import pytest

from adm01_fixtures import privacy_scanner, analytics_admin, analytics_student, analytics_teacher, no_ai, tracked_users  # noqa: F401
from adm01_helpers import (GENERATION, QUALITY, RUNS, USAGE, day, run_count, seed_generation_response,
                           seed_student_response, send, url)
from adm02_helpers import actor, uid
from auth_helpers import call, sql

FORBIDDEN_KEYS = {"request_text", "response_text", "context_text", "prompt", "reply", "messages", "email",
                  "password", "password_hash", "answer_key", "correct_answer", "explanation"}
DATA_KEYS = ("chatbot", "workflows", "grades", "run_id", "practice_completion", "recording_started_on")


def all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from all_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from all_keys(v)


@pytest.fixture
def sources(tracked_users):
    """Two students and a teacher whose private text sits in the analytics tables, with unique sentinels."""
    tag = uuid.uuid4().hex[:10]
    a, b, t = actor("student"), actor("student"), actor("teacher")
    tracked_users.extend([a, b, t])
    s = {"tag": tag, "a": a, "b": b, "t": t,
         "sentinels": [f"PRIVREQ-A-{tag}", f"PRIVRESP-A-{tag}", f"PRIVCTX-A-{tag}", f"PRIVREQ-B-{tag}",
                       f"PRIVRESP-B-{tag}", f"PRIVGENREQ-T-{tag}", f"ANSWERKEY-T-{tag}"]}
    seed_student_response(a, request_text=s["sentinels"][0], response_text=s["sentinels"][1],
                          context_text=s["sentinels"][2])
    seed_student_response(b, request_text=s["sentinels"][3], response_text=s["sentinels"][4])
    seed_generation_response(t, request_text=s["sentinels"][5],
                             response_text=f"Q1: Which? \n A) one\n B) two\n Correct answer: {s['sentinels'][6]}")
    s["identities"] = [str(x) for x in (a, b, t)]
    return s


# ---------------------------------------------------------------- student/teacher cannot call any endpoint

def hostile_requests(other_user_id):
    p = {"period_start": day(5), "period_end": day(0)}
    gets = [url(USAGE, **p), url(USAGE, user_id=other_user_id, **p), url(USAGE, role="student", **p),
            url(GENERATION, **p), url(GENERATION, user_id=other_user_id, **p),
            url(QUALITY, workflow="student_exercise", **p), url(QUALITY, workflow="teacher_lesson_planning", **p),
            url(QUALITY, workflow="student_exercise", user_id=other_user_id, limit=100, **p),
            RUNS + "/1", RUNS + "/999999999"]
    posts = [{"workflow": "student_exercise", **p}, {"workflow": "teacher_lesson_planning", **p},
             {"workflow": "student_exercise", "user_id": other_user_id, **p}]
    return [("GET", g, None) for g in gets] + [("POST", RUNS, b) for b in posts]


@pytest.mark.parametrize("who,status", [("student", 403), ("teacher", 403), ("anonymous", 401)])
def test_adm01_ac1_ac39_non_admins_cannot_call_any_analytics_endpoint_even_with_a_user_filter(
        who, status, analytics_student, analytics_teacher, sources, no_ai):
    caller = {"student": analytics_student, "teacher": analytics_teacher, "anonymous": None}[who]
    before = run_count()
    for method, path, body in hostile_requests(sources["identities"][0]):
        r = call(method, path, caller, body)
        assert r.status_code == status, (who, method, path, r.status_code, r.text)
        assert not any(s in r.text for s in sources["sentinels"] + sources["identities"]), (method, path)
        assert not any(k in r.text for k in DATA_KEYS), (method, path, r.text)
    assert run_count() == before and not no_ai.calls


def test_adm01_ac39_a_student_cannot_read_their_own_analytics_either(sources, no_ai):
    """Own data is not special: there is no per-user analytics read in the contract."""
    r = call("GET", url(USAGE, period_start=day(0), period_end=day(0), user_id=str(sources["a"])), sources["a"])
    assert r.status_code == 403, r.text
    r = call("GET", url(QUALITY, workflow="student_exercise", period_start=day(0), period_end=day(0)), sources["a"])
    assert r.status_code == 403, r.text


# ---------------------------------------------------------------- admin never sees private text

def admin_responses(admin):
    p = {"period_start": day(0), "period_end": day(0)}
    out = [send(admin, "usage", **p), send(admin, "generation", **p)]
    for wf in ("student_exercise", "teacher_lesson_planning"):
        out.append(send(admin, "quality", workflow=wf, limit=100, **p))
    started = send(admin, "start", **p)
    out += [started]
    if started.status_code == 202:
        out.append(call("GET", f"{RUNS}/{started.json()['run_id']}", admin))
    return out


def test_adm01_ac11_ac39_admin_responses_never_contain_another_sources_private_text(
        analytics_admin, sources, no_ai):
    responses = admin_responses(analytics_admin)
    assert [r.status_code for r in responses[:4]] == [200, 200, 200, 200], [r.text for r in responses]
    assert responses[4].status_code == 202 and responses[5].status_code == 200
    for r in responses:
        for secret in sources["sentinels"]:
            assert secret not in r.text, (r.request.url, secret)
        assert not FORBIDDEN_KEYS & set(all_keys(r.json())), (r.request.url, set(all_keys(r.json())))
    assert not no_ai.calls


def test_adm01_ac11_the_seeded_responses_are_visible_as_rows_but_without_their_text(analytics_admin, sources, no_ai):
    """Guards against a vacuous pass: the sources exist in the report, only their text is withheld."""
    student = send(analytics_admin, "quality", workflow="student_exercise", limit=100,
                   period_start=day(0), period_end=day(0)).json()
    teacher = send(analytics_admin, "quality", workflow="teacher_lesson_planning", limit=100,
                   period_start=day(0), period_end=day(0)).json()
    assert student["items"]["total"] >= 2 and teacher["items"]["total"] >= 1
    assert all(i["status"] in ("pending", "graded", "grading_failed", "content_expired", "privacy_blocked")
               for i in student["items"]["rows"] + teacher["items"]["rows"])
    for row in student["items"]["rows"] + teacher["items"]["rows"]:
        assert not FORBIDDEN_KEYS & set(row)


def test_adm01_ac11_the_usage_report_shows_names_and_counts_only(analytics_admin, sources, no_ai, tracked_users):
    sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, completed_at, "
        "duration_ms, outcome) VALUES (%s,'student',NULL,NULL,now(),now(),500,'success')", (str(sources["a"]),))
    r = send(analytics_admin, "usage", period_start=day(0), period_end=day(0))
    assert r.status_code == 200, r.text
    for row in r.json()["chatbot"]["student"]["rows"]:
        assert set(row) == {"user_id", "name", "successful", "unsuccessful"}, row
    assert sources["a"].email not in r.text


# ---------------------------------------------------------------- no user-id filter anywhere

@pytest.mark.parametrize("kind,extra", [("usage", {}), ("generation", {}), ("quality", {"workflow": "student_exercise"})])
@pytest.mark.parametrize("filter_", [{"user_id": "STUDENT_A"}, {"student_id": "STUDENT_A"}, {"role": "student"},
                                     {"email": "x@example.com"}, {"requested_by": "STUDENT_A"}])
def test_adm01_ac39_admin_endpoints_ignore_or_reject_a_user_filter(kind, extra, filter_, analytics_admin, sources, no_ai):
    p = {"period_start": day(0), "period_end": day(0), **extra}
    baseline = send(analytics_admin, kind, **p)
    assert baseline.status_code == 200, baseline.text
    value = {k: str(sources["a"]) if v == "STUDENT_A" else v for k, v in filter_.items()}
    r = send(analytics_admin, kind, **p, **value)
    # Not accepted for filtering: either rejected, or the answer is exactly the unfiltered one.
    assert r.status_code in (200, 422), r.text
    if r.status_code == 200:
        assert r.json() == baseline.json()


def test_adm01_ac39_the_published_api_declares_no_user_selecting_parameter(no_ai):
    r = call("GET", "/openapi.json")
    if r.status_code != 200:
        pytest.skip("OpenAPI schema is not published")
    spec = r.json()
    ops = [(path, method, op) for path, item in spec["paths"].items() if path.startswith("/api/admin/analytics")
           for method, op in item.items() if method in ("get", "post")]
    # ADM-07 P2-5: 4 new read endpoints (health, hourly, daily, chatbot-users) join the 5 ADM-01 ones.
    assert len(ops) == 9, [(p, m) for p, m, _ in ops]
    banned = re.compile(r"user|student|teacher|email|role|owner|requested", re.I)
    for path, method, op in ops:
        for param in op.get("parameters", []):
            if path.endswith("/chatbot-users") and param["name"] == "role":
                continue  # ADM-07 plan: `role` selects the student/teacher table, never a user
            assert not banned.search(param["name"]), (path, method, param["name"])
        body = op.get("requestBody")
        if body:
            ref = body["content"]["application/json"]["schema"].get("$ref")
            schema = spec["components"]["schemas"][ref.rsplit("/", 1)[1]] if ref else body["content"]["application/json"]["schema"]
            assert set(schema["properties"]) == {"workflow", "period_start", "period_end"}, schema


# ---------------------------------------------------------------- hooks: the user id is an explicit keyword only

HOOKS = {
    # plan decision 4: no `role` parameter (every recorded chat request is a student request)
    "record_chat_request_received": ([], {"user_id", "activity_type", "activity_ref", "received_at"}),
    "record_chat_request_outcome": (["request_id"], {"success", "grading", "completed_at", "source", "identity_values", "failure_category"}),  # ADM-07 P4: plan adds failure_category
    "record_practice_attempt_started": ([], {"user_id", "practice_set_id", "attempt_ref", "started_at"}),
    "record_practice_attempt_submitted": ([], {"attempt_ref", "submitted_at"}),
    "record_generation_accepted": ([], {"workflow", "user_id", "accepted_at"}),
    "record_generation_outcome": (["attempt_id"], {"success", "grading", "completed_at", "source", "identity_values", "failure_category"}),  # ADM-07 P4
}


@pytest.mark.parametrize("name", sorted(HOOKS))
def test_adm01_ac39_hook_signature_matches_the_documented_contract(name):
    from feature_analytics import recording

    fn = getattr(recording, name)
    assert not inspect.iscoroutinefunction(fn), "hooks are plain synchronous functions"
    params = inspect.signature(fn).parameters
    positional = [n for n, p in params.items() if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    keyword_only = {n for n, p in params.items() if p.kind == p.KEYWORD_ONLY}
    expected_positional, expected_kw = HOOKS[name]
    assert positional == expected_positional, (name, positional)
    assert keyword_only == expected_kw, (name, keyword_only)
    assert not any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params.values()), name


@pytest.mark.parametrize("name", ["record_chat_request_received", "record_practice_attempt_started",
                                  "record_generation_accepted"])
def test_adm01_ac39_hooks_that_create_rows_require_the_user_id(name):
    from feature_analytics import recording

    p = inspect.signature(getattr(recording, name)).parameters["user_id"]
    assert p.default is inspect.Parameter.empty and p.kind is p.KEYWORD_ONLY


@pytest.mark.parametrize("name", ["record_chat_request_outcome", "record_practice_attempt_submitted",
                                  "record_generation_outcome"])
def test_adm01_ac39_follow_up_hooks_cannot_name_another_user(name):
    """Outcome and submission hooks identify the row, never a user: no user_id/role parameter exists."""
    from feature_analytics import recording

    names = set(inspect.signature(getattr(recording, name)).parameters)
    assert not {n for n in names if re.search(r"user|student|teacher|owner|role", n)}, names


# ---------------------------------------------------------------- hooks: behaviour is per-user

def test_adm01_ac39_hooks_write_exactly_the_user_id_they_are_given(tracked_users):
    from feature_analytics import recording

    a, b, t = actor("student"), actor("student"), actor("teacher")
    tracked_users.extend([a, b, t])
    ref_a, ref_b = "att-" + uid(), "att-" + uid()
    recording.record_practice_attempt_started(user_id=str(a), practice_set_id="s", attempt_ref=ref_a)
    recording.record_practice_attempt_started(user_id=str(b), practice_set_id="s", attempt_ref=ref_b)
    rid_a = recording.record_chat_request_received(user_id=str(a),
                                                   activity_type="practice_attempt", activity_ref=ref_a)
    rid_b = recording.record_chat_request_received(user_id=str(b),
                                                   activity_type="practice_attempt", activity_ref=ref_b)
    gid = recording.record_generation_accepted(workflow="mcq_batch", user_id=str(t))
    assert sql("SELECT user_id, role FROM analytics_chat_request WHERE id=%s", (rid_a,)) == [(str(a), "student")]
    assert sql("SELECT user_id, role FROM analytics_chat_request WHERE id=%s", (rid_b,)) == [(str(b), "student")]
    assert sql("SELECT user_id FROM analytics_practice_attempt WHERE attempt_ref=%s", (ref_a,)) == [(str(a),)]
    assert sql("SELECT user_id FROM analytics_session WHERE activity_ref=%s", (ref_b,)) == [(str(b),)]
    assert sql("SELECT user_id, workflow FROM analytics_generation_attempt WHERE id=%s", (gid,)) == [(str(t), "mcq_batch")]


def test_adm01_ac39_an_outcome_changes_only_the_request_it_names(tracked_users):
    from feature_analytics import recording

    a, b = actor("student"), actor("student")
    tracked_users.extend([a, b])
    rid_a = recording.record_chat_request_received(user_id=str(a))
    rid_b = recording.record_chat_request_received(user_id=str(b))
    recording.record_chat_request_outcome(rid_a, success=True)
    assert sql("SELECT outcome FROM analytics_chat_request WHERE id=%s", (rid_a,)) == [("success",)]
    assert sql("SELECT outcome, completed_at FROM analytics_chat_request WHERE id=%s", (rid_b,)) == [("pending", None)]
    gid_a = recording.record_generation_accepted(workflow="study_notes", user_id=str(a))
    gid_b = recording.record_generation_accepted(workflow="study_notes", user_id=str(b))
    recording.record_generation_outcome(gid_a, success=False)
    assert sql("SELECT outcome FROM analytics_generation_attempt WHERE id=%s", (gid_a,)) == [("failure",)]
    assert sql("SELECT outcome FROM analytics_generation_attempt WHERE id=%s", (gid_b,)) == [("pending",)]


def test_adm01_ac39_a_submission_closes_only_the_owners_session_and_attempt(tracked_users):
    from feature_analytics import recording

    a, b = actor("student"), actor("student")
    tracked_users.extend([a, b])
    shared, own_b = "att-" + uid(), "att-" + uid()
    recording.record_practice_attempt_started(user_id=str(a), practice_set_id="s", attempt_ref=shared)
    recording.record_practice_attempt_started(user_id=str(b), practice_set_id="s", attempt_ref=own_b)
    for user in (a, b):  # b's activity_ref text collides with a's attempt reference
        recording.record_chat_request_received(user_id=str(user),
                                               activity_type="practice_attempt", activity_ref=shared)
    recording.record_practice_attempt_submitted(attempt_ref=shared)
    assert sql("SELECT submitted_at IS NOT NULL FROM analytics_practice_attempt WHERE attempt_ref=%s", (shared,)) == [(True,)]
    assert sql("SELECT submitted_at FROM analytics_practice_attempt WHERE attempt_ref=%s", (own_b,)) == [(None,)]
    assert sql("SELECT end_reason FROM analytics_session WHERE user_id=%s AND activity_ref=%s AND ended_at IS NOT NULL",
               (str(a), shared)) == [("activity_ended",)]
    # only the attempt owner's session is closed; b's session with the same activity_ref text stays open
    assert sql("SELECT activity_ref FROM analytics_session WHERE user_id=%s AND ended_at IS NULL", (str(b),)) == [(shared,)]


def test_adm01_ac39_follow_up_hooks_with_unknown_ids_create_nothing_and_do_not_raise(tracked_users):
    from feature_analytics import recording

    def counts():
        return [sql(f"SELECT count(*) FROM {t}")[0][0] for t in
                ("analytics_chat_request", "analytics_generation_attempt", "analytics_practice_attempt",
                 "analytics_session", "analytics_grading_item")]

    before = counts()
    assert recording.record_chat_request_outcome(None, success=True) is None
    assert recording.record_chat_request_outcome(2 ** 40, success=True) is None
    assert recording.record_generation_outcome(None, success=True) is None
    assert recording.record_generation_outcome(2 ** 40, success=False) is None
    assert recording.record_practice_attempt_submitted(attempt_ref="no-such-attempt-" + uid()) is None
    assert counts() == before
