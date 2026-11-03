"""Per-process rate limits on the shared sliding-window limiter, all updated under one lock."""
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from errors import ApiError
from sliding_window import SlidingWindowLimiter

_lock = threading.Lock()
_limiters: dict[tuple[int, int], SlidingWindowLimiter] = {}
_key_locks: dict[str, list] = {}  # key -> [lock, users]


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


@contextmanager
def serialised(attempts: list[tuple[str, int, int]]) -> Iterator[None]:
    """Hold a per-key lock on every key, taken in sorted order, so attempts on one key run one at a time.

    Inside, `blocked` sees the failures recorded by every earlier attempt, so parallel wrong guesses
    cannot all pass the check first, while correct logins are never counted or refused for others.
    The lock table drops a key's lock when nobody uses it. Always released, also on exceptions.
    """
    keys = sorted({key for key, _, _ in attempts})
    held: list[threading.Lock] = []
    with _lock:
        for key in keys:
            entry = _key_locks.setdefault(key, [threading.Lock(), 0])
            entry[1] += 1
    try:
        for key in keys:
            lock = _key_locks[key][0]
            lock.acquire()
            held.append(lock)
        yield
    finally:
        for lock in reversed(held):
            lock.release()
        with _lock:
            for key in keys:
                entry = _key_locks[key]
                entry[1] -= 1
                if entry[1] == 0:
                    del _key_locks[key]


def blocked(attempts: list[tuple[str, int, int]]) -> int | None:
    """Seconds to wait when any key has reached its limit of recorded failures; nothing is recorded."""
    with _lock:
        waits = [w for key, limit, window in attempts if (w := _limiter(limit, window).retry_after(key)) is not None]
    return max(waits) if waits else None


def record_failure(attempts: list[tuple[str, int, int]]) -> None:
    with _lock:
        for key, limit, window in attempts:
            _limiter(limit, window).record(key)


def limited(wait: int) -> ApiError:
    return ApiError(429, "rate_limited", "Too many attempts. Try again later.", retry_after_seconds=wait)
