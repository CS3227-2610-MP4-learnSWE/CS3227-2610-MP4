"""The weak-topic rule: the only home of its numbers and pure functions (STU-04)."""
from typing import Literal

MIN_ANSWERS_FOR_TOPIC = 3
WEAK_BELOW_PERCENT = 60
RECENT_LESSON_LIMIT = 5

TopicStatus = Literal["needs_practice", "on_track", "insufficient"]


def topic_status(answered: int, correct: int) -> TopicStatus:
    if answered < MIN_ANSWERS_FOR_TOPIC:
        return "insufficient"
    if correct * 100 < WEAK_BELOW_PERCENT * answered:
        return "needs_practice"
    return "on_track"


def accuracy_percent(answered: int, correct: int) -> int:
    return correct * 100 // answered if answered else 0
