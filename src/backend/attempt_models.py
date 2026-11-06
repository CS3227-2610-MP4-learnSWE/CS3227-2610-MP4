"""STU-04 persistent practice attempts. Holds the student's selections and ids, never the answer key."""
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from teacher_materials.models import Base


class PracticeAttempt(Base):
    __tablename__ = "practice_attempt"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True))
    student_id: Mapped[str] = mapped_column(String(64), ForeignKey("user.id", ondelete="CASCADE"))
    set_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    answers: Mapped[dict[str, str]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    score_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    correct_question_ids: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("seq", name="uq_practice_attempt_seq"),
        CheckConstraint("status in ('in_progress', 'submitted')", name="ck_practice_attempt_status"),
        CheckConstraint("jsonb_typeof(answers) = 'object'", name="ck_practice_attempt_answers"),
        CheckConstraint("jsonb_typeof(correct_question_ids) = 'array'", name="ck_practice_attempt_correct_ids"),
        CheckConstraint(
            "(status = 'submitted' and score_correct is not null and score_total is not null "
            "and key_version is not null and submitted_at is not null) "
            "or (status = 'in_progress' and score_correct is null and score_total is null "
            "and key_version is null and submitted_at is null and correct_question_ids = '[]'::jsonb)",
            name="ck_practice_attempt_state",
        ),
        CheckConstraint("score_correct is null or (score_correct between 0 and score_total)", name="ck_practice_attempt_score"),
        Index("ix_practice_attempt_student_set", "student_id", "set_id", "seq"),
        Index("ix_practice_attempt_submitted", "student_id", "set_id", "submitted_at", postgresql_where=text("status = 'submitted'")),
    )
