"""Persistent survey records. Private drafts are separate from collected responses."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class FeedbackForm(Base):
    __tablename__ = "feedback_forms"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(2000))
    association: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    questions: Mapped[list] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(16), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audience_role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    __table_args__ = (CheckConstraint("version >= 1"), CheckConstraint("state in ('draft','open','closed')"),)


class FeedbackRecipient(Base):
    __tablename__ = "feedback_recipients"
    form_id: Mapped[UUID] = mapped_column(ForeignKey("feedback_forms.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    display_name_snapshot: Mapped[str] = mapped_column(String(200))
    role_snapshot: Mapped[str] = mapped_column(String(16))
    inbox_id: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid4)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FeedbackResponse(Base):
    __tablename__ = "feedback_responses"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("feedback_forms.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    display_name_snapshot: Mapped[str] = mapped_column(String(200))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    form_snapshot: Mapped[dict] = mapped_column(JSONB)
    answers: Mapped[list] = mapped_column(JSONB)
    __table_args__ = (UniqueConstraint("form_id", "user_id"), ForeignKeyConstraint(["form_id", "user_id"], ["feedback_recipients.form_id", "feedback_recipients.user_id"]),)


class FeedbackResponseDraft(Base):
    __tablename__ = "feedback_response_drafts"
    form_id: Mapped[UUID] = mapped_column(ForeignKey("feedback_forms.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    answers: Mapped[list] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("version >= 1"), ForeignKeyConstraint(["form_id", "user_id"], ["feedback_recipients.form_id", "feedback_recipients.user_id"]),)
