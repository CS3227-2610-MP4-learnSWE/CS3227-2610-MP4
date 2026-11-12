"""ADM-08 AC28 (SHR-01, SHR-05): GET /api/admin/messaging/followup-counts.

Contract: workflow/specs/ADM-08/plan.md "The new endpoint: follow-up count" and "Test plan". The value is global (shared by
the whole test database), so each test compares against a baseline read just before it acts. The SoC LLM is never reached:
the read-only test also proves no analysis row is created.
"""
import json

import pytest

from auth_helpers import call, sql
from adm02_helpers import ADMIN as FEEDBACK, actor, answers, created, payload, published, submit, race
from adm04_helpers import ADMIN, PREVIEWS, announcement, check_error, delivered, feedback, preview

URL = ADMIN + "/followup-counts"


@pytest.fixture
def admin():
    return actor("admin")


def count(admin):
    reply = call("GET", URL, admin)
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert set(body) == {"unanswered_responses"}
    value = body["unanswered_responses"]
    assert isinstance(value, int) and not isinstance(value, bool) and value >= 0
    return value


def reply_to(admin, rid, subject="Your feedback"):
    return delivered(admin, preview(admin, dict(kind="feedback_response", response_id=rid, subject=subject, body="Thanks.")))


def test_adm08_followup_count_401_anonymous():
    check_error(call("GET", URL, None), 401, "unauthenticated")


@pytest.mark.parametrize("role", ["student", "teacher"])
def test_adm08_followup_count_403_non_admin(role):
    reply = call("GET", URL, actor(role))
    assert reply.status_code == 403, reply.text
    assert "no-store" in reply.headers.get("cache-control", "")
    assert "unanswered_responses" not in reply.text


def test_adm08_followup_count_exact_shape_and_no_store(admin):
    reply = call("GET", URL, admin)
    assert reply.status_code == 200 and reply.json().keys() == {"unanswered_responses"}
    assert "no-store" in reply.headers.get("cache-control", "")


def test_adm08_followup_count_counts_responses_without_reply(admin):
    other_admin = actor("admin")
    base = count(admin)
    users = [actor() for _ in range(3)]
    form = published(admin, users, payload())
    rids = [submit(u, form, answers(form)).json()["id"] for u in users]
    assert count(admin) == base + 3
    reply_to(admin, rids[0])
    assert count(admin) == base + 2
    reply_to(other_admin, rids[1])  # a reply sent by a different admin also answers it
    assert count(admin) == base + 1


def test_adm08_followup_count_teacher_respondents_are_counted(admin):
    base = count(admin)
    teacher = actor("teacher")
    form = published(admin, [teacher], payload())
    assert submit(teacher, form, answers(form)).status_code == 201
    assert count(admin) == base + 1


def test_adm08_followup_count_announcement_does_not_answer(admin):
    user = actor()
    feedback(admin, user)
    base = count(admin)
    delivered(admin, preview(admin, announcement([user])))
    assert count(admin) == base


def test_adm08_followup_count_drafts_and_unsubmitted_are_not_counted(admin):
    base = count(admin)
    created(admin)
    published(admin, [actor()], payload())  # published, nobody has submitted
    assert count(admin) == base


@pytest.mark.parametrize("state", ["disabled", "archived"])
def test_adm08_followup_count_excludes_unavailable_respondents(admin, state):
    user = actor()
    feedback(admin, user)
    base = count(admin)
    sql('UPDATE "user" SET access_status=%s WHERE id=%s', (state, str(user)))
    assert count(admin) == base - 1
    sql('UPDATE "user" SET access_status=\'enabled\' WHERE id=%s', (str(user),))
    assert count(admin) == base


def test_adm08_followup_count_excludes_archived_at_timestamp(admin):
    user = actor()
    feedback(admin, user)
    base = count(admin)
    sql('UPDATE "user" SET archived_at=now() WHERE id=%s', (str(user),))
    assert count(admin) == base - 1
    sql('UPDATE "user" SET archived_at=NULL WHERE id=%s', (str(user),))
    assert count(admin) == base


def test_adm08_followup_count_deleted_response_not_counted(admin):
    user = actor()
    form, rid = feedback(admin, user)
    base = count(admin)
    gone = call("DELETE", f"{FEEDBACK}/forms/{form['id']}/responses/{rid}", admin)
    assert gone.status_code in (200, 204), gone.text
    assert count(admin) == base - 1


def test_adm08_followup_count_same_for_all_admins(admin):
    other = actor("admin")
    feedback(admin, actor())
    assert count(admin) == count(other)


def test_adm08_followup_count_no_leakage(admin):
    evil = '<img src=x onerror=alert(1)> "; DROP TABLE x; --'
    user = actor()
    body = payload()
    body["title"] = "ADM08 " + evil
    form = published(admin, [user], body)
    receipt = submit(user, form, answers(form))
    assert receipt.status_code == 201
    reply = call("GET", URL, admin)
    assert reply.status_code == 200 and list(reply.json()) == ["unanswered_responses"]
    text = json.dumps(reply.json()) + reply.text + json.dumps(dict(reply.headers))
    for secret in (str(user), user.email, receipt.json()["id"], form["id"], "ADM08", "text", "onerror"):
        assert secret not in text


@pytest.mark.parametrize("query", ["?x=1", "?user_id=abc", "?limit=1", "?offset=0", "?form_id=" + "a" * 36])
def test_adm08_followup_count_rejects_query(admin, query):
    base = count(admin)
    check_error(call("GET", URL + query, admin), 422, "INVALID_REQUEST")
    assert count(admin) == base


def test_adm08_followup_count_read_only(admin):
    feedback(admin, actor())
    tables = ("feedback_responses", "feedback_forms", "feedback_analyses", "admin_messages",
              "admin_message_deliveries", "admin_message_previews")

    def rows():
        return tuple(sql("SELECT count(*) FROM " + t)[0][0] for t in tables)

    before = rows()
    for _ in range(5):
        assert call("GET", URL, admin).status_code == 200
    assert rows() == before  # nothing written; no analysis row, so no SoC LLM call was made


def test_adm08_followup_count_rate_limited(admin):
    assert [call("GET", URL, admin).status_code for _ in range(20)] == [200] * 20
    reply = call("GET", URL, admin)
    check_error(reply, 429, "MESSAGING_RATE_LIMITED")
    assert reply.json()["detail"]["retry_after_seconds"] > 0


def test_adm08_followup_count_shares_the_messaging_read_bucket(admin):
    for _ in range(10):
        assert call("GET", ADMIN + "/recipients?role=student", admin).status_code == 200
    for _ in range(10):
        assert call("GET", URL, admin).status_code == 200
    check_error(call("GET", ADMIN + "/recipients?role=student", admin), 429, "MESSAGING_RATE_LIMITED")


def test_adm08_followup_count_quota_is_per_admin(admin):
    other = actor("admin")
    for _ in range(20):
        call("GET", URL, admin)
    assert call("GET", URL, admin).status_code == 429
    assert call("GET", URL, other).status_code == 200


def test_adm08_followup_count_concurrent_with_send(admin):
    users = [actor() for _ in range(3)]
    form = published(admin, users, payload())
    rids = [submit(u, form, answers(form)).json()["id"] for u in users]
    reader = actor("admin")
    base = count(reader)
    value = preview(admin, dict(kind="feedback_response", response_id=rids[0], subject="Reply", body="Thanks."))
    replies = race(lambda: call("POST", f"{PREVIEWS}/{value['id']}/send", admin, {}),
                   lambda: call("GET", URL, reader), lambda: call("GET", URL, reader),
                   lambda: call("POST", f"{PREVIEWS}/{value['id']}/send", admin, {}))
    assert replies[0].status_code == 200 and replies[3].status_code == 200
    for r in replies[1:3]:
        assert r.status_code == 200, r.text
        assert r.json()["unanswered_responses"] in (base, base - 1)
    assert count(reader) == base - 1  # two sends of one preview decrease the count by exactly 1


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_adm08_followup_count_method_not_allowed_and_changes_nothing(admin, method):
    base = count(admin)
    assert call(method, URL, admin, {}).status_code == 405
    assert count(admin) == base
