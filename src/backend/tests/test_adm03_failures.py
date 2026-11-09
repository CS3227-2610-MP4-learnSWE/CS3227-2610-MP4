"""ADM-03 AC6, AC15, AC31: every AI failure code, at the first map call, a middle map call and the reduce call."""
import json
import logging
import re

import pytest

import llm_client
from llm_client import LlmReply
from adm02_helpers import actor
from adm03_fixtures import admin, llm  # noqa: F401
from adm03_helpers import SEEDED_USERS, cleanup_from, create, get, listing, run, text_form, wait_done

N_MAP = 3  # 65 distinct free-text answers, at most 30 entries per batch
# (first call number of the step, step text, steps finished before it)
POSITIONS = {"first": (1, "batch 1 of 3", 0), "middle": (2, "batch 2 of 3", 1), "reduce": (4, "merging themes", 3)}
RETRIED = {"ai_reply_cut_off", "ai_reply_not_json", "ai_reply_invalid"}  # model-output problems get one more attempt
VALID_MAP = '{"themes":[{"title":"T","description":"D","evidence":["R1"]}]}'


@pytest.fixture(scope="module")
def big():
    mark = len(SEEDED_USERS)
    admin = actor("admin")
    form, ids = text_form(admin, 65)
    yield admin, form, ids
    cleanup_from(mark)


def reduce_json(summary="Summary.", themes=None, suggestions=None):
    return json.dumps({"summary": summary, "themes": [] if themes is None else themes,
                       "suggestions": [] if suggestions is None else suggestions})


def theme(ev=("R1",), title="T", desc="D"):
    return {"title": title, "description": desc, "evidence": list(ev)}


def sug(basis="feedback", ev=("R1",), text="Do it."):
    return {"text": text, "basis": basis, "evidence": list(ev)}


def invalid(rule):
    return lambda step: re.compile(
        re.escape(f"The AI reply for {step} was rejected because ") + rule
        + re.escape(". No AI result was saved. Start a new analysis."))


def exact(template):
    return lambda step: re.compile(re.escape(template.format(step=step)))


# (id, positions, script value or factory(position), expected code, message matcher(step) -> compiled regex, details subset)
EXCEPTIONS = [
    ("rate_minute", llm_client.LlmRateLimited("student_minute", 12), "rate_limited_minute",
     exact("The AI limit of 20 requests per minute was reached while processing {step}. Try again in 12 seconds."),
     {"limit": 20, "window": "minute", "retry_after_seconds": 12}),
    ("rate_day", llm_client.LlmRateLimited("student_day", 3600), "rate_limited_day",
     exact("The daily AI limit of 300 requests was reached while processing {step}. Try again in 3600 seconds."),
     {"limit": 300, "window": "day", "retry_after_seconds": 3600}),
    ("busy", llm_client.LlmBusy(7), "ai_busy",
     exact("The AI service replied that it is busy (HTTP 429) while processing {step}. Try again in 7 seconds."),
     {"retry_after_seconds": 7}),
    ("timeout", llm_client.LlmTimeout("slow"), "ai_timeout",
     lambda step: exact("The AI service did not answer within 15 seconds (after up to 2 attempts) while processing {step}. The statistics are unaffected. Start a new analysis to run the AI part again.".replace("within 15 seconds", "within " + ("60" if step == "merging themes" else "30") + " seconds"))(step),
     {"timeout_seconds": 30, "attempts": 2}),
    ("upstream", llm_client.LlmUpstreamError("5xx"), "ai_unavailable",
     exact("The AI service could not be reached or returned a server error while processing {step}, after up to 2 attempts. The statistics are unaffected. Start a new analysis once the service is back."),
     {"attempts": 2}),
    ("bad_body", llm_client.LlmBadResponse("none"), "ai_reply_not_json",
     exact("The AI reply for {step} was not a single JSON object, so it was rejected. No AI result was saved. Start a new analysis."), {}),
    ("not_configured", llm_client.LlmNotConfigured("none"), "ai_not_configured",
     lambda step: re.compile(re.escape("AI analysis is not configured on this server (no SoC LLM settings are present), so the AI part could not start. Ask the site operator to configure it. The statistics are unaffected.")), {}),
    ("too_large", llm_client.LlmInputTooLarge("big"), "ai_input_too_large",
     lambda step: re.compile(re.escape(f"The AI input for {step} was ") + r"\d+" + re.escape(" characters, over the limit of ") + r"12000"
                             + re.escape(". This is a defect in the batch size, not something you can fix by selecting differently. Reference ") + r"\S+"
                             + re.escape(" identifies it in the server logs.")), {}),
    ("cut_off", LlmReply(text=VALID_MAP, finish_reason="length", prompt_tokens=1, completion_tokens=1), "ai_reply_cut_off", None, {}),
    ("cut_off_empty", LlmReply(text="", finish_reason="length", prompt_tokens=1, completion_tokens=1), "ai_reply_cut_off", None, {}),
    ("not_json", "I think the themes are great.", "ai_reply_not_json",
     exact("The AI reply for {step} was not a single JSON object, so it was rejected. No AI result was saved. Start a new analysis."), {}),
    ("fenced", "```json\n" + VALID_MAP + "\n```", "ai_reply_not_json",
     exact("The AI reply for {step} was not a single JSON object, so it was rejected. No AI result was saved. Start a new analysis."), {}),
    ("two_objects", VALID_MAP + VALID_MAP, "ai_reply_not_json",
     exact("The AI reply for {step} was not a single JSON object, so it was rejected. No AI result was saved. Start a new analysis."), {}),
]
FIELD = r"[\w\.\[\]]*"


def cut_off_matcher(position):
    limit = 3000 if position == "reduce" else 1600
    return lambda step: re.compile(re.escape(f"The AI reply for {step} was cut off at the output limit of {limit} tokens")
                                   + r"( \(the model used its whole token budget before answering\))?"
                                   + re.escape(". No AI result was saved. Select fewer responses and start a new analysis."))


MAP_INVALID = [
    ("map_extra_key", '{"themes":[],"x":1}', invalid(r"an unexpected field \(x\) was present")),
    ("map_missing_key", "{}", invalid(r"a required field \(themes\) was missing")),
    ("map_wrong_type", '{"themes":"a"}', invalid(r"themes had the wrong type")),
    ("map_empty_title", json.dumps({"themes": [theme(title="")]}), invalid(FIELD + r"title was empty")),
    ("map_long_title", json.dumps({"themes": [theme(title="x" * 51)]}), invalid(FIELD + r"title was longer than 50 characters")),
    ("map_too_many_themes", json.dumps({"themes": [theme(title=f"t{i}") for i in range(4)]}), invalid(r"themes had 4 items, the maximum is 3")),
    ("map_no_evidence", json.dumps({"themes": [theme(ev=())]}), invalid(r"a theme had no supporting responses")),
    ("map_label_outside_selection", json.dumps({"themes": [theme(ev=("R999",))]}), invalid(r"a supporting response label \(R999\) is not in the selection")),
]
REDUCE_INVALID = [
    ("reduce_extra_key", json.dumps({"summary": "s", "themes": [], "suggestions": [], "action": "send"}), invalid(r"an unexpected field \(action\) was present")),
    ("reduce_missing_key", '{"themes":[],"suggestions":[]}', invalid(r"a required field \(summary\) was missing")),
    ("reduce_wrong_type", reduce_json(summary=5), invalid(r"summary had the wrong type")),
    ("reduce_empty_summary", reduce_json(summary=""), invalid(FIELD + r"summary was empty")),
    ("reduce_long_summary", reduce_json(summary="s" * 401), invalid(FIELD + r"summary was longer than 400 characters")),
    ("reduce_too_many_themes", reduce_json(themes=[theme(title=f"t{i}") for i in range(6)]), invalid(r"themes had 6 items, the maximum is 5")),
    ("reduce_too_many_suggestions", reduce_json(suggestions=[sug(text=f"s{i}") for i in range(7)]), invalid(r"suggestions had 7 items, the maximum is 6")),
    ("reduce_theme_no_evidence", reduce_json(themes=[theme(ev=())]), invalid(r"a theme had no supporting responses")),
    ("reduce_label_outside_selection", reduce_json(themes=[theme(ev=("R999",))]), invalid(r"a supporting response label \(R999\) is not in the selection")),
    ("reduce_label_outside_input", reduce_json(themes=[theme(ev=("R3",))]), invalid(r"a supporting response label \(R3\) was not in the input for this step")),
    ("reduce_feedback_without_evidence", reduce_json(suggestions=[sug("feedback", ())]), invalid(r"a suggestion marked as based on feedback had no supporting responses")),
    ("reduce_ai_with_evidence", reduce_json(suggestions=[sug("ai", ("R1",))]), invalid(r"a suggestion marked as an AI suggestion listed supporting responses")),
    ("reduce_bad_basis", reduce_json(suggestions=[sug("opinion", ())]), invalid(r"a suggestion basis was not feedback or ai")),
]


def cases():
    out = []
    for name, value, code, matcher, details in EXCEPTIONS:
        for pos in POSITIONS:
            m = cut_off_matcher(pos) if name.startswith("cut_off") else matcher
            out.append(pytest.param(pos, value, code, m, details, id=f"{name}-{pos}"))
    for name, value, matcher in MAP_INVALID:
        for pos in ("first", "middle"):
            out.append(pytest.param(pos, value, "ai_reply_invalid", matcher, {}, id=f"{name}-{pos}"))
    # a label of another batch, which is inside the selection but not in this step's input
    for pos, label in (("first", "R65"), ("middle", "R1")):
        out.append(pytest.param(pos, json.dumps({"themes": [theme(ev=(label,))]}), "ai_reply_invalid",
                                invalid(r"a supporting response label \(" + label + r"\) was not in the input for this step"),
                                {}, id=f"map_label_outside_input-{pos}"))
    for name, value, matcher in REDUCE_INVALID:
        out.append(pytest.param("reduce", value, "ai_reply_invalid", matcher, {}, id=name))
    return out


@pytest.mark.parametrize("pos,value,code,matcher,details", cases())
def test_adm03_ac6_15_31_ai_failure_has_exact_stored_message_step_details_and_stops(big, llm, pos, value, code, matcher, details):
    admin, form, ids = big
    n, step_text, finished = POSITIONS[pos]
    retried = code in RETRIED
    llm.script = {n: value, n + 1: value} if retried else {n: value}
    r = create(admin, form, ids)
    assert r.status_code == 201, r.text
    done = wait_done(admin, r.json()["id"])
    err = done["ai"]["error"]
    assert done["ai"]["status"] == "failed" and done["ai"]["result"] is None
    assert err["code"] == code, err
    if retried:  # the second attempt's failure is stored, with the attempt count
        base = matcher(step_text).pattern.split(r"\.\ No\ AI\ result")[0]
        assert re.match(base, err["message"]), err["message"]
        assert "after 2 attempts" in err["message"], err["message"]
        assert err["details"]["attempts"] == 2 and err["details"]["first_attempt_code"] == code, err["details"]
    else:
        assert matcher(step_text).fullmatch(err["message"]), err["message"]
        assert "after 2 attempts" not in err["message"] or code in ("ai_timeout", "ai_unavailable")
    if code != "ai_not_configured":
        want = {"batch": {"kind": "batch", "index": n, "total": N_MAP}, "reduce": {"kind": "merge", "index": None, "total": None}}
        assert err["step"] == want["batch" if pos != "reduce" else "reduce"]
    if code == "ai_timeout":  # the actual per-call limit: 30 s for a batch, 60 s for the merge
        details = {**details, "timeout_seconds": 60 if pos == "reduce" else 30}
    for k, v in details.items():
        assert err["details"][k] == v, err["details"]
    assert done["ai"]["progress"]["done"] == finished  # a partial result is never presented as complete
    assert len(llm.calls) == n + (1 if retried else 0)  # exactly the attempts of the failing step, no later call
    again = get(admin, done["id"]).json()
    assert again["ai"] == done["ai"] and again["aggregates"] == done["aggregates"]
    item = listing(admin)["items"][0]
    assert item["id"] == done["id"] and item["ai_status"] == "failed"
    # the admin can immediately start another analysis
    llm.script = {}
    ok = create(admin, form, ids[:3])
    assert ok.status_code == 201, ok.text
    assert wait_done(admin, ok.json()["id"])["ai"]["status"] == "complete"


@pytest.mark.parametrize("pos", list(POSITIONS))
def test_adm03_ac31_unexpected_job_exception_is_internal_error_with_a_logged_reference(big, llm, pos, caplog):
    admin, form, ids = big
    n, step_text, _ = POSITIONS[pos]
    llm.script = {n: RuntimeError("SECRET-INTERNAL-DETAIL response text")}
    with caplog.at_level(logging.DEBUG):
        done = wait_done(admin, create(admin, form, ids).json()["id"])
    err = done["ai"]["error"]
    m = re.fullmatch(r"An unexpected server error occurred while .*" + re.escape(step_text)
                     + r"\. The cause was not an invalid request\. Reference (\S+) identifies it in the server logs\.", err["message"])
    assert err["code"] == "internal_error" and m, err
    assert err["details"]["reference"] == m.group(1) and m.group(1) in caplog.text
    assert "SECRET-INTERNAL-DETAIL" not in str(done) and len(llm.calls) == n


def test_adm03_ac31_failure_messages_never_contain_response_text_or_identity(big, llm):
    admin, form, ids = big
    llm.script = {2: llm_client.LlmTimeout("unique feedback number 31 about topic 217")}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    blob = json.dumps(done["ai"]["error"])
    assert "unique feedback" not in blob and form["id"] not in blob and form["title"] not in blob
    assert not any(i in blob for i in ids) and str(admin) not in blob


def test_adm03_ac2_complete_only_when_every_call_validated(big, llm):
    admin, form, ids = big
    done = run(admin, form, ids)
    assert done["ai"]["status"] == "complete" and done["ai"]["progress"]["done"] == done["ai"]["progress"]["total"] == 4
    assert len(llm.calls) == 4


def test_adm03_ac2_a_long_valid_reduce_reply_completes_the_analysis(big, llm):
    admin, form, ids = big
    long_reply = json.dumps({
        "summary": "s" * 400,
        "themes": [{"title": f"Theme {i} " + "t" * 60, "description": "d" * 250, "evidence": ["R1"]} for i in range(5)],
        "suggestions": [{"text": "x" * 200, "basis": "feedback", "evidence": ["R1"]} for _ in range(6)]})
    assert len(long_reply) >= 3000
    llm.script = {4: long_reply}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    assert done["ai"]["status"] == "complete", done["ai"]["error"]
    assert len(done["ai"]["result"]["themes"]) == 5 and len(done["ai"]["result"]["suggestions"]) == 6


def test_adm03_ac31_empty_reply_cut_off_message_is_the_registry_text(big, llm):
    admin, form, ids = big
    empty = LlmReply(text="", finish_reason="length", prompt_tokens=1, completion_tokens=1)
    llm.script = {4: empty, 5: empty}
    err = wait_done(admin, create(admin, form, ids).json()["id"])["ai"]["error"]
    assert err["code"] == "ai_reply_cut_off"
    assert "output limit of 3000 tokens (the model used its whole token budget before answering)" in err["message"]


# ---- fifth pass: one more attempt for model-output problems only ----

BAD_REPLIES = ["not json at all", "", '{"themes":[],"x":1}']


@pytest.mark.parametrize("bad", BAD_REPLIES)
@pytest.mark.parametrize("pos", ["first", "middle", "reduce"])
def test_adm03_ac15_second_attempt_succeeds_after_a_bad_first_reply(big, llm, pos, bad):
    admin, form, ids = big
    n, _, _ = POSITIONS[pos]
    bad_text = bad if pos != "reduce" else bad.replace('"themes":[]', '"summary":"s","themes":[],"suggestions":[]')
    llm.script = {n: bad_text}  # the next call (attempt 2 of the same step) falls back to the valid default
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    assert done["ai"]["status"] == "complete" and done["ai"]["error"] is None, done["ai"]["error"]
    assert len(llm.calls) == 5  # 3 map steps + 1 reduce + one extra attempt
    assert llm.calls[n - 1].all_text == llm.calls[n].all_text  # same prompt for the second attempt
    assert done["ai"]["progress"]["done"] == done["ai"]["progress"]["total"] == 4  # progress counts steps, not attempts


def test_adm03_ac15_cut_off_first_attempt_is_retried(big, llm):
    admin, form, ids = big
    llm.script = {1: LlmReply(text="", finish_reason="length", prompt_tokens=1, completion_tokens=1)}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    assert done["ai"]["status"] == "complete" and len(llm.calls) == 5


NOT_RETRIED = [
    ("rate_minute", llm_client.LlmRateLimited("student_minute", 12)), ("rate_day", llm_client.LlmRateLimited("student_day", 99)),
    ("busy", llm_client.LlmBusy(7)), ("timeout", llm_client.LlmTimeout("slow")),
    ("upstream", llm_client.LlmUpstreamError("5xx")), ("not_configured", llm_client.LlmNotConfigured("none")),
    ("too_large", llm_client.LlmInputTooLarge("big")), ("internal", RuntimeError("boom")),
]


@pytest.mark.parametrize("name,exc", NOT_RETRIED, ids=[x[0] for x in NOT_RETRIED])
@pytest.mark.parametrize("pos", ["first", "reduce"])
def test_adm03_ac31_errors_that_are_not_model_output_are_never_retried(big, llm, pos, name, exc):
    admin, form, ids = big
    n, _, _ = POSITIONS[pos]
    llm.script = {n: exc}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    assert done["ai"]["status"] == "failed"
    assert len(llm.calls) == n  # exactly one call for the failing step
    assert done["ai"]["error"]["details"].get("first_attempt_code") is None
    if name not in ("timeout", "upstream"):
        assert "after 2 attempts" not in done["ai"]["error"]["message"]


def test_adm03_ac46_responses_deleted_is_not_retried(admin, llm):
    from adm03_helpers import release, start_blocked
    from adm02_helpers import ADMIN as ADM02
    from auth_helpers import call
    form, ids = text_form(admin, 65)
    fut, aid = start_blocked(admin, llm, form, ids)
    assert call("DELETE", f"{ADM02}/forms/{form['id']}/responses/{ids[40]}", admin).status_code == 204
    release(llm, fut)
    done = wait_done(admin, aid)
    assert done["ai"]["error"]["code"] == "ai_responses_deleted"
    assert len(llm.calls) < 4 and done["ai"]["error"]["details"].get("first_attempt_code") is None


def test_adm03_ac31_reduce_prompt_asks_for_a_summary_of_at_most_350_characters(big, llm):
    admin, form, ids = big
    wait_done(admin, create(admin, form, ids).json()["id"])
    red = llm.of("reduce")[0]
    assert "350" in red.system_text + red.user_text
