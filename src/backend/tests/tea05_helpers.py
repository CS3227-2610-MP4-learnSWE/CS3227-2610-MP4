"""Shared helpers for the TEA-05 tests (contract: workflow/specs/TEA-05/plan.md).

Only the HTTP contract and the table columns named in the plan are used. Students are inserted by
SQL (they never sign in), memberships, lessons, completions, sets and attempts too, so every
instant is chosen exactly. The service clock is `teacher_overview.service.utc_now`.
"""
import importlib
import json
import uuid
from datetime import datetime, timezone

from adm02_helpers import actor
from auth_helpers import call, code_of  # noqa: F401
from published_sets import insert_published_set
from stu01_helpers import enroll, make_course, make_lesson, make_topic, sql, uid, unenroll  # noqa: F401
from stu04_helpers import insert_attempt

PATH = "/api/teacher/overview"
NOW = datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc)
BAD_PERIOD = {"code": "invalid_overview_period", "message": "Choose Last 7 days, Last 30 days or All time."}
RATE_LIMITED = "Too many overview requests. Try again shortly."

TOP_KEYS = {"period", "as_of", "courses"}
PERIOD_KEYS = {"preset", "start", "end", "start_date", "end_date", "timezone"}
COURSE_KEYS = {"course_id", "title", "student_count", "lesson_count", "completion_rate_percent", "lessons", "practice"}
LESSON_KEYS = {"lesson_id", "title", "topic", "completed_students", "rate_percent"}
PRACTICE_KEYS = {"sets", "missed_questions"}
SET_KEYS = {"set_id", "title", "topic", "students_attempted", "submitted_attempts", "average_score_percent"}
MISSED_KEYS = {"set_id", "set_title", "position", "question", "missed", "answered", "miss_rate_percent"}

SECRET_QUESTIONS = [
    (f"Visible question {i}?", [f"SECRETCHOICE-{i}-{c}" for c in "ABCD"], i % 4, f"SECRETEXPLANATION-{i}")
    for i in range(1, 4)
]


def set_clock(monkeypatch, now=NOW):
    service = importlib.import_module("teacher_overview.service")
    monkeypatch.setattr(service, "utc_now", lambda: now)
    return service


def teacher_with_course(title=None):
    teacher = actor("teacher")
    course = make_course(title)
    enroll(teacher, course)
    return teacher, course


def overview(user, period="30d", query=None):
    return call("GET", PATH + (query if query is not None else f"?period={period}"), user)


def report(user, period="30d"):
    r = overview(user, period)
    assert r.status_code == 200, r.text
    return r.json()


def only_course(body):
    assert len(body["courses"]) == 1, body["courses"]
    return body["courses"][0]


def student_row(course_id=None, *, status="enabled", name=None, prefix="t5"):
    """A student account inserted by SQL (copy of the seeded password hash); enrolled when course_id is given."""
    user_id = "u-" + uuid.uuid4().hex
    email = f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"
    sql('INSERT INTO "user"(id,display_name,role,email,password_hash,access_status) '
        'SELECT %s,%s,\'student\',%s,password_hash,%s FROM "user" WHERE id=\'demo-admin\'',
        (user_id, name or f"Student {prefix} {user_id[-6:]}", email, status))
    if course_id:
        enroll(user_id, course_id)
    return user_id


def roster(course_id, n, **kw):
    return [student_row(course_id, **kw) for _ in range(n)]


def complete(user_id, lesson_id, when="2026-11-05T10:00:00Z", completed=True):
    sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
        "SELECT %s, id, course_id, %s, CASE WHEN %s THEN %s::timestamptz END FROM published_lesson WHERE id = %s "
        "ON CONFLICT (user_id, lesson_id) DO UPDATE SET completed = EXCLUDED.completed, completed_at = EXCLUDED.completed_at",
        (str(user_id), completed, completed, when, lesson_id))


def published_set(course_id, title="Testing basics", questions=None, topic_name=None, published_at=None):
    topic = make_topic(course_id, topic_name or f"Topic {uuid.uuid4().hex[:6]}")
    return insert_published_set(course_id, topic, title, questions, published_at=published_at)


def question_ids(set_id):
    return [r[0] for r in sql("SELECT id::text FROM published_practice_question WHERE set_id = %s ORDER BY position", (set_id,))]


def attempt(student, set_id, *, correct=None, answered=None, when="2026-11-05T10:00:00Z", total=None, status="submitted"):
    """Insert an attempt on a published set. `correct`/`answered` are lists of question POSITIONS (1-based);
    default answered = every question, correct = none."""
    qids = question_ids(set_id)
    answered = list(range(1, len(qids) + 1)) if answered is None else answered
    correct = [] if correct is None else correct
    answers = {qids[p - 1]: 0 for p in answered}
    correct_ids = [qids[p - 1] for p in correct]
    return insert_attempt(student, answers=answers, correct_ids=correct_ids, status=status, set_id=set_id,
                          submitted_at=when, total=len(qids) if total is None else total)


def miss_counts(students, set_id, spec, when="2026-11-05T10:00:00Z"):
    """One attempt per student on the set so that the question at position i+1 has spec[i] = (missed, answered)."""
    for k, student in enumerate(students):
        answered = [i + 1 for i, (_, a) in enumerate(spec) if k < a]
        correct = [i + 1 for i, (m, a) in enumerate(spec) if k < a and k >= m]
        attempt(student, set_id, answered=answered, correct=correct, when=when)


def walk(value):
    """Yield (key, value) for every dict key in a JSON value."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield k, v
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def dumps(body):
    return json.dumps(body, ensure_ascii=False)
