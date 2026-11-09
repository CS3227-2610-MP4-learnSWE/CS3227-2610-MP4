"""STU-03-grounding regression tests after verifier FAIL: the NOT_IN_LESSON marker must not hide a
letter or verdict from the leak check (AC14), and must never be visible in any reply (AC15).

Fake LLM and fake lesson provider only. Contract: workflow/specs/STU-03-grounding/{spec,plan}.md.
"""
import unicodedata

import pytest
from companion_helpers import new_student
from grounding_helpers import LESSON_CANNED, LIMITATION, lesson_ask

import companion_service as service
from lesson_provider import LessonText

TITLE = "Closures and scope"
BODY = "A closure remembers variables from the scope where it was created. Scope decides which names are visible."
L1 = LessonText("00000000-0000-4000-8000-000000000001", "Databases", "Tables hold rows.")


def _marker_visible(text: str) -> bool:
    folded = "".join(unicodedata.normalize("NFKC", text).casefold().split())
    return "not_in_lesson" in folded


# ---------------------------------------------------------------- (a) routes: AC14 with a marker inside the statement
MID_STATEMENT_LEAKS = [
    "The answer isNOT_IN_LESSON: b.",
    "The correct one is NOT_IN_LESSON:b",
    "Answer: NOT_IN_LESSON:b",
    "The answerNOT_IN_LESSON: is b.",
    "Option aNOT_IN_LESSON: is wrong.",
    "Option a is NOT_IN_LESSON: wrong.",
    "The answer is not_in_lesson: b.",
    "NOT_IN_LESSON: Option a is wrong.",
    "NOT_IN_LESSON:The correct answer is b.",
    "  NOT_IN_LESSON: the answer is NOT_IN_LESSON: b.",
]


@pytest.mark.usefixtures("fake_provider", "fake_lessons")
@pytest.mark.parametrize("leak", MID_STATEMENT_LEAKS)
def test_stu03_grounding_ac14_marker_inside_a_letter_or_verdict_is_withheld(fake, fake_lessons, leak):
    lid = fake_lessons.add(TITLE, BODY)
    fake.reply = leak
    r = lesson_ask(new_student(), "What is a closure?", lid)
    assert r.status_code == 200, r.text
    assert r.json() == {"reply": LESSON_CANNED, "mode": "lesson", "withheld": True, "sources": []}
    assert not _marker_visible(r.text)


@pytest.mark.usefixtures("fake_provider", "fake_lessons")
@pytest.mark.parametrize(
    "reply",
    ["Closures keep variables. NOT_IN_LESSON: Scope matters.", "NOT_IN_LESSON: Closures keep variables."],
)
def test_stu03_grounding_ac15_marker_in_a_harmless_reply_is_never_returned(fake, fake_lessons, reply):
    lid = fake_lessons.add(TITLE, BODY)
    fake.reply = reply
    r = lesson_ask(new_student(), "What is a closure?", lid)
    assert r.status_code == 200 and r.json()["withheld"] is False
    assert not _marker_visible(r.text)


# ---------------------------------------------------------------- (b) finish_lesson_reply units
def test_stu03_grounding_finish_double_marker_never_leaves_a_marker():
    reply, sources = service.finish_lesson_reply("NOT_IN_LESSON: NOT_IN_LESSON: hi", [L1])
    assert not _marker_visible(reply)
    assert reply.startswith(LIMITATION) and "hi" in reply
    assert sources == []


def test_stu03_grounding_finish_fullwidth_marker_is_the_leading_marker():
    reply, sources = service.finish_lesson_reply("ＮＯＴ＿ＩＮ＿ＬＥＳＳＯＮ： hi", [L1])
    assert reply == f"{LIMITATION} hi"
    assert sources == []


def test_stu03_grounding_finish_bold_marker_gives_limitation():
    reply, sources = service.finish_lesson_reply("**NOT_IN_LESSON:** hi", [L1])
    assert reply.startswith(LIMITATION) and "hi" in reply
    assert not _marker_visible(reply)
    assert sources == []


@pytest.mark.parametrize(
    "text",
    ["Not_In_Lesson: hi", "not_in_lesson:hi", "NOT_IN_LESSON:\n\nhi", " NOT_IN_LESSON:\thi", "NOT_IN_LESSON:   hi"],
)
def test_stu03_grounding_finish_casing_and_spacing_variants_give_limitation(text):
    reply, sources = service.finish_lesson_reply(text, [L1])
    assert reply == f"{LIMITATION} hi"
    assert sources == []


@pytest.mark.parametrize(
    "text",
    [
        "NOT_IN_LESSON:",
        "NOT_IN_LESSON: NOT_IN_LESSON:",
        "NOT_IN_LESSON: NOT_IN_LESSON: hi",
        "ＮＯＴ＿ＩＮ＿ＬＥＳＳＯＮ： hi",
        "**NOT_IN_LESSON:** hi",
        "hi NOT_IN_LESSON: there",
        "hi not_in_lesson: there NOT_IN_LESSON: again",
        "hiＮＯＴ＿ＩＮ＿ＬＥＳＳＯＮ：there",
        "NOT_IN_NOT_IN_LESSON:LESSON: hi",
        "NOT_IN_LESSON:NOT_IN_LESSON:NOT_IN_LESSON:hi",
        "Tables hold rows.",
        "",
    ],
)
def test_stu03_grounding_finish_output_never_contains_the_marker(text):
    reply, _ = service.finish_lesson_reply(text, [L1])
    assert not _marker_visible(reply)


def test_stu03_grounding_finish_marker_in_the_middle_keeps_sources():
    reply, sources = service.finish_lesson_reply("hi ＮＯＴ＿ＩＮ＿ＬＥＳＳＯＮ： there", [L1])
    assert not _marker_visible(reply)
    assert LIMITATION not in reply
    assert sources == [L1]
