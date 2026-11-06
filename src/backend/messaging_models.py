"""Immutable reviewed messages and private per-account delivery state."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class MessagePreview(Base):
    __tablename__ = "admin_message_previews"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_admin_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    feedback_response_id: Mapped[UUID | None] = mapped_column(ForeignKey("feedback_responses.id"), nullable=True)
    audience_role: Mapped[str] = mapped_column(String(16))
    audience_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    subject: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(5000))
    recipients: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_message_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class AdminMessage(Base):
    __tablename__ = "admin_messages"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    preview_id: Mapped[UUID] = mapped_column(ForeignKey("admin_message_previews.id"), unique=True)
    sender_admin_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    kind: Mapped[str] = mapped_column(String(24))
    source_feedback_response_id: Mapped[UUID | None] = mapped_column(ForeignKey("feedback_responses.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(5000))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MessageDelivery(Base):
    __tablename__ = "admin_message_deliveries"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(ForeignKey("admin_messages.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("user.id"), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("message_id", "recipient_id"),)
