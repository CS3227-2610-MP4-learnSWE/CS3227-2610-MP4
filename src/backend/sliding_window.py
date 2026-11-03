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
        """Live hits for the key. Reads create nothing; a key with no live hits is dropped."""
        hits = self._hits.get(key)
        if hits is None:
            return deque()
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return deque()
        return hits

    def count(self, key: str) -> int:
        """Hits currently inside the window."""
        return len(self._prune(key, self._clock()))

    def retry_after(self, key: str) -> int | None:
        """Seconds (at least 1) until a slot frees up, or None if a request is allowed now."""
        now = self._clock()
        hits = self._prune(key, now)
        if len(hits) < self._limit:
            return None
        return max(1, math.ceil(hits[0] + self._window - now))

    def record(self, key: str) -> None:
        now = self._clock()
        self._prune(key, now)
        self._hits.setdefault(key, deque()).append(now)
