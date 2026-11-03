"""Persistent TEA-01 records shared with later course features."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, LargeBinary, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("role in ('student', 'teacher', 'admin')"),)


class Course(Base):
    __tablename__ = "course"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CourseMembership(Base):
    __tablename__ = "course_membership"
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"), primary_key=True)


class Topic(Base):
    __tablename__ = "topic"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("course_id", "name"), UniqueConstraint("id", "course_id"),)


class Material(Base):
    __tablename__ = "material"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    topic_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]), CheckConstraint("size_bytes between 1 and 10485760"), UniqueConstraint("id", "course_id", name="uq_material_id_course"))


class MaterialFile(Base):
    __tablename__ = "material_file"
    material_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("material.id", ondelete="CASCADE"), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    __table_args__ = (CheckConstraint("octet_length(content) between 1 and 10485760", name="ck_material_file_length"),)


class StudyNoteDraft(Base):
    __tablename__ = "study_note_draft"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    source_material_id: Mapped[UUID] = mapped_column(Uuid)
    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source_title: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    updated_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_note_version_positive"),
        ForeignKeyConstraint(["source_material_id", "course_id"], ["material.id", "material.course_id"]),
        CheckConstraint("char_length(content) between 1 and 2000", name="ck_note_content_length"),
    )


class McqDraftBatch(Base):
    __tablename__ = "mcq_draft_batch"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("course.id"))
    source_material_id: Mapped[UUID] = mapped_column(Uuid)
    created_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    source_title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (ForeignKeyConstraint(["source_material_id", "course_id"], ["material.id", "material.course_id"]),)


class McqDraftQuestion(Base):
    __tablename__ = "mcq_draft_question"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("mcq_draft_batch.id"))
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(200))
    choices: Mapped[list[str]] = mapped_column(JSONB)
    correct_choice_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(String(200))
    __table_args__ = (
        UniqueConstraint("batch_id", "position"),
        CheckConstraint("position between 1 and 3", name="ck_mcq_position"),
        CheckConstraint("correct_choice_index between 0 and 3", name="ck_mcq_answer"),
        CheckConstraint("char_length(question) between 1 and 200", name="ck_mcq_question_length"),
        CheckConstraint("char_length(explanation) between 1 and 200", name="ck_mcq_explanation_length"),
        CheckConstraint("CASE WHEN jsonb_typeof(choices) = 'array' THEN jsonb_array_length(choices) = 4 ELSE false END", name="ck_mcq_choices_count"),
        *[CheckConstraint(f"jsonb_typeof(choices->{i}) = 'string' AND char_length(choices->>{i}) between 1 and 80", name=f"ck_mcq_choice_{i}") for i in range(4)],
    )
