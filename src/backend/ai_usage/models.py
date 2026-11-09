"""Persistent attempt metadata; never store provider content or identities."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class ServiceAttempt(Base):
    __tablename__ = "ai_service_attempts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    feature: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    outcome: Mapped[str] = mapped_column(String(16))
    input_tokens: Mapped[int | None] = mapped_column(BigInteger)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger)
    __table_args__ = (
        CheckConstraint("feature in ('STU-03', 'TEA-02', 'ADM-03', 'ADM-01')", name="ck_ai_attempt_feature"),
        CheckConstraint("outcome in ('pending', 'success', 'rate_limit', 'other_failure')", name="ck_ai_attempt_outcome"),
        CheckConstraint("(outcome = 'pending' and finished_at is null) or (outcome <> 'pending' and finished_at is not null)", name="ck_ai_attempt_finished"),
        CheckConstraint("input_tokens >= 0 and output_tokens >= 0 and total_tokens >= 0", name="ck_ai_attempt_tokens"),
        Index("ix_ai_attempt_feature_started", "feature", "started_at"),
    )


class UsageCoverage(Base):
    __tablename__ = "ai_usage_coverage"
    feature: Mapped[str] = mapped_column(String(16), primary_key=True)
    covered_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    incomplete_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("feature in ('STU-03', 'TEA-02', 'ADM-03', 'ADM-01')", name="ck_ai_coverage_feature"),
        CheckConstraint("not enabled or covered_since is not null", name="ck_ai_coverage_start"),
    )
