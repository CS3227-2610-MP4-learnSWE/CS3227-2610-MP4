"""Published MCQ snapshots; notes reuse PublishedLesson."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class PublishedPracticeSet(Base):
    __tablename__ = "published_practice_set"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    topic_id: Mapped[UUID] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(String(200))
    source_draft_id: Mapped[UUID] = mapped_column(Uuid, unique=True)
    source_version: Mapped[int] = mapped_column(Integer)
    published_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]),
        ForeignKeyConstraint(["source_draft_id", "course_id"], ["mcq_draft_batch.id", "mcq_draft_batch.course_id"], ondelete="RESTRICT"),
        CheckConstraint("source_version >= 1", name="ck_published_set_version"),
        CheckConstraint("char_length(title) between 1 and 200", name="ck_published_set_title"),
    )


class PublishedPracticeQuestion(Base):
    __tablename__ = "published_practice_question"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    set_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("published_practice_set.id", ondelete="RESTRICT"))
    source_question_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("mcq_draft_question.id", ondelete="RESTRICT"))
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(200))
    choices: Mapped[list[str]] = mapped_column(JSONB)
    correct_choice_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("set_id", "position"), UniqueConstraint("set_id", "source_question_id"),
        CheckConstraint("position between 1 and 3", name="ck_published_question_position"),
        CheckConstraint("correct_choice_index between 0 and 3", name="ck_published_question_answer"),
        CheckConstraint("char_length(question) between 1 and 200", name="ck_published_question_text"),
        CheckConstraint("char_length(explanation) between 1 and 200", name="ck_published_question_explanation"),
        CheckConstraint("CASE WHEN jsonb_typeof(choices) = 'array' THEN jsonb_array_length(choices) = 4 ELSE false END", name="ck_published_choices_count"),
        *[CheckConstraint(f"jsonb_typeof(choices->{i}) = 'string' AND char_length(choices->>{i}) between 1 and 80", name=f"ck_published_choice_{i}") for i in range(4)],
    )
