"""ADM-03 AC32-AC37: owner-only hard delete, 409 while running, no side effects, delete versus job races."""
import re
import time

from auth_helpers import call, sql
from adm02_helpers import race, uid
from adm03_fixtures import admin, llm, other_admin  # noqa: F401
from adm03_helpers import (BASE, MSG, create, expect, get, listing, release, row_count, run, start_blocked,
                           table_counts, text_form, wait_done)

RUNNING = re.compile(r"This analysis cannot be deleted yet: its AI step has been running for (\d+) seconds\. "
                     r"It finishes or is marked interrupted within (\d+) seconds \(the limit is 420 seconds\)\. Delete it after that\.")


def delete(user, aid):
    return call("DELETE", f"{BASE}/{aid}", user)


def test_adm03_ac32_owner_delete_returns_204_and_removes_everything(admin, llm):
    form, ids = text_form(admin, 4)
    done = run(admin, form, ids)
    before = sql("SELECT aggregates IS NOT NULL, ai_result IS NOT NULL, label_map IS NOT NULL FROM feedback_analyses WHERE id=%s", (done["id"],))
    assert before == [(True, True, True)]
    r = delete(admin, done["id"])
    assert r.status_code == 204 and r.content == b""
    assert row_count(done["id"]) == 0
    expect(get(admin, done["id"]), 404, "analysis_not_found", MSG["analysis_not_found"])
    for item in done["labels"]:
        expect(call("GET", f"{BASE}/{done['id']}/responses/{item['label']}", admin), 404, "evidence_not_found", MSG["evidence_not_found"])
    assert listing(admin)["items"] == []
    expect(delete(admin, done["id"]), 404, "analysis_not_found", MSG["analysis_not_found"])  # second delete


def test_adm03_ac32_a_failed_analysis_can_be_deleted_too(admin, llm):
    form, ids = text_form(admin, 2)
    llm.script = {1: "nonsense"}
    failed = run(admin, form, ids)
    assert failed["ai"]["status"] == "failed"
    assert delete(admin, failed["id"]).status_code == 204 and row_count(failed["id"]) == 0


def test_adm03_ac33_34_other_admin_unknown_and_malformed_ids_are_identical_404s(admin, other_admin, llm):
    form, ids = text_form(admin, 2)
    done = run(admin, form, ids)
    bodies = [delete(other_admin, done["id"]), delete(admin, uid()), delete(admin, "not-a-uuid"), delete(admin, "123")]
    for r in bodies:
        expect(r, 404, "analysis_not_found", MSG["analysis_not_found"])
    assert len({r.text for r in bodies}) == 1
    assert row_count(done["id"]) == 1 and get(admin, done["id"]).json() == done
    gone = run(admin, form, ids)["id"]
    assert delete(admin, gone).status_code == 204
    assert delete(admin, gone).text == bodies[0].text  # already deleted is indistinguishable


def test_adm03_ac35_running_analysis_is_refused_with_409_then_deletable_when_finished(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    r = delete(admin, aid)
    d = expect(r, 409, "analysis_running")
    m = RUNNING.fullmatch(d["message"])
    assert m, d["message"]
    s, rem = int(m.group(1)), int(m.group(2))
    assert d["ran_seconds"] == s and d["remaining_seconds"] == rem == max(0, 420 - s) and s < 60
    assert row_count(aid) == 1 and get(admin, aid).json()["ai"]["status"] == "running"
    release(llm, fut)
    wait_done(admin, aid)
    assert delete(admin, aid).status_code == 204 and row_count(aid) == 0


def test_adm03_ac35_a_running_row_older_than_420_s_is_swept_to_interrupted_then_deletable(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    sql("UPDATE feedback_analyses SET created_at = now() - interval '500 seconds' WHERE id=%s", (aid,))
    assert delete(admin, aid).status_code == 204
    assert row_count(aid) == 0
    release(llm, fut)


def test_adm03_ac36_delete_leaves_responses_forms_and_usage_counters_unchanged(admin, llm):
    form, ids = text_form(admin, 4)
    done = run(admin, form, ids)
    state = lambda: (table_counts(), sql("SELECT count(*) FROM ai_service_attempts")[0][0],
                     sql("SELECT answers::text, form_snapshot::text FROM feedback_responses WHERE form_id=%s ORDER BY id", (form["id"],)),
                     sql("SELECT questions::text, version FROM feedback_forms WHERE id=%s", (form["id"],)))
    before = state()
    assert delete(admin, done["id"]).status_code == 204
    after = state()
    assert after[1:] == before[1:] and after[0][0] == before[0][0] and after[0][1] == before[0][1]


def test_adm03_ac37_late_job_write_after_delete_changes_nothing(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    sql("UPDATE feedback_analyses SET created_at = now() - interval '500 seconds' WHERE id=%s", (aid,))
    assert get(admin, aid).json()["ai"]["error"]["code"] == "analysis_interrupted"
    assert delete(admin, aid).status_code == 204
    posted = release(llm, fut)  # the job now finishes every remaining call and tries to write
    assert posted.status_code == 201
    time.sleep(1.0)
    assert row_count(aid) == 0 and listing(admin)["items"] == []
    expect(get(admin, aid), 404, "analysis_not_found")
    assert len(llm.calls) >= 1


def test_adm03_ac37_two_simultaneous_deletes_give_one_204_and_one_404(admin, llm):
    form, ids = text_form(admin, 2)
    done = run(admin, form, ids)
    replies = race(lambda: delete(admin, done["id"]), lambda: delete(admin, done["id"]))
    assert sorted(r.status_code for r in replies) == [204, 404]
    assert row_count(done["id"]) == 0


def test_adm03_ac37_delete_racing_the_finishing_job_never_errors_or_resurrects(admin, llm):
    form, ids = text_form(admin, 2)
    for _ in range(3):
        r = create(admin, form, ids)
        aid = r.json()["id"]
        outcomes = race(lambda: delete(admin, aid), lambda: delete(admin, aid), lambda: get(admin, aid))
        assert all(o.status_code in (200, 204, 404, 409) for o in outcomes), [o.text for o in outcomes]
        wait_end = time.monotonic() + 20
        while time.monotonic() < wait_end and sql("SELECT ai_status FROM feedback_analyses WHERE id=%s", (aid,)) == [("running",)]:
            time.sleep(0.05)
        if row_count(aid):
            assert delete(admin, aid).status_code == 204
        time.sleep(0.2)
        assert row_count(aid) == 0
