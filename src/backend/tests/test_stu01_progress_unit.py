"""STU-01 AC11 and the TEA-03 hand-over: direct unit tests of study_lessons.progress, access and publish.

These call the Python functions named in plan.md against the test schema (a real SQLAlchemy Session),
not the HTTP routes. Imports are lazy so the other suites collect before the package exists.
"""
import os
import uuid

import pytest
from auth_helpers import require_db
from stu01_helpers import sql
from stu01_helpers import (enroll, enrolled_student, make_course, make_draft, make_lesson, make_topic, uid,
                           unenroll, withdraw)


@pytest.fixture
def db():
    require_db()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        yield session
    engine.dispose()


def auth_user(user_id, role="student"):
    from auth.dependencies import AuthUser

    return AuthUser(id=str(user_id), email=None, display_name="Unit", role=role)


def mark(user_id, lesson_id, course_id, completed, at="2026-02-01T00:00:00Z"):
    sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
        "VALUES (%s, %s, %s, %s, CASE WHEN %s THEN %s::timestamptz END) "
        "ON CONFLICT (user_id, lesson_id) DO UPDATE SET completed = EXCLUDED.completed, "
        "completed_at = EXCLUDED.completed_at",
        (str(user_id), lesson_id, course_id, completed, completed, at))


# ------------------------------------------------------------------ completion_counts
def test_stu01_ac11_completion_counts_counts_visible_lessons_in_member_courses(db):
    from study_lessons.progress import completion_counts

    c1, c2, outsider = make_course(), make_course(), make_course()
    empty = make_course()
    s = enrolled_student()
    for c in (c1, c2, empty):
        enroll(s, c)
    a, b = make_lesson(c1), make_lesson(c1)
    gone = make_lesson(c1, withdrawn=True)
    d = make_lesson(c2)
    make_lesson(outsider)
    mark(s, a, c1, True)
    mark(s, gone, c1, True)
    mark(s, d, c2, False)
    counts = completion_counts(db, str(s))
    assert set(counts) == {uuid.UUID(c1), uuid.UUID(c2), uuid.UUID(empty)}
    assert (counts[uuid.UUID(c1)].lesson_count, counts[uuid.UUID(c1)].completed_count) == (2, 1)
    assert (counts[uuid.UUID(c2)].lesson_count, counts[uuid.UUID(c2)].completed_count) == (1, 0)
    assert (counts[uuid.UUID(empty)].lesson_count, counts[uuid.UUID(empty)].completed_count) == (0, 0)


def test_stu01_ac11_completion_counts_course_filter_and_unknown_or_non_member_ids_are_absent(db):
    from study_lessons.progress import completion_counts

    c1, c2, outsider = make_course(), make_course(), make_course()
    s = enrolled_student()
    enroll(s, c1)
    enroll(s, c2)
    make_lesson(c1)
    make_lesson(outsider)
    got = completion_counts(db, str(s), [uuid.UUID(c1), uuid.UUID(outsider), uuid.uuid4()])
    assert set(got) == {uuid.UUID(c1)}
    assert completion_counts(db, str(s), []) == {}
    assert completion_counts(db, "u-does-not-exist") == {}


def test_stu01_ac11_completion_counts_ignore_other_users_rows(db):
    from study_lessons.progress import completion_counts

    cid = make_course()
    me, other = enrolled_student(cid), enrolled_student(cid)
    lid = make_lesson(cid)
    mark(other, lid, cid, True)
    assert completion_counts(db, str(me))[uuid.UUID(cid)].completed_count == 0
    assert completion_counts(db, str(other))[uuid.UUID(cid)].completed_count == 1


def test_stu01_ac11_withdrawn_lessons_stop_counting_without_losing_the_record(db):
    from study_lessons.progress import completion_counts

    cid = make_course()
    s = enrolled_student(cid)
    lid, keep = make_lesson(cid), make_lesson(cid)
    mark(s, lid, cid, True)
    mark(s, keep, cid, True)
    assert completion_counts(db, str(s))[uuid.UUID(cid)].completed_count == 2
    withdraw(lid)
    db.expire_all()
    got = completion_counts(db, str(s))[uuid.UUID(cid)]
    assert (got.lesson_count, got.completed_count) == (1, 1)
    assert sql("SELECT count(*) FROM lesson_completion WHERE lesson_id = %s", (lid,))[0][0] == 1


# ------------------------------------------------------------------ completed_lessons
def test_stu01_ac11_completed_lessons_excludes_incomplete_withdrawn_foreign_and_other_users(db):
    from study_lessons.progress import completed_lessons

    cid, other_course = make_course(), make_course()
    topic = make_topic(cid, "Testing")
    me, other = enrolled_student(cid), enrolled_student(cid)
    done = make_lesson(cid, topic_id=topic, title="Done one")
    undone = make_lesson(cid, title="Undone")
    gone = make_lesson(cid, title="Gone", withdrawn=True)
    foreign = make_lesson(other_course, title="Foreign")
    theirs = make_lesson(cid, title="Theirs")
    mark(me, done, cid, True)
    mark(me, undone, cid, False)
    mark(me, gone, cid, True)
    mark(other, theirs, cid, True)
    mark(me, foreign, other_course, True)
    result = completed_lessons(db, str(me))
    assert [r.lesson_id for r in result] == [uuid.UUID(done)]
    row = result[0]
    assert row.course_id == uuid.UUID(cid) and row.topic_id == uuid.UUID(topic)
    assert row.title == "Done one" and row.completed_at is not None


def test_stu01_ac11_completed_lessons_order_is_newest_first_then_id(db):
    from study_lessons.progress import completed_lessons

    cid = make_course()
    s = enrolled_student(cid)
    old, new = make_lesson(cid), make_lesson(cid)
    tie_a, tie_b = make_lesson(cid), make_lesson(cid)
    mark(s, old, cid, True, "2026-01-01T00:00:00Z")
    mark(s, new, cid, True, "2026-03-01T00:00:00Z")
    mark(s, tie_a, cid, True, "2026-02-01T00:00:00Z")
    mark(s, tie_b, cid, True, "2026-02-01T00:00:00Z")
    ids = [str(r.lesson_id) for r in completed_lessons(db, str(s))]
    first_tie, second_tie = sorted([tie_a, tie_b])
    assert ids == [new, first_tie, second_tie, old]


def test_stu01_ac11_completed_lessons_null_topic_and_empty_result(db):
    from study_lessons.progress import completed_lessons

    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    assert completed_lessons(db, str(s)) == []
    mark(s, lid, cid, True)
    assert completed_lessons(db, str(s))[0].topic_id is None


def test_stu01_ac11_completed_lessons_figures_agree_with_completion_counts(db):
    from study_lessons.progress import completed_lessons, completion_counts

    c1, c2 = make_course(), make_course()
    s = enrolled_student()
    enroll(s, c1)
    enroll(s, c2)
    for c, n in ((c1, 3), (c2, 2)):
        for i in range(n):
            lid = make_lesson(c)
            if i != 1:
                mark(s, lid, c, True)
    total = sum(v.completed_count for v in completion_counts(db, str(s)).values())
    assert total == len(completed_lessons(db, str(s))) == 3


# ------------------------------------------------------------------ access and set_completion
def test_stu01_ac2_get_visible_lesson_returns_only_what_a_student_may_read(db):
    from errors import ApiError
    from study_lessons.access import get_visible_lesson

    mine, other = make_course(), make_course()
    s = enrolled_student(mine)
    ok = make_lesson(mine, title="Readable", content="Body text")
    lesson = get_visible_lesson(db, auth_user(s), uuid.UUID(ok))
    assert str(lesson.id) == ok and lesson.title == "Readable" and lesson.content == "Body text"
    for bad in (make_lesson(mine, withdrawn=True), make_lesson(other), make_draft(mine), str(uuid.uuid4())):
        with pytest.raises(ApiError):
            get_visible_lesson(db, auth_user(s), uuid.UUID(bad))
    unenroll(s, mine)
    with pytest.raises(ApiError):
        get_visible_lesson(db, auth_user(s), uuid.UUID(ok))


def test_stu01_ac9_set_completion_upserts_one_row_and_returns_the_stored_row(db):
    from study_lessons.progress import set_completion

    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    row = set_completion(db, auth_user(s), uuid.UUID(lid), True)
    assert row.completed is True and row.completed_at is not None
    first = row.completed_at
    again = set_completion(db, auth_user(s), uuid.UUID(lid), True)
    assert again.completed_at == first
    off = set_completion(db, auth_user(s), uuid.UUID(lid), False)
    assert off.completed is False and off.completed_at is None
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 1


def test_stu01_ac7_set_completion_refuses_invisible_lessons_and_writes_nothing(db):
    from errors import ApiError
    from study_lessons.progress import set_completion

    mine, other = make_course(), make_course()
    s = enrolled_student(mine)
    for bad in (make_lesson(other), make_lesson(mine, withdrawn=True), make_draft(mine), str(uuid.uuid4())):
        with pytest.raises(ApiError):
            set_completion(db, auth_user(s), uuid.UUID(bad), True)
        db.rollback()
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 0


# ------------------------------------------------------------------ publish_lesson (hand-over to TEA-03)
def draft_with_topic(course_id, topic_id, title="Notes title", content="Notes body\nline two"):
    """A study_note_draft whose source material sits in `topic_id` (None = no topic)."""
    mid, did = uid(), uid()
    sql("INSERT INTO material(id, course_id, topic_id, uploaded_by, title, original_filename, media_type, "
        "size_bytes) VALUES (%s, %s, %s, 'demo-teacher', 'Source', 's.txt', 'text/plain', 1)",
        (mid, course_id, topic_id))
    sql("INSERT INTO study_note_draft(id, course_id, source_material_id, created_by, title, content, "
        "source_title, updated_by) VALUES (%s, %s, %s, 'demo-teacher', %s, %s, 'Source', 'demo-teacher')",
        (did, course_id, mid, title, content))
    return did


def load_draft(db, draft_id):
    from teacher_materials.models import StudyNoteDraft

    return db.get(StudyNoteDraft, uuid.UUID(draft_id))


def test_stu01_publish_lesson_copies_title_content_course_topic_and_draft_id(db):
    from study_lessons.publish import publish_lesson

    cid = make_course()
    topic = make_topic(cid, "Testing")
    did = draft_with_topic(cid, topic, title="Notes title", content="Notes body\nline two")
    teacher = auth_user("demo-teacher", "teacher")
    lesson = publish_lesson(db, load_draft(db, did), teacher)
    db.commit()
    assert lesson.title == "Notes title" and lesson.content == "Notes body\nline two"
    assert str(lesson.course_id) == cid and str(lesson.topic_id) == topic
    assert str(lesson.source_draft_id) == did and lesson.published_by == "demo-teacher"
    assert lesson.withdrawn_at is None and lesson.published_at is not None
    row = sql("SELECT course_id::text, topic_id::text, title, content, source_draft_id::text, published_by, "
              "withdrawn_at FROM published_lesson WHERE id = %s", (str(lesson.id),))
    assert row == [(cid, topic, "Notes title", "Notes body\nline two", did, "demo-teacher", None)]


def test_stu01_publish_lesson_keeps_a_null_topic_null(db):
    from study_lessons.publish import publish_lesson

    cid = make_course()
    did = draft_with_topic(cid, None)
    lesson = publish_lesson(db, load_draft(db, did), auth_user("demo-teacher", "teacher"))
    db.commit()
    assert lesson.topic_id is None
    assert sql("SELECT topic_id FROM published_lesson WHERE id = %s", (str(lesson.id),)) == [(None,)]


def test_stu01_publish_lesson_makes_the_lesson_readable_by_members_only(db):
    from study_lessons.publish import publish_lesson
    from stu01_helpers import get_lesson

    cid = make_course()
    member, outsider = enrolled_student(cid), enrolled_student()
    did = draft_with_topic(cid, None, title="Published via helper", content="Visible text")
    lesson = publish_lesson(db, load_draft(db, did), auth_user("demo-teacher", "teacher"))
    db.commit()
    r = get_lesson(member, str(lesson.id))
    assert r.status_code == 200 and r.json()["title"] == "Published via helper"
    assert r.json()["topic"] == {"id": None, "name": "General"}
    assert get_lesson(outsider, str(lesson.id)).status_code == 404


def test_stu01_publish_lesson_is_a_snapshot_later_draft_edits_do_not_change_it(db):
    from study_lessons.publish import publish_lesson

    cid = make_course()
    did = draft_with_topic(cid, None, title="Original", content="Original body")
    lesson = publish_lesson(db, load_draft(db, did), auth_user("demo-teacher", "teacher"))
    db.commit()
    sql("UPDATE study_note_draft SET title = 'Edited', content = 'Edited body' WHERE id = %s", (did,))
    assert sql("SELECT title, content FROM published_lesson WHERE id = %s", (str(lesson.id),)) == [
        ("Original", "Original body")]


def test_stu01_publish_lesson_republishing_creates_a_new_lesson_with_a_new_id(db):
    from study_lessons.publish import publish_lesson

    cid = make_course()
    did = draft_with_topic(cid, None)
    teacher = auth_user("demo-teacher", "teacher")
    first = publish_lesson(db, load_draft(db, did), teacher)
    db.commit()
    second = publish_lesson(db, load_draft(db, did), teacher)
    db.commit()
    assert first.id != second.id
    assert sql("SELECT count(*) FROM published_lesson WHERE source_draft_id = %s", (did,))[0][0] == 2


def test_stu01_publish_lesson_deleting_the_draft_keeps_the_lesson(db):
    from study_lessons.publish import publish_lesson

    cid = make_course()
    did = draft_with_topic(cid, None)
    lesson = publish_lesson(db, load_draft(db, did), auth_user("demo-teacher", "teacher"))
    db.commit()
    db.expire_all()
    sql("DELETE FROM study_note_draft WHERE id = %s", (did,))
    assert sql("SELECT source_draft_id FROM published_lesson WHERE id = %s", (str(lesson.id),)) == [(None,)]
