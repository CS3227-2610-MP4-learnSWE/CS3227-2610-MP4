"""Shared helpers for the STU-01 tests (contract: workflow/specs/STU-01/plan.md).

Only the HTTP contract and the table columns named in the plan are used. Lessons, topics,
courses, memberships and drafts are inserted by SQL, because the publish route belongs to TEA-03.
"""
import uuid

from auth_helpers import call, new_student, require_db
from auth_helpers import sql as _sql

STUDY = "/api/study"
RANDOM_ID = "99999999-9999-4999-8999-999999999999"
LESSON_NOT_FOUND = {"detail": {"code": "not_found", "message": "Lesson not found."}}


def sql(statement, params=()):
    """auth_helpers.sql, but a test skips (no database) instead of failing on a missing DATABASE_URL."""
    require_db()
    return _sql(statement, params)


def uid():
    return str(uuid.uuid4())


def make_course(title=None):
    cid = uid()
    sql("INSERT INTO course(id, title) VALUES (%s, %s)", (cid, title or f"Course {cid[:8]}"))
    return cid


def enroll(user_id, course_id):
    sql("INSERT INTO course_membership(course_id, user_id) VALUES (%s, %s)", (course_id, str(user_id)))


def unenroll(user_id, course_id):
    sql("DELETE FROM course_membership WHERE course_id = %s AND user_id = %s", (course_id, str(user_id)))


def make_topic(course_id, name):
    tid = uid()
    sql("INSERT INTO topic(id, course_id, name) VALUES (%s, %s, %s)", (tid, course_id, name))
    return tid


def make_lesson(course_id, *, topic_id=None, title="A lesson", content="Plain lesson text.",
                published_at=None, withdrawn=False, published_by="demo-teacher"):
    lid = uid()
    sql(
        "INSERT INTO published_lesson(id, course_id, topic_id, title, content, published_by, published_at, "
        "withdrawn_at) VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()), "
        "CASE WHEN %s THEN now() END)",
        (lid, course_id, topic_id, title, content, published_by, published_at, withdrawn),
    )
    return lid


def withdraw(lesson_id, on=True):
    sql("UPDATE published_lesson SET withdrawn_at = CASE WHEN %s THEN now() END WHERE id = %s",
        (on, lesson_id))


def make_draft(course_id, *, title="Draft title", content="DRAFT-ONLY-CONTENT-7731"):
    """A teacher's unpublished study note draft (never visible to students)."""
    mid, did = uid(), uid()
    sql("INSERT INTO material(id, course_id, uploaded_by, title, original_filename, media_type, size_bytes) "
        "VALUES (%s, %s, 'demo-teacher', 'Source', 's.txt', 'text/plain', 1)", (mid, course_id))
    sql("INSERT INTO study_note_draft(id, course_id, source_material_id, created_by, title, content, "
        "source_title, updated_by) VALUES (%s, %s, %s, 'demo-teacher', %s, %s, 'Source', 'demo-teacher')",
        (did, course_id, mid, title, content))
    return did


def enrolled_student(course_id=None, prefix="stu"):
    s = new_student(prefix)
    if course_id:
        enroll(s, course_id)
    return s


def world(n_lessons=2):
    """A course, an enrolled student and `n_lessons` published lessons (ids in publish order)."""
    cid = make_course()
    s = enrolled_student(cid)
    lessons = [make_lesson(cid, title=f"Lesson {i}", content=f"Body {i}",
                           published_at=f"2026-01-0{i + 1}T00:00:00Z") for i in range(n_lessons)]
    return cid, s, lessons


def put_completion(student, lesson_id, completed, **kw):
    return call("PUT", f"{STUDY}/lessons/{lesson_id}/completion", student, {"completed": completed}, **kw)


def get_lesson(student, lesson_id, **kw):
    return call("GET", f"{STUDY}/lessons/{lesson_id}", student, **kw)


def get_courses(student, **kw):
    return call("GET", f"{STUDY}/courses", student, **kw)


def get_course_lessons(student, course_id, **kw):
    return call("GET", f"{STUDY}/courses/{course_id}/lessons", student, **kw)


def course_entry(student, course_id):
    for c in get_courses(student).json()["courses"]:
        if c["id"] == course_id:
            return c
    return None


def completion_rows(user_id, lesson_id=None):
    if lesson_id:
        return sql("SELECT lesson_id::text, completed, completed_at FROM lesson_completion "
                   "WHERE user_id = %s AND lesson_id = %s", (str(user_id), lesson_id))
    return sql("SELECT lesson_id::text, completed, completed_at FROM lesson_completion WHERE user_id = %s",
               (str(user_id),))
