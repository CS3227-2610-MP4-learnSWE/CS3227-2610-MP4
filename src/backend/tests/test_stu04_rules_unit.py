"""STU-04 AC3, AC4, AC10, AC11: the weak-topic rule as pure functions (progress_rules, no database)."""
import pytest

import progress_rules as rules


def test_stu04_ac11_constants_are_the_documented_numbers():
    assert rules.MIN_ANSWERS_FOR_TOPIC == 3
    assert rules.WEAK_BELOW_PERCENT == 60
    assert rules.RECENT_LESSON_LIMIT == 5


@pytest.mark.parametrize(
    "answered, correct, expected",
    [
        (3, 1, "needs_practice"),   # 33%
        (3, 0, "needs_practice"),
        (3, 2, "on_track"),         # 66%
        (3, 3, "on_track"),
        (5, 3, "on_track"),         # exactly 60% is not weak
        (5, 2, "needs_practice"),   # 40%
        (10, 6, "on_track"),        # exactly 60%
        (10, 5, "needs_practice"),  # 50%
        (100, 59, "needs_practice"),  # 59% is weak
        (100, 60, "on_track"),
        (2, 0, "insufficient"),     # fewer than 3 answers is never weak
        (2, 2, "insufficient"),
        (1, 0, "insufficient"),
        (0, 0, "insufficient"),
    ],
)
def test_stu04_ac10_topic_status_boundaries(answered, correct, expected):
    assert rules.topic_status(answered, correct) == expected


def test_stu04_ac10_status_uses_integer_arithmetic_not_rounded_percent():
    # 59.9% (599 of 1000) must be weak although it displays as 59 and a float round could say 60.
    assert rules.topic_status(1000, 599) == "needs_practice"
    assert rules.topic_status(1000, 600) == "on_track"
    # 7 of 12 is 58.33...% -> weak; 8 of 12 is 66.67% -> on track
    assert rules.topic_status(12, 7) == "needs_practice"
    assert rules.topic_status(12, 8) == "on_track"


@pytest.mark.parametrize(
    "answered, correct, expected",
    [(3, 1, 33), (3, 2, 66), (3, 3, 100), (3, 0, 0), (5, 3, 60), (7, 2, 28), (1000, 599, 59), (0, 0, 0)],
)
def test_stu04_ac10_accuracy_percent_is_floored_and_safe_for_zero(answered, correct, expected):
    assert rules.accuracy_percent(answered, correct) == expected


def test_stu04_ac10_a_displayed_59_is_always_weak_and_a_displayed_60_never_is():
    for answered in range(3, 60):
        for correct in range(0, answered + 1):
            shown = rules.accuracy_percent(answered, correct)
            status = rules.topic_status(answered, correct)
            if shown <= 59:
                assert status == "needs_practice", (answered, correct, shown)
            else:
                assert status == "on_track", (answered, correct, shown)
