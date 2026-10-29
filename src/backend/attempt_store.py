"""Attempt store: an interface plus an in-memory implementation."""
import secrets
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


class InMemoryAttemptStore:
    def __init__(self) -> None:
        self._attempts: dict[str, Attempt] = {}

    def create(self, student_id: str, set_id: str) -> Attempt:
        attempt = Attempt(secrets.token_urlsafe(16), student_id, set_id)
        self._attempts[attempt.id] = attempt
        return attempt

    def get_owned(self, attempt_id: str, student_id: str) -> Attempt | None:
        attempt = self._attempts.get(attempt_id)
        if attempt is None or attempt.student_id != student_id:
            return None
        return attempt


store: AttemptStore = InMemoryAttemptStore()
