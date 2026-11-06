"""Reviewed administrative messages and durable private inbox delivery."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261107_adm04_messaging"
down_revision = "20261107_adm02_feedback"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("admin_message_previews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_admin_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("feedback_response_id", sa.Uuid(), sa.ForeignKey("feedback_responses.id")),
        sa.Column("audience_role", sa.String(16), nullable=False),
        sa.Column("audience_mode", sa.String(16)),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("body", sa.String(5000), nullable=False),
        sa.Column("recipients", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_message_id", sa.Uuid()))
    op.create_index("ix_admin_message_previews_owner_admin_id", "admin_message_previews", ["owner_admin_id"])
    op.create_table("admin_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("preview_id", sa.Uuid(), sa.ForeignKey("admin_message_previews.id"), unique=True, nullable=False),
        sa.Column("sender_admin_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("source_feedback_response_id", sa.Uuid(), sa.ForeignKey("feedback_responses.id")),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("body", sa.String(5000), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_admin_messages_sent_at", "admin_messages", ["sent_at"])
    op.create_table("admin_message_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("message_id", sa.Uuid(), sa.ForeignKey("admin_messages.id"), nullable=False),
        sa.Column("recipient_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("message_id", "recipient_id"))
    op.create_index("ix_admin_message_deliveries_message_id", "admin_message_deliveries", ["message_id"])
    op.create_index("ix_admin_message_deliveries_recipient_id", "admin_message_deliveries", ["recipient_id"])


def downgrade():
    op.drop_table("admin_message_deliveries")
    op.drop_table("admin_messages")
    op.drop_table("admin_message_previews")
