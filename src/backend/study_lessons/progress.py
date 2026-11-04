"""Completion reads and the one write. STU-04 must use these helpers, not the tables."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser
from study_lessons.access import get_visible_lesson
from study_lessons.models import LessonCompletion, PublishedLesson
from teacher_materials.models import CourseMembership


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
