"""Publish a teacher's note draft as an immutable lesson snapshot (called by the TEA-03 publish route)."""
from sqlalchemy.orm import Session

from auth.dependencies import AuthUser
from study_lessons.models import PublishedLesson
from teacher_materials.models import Material, StudyNoteDraft


def publish_lesson(db: Session, draft: StudyNoteDraft, teacher: AuthUser) -> PublishedLesson:
    """Copy the draft into a new lesson in the source material's course and topic.

    The caller has already checked that the teacher owns the draft's course. The caller commits.
    """
    material = db.get(Material, draft.source_material_id)
    lesson = PublishedLesson(
        course_id=draft.course_id,
        topic_id=material.topic_id if material else None,
        title=draft.title,
        content=draft.content,
        source_draft_id=draft.id,
        published_by=teacher.id,
    )
    db.add(lesson)
    db.flush()
    db.refresh(lesson)
    return lesson
