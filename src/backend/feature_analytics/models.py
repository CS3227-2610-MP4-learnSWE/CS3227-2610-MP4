"""ADM-01 tables (created by the 20261109_adm01_analytics migration). Timestamps are timestamptz, read as UTC."""
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base

_BIG = BigInteger  # PostgreSQL only: bigserial primary keys


class AnalyticsMeta(Base):
    __tablename__ = "analytics_meta"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class AnalyticsSession(Base):
    __tablename__ = "analytics_session"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(Text)
    activity_type: Mapped[str] = mapped_column(Text)
    activity_ref: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalyticsChatRequest(Base):
    __tablename__ = "analytics_chat_request"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    role: Mapped[str] = mapped_column(Text, server_default="student")
    activity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("analytics_session.id"), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsPracticeAttempt(Base):
    __tablename__ = "analytics_practice_attempt"
    attempt_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    practice_set_id: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalyticsGenerationAttempt(Base):
    __tablename__ = "analytics_generation_attempt"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    workflow: Mapped[str] = mapped_column(Text)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, server_default="pending")


class AnalyticsGradingItem(Base):
    __tablename__ = "analytics_grading_item"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    workflow: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(BigInteger)
    generation_workflow: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int] = mapped_column(Integer)
    request_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    failure_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsGrade(Base):
    __tablename__ = "analytics_grade"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("analytics_grading_item.id", ondelete="CASCADE"))
    dimension: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reason: Mapped[str] = mapped_column(Text)


class AnalyticsGradingRun(Base):
    __tablename__ = "analytics_grading_run"
    id: Mapped[int] = mapped_column(_BIG, primary_key=True, autoincrement=True)
    workflow: Mapped[str] = mapped_column(Text)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    items_total: Mapped[int] = mapped_column(Integer, server_default="0")
    items_graded: Mapped[int] = mapped_column(Integer, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    failure_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(64), ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
