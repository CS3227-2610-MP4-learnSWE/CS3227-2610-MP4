"""Fixture practice set and answer key. Server-side only; never serialised directly."""
from dataclasses import dataclass

KEY_VERSION = "v1"


@dataclass(frozen=True)
class Choice:
    id: str
    text: str


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    code: str | None
    choices: tuple[Choice, ...]
    correct_choice: str
    explanation: str


@dataclass(frozen=True)
class PracticeSet:
    id: str
    title: str
    questions: tuple[Question, ...]


def _choices(*texts: str) -> tuple[Choice, ...]:
    return tuple(Choice(i, t) for i, t in zip("abc", texts))


PRACTICE_SETS: dict[str, PracticeSet] = {
    "intro-se-1": PracticeSet(
        id="intro-se-1",
        title="Software engineering basics",
        questions=(
            Question(
                "q1",
                "What should a well-designed function have?",
                None,
                _choices(
                    "A single, focused responsibility",
                    "As many responsibilities as possible",
                    "No descriptive name",
                ),
                "a",
                "One focused responsibility makes a function easier to understand, test and change.",
            ),
            Question(
                "q2",
                "Why do we keep automated tests alongside our code?",
                None,
                _choices(
                    "To make the repository larger",
                    "To catch regressions when code changes",
                    "To avoid ever reviewing code",
                ),
                "b",
                "Tests protect expected behaviour and can catch regressions introduced by later changes.",
            ),
            Question(
                "q3",
                "What does this Python code print?",
                "values = [1, 2, 3]\nprint(len(values))",
                _choices("2", "4", "3"),
                "c",
                "len returns the number of items. The list contains three items.",
            ),
        ),
    )
}


def get_set(set_id: str) -> PracticeSet | None:
    return PRACTICE_SETS.get(set_id)
