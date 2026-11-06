"""Domain types for practice sets and the answer key. Server-side only; never serialised directly."""
from dataclasses import dataclass

KEY_VERSION = "v1"


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    code: str | None
    choices: tuple[tuple[str, str], ...]
    correct: str
    explanation: str
    topic_id: str | None = None


@dataclass(frozen=True)
class PracticeSet:
    id: str
    title: str
    questions: tuple[Question, ...]
