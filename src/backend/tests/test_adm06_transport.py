"""ADM-06 independent observer contract; transport is always mocked."""
from concurrent.futures import ThreadPoolExecutor
import threading
from uuid import uuid4

import httpx
import pytest

from llm_client import (ChatMessage, Limits, Settings, SoclaasClient, LlmBadResponse,
                        LlmBusy, LlmInputTooLarge, LlmNotConfigured, LlmRateLimited,
                        LlmTimeout, LlmUpstreamError)

SECRET = "ADM06-PRIVATE-PROMPT-SECRET"
MESSAGES = [ChatMessage("user", SECRET)]


class Observer:
    def __init__(self, reserve_error=False, finish_error=False):
        self.reserved, self.finished = [], []
        self.reserve_error, self.finish_error = reserve_error, finish_error
        self.lock = threading.Lock()

    def reserve(self, feature):
        if self.reserve_error:
            raise RuntimeError(SECRET)
        aid = uuid4()
        with self.lock:
            self.reserved.append((aid, feature))
        return aid

    def finish(self, aid, outcome, **measurements):
        if self.finish_error:
            raise RuntimeError(SECRET)
        with self.lock:
            self.finished.append((aid, outcome, measurements))
        return True


def make_client(script=None, observer=None, limits=None, settings=None):
    observer = observer or Observer()
    script = list(script or [httpx.Response(200, json=body())])
    requests = []

    def send(request):
        assert len(observer.reserved) > len(requests), "dispatch must follow durable reservation"
        requests.append(request)
        result = script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    client = SoclaasClient(settings or Settings("https://soc.example.test/v1", "test-only-key", "test"),
                           transport=httpx.MockTransport(send), observer=observer,
                           limits=limits or Limits(), sleep=lambda _: None)
    return client, observer, requests


def body(usage=None):
    return {"choices": [{"message": {"content": "Safe answer"}, "finish_reason": "stop"}],
            "usage": usage or {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 99}}


def invoke(client, caller="test-student"):
    return client.complete(MESSAGES, max_tokens=30, caller_id=caller)


def test_adm06_ac1_3_retry_is_separate_attempt_with_rate_limit_category():
    client, observer, requests = make_client([httpx.Response(503), httpx.Response(429)])
    with pytest.raises(LlmBusy):
        invoke(client)
    assert len(requests) == len(observer.reserved) == len(observer.finished) == 2
    assert observer.reserved[0][0] != observer.reserved[1][0]
    assert [x[1] for x in observer.finished] == ["other_failure", "rate_limit"]
    assert [x[0] for x in observer.finished] == [x[0] for x in observer.reserved]


@pytest.mark.parametrize("responses,error,outcomes", [
    ([httpx.ReadTimeout("private"), httpx.ReadTimeout("private")], LlmTimeout, ["other_failure"] * 2),
    ([httpx.ConnectError("private"), httpx.Response(200, json=body())], None, ["other_failure", "success"]),
    ([httpx.Response(400)], LlmBadResponse, ["other_failure"]),
    ([httpx.Response(302)], LlmBadResponse, ["other_failure"]),
    ([httpx.Response(200, json={"choices": []})], LlmBadResponse, ["success"]),
    ([httpx.Response(200, content="bad-json")], LlmBadResponse, ["success"]),
])
def test_adm06_ac1_12_each_transport_outcome_recorded_before_parsing(responses, error, outcomes):
    client, observer, requests = make_client(responses)
    if error:
        with pytest.raises(error):
            invoke(client)
    else:
        invoke(client)
    assert [x[1] for x in observer.finished] == outcomes
    assert len(requests) == len(observer.reserved) == len(outcomes)


def test_adm06_ac7_9_provider_counters_are_independent_recorded_values():
    client, observer, _ = make_client()
    invoke(client)
    assert observer.finished[0][2] == {"input_tokens": 11, "output_tokens": 7, "total_tokens": 99}
    assert SECRET not in str(observer.reserved) + str(observer.finished)


@pytest.mark.parametrize("value", [None, -1, True, False, "15", 1.5, 2**63, {}, []])
def test_adm06_ac8_invalid_provider_measurements_never_become_observed_tokens(value):
    client, observer, _ = make_client([httpx.Response(200, json=body({
        "prompt_tokens": value, "completion_tokens": 0, "total_tokens": value}))])
    invoke(client)
    assert observer.finished[0][2] == {"input_tokens": None, "output_tokens": 0, "total_tokens": None}


def test_adm06_ac8_missing_total_is_not_derived_from_other_counters():
    client, observer, _ = make_client([httpx.Response(200, json=body({"prompt_tokens": 5, "completion_tokens": 3}))])
    invoke(client)
    assert observer.finished[0][2] == {"input_tokens": 5, "output_tokens": 3, "total_tokens": None}


def test_adm06_ac12_reservation_failure_blocks_transport_and_has_safe_error():
    client, observer, requests = make_client(observer=Observer(reserve_error=True))
    with pytest.raises(LlmUpstreamError) as error:
        invoke(client)
    assert requests == [] and observer.finished == []
    assert SECRET not in str(error.value)


def test_adm06_ac12_finalisation_failure_keeps_provider_result_and_no_content_logs(caplog):
    client, observer, requests = make_client(observer=Observer(finish_error=True))
    assert invoke(client).text == "Safe answer"
    assert len(requests) == len(observer.reserved) == 1 and observer.finished == []
    assert SECRET not in caplog.text


def test_adm06_ac1_local_validation_configuration_and_quota_rejections_are_not_attempts():
    client, observer, requests = make_client(limits=Limits(per_caller_per_minute=1))
    invoke(client)
    with pytest.raises(LlmRateLimited):
        invoke(client)
    with pytest.raises(LlmInputTooLarge):
        client.complete([ChatMessage("user", "x" * 12001)], max_tokens=20, caller_id="other")
    assert len(requests) == len(observer.reserved) == 1
    empty, empty_observer, _ = make_client(settings=Settings(None, None, None))
    with pytest.raises(LlmNotConfigured):
        invoke(empty)
    assert empty_observer.reserved == []


def test_adm06_ac12_context_is_server_owned_nested_reset_and_thread_isolated():
    from llm_client import usage_feature

    observer = Observer()
    barrier = threading.Barrier(2)

    def run(feature):
        client, _, _ = make_client(observer=observer)
        with usage_feature(feature):
            barrier.wait(timeout=5)
            invoke(client, feature)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, ["STU-03", "TEA-02"]))
    assert sorted(x[1] for x in observer.reserved) == ["STU-03", "TEA-02"]
    client, nested, _ = make_client([httpx.Response(200, json=body())] * 3)
    with usage_feature("TEA-02"):
        invoke(client)
        with usage_feature("STU-03"):
            invoke(client)
    invoke(client)
    assert [x[1] for x in nested.reserved] == ["TEA-02", "STU-03", "STU-03"]


def test_adm06_ac12_both_teacher_generation_paths_bind_tea02_context():
    from teacher_notes.generation import generate_notes
    from teacher_mcqs.generation import generate_mcqs
    from errors import ApiError

    client, observer, _ = make_client([httpx.Response(200, json=body())] * 2)
    assert generate_notes(client, "source", "teacher-id") == "Safe answer"
    with pytest.raises(ApiError):
        generate_mcqs(client, "source", "teacher-id")
    assert [x[1] for x in observer.reserved] == ["TEA-02", "TEA-02"]
    # Invalid question content is a feature failure, but both services returned HTTP 200.
    assert [x[1] for x in observer.finished] == ["success", "success"]


def test_adm06_ac12_production_dependency_injects_durable_observer(monkeypatch):
    import llm_client
    from ai_usage import service

    observer = Observer()
    monkeypatch.setenv("SOCLAAS_BASE_URL", "https://soc.example.test/v1")
    monkeypatch.setenv("SOCLAAS_API_KEY", "mock-key-no-live-use")
    monkeypatch.setenv("SOCLAAS_MODEL", "mock-model")
    monkeypatch.setattr(llm_client, "_client", None)
    monkeypatch.setattr(service, "reserve_attempt", observer.reserve)
    monkeypatch.setattr(service, "finish_attempt", observer.finish)
    client = llm_client.get_llm_client()
    monkeypatch.setattr(client._http, "post", lambda *a, **kw: httpx.Response(200, json=body()))
    invoke(client)
    assert len(observer.reserved) == len(observer.finished) == 1
    assert observer.reserved[0][1] == "STU-03"
    client._http.close()
