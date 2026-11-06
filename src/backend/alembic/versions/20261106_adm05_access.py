"""Persistent account access lifecycle; retain account identity and history."""
from alembic import op
import sqlalchemy as sa

revision = "20261106_adm05_access"
down_revision = "20261105_tea03_publications"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("access_status", sa.String(16), nullable=False, server_default="enabled"))
    op.add_column("user", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_user_access_status", "user", "access_status in ('enabled', 'disabled', 'archived')")


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT EXISTS (SELECT 1 FROM "user" WHERE access_status <> \'enabled\')')):
        raise RuntimeError("Cannot downgrade while disabled or archived accounts exist.")
    op.drop_constraint("ck_user_access_status", "user", type_="check")
    op.drop_column("user", "archived_at")
    op.drop_column("user", "access_status")
