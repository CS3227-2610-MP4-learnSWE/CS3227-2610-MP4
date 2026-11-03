"""Per-process rate limits on the shared sliding-window limiter, all updated under one lock."""
import threading
import time

from errors import ApiError
from sliding_window import SlidingWindowLimiter

_lock = threading.Lock()
_limiters: dict[tuple[int, int], SlidingWindowLimiter] = {}
_in_flight: dict[str, int] = {}


def _limiter(limit: int, window: int) -> SlidingWindowLimiter:
    if (limit, window) not in _limiters:
        _limiters[(limit, window)] = SlidingWindowLimiter(limit, window, time.monotonic)
    return _limiters[(limit, window)]


def admit(key: str, limit: int, window: int) -> int | None:
    """Atomic check and record. Returns seconds to wait when the limit is reached (nothing recorded)."""
    with _lock:
        limiter = _limiter(limit, window)
        wait = limiter.retry_after(key)
        if wait is None:
            limiter.record(key)
        return wait


def reserve(attempts: list[tuple[str, int, int]]) -> int | None:
    """Atomically refuse (seconds to wait) or reserve a slot on every (key, limit, window).

    Recorded failures plus attempts still being verified count against the limit, so parallel
    guesses cannot all pass before the first failure is recorded. The first key is checked first
    and a limited key reserves nothing. Pair every success with `settle`.
    """
    with _lock:
        for key, limit, window in attempts:
            limiter = _limiter(limit, window)
            pending = _in_flight.get(key, 0)
            if limiter.count(key) + pending >= limit:
                return limiter.retry_after(key) or 1
        for key, _, _ in attempts:
            _in_flight[key] = _in_flight.get(key, 0) + 1
        return None


def settle(attempts: list[tuple[str, int, int]], failed: bool) -> None:
    """Release the reservation; turn it into a recorded failure when the attempt failed."""
    with _lock:
        for key, limit, window in attempts:
            left = _in_flight.get(key, 0) - 1
            if left > 0:
                _in_flight[key] = left
            else:
                _in_flight.pop(key, None)
            if failed:
                _limiter(limit, window).record(key)


def limited(wait: int) -> ApiError:
    return ApiError(429, "rate_limited", "Too many attempts. Try again later.", retry_after_seconds=wait)
