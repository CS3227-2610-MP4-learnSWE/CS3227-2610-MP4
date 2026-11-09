"""ADM-03 AC20, AC24 (server side), AC28: statistics computed in the create request, independent of the AI."""
import time
from datetime import timedelta

import pytest

import llm_client
from adm03_fixtures import admin, llm  # noqa: F401
from adm03_helpers import (T0, ans, create, get, qdef, release, run, seed, start_blocked, text_form, uid,
                           wait_done)
from adm02_helpers import created, payload


def by_prompt(aggs):
    return {a["prompt"]: a for a in aggs}


def pct(x):
    return pytest.approx(x, abs=0.06)


def test_adm03_ac20_aggregates_every_kind_in_the_create_response(admin, llm):
    mc, dd, cb = qdef("multiple_choice", "MC q", ("A", "B")), qdef("dropdown", "DD q", ("P", "Q")), qdef("checkbox", "CB q", ("X", "Y", "Z"))
    sc, tx = qdef("linear_scale", "Scale q", scale=(1, 5)), qdef("short_answer", "Text q")
    form = created(admin, payload([mc, dd, cb, sc, tx]))
    mc, dd, cb, sc, tx = form["questions"]
    A, B = [o["id"] for o in mc["options"]]
    X, Y, Z = [o["id"] for o in cb["options"]]
    rows = [
        {"answers": [ans(mc, A), ans(dd, dd["options"][0]["id"]), ans(cb, [X, Y]), ans(sc, 4), ans(tx, "t1")]},
        {"answers": [ans(mc, A), ans(dd, dd["options"][1]["id"]), ans(cb, [Y]), ans(sc, 5), ans(tx, "t2")]},
        {"answers": [ans(mc, B), ans(dd, None), ans(cb, None), ans(sc, None)]},  # text absent: skipped
        {"answers": [ans(mc, None), ans(cb, [X]), ans(sc, 3), ans(tx, "t1")]},  # dd absent: skipped
    ]
    form, ids = seed(admin, None, rows, form=form)
    r = create(admin, form, ids)
    assert r.status_code == 201, r.text
    a = by_prompt(r.json()["aggregates"])
    assert [x["prompt"] for x in r.json()["aggregates"]] == ["MC q", "DD q", "CB q", "Scale q", "Text q"]
    m = a["MC q"]
    assert (m["kind"], m["answered"], m["skipped"]) == ("single", 3, 1)
    assert {o["label"]: (o["count"], o["option_id"]) for o in m["options"]} == {"A": (2, A), "B": (1, B)}
    assert {o["label"]: o["percent"] for o in m["options"]} == {"A": pct(66.7), "B": pct(33.3)}
    d = a["DD q"]
    assert (d["answered"], d["skipped"]) == (2, 2)
    assert [o["count"] for o in d["options"]] == [1, 1] and [o["percent"] for o in d["options"]] == [pct(50.0)] * 2
    c = a["CB q"]
    assert (c["kind"], c["answered"], c["skipped"]) == ("multi", 3, 1)
    assert {o["label"]: o["count"] for o in c["options"]} == {"X": 2, "Y": 2, "Z": 0}
    assert {o["label"]: o["percent"] for o in c["options"]} == {"X": pct(66.7), "Y": pct(66.7), "Z": pct(0.0)}
    s = a["Scale q"]
    assert (s["kind"], s["answered"], s["skipped"], s["min"], s["max"]) == ("scale", 3, 1, 1, 5)
    assert (s["min_label"], s["max_label"]) == ("Low", "High")
    assert s["mean"] == pytest.approx(4.0, abs=0.005) and s["median"] == pytest.approx(4.0, abs=0.005)
    assert [(x["label"], x["count"]) for x in s["distribution"]] == [("1", 0), ("2", 0), ("3", 1), ("4", 1), ("5", 1)]
    assert s["distribution"][2]["percent"] == pct(33.3)
    t = a["Text q"]
    assert (t["kind"], t["answered"], t["skipped"]) == ("text", 3, 1)
    assert "options" not in t and "mean" not in t
    assert r.json()["response_count"] == 4 and r.json()["ai"]["status"] == "running"


def test_adm03_ac20_zero_answers_gives_null_mean_and_median(admin, llm):
    sc, tx = qdef("linear_scale", "Scale q"), qdef("short_answer", "Text q")
    form = created(admin, payload([sc, tx]))
    sc, tx = form["questions"]
    _, ids = seed(admin, None, [{"answers": [ans(sc, None), ans(tx, "hello")]}, {"answers": [ans(tx, "bye")]}], form=form)
    r = create(admin, form, ids)
    assert r.status_code == 201, r.text
    s = by_prompt(r.json()["aggregates"])["Scale q"]
    assert (s["answered"], s["skipped"], s["mean"], s["median"]) == (0, 2, None, None)
    assert len(s["distribution"]) == 5 and all(x["count"] == 0 for x in s["distribution"])


def test_adm03_ac20_median_of_even_count_is_the_midpoint(admin, llm):
    sc = qdef("linear_scale", "Scale q", scale=(0, 10))
    form = created(admin, payload([sc]))
    sc = form["questions"][0]
    _, ids = seed(admin, None, [{"answers": [ans(sc, v)]} for v in (1, 2, 8, 10)], form=form)
    s = create(admin, form, ids).json()["aggregates"][0]
    assert s["mean"] == pytest.approx(5.25, abs=0.005) and s["median"] == pytest.approx(5.0, abs=0.005)


def test_adm03_ac28_two_form_versions_grouped_by_question_id_with_newest_text(admin, llm):
    q1_id, q3_id, q4_id, text_id = uid(), uid(), uid(), uid()
    oa, ob, oc, od = uid(), uid(), uid(), uid()

    def snap(questions):
        return {"title": "T", "description": "", "association": None, "questions": questions}

    def mcq(prompt, opts):
        return {"id": q1_id, "type": "multiple_choice", "required": False, "prompt": prompt, "options": opts, "scale": None}

    def scale(lo, hi):
        return {"id": q4_id, "type": "linear_scale", "required": False, "prompt": "Rate", "options": [],
                "scale": {"min": lo, "max": hi, "min_label": f"lo{lo}", "max_label": f"hi{hi}"}}
    textq = {"id": text_id, "type": "short_answer", "required": False, "prompt": "Free", "options": [], "scale": None}
    v1 = snap([mcq("Old prompt", [{"id": oa, "label": "A old"}, {"id": ob, "label": "B"}, {"id": od, "label": "D only old"}]),
               textq, scale(1, 5)])
    v2 = snap([mcq("New prompt", [{"id": oa, "label": "A new"}, {"id": ob, "label": "B"}, {"id": oc, "label": "C"}]),
               {"id": q3_id, "type": "paragraph", "required": False, "prompt": "Only in v2", "options": [], "scale": None},
               textq, scale(0, 10)])
    form = created(admin, payload())
    rows = [
        {"snapshot": v1, "submitted_at": T0, "answers": [{"question_id": q1_id, "value": od}, {"question_id": q4_id, "value": 1}]},
        {"snapshot": v1, "submitted_at": T0 + timedelta(minutes=1), "answers": [{"question_id": q1_id, "value": oa}, {"question_id": q4_id, "value": 5}]},
        {"snapshot": v2, "submitted_at": T0 + timedelta(minutes=2), "answers": [{"question_id": q1_id, "value": oa}, {"question_id": q3_id, "value": "hi"}, {"question_id": q4_id, "value": 10}]},
        {"snapshot": v2, "submitted_at": T0 + timedelta(minutes=3), "answers": [{"question_id": q1_id, "value": uid()}, {"question_id": q3_id, "value": None}, {"question_id": q4_id, "value": 11}]},
    ]
    form, ids = seed(admin, None, rows, form=form)
    r = create(admin, form, ids)
    assert r.status_code == 201, r.text
    aggs = r.json()["aggregates"]
    # newest snapshot's question order, then older-only questions
    assert [a["question_id"] for a in aggs] == [q1_id, q3_id, text_id, q4_id]
    q1 = aggs[0]
    assert q1["prompt"] == "New prompt"
    labels = [(o["option_id"], o["label"], o["count"]) for o in q1["options"]]
    # newest snapshot order, renamed option is one bar, older-only option kept last with its old label
    assert labels == [(oa, "A new", 2), (ob, "B", 0), (oc, "C", 0), (od, "D only old", 1)]
    assert (q1["answered"], q1["skipped"]) == (3, 1)  # unknown option id counts as skipped
    q3 = aggs[1]  # absent from the two v1 snapshots: counted in neither answered nor skipped
    assert (q3["answered"], q3["skipped"]) == (1, 1)
    assert (aggs[2]["answered"], aggs[2]["skipped"]) == (0, 4)
    q4 = aggs[3]
    assert (q4["min"], q4["max"]) == (0, 10) and len(q4["distribution"]) == 11
    assert (q4["answered"], q4["skipped"]) == (3, 1)  # 11 is outside the widest range: skipped
    assert q4["min_label"] == "lo0" and q4["max_label"] == "hi10"  # newest snapshot's labels
    assert q4["mean"] == pytest.approx((1 + 5 + 10) / 3, abs=0.005)


def test_adm03_ac20_type_changed_value_counts_as_skipped(admin, llm):
    qid, a1 = uid(), uid()
    old = {"title": "T", "description": "", "association": None, "questions": [
        {"id": qid, "type": "short_answer", "required": False, "prompt": "Was text", "options": [], "scale": None}]}
    new = {"title": "T", "description": "", "association": None, "questions": [
        {"id": qid, "type": "multiple_choice", "required": False, "prompt": "Now choice",
         "options": [{"id": a1, "label": "A"}], "scale": None}]}
    form = created(admin, payload())
    form, ids = seed(admin, None, [
        {"snapshot": old, "submitted_at": T0, "answers": [{"question_id": qid, "value": "free words"}]},
        {"snapshot": new, "submitted_at": T0 + timedelta(minutes=1), "answers": [{"question_id": qid, "value": a1}]}], form=form)
    q = create(admin, form, ids).json()["aggregates"][0]
    assert q["kind"] == "single" and q["prompt"] == "Now choice"
    assert (q["answered"], q["skipped"]) == (1, 1)


@pytest.mark.parametrize("mode", ["blocked", "never_configured", "timeout", "reply_not_json"])
def test_adm03_ac20_23_statistics_present_and_unchanged_whatever_the_ai_does(admin, llm, mode):
    form, ids = text_form(admin, 3)
    if mode == "blocked":
        fut, aid = start_blocked(admin, llm, form, ids)
        live = get(admin, aid).json()
        assert live["ai"]["status"] == "running" and live["aggregates"]
        first = release(llm, fut).json()
    else:
        mode_value = {"never_configured": llm_client.LlmNotConfigured("x"), "timeout": llm_client.LlmTimeout("x"),
                          "reply_not_json": "not json"}[mode]
        llm.script = {1: mode_value, 2: mode_value}
        first = create(admin, form, ids).json()
    final = wait_done(admin, first["id"])
    assert first["aggregates"] and final["aggregates"] == first["aggregates"]
    assert final["free_text"] == first["free_text"] and final["labels"] == first["labels"]
    if mode != "blocked":
        assert final["ai"]["status"] == "failed" and final["ai"]["result"] is None


def test_adm03_ac20_500_responses_create_within_3s_while_the_llm_is_slow(admin, llm):
    form, ids = text_form(admin, 500)
    llm.gate = None
    start = time.monotonic()
    fut, aid = start_blocked(admin, llm, form, ids)
    # statistics are readable as soon as the row exists, long before the held LLM call returns
    r = get(admin, aid)
    assert r.status_code == 200 and r.json()["aggregates"]
    assert time.monotonic() - start < 3 + 1.5  # POST work plus the first poll; the 3 s bound applies to the POST
    posted = release(llm, fut)
    assert posted.status_code == 201 and posted.json()["response_count"] == 500
