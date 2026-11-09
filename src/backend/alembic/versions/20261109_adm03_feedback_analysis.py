"""ADM-03 stored feedback analyses (no automatic retention)."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261109_adm03_analysis"
down_revision = "20261107_adm04_messaging"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("feedback_analyses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("admin_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("form_id", sa.Uuid(), sa.ForeignKey("feedback_forms.id"), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("expected_count", sa.Integer()),
        sa.Column("response_count", sa.Integer(), nullable=False),
        sa.Column("label_map", JSONB(), nullable=False),
        sa.Column("label_dates", JSONB(), nullable=False),
        sa.Column("aggregates", JSONB(), nullable=False),
        sa.Column("free_text_total", sa.Integer(), nullable=False),
        sa.Column("free_text_used", sa.Integer(), nullable=False),
        sa.Column("ai_status", sa.String(16), nullable=False),
        sa.Column("ai_done", sa.Integer(), nullable=False),
        sa.Column("ai_total", sa.Integer(), nullable=False),
        sa.Column("ai_result", JSONB()),
        sa.Column("ai_error", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("admin_id", "request_id", name="uq_feedback_analyses_admin_request"),
        sa.CheckConstraint("ai_status in ('running','complete','failed')", name="ck_feedback_analyses_status"))
    op.create_index("ix_feedback_analyses_admin_id", "feedback_analyses", ["admin_id"])
    op.create_index("ix_feedback_analyses_history", "feedback_analyses",
                    ["admin_id", sa.text("created_at DESC"), sa.text("id DESC")])
    op.create_index("uq_feedback_analyses_one_running", "feedback_analyses", ["admin_id"], unique=True,
                    postgresql_where=sa.text("ai_status = 'running'"))


def downgrade():
    op.drop_table("feedback_analyses")
