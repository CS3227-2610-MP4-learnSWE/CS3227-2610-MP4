"""Add login columns to user and the server-side auth_session table."""
from alembic import op
import sqlalchemy as sa

revision = "20261103_shr01_auth"
down_revision = "20261102_tea01_db_storage"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("email", sa.String(254), nullable=True))
    op.add_column("user", sa.Column("password_hash", sa.String(255), nullable=True))
    op.create_check_constraint("ck_user_email_lower", "user", "email = lower(email)")
    op.create_index("ux_user_email", "user", ["email"], unique=True)
    op.create_table("auth_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auth_session_token_hash", "auth_session", ["token_hash"], unique=True)
    op.create_index("ix_auth_session_user_id", "auth_session", ["user_id"])
    op.create_index("ix_auth_session_expires_at", "auth_session", ["expires_at"])


def downgrade():
    op.drop_table("auth_session")
    op.drop_index("ux_user_email", table_name="user")
    op.drop_constraint("ck_user_email_lower", "user", type_="check")
    op.drop_column("user", "password_hash")
    op.drop_column("user", "email")
