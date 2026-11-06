"""Persistent targeted surveys, private response drafts and submitted snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261107_adm02_feedback"
down_revision = "20261106_adm06_ai_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("feedback_forms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("association", JSONB(), nullable=True),
        sa.Column("questions", JSONB(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("audience_role", sa.String(16)),
        sa.CheckConstraint("version >= 1"),
        sa.CheckConstraint("state in ('draft','open','closed')"),
    )
    op.create_table("feedback_recipients",
        sa.Column("form_id", sa.Uuid(), sa.ForeignKey("feedback_forms.id"), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id"), primary_key=True),
        sa.Column("display_name_snapshot", sa.String(200), nullable=False),
        sa.Column("role_snapshot", sa.String(16), nullable=False),
        sa.Column("inbox_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_table("feedback_responses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("form_id", sa.Uuid(), sa.ForeignKey("feedback_forms.id"), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("display_name_snapshot", sa.String(200), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("form_snapshot", JSONB(), nullable=False),
        sa.Column("answers", JSONB(), nullable=False),
        sa.UniqueConstraint("form_id", "user_id"),
        sa.ForeignKeyConstraint(["form_id", "user_id"], ["feedback_recipients.form_id", "feedback_recipients.user_id"]),
    )
    op.create_table("feedback_response_drafts",
        sa.Column("form_id", sa.Uuid(), sa.ForeignKey("feedback_forms.id"), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id"), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("answers", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1"),
        sa.ForeignKeyConstraint(["form_id", "user_id"], ["feedback_recipients.form_id", "feedback_recipients.user_id"]),
    )


def downgrade():
    op.drop_table("feedback_response_drafts")
    op.drop_table("feedback_responses")
    op.drop_table("feedback_recipients")
    op.drop_table("feedback_forms")
