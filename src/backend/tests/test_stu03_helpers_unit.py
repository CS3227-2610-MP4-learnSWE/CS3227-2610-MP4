"""STU-03 pure helpers: question_match.find_match and leak_check.find_leak.

Uses the real fixture set intro-se-1 through practice_data.get_set (the plan names
PracticeSet and Question as the existing types). Attribute names text, code, id and
choices[].text are the ones the read API exposes (STU-02 AC1).
"""
import practice_data
import pytest
from leak_check import find_leak
from question_match import find_match

SET = practice_data.get_set("intro-se-1")
SETS = [SET]
Q1, Q2, Q3 = SET.questions


def matched_id(message, sets=SETS):
    q = find_match(message, sets)
    return None if q is None else q.id


# ------------------------------------------------------------------ find_match
@pytest.mark.parametrize(
    "message,qid",
    [
        ("What should a well-designed function have?", "q1"),
        ("  WHAT   should a well-designed\n function    HAVE?  ", "q1"),
        ("> **“What should a well-designed function have?”**", "q1"),
        ("`What should a well-designed function have?`", "q1"),
        ("hey, stuck here: Why do we keep automated tests alongside our code? any idea?", "q2"),
        ("Why do we keep automated tests alongside our code?\na) To make the repository larger\nb) To catch regressions when code changes", "q2"),
        ("What does this Python code print?\nvalues = [1, 2, 3]\nprint(len(values))", "q3"),
        # two choice texts without the stem
        ("is it to make the repository larger or to catch regressions when code changes?", "q2"),
        # nearly all words of the stem, reordered (>= 80 percent)
        ("function have well-designed should What a", "q1"),
        # full-width characters are folded by NFKC
        ("Ｗhat should a well-designed function have?", "q1"),
    ],
)
def test_stu03_find_match_matches(message, qid):
    assert matched_id(message) == qid


@pytest.mark.parametrize(
    "message",
    [
        "what is a function?",
        "How do I use this app?",
        "Explain recursion to me",
        "What should I study today?",
        "No descriptive name",  # one choice alone is not enough
        "",
        "   ",
    ],
)
def test_stu03_find_match_does_not_match_generic_messages(message):
    assert matched_id(message) is None


def test_stu03_find_match_empty_sets():
    assert find_match("What should a well-designed function have?", []) is None


def test_stu03_find_match_searches_every_set_in_the_sequence():
    assert matched_id(Q2.text, [SET, SET]) == "q2"


def test_stu03_find_match_returns_a_question_from_the_given_sets():
    q = find_match(Q1.text, SETS)
    assert q is not None and q.text == Q1.text


# ------------------------------------------------------------------ find_leak
QS = list(SET.questions)
MUST_BLOCK = [
    "The answer is b.",
    "Option B is correct.",
    "choice (c)",
    "a) is right",
    "b is the right choice",
    "A single, focused responsibility",
    "To catch regressions when code changes",
    "Go for 'to catch regressions when code changes' here.",
    "It prints 3.",
    "Options a and c are wrong",
    "'No descriptive name' is incorrect",
    "THE ANSWER IS B.",
    "**Option B** is correct",
    "the answer is ｂ",
    "(a) is the one you want",
]
MUST_PASS = [
    "Think about what makes a function easy to understand and change.",
    "A good hint is to ask what happens when code changes later.",
    "Look at how many items the list holds.",
    "a function with a clear name",
    "What have you tried so far, and which part of the code is unclear?",
    "A test is a small program that checks another program.",
]


@pytest.mark.parametrize("reply", MUST_BLOCK)
def test_stu03_find_leak_blocks(reply):
    reason = find_leak(reply, QS)
    assert reason in {"letter", "text", "verdict"}, reply


@pytest.mark.parametrize("reply", MUST_PASS)
def test_stu03_find_leak_passes(reply):
    assert find_leak(reply, QS) is None, reply


@pytest.mark.parametrize("q", QS, ids=["q1", "q2", "q3"])
@pytest.mark.parametrize("reply", MUST_PASS)
def test_stu03_find_leak_passes_for_each_single_question(q, reply):
    assert find_leak(reply, [q]) is None


def test_stu03_find_leak_article_a_is_not_a_letter_reference():
    assert find_leak("Write a function and give a name to a variable.", QS) is None


def test_stu03_find_leak_numeric_choice_only_matters_near_output_words():
    # "3" alone in ordinary prose must not trigger; the 3 near an output word must.
    assert find_leak("Split the problem into 3 small steps.", [Q3]) is None
    assert find_leak("The output is 3.", [Q3]) is not None
    assert find_leak("It returns 3", [Q3]) is not None


def test_stu03_find_leak_is_pure_and_repeatable():
    first = find_leak("The answer is b.", QS)
    assert find_leak("The answer is b.", QS) == first
    assert find_leak(MUST_PASS[0], QS) is None
