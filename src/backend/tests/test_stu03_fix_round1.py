"""STU-03 fix round 1 tests.

Written by the developer in a fix round, NOT by the independent test-designer.
Covers: leak_check letter/verdict/format-character forms, short choices before output words,
a pasted question from another set being leak-checked in hint mode, and a non-ASCII
Retry-After digit.
"""
import httpx
import pytest
from companion_helpers import CANNED, SET_ID, ask, new_student
from leak_check import find_leak
from llm_client import ChatMessage, Limits, LlmBusy, Settings, SoclaasClient
from fake_sets import FIXTURE_SET
from practice_data import PracticeSet, Question
import pytest as _pytest

pytestmark = _pytest.mark.usefixtures("fake_provider")

QS = FIXTURE_SET.questions  # answers q1 a, q2 b, q3 c

MUST_BLOCK = [
    "the answer is **b**",
    "The answer is `b`.",
    'The answer is "b".',
    "The answer is 'b'.",
    "The answer is A because it keeps the function focused.",
    "Option A because focus matters",
    "So the answer is A - one responsibility",
    "It's option A here",
    "Correct: b",
    "Correct answer — b",
    "b looks correct",
    "b seems right",
    "b would be right",
    "b ✓",
    "q1: a, q2: b, q3: c",
    "3 is printed",
    "len(values) is 3",
    "The code shows 3",
    "it gives 3 as output",
    "A single, foc­used responsibility",
    "A single, focused​ responsibility",
    "To catch regres​sions when code changes",
]
MUST_PASS = [
    "Think about what makes a function easy to understand and change.",
    "A good hint is to ask what happens when code changes later.",
    "Look at how many items the list holds.",
    "a function with a clear name",
    "The list [1, 2, 3] is what len looks at.",
]


@pytest.mark.parametrize("reply", MUST_BLOCK)
def test_stu03_fix1_leak_check_blocks(reply):
    assert find_leak(reply, QS) is not None


@pytest.mark.parametrize("reply", MUST_PASS)
def test_stu03_fix1_leak_check_passes_benign(reply):
    assert find_leak(reply, QS) is None


def test_stu03_fix3_pasted_question_from_another_set_is_leak_checked(fake, fake_provider):
    other = Question(
        "z1",
        "Which structure gives first in first out ordering for a print queue?",
        None,
        (("a", "A stack"), ("b", "A queue with enqueue at the tail"), ("c", "A tree")),
        "b",
        "Queues are first in first out.",
    )
    fake_provider.add(PracticeSet("c0000000-0000-4000-8000-000000000002", "Other", (other,)))
    fake.reply = "You want a queue with enqueue at the tail."
    r = ask(new_student(), other.text, page="practice", set_id=SET_ID)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "hint"
    assert body["withheld"] is True
    assert body["reply"] == CANNED


def test_stu03_fix3_other_set_leak_scope_is_not_added_to_context(fake, fake_provider):
    other = Question(
        "z1", "Which structure gives first in first out ordering for a print queue?", None,
        (("a", "A stack"), ("b", "A queue with enqueue at the tail")), "b", "Queues are FIFO.",
    )
    fake_provider.add(PracticeSet("c0000000-0000-4000-8000-000000000002", "Other", (other,)))
    ask(new_student(), other.text, page="practice", set_id=SET_ID)
    assert other.text not in fake.last.all_text.split("Student message:")[0]


@pytest.mark.parametrize("value", ["²", "٣", "7²"])
def test_stu03_fix4_non_ascii_retry_after_falls_back_to_thirty(value):
    def handler(request):
        return httpx.Response(429, headers=[(b"Retry-After", value.encode("utf-8"))])

    client = SoclaasClient(
        Settings("http://llm.test", "k", "m"),
        limits=Limits(),
        transport=httpx.MockTransport(handler),
        clock=lambda: 0.0,
        sleep=lambda s: None,
    )
    with pytest.raises(LlmBusy) as info:
        client.complete([ChatMessage("user", "hi")], max_tokens=10, caller_id="s")
    assert info.value.retry_after_seconds == 30
