"""STU-03 fix round 2 tests (extra fix beyond the two-round cap).

Written by the developer, NOT by the independent test-designer.
Leak check forms the verifier found still passing, plus false-positive guards.
"""
import pytest
from companion_helpers import SET_ID
from leak_check import find_leak
from practice_data import PRACTICE_SETS

QS = PRACTICE_SETS[SET_ID].questions  # answers q1 a, q2 b, q3 c

MUST_BLOCK = [
    "b is the answer",
    "B is the answer.",
    "The answer is: b",
    "The correct one is b",
    "The right one is b",
    "Answer = b",
    "answer -> b",
    "answer-b",
    "The answer is a because one job is easier to test.",
    "The answer is a since one job is easier to test.",
    "The answer is a, because one job is easier to test.",
    "The answer is a - one job is easier to test.",
    "The answer is a and it keeps things focused.",
    "q1: a, q2: b, q3: c",
    # round 1 strings must keep working
    "the answer is **b**",
    "The answer is A because it keeps the function focused.",
    "Option A because focus matters",
    "So the answer is A - one responsibility",
    "It's option A here",
    "Correct: b",
    "b looks correct",
    "b ✓",
]

MUST_PASS = [
    "For Q1: a good way to think is about change.",
    "Q2 - a test suite runs often.",
    "The answer is a function with one job.",
    "Think about what makes a function easy to understand and change.",
    "A good hint is to ask what happens when code changes later.",
    "Look at how many items the list holds.",
    "a function with a clear name",
]


@pytest.mark.parametrize("reply", MUST_BLOCK)
def test_stu03_fix2_leak_check_blocks(reply):
    assert find_leak(reply, QS) is not None


@pytest.mark.parametrize("reply", MUST_PASS)
def test_stu03_fix2_leak_check_passes(reply):
    assert find_leak(reply, QS) is None
