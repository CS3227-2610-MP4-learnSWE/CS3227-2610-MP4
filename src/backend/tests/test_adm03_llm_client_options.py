"""ADM-03 verifier round 3: the job's 600 s start cutoff (fake monotonic clock) and the reasoning_effort fallback."""
import json
import re

import httpx
import pytest

import llm_client
from llm_client import ChatMessage, Limits, Settings, SoclaasClient
from adm02_helpers import actor
from adm03_fixtures import admin, llm  # noqa: F401
from adm03_helpers import SEEDED_USERS, cleanup_from, create, expect, get, release, start_blocked, text_form, wait_done

MSGS = [ChatMessage("user", "hello")]


# ---- job clock seam ----

class Clock:
    def __init__(self):
        self.t = 1000.0

    def advance(self, seconds):
        self.t += seconds

    def __call__(self):
        return self.t


@pytest.fixture
def clock(monkeypatch):
    from feedback_analysis import jobs
    c = Clock()
    monkeypatch.setattr(jobs, "_now", c)
    return c


@pytest.fixture(scope="module")
def three_batches():
    mark = len(SEEDED_USERS)
    a = actor("admin")
    form, ids = text_form(a, 65)
    yield a, form, ids
    cleanup_from(mark)


def advancing(llm, clock, seconds, bad=False):
    def reply(c):
        clock.advance(seconds)
        return "not json" if bad else llm.default_text(c)
    return reply


def test_adm03_ac23_no_call_starts_after_600_s_and_the_step_fails_with_ai_time_limit(three_batches, llm, clock):
    admin, form, ids = three_batches
    llm.script = {1: advancing(llm, clock, 601)}  # the first map step ends at age 601
    first = create(admin, form, ids).json()
    done = wait_done(admin, first["id"])
    err = done["ai"]["error"]
    assert done["ai"]["status"] == "failed" and err["code"] == "ai_time_limit", err
    assert len(llm.calls) == 1  # the first attempt of the next step never started
    assert done["ai"]["result"] is None and done["aggregates"] == first["aggregates"]
    d = err["details"]
    assert d["elapsed_seconds"] >= 600 and d["limit_seconds"] == 600 and d["step"]
    m = re.fullmatch(r"The AI step stopped before (.+) because the analysis had already run (\d+) seconds, close to the 600 second limit\. "
                     r"The statistics remain correct\. Start a new analysis, or select fewer responses\.", err["message"])
    assert m and int(m.group(2)) == d["elapsed_seconds"], err["message"]
    assert done["ai"]["progress"]["done"] == 1


def test_adm03_ac23_a_retry_blocked_by_the_cutoff_stores_the_first_attempts_failure(three_batches, llm, clock):
    admin, form, ids = three_batches
    llm.script = {1: advancing(llm, clock, 601, bad=True)}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    err = done["ai"]["error"]
    assert err["code"] == "ai_reply_not_json", err  # not ai_time_limit: the first failure stands
    assert len(llm.calls) == 1
    assert err["details"].get("attempts") != 2


def test_adm03_ac23_slow_steps_stop_the_job_before_the_sweep_bound_and_the_slot_stays_taken_until_it_ends(llm, clock):
    admin = actor("admin")
    form, ids = text_form(admin, 300, text=lambda i: f"comment {i:04d} " + "word " * 50)  # ten batches
    llm.script = {n: advancing(llm, clock, 100) for n in range(1, 40)}  # every call ages the job by 100 s
    fut, aid = start_blocked(admin, llm, form, ids)
    expect(create(admin, form, ids), 409, "analysis_in_progress")  # a healthy running job holds the slot
    release(llm, fut)
    done = wait_done(admin, aid)
    err = done["ai"]["error"]
    assert done["ai"]["status"] == "failed" and err["code"] == "ai_time_limit", err
    assert len(llm.calls) == 6  # calls at ages 0..500 started; the one at 600 did not
    assert 600 <= err["details"]["elapsed_seconds"] < 780
    llm.script = {}
    again = create(admin, form, ids)
    assert again.status_code == 201, again.text  # the slot is free once the job ended
    wait_done(admin, again.json()["id"])


def test_adm03_ac31_ai_time_limit_is_registered_without_generic_wording_and_is_not_retried(three_batches, llm, clock):
    from feedback_analysis import failures
    assert "ai_time_limit" in failures.MESSAGES
    text = failures.render("ai_time_limit", step="batch 2 of 3", s=601, limit=600)
    assert text == ("The AI step stopped before batch 2 of 3 because the analysis had already run 601 seconds, close to the 600 second "
                    "limit. The statistics remain correct. Start a new analysis, or select fewer responses.")
    low = text.lower()
    assert not any(w in low for w in ("something went wrong", "an error occurred", "unknown error", "try again later"))
    admin, form, ids = three_batches
    llm.script = {1: advancing(llm, clock, 700)}
    done = wait_done(admin, create(admin, form, ids).json()["id"])
    assert done["ai"]["error"]["code"] == "ai_time_limit" and len(llm.calls) == 1  # no retry after the limit
    assert done["ai"]["error"]["details"].get("first_attempt_code") is None


# ---- reasoning_effort fallback in SoclaasClient ----

class Observer:
    def __init__(self):
        self.reserved, self.finished = [], []

    def reserve(self, feature):
        self.reserved.append(feature)
        return len(self.reserved)

    def finish(self, aid, outcome, **measurements):
        self.finished.append((aid, outcome))
        return True


def ok():
    return httpx.Response(200, json={"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}]})


def client(script):
    obs, bodies = Observer(), []

    def send(request):
        bodies.append(json.loads(request.content))
        return script.pop(0)

    c = SoclaasClient(Settings("https://soc.example.test/v1", "test-only-key", "m"), transport=httpx.MockTransport(send),
                      observer=obs, limits=Limits(), sleep=lambda _: None)
    return c, obs, bodies


@pytest.mark.parametrize("status", [400, 422])
def test_adm03_ac26_gateway_rejecting_reasoning_effort_is_retried_once_without_it_and_accounted(status):
    c, obs, bodies = client([httpx.Response(status, json={"error": "unsupported"}), ok()])
    reply = c.complete(MSGS, max_tokens=30, caller_id="u", reasoning_effort="low")
    assert reply.text == "hi"
    assert bodies[0]["reasoning_effort"] == "low" and "reasoning_effort" not in bodies[1]
    assert len(obs.reserved) == len(obs.finished) == 2  # two reserve/finish pairs
    assert obs.finished[0][1] == "other_failure" and obs.finished[1][1] == "success"


@pytest.mark.parametrize("status", [401, 403, 404, 429])
def test_adm03_ac26_other_statuses_are_not_retried_without_the_field(status):
    c, obs, bodies = client([httpx.Response(status, json={"error": "x"}), ok(), ok()])
    with pytest.raises(Exception):
        c.complete(MSGS, max_tokens=30, caller_id="u", reasoning_effort="low")
    assert all(b.get("reasoning_effort") == "low" for b in bodies)  # never resent without the field
    assert len(obs.reserved) == len(obs.finished) == len(bodies)


def test_adm03_ac26_a_request_without_reasoning_effort_behaves_as_before():
    c, obs, bodies = client([httpx.Response(400, json={"error": "bad"}), ok()])
    with pytest.raises(llm_client.LlmBadResponse):
        c.complete(MSGS, max_tokens=30, caller_id="u")
    assert len(bodies) == 1 and "reasoning_effort" not in bodies[0] and len(obs.reserved) == 1


def test_adm03_ac26_reasoning_effort_success_sends_the_field_once():
    c, obs, bodies = client([ok()])
    c.complete(MSGS, max_tokens=30, caller_id="u", reasoning_effort="low")
    assert len(bodies) == 1 and bodies[0]["reasoning_effort"] == "low" and len(obs.reserved) == 1
