"""TEA-05 privacy allow-list, rate limit, failure mapping, no-LLM and concurrency (AC10, AC11; SHR-01, SHR-02, SHR-05)."""
import importlib
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.exc import SQLAlchemyError

from adm02_helpers import actor
from auth_helpers import call, code_of
from stu01_helpers import make_draft, withdraw
from tea05_helpers import (COURSE_KEYS, LESSON_KEYS, MISSED_KEYS, PERIOD_KEYS, PRACTICE_KEYS, RATE_LIMITED, SECRET_QUESTIONS,
                           SET_KEYS, TOP_KEYS, attempt, complete, dumps, enroll, make_course, make_lesson, miss_counts,
                           overview, published_set, report, roster, set_clock, sql, student_row, teacher_with_course, walk)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    set_clock(monkeypatch)


# ---------- AC10 allow-list and leakage ----------

def _rich_world():
    teacher, course = teacher_with_course("TEA05 privacy course")
    lesson = make_lesson(course, title="Visible lesson")
    withdrawn = make_lesson(course, title="HIDDEN-WITHDRAWN-LESSON")
    make_draft(course, title="HIDDEN-DRAFT-TITLE", content="HIDDEN-DRAFT-CONTENT-7731")
    students = [student_row(course, name=f"Secretname{i} Surname{i}", prefix="leakmail") for i in range(4)]
    sid = published_set(course, "Visible set", SECRET_QUESTIONS)
    for s in students:
        complete(s, lesson)
        complete(s, withdrawn)
    withdraw(withdrawn)
    miss_counts(students, sid, [(3, 4), (2, 4), (1, 4)])
    other_teacher, other_course = teacher_with_course("TEA05 SOMEONE-ELSES-COURSE")
    make_lesson(other_course, title="SOMEONE-ELSES-LESSON")
    return teacher, course, students, sid


def test_tea05_ac10_response_keys_are_exactly_the_allow_list():
    teacher, course, _, sid = _rich_world()
    body = report(teacher)
    assert set(body) == TOP_KEYS and set(body["period"]) == PERIOD_KEYS
    (c,) = body["courses"]
    assert set(c) == COURSE_KEYS and c["lessons"] and c["practice"]["sets"] and c["practice"]["missed_questions"]
    assert all(set(item) == LESSON_KEYS for item in c["lessons"])
    assert set(c["practice"]) == PRACTICE_KEYS
    assert all(set(item) == SET_KEYS for item in c["practice"]["sets"])
    assert all(set(item) == MISSED_KEYS for item in c["practice"]["missed_questions"])
    allowed = TOP_KEYS | PERIOD_KEYS | COURSE_KEYS | LESSON_KEYS | PRACTICE_KEYS | SET_KEYS | MISSED_KEYS
    assert {k for k, _ in walk(body)} <= allowed


def test_tea05_ac10_no_student_identity_answer_key_or_unpublished_content_in_the_json():
    teacher, course, students, sid = _rich_world()
    for preset in ("7d", "30d", "all"):
        text = dumps(report(teacher, preset))
        lowered = text.lower()
        for s in students:
            assert s not in text
            name, email = sql('SELECT display_name, email FROM "user" WHERE id = %s', (s,))[0]
            assert name.lower() not in lowered and email.lower() not in lowered
        for fragment in ("secretname", "surname", "leakmail", "@example.com", "secretchoice", "secretexplanation",
                         "hidden-withdrawn", "hidden-draft", "someone-elses", "correct_choice", "explanation",
                         "choices", "answers", "student_id", "email", "display_name", "password", "attempt_id"):
            assert fragment not in lowered, fragment
        assert "Visible question 1?" in text  # teacher's own published question text is allowed


def test_tea05_ac10_values_are_only_ids_text_integers_and_nulls():
    teacher, *_ = _rich_world()
    body = report(teacher)
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", body["as_of"])
    for key, value in walk(body):
        assert value is None or isinstance(value, (str, int, list, dict)) and not isinstance(value, float), key
        assert not isinstance(value, bool), key
    assert not any(k.endswith(("_at", "_time", "timestamp")) for k, _ in walk(body["courses"]))


def test_tea05_ac10_responses_are_no_store_for_success_and_errors():
    teacher, _ = teacher_with_course()
    for r in (overview(teacher), overview(teacher, query="?period=bad"), call("GET", "/api/teacher/overview?period=7d"),
              overview(actor("student"))):
        assert r.headers["cache-control"] == "no-store"  # AC10 amended 2026-11-09 (user decision)


def test_tea05_ac10_membership_removal_and_other_teachers_data_never_leak():
    teacher_a, course_a = teacher_with_course("TEA05 only A")
    teacher_b, course_b = teacher_with_course("TEA05 only B")
    la, lb = make_lesson(course_a, title="LESSON-ONLY-A"), make_lesson(course_b, title="LESSON-ONLY-B")
    a_student = student_row(course_a)
    complete(a_student, la)
    assert "LESSON-ONLY-B" not in dumps(report(teacher_a)) and "LESSON-ONLY-A" not in dumps(report(teacher_b))
    assert lb


# ---------- AC11 rate limit ----------

def test_tea05_ac11_the_31st_request_in_a_window_is_429_with_retry_after():
    teacher, _ = teacher_with_course()
    for i in range(30):
        assert overview(teacher, "30d").status_code == 200, i
    r = overview(teacher, "30d")
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert {k: detail[k] for k in ("code", "message")} == {"code": "overview_rate_limited", "message": RATE_LIMITED}
    assert set(detail) <= {"code", "message", "retry_after_seconds"}
    retry = r.headers["retry-after"]
    assert retry.isdigit() and 1 <= int(retry) <= 60
    assert "no-store" in r.headers["cache-control"]


def test_tea05_ac11_invalid_periods_do_not_consume_the_budget():
    teacher, _ = teacher_with_course()
    for _ in range(40):
        assert overview(teacher, query="?period=nope").status_code == 422
    for i in range(30):
        assert overview(teacher, "7d").status_code == 200, i
    assert overview(teacher, "7d").status_code == 429


def test_tea05_ac11_limit_is_per_teacher_and_refused_callers_do_not_consume_it():
    a, _ = teacher_with_course()
    b, _ = teacher_with_course()
    for _ in range(30):
        overview(a)
    assert overview(a).status_code == 429
    assert overview(b).status_code == 200
    student = actor("student")
    for _ in range(35):
        assert overview(student).status_code == 403
    assert overview(student).status_code == 403  # a role failure is never a 429


def test_tea05_ac11_period_presets_share_one_budget():
    teacher, _ = teacher_with_course()
    for i in range(30):
        assert overview(teacher, ("7d", "30d", "all")[i % 3]).status_code == 200
    assert overview(teacher, "all").status_code == 429


# ---------- AC11 database failure ----------

@pytest.mark.parametrize("error", [SQLAlchemyError("boom"), ])
def test_tea05_ac11_database_failure_is_503_not_an_empty_200(monkeypatch, error):
    teacher, _ = teacher_with_course()

    def boom(*args, **kwargs):
        raise error

    service = importlib.import_module("teacher_overview.service")
    routes = importlib.import_module("teacher_overview.routes")
    monkeypatch.setattr(service, "build_overview", boom)
    monkeypatch.setattr(routes, "build_overview", boom, raising=False)
    r = overview(teacher)
    assert r.status_code == 503
    assert code_of(r) == "service_unavailable"
    assert r.json()["detail"]["message"] == "Teacher service is unavailable. Please try again."
    assert "boom" not in r.text


# ---------- SHR-02: no AI ----------

def test_tea05_shr02_the_endpoint_never_calls_the_llm(fake, monkeypatch):
    import llm_client

    def forbidden(*args, **kwargs):
        raise AssertionError("TEA-05 must not use the SoC LLM client")

    monkeypatch.setattr(llm_client, "SoclaasClient", forbidden, raising=False)
    teacher, course = teacher_with_course()
    roster(course, 2)
    sid = published_set(course, "No AI")
    attempt(roster(course, 1)[0], sid)
    for period in ("7d", "30d", "all"):
        assert overview(teacher, period).status_code == 200
    assert fake.calls == []


# ---------- concurrency ----------

def test_tea05_concurrent_identical_reads_return_equal_bodies():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="Concurrent")
    students = roster(course, 5)
    complete(students[0], lesson)
    sid = published_set(course, "Parallel")
    miss_counts(students, sid, [(2, 4), (1, 3), (0, 2)])
    with ThreadPoolExecutor(10) as pool:
        replies = list(pool.map(lambda _: overview(teacher), range(10)))
    assert {r.status_code for r in replies} == {200}
    bodies = [r.json() for r in replies]
    assert all(b == bodies[0] for b in bodies)


def test_tea05_concurrent_enrolment_and_completion_writers_keep_the_figures_consistent():
    teacher, course = teacher_with_course()
    lessons = [make_lesson(course, title=f"W{i}", published_at=f"2026-01-0{i + 1}T00:00:00Z") for i in range(2)]
    seed_students = roster(course, 2)
    stop = threading.Event()

    def writer():
        while not stop.is_set():
            s = student_row(course)
            for lesson in lessons:
                complete(s, lesson, "2026-11-08T10:00:00Z")

    def check(body):
        (c,) = body["courses"]
        assert c["completion_rate_percent"] is None or 0 <= c["completion_rate_percent"] <= 100
        for item in c["lessons"]:
            assert 0 <= item["completed_students"] <= c["student_count"]
            assert item["rate_percent"] is None or 0 <= item["rate_percent"] <= 100

    for s in seed_students:
        complete(s, lessons[0])
    thread = threading.Thread(target=writer)
    thread.start()
    try:
        with ThreadPoolExecutor(6) as pool:
            replies = list(pool.map(lambda _: overview(teacher, "7d"), range(20)))
    finally:
        stop.set()
        thread.join(30)
    assert {r.status_code for r in replies} == {200}
    for r in replies:
        check(r.json())


def test_tea05_concurrent_reads_do_not_change_stored_data():
    teacher, course = teacher_with_course()
    lesson = make_lesson(course, title="ReadOnly")
    (s,) = roster(course, 1)
    complete(s, lesson)
    before = (sql("SELECT count(*) FROM lesson_completion"), sql("SELECT count(*) FROM practice_attempt"),
              sql("SELECT count(*) FROM course_membership"))
    with ThreadPoolExecutor(5) as pool:
        list(pool.map(lambda _: overview(teacher), range(5)))
    after = (sql("SELECT count(*) FROM lesson_completion"), sql("SELECT count(*) FROM practice_attempt"),
             sql("SELECT count(*) FROM course_membership"))
    assert before == after
