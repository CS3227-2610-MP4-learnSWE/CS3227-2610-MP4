"""Add practice_attempt (STU-04): persistent practice attempts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261105_stu04_practice_attempt"
down_revision = "20261104_stu01_lessons"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("practice_attempt",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("student_id", sa.String(64), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("set_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("answers", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("score_correct", sa.Integer(), nullable=True),
        sa.Column("score_total", sa.Integer(), nullable=True),
        sa.Column("key_version", sa.String(16), nullable=True),
        sa.Column("correct_question_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("seq", name="uq_practice_attempt_seq"),
        sa.CheckConstraint("status in ('in_progress', 'submitted')", name="ck_practice_attempt_status"),
        sa.CheckConstraint("jsonb_typeof(answers) = 'object'", name="ck_practice_attempt_answers"),
        sa.CheckConstraint("jsonb_typeof(correct_question_ids) = 'array'", name="ck_practice_attempt_correct_ids"),
        sa.CheckConstraint(
            "(status = 'submitted' and score_correct is not null and score_total is not null "
            "and key_version is not null and submitted_at is not null) "
            "or (status = 'in_progress' and score_correct is null and score_total is null "
            "and key_version is null and submitted_at is null and correct_question_ids = '[]'::jsonb)",
            name="ck_practice_attempt_state"),
        sa.CheckConstraint(
            "score_correct is null or (score_correct between 0 and score_total)", name="ck_practice_attempt_score"))
    op.create_index("ix_practice_attempt_student_set", "practice_attempt", ["student_id", "set_id", "seq"])
    op.create_index("ix_practice_attempt_submitted", "practice_attempt", ["student_id", "set_id", "submitted_at"],
                    postgresql_where=sa.text("status = 'submitted'"))


def downgrade():
    op.drop_table("practice_attempt")
