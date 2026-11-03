"""Per-key sliding-window limiter shared by the LLM client and the auth rate limits."""
import math
from collections import deque
from collections.abc import Callable


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
