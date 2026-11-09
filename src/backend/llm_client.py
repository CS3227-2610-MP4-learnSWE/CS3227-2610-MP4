"""Shared SoC LLM client: sends chat messages, returns text, with limits and error mapping.

Generic on purpose: it knows nothing about practice sets, modes or leaks. The API key is
only ever placed in the Authorization header; errors carry fixed messages, never the key or
the request body.
"""
import os
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx

from sliding_window import SlidingWindowLimiter

MAX_REPLY_CHARS = 2_000
DEFAULT_RETRY_AFTER_SECONDS = 30
_usage_feature: ContextVar[str] = ContextVar("ai_usage_feature", default="STU-03")


@contextmanager
def usage_feature(feature: str):
    """Server-owned attribution scoped to one call, safe across threads/tasks."""
    if feature not in ("STU-03", "TEA-02", "ADM-03", "ADM-01"):
        raise ValueError("Unsupported AI feature.")
    token = _usage_feature.set(feature)
    try:
        yield
    finally:
        _usage_feature.reset(token)



@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class LlmReply:
    text: str
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None


class LlmClient(Protocol):
    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int,
        caller_id: str,
        timeout_seconds: float | None = None,
        max_reply_chars: int | None = None,
        reasoning_effort: str | None = None,
    ) -> LlmReply: ...


@dataclass(frozen=True)
class Limits:
    per_caller_per_minute: int = 20
    per_caller_per_day: int = 300
    timeout_seconds: float = 15.0
    max_retries: int = 1
    retry_delay_seconds: float = 0.5
    max_input_chars: int = 12_000


@dataclass(frozen=True)
class Settings:
    base_url: str | None
    # repr=False so the key cannot reach a log line through repr().
    api_key: str | None = field(repr=False)
    model: str | None

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ

        def read(name: str) -> str | None:
            return (env.get(name) or "").strip() or None

        return cls(read("SOCLAAS_BASE_URL"), read("SOCLAAS_API_KEY"), read("SOCLAAS_MODEL"))

    @property
    def complete(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class LlmError(Exception):
    """Base class. Messages are fixed text only."""


class LlmNotConfigured(LlmError):
    pass


class LlmInputTooLarge(LlmError):
    pass


class LlmRateLimited(LlmError):
    def __init__(self, scope: str, retry_after_seconds: int) -> None:
        super().__init__("Rate limit reached.")
        self.scope = scope
        self.retry_after_seconds = retry_after_seconds


class LlmBusy(LlmError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("The model service is busy.")
        self.retry_after_seconds = retry_after_seconds


class LlmTimeout(LlmError):
    pass


class LlmUpstreamError(LlmError):
    pass


class LlmBadResponse(LlmError):
    pass


class LlmReplyCutOff(LlmBadResponse):
    """No content at all and finish_reason "length": the model used its whole token budget (reasoning) before answering."""


class SoclaasClient:
    def __init__(
        self,
        settings: Settings,
        *,
        limits: Limits = Limits(),
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        observer=None,
    ) -> None:
        self._observer = observer
        self._settings = settings
        self._limits = limits
        self._sleep = sleep
        self._lock = threading.Lock()
        self._minute = SlidingWindowLimiter(limits.per_caller_per_minute, 60, clock)
        self._day = SlidingWindowLimiter(limits.per_caller_per_day, 86_400, clock)
        self._http = httpx.Client(transport=transport, timeout=limits.timeout_seconds)

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        max_tokens: int,
        caller_id: str,
        timeout_seconds: float | None = None,
        max_reply_chars: int | None = None,
        reasoning_effort: str | None = None,
    ) -> LlmReply:
        """Optional per-call overrides; None keeps the defaults (and sends nothing extra).

        `reasoning_effort` is sent as the request-body field of that name only when set.

        `timeout_seconds` replaces `Limits.timeout_seconds` for this call's attempts. `max_reply_chars` replaces
        MAX_REPLY_CHARS, the length at which the reply text is cut (a structured JSON reply must not be cut).
        """
        s = self._settings
        if not s.complete:
            raise LlmNotConfigured("The model service is not configured.")
        if sum(len(m.content) for m in messages) > self._limits.max_input_chars:
            raise LlmInputTooLarge("The request is too large.")
        self._admit(caller_id)
        url = f"{s.base_url.rstrip('/')}/chat/completions"  # type: ignore[union-attr]
        headers = {"Authorization": f"Bearer {s.api_key}"}
        payload = {
            "model": s.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        response = self._send(url, headers, payload, timeout_seconds)
        return self._parse(response, max_reply_chars or MAX_REPLY_CHARS)

    def _admit(self, caller_id: str) -> None:
        with self._lock:
            wait = self._minute.retry_after(caller_id)
            if wait is not None:
                raise LlmRateLimited("student_minute", wait)
            wait = self._day.retry_after(caller_id)
            if wait is not None:
                raise LlmRateLimited("student_day", wait)
            self._minute.record(caller_id)
            self._day.record(caller_id)

    def _send(
        self, url: str, headers: dict[str, str], payload: dict, timeout_seconds: float | None = None
    ) -> httpx.Response:
        attempts = self._limits.max_retries + 1
        extra = {} if timeout_seconds is None else {"timeout": timeout_seconds}
        for attempt in range(attempts):
            last = attempt == attempts - 1
            attempt_id = self._reserve()
            try:
                response = self._http.post(url, headers=headers, json=payload, **extra)
                if "reasoning_effort" in payload and response.status_code in (400, 422):
                    # The gateway rejected the optional field (some models do): retry once without it, accounted
                    # like any other attempt (own reservation).
                    self._finish(attempt_id, "other_failure", response)
                    payload = {k: v for k, v in payload.items() if k != "reasoning_effort"}
                    attempt_id = self._reserve()
                    response = self._http.post(url, headers=headers, json=payload, **extra)
            except httpx.TimeoutException:
                self._finish(attempt_id, "other_failure")
                if last:
                    raise LlmTimeout("The model service timed out.") from None
            except httpx.HTTPError:
                self._finish(attempt_id, "other_failure")
                if last:
                    raise LlmUpstreamError("The model service could not be reached.") from None
            else:
                outcome = ("success" if 200 <= response.status_code < 300 else
                           "rate_limit" if response.status_code == 429 else "other_failure")
                self._finish(attempt_id, outcome, response)
                if response.status_code == 429:
                    raise LlmBusy(_retry_after(response)) from None
                if response.status_code >= 500:
                    if last:
                        raise LlmUpstreamError("The model service failed.") from None
                elif response.status_code >= 400 or response.status_code < 200:
                    raise LlmBadResponse("The model service rejected the request.") from None
                else:
                    return response
            self._sleep(self._limits.retry_delay_seconds)
        raise LlmUpstreamError("The model service failed.")  # unreachable

    def _reserve(self):
        if self._observer is None:
            return None
        try:
            return self._observer.reserve(_usage_feature.get())
        except Exception:
            # Fail closed before dispatch; never log database/provider details.
            raise LlmUpstreamError("The model service could not be reached.") from None

    def _finish(self, attempt_id, outcome: str, response: httpx.Response | None = None) -> None:
        if self._observer is None:
            return
        try:
            data = response.json() if response is not None else None
        except (ValueError, TypeError, RecursionError):
            data = None
        usage = data.get("usage") if isinstance(data, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        fields = {}
        for target, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens"),
                               ("total_tokens", "total_tokens")):
            value = usage.get(source)
            fields[target] = value if type(value) is int and 0 <= value <= 2**63 - 1 else None
        try:
            self._observer.finish(attempt_id, outcome, **fields)
        except Exception:
            # Reservation remains pending, making the report explicitly unavailable.
            pass

    @staticmethod
    def _parse(response: httpx.Response, max_chars: int = MAX_REPLY_CHARS) -> LlmReply:
        try:
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmBadResponse("The model service sent an unusable reply.") from None
        if not isinstance(text, str) or not text.strip():
            if choice.get("finish_reason") == "length":
                raise LlmReplyCutOff("The model used its whole token budget before answering.")
            raise LlmBadResponse("The model service sent an unusable reply.")
        usage = data.get("usage") if isinstance(data, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        finish = choice.get("finish_reason")
        return LlmReply(
            text=text.strip()[:max_chars],
            finish_reason=finish if isinstance(finish, str) else None,
            prompt_tokens=_int_or_none(usage.get("prompt_tokens")),
            completion_tokens=_int_or_none(usage.get("completion_tokens")),
        )


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _retry_after(response: httpx.Response) -> int:
    raw = response.headers.get("Retry-After", "").strip()
    return max(1, int(raw)) if raw.isascii() and raw.isdigit() else DEFAULT_RETRY_AFTER_SECONDS


_client: SoclaasClient | None = None
_client_lock = threading.Lock()


def get_llm_client() -> LlmClient:
    """FastAPI dependency: one client built from the environment on first use."""
    global _client
    with _client_lock:
        if _client is None:
            from ai_usage.observer import DatabaseAttemptObserver
            _client = SoclaasClient(Settings.from_env(), observer=DatabaseAttemptObserver())
        return _client
