"""STU-03 shared SoC LLM client (llm_client.py), AC19 to AC24 and the input ceiling.

httpx.MockTransport plus an injected clock and sleep: no network, no real sleeping,
no real key (the key below is a made-up sentinel).
"""
import json
import logging
import threading

import httpx
import llm_client
import pytest
from llm_client import (
    ChatMessage,
    Limits,
    LlmBadResponse,
    LlmBusy,
    LlmError,
    LlmInputTooLarge,
    LlmNotConfigured,
    LlmRateLimited,
    LlmTimeout,
    LlmUpstreamError,
    Settings,
    SoclaasClient,
)

KEY = "sk-TEST-SENTINEL-KEY-0001"
BASE = "https://llm.example.test/v1"
MODEL = "test-model"
MSGS = [ChatMessage("system", "rules"), ChatMessage("user", "hello")]


def ok_json(text="Hi there", finish="stop", usage=(11, 7)):
    body = {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}]}
    if usage:
        body["usage"] = {"prompt_tokens": usage[0], "completion_tokens": usage[1]}
    return body


class Env:
    """A client wired to a scripted MockTransport, a fake clock and a recording sleep."""

    def __init__(self, script=None, limits=Limits(), settings=None):
        self.script = list(script or [])  # items: httpx.Response | Exception | callable(request)
        self.requests: list[httpx.Request] = []
        self.now = 0.0
        self.sleeps: list[float] = []
        self._lock = threading.Lock()
        self.client = SoclaasClient(
            settings or Settings(BASE, KEY, MODEL),
            limits=limits,
            transport=httpx.MockTransport(self._handle),
            clock=lambda: self.now,
            sleep=self.sleeps.append,
        )

    def _handle(self, request):
        with self._lock:
            self.requests.append(request)
            step = self.script.pop(0) if self.script else httpx.Response(200, json=ok_json())
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        return step

    def complete(self, messages=MSGS, max_tokens=100, caller="stu-a"):
        return self.client.complete(messages, max_tokens=max_tokens, caller_id=caller)

    @property
    def calls(self):
        return len(self.requests)


def timeout_error():
    return httpx.ReadTimeout("timed out")


# ---------------------------------------------------------------- AC19
def test_stu03_ac19_request_shape_and_reply_fields():
    env = Env([httpx.Response(200, json=ok_json("Hello", "stop", (11, 7)))])
    reply = env.complete(max_tokens=77)
    assert reply.text == "Hello"
    assert reply.finish_reason == "stop"
    assert (reply.prompt_tokens, reply.completion_tokens) == (11, 7)
    assert env.calls == 1
    req = env.requests[0]
    assert req.method == "POST"
    assert str(req.url) == f"{BASE}/chat/completions"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    body = json.loads(req.content)
    assert body["model"] == MODEL
    assert body["max_tokens"] == 77
    assert body["messages"] == [{"role": "system", "content": "rules"}, {"role": "user", "content": "hello"}]


def test_stu03_ac19_missing_usage_gives_none_tokens():
    env = Env([httpx.Response(200, json=ok_json(usage=None))])
    reply = env.complete()
    assert reply.prompt_tokens is None and reply.completion_tokens is None


@pytest.mark.parametrize(
    "settings",
    [
        Settings(None, KEY, MODEL),
        Settings(BASE, None, MODEL),
        Settings(BASE, KEY, None),
        Settings(None, None, None),
    ],
)
def test_stu03_ac19_missing_settings_raise_without_a_network_call(settings):
    env = Env(settings=settings)
    with pytest.raises(LlmNotConfigured):
        env.complete()
    assert env.calls == 0


def test_stu03_ac19_from_env_reads_the_three_variables_and_treats_blank_as_missing():
    full = {"SOCLAAS_BASE_URL": BASE, "SOCLAAS_API_KEY": KEY, "SOCLAAS_MODEL": MODEL}
    s = Settings.from_env(full)
    assert (s.base_url, s.api_key, s.model) == (BASE, KEY, MODEL)
    for name in full:
        blank = dict(full, **{name: "   "})
        s = Settings.from_env(blank)
        assert [s.base_url, s.api_key, s.model].count(None) == 1
        gone = {k: v for k, v in full.items() if k != name}
        assert [Settings.from_env(gone).base_url, Settings.from_env(gone).api_key,
                Settings.from_env(gone).model].count(None) == 1
    s = Settings.from_env({})
    assert (s.base_url, s.api_key, s.model) == (None, None, None)


def test_stu03_ac19_get_llm_client_is_built_from_the_environment_and_reused(monkeypatch):
    clear = getattr(llm_client.get_llm_client, "cache_clear", None)
    for name in ("SOCLAAS_BASE_URL", "SOCLAAS_API_KEY", "SOCLAAS_MODEL"):
        monkeypatch.delenv(name, raising=False)
    if clear:
        clear()
    try:
        first = llm_client.get_llm_client()
        assert llm_client.get_llm_client() is first
        with pytest.raises(LlmNotConfigured):
            first.complete(MSGS, max_tokens=10, caller_id="x")
    finally:
        if clear:
            clear()


# ---------------------------------------------------------------- AC20
def test_stu03_ac20_timeout_per_try_is_fifteen_seconds():
    env = Env([httpx.Response(200, json=ok_json())])
    env.complete()
    assert env.requests[0].extensions["timeout"]["read"] == 15.0
    env2 = Env([httpx.Response(200, json=ok_json())], limits=Limits(timeout_seconds=3.0))
    env2.complete()
    assert env2.requests[0].extensions["timeout"]["read"] == 3.0


def test_stu03_ac20_timeout_then_success_retries_once_after_the_delay():
    env = Env([timeout_error(), httpx.Response(200, json=ok_json("second"))])
    assert env.complete().text == "second"
    assert env.calls == 2
    assert env.sleeps == [0.5]


def test_stu03_ac20_timeout_twice_raises_llm_timeout():
    env = Env([timeout_error(), timeout_error(), httpx.Response(200, json=ok_json())])
    with pytest.raises(LlmTimeout):
        env.complete()
    assert env.calls == 2


@pytest.mark.parametrize("status", [500, 502, 503])
def test_stu03_ac20_5xx_then_success(status):
    env = Env([httpx.Response(status, text="boom"), httpx.Response(200, json=ok_json("fine"))])
    assert env.complete().text == "fine"
    assert env.calls == 2


@pytest.mark.parametrize("status", [500, 503])
def test_stu03_ac20_5xx_twice_raises_upstream_error(status):
    env = Env([httpx.Response(status), httpx.Response(status), httpx.Response(200, json=ok_json())])
    with pytest.raises(LlmUpstreamError):
        env.complete()
    assert env.calls == 2


def test_stu03_ac20_connection_error_is_retried_then_upstream_error():
    env = Env([httpx.ConnectError("refused"), httpx.ConnectError("refused"), httpx.Response(200, json=ok_json())])
    with pytest.raises(LlmUpstreamError):
        env.complete()
    assert env.calls == 2


def test_stu03_ac20_retries_follow_the_limits_setting():
    env = Env([timeout_error(), httpx.Response(200, json=ok_json())], limits=Limits(max_retries=0))
    with pytest.raises(LlmTimeout):
        env.complete()
    assert env.calls == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_stu03_ac20_other_4xx_is_bad_response_without_retry(status):
    env = Env([httpx.Response(status, json={"error": "nope"})])
    with pytest.raises(LlmBadResponse):
        env.complete()
    assert env.calls == 1
    assert env.sleeps == []


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="this is not json"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{}]}),
        httpx.Response(200, json={"choices": [{"message": {}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": "   \n "}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": None}}]}),
        httpx.Response(200, json={"choices": [{"message": {"content": 123}}]}),
        httpx.Response(200, json=["not", "an", "object"]),
    ],
    ids=["not-json", "empty-object", "no-choices", "empty-choice", "no-content", "empty-text",
         "blank-text", "null-content", "number-content", "array"],
)
def test_stu03_ac20_malformed_success_is_bad_response_without_retry(response):
    env = Env([response, httpx.Response(200, json=ok_json())])
    with pytest.raises(LlmBadResponse):
        env.complete()
    assert env.calls == 1


def test_stu03_ac20_reply_text_is_cut_to_two_thousand_characters():
    env = Env([httpx.Response(200, json=ok_json("y" * 5000))])
    assert len(env.complete().text) <= 2000


def test_stu03_ac20_all_errors_share_a_base_class():
    for cls in (LlmNotConfigured, LlmInputTooLarge, LlmRateLimited, LlmBusy, LlmTimeout,
                LlmUpstreamError, LlmBadResponse):
        assert issubclass(cls, LlmError)


# ---------------------------------------------------------------- AC21
def test_stu03_ac21_twenty_pass_and_the_twenty_first_is_limited_by_minute():
    env = Env()
    for _ in range(20):
        env.complete()
    assert env.calls == 20
    with pytest.raises(LlmRateLimited) as info:
        env.complete()
    assert info.value.scope == "student_minute"
    assert 1 <= info.value.retry_after_seconds <= 60
    assert isinstance(info.value.retry_after_seconds, int)
    assert env.calls == 20  # no transport call for the refused one


def test_stu03_ac21_allowed_again_after_the_window_passes():
    env = Env()
    for _ in range(20):
        env.complete()
    env.now += 30
    with pytest.raises(LlmRateLimited):
        env.complete()
    env.now += 31  # 61 s after the first call
    env.complete()
    assert env.calls == 21


def test_stu03_ac21_three_hundred_per_day_then_student_day():
    env = Env()
    for batch in range(15):
        for _ in range(20):
            env.complete()
        env.now += 61  # each batch is in its own minute window
    assert env.calls == 300
    with pytest.raises(LlmRateLimited) as info:
        env.complete()
    assert info.value.scope == "student_day"
    assert 1 <= info.value.retry_after_seconds <= 86_400
    assert env.calls == 300
    env.now += 86_400  # the first calls are now more than a day old
    env.complete()
    assert env.calls == 301


def test_stu03_ac21_other_callers_are_unaffected():
    env = Env()
    for _ in range(20):
        env.complete(caller="stu-a")
    with pytest.raises(LlmRateLimited):
        env.complete(caller="stu-a")
    env.complete(caller="stu-b")
    assert env.calls == 21


def test_stu03_ac21_an_internal_retry_counts_once():
    env = Env()
    for _ in range(20):
        env.script.extend([timeout_error(), httpx.Response(200, json=ok_json())])
        env.complete()
    assert env.calls == 40
    with pytest.raises(LlmRateLimited):
        env.complete()


def test_stu03_ac21_failed_upstream_calls_still_count():
    env = Env(limits=Limits(per_caller_per_minute=2))
    env.script.extend([httpx.Response(400), httpx.Response(400)])
    for _ in range(2):
        with pytest.raises(LlmBadResponse):
            env.complete()
    with pytest.raises(LlmRateLimited):
        env.complete()


# ---------------------------------------------------------------- AC22
def test_stu03_ac22_no_shared_limit_across_callers():
    env = Env()
    for i in range(60):
        env.complete(caller=f"stu-{i}")
    assert env.calls == 60


def test_stu03_ac22_refused_checks_consume_no_slot():
    env = Env(limits=Limits(per_caller_per_minute=2, per_caller_per_day=3))
    env.complete()
    env.complete()
    for _ in range(5):
        with pytest.raises(LlmRateLimited) as info:
            env.complete()
        assert info.value.scope == "student_minute"
    env.now += 61
    env.complete()  # third call of the day: only possible if refusals took no day slot
    env.now += 61
    with pytest.raises(LlmRateLimited) as info:
        env.complete()
    assert info.value.scope == "student_day"
    assert env.calls == 3


def test_stu03_ac22_input_ceiling_and_not_configured_consume_no_slot():
    env = Env(limits=Limits(per_caller_per_minute=1))
    with pytest.raises(LlmInputTooLarge):
        env.complete([ChatMessage("user", "x" * 12_001)])
    env.complete()  # still has its one slot
    assert env.calls == 1
    env2 = Env(settings=Settings(None, None, None), limits=Limits(per_caller_per_minute=1))
    with pytest.raises(LlmNotConfigured):
        env2.complete()


def test_stu03_ac22_thirty_threads_one_caller_admit_exactly_twenty():
    env = Env()
    barrier = threading.Barrier(30)
    outcome = []
    lock = threading.Lock()

    def work():
        barrier.wait(10)
        try:
            env.complete(caller="stu-race")
            result = "ok"
        except LlmRateLimited as exc:
            result = exc.scope
        with lock:
            outcome.append(result)

    threads = [threading.Thread(target=work) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    assert len(outcome) == 30
    assert outcome.count("ok") == 20
    assert outcome.count("student_minute") == 10
    assert env.calls == 20


# ---------------------------------------------------------------- AC23
def test_stu03_ac23_provider_429_with_retry_after():
    env = Env([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json=ok_json())])
    with pytest.raises(LlmBusy) as info:
        env.complete()
    assert info.value.retry_after_seconds == 7
    assert env.calls == 1
    assert env.sleeps == []


@pytest.mark.parametrize("headers", [{}, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, {"Retry-After": "soon"}])
def test_stu03_ac23_provider_429_defaults_to_thirty_seconds(headers):
    env = Env([httpx.Response(429, headers=headers)])
    with pytest.raises(LlmBusy) as info:
        env.complete()
    assert info.value.retry_after_seconds == 30
    assert env.calls == 1


# ---------------------------------------------------------------- AC24
def all_text(exc):
    return " ".join([str(exc), repr(exc), *map(str, exc.args)])


def test_stu03_ac24_key_never_in_exceptions_reprs_or_logs(caplog):
    caplog.set_level(logging.DEBUG)
    user_text = "PRIVATE-STUDENT-TEXT-31337"
    msgs = [ChatMessage("system", "rules"), ChatMessage("user", user_text)]

    def leaky(request):
        raise httpx.ConnectError(f"failed sending {request.headers['authorization']}", request=request)

    scenarios = [
        [leaky, leaky],
        [timeout_error(), timeout_error()],
        [httpx.Response(500, text=f"server echo {KEY}"), httpx.Response(500, text=f"server echo {KEY}")],
        [httpx.Response(401, json={"error": f"invalid key {KEY} for {user_text}"})],
        [httpx.Response(429, text=f"slow down {KEY}")],
        [httpx.Response(200, text=f"not json {KEY}")],
    ]
    for script in scenarios:
        env = Env(script)
        with pytest.raises(LlmError) as info:
            env.complete(msgs)
        text = all_text(info.value)
        assert KEY not in text
        assert user_text not in text
        assert KEY not in repr(env.client)
    # success path and the object reprs
    env = Env([httpx.Response(200, json=ok_json("fine"))])
    reply = env.complete(msgs)
    assert KEY not in repr(reply)
    assert KEY not in repr(Settings(BASE, KEY, MODEL))
    assert KEY not in str(Settings(BASE, KEY, MODEL))
    assert KEY not in caplog.text
    assert user_text not in caplog.text


def test_stu03_ac24_key_missing_error_does_not_name_a_value(caplog):
    caplog.set_level(logging.DEBUG)
    env = Env(settings=Settings(BASE, None, MODEL))
    with pytest.raises(LlmNotConfigured) as info:
        env.complete()
    assert KEY not in all_text(info.value)
    assert KEY not in caplog.text


# ---------------------------------------------------------------- input ceiling
def test_stu03_input_ceiling_over_twelve_thousand_characters():
    env = Env()
    with pytest.raises(LlmInputTooLarge):
        env.complete([ChatMessage("system", "s" * 6000), ChatMessage("user", "u" * 6001)])
    assert env.calls == 0


def test_stu03_input_ceiling_exactly_twelve_thousand_is_allowed():
    env = Env()
    env.complete([ChatMessage("system", "s" * 6000), ChatMessage("user", "u" * 6000)])
    assert env.calls == 1


def test_stu03_input_ceiling_follows_the_limits_setting():
    env = Env(limits=Limits(max_input_chars=10))
    with pytest.raises(LlmInputTooLarge):
        env.complete([ChatMessage("user", "x" * 11)])
    assert env.calls == 0
