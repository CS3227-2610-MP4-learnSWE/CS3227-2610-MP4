"""The single rule for which lessons a student may read: published, not withdrawn, member course."""
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser
from errors import ApiError
from study_lessons.models import PublishedLesson
from teacher_materials.models import CourseMembership


def visible_lessons(user: AuthUser) -> Select[tuple[PublishedLesson]]:
    """Selectable of the lessons this user may read; add filters and ordering to it."""
    return (
        select(PublishedLesson)
        .join(CourseMembership, CourseMembership.course_id == PublishedLesson.course_id)
        .where(CourseMembership.user_id == user.id, PublishedLesson.withdrawn_at.is_(None))
    )


def get_visible_lesson(db: Session, user: AuthUser, lesson_id: UUID) -> PublishedLesson:
    """The lesson, or the same 404 for unknown, withdrawn, draft and non-member ids."""
    lesson = db.scalar(visible_lessons(user).where(PublishedLesson.id == lesson_id))
    if lesson is None:
        raise ApiError(404, "not_found", "Lesson not found.")
    return lesson
