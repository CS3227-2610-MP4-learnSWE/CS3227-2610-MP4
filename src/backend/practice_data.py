"""Fixture practice set and answer key. Server-side only; never serialised directly."""
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


@dataclass(frozen=True)
class PracticeSet:
    id: str
    title: str
    questions: tuple[Question, ...]


_SET = PracticeSet(
    id="intro-se-1",
    title="Software engineering basics",
    questions=(
        Question(
            "q1",
            "What should a well-designed function have?",
            None,
            (
                ("a", "A single, focused responsibility"),
                ("b", "As many responsibilities as possible"),
                ("c", "No descriptive name"),
            ),
            "a",
            "One focused responsibility makes a function easier to understand, test and change.",
        ),
        Question(
            "q2",
            "Why do we keep automated tests alongside our code?",
            None,
            (
                ("a", "To make the repository larger"),
                ("b", "To catch regressions when code changes"),
                ("c", "To avoid ever reviewing code"),
            ),
            "b",
            "Tests protect expected behaviour and can catch regressions introduced by later changes.",
        ),
        Question(
            "q3",
            "What does this Python code print?",
            "values = [1, 2, 3]\nprint(len(values))",
            (("a", "2"), ("b", "4"), ("c", "3")),
            "c",
            "len returns the number of items. The list contains three items.",
        ),
    ),
)

PRACTICE_SETS: dict[str, PracticeSet] = {_SET.id: _SET}


def get_set(set_id: str) -> PracticeSet | None:
    return PRACTICE_SETS.get(set_id)
