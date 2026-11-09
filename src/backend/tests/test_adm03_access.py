"""ADM-03 AC8-AC13, AC33, AC34: evidence, authorisation, cross-admin isolation (task 10)."""
import pytest

from auth_helpers import call, new_student, sql
from adm02_helpers import actor, uid
from adm03_fixtures import admin, llm, other_admin  # noqa: F401
from adm03_helpers import BASE, MSG, create, expect, get, listing, release, row_count, run, start_blocked, text_form, wait_done

ADM02 = "/api/admin/feedback"
FORMS = ADM02 + "/forms"


@pytest.fixture
def owned(admin, llm):
    form, ids = text_form(admin, 5)
    done = run(admin, form, ids[:4])
    return form, ids, done


def endpoints(aid, form):
    return [("POST", BASE, {"form_id": form["id"], "request_id": uid(), "response_ids": [uid()]}),
            ("GET", BASE, None), ("GET", f"{BASE}/{aid}", None), ("DELETE", f"{BASE}/{aid}", None),
            ("GET", f"{BASE}/{aid}/responses/R1", None),
            ("GET", f"{FORMS}/{form['id']}/response-count", None)]


def callers():
    disabled = actor("admin")
    sql('UPDATE "user" SET access_status=\'disabled\' WHERE id=%s', (str(disabled),))
    return [("anonymous", None, (401,)), ("student", new_student("adm03"), (403,)), ("teacher", actor("teacher"), (403,)),
            ("disabled_admin", disabled, (401, 403))]


def test_adm03_ac12_33_every_endpoint_rejects_unauthenticated_non_admin_and_disabled_before_any_work(owned, admin, llm):
    form, ids, done = owned
    calls_before, rows_before = len(llm.calls), sql("SELECT count(*) FROM feedback_analyses")[0][0]
    for who, user, statuses in callers():
        for method, path, body in endpoints(done["id"], form):
            r = call(method, path, user, body)
            assert r.status_code in statuses, (who, method, path, r.status_code, r.text)
            assert not any(k in r.text for k in ("aggregates", "form_snapshot", "label", "R1"))
    assert len(llm.calls) == calls_before
    assert sql("SELECT count(*) FROM feedback_analyses")[0][0] == rows_before and row_count(done["id"]) == 1
    assert get(admin, done["id"]).status_code == 200


def test_adm03_ac13_34_other_admin_cannot_read_open_list_or_delete(owned, admin, other_admin, llm):
    form, ids, done = owned
    aid = done["id"]
    expect(get(other_admin, aid), 404, "analysis_not_found", MSG["analysis_not_found"])
    expect(call("GET", f"{BASE}/{aid}/responses/R1", other_admin), 404, "evidence_not_found", MSG["evidence_not_found"])
    expect(call("DELETE", f"{BASE}/{aid}", other_admin), 404, "analysis_not_found", MSG["analysis_not_found"])
    assert listing(other_admin)["items"] == [] and [i["id"] for i in listing(admin)["items"]] == [aid]
    assert get(admin, aid).json() == done and row_count(aid) == 1


def test_adm03_ac13_other_admin_cannot_reuse_a_request_id_to_reach_the_analysis(owned, admin, other_admin, llm):
    form, ids, done = owned
    first = create(admin, form, ids[:1], request_id=uid())
    rid = sql("SELECT request_id FROM feedback_analyses WHERE id=%s", (first.json()["id"],))[0][0]
    r = create(other_admin, form, ids[:1], request_id=str(rid))
    assert r.status_code == 201 and r.json()["id"] != first.json()["id"]


def test_adm03_ac8_evidence_is_exactly_the_response_behind_the_label(admin, llm):
    form, ids = text_form(admin, 6)
    done = run(admin, form, ids[:5])
    seen = {}
    for item in done["labels"]:
        r = call("GET", f"{BASE}/{done['id']}/responses/{item['label']}", admin)
        assert r.status_code == 200, r.text
        v = r.json()
        assert set(v) == {"label", "response"} and v["label"] == item["label"]
        direct = call("GET", f"{FORMS}/{form['id']}/responses/{v['response']['id']}", admin)
        assert v["response"] == direct.json()  # the exact body of the ADM-02-04 endpoint
        seen[item["label"]] = v["response"]["id"]
    assert sorted(seen.values()) == sorted(ids[:5]) and ids[5] not in seen.values()
    # the label shown to the model is the label opened by the admin
    for labels, _, text in [e for c in llm.of("map") for e in c.entries()]:
        resp = call("GET", f"{BASE}/{done['id']}/responses/{labels[0]}", admin).json()["response"]
        assert text.strip() in str(resp["answers"])


def test_adm03_ac8_ac9_normalised_labels_and_uniform_404_for_every_invalid_reference(owned, admin, other_admin):
    form, ids, done = owned
    aid = done["id"]
    ok = call("GET", f"{BASE}/{aid}/responses/R1", admin).json()
    assert call("GET", f"{BASE}/{aid}/responses/r1%20", admin).json() == ok
    cited = call("GET", f"{BASE}/{aid}/responses/R2", admin).json()["response"]["id"]
    sql("DELETE FROM feedback_responses WHERE id=%s", (cited,))  # cited response deleted later
    bodies = []
    for label in ("R2", "R5", "R0", "R501", "R01", "R", "x1", "R1.5", "R-1", ids[0]):
        r = call("GET", f"{BASE}/{aid}/responses/{label}", admin)
        bodies.append(expect(r, 404, "evidence_not_found", MSG["evidence_not_found"]))
    assert all(b == bodies[0] for b in bodies)
    foreign = call("GET", f"{BASE}/{aid}/responses/R1", other_admin)
    assert foreign.json() == call("GET", f"{BASE}/{aid}/responses/R2", admin).json()
    assert get(admin, aid).status_code == 200  # the analysis itself stays
    assert get(admin, aid).json()["labels"] == done["labels"]


def test_adm03_ac9_form_deleted_gives_evidence_not_found_without_content(owned, admin):
    form, ids, done = owned
    sql("DELETE FROM feedback_responses WHERE form_id=%s", (form["id"],))
    r = call("GET", f"{BASE}/{done['id']}/responses/R1", admin)
    expect(r, 404, "evidence_not_found", MSG["evidence_not_found"])
    assert "unique feedback" not in r.text


def test_adm03_ac8_evidence_works_while_the_ai_step_runs_and_after_it_failed(admin, llm):
    form, ids = text_form(admin, 3)
    fut, aid = start_blocked(admin, llm, form, ids)
    assert call("GET", f"{BASE}/{aid}/responses/R2", admin).status_code == 200
    release(llm, fut)
    wait_done(admin, aid)
    llm.gate = None
    llm.script = {len(llm.calls) + 1: "nonsense"}
    failed = run(admin, form, ids)
    assert failed["ai"]["status"] == "failed"
    assert call("GET", f"{BASE}/{failed['id']}/responses/R3", admin).status_code == 200


def test_adm03_ac10_evidence_never_accepts_a_response_id_or_browses_the_form(owned, admin):
    form, ids, done = owned
    expect(call("GET", f"{BASE}/{done['id']}/responses/{ids[0]}", admin), 404, "evidence_not_found")
    r = call("GET", f"{BASE}/{done['id']}/responses", admin)
    assert r.status_code in (404, 405)


def test_adm03_ac11_opening_evidence_changes_nothing(owned, admin, llm):
    form, ids, done = owned
    before = (get(admin, done["id"]).json(), sql("SELECT count(*) FROM admin_messages")[0][0],
              sql("SELECT count(*) FROM feedback_analyses")[0][0], len(llm.calls))
    for label in ("R1", "R2", "R9"):
        call("GET", f"{BASE}/{done['id']}/responses/{label}", admin)
    after = (get(admin, done["id"]).json(), sql("SELECT count(*) FROM admin_messages")[0][0],
             sql("SELECT count(*) FROM feedback_analyses")[0][0], len(llm.calls))
    assert before == after


def test_adm03_ac1_a_response_of_a_form_the_admin_names_but_another_form_holds_is_refused(admin, other_admin, llm):
    form, ids = text_form(admin, 2)
    other_form, other_ids = text_form(other_admin, 2)
    r = create(admin, form, other_ids)
    expect(r, 404, "response_not_found")
    assert not llm.calls
