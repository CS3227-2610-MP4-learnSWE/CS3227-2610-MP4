"""Publish a teacher's note draft as an immutable lesson snapshot (called by the TEA-03 publish route)."""
from uuid import UUID

from sqlalchemy.orm import Session

from auth.dependencies import AuthUser
from study_lessons.models import PublishedLesson
from teacher_materials.models import Material, StudyNoteDraft


def publish_lesson(db: Session, draft: StudyNoteDraft, teacher: AuthUser, *, title: str | None = None, topic_id: UUID | None = None) -> PublishedLesson:
    """Copy the draft into a new lesson in the source material's course and topic.

    The caller has already checked that the teacher owns the draft's course. The caller commits.
    """
    material = db.get(Material, draft.source_material_id)
    lesson = PublishedLesson(
        course_id=draft.course_id,
        topic_id=topic_id if topic_id is not None else material.topic_id if material else None,
        title=draft.title if title is None else title,
        content=draft.content,
        source_draft_id=draft.id,
        source_version=draft.version,
        published_by=teacher.id,
    )
    db.add(lesson)
    db.flush()
    db.refresh(lesson)
    return lesson
