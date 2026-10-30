"""Shared SoC LLM client: sends chat messages, returns text, with limits and error mapping.

Generic on purpose: it knows nothing about practice sets, modes or leaks. The API key is
only ever placed in the Authorization header; errors carry fixed messages, never the key or
the request body.
"""
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx

MAX_REPLY_CHARS = 2_000
DEFAULT_RETRY_AFTER_SECONDS = 30


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
        self, messages: Sequence[ChatMessage], *, max_tokens: int, caller_id: str
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


class SlidingWindowLimiter:
    """Per-key sliding window. Not locked itself: the client holds one lock around check and record."""

    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float]) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        return hits

    def retry_after(self, key: str) -> int | None:
        """Seconds (at least 1) until a slot frees up, or None if a request is allowed now."""
        now = self._clock()
        hits = self._prune(key, now)
        if len(hits) < self._limit:
            return None
        return max(1, math.ceil(hits[0] + self._window - now))

    def record(self, key: str) -> None:
        now = self._clock()
        self._prune(key, now).append(now)


class SoclaasClient:
    def __init__(
        self,
        settings: Settings,
        *,
        limits: Limits = Limits(),
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._limits = limits
        self._sleep = sleep
        self._lock = threading.Lock()
        self._minute = SlidingWindowLimiter(limits.per_caller_per_minute, 60, clock)
        self._day = SlidingWindowLimiter(limits.per_caller_per_day, 86_400, clock)
        self._http = httpx.Client(transport=transport, timeout=limits.timeout_seconds)

    def complete(
        self, messages: Sequence[ChatMessage], *, max_tokens: int, caller_id: str
    ) -> LlmReply:
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
        response = self._send(url, headers, payload)
        return self._parse(response)

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

    def _send(self, url: str, headers: dict[str, str], payload: dict) -> httpx.Response:
        attempts = self._limits.max_retries + 1
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                response = self._http.post(url, headers=headers, json=payload)
            except httpx.TimeoutException:
                if last:
                    raise LlmTimeout("The model service timed out.") from None
            except httpx.HTTPError:
                if last:
                    raise LlmUpstreamError("The model service could not be reached.") from None
            else:
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

    @staticmethod
    def _parse(response: httpx.Response) -> LlmReply:
        try:
            data = response.json()
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmBadResponse("The model service sent an unusable reply.") from None
        if not isinstance(text, str) or not text.strip():
            raise LlmBadResponse("The model service sent an unusable reply.")
        usage = data.get("usage") if isinstance(data, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        finish = choice.get("finish_reason")
        return LlmReply(
            text=text.strip()[:MAX_REPLY_CHARS],
            finish_reason=finish if isinstance(finish, str) else None,
            prompt_tokens=_int_or_none(usage.get("prompt_tokens")),
            completion_tokens=_int_or_none(usage.get("completion_tokens")),
        )


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _retry_after(response: httpx.Response) -> int:
    raw = response.headers.get("Retry-After", "").strip()
    return max(1, int(raw)) if raw.isdigit() else DEFAULT_RETRY_AFTER_SECONDS


_client: SoclaasClient | None = None
_client_lock = threading.Lock()


def get_llm_client() -> LlmClient:
    """FastAPI dependency: one client built from the environment on first use."""
    global _client
    with _client_lock:
        if _client is None:
            _client = SoclaasClient(Settings.from_env())
        return _client
