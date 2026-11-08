"""Completion reads and the one write. STU-04 must use these helpers, not the tables."""
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser
from study_lessons.access import get_visible_lesson
from study_lessons.models import LessonCompletion, PublishedLesson
from teacher_materials.models import Course, CourseMembership, User


@dataclass(frozen=True)
class CourseCounts:
    lesson_count: int
    completed_count: int


@dataclass(frozen=True)
class CompletedLesson:
    lesson_id: UUID
    course_id: UUID
    topic_id: UUID | None
    title: str
    completed_at: datetime


@dataclass(frozen=True)
class LessonCompletionStat:
    lesson_id: UUID
    title: str
    topic_id: UUID | None
    completed_students: int


def member_courses(db: Session, user_id: str) -> list[tuple[UUID, str]]:
    """The user's member courses as (id, title), ordered by lower(title) then id."""
    query = (
        select(Course.id, Course.title)
        .join(CourseMembership, CourseMembership.course_id == Course.id)
        .where(CourseMembership.user_id == user_id)
        .order_by(func.lower(Course.title), Course.id)
    )
    return [(cid, title) for cid, title in db.execute(query)]


def completion_counts(db: Session, user_id: str, course_ids: Sequence[UUID] | None = None) -> dict[UUID, CourseCounts]:
    """Per member course: visible lessons and how many the user completed. Non-member ids are absent."""
    query = (
        select(
            CourseMembership.course_id,
            func.count(PublishedLesson.id),
            func.count(LessonCompletion.lesson_id).filter(LessonCompletion.completed.is_(True)),
        )
        .select_from(CourseMembership)
        .outerjoin(
            PublishedLesson,
            (PublishedLesson.course_id == CourseMembership.course_id) & PublishedLesson.withdrawn_at.is_(None),
        )
        .outerjoin(
            LessonCompletion,
            (LessonCompletion.lesson_id == PublishedLesson.id) & (LessonCompletion.user_id == CourseMembership.user_id),
        )
        .where(CourseMembership.user_id == user_id)
        .group_by(CourseMembership.course_id)
    )
    if course_ids is not None:
        query = query.where(CourseMembership.course_id.in_(list(course_ids)))
    return {course: CourseCounts(total, done) for course, total, done in db.execute(query)}


def completed_lessons(db: Session, user_id: str) -> list[CompletedLesson]:
    """Completed, still-visible lessons of the user, newest completion first."""
    query = (
        select(PublishedLesson.id, PublishedLesson.course_id, PublishedLesson.topic_id, PublishedLesson.title, LessonCompletion.completed_at)
        .join(LessonCompletion, LessonCompletion.lesson_id == PublishedLesson.id)
        .join(CourseMembership, CourseMembership.course_id == PublishedLesson.course_id)
        .where(
            LessonCompletion.user_id == user_id,
            LessonCompletion.completed.is_(True),
            CourseMembership.user_id == user_id,
            PublishedLesson.withdrawn_at.is_(None),
        )
        .order_by(LessonCompletion.completed_at.desc(), PublishedLesson.id)
    )
    return [CompletedLesson(*row) for row in db.execute(query)]


def set_completion(db: Session, user: AuthUser, lesson_id: UUID, completed: bool) -> LessonCompletion:
    """Store the requested state with one upsert, so concurrent requests keep one row."""
    lesson = get_visible_lesson(db, user, lesson_id)
    now = func.now()
    stamp = now if completed else None
    insertion = insert(LessonCompletion).values(
        user_id=user.id, lesson_id=lesson.id, course_id=lesson.course_id, completed=completed, completed_at=stamp, updated_at=now
    )
    upsert = insertion.on_conflict_do_update(
        index_elements=[LessonCompletion.user_id, LessonCompletion.lesson_id],
        set_={
            "completed": insertion.excluded.completed,
            "completed_at": case(
                (insertion.excluded.completed, func.coalesce(LessonCompletion.completed_at, insertion.excluded.completed_at)),
                else_=None,
            ),
            "updated_at": now,
        },
    ).returning(LessonCompletion)
    row = db.scalars(upsert, execution_options={"populate_existing": True}).one()
    db.commit()
    return row


def course_student_ids(db: Session, course_ids: Sequence[UUID]) -> dict[UUID, frozenset[str]]:
    """Current members with account role 'student' per course; every requested course is present (empty set if none)."""
    students: dict[UUID, set[str]] = {course_id: set() for course_id in course_ids}
    if students:
        query = (
            select(CourseMembership.course_id, CourseMembership.user_id)
            .join(User, User.id == CourseMembership.user_id)
            .where(CourseMembership.course_id.in_(list(students)), User.role == "student")
        )
        for course_id, user_id in db.execute(query):
            students[course_id].add(user_id)
    return {course_id: frozenset(ids) for course_id, ids in students.items()}


def lesson_completion_stats(
    db: Session, course_id: UUID, student_ids: Collection[str], start: datetime | None, end: datetime
) -> list[LessonCompletionStat]:
    """Non-withdrawn lessons ordered published_at, id, with how many of student_ids completed each in [start, end)."""
    lessons = db.execute(
        select(PublishedLesson.id, PublishedLesson.title, PublishedLesson.topic_id)
        .where(PublishedLesson.course_id == course_id, PublishedLesson.withdrawn_at.is_(None))
        .order_by(PublishedLesson.published_at, PublishedLesson.id)
    ).all()
    counts: dict[UUID, int] = {}
    if lessons and student_ids:
        done = (
            select(LessonCompletion.lesson_id, func.count())
            .where(
                LessonCompletion.course_id == course_id,
                LessonCompletion.user_id.in_(list(student_ids)),
                LessonCompletion.completed.is_(True),
                LessonCompletion.completed_at < end,
            )
            .group_by(LessonCompletion.lesson_id)
        )
        if start is not None:
            done = done.where(LessonCompletion.completed_at >= start)
        counts = dict(db.execute(done).all())
    return [LessonCompletionStat(lid, title, topic_id, counts.get(lid, 0)) for lid, title, topic_id in lessons]
