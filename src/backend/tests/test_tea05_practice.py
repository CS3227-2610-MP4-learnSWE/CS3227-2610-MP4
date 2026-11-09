"""TEA-05 practice figures and commonly missed questions (AC4, AC7, AC8)."""
import pytest

from fake_sets import FIXTURE_SET_ID
from published_sets import question_set
from tea05_helpers import (MISSED_KEYS, attempt, enroll, make_course, make_topic, miss_counts, only_course,
                           published_set, report, roster, set_clock, student_row, teacher_with_course, unenroll)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    set_clock(monkeypatch)


def sets_by_title(course):
    return {s["title"]: s for s in course["practice"]["sets"]}


# ---------- AC7 sets ----------

def test_tea05_ac7_sets_are_listed_by_lower_title_then_id_with_zero_values_and_null_average():
    teacher, course = teacher_with_course()
    roster(course, 2)
    ids = {t: published_set(course, t) for t in ("beta set", "Alpha set", "Zulu set")}
    got = only_course(report(teacher))["practice"]
    assert [s["title"] for s in got["sets"]] == ["Alpha set", "beta set", "Zulu set"]
    assert got["missed_questions"] == []
    for s in got["sets"]:
        assert set(s) == {"set_id", "title", "topic", "students_attempted", "submitted_attempts", "average_score_percent"}
        assert (s["students_attempted"], s["submitted_attempts"], s["average_score_percent"]) == (0, 0, None)
        assert s["set_id"] == ids[s["title"]]


def test_tea05_ac7_set_topic_is_the_topic_name():
    teacher, course = teacher_with_course()
    published_set(course, "Named topic", topic_name="Testing")
    assert only_course(report(teacher))["practice"]["sets"][0]["topic"] == "Testing"


def test_tea05_ac7_course_without_sets_has_empty_practice():
    teacher, course = teacher_with_course()
    roster(course, 2)
    assert only_course(report(teacher))["practice"] == {"sets": [], "missed_questions": []}


def test_tea05_ac7_counts_latest_attempt_average_and_ignores_in_progress():
    teacher, course = teacher_with_course()
    s1, s2, s3 = roster(course, 3)
    sid = published_set(course, "P")
    attempt(s1, sid, correct=[], when="2026-11-04T10:00:00Z")  # superseded
    attempt(s1, sid, correct=[1, 2, 3], when="2026-11-05T10:00:00Z")  # latest: 3/3
    attempt(s2, sid, correct=[1], when="2026-11-06T10:00:00Z")  # 1/3
    attempt(s3, sid, correct=[1, 2, 3], status="in_progress")
    row = sets_by_title(only_course(report(teacher)))["P"]
    assert row["students_attempted"] == 2
    assert row["submitted_attempts"] == 3
    assert row["average_score_percent"] == 66  # (3 + 1) / (3 + 3) floored


def test_tea05_ac7_average_is_pooled_and_floored_and_zero_is_not_null():
    teacher, course = teacher_with_course()
    (s1,) = roster(course, 1)
    sid = published_set(course, "Zero")
    attempt(s1, sid, correct=[])
    assert sets_by_title(only_course(report(teacher)))["Zero"]["average_score_percent"] == 0
    s2, s3 = roster(course, 2)
    sid2 = published_set(course, "Floor")
    attempt(s2, sid2, correct=[1, 2])
    attempt(s3, sid2, correct=[])
    assert sets_by_title(only_course(report(teacher)))["Floor"]["average_score_percent"] == 33  # 2 of 6


def test_tea05_ac7_latest_attempt_is_by_submit_time_then_sequence():
    teacher, course = teacher_with_course()
    s1, s2 = roster(course, 2)
    sid = published_set(course, "Ties")
    t = "2026-11-05T10:00:00Z"
    attempt(s1, sid, correct=[1, 2, 3], when=t)
    attempt(s1, sid, correct=[], when=t)  # same instant, later sequence: latest
    attempt(s2, sid, correct=[], when="2026-11-06T10:00:00Z")  # inserted first by sequence, later by time
    attempt(s2, sid, correct=[1, 2, 3], when="2026-11-05T10:00:00Z")  # later sequence, earlier time
    row = sets_by_title(only_course(report(teacher)))["Ties"]
    assert row["submitted_attempts"] == 4
    assert row["average_score_percent"] == 0  # s1 latest 0/3, s2 latest 0/3


def test_tea05_ac7_attempts_outside_the_period_are_ignored_and_latest_is_taken_inside_it():
    teacher, course = teacher_with_course()
    s1, s2 = roster(course, 2)
    sid = published_set(course, "Window")
    attempt(s1, sid, correct=[1, 2, 3], when="2026-10-20T10:00:00Z")  # 30d only
    attempt(s1, sid, correct=[], when="2026-11-05T10:00:00Z")
    attempt(s2, sid, correct=[1, 2, 3], when="2026-11-10T00:00:00Z")  # at end: outside every period
    attempt(s2, sid, correct=[1, 2, 3], when="2025-02-01T00:00:00Z")  # all only
    rows = {p: sets_by_title(only_course(report(teacher, p)))["Window"] for p in ("7d", "30d", "all")}
    assert (rows["7d"]["students_attempted"], rows["7d"]["submitted_attempts"], rows["7d"]["average_score_percent"]) == (1, 1, 0)
    assert (rows["30d"]["students_attempted"], rows["30d"]["submitted_attempts"], rows["30d"]["average_score_percent"]) == (1, 2, 0)
    assert (rows["all"]["students_attempted"], rows["all"]["submitted_attempts"], rows["all"]["average_score_percent"]) == (2, 3, 50)


def test_tea05_ac7_removed_students_and_non_members_do_not_count_disabled_do():
    teacher, course = teacher_with_course()
    sid = published_set(course, "Roster")
    stay, leave = roster(course, 2)
    disabled = student_row(course, status="disabled")
    outsider = student_row()
    for s in (stay, leave, disabled, outsider):
        attempt(s, sid, correct=[1, 2, 3])
    unenroll(leave, course)
    attempt(str(teacher), sid, correct=[1, 2, 3])  # teacher members are not students
    row = sets_by_title(only_course(report(teacher)))["Roster"]
    assert (row["students_attempted"], row["submitted_attempts"], row["average_score_percent"]) == (2, 2, 100)


def test_tea05_ac7_attempts_on_non_published_sets_are_ignored():
    teacher, course = teacher_with_course()
    (student,) = roster(course, 1)
    sid = published_set(course, "Real")
    from stu04_helpers import insert_attempt
    insert_attempt(student, answers={"q1": "a", "q2": "b", "q3": "c"}, correct_ids=["q1", "q2", "q3"], set_id=FIXTURE_SET_ID)
    insert_attempt(student, answers={"q1": "a"}, correct_ids=[], set_id="builtin-sample")
    row = sets_by_title(only_course(report(teacher)))["Real"]
    assert (row["students_attempted"], row["submitted_attempts"], row["average_score_percent"]) == (0, 0, None)
    assert only_course(report(teacher))["practice"]["missed_questions"] == []



def test_tea05_ac7_other_courses_sets_do_not_mix():
    teacher, course = teacher_with_course()
    other = make_course("TEA05 other")
    enroll(teacher, other)
    shared = student_row(course)
    enroll(shared, other)
    mine, theirs = published_set(course, "Mine"), published_set(other, "Theirs")
    attempt(shared, theirs, correct=[1, 2, 3])
    courses = {c["course_id"]: c for c in report(teacher)["courses"]}
    assert courses[course]["practice"]["sets"][0]["submitted_attempts"] == 0
    assert courses[other]["practice"]["sets"][0]["submitted_attempts"] == 1
    assert mine


# ---------- AC4 empty states are visible in the data ----------

def test_tea05_ac4_no_attempts_gives_no_missed_questions():
    teacher, course = teacher_with_course()
    roster(course, 3)
    published_set(course, "Quiet")
    got = only_course(report(teacher))["practice"]
    assert got["missed_questions"] == []
    assert got["sets"][0]["submitted_attempts"] == 0


def test_tea05_ac4_attempts_without_misses_give_an_empty_list_but_non_zero_counts():
    teacher, course = teacher_with_course()
    s1, s2 = roster(course, 2)
    sid = published_set(course, "Perfect")
    attempt(s1, sid, correct=[1, 2, 3])
    attempt(s2, sid, correct=[1, 2, 3])
    got = only_course(report(teacher))["practice"]
    assert got["missed_questions"] == []
    assert got["sets"][0]["submitted_attempts"] == 2


# ---------- AC8 missed questions ----------

def test_tea05_ac8_item_shape_text_and_floor():
    teacher, course = teacher_with_course()
    students = roster(course, 3)
    sid = published_set(course, "Shape", question_set((0, 0, 0)))
    miss_counts(students, sid, [(2, 3), (0, 3), (0, 3)])
    (item,) = only_course(report(teacher))["practice"]["missed_questions"]
    assert set(item) == MISSED_KEYS
    assert item == {"set_id": sid, "set_title": "Shape", "position": 1, "question": "Question number 1?",
                    "missed": 2, "answered": 3, "miss_rate_percent": 66}


def test_tea05_ac8_ranks_by_exact_fraction_then_misses_and_caps_at_five_excluding_zero_miss():
    teacher, course = teacher_with_course()
    students = roster(course, 19)
    zeta = published_set(course, "Zeta", question_set((0,) * 3))
    alpha = published_set(course, "alpha", question_set((0,) * 3))
    beta = published_set(course, "Beta", question_set((0,) * 3))
    miss_counts(students, zeta, [(7, 11), (12, 19), (1, 1)])
    miss_counts(students, alpha, [(1, 1), (2, 2), (1, 2)])
    miss_counts(students, beta, [(0, 5), (0, 3), (0, 3)])
    items = only_course(report(teacher))["practice"]["missed_questions"]
    assert len(items) == 5
    assert [(i["set_title"], i["position"]) for i in items] == [
        ("alpha", 2),  # 2 of 2 = 100%, two misses
        ("alpha", 1),  # 1 of 1 = 100%, one miss, set title alpha before Zeta (case-insensitive)
        ("Zeta", 3),   # 1 of 1
        ("Zeta", 1),   # 7 of 11 = 63.63%
        ("Zeta", 2),   # 12 of 19 = 63.15%: same floored 63 but a lower exact fraction, more misses
    ]
    assert [(i["missed"], i["answered"], i["miss_rate_percent"]) for i in items] == [
        (2, 2, 100), (1, 1, 100), (1, 1, 100), (7, 11, 63), (12, 19, 63)]
    assert all(i["set_id"] in (zeta, alpha) for i in items)  # the all-correct set never appears


def test_tea05_ac8_ties_break_by_misses_then_set_title_case_insensitive_then_position():
    teacher, course = teacher_with_course()
    students = roster(course, 4)
    lower = published_set(course, "alpha", question_set((0,) * 2))
    upper = published_set(course, "Beta", question_set((0,) * 2))
    big = published_set(course, "zz", question_set((0,) * 1))
    miss_counts(students, lower, [(1, 2), (1, 2)])
    miss_counts(students, upper, [(1, 2), (1, 2)])
    miss_counts(students, big, [(2, 4)])
    items = only_course(report(teacher))["practice"]["missed_questions"]
    assert [(i["set_title"], i["position"]) for i in items] == [
        ("zz", 1), ("alpha", 1), ("alpha", 2), ("Beta", 1), ("Beta", 2)]


def test_tea05_ac8_same_title_sets_are_ordered_by_position_then_set_id():
    teacher, course = teacher_with_course()
    students = roster(course, 2)
    a = published_set(course, "Same", question_set((0,) * 1))
    b = published_set(course, "Same", question_set((0,) * 1))
    miss_counts(students, a, [(1, 2)])
    miss_counts(students, b, [(1, 2)])
    items = only_course(report(teacher))["practice"]["missed_questions"]
    assert [i["set_id"] for i in items] == sorted([a, b])


def test_tea05_ac8_answered_counts_only_answered_questions_and_latest_attempt_only():
    teacher, course = teacher_with_course()
    s1, s2, s3 = roster(course, 3)
    sid = published_set(course, "Partial", question_set((0, 0, 0)))
    attempt(s1, sid, answered=[1], correct=[], when="2026-11-04T10:00:00Z", total=3)  # superseded
    attempt(s1, sid, answered=[1, 2], correct=[1], when="2026-11-05T10:00:00Z")  # q1 right, q2 missed
    attempt(s2, sid, answered=[1, 2], correct=[], when="2026-11-05T10:00:00Z")  # q1, q2 missed
    attempt(s3, sid, answered=[1, 2, 3], correct=[1, 2, 3], when="2026-11-05T10:00:00Z")
    items = {i["position"]: i for i in only_course(report(teacher))["practice"]["missed_questions"]}
    assert set(items) == {1, 2}  # question 3 was answered once, correctly: not listed
    assert (items[1]["missed"], items[1]["answered"]) == (1, 3)
    assert (items[2]["missed"], items[2]["answered"]) == (2, 3)


def test_tea05_ac8_missed_list_is_per_course_and_respects_the_period():
    teacher, course = teacher_with_course()
    other = make_course("TEA05 another")
    enroll(teacher, other)
    mine, theirs = roster(course, 1), roster(other, 1)
    s1 = published_set(course, "Old misses", question_set((0,)))
    s2 = published_set(other, "Other misses", question_set((0,)))
    miss_counts(mine, s1, [(1, 1)], when="2026-10-20T10:00:00Z")
    miss_counts(theirs, s2, [(1, 1)], when="2026-11-05T10:00:00Z")
    by_id = {c["course_id"]: c for c in report(teacher, "7d")["courses"]}
    assert by_id[course]["practice"]["missed_questions"] == []
    assert [i["set_title"] for i in by_id[other]["practice"]["missed_questions"]] == ["Other misses"]
    by_id = {c["course_id"]: c for c in report(teacher, "30d")["courses"]}
    assert [i["set_title"] for i in by_id[course]["practice"]["missed_questions"]] == ["Old misses"]
