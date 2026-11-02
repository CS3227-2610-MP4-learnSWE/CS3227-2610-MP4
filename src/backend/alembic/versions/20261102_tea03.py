"""Add source snapshots and optimistic draft edit metadata."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_tea03"
down_revision = "20261101_tea02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("study_note_draft", sa.Column("source_title", sa.String(200), nullable=True))
    op.add_column("study_note_draft", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("study_note_draft", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column("study_note_draft", sa.Column("updated_by", sa.String(64), nullable=True))
    op.execute("UPDATE study_note_draft SET source_title = title, updated_at = created_at, updated_by = created_by")
    for name in ("source_title", "updated_at", "updated_by"):
        op.alter_column("study_note_draft", name, nullable=False)
    op.create_foreign_key("fk_note_updated_by", "study_note_draft", "user", ["updated_by"], ["id"])
    op.create_check_constraint("ck_note_version_positive", "study_note_draft", "version >= 1")


def downgrade():
    op.drop_constraint("ck_note_version_positive", "study_note_draft", type_="check")
    op.drop_constraint("fk_note_updated_by", "study_note_draft", type_="foreignkey")
    for name in ("updated_by", "updated_at", "version", "source_title"):
        op.drop_column("study_note_draft", name)
