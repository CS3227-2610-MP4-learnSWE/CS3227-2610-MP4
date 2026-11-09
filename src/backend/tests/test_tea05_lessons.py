"""TEA-05 lesson completion figures (AC2, AC6)."""
import pytest

from stu01_helpers import make_draft, make_topic, withdraw
from tea05_helpers import (complete, enroll, make_course, make_lesson, only_course, report, roster, set_clock,
                           student_row, teacher_with_course, unenroll, sql)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    set_clock(monkeypatch)


def lessons_by_title(course):
    return {item["title"]: item for item in course["lessons"]}


def test_tea05_ac6_counts_floor_rates_and_general_topic():
    teacher, course = teacher_with_course()
    algebra = make_topic(course, "Algebra")
    l1 = make_lesson(course, topic_id=algebra, title="L1", published_at="2026-01-01T00:00:00Z")
    l2 = make_lesson(course, title="L2", published_at="2026-01-02T00:00:00Z")
    a, b, c = roster(course, 3)
    complete(a, l1)
    complete(b, l1)
    complete(c, l1, completed=False)
    complete(a, l2)
    got = only_course(report(teacher))
    assert (got["student_count"], got["lesson_count"]) == (3, 2)
    assert got["lessons"] == [
        {"lesson_id": l1, "title": "L1", "topic": "Algebra", "completed_students": 2, "rate_percent": 66},
        {"lesson_id": l2, "title": "L2", "topic": "General", "completed_students": 1, "rate_percent": 33},
    ]
    assert got["completion_rate_percent"] == 50  # 3 of 6


def test_tea05_ac6_course_rate_is_floored_not_rounded():
    teacher, course = teacher_with_course()
    lessons = [make_lesson(course, title=f"L{i}", published_at=f"2026-01-0{i + 1}T00:00:00Z") for i in range(3)]
    students = roster(course, 3)
    complete(students[0], lessons[0])
    complete(students[1], lessons[0])
    complete(students[2], lessons[0])
    complete(students[0], lessons[1])
    complete(students[0], lessons[2])
    complete(students[1], lessons[2])
    # 6 of 9 = 66.67 -> 66
    assert only_course(report(teacher))["completion_rate_percent"] == 66


def test_tea05_ac6_lessons_are_ordered_by_publication_then_id():
    teacher, course = teacher_with_course()
    late = make_lesson(course, title="Published late", published_at="2026-03-01T00:00:00Z")
    early = make_lesson(course, title="Published early", published_at="2026-01-01T00:00:00Z")
    same = sorted(make_lesson(course, title=f"Same {i}", published_at="2026-02-01T00:00:00Z") for i in range(3))
    roster(course, 1)
    ids = [item["lesson_id"] for item in only_course(report(teacher))["lessons"]]
    assert ids == [early, *same, late]


def test_tea05_ac2_ac6_no_students_gives_null_rates_and_zero_counts():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Lonely")
    got = only_course(report(teacher))
    assert got["student_count"] == 0 and got["lesson_count"] == 1
    assert got["completion_rate_percent"] is None
    assert got["lessons"] == [{"lesson_id": lesson, "title": "Lonely", "topic": "General",
                               "completed_students": 0, "rate_percent": None}]


def test_tea05_ac2_ac6_no_lessons_gives_null_course_rate_and_empty_list():
    teacher, course = teacher_with_course()
    roster(course, 2)
    got = only_course(report(teacher))
    assert (got["student_count"], got["lesson_count"], got["lessons"]) == (2, 0, [])
    assert got["completion_rate_percent"] is None


def test_tea05_ac2_no_activity_is_zero_not_null():
    teacher, course = teacher_with_course()
    make_lesson(course, title="Idle")
    roster(course, 4)
    got = only_course(report(teacher))
    assert got["completion_rate_percent"] == 0
    assert got["lessons"][0]["completed_students"] == 0 and got["lessons"][0]["rate_percent"] == 0


def test_tea05_ac6_withdrawn_and_draft_lessons_are_absent():
    teacher, course = teacher_with_course()
    kept = make_lesson(course, title="Kept lesson")
    gone = make_lesson(course, title="WITHDRAWN-TITLE-5521")
    make_draft(course, title="DRAFT-TITLE-5521", content="DRAFT-BODY-5521")
    (student,) = roster(course, 1)
    complete(student, gone)
    withdraw(gone)
    got = only_course(report(teacher))
    assert got["lesson_count"] == 1 and [i["title"] for i in got["lessons"]] == ["Kept lesson"]
    assert got["completion_rate_percent"] == 0
    text = str(report(teacher))
    assert "WITHDRAWN-TITLE-5521" not in text and "DRAFT-TITLE-5521" not in text and "DRAFT-BODY-5521" not in text
    assert kept in text


def test_tea05_ac6_completed_then_undone_is_not_counted():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Undone")
    done, undone = roster(course, 2)
    complete(done, lesson)
    complete(undone, lesson, completed=False)
    assert only_course(report(teacher))["lessons"][0]["completed_students"] == 1


def test_tea05_ac6_completions_by_teachers_non_members_and_other_courses_are_not_counted():
    teacher, course = teacher_with_course()
    other = make_course("TEA05 other course")
    lesson = make_lesson(course, title="Mine")
    other_lesson = make_lesson(other, title="Theirs")
    (member,) = roster(course, 1)
    outsider = student_row()  # not enrolled anywhere
    complete(member, lesson)
    complete(outsider, lesson)
    complete(str(teacher), lesson)  # the teacher is a member but not a student
    elsewhere = student_row(other)
    complete(elsewhere, other_lesson)
    got = only_course(report(teacher))
    assert got["student_count"] == 1
    assert got["lessons"][0]["completed_students"] == 1
    assert got["lessons"][0]["rate_percent"] == 100
    assert got["completion_rate_percent"] == 100


def test_tea05_ac6_removed_student_drops_out_of_every_figure():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Roster")
    stay, leave = roster(course, 2)
    complete(stay, lesson)
    complete(leave, lesson)
    assert only_course(report(teacher))["lessons"][0]["completed_students"] == 2
    unenroll(leave, course)
    got = only_course(report(teacher))
    assert got["student_count"] == 1 and got["lessons"][0]["completed_students"] == 1
    assert got["lessons"][0]["rate_percent"] == 100


def test_tea05_ac6_disabled_student_still_counts():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Disabled")
    active = student_row(course)
    disabled = student_row(course, status="disabled")
    complete(active, lesson)
    complete(disabled, lesson)
    got = only_course(report(teacher))
    assert got["student_count"] == 2 and got["lessons"][0]["completed_students"] == 2


def test_tea05_ac6_student_in_two_courses_counts_in_each_for_its_own_lessons():
    teacher, course = teacher_with_course()
    other = make_course("TEA05 second")
    enroll(teacher, other)
    l1, l2 = make_lesson(course, title="In first"), make_lesson(other, title="In second")
    student = student_row(course)
    enroll(student, other)
    complete(student, l1)
    by_title = {c["title"]: c for c in report(teacher)["courses"]}
    first = next(c for c in report(teacher)["courses"] if c["course_id"] == course)
    second = next(c for c in report(teacher)["courses"] if c["course_id"] == other)
    assert first["lessons"][0]["completed_students"] == 1
    assert second["lessons"][0]["completed_students"] == 0
    assert l2 and by_title


def test_tea05_ac6_completions_are_counted_by_completion_time_inside_the_period():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Timed")
    a, b, c = roster(course, 3)
    complete(a, lesson, "2026-11-08T08:00:00Z")  # 7d, 30d, all
    complete(b, lesson, "2026-10-20T08:00:00Z")  # 30d, all
    complete(c, lesson, "2025-01-20T08:00:00Z")  # all
    seen = {p: only_course(report(teacher, p)) for p in ("7d", "30d", "all")}
    assert [seen[p]["lessons"][0]["completed_students"] for p in ("7d", "30d", "all")] == [1, 2, 3]
    assert [seen[p]["lessons"][0]["rate_percent"] for p in ("7d", "30d", "all")] == [33, 66, 100]
    assert [seen[p]["completion_rate_percent"] for p in ("7d", "30d", "all")] == [33, 66, 100]


def test_tea05_ac6_percentages_never_exceed_100_and_are_integers():
    teacher, course = teacher_with_course()
    lessons = [make_lesson(course, title=f"P{i}") for i in range(2)]
    for student in roster(course, 3):
        for lesson in lessons:
            complete(student, lesson)
    got = only_course(report(teacher))
    assert got["completion_rate_percent"] == 100
    assert all(isinstance(i["rate_percent"], int) and i["rate_percent"] == 100 for i in got["lessons"])
