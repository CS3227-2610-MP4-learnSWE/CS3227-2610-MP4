"""ADM-03 selection, request validation, AI success path, history, response-count (AC1-5, 7, 17, 18, 27, 30)."""
import re

import pytest

from auth_helpers import call, sql
from adm02_helpers import created, payload, uid
from adm03_fixtures import admin, llm, other_admin  # noqa: F401
from adm03_helpers import (BASE, MSG, ans, body_for, create, expect, get, listing, qdef, run, seed, table_counts,
                           text_form, text_rows, wait_done)

REASON = "The analysis request is malformed: {}."


def test_adm03_ac1_explicit_selection_uses_only_selected_responses(admin, llm):
    form, ids = text_form(admin, 5)
    done = run(admin, form, ids[:2])
    assert done["response_count"] == 2 and done["mode"] == "explicit"
    assert [x["label"] for x in done["labels"]] == ["R1", "R2"]
    prompts = "\n".join(c.user_text for c in llm.of("map"))
    assert "number 0 " in prompts and "number 1 " in prompts and "number 2 " not in prompts
    assert "number 3 " not in prompts and "number 4 " not in prompts


def test_adm03_ac17_duplicate_ids_are_deduplicated_and_ids_normalised(admin, llm):
    form, ids = text_form(admin, 3)
    r = create(admin, form, [ids[0], ids[0].upper(), f"  {ids[1]}  ", ids[0]])
    assert r.status_code == 201, r.text
    assert r.json()["response_count"] == 2


def test_adm03_ac17_exactly_500_accepted_501_rejected_with_n_and_no_llm_call(admin, llm):
    form, ids = text_form(admin, 500)
    r = create(admin, form, ids)
    assert r.status_code == 201, r.text
    wait_done(admin, r.json()["id"])
    llm.calls.clear()
    d = expect(create(admin, form, ids + [uid()]), 422, "too_many_responses",
               "You selected 501 responses, but one analysis can cover at most 500. Select fewer responses.")
    assert d["code"] == "too_many_responses" and not llm.calls


def test_adm03_ac5_ac17_empty_selection_has_exact_message_no_row_no_llm(admin, llm):
    before = listing(admin)["items"]
    expect(create(admin, uid(), []), 422, "selection_required", MSG["selection_required"])
    assert listing(admin)["items"] == before and not llm.calls


def test_adm03_ac17_unknown_form_and_other_forms_responses(admin, llm):
    form, ids = text_form(admin, 2)
    other_form, other_ids = text_form(admin, 2)
    expect(create(admin, uid(), ids), 404, "form_not_found", MSG["form_not_found"])
    expect(create(admin, form, [ids[0], other_ids[0], uid()]), 404, "response_not_found",
           "2 of the 3 selected responses are not available for this form (they may have been deleted or belong to another form). Reload the list and select again.")
    assert not llm.calls


def test_adm03_ac18_select_all_snapshot_spans_pages_and_reports_exact_count(admin, llm):
    form, ids = text_form(admin, 130)  # more than one ADM-02 page of 100
    r = create(admin, form, select_all=True, expected=130)
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["mode"] == "select_all" and v["response_count"] == 130 and v["expected_count"] == 130
    assert len(v["labels"]) == 130
    count = call("GET", f"/api/admin/feedback/forms/{form['id']}/response-count", admin)
    assert count.status_code == 200 and count.json() == {"form_id": form["id"], "count": 130}
    wait_done(admin, v["id"])
    seed(admin, None, text_rows(form, 3, start=900), form=form)  # added after creation
    again = get(admin, v["id"]).json()
    assert again["response_count"] == 130 and len(again["labels"]) == 130


def test_adm03_ac18_expected_count_may_differ_from_the_snapshot_and_is_reported(admin, llm):
    form, ids = text_form(admin, 4)
    v = create(admin, form, select_all=True, expected=3).json()
    assert v["response_count"] == 4 and v["expected_count"] == 3


def test_adm03_ac18_empty_form_select_all_is_no_responses(admin, llm):
    form = created(admin, payload())
    expect(create(admin, form, select_all=True), 422, "no_responses", MSG["no_responses"])


def test_adm03_ac17_form_with_only_empty_answers_is_nothing_to_analyse(admin, llm):
    q = qdef("short_answer", "Text")
    form = created(admin, payload([q]))
    q = form["questions"][0]
    form, ids = seed(admin, None, [{"answers": [ans(q, None)]}, {"answers": []}], form=form)
    expect(create(admin, form, ids), 422, "nothing_to_analyse",
           "The 2 selected responses contain no answered questions, so there is nothing to analyse.")
    assert not llm.calls and listing(admin)["items"] == []


@pytest.mark.parametrize("extra,reason", [
    ({"select_all": True}, "send either response_ids or select_all, not both"),
    ({"select_all": False}, "select_all must be true"),
    ({"surprise": 1}, "unknown field surprise"),
    ({"expected_count": 3}, "expected_count is only allowed with select_all"),
])
def test_adm03_ac18_invalid_shapes_with_explicit_ids(admin, llm, extra, reason):
    form, ids = text_form(admin, 2)
    b = body_for(form, ids)
    b.update(extra)
    expect(call("POST", BASE, admin, b), 422, "invalid_request", REASON.format(reason))
    assert not llm.calls


@pytest.mark.parametrize("mutate,reason", [
    (lambda b: b.update(form_id="nope"), "form_id is not a valid id"),
    (lambda b: b.update(request_id="nope"), "request_id is not a valid id"),
    (lambda b: b.update(response_ids="x"), "response_ids must be a list of ids"),
    (lambda b: b.update(response_ids=["nope"]), "response_ids contains a value that is not a valid id"),
    (lambda b: b.pop("response_ids"), "send response_ids or select_all set to true"),
    (lambda b: (b.pop("response_ids"), b.update(select_all=True, expected_count=501)), "expected_count must be a whole number from 0 to 500"),
    (lambda b: (b.pop("response_ids"), b.update(select_all=True, expected_count="3")), "expected_count must be a whole number from 0 to 500"),
])
def test_adm03_ac17_invalid_request_reasons(admin, llm, mutate, reason):
    form, ids = text_form(admin, 2)
    b = body_for(form, ids)
    mutate(b)
    expect(call("POST", BASE, admin, b), 422, "invalid_request", REASON.format(reason))


def test_adm03_ac2_3_4_result_sections_and_evidence_labels(admin, llm):
    form, ids = text_form(admin, 5)
    done = run(admin, form, ids)
    ai = done["ai"]
    assert ai["status"] == "complete" and ai["error"] is None and ai["completed_at"]
    res = ai["result"]
    assert set(res) == {"summary", "themes", "suggestions"} and res["summary"]
    allowed = {x["label"] for x in done["labels"]}
    assert res["themes"] and all(t["evidence"] and set(t["evidence"]) <= allowed for t in res["themes"])
    bases = {s["basis"] for s in res["suggestions"]}
    assert bases == {"feedback", "ai"}
    for s in res["suggestions"]:
        assert (s["basis"] == "feedback") == bool(s["evidence"]) and set(s["evidence"]) <= allowed
    assert ai["progress"]["done"] == ai["progress"]["total"] and ai["progress"]["step"] is None
    assert done["free_text"] == {"total": 5, "used": 5}
    # response ids and the label map never leave the server
    text = str(done)
    assert not any(i in text for i in ids) and "label_map" not in text


def test_adm03_ac23_progress_totals_are_map_calls_plus_one(admin, llm):
    form, ids = text_form(admin, 65)  # at most 30 entries per batch: 3 map calls
    r = create(admin, form, ids)
    assert r.status_code == 201
    assert r.json()["ai"]["progress"]["total"] == 4
    done = wait_done(admin, r.json()["id"])
    assert len(llm.of("map")) == 3 and len(llm.of("reduce")) == 1
    assert llm.calls[-1].kind == "reduce"  # map calls first, reduce last, sequential
    assert done["ai"]["progress"]["done"] == 4


def test_adm03_ac2_form_without_free_text_makes_only_a_reduce_call(admin, llm):
    q = qdef("multiple_choice", "Pick")
    form = created(admin, payload([q]))
    q = form["questions"][0]
    form, ids = seed(admin, None, [{"answers": [ans(q, q["options"][0]["id"])]}], form=form)
    r = create(admin, form, ids)
    assert r.json()["ai"]["progress"]["total"] == 1
    done = wait_done(admin, r.json()["id"])
    assert [c.kind for c in llm.calls] == ["reduce"] and done["ai"]["status"] == "complete"
    assert done["free_text"] == {"total": 0, "used": 0}


def test_adm03_ac7_analysis_does_not_change_forms_responses_or_messages(admin, llm):
    form, ids = text_form(admin, 4)
    before = table_counts()
    msgs = sql("SELECT count(*) FROM admin_messages")[0][0]
    snap = sql("SELECT answers::text, form_snapshot::text FROM feedback_responses WHERE form_id=%s ORDER BY id", (form["id"],))
    run(admin, form, ids)
    call("GET", f"{BASE}/{listing(admin)['items'][0]['id']}/responses/R1", admin)
    assert table_counts() == before and sql("SELECT count(*) FROM admin_messages")[0][0] == msgs
    assert sql("SELECT answers::text, form_snapshot::text FROM feedback_responses WHERE form_id=%s ORDER BY id", (form["id"],)) == snap


def test_adm03_ac27_response_count_exact_zero_and_not_found(admin, llm):
    form, _ = text_form(admin, 101)
    empty = created(admin, payload())
    ok = call("GET", f"/api/admin/feedback/forms/{form['id']}/response-count", admin)
    assert ok.status_code == 200 and ok.json() == {"form_id": form["id"], "count": 101}
    assert call("GET", f"/api/admin/feedback/forms/{empty['id']}/response-count", admin).json()["count"] == 0
    for bad in (uid(), "not-a-uuid"):
        expect(call("GET", f"/api/admin/feedback/forms/{bad}/response-count", admin), 404, "form_not_found", MSG["form_not_found"])


def test_adm03_ac30_history_is_permanent_newest_first_and_paginated(admin, other_admin, llm):
    form, ids = text_form(admin, 2)
    made = [create(admin, form, ids[:1]).json()["id"] for _ in range(1)]
    wait_done(admin, made[0])
    for _ in range(24):
        r = create(admin, form, ids)
        assert r.status_code == 201, r.text
        made.append(r.json()["id"])
        wait_done(admin, r.json()["id"])
    first = listing(admin)
    assert len(first["items"]) == 20 and first["next_offset"] == 20
    assert [i["id"] for i in first["items"]] == list(reversed(made))[:20]
    assert set(first["items"][0]) == {"id", "form_id", "form_title", "created_at", "response_count", "ai_status"}
    second = listing(admin, "?limit=20&offset=20")
    assert len(second["items"]) == 5 and second["next_offset"] is None
    assert len(listing(admin, "?limit=50")["items"]) == 25
    assert listing(other_admin)["items"] == []
    sql("UPDATE feedback_analyses SET created_at = created_at - interval '400 days' WHERE admin_id=%s", (str(admin),))
    assert len(listing(admin, "?limit=50")["items"]) == 25  # nothing is pruned
    for q in ("?limit=0", "?limit=51", "?limit=x", "?offset=-1", "?offset=100001", "?offset=x"):
        r = call("GET", BASE + q, admin)
        reason = ("limit must be a whole number from 1 to 50" if "limit" in q
                  else "offset must be a whole number from 0 to 100000")
        expect(r, 422, "invalid_request", REASON.format(reason))


def test_adm03_ac30_equal_timestamps_keep_a_stable_order(admin, llm):
    form, ids = text_form(admin, 1)
    made = [run(admin, form, ids)["id"] for _ in range(4)]
    sql("UPDATE feedback_analyses SET created_at='2031-01-01T00:00:00Z' WHERE admin_id=%s", (str(admin),))
    a = [i["id"] for i in listing(admin)["items"]]
    assert a == sorted(made, reverse=True) and a == [i["id"] for i in listing(admin)["items"]]
    page = [i["id"] for i in listing(admin, "?limit=2")["items"]] + [i["id"] for i in listing(admin, "?limit=2&offset=2")["items"]]
    assert page == a


def test_adm03_ac30_row_stores_statistics_result_snapshot_and_mapping(admin, llm):
    form, ids = text_form(admin, 3)
    done = run(admin, form, ids)
    r = sql("SELECT response_count, label_map::text, aggregates::text, ai_result::text FROM feedback_analyses WHERE id=%s", (done["id"],))[0]
    assert r[0] == 3 and all(i in r[1] for i in ids) and r[2] and r[3]
    assert sql("SELECT 1 FROM information_schema.columns WHERE table_name='feedback_analyses' AND column_name='deleted_at'") == []


def test_adm03_ac30_single_alembic_head():
    import subprocess, sys, os
    from pathlib import Path
    out = subprocess.run([sys.executable, "-m", "alembic", "heads"], cwd=Path(__file__).resolve().parents[1],
                         env=os.environ, capture_output=True, text=True, check=True).stdout
    assert len(re.findall(r"\(head\)", out)) == 1
    assert sql("SELECT 1 FROM information_schema.tables WHERE table_name='feedback_analyses'") != []
