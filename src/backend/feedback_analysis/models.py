"""Stored analyses: statistics, AI result or failure record, and the private label map."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class FeedbackAnalysis(Base):
    __tablename__ = "feedback_analyses"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    admin_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("feedback_forms.id"))
    mode: Mapped[str] = mapped_column(String(16))
    expected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_count: Mapped[int] = mapped_column(Integer)
    label_map: Mapped[dict] = mapped_column(JSONB)
    label_dates: Mapped[dict] = mapped_column(JSONB)
    aggregates: Mapped[list] = mapped_column(JSONB)
    free_text_total: Mapped[int] = mapped_column(Integer)
    free_text_used: Mapped[int] = mapped_column(Integer)
    ai_status: Mapped[str] = mapped_column(String(16))
    ai_done: Mapped[int] = mapped_column(Integer)
    ai_total: Mapped[int] = mapped_column(Integer)
    ai_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_error: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ai_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("admin_id", "request_id", name="uq_feedback_analyses_admin_request"),
        Index("ix_feedback_analyses_history", "admin_id", text("created_at DESC"), text("id DESC")),
        Index("uq_feedback_analyses_one_running", "admin_id", unique=True, postgresql_where=text("ai_status = 'running'")),
    )
