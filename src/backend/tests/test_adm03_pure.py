"""ADM-03 AC15, AC31: the message registry and the strict reply validators (pure, no DB, no HTTP)."""
import json
import re

import pytest

CODES = [
    "invalid_request", "selection_required", "no_responses", "too_many_responses", "nothing_to_analyse",
    "form_not_found", "response_not_found", "analysis_in_progress", "analysis_not_found", "analysis_running",
    "evidence_not_found", "internal_error", "ai_timeout", "rate_limited_minute", "rate_limited_day", "ai_busy",
    "ai_unavailable", "ai_not_configured", "ai_input_too_large", "ai_reply_not_json", "ai_reply_invalid",
    "ai_reply_cut_off", "analysis_interrupted",
]
AI_CODES = [c for c in CODES if c.startswith("ai_") or c.startswith("rate_limited") or c in ("analysis_interrupted",)]
FORBIDDEN = ["something went wrong", "an error occurred", "unknown error"]


@pytest.fixture(scope="module")
def failures():
    from feedback_analysis import failures
    return failures


def test_adm03_ac31_registry_has_every_code_of_the_spec(failures):
    assert set(CODES) <= set(failures.MESSAGES)


def test_adm03_ac31_no_template_uses_catch_all_wording(failures):
    for code, template in failures.MESSAGES.items():
        low = template.lower().strip()
        assert not any(w in low for w in FORBIDDEN), code
        assert "try again later" not in low, code
        assert low.rstrip(".") != "try again later"


def test_adm03_ac31_every_ai_failure_names_its_step_or_a_number(failures):
    for code in AI_CODES:
        if code == "ai_not_configured":
            continue  # states the cause and the action; there is no step yet
        assert "{" in failures.MESSAGES[code], code


@pytest.mark.parametrize("code,values,text", [
    ("analysis_running", dict(s=100, r=260),
     "This analysis cannot be deleted yet: its AI step has been running for 100 seconds. It finishes or is marked interrupted within 260 seconds (the limit is 420 seconds). Delete it after that."),
    ("analysis_in_progress", dict(s=12),
     "Another analysis started 12 seconds ago is still running its AI step. A running AI step finishes or fails within 420 seconds. Wait for it, then generate again."),
    ("too_many_responses", dict(n=501),
     "You selected 501 responses, but one analysis can cover at most 500. Select fewer responses."),
    ("response_not_found", dict(k=2, n=5),
     "2 of the 5 selected responses are not available for this form (they may have been deleted or belong to another form). Reload the list and select again."),
    ("nothing_to_analyse", dict(n=4),
     "The 4 selected responses contain no answered questions, so there is nothing to analyse."),
    ("internal_error", dict(step="deleting the analysis", ref="abc123"),
     "An unexpected server error occurred while deleting the analysis. The cause was not an invalid request. Reference abc123 identifies it in the server logs."),
    ("analysis_interrupted", dict(s=500, done=2, total=4),
     "The AI step was interrupted: it had been running for 500 seconds without finishing (the limit is 420 seconds), probably because the server restarted. It had finished 2 of 4 steps. The statistics are unaffected. Start a new analysis."),
])
def test_adm03_ac31_render_gives_the_exact_spec_text(failures, code, values, text):
    assert failures.render(code, **values) == text


def test_adm03_ac31_rendered_messages_hold_only_what_they_are_given(failures):
    out = failures.render("rate_limited_minute", limit=20, step="batch 3 of 6", n=41)
    assert out == "The AI limit of 20 requests per minute was reached while processing batch 3 of 6. Try again in 41 seconds."
    out = failures.render("ai_reply_invalid", step="merging themes", rule="a theme had no supporting responses")
    assert "merging themes" in out and "a theme had no supporting responses" in out


MAP_OK = {"themes": [{"title": "T", "description": "D", "evidence": ["R1", "R2"]}]}
REDUCE_OK = {"summary": "S", "themes": [{"title": "T", "description": "D", "evidence": ["R1"]}],
             "suggestions": [{"text": "x", "basis": "feedback", "evidence": ["R1"]}, {"text": "y", "basis": "ai", "evidence": []}]}


@pytest.fixture(scope="module")
def validate():
    from feedback_analysis import validate
    return validate


def code_for(fn, text, labels):
    with pytest.raises(Exception) as e:
        fn(text, labels)
    assert type(e.value).__name__ == "InvalidReply", e.value
    return e.value.code


def test_adm03_ac15_valid_replies_are_accepted(validate):
    validate.parse_map_reply(json.dumps(MAP_OK), {"R1", "R2", "R3"})
    validate.parse_reduce_reply(json.dumps(REDUCE_OK), {"R1", "R2"})
    validate.parse_map_reply('  {"themes":[]}\n', {"R1"})


@pytest.mark.parametrize("text", ["", "ok", "[]", "```json\n{\"themes\":[]}\n```", '{"themes":[]} extra', '{"themes":[]}{"themes":[]}', "null", '"x"'])
def test_adm03_ac15_not_a_single_json_object_is_ai_reply_not_json(validate, text):
    assert code_for(validate.parse_map_reply, text, {"R1"}) == "ai_reply_not_json"
    assert code_for(validate.parse_reduce_reply, text, {"R1"}) == "ai_reply_not_json"


@pytest.mark.parametrize("obj", [
    {"themes": [], "extra": 1}, {}, {"themes": {}}, {"themes": [{"title": "", "description": "D", "evidence": ["R1"]}]},
    {"themes": [{"title": "T" * 51, "description": "D", "evidence": ["R1"]}]},
    {"themes": [{"title": "T", "description": "D" * 101, "evidence": ["R1"]}]},
    {"themes": [{"title": "T", "description": "D", "evidence": []}]},
    {"themes": [{"title": "T", "description": "D", "evidence": ["R9"]}]},
    {"themes": [{"title": "T", "description": "D", "evidence": ["R1"]}] * 4},
])
def test_adm03_ac15_map_schema_violations_are_ai_reply_invalid(validate, obj):
    assert code_for(validate.parse_map_reply, json.dumps(obj), {"R1", "R2"}) == "ai_reply_invalid"


def test_adm03_ac15_reduce_rules(validate):
    labels = {"R1", "R2"}
    def bad(**change):
        o = json.loads(json.dumps(REDUCE_OK))
        o.update(change)
        return code_for(validate.parse_reduce_reply, json.dumps(o), labels)
    assert bad(summary="") == "ai_reply_invalid"
    assert bad(summary="s" * 601) == "ai_reply_invalid"
    assert bad(suggestions=[{"text": "x", "basis": "feedback", "evidence": []}]) == "ai_reply_invalid"
    assert bad(suggestions=[{"text": "x", "basis": "ai", "evidence": ["R1"]}]) == "ai_reply_invalid"
    assert bad(suggestions=[{"text": "x", "basis": "maybe", "evidence": []}]) == "ai_reply_invalid"
    assert bad(themes=[{"title": "T", "description": "D", "evidence": ["R7"]}]) == "ai_reply_invalid"
    assert bad(themes=[{"title": "T", "description": "D", "evidence": ["R1"]}] * 7) == "ai_reply_invalid"
    assert bad(suggestions=[{"text": "x", "basis": "ai", "evidence": []}] * 9) == "ai_reply_invalid"


def long_reduce(desc=250, text=200, summary=400):
    return {"summary": "s" * summary,
            "themes": [{"title": f"Theme {i} " + "t" * 60, "description": "d" * desc, "evidence": ["R1"]} for i in range(5)],
            "suggestions": [{"text": "x" * text, "basis": "feedback", "evidence": ["R1"]} for _ in range(6)]}


def test_adm03_ac15_a_long_valid_reduce_reply_of_about_3000_characters_is_accepted(validate):
    reply = json.dumps(long_reduce())
    assert len(reply) >= 3000
    validate.parse_reduce_reply(reply, {"R1"})


def test_adm03_ac15_reduce_description_and_suggestion_caps(validate):
    validate.parse_reduce_reply(json.dumps(long_reduce(desc=250, text=200)), {"R1"})
    assert code_for(validate.parse_reduce_reply, json.dumps(long_reduce(desc=251)), {"R1"}) == "ai_reply_invalid"
    assert code_for(validate.parse_reduce_reply, json.dumps(long_reduce(text=201)), {"R1"}) == "ai_reply_invalid"
    validate.parse_reduce_reply(json.dumps(long_reduce(summary=400)), {"R1"})
    assert code_for(validate.parse_reduce_reply, json.dumps(long_reduce(summary=401)), {"R1"}) == "ai_reply_invalid"
