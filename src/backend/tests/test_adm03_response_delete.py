"""ADM-03 amendment, task 15, AC39-AC50: admin delete of a feedback response and its effects on stored analyses."""
import re

import pytest

from auth_helpers import call, sql
from adm02_helpers import (ADMIN as ADM02, actor, answers, close, created, error, inbox, payload, publish, published,
                           race, save, submit, uid)
from adm03_fixtures import admin, llm  # noqa: F401
from adm03_helpers import (BASE, MSG, create, expect, get, listing, release, run, start_blocked, text_form, wait_done)

NOT_FOUND = "This response was not found. It may already have been deleted, or it does not belong to this form."
AI_DELETED = re.compile(r"The AI step stopped while (processing batch \d+ of \d+|starting the AI step) because (\d+) of the (\d+) selected "
                        r"responses were deleted after the analysis started\. The statistics remain correct for the responses present "
                        r"when the analysis was created\. Start a new analysis to analyse the remaining responses\.")


def path(form, rid):
    return f"{ADM02}/forms/{form['id'] if isinstance(form, dict) else form}/responses/{rid}"


def delete(admin, form, rid):
    return call("DELETE", path(form, rid), admin)


def respondents(admin, n=3, state_closed=False):
    users = [actor("student") for _ in range(n)]
    form = published(admin, users, payload())
    rids = []
    for u in users:
        r = submit(u, form, answers(form))
        assert r.status_code == 201, r.text
        rids.append(r.json()["id"])
    return form, users, rids


def snapshot(form_id):
    return (sql("SELECT id::text FROM feedback_responses WHERE form_id=%s ORDER BY id", (form_id,)),
            sql("SELECT user_id, read_at::text FROM feedback_recipients WHERE form_id=%s ORDER BY user_id", (form_id,)),
            sql("SELECT to_jsonb(f)::text FROM feedback_forms f WHERE id=%s", (form_id,)),
            sql("SELECT count(*) FROM admin_messages")[0][0], sql("SELECT count(*) FROM ai_service_attempts")[0][0])


def test_adm03_ac39_delete_rejects_anonymous_non_admin_and_disabled_before_any_change(admin):
    form, users, rids = respondents(admin, 1)
    disabled = actor("admin")
    sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(disabled),))
    for who, codes in ((None, (401,)), (actor("student"), (403,)), (actor("teacher"), (403,)), (disabled, (401, 403))):
        r = delete(who, form, rids[0])
        assert r.status_code in codes, (who, r.status_code, r.text)
    assert sql("SELECT count(*) FROM feedback_responses WHERE id=%s", (rids[0],))[0][0] == 1


def test_adm03_ac40_44_owner_delete_is_204_hard_delete_and_respondent_can_resubmit_while_open(admin):
    form, users, rids = respondents(admin, 2)
    assert inbox(users[0], form)["response_status"] == "completed"
    r = delete(admin, form, rids[0])
    assert r.status_code == 204 and r.content == b""
    assert sql("SELECT count(*) FROM feedback_responses WHERE id=%s", (rids[0],))[0][0] == 0
    assert call("GET", path(form, rids[0]), admin).status_code == 404
    assert rids[0] not in [i["id"] for i in call("GET", f"{ADM02}/forms/{form['id']}/responses", admin).json()["items"]]
    assert inbox(users[0], form)["response_status"] == "not_started"
    assert inbox(users[1], form)["response_status"] == "completed"
    again = submit(users[0], form, answers(form))
    assert again.status_code == 201, again.text
    assert again.json()["id"] != rids[0] and inbox(users[0], form)["response_status"] == "completed"


def test_adm03_ac44_closed_form_stays_closed_after_delete(admin):
    form, users, rids = respondents(admin, 1)
    assert close(admin, form).status_code == 200
    assert delete(admin, form, rids[0]).status_code == 204
    assert inbox(users[0], form)["response_status"] == "closed"
    error(submit(users[0], form, answers(form)), 409, "feedback_closed")
    assert sql("SELECT count(*) FROM feedback_responses WHERE form_id=%s", (form["id"],))[0][0] == 0


def test_adm03_ac40_unknown_malformed_other_form_and_repeated_ids_give_one_uniform_404(admin):
    form, users, rids = respondents(admin, 1)
    other, _, other_rids = respondents(admin, 1)
    replies = [delete(admin, form, uid()), delete(admin, form, "not-a-uuid"), delete(admin, uid(), rids[0]),
               delete(admin, form, other_rids[0])]
    for r in replies:
        expect(r, 404, "feedback_response_not_found", NOT_FOUND)
    assert len({r.text for r in replies}) == 1
    assert sql("SELECT count(*) FROM feedback_responses WHERE id=%s", (other_rids[0],))[0][0] == 1  # intact
    assert delete(admin, form, rids[0]).status_code == 204
    expect(delete(admin, form, rids[0]), 404, "feedback_response_not_found", NOT_FOUND)  # second delete


def test_adm03_ac42_two_simultaneous_deletes_give_one_204_and_one_404(admin):
    form, users, rids = respondents(admin, 1)
    replies = race(lambda: delete(admin, form, rids[0]), lambda: delete(admin, form, rids[0]))
    assert sorted(r.status_code for r in replies) == [204, 404], [r.text for r in replies]


@pytest.mark.parametrize("round_", range(6))
def test_adm03_ac43_delete_racing_submit_and_draft_save_never_5xx_and_state_matches_the_row(admin, round_):
    form, users, rids = respondents(admin, 1)
    user = users[0]
    replies = race(lambda: delete(admin, form, rids[0]), lambda: submit(user, form, answers(form)),
                   lambda: save(user, form, answers(form)))
    assert all(r.status_code < 500 for r in replies), [(r.status_code, r.text) for r in replies]
    rows = sql("SELECT count(*) FROM feedback_responses WHERE form_id=%s AND user_id=%s", (form["id"], str(user)))[0][0]
    assert rows <= 1
    assert (inbox(user, form)["response_status"] == "completed") == (rows == 1)


def test_adm03_ac41_delete_changes_nothing_except_the_row(admin):
    form, users, rids = respondents(admin, 3)
    before = snapshot(form["id"])
    assert delete(admin, form, rids[0]).status_code == 204
    after = snapshot(form["id"])
    assert after[0] == [r for r in before[0] if r[0] != rids[0]]
    assert after[1:] == before[1:]  # recipients (incl. inbox read state), form, messages, usage counters


def test_adm03_ac45_50_stored_analysis_is_unchanged_and_readable_after_a_cited_response_is_deleted(admin, llm):
    form, users, rids = respondents(admin, 3)
    done = run(admin, form, rids)
    before = sql("SELECT to_jsonb(a)::text FROM feedback_analyses a WHERE id=%s", (done["id"],))
    cited = call("GET", f"{BASE}/{done['id']}/responses/R1", admin).json()["response"]["id"]
    sql("UPDATE feedback_analyses SET created_at = created_at - interval '400 days' WHERE id=%s", (done["id"],))
    before = sql("SELECT to_jsonb(a)::text FROM feedback_analyses a WHERE id=%s", (done["id"],))
    assert delete(admin, form, cited).status_code == 204
    assert sql("SELECT to_jsonb(a)::text FROM feedback_analyses a WHERE id=%s", (done["id"],)) == before
    again = get(admin, done["id"]).json()
    assert again == done and again["response_count"] == 3 and again["ai"]["status"] == "complete"
    expect(call("GET", f"{BASE}/{done['id']}/responses/R1", admin), 404, "evidence_not_found", MSG["evidence_not_found"])
    for label in ("R2", "R3"):
        assert call("GET", f"{BASE}/{done['id']}/responses/{label}", admin).status_code == 200
    assert [i["id"] for i in listing(admin)["items"]] == [done["id"]]  # never expired or pruned


def test_adm03_ac46_running_analysis_fails_with_ai_responses_deleted_and_keeps_its_statistics(admin, llm):
    form, ids = text_form(admin, 65)  # 3 batches
    fut, aid = start_blocked(admin, llm, form, ids)
    stats = get(admin, aid).json()["aggregates"]
    victim = ids[40]
    assert delete(admin, form, victim).status_code == 204
    release(llm, fut)
    done = wait_done(admin, aid)
    err = done["ai"]["error"]
    assert done["ai"]["status"] == "failed" and err["code"] == "ai_responses_deleted", err
    m = AI_DELETED.fullmatch(err["message"])
    assert m and (m.group(2), m.group(3)) == ("1", "65"), err["message"]
    assert err["details"]["missing"] == 1 and err["details"]["selected"] == 65
    assert done["ai"]["result"] is None and done["aggregates"] == stats and done["response_count"] == 65
    assert len(llm.calls) < 4  # the job stopped before the reduce call


def test_adm03_ac46_deleting_after_completion_changes_nothing(admin, llm):
    form, ids = text_form(admin, 4)
    done = run(admin, form, ids)
    assert delete(admin, form, ids[0]).status_code == 204
    assert get(admin, done["id"]).json() == done


def test_adm03_ac47_response_count_and_select_all_count_live_responses(admin, llm):
    form, ids = text_form(admin, 5)
    assert delete(admin, form, ids[0]).status_code == 204
    count = call("GET", f"{ADM02}/forms/{form['id']}/response-count", admin)
    assert count.json() == {"form_id": form["id"], "count": 4}
    fresh = create(admin, form, select_all=True, expected=4)
    assert fresh.status_code == 201 and fresh.json()["response_count"] == 4
    wait_done(admin, fresh.json()["id"])
    expect(create(admin, form, ids[:2]), 404, "response_not_found")  # an explicit deleted id is still refused


def test_adm03_ac49_registry_has_the_new_codes_without_generic_wording():
    from feedback_analysis import failures
    assert {"feedback_response_not_found", "ai_responses_deleted"} <= set(failures.MESSAGES)
    assert failures.render("feedback_response_not_found") == NOT_FOUND
    text = failures.render("ai_responses_deleted", step="processing batch 2 of 3", k=1, n=65)
    assert AI_DELETED.fullmatch(text)
    for code in ("feedback_response_not_found", "ai_responses_deleted"):
        low = failures.MESSAGES[code].lower()
        assert not any(w in low for w in ("something went wrong", "an error occurred", "unknown error", "try again later"))
