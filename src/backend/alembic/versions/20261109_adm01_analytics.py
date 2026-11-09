"""ADM-01 feature analytics tables, and the ADM-06 usage-label extension for the "ADM-01" label."""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20261109_adm01_analytics"
down_revision = "20261109_adm03_analysis"
branch_labels = None
depends_on = None

OLD_FEATURES = "feature in ('STU-03', 'TEA-02', 'ADM-03')"
NEW_FEATURES = "feature in ('STU-03', 'TEA-02', 'ADM-03', 'ADM-01')"
OUTCOMES = "outcome in ('pending', 'success', 'failure')"


def _timestamp(name):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def _optional_timestamp(name):
    return sa.Column(name, sa.DateTime(timezone=True))


def _id():
    return sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True)


def _user(name="user_id"):
    return sa.Column(name, sa.String(64), sa.ForeignKey("user.id"), nullable=False)


def upgrade():
    # ADM-06: permit the new usage label and seed its (disabled) coverage row, as 20261106_adm06_ai_usage does.
    op.drop_constraint("ck_ai_attempt_feature", "ai_service_attempts", type_="check")
    op.create_check_constraint("ck_ai_attempt_feature", "ai_service_attempts", NEW_FEATURES)
    op.drop_constraint("ck_ai_coverage_feature", "ai_usage_coverage", type_="check")
    op.create_check_constraint("ck_ai_coverage_feature", "ai_usage_coverage", NEW_FEATURES)
    op.execute(sa.text("INSERT INTO ai_usage_coverage (feature, enabled) VALUES ('ADM-01', false)"))

    meta = op.create_table("analytics_meta",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False))
    op.bulk_insert(meta, [{"key": "recording_started_at", "value": datetime.now(timezone.utc).isoformat()}])

    op.create_table("analytics_session",
        _id(), _user(),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("activity_type", sa.Text(), nullable=False),
        sa.Column("activity_ref", sa.Text(), nullable=False),
        _timestamp("started_at"), _timestamp("last_message_at"), _optional_timestamp("ended_at"),
        sa.Column("end_reason", sa.Text()),
        sa.CheckConstraint("end_reason is null or end_reason in ('activity_ended', 'inactivity', 'new_activity')",
                           name="ck_analytics_session_end_reason"))
    op.create_index("uq_analytics_session_open", "analytics_session", ["user_id"], unique=True,
                    postgresql_where=sa.text("ended_at IS NULL"))
    op.create_index("ix_analytics_session_started", "analytics_session", ["started_at"])

    op.create_table("analytics_chat_request",
        _id(), _user(),
        sa.Column("role", sa.Text(), nullable=False, server_default="student"),
        sa.Column("activity_type", sa.Text()),
        sa.Column("activity_ref", sa.Text()),
        sa.Column("session_id", sa.BigInteger(), sa.ForeignKey("analytics_session.id")),
        _timestamp("received_at"), _optional_timestamp("completed_at"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("outcome", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(OUTCOMES, name="ck_analytics_chat_outcome"),
        sa.CheckConstraint("activity_type is null or activity_type in ('practice_attempt', 'lesson')",
                           name="ck_analytics_chat_activity_type"))
    op.create_index("ix_analytics_chat_received", "analytics_chat_request", ["received_at"])
    op.create_index("ix_analytics_chat_user_received", "analytics_chat_request", ["user_id", "received_at"])
    op.create_index("ix_analytics_chat_activity_received", "analytics_chat_request", ["activity_type", "received_at"])

    op.create_table("analytics_practice_attempt",
        sa.Column("attempt_ref", sa.Text(), primary_key=True),
        _user(),
        sa.Column("practice_set_id", sa.Text(), nullable=False),
        _timestamp("started_at"), _optional_timestamp("submitted_at"),
        sa.CheckConstraint("char_length(attempt_ref) between 1 and 100", name="ck_analytics_attempt_ref"))
    op.create_index("ix_analytics_practice_started", "analytics_practice_attempt", ["started_at"])

    op.create_table("analytics_generation_attempt",
        _id(),
        sa.Column("workflow", sa.Text(), nullable=False),
        _user(),
        _timestamp("accepted_at"), _optional_timestamp("completed_at"),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("outcome", sa.Text(), nullable=False, server_default="pending"),
        sa.CheckConstraint("workflow in ('study_notes', 'mcq_batch')", name="ck_analytics_generation_workflow"),
        sa.CheckConstraint(OUTCOMES, name="ck_analytics_generation_outcome"))
    op.create_index("ix_analytics_generation_workflow_accepted", "analytics_generation_attempt",
                    ["workflow", "accepted_at"])

    op.create_table("analytics_grading_item",
        _id(),
        sa.Column("workflow", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("generation_workflow", sa.Text()),
        _timestamp("received_at"),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("request_text", sa.Text()),
        sa.Column("response_text", sa.Text()),
        sa.Column("context_text", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("failure_code", sa.Text()),
        _optional_timestamp("graded_at"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_type", "source_id", name="uq_analytics_grading_item_source"),
        sa.CheckConstraint("workflow in ('student_exercise', 'teacher_lesson_planning')", name="ck_analytics_item_workflow"),
        sa.CheckConstraint("source_type in ('chat_request', 'generation_attempt')", name="ck_analytics_item_source_type"),
        sa.CheckConstraint("status in ('pending', 'graded', 'grading_failed')", name="ck_analytics_item_status"))
    op.create_index("ix_analytics_item_workflow_received", "analytics_grading_item", ["workflow", "received_at"])

    op.create_table("analytics_grade",
        _id(),
        sa.Column("item_id", sa.BigInteger(), sa.ForeignKey("analytics_grading_item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("score", sa.SmallInteger()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.UniqueConstraint("item_id", "dimension", name="uq_analytics_grade_item_dimension"),
        sa.CheckConstraint("dimension in ('relevance', 'factual_accuracy', 'clarity', 'safety')",
                           name="ck_analytics_grade_dimension"),
        sa.CheckConstraint("(state = 'graded' and score between 1 and 5) or (state = 'unassessable' and score is null)",
                           name="ck_analytics_grade_score"),
        sa.CheckConstraint("char_length(reason) between 1 and 300", name="ck_analytics_grade_reason"))

    op.create_table("analytics_grading_run",
        _id(),
        sa.Column("workflow", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_graded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_code", sa.Text()),
        _user("requested_by"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        _optional_timestamp("started_at"), _optional_timestamp("finished_at"),
        sa.CheckConstraint("status in ('queued', 'running', 'completed', 'failed')", name="ck_analytics_run_status"))
    op.create_index("uq_analytics_grading_run_active", "analytics_grading_run", [sa.text("(true)")], unique=True,
                    postgresql_where=sa.text("status IN ('queued', 'running')"))


def downgrade():
    for table in ("analytics_grading_run", "analytics_grade", "analytics_grading_item", "analytics_generation_attempt",
                  "analytics_practice_attempt", "analytics_chat_request", "analytics_session", "analytics_meta"):
        op.drop_table(table)
    op.execute(sa.text("DELETE FROM ai_service_attempts WHERE feature = 'ADM-01'"))
    op.execute(sa.text("DELETE FROM ai_usage_coverage WHERE feature = 'ADM-01'"))
    op.drop_constraint("ck_ai_attempt_feature", "ai_service_attempts", type_="check")
    op.create_check_constraint("ck_ai_attempt_feature", "ai_service_attempts", OLD_FEATURES)
    op.drop_constraint("ck_ai_coverage_feature", "ai_usage_coverage", type_="check")
    op.create_check_constraint("ck_ai_coverage_feature", "ai_usage_coverage", OLD_FEATURES)
