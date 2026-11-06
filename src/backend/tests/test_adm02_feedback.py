"""Independent ADM-02 AC01-25, access, validation and race tests."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from auth_helpers import call, code_of, login, sql, student_from_login
from stu01_helpers import make_course, make_draft, make_lesson, withdraw
from adm02_helpers import (ADMIN, PUBLIC, actor, answers, close, created, error,
                          form_get, inbox, payload, publish, published, question,
                          race, response, save, submit, uid)

KINDS = ["short_answer", "paragraph", "multiple_choice", "dropdown", "checkbox", "linear_scale"]


@pytest.fixture
def admin():
    return actor("admin")


@pytest.fixture
def user():
    return actor()


@pytest.mark.parametrize("kind", KINDS)
def test_adm02_ac01_03_06_six_types_draft_save_and_reopen_exact(admin, kind):
    body = payload([question(kind)])
    form = created(admin, body)
    assert form["state"] == "draft" and form["version"] == 1
    assert form["response_count"] == form["recipient_count"] == 0
    got = call("GET", f"{ADMIN}/forms/{form['id']}", admin)
    assert got.status_code == 200, got.text
    for key in body:
        assert got.json()[key] == body[key]
    assert "no-store" in got.headers["cache-control"]


def test_adm02_ac05_association_options_and_none_feature_lesson_metadata_only(admin, user):
    course = make_course()
    lesson = make_lesson(course, title="ADM02 public lesson", content="PROTECTED LESSON BODY")
    draft = make_draft(course)
    options = call("GET", ADMIN + "/associations", admin)
    assert options.status_code == 200, options.text
    assert set(options.json()) == {"features", "lessons", "truncated"}
    assert {"id": lesson, "title": "ADM02 public lesson"} in options.json()["lessons"]
    assert draft not in options.text and "PROTECTED LESSON BODY" not in options.text
    for association in (None, {"kind": "feature", "id": "ADM-02"}, {"kind": "lesson", "id": lesson}):
        form = published(admin, [user], payload(association=association))
        got = form_get(user, form)
        assert got.status_code == 200 and got.json()["association"] == association
        assert "PROTECTED LESSON BODY" not in got.text
    invalid = created(admin)
    for association in ({"kind": "feature", "id": "ADM-999"}, {"kind": "lesson", "id": draft}):
        body = payload(association=association)
        error(call("POST", ADMIN + "/forms", admin, body), 422, "invalid_feedback_association")
    withdraw(lesson)
    error(call("POST", ADMIN + "/forms", admin, payload(association={"kind": "lesson", "id": lesson})),
          422, "invalid_feedback_association")


def test_adm02_ac06_update_preserves_order_and_version_and_normalises_text(admin):
    body = payload([question("dropdown"), question("paragraph", False)])
    form = created(admin, body)
    body["title"] = "  Revised title  "
    body["questions"][0]["prompt"] = "  Changed prompt  "
    r = call("PUT", f"{ADMIN}/forms/{form['id']}", admin, {**body, "version": 1})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2 and r.json()["title"] == "Revised title"
    assert r.json()["questions"][0]["prompt"] == "Changed prompt"
    assert [q["id"] for q in r.json()["questions"]] == [q["id"] for q in body["questions"]]
    error(call("PUT", f"{ADMIN}/forms/{form['id']}", admin, {**body, "version": 1}),
          409, "feedback_version_conflict")


@pytest.mark.parametrize("method,suffix", [("GET", ""), ("PUT", "/draft"), ("POST", "/responses")])
def test_adm02_ac07_08_unpublished_form_is_hidden_and_no_inbox(admin, user, method, suffix):
    form = created(admin)
    assert inbox(user, form) is None
    body = {"version": 0, "answers": []} if method == "PUT" else {"draft_version": 0, "answers": []}
    error(call(method, f"{PUBLIC}/forms/{form['id']}{suffix}", user,
               None if method == "GET" else body), 404, "feedback_not_found")


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_adm02_ac09_12_explicit_audience_atomic_delivery_read_and_no_retroactive_target(admin, role):
    selected, excluded = actor(role), actor(role)
    form = created(admin)
    audience = call("GET", f"{ADMIN}/forms/{form['id']}/audience?role={role}&search={selected}", admin)
    assert audience.status_code == 200, audience.text
    selected_row = next(i for i in audience.json()["items"] if i["id"] == str(selected))
    assert set(selected_row) == {"id", "display_name", "role"} and selected_row["role"] == role
    pub = publish(admin, form, [selected])
    assert pub.status_code == 200, pub.text
    opened = pub.json()
    assert opened["recipient_count"] == 1 and opened["state"] == "open"
    item = inbox(selected, form)
    assert item["read_at"] is None and item["response_status"] == "not_started"
    assert inbox(excluded, form) is None
    assert inbox(actor(role), form) is None
    view = form_get(selected, form)
    assert view.status_code == 200 and view.json()["draft"] == {"version": 0, "answers": [], "updated_at": None}
    first_read = inbox(selected, form)["read_at"]
    assert first_read is not None
    form_get(selected, form)
    assert inbox(selected, form)["read_at"] == first_read
    error(publish(admin, form, [selected]), 409, "feedback_state_conflict")
    assert sql("SELECT count(*) FROM feedback_recipients WHERE form_id=%s", (form["id"],))[0][0] == 1
    error(form_get(excluded, form), 404, "feedback_not_found")


@pytest.mark.parametrize("bad", ["mixed", "duplicate", "missing", "empty", "inactive"])
def test_adm02_ac10_invalid_audience_rolls_back_all_inbox_and_state(admin, user, bad):
    form = created(admin)
    ids = [str(user)]
    if bad == "mixed":
        ids.append(str(actor("teacher")))
    elif bad == "duplicate":
        ids.append(str(user))
    elif bad == "missing":
        ids.append("u-missing")
    elif bad == "empty":
        ids = []
    else:
        sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(user),))
    r = call("POST", f"{ADMIN}/forms/{form['id']}/publish", admin,
             {"version": 1, "audience_role": "student", "recipient_ids": ids})
    expected = "invalid_feedback_audience" if bad in ("duplicate", "empty") else "feedback_audience_changed"
    error(r, 422 if bad in ("duplicate", "empty") else 409, expected)
    got = call("GET", f"{ADMIN}/forms/{form['id']}", admin).json()
    assert got["state"] == "draft" and got["recipient_count"] == 0
    assert sql("SELECT count(*) FROM feedback_recipients WHERE form_id=%s", (form["id"],))[0][0] == 0


@pytest.mark.parametrize("kind", KINDS)
def test_adm02_ac04_22_24_incomplete_required_draft_restores_but_submission_requires_answer(admin, user, kind):
    form = published(admin, [user], payload([question(kind)]))
    partial = [{"question_id": form["questions"][0]["id"], "value": None}]
    saved = save(user, form, partial)
    assert saved.status_code == 200 and saved.json()["version"] == 1, saved.text
    assert form_get(user, form).json()["draft"]["answers"] == partial
    error(submit(user, form, partial, 1), 422, "invalid_feedback_answers")
    assert inbox(user, form)["response_status"] == "draft"
    receipt = submit(user, form, answers(form), 1)
    assert receipt.status_code == 201, receipt.text
    assert inbox(user, form)["response_status"] == "completed"
    done = form_get(user, form).json()
    assert done["submitted"] is True and done["draft"] is None and done["questions"] == []
    error(save(user, form, partial, 1), 409, "feedback_already_submitted")
    error(submit(user, form, answers(form), 1), 409, "feedback_already_submitted")


def test_adm02_ac22_23_25_draft_exact_whitespace_owner_only_and_new_login_restores(admin, user):
    other = actor()
    form = published(admin, [user, other], payload([question("paragraph"), question("short_answer")]))
    secret = "  PRIVATE DRAFT <script>alert(1)</script>\n  unfinished  "
    data = [{"question_id": form["questions"][0]["id"], "value": secret}]
    saved = save(user, form, data)
    assert saved.status_code == 200, saved.text
    again = student_from_login(login(user.email, user.password), user.email, user.password)
    assert form_get(again, form).json()["draft"]["answers"] == data
    assert form_get(other, form).json()["draft"]["answers"] == []
    listing = call("GET", f"{ADMIN}/forms/{form['id']}/responses", admin)
    assert listing.json() == {"items": [], "next_offset": None}
    assert secret not in listing.text
    admin_view = call("GET", f"{ADMIN}/forms/{form['id']}", admin)
    assert admin_view.json()["response_count"] == 0 and secret not in admin_view.text
    assert secret not in call("GET", PUBLIC + "/inbox", user).text
    error(form_get(admin, form), 403, "forbidden")
    error(save(admin, form, data), 403, "forbidden")
    error(save(user, form, data, 0), 409, "feedback_draft_version_conflict")
    assert form_get(user, form).json()["draft"]["answers"] == data


def test_adm02_ac18_20_final_snapshot_preserves_question_and_required_text_and_private_review(admin, user):
    form = published(admin, [user], payload([question("checkbox"), question("paragraph", False)]))
    final = answers(form, optional_null=True)
    receipt = submit(user, form, final)
    assert receipt.status_code == 201, receipt.text
    got = response(admin, form, receipt.json())
    assert got["form_id"] == form["id"] and got["respondent"]["id"] == str(user)
    assert got["form_snapshot"]["questions"] == form["questions"]
    assert got["answers"][0]["value"] == [o["id"] for o in form["questions"][0]["options"]]
    assert got["answers"][1]["value"] is None
    update = {k: deepcopy(form[k]) for k in ("title", "description", "association", "questions")}
    update["questions"][0]["prompt"] = "Changed after publication"
    error(call("PUT", f"{ADMIN}/forms/{form['id']}", admin, {**update, "version": form["version"]}),
          409, "feedback_state_conflict")
    assert response(admin, form, receipt.json()) == got
    second_form = created(admin)
    error(call("GET", f"{ADMIN}/forms/{second_form['id']}/responses/{receipt.json()['id']}", admin),
          404, "feedback_not_found")
    for outsider in (user, actor(), actor("teacher")):
        error(call("GET", f"{ADMIN}/forms/{form['id']}/responses", outsider), 403, "forbidden")
        error(call("GET", f"{ADMIN}/forms/{form['id']}/responses/{receipt.json()['id']}", outsider),
              403, "forbidden")


def test_adm02_ac14_17_closure_keeps_submitted_and_hides_drafts_no_reopen(admin, user):
    pending = actor()
    form = published(admin, [user, pending])
    receipt = submit(user, form, answers(form))
    assert receipt.status_code == 201
    assert save(pending, form, answers(form)).status_code == 200
    closed = close(admin, form)
    assert closed.status_code == 200 and closed.json()["state"] == "closed", closed.text
    assert close(admin, form).json()["version"] == closed.json()["version"]
    terminal = form_get(pending, form).json()
    assert terminal["questions"] == [] and terminal["draft"] is None and not terminal["submitted"]
    assert inbox(pending, form)["response_status"] == "closed"
    assert inbox(user, form)["response_status"] == "completed"
    error(submit(pending, form, answers(form), 1), 409, "feedback_closed")
    error(save(pending, form, answers(form), 1), 409, "feedback_closed")
    assert response(admin, form, receipt.json())["form_snapshot"]["questions"] == form["questions"]
    assert sql("SELECT count(*) FROM feedback_response_drafts WHERE form_id=%s", (form["id"],))[0][0] == 1
    for method, suffix in (("DELETE", ""), ("POST", "/reopen"), ("POST", "/analyse")):
        r = call(method, f"{ADMIN}/forms/{form['id']}{suffix}", admin)
        assert r.status_code in (404, 405)


@pytest.mark.parametrize("mutation", ["extra", "blank_title", "no_questions", "duplicate_question", "duplicate_option", "bad_scale", "bad_bool"])
def test_adm02_validation_rejects_malformed_form_without_partial_save(admin, mutation):
    body = payload([question("dropdown")])
    code = "invalid_feedback_input"
    if mutation == "extra": body["created_by"] = "demo-admin"
    elif mutation == "blank_title": body["title"], code = "  ", "invalid_feedback_title"
    elif mutation == "no_questions": body["questions"], code = [], "invalid_feedback_questions"
    elif mutation == "duplicate_question": body["questions"] *= 2; code = "invalid_feedback_questions"
    elif mutation == "duplicate_option":
        body["questions"][0]["options"][1]["label"] = " FIRST "; code = "invalid_feedback_options"
    elif mutation == "bad_scale":
        body["questions"] = [question("linear_scale")]
        body["questions"][0]["scale"]["max"] = True; code = "invalid_feedback_scale"
    elif mutation == "bad_bool": body["questions"][0]["required"] = "true"
    error(call("POST", ADMIN + "/forms", admin, body), 422, code)


@pytest.mark.parametrize("kind,value", [("short_answer", 7), ("short_answer", "x" * 501),
    ("paragraph", "x" * 5001), ("multiple_choice", "foreign"), ("dropdown", []),
    ("checkbox", ["foreign"]), ("linear_scale", True), ("linear_scale", 6)])
def test_adm02_answer_validation_applies_to_drafts_and_submission(admin, user, kind, value):
    form = published(admin, [user], payload([question(kind)]))
    data = [{"question_id": form["questions"][0]["id"], "value": value}]
    error(save(user, form, data), 422, "invalid_feedback_draft_answers")
    error(submit(user, form, data), 422, "invalid_feedback_answers")
    assert form_get(user, form).json()["draft"]["version"] == 0


@pytest.mark.parametrize("bad", ["foreign", "duplicate", "unknown_key", "oversize"])
def test_adm02_forged_answers_or_oversize_never_saved(admin, user, bad):
    form = published(admin, [user])
    data = answers(form)
    body = {"version": 0, "answers": data}
    if bad == "foreign": data[0]["question_id"] = uid()
    if bad == "duplicate": data.append(deepcopy(data[0]))
    if bad == "unknown_key": body["user_id"] = "demo-student"
    if bad == "oversize": data[0]["value"] = "x" * 262145
    r = call("PUT", f"{PUBLIC}/forms/{form['id']}/draft", user, body)
    error(r, 413 if bad == "oversize" else 422,
          "feedback_too_large" if bad == "oversize" else "invalid_feedback_input" if bad == "unknown_key" else "invalid_feedback_draft_answers")


@pytest.mark.parametrize("query", ["?limit=0", "?limit=101", "?offset=-1", "?extra=1", "?limit=1&limit=2"])
def test_adm02_bounded_strict_queries(admin, query):
    error(call("GET", ADMIN + "/forms" + query, admin), 422, "invalid_feedback_input")


@pytest.mark.parametrize("method,suffix", [("GET", ""), ("PUT", "/draft"), ("POST", "/responses")])
def test_adm02_respondent_visibility_and_no_spoofed_identity(admin, user, method, suffix):
    form = published(admin, [user])
    outsider = actor()
    body = {"version": 0, "answers": []} if method == "PUT" else {"draft_version": 0, "answers": []}
    error(call(method, f"{PUBLIC}/forms/{form['id']}{suffix}", outsider,
               None if method == "GET" else body,
               headers={"X-Student-Id": str(user), "X-Demo-User-Id": str(user)}), 404, "feedback_not_found")
    error(call(method, f"{PUBLIC}/forms/not-an-id{suffix}", user,
               None if method == "GET" else body), 404, "feedback_not_found")


def test_adm02_all_routes_auth_roles_csrf_and_no_store(admin, user):
    form = published(admin, [user])
    paths = [("GET", ADMIN + "/forms"), ("POST", ADMIN + "/forms"),
             ("GET", ADMIN + "/associations"), ("GET", f"{ADMIN}/forms/{form['id']}"),
             ("PUT", f"{ADMIN}/forms/{form['id']}"),
             ("GET", f"{ADMIN}/forms/{form['id']}/audience?role=student"),
             ("POST", f"{ADMIN}/forms/{form['id']}/publish"),
             ("POST", f"{ADMIN}/forms/{form['id']}/close"),
             ("GET", f"{ADMIN}/forms/{form['id']}/responses"),
             ("GET", f"{ADMIN}/forms/{form['id']}/responses/{uid()}"),
             ("GET", PUBLIC + "/inbox"), ("GET", f"{PUBLIC}/forms/{form['id']}"),
             ("PUT", f"{PUBLIC}/forms/{form['id']}/draft"),
             ("POST", f"{PUBLIC}/forms/{form['id']}/responses")]
    teacher = actor("teacher")
    for method, path in paths:
        error(call(method, path), 401, "unauthenticated")
        wrong = admin if path.startswith(PUBLIC) else user
        error(call(method, path, wrong, {} if method != "GET" else None), 403, "forbidden")
        if path.startswith(ADMIN):
            error(call(method, path, teacher, {} if method != "GET" else None), 403, "forbidden")
        if method in ("POST", "PUT"):
            good = admin if path.startswith(ADMIN) else user
            error(call(method, path, good, {}, csrf=False), 403, "csrf_failed")
            error(call(method, path, good, {}, headers={"Origin": "https://evil.example"}), 403, "csrf_failed")


def test_adm02_disabled_account_loses_draft_and_submit_access(admin, user):
    form = published(admin, [user])
    assert save(user, form, answers(form)).status_code == 200
    sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(user),))
    error(form_get(user, form), 401, "unauthenticated")
    error(save(user, form, answers(form), 1), 401, "unauthenticated")
    error(submit(user, form, answers(form), 1), 401, "unauthenticated")


def test_adm02_concurrent_admin_updates_prevent_lost_edits(admin):
    form = created(admin)
    bodies = [payload(), payload()]
    replies = race(*(lambda body=body: call("PUT", f"{ADMIN}/forms/{form['id']}", admin,
                     {**body, "version": 1}) for body in bodies))
    assert sorted(r.status_code for r in replies) == [200, 409]
    loser = next(r for r in replies if r.status_code == 409)
    assert code_of(loser) == "feedback_version_conflict"
    winner = next(r.json() for r in replies if r.status_code == 200)
    assert call("GET", f"{ADMIN}/forms/{form['id']}", admin).json()["title"] == winner["title"]


def test_adm02_concurrent_publication_creates_exactly_one_recipient_set(admin, user):
    form = created(admin)
    replies = race(lambda: publish(admin, form, [user]), lambda: publish(admin, form, [user]))
    assert sorted(r.status_code for r in replies) == [200, 409]
    assert sql("SELECT count(*) FROM feedback_recipients WHERE form_id=%s", (form["id"],))[0][0] == 1


def test_adm02_ac22_two_tabs_cannot_overwrite_same_draft_version(admin, user):
    form = published(admin, [user])
    values = [[{"question_id": form["questions"][0]["id"], "value": text}] for text in ("Tab A", "Tab B")]
    replies = race(lambda: save(user, form, values[0]), lambda: save(user, form, values[1]))
    assert sorted(r.status_code for r in replies) == [200, 409]
    winner = next(r.json() for r in replies if r.status_code == 200)
    assert form_get(user, form).json()["draft"] == winner
    assert code_of(next(r for r in replies if r.status_code == 409)) == "feedback_draft_version_conflict"


def test_adm02_ac24_duplicate_submission_exactly_one_response(admin, user):
    form = published(admin, [user])
    replies = race(lambda: submit(user, form, answers(form)), lambda: submit(user, form, answers(form)))
    assert sorted(r.status_code for r in replies) == [201, 409]
    assert code_of(next(r for r in replies if r.status_code == 409)) == "feedback_already_submitted"
    assert sql("SELECT count(*) FROM feedback_responses WHERE form_id=%s", (form["id"],))[0][0] == 1


def test_adm02_ac24_save_racing_submit_never_recreates_completed_draft(admin, user):
    form = published(admin, [user])
    replies = race(lambda: save(user, form, answers(form)), lambda: submit(user, form, answers(form)))
    save_reply, submit_reply = replies
    if submit_reply.status_code == 201:
        error(save_reply, 409, "feedback_already_submitted")
        assert sql("SELECT count(*) FROM feedback_response_drafts WHERE form_id=%s", (form["id"],))[0][0] == 0
    else:
        assert save_reply.status_code == 200, save_reply.text
        error(submit_reply, 409, "feedback_draft_version_conflict")
        assert submit(user, form, answers(form), 1).status_code == 201
    assert inbox(user, form)["response_status"] == "completed"


@pytest.mark.parametrize("operation", ["save", "submit"])
def test_adm02_ac15_24_close_race_linearises_and_rejects_every_late_write(admin, user, operation):
    form = published(admin, [user])
    write = (lambda: save(user, form, answers(form))) if operation == "save" else (lambda: submit(user, form, answers(form)))
    written, closed = race(write, lambda: close(admin, form))
    assert closed.status_code == 200, closed.text
    assert written.status_code in (200, 201, 409), written.text
    if written.status_code == 409: assert code_of(written) == "feedback_closed"
    error(write(), 409, "feedback_closed")
    detail = call("GET", f"{ADMIN}/forms/{form['id']}", admin).json()
    assert detail["state"] == "closed"
    assert detail["response_count"] == (1 if written.status_code == 201 else 0)


def test_adm02_ac06_22_draft_and_form_survive_fresh_application_process(admin, user):
    form = published(admin, [user])
    data = [{"question_id": form["questions"][0]["id"], "value": "persist exactly  \n"}]
    assert save(user, form, data).status_code == 200
    script = """import json, os, sys
sys.path.insert(0, 'tests')
from auth_helpers import Student, call, seed_state
seed_state['ready'] = True
u = Student(os.environ['ADM02_UID'], email='', password='', token=os.environ['ADM02_TOKEN'], csrf=os.environ['ADM02_CSRF'])
r = call('GET', '/api/feedback/forms/' + os.environ['ADM02_FORM'], u)
assert r.status_code == 200, r.text
print(json.dumps(r.json()['draft']['answers']))
"""
    env = dict(os.environ, ADM02_UID=str(user), ADM02_TOKEN=user.token,
               ADM02_CSRF=user.csrf, ADM02_FORM=form["id"])
    r = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-1000:]
    assert json.loads(r.stdout.strip().splitlines()[-1]) == data


def test_adm02_publication_inbox_failure_rolls_back_state_and_all_recipients(admin, user):
    form = created(admin)
    trigger, function = "adm02_fail_" + uid().replace("-", ""), "adm02_function_" + uid().replace("-", "")
    sql(f"CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
        f"IF NEW.form_id = '{form['id']}'::uuid THEN RAISE EXCEPTION 'PRIVATE-DB-ERROR-ADM02'; "
        "END IF; RETURN NEW; END $$")
    sql(f"CREATE TRIGGER {trigger} BEFORE INSERT ON feedback_recipients FOR EACH ROW EXECUTE FUNCTION {function}()")
    try:
        r = publish(admin, form, [user, actor()])
        error(r, 503, "feedback_unavailable")
        assert "PRIVATE-DB-ERROR-ADM02" not in r.text
        got = call("GET", f"{ADMIN}/forms/{form['id']}", admin).json()
        assert got["state"] == "draft" and got["recipient_count"] == 0
        assert sql("SELECT count(*) FROM feedback_recipients WHERE form_id=%s", (form["id"],))[0][0] == 0
    finally:
        sql(f"DROP TRIGGER {trigger} ON feedback_recipients")
        sql(f"DROP FUNCTION {function}()")


def test_adm02_read_quota_is_bounded_and_reports_retry_after(admin):
    for _ in range(120):
        r = call("GET", ADMIN + "/forms", admin)
        assert r.status_code == 200, r.text
    r = call("GET", ADMIN + "/forms", admin)
    error(r, 429, "feedback_rate_limited")
    assert int(r.headers["retry-after"]) >= 1


def test_adm02_draft_save_quota_is_separate_from_other_mutations(admin, user):
    form = published(admin, [user])
    for version in range(120):
        r = save(user, form, answers(form), version)
        assert r.status_code == 200, (version, r.text)
    r = save(user, form, answers(form), 120)
    error(r, 429, "feedback_rate_limited")
    assert int(r.headers["retry-after"]) >= 1
