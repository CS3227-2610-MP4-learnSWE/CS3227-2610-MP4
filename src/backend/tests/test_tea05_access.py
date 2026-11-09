"""TEA-05 access, course scoping, period object and period validation (AC1, AC3, AC5, AC9)."""
import hashlib

import pytest

from adm02_helpers import actor
from auth_helpers import call, code_of, seeded
from published_sets import question_set
from tea05_helpers import (BAD_PERIOD, NOW, complete, enroll, make_course, make_lesson, only_course, overview,
                           published_set, report, roster, set_clock, sql, teacher_with_course, unenroll,
                           attempt, student_row)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    set_clock(monkeypatch)


# ---------- AC9 roles ----------

def test_tea05_ac9_anonymous_is_401_unauthenticated():
    r = call("GET", "/api/teacher/overview?period=30d")
    assert r.status_code == 401
    assert code_of(r) == "unauthenticated"


@pytest.mark.parametrize("role", ["student", "admin"])
def test_tea05_ac9_student_and_admin_are_403_forbidden(role):
    user = actor(role)
    r = overview(user)
    assert r.status_code == 403
    assert code_of(r) == "forbidden"
    seeded_user = seeded(role)
    assert overview(seeded_user).status_code == 403


@pytest.mark.parametrize("role", ["student", "admin"])
def test_tea05_ac9_role_check_runs_before_period_validation(role):
    assert overview(actor(role), query="?period=bogus").status_code == 403
    assert call("GET", "/api/teacher/overview?period=bogus").status_code == 401


def test_tea05_ac9_expired_session_is_refused():
    teacher, _ = teacher_with_course()
    assert overview(teacher).status_code == 200
    digest = hashlib.sha256(teacher.token.encode()).hexdigest()
    sql("UPDATE auth_session SET expires_at = now() - interval '1 hour' WHERE token_hash = %s", (digest,))
    r = overview(teacher)
    assert r.status_code == 401
    assert code_of(r) == "unauthenticated"


def test_tea05_ac9_disabled_teacher_is_refused():
    teacher, _ = teacher_with_course()
    assert overview(teacher).status_code == 200
    sql('UPDATE "user" SET access_status = \'disabled\' WHERE id = %s', (str(teacher),))
    assert overview(teacher).status_code in (401, 403)


def test_tea05_ac9_response_is_not_cacheable():
    teacher, _ = teacher_with_course()
    assert "no-store" in overview(teacher).headers["cache-control"]


# ---------- AC1 / AC3 / AC9 course scope ----------

def test_tea05_ac1_ac3_teacher_sees_only_courses_they_are_a_member_of():
    mine_a, mine_b = make_course("TEA05 Zulu course"), make_course("tea05 alpha course")
    other = make_course("TEA05 Other teacher course")
    teacher, outsider = actor("teacher"), actor("teacher")
    enroll(teacher, mine_a)
    enroll(teacher, mine_b)
    enroll(outsider, other)
    for course in (mine_a, mine_b, other):
        lesson = make_lesson(course, title=f"Lesson of {course}")
        complete(roster(course, 1)[0], lesson)
        published_set(course, title=f"Set of {course}")
    body = report(teacher)
    assert [c["course_id"] for c in body["courses"]] == [mine_b, mine_a]  # lower(title)
    assert [c["title"] for c in body["courses"]] == ["tea05 alpha course", "TEA05 Zulu course"]
    assert "Other teacher course" not in str(body) and other not in str(body)
    assert [c["course_id"] for c in report(outsider)["courses"]] == [other]


def test_tea05_ac1_courses_with_equal_titles_are_ordered_by_id():
    teacher = actor("teacher")
    ids = [make_course("TEA05 same title") for _ in range(3)]
    for c in ids:
        enroll(teacher, c)
    assert [c["course_id"] for c in report(teacher)["courses"]] == sorted(ids)


def test_tea05_ac9_teacher_without_membership_gets_empty_course_list():
    teacher = actor("teacher")
    body = report(teacher)
    assert body["courses"] == []
    assert body["period"]["preset"] == "30d"


def test_tea05_ac9_removed_membership_removes_the_course():
    teacher, course = teacher_with_course("TEA05 removable")
    assert [c["course_id"] for c in report(teacher)["courses"]] == [course]
    unenroll(teacher, course)
    assert report(teacher)["courses"] == []


def test_tea05_ac9_enrolled_student_in_a_course_does_not_make_a_teacher_member_elsewhere():
    teacher, course = teacher_with_course()
    other_course = make_course("TEA05 foreign")
    student = student_row(other_course)
    enroll(student, course)
    ids = [c["course_id"] for c in report(teacher)["courses"]]
    assert ids == [course]
    only = only_course(report(teacher))
    assert only["student_count"] == 1  # enrolled in this course too, counted here only


@pytest.mark.parametrize("extra", ["&course_id=x", "&teacher_id=demo-teacher", "&user=demo-teacher"])
def test_tea05_ac9_scope_cannot_be_chosen_by_the_request(extra):
    teacher, _ = teacher_with_course()
    r = overview(teacher, query="?period=30d" + extra)
    assert r.status_code == 422
    assert r.json()["detail"] == BAD_PERIOD


def test_tea05_ac9_membership_of_a_non_teacher_account_is_not_exposed_to_a_teacher():
    teacher, course = teacher_with_course("TEA05 mine")
    other_teacher, other_course = teacher_with_course("TEA05 theirs")
    body = report(teacher)
    assert [c["title"] for c in body["courses"]] == ["TEA05 mine"]
    assert other_course not in str(body)


# ---------- AC1 / AC3 / AC5 period object ----------

PERIODS = {
    "7d": ("2026-11-03T00:00:00Z", "2026-11-03"),
    "30d": ("2026-10-11T00:00:00Z", "2026-10-11"),
    "all": (None, None),
}


@pytest.mark.parametrize("preset", ["7d", "30d", "all"])
def test_tea05_ac1_ac3_ac5_period_object_names_the_period_and_server_time(preset):
    teacher, _ = teacher_with_course()
    body = report(teacher, preset)
    start, start_date = PERIODS[preset]
    assert body["period"] == {"preset": preset, "start": start, "end": "2026-11-10T00:00:00Z",
                              "start_date": start_date, "end_date": "2026-11-09", "timezone": "UTC"}
    assert body["as_of"] == "2026-11-09T12:00:00Z"


def test_tea05_ac5_period_object_uses_utc_day_boundaries_at_the_edges_of_the_day(monkeypatch):
    from datetime import datetime, timezone
    teacher, _ = teacher_with_course()
    for now, end_date in [(datetime(2026, 11, 9, 0, 0, 0, tzinfo=timezone.utc), "2026-11-09"),
                          (datetime(2026, 11, 9, 23, 59, 59, 999999, tzinfo=timezone.utc), "2026-11-09"),
                          (datetime(2026, 3, 1, 5, 0, tzinfo=timezone.utc), "2026-03-01")]:
        set_clock(monkeypatch, now)
        period = report(teacher, "7d")["period"]
        assert period["end_date"] == end_date
        assert period["end"].endswith("T00:00:00Z") and period["end"][:10] > end_date
    # 7 days across the end of February: today and the previous 6 days
    set_clock(monkeypatch, datetime(2026, 3, 3, 10, 0, tzinfo=timezone.utc))
    period = report(teacher, "7d")["period"]
    assert (period["start_date"], period["end_date"]) == ("2026-02-25", "2026-03-03")
    period = report(teacher, "30d")["period"]
    assert (period["start_date"], period["end_date"]) == ("2026-02-02", "2026-03-03")


# ---------- AC5 period validation ----------

@pytest.mark.parametrize("query", [
    "", "?", "?period=", "?period=1d", "?period=ALL", "?period=7D", "?period=30", "?period=7d&period=7d",
    "?period=7d&period=30d", "?period=7d&extra=1", "?other=7d", "?Period=7d", "?period=7d%00",
    "?period=all%20time", "?period=7d;30d", "?period=7d%27%20OR%20%271%27%3D%271",
    "?period=%3Cscript%3Ealert(1)%3C/script%3E", "?period=../../etc/passwd", "?period=%E2%80%837d",
])
def test_tea05_ac5_invalid_period_is_422_without_echoing_the_value(query):
    teacher, _ = teacher_with_course()
    r = overview(teacher, query=query)
    assert r.status_code == 422, r.text
    assert r.json() == {"detail": BAD_PERIOD}
    for fragment in ("script", "passwd", "OR '1'", "ALL", "all time"):
        assert fragment not in r.text.replace(BAD_PERIOD["message"], "")


@pytest.mark.parametrize("query,preset", [
    ("?period=%207d%20", "7d"), ("?period=%0930d", "30d"), ("?period=all%20", "all"), ("?period=+30d+", "30d"),
])
def test_tea05_ac5_surrounding_ascii_whitespace_is_trimmed(query, preset):
    teacher, _ = teacher_with_course()
    r = overview(teacher, query=query)
    assert r.status_code == 200, r.text
    assert r.json()["period"]["preset"] == preset


def test_tea05_ac5_period_is_case_sensitive_and_never_defaults():
    teacher, _ = teacher_with_course()
    assert overview(teacher, query="").status_code == 422
    assert overview(teacher, query="?period=All").status_code == 422


# ---------- AC5 boundaries ----------

def _boundary_world():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Boundary lesson")
    students = roster(course, 5)
    s = published_set(course, "Boundary set", question_set((0, 0, 0)))
    return teacher, course, lesson, students, s


@pytest.mark.parametrize("preset,start,before", [
    ("7d", "2026-11-03T00:00:00Z", "2026-11-02T23:59:59.999999Z"),
    ("30d", "2026-10-11T00:00:00Z", "2026-10-10T23:59:59.999999Z"),
])
def test_tea05_ac5_item_exactly_at_start_is_inside_one_microsecond_before_is_outside(preset, start, before):
    teacher, course, lesson, students, s = _boundary_world()
    complete(students[0], lesson, start)
    complete(students[1], lesson, before)
    attempt(students[0], s, correct=[1, 2, 3], when=start)
    attempt(students[1], s, correct=[1, 2, 3], when=before)
    c = only_course(report(teacher, preset))
    assert c["lessons"][0]["completed_students"] == 1
    assert c["practice"]["sets"][0]["students_attempted"] == 1
    assert c["practice"]["sets"][0]["submitted_attempts"] == 1


def test_tea05_ac5_end_is_exclusive_and_all_has_no_lower_bound():
    teacher, course, lesson, students, s = _boundary_world()
    complete(students[0], lesson, "2026-11-09T23:59:59.999999Z")  # last instant of today: inside
    complete(students[1], lesson, "2026-11-10T00:00:00Z")  # end: outside
    complete(students[2], lesson, "2020-01-01T00:00:00Z")  # only in all
    attempt(students[0], s, when="2026-11-09T23:59:59.999999Z")
    attempt(students[1], s, when="2026-11-10T00:00:00Z")
    attempt(students[2], s, when="2020-01-01T00:00:00Z")
    for preset, completed, attempted in [("7d", 1, 1), ("30d", 1, 1), ("all", 2, 2)]:
        c = only_course(report(teacher, preset))
        assert c["lessons"][0]["completed_students"] == completed, preset
        assert c["practice"]["sets"][0]["students_attempted"] == attempted, preset
