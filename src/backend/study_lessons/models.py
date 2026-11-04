"""Published lesson snapshots and per-student completion records."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class PublishedLesson(Base):
    __tablename__ = "published_lesson"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    topic_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source_draft_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("study_note_draft.id", ondelete="SET NULL"), nullable=True)
    published_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]),
        CheckConstraint("char_length(title) between 1 and 200", name="ck_published_lesson_title_length"),
        CheckConstraint("char_length(content) between 1 and 2000", name="ck_published_lesson_content_length"),
        UniqueConstraint("id", "course_id", name="uq_published_lesson_id_course"),
        Index("ix_published_lesson_course", "course_id", "withdrawn_at"),
    )


class LessonCompletion(Base):
    __tablename__ = "lesson_completion"
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    lesson_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    course_id: Mapped[UUID] = mapped_column(Uuid)
    completed: Mapped[bool] = mapped_column(Boolean)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        ForeignKeyConstraint(["lesson_id", "course_id"], ["published_lesson.id", "published_lesson.course_id"]),
        CheckConstraint("completed = (completed_at is not null)", name="ck_lesson_completion_state"),
        Index("ix_lesson_completion_user_course", "user_id", "course_id"),
        Index("ix_lesson_completion_lesson", "lesson_id"),
    )
