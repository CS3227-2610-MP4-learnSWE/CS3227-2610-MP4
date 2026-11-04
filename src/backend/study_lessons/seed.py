"""Idempotent demo lessons for development and demos only.

Run after migrations and teacher_materials.seed:  uv run python -m study_lessons.seed
"""
import os
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from study_lessons.models import PublishedLesson

COURSE = UUID("11111111-1111-4111-8111-111111111111")
TOPIC = UUID("33333333-3333-4333-8333-333333333333")
LESSONS = (
    (
        UUID("55555555-5555-4555-8555-555555555551"),
        TOPIC,
        "Writing a useful test",
        "A useful test checks one behaviour.\nStart with a concrete example, run the real code, and compare the result with an outcome you worked out independently.",
    ),
    (
        UUID("55555555-5555-4555-8555-555555555552"),
        None,
        "Keep changes small",
        "Small, focused changes are easier to review.\nChange one thing, give it a clear name, and explain why in a short message.",
    ),
)


def seed_lessons(session: Session) -> None:
    for lesson_id, topic_id, title, content in LESSONS:
        if session.get(PublishedLesson, lesson_id) is None:
            session.add(
                PublishedLesson(id=lesson_id, course_id=COURSE, topic_id=topic_id, title=title, content=content, published_by="demo-teacher")
            )
    session.commit()


if __name__ == "__main__":
    with Session(create_engine(os.environ["DATABASE_URL"])) as session:
        seed_lessons(session)
