"""Per-process rate limits on the shared sliding-window limiter, all updated under one lock."""
import threading
import time

from errors import ApiError
from sliding_window import SlidingWindowLimiter

_lock = threading.Lock()
_limiters: dict[tuple[int, int], SlidingWindowLimiter] = {}


def _limiter(limit: int, window: int) -> SlidingWindowLimiter:
    if (limit, window) not in _limiters:
        _limiters[(limit, window)] = SlidingWindowLimiter(limit, window, time.monotonic)
    return _limiters[(limit, window)]


def check(key: str, limit: int, window: int) -> int | None:
    """Seconds to wait, or None when another attempt is allowed. Does not record."""
    with _lock:
        return _limiter(limit, window).retry_after(key)


def record(key: str, limit: int, window: int) -> None:
    with _lock:
        _limiter(limit, window).record(key)


def admit(key: str, limit: int, window: int) -> int | None:
    """Atomic check and record. Returns seconds to wait when the limit is reached (nothing recorded)."""
    with _lock:
        limiter = _limiter(limit, window)
        wait = limiter.retry_after(key)
        if wait is None:
            limiter.record(key)
        return wait


def limited(wait: int) -> ApiError:
    return ApiError(429, "rate_limited", "Too many attempts. Try again later.", retry_after_seconds=wait)
