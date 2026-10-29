"""Attempt store: an interface plus an in-memory implementation."""
import secrets
import threading
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Attempt:
    id: str
    student_id: str
    set_id: str
    status: str = "in_progress"
    answers: dict[str, str] = field(default_factory=dict)


class AttemptStore(Protocol):
    def create(self, student_id: str, set_id: str) -> Attempt: ...

    def get_owned(self, attempt_id: str, student_id: str) -> Attempt | None:
        """Return the attempt only if it exists and belongs to the student."""
        ...

    def lock(self, attempt_id: str) -> AbstractContextManager:
        """Hold while checking and changing one attempt, so concurrent requests cannot interleave."""
        ...


class InMemoryAttemptStore:
    def __init__(self) -> None:
        self._attempts: dict[str, Attempt] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def create(self, student_id: str, set_id: str) -> Attempt:
        attempt = Attempt(secrets.token_urlsafe(16), student_id, set_id)
        self._attempts[attempt.id] = attempt
        return attempt

    def get_owned(self, attempt_id: str, student_id: str) -> Attempt | None:
        attempt = self._attempts.get(attempt_id)
        if attempt is None or attempt.student_id != student_id:
            return None
        return attempt

    def lock(self, attempt_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(attempt_id, threading.Lock())


store: AttemptStore = InMemoryAttemptStore()
