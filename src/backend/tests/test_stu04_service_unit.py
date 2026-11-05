"""STU-04 AC3, AC4, AC9, AC10, AC11: build_progress with a fake store and synthetic multi-topic sets.

The plan's signature: build_progress(db, student_id, attempts=store, sets=PRACTICE_SETS) -> ProgressOut.
A real database session is used for the lesson helpers and the topic names (skipped without a database).
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from attempt_store import Attempt, SetSummary
from auth_helpers import new_student
from practice_data import PracticeSet, Question
from progress_service import build_progress
from stu01_helpers import make_course, make_topic


@pytest.fixture
def db():
    if not os.environ.get("TEA01_TEST_DATABASE_URL"):
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        yield session
    engine.dispose()


class FakeStore:
    def __init__(self, summaries):
        self.summaries = summaries
        self.asked = []

    def submitted_summaries(self, student_id):
        self.asked.append(student_id)
        return list(self.summaries)


def q(qid, topic_id):
    return Question(qid, f"Question {qid}?", None, (("a", "A"), ("b", "B")), "a", "Because.", topic_id)


def make_set(set_id, title, questions):
    return PracticeSet(set_id, title, tuple(questions))


def summary(set_id, answered, correct_ids, *, total=None, attempts=1, best=None):
    """A SetSummary whose latest attempt answered `answered` question ids and got `correct_ids` right."""
    latest = Attempt(
        id="a-" + uuid.uuid4().hex[:10], student_id="s", set_id=set_id, status="submitted",
        answers={qid: "a" for qid in answered}, score_correct=len(correct_ids),
        score_total=total if total is not None else len(answered), key_version="v1",
        correct_question_ids=list(correct_ids), submitted_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    b = best if best is not None else (latest.score_correct, latest.score_total)
    return SetSummary(set_id, attempts, b[0], b[1], latest)


def run(db, student, summaries, sets):
    out = build_progress(db, str(student), FakeStore(summaries), sets)
    return out.model_dump(mode="json")


def items_by_name(body):
    return {i["topic"]["name"]: i for i in body["topics"]["items"]}


def test_stu04_ac10_topics_sum_over_the_latest_attempt_of_several_sets(db):
    s = new_student()
    cid = make_course()
    t1, t2 = make_topic(cid, "Alpha topic"), make_topic(cid, "Beta topic")
    sets = {
        "s1": make_set("s1", "Set one", [q("a1", t1), q("a2", t1), q("b1", t2)]),
        "s2": make_set("s2", "Set two", [q("c1", t1), q("c2", t2), q("c3", t2)]),
    }
    body = run(db, s, [
        summary("s1", ["a1", "a2", "b1"], ["a1", "b1"]),
        summary("s2", ["c1", "c2", "c3"], ["c2"]),
    ], sets)
    got = items_by_name(body)
    # Alpha: a1 a2 c1 answered (3), correct a1 (1) -> 33% weak. Beta: b1 c2 c3 (3), correct b1 c2 (2) -> 66% on track
    assert (got["Alpha topic"]["answered"], got["Alpha topic"]["correct"]) == (3, 1)
    assert got["Alpha topic"]["status"] == "needs_practice" and got["Alpha topic"]["accuracy_percent"] == 33
    assert (got["Beta topic"]["answered"], got["Beta topic"]["correct"]) == (3, 2)
    assert got["Beta topic"]["status"] == "on_track" and got["Beta topic"]["accuracy_percent"] == 66
    assert got["Alpha topic"]["topic"]["id"] == t1


def test_stu04_ac4_ac10_fewer_than_three_answers_is_insufficient_not_weak(db):
    s = new_student()
    cid = make_course()
    t = make_topic(cid, "Thin topic")
    sets = {"s1": make_set("s1", "Set", [q("a1", t), q("a2", t), q("a3", t)])}
    body = run(db, s, [summary("s1", ["a1", "a2"], [], total=3)], sets)
    item = items_by_name(body)["Thin topic"]
    assert item["status"] == "insufficient"
    assert (item["answered"], item["correct"], item["accuracy_percent"]) == (2, 0, 0)


def test_stu04_ac10_unanswered_questions_are_not_counted_as_answered(db):
    s = new_student()
    t = make_topic(make_course(), "Partly answered")
    sets = {"s1": make_set("s1", "Set", [q("a1", t), q("a2", t), q("a3", t), q("a4", t)])}
    body = run(db, s, [summary("s1", ["a1", "a2", "a3"], ["a1", "a2", "a3"], total=4)], sets)
    item = items_by_name(body)["Partly answered"]
    assert (item["answered"], item["correct"], item["status"]) == (3, 3, "on_track")


def test_stu04_ac10_ids_that_are_not_in_the_current_set_are_ignored(db):
    s = new_student()
    t = make_topic(make_course(), "Current topic")
    sets = {"s1": make_set("s1", "Set", [q("a1", t), q("a2", t), q("a3", t)])}
    body = run(db, s, [summary("s1", ["a1", "a2", "a3", "gone1", "gone2"], ["a1", "gone1"], total=3)], sets)
    item = items_by_name(body)["Current topic"]
    assert (item["answered"], item["correct"]) == (3, 1)


def test_stu04_ac10_a_question_without_a_topic_and_one_with_an_unknown_topic_count_under_general(db):
    s = new_student()
    unknown = str(uuid.uuid4())
    sets = {"s1": make_set("s1", "Set", [q("a1", None), q("a2", unknown), q("a3", "not-a-uuid")])}
    body = run(db, s, [summary("s1", ["a1", "a2", "a3"], ["a1", "a2"])], sets)
    assert len(body["topics"]["items"]) == 1
    item = body["topics"]["items"][0]
    assert item["topic"] == {"id": None, "name": "General"}
    assert (item["answered"], item["correct"], item["status"]) == (3, 2, "on_track")


def test_stu04_ac10_topic_names_come_from_the_topic_table_not_from_the_fixture(db):
    s = new_student()
    t = make_topic(make_course(), "Name from the table")
    sets = {"s1": make_set("s1", "Set", [q("a1", t), q("a2", t), q("a3", t)])}
    body = run(db, s, [summary("s1", ["a1", "a2", "a3"], ["a1"])], sets)
    assert body["topics"]["items"][0]["topic"] == {"id": t, "name": "Name from the table"}


def test_stu04_ac11_rule_in_the_response_equals_the_constants_of_progress_rules(db):
    import progress_rules

    body = run(db, new_student(), [], {})
    assert body["topics"]["rule"] == {"min_answers": progress_rules.MIN_ANSWERS_FOR_TOPIC,
                                      "weak_below_percent": progress_rules.WEAK_BELOW_PERCENT}


def test_stu04_ac10_topics_are_sorted_by_status_then_accuracy_then_name_then_id(db):
    s = new_student()
    cid = make_course()
    names = ["zeta weak 33", "Alpha weak 33", "Beta weak 0", "ok topic", "thin topic"]
    ids = {n: make_topic(cid, n) for n in names}
    qs, answered, correct = [], [], []
    plan = {"zeta weak 33": (3, 1), "Alpha weak 33": (3, 1), "Beta weak 0": (3, 0), "ok topic": (3, 3),
            "thin topic": (2, 2)}
    for n, (a, c) in plan.items():
        for i in range(a):
            qid = f"{n[:3]}{i}".replace(" ", "")
            qs.append(q(qid, ids[n]))
            answered.append(qid)
            if i < c:
                correct.append(qid)
    body = run(db, s, [summary("s1", answered, correct, total=len(qs))], {"s1": make_set("s1", "Set", qs)})
    assert [i["topic"]["name"] for i in body["topics"]["items"]] == [
        "Beta weak 0", "Alpha weak 33", "zeta weak 33", "ok topic", "thin topic"]
    assert [i["status"] for i in body["topics"]["items"]] == [
        "needs_practice", "needs_practice", "needs_practice", "on_track", "insufficient"]


def test_stu04_ac9_scores_and_average_come_from_the_summaries(db):
    s = new_student()
    sets = {"s1": make_set("s1", "Beta set", [q("a1", None), q("a2", None), q("a3", None)]),
            "s2": make_set("s2", "alpha set", [q("b1", None), q("b2", None)])}
    body = run(db, s, [
        summary("s1", ["a1", "a2", "a3"], ["a1", "a2"], attempts=3, best=(3, 3)),
        summary("s2", ["b1", "b2"], ["b1"], attempts=1),
    ], sets)
    rows = body["practice"]["sets"]
    assert [r["title"] for r in rows] == ["alpha set", "Beta set"]  # case-insensitive A to Z
    beta = rows[1]
    assert beta["attempts_submitted"] == 3
    assert beta["best"] == {"correct": 3, "total": 3}
    assert (beta["latest"]["correct"], beta["latest"]["total"]) == (2, 3)
    assert beta["latest"]["submitted_at"].endswith("Z")
    # mean of latest percentages: (66.66 + 50) / 2 = 58.33 -> floor 58 (exact arithmetic, not a mean of floors)
    assert body["practice"]["average_latest_percent"] == 58


def test_stu04_ac9_average_is_null_without_a_submitted_set_and_floors_two_thirds_to_66(db):
    s = new_student()
    assert run(db, s, [], {})["practice"]["average_latest_percent"] is None
    sets = {"s1": make_set("s1", "Set", [q("a1", None), q("a2", None), q("a3", None)])}
    body = run(db, s, [summary("s1", ["a1", "a2", "a3"], ["a1", "a2"])], sets)
    assert body["practice"]["average_latest_percent"] == 66


def test_stu04_ac9_a_summary_for_a_set_that_no_longer_exists_is_skipped(db):
    s = new_student()
    sets = {"s1": make_set("s1", "Kept", [q("a1", None)])}
    body = run(db, s, [summary("gone", ["x1", "x2", "x3"], ["x1"]), summary("s1", ["a1"], ["a1"])], sets)
    assert [r["set_id"] for r in body["practice"]["sets"]] == ["s1"]
    assert body["practice"]["average_latest_percent"] == 100
    assert all(i["topic"]["name"] == "General" and i["answered"] == 1 for i in body["topics"]["items"])


def test_stu04_ac1_the_store_is_asked_only_for_the_given_student(db):
    s = new_student()
    store = FakeStore([])
    build_progress(db, str(s), store, {})
    assert store.asked == [str(s)]
