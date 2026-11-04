"""Version and audit existing MCQ batches without changing their questions."""
from alembic import op
import sqlalchemy as sa

revision = "20261104_tea03_mcq_edit"
down_revision = "20261103_shr01_auth"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mcq_draft_batch", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("mcq_draft_batch", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column("mcq_draft_batch", sa.Column("updated_by", sa.String(64), nullable=True))
    op.execute("UPDATE mcq_draft_batch SET updated_at = created_at, updated_by = created_by")
    op.alter_column("mcq_draft_batch", "updated_at", nullable=False)
    op.alter_column("mcq_draft_batch", "updated_by", nullable=False)
    op.create_foreign_key("fk_mcq_updated_by", "mcq_draft_batch", "user", ["updated_by"], ["id"])
    op.create_check_constraint("ck_mcq_version_positive", "mcq_draft_batch", "version >= 1")


def downgrade():
    op.drop_constraint("ck_mcq_version_positive", "mcq_draft_batch", type_="check")
    op.drop_constraint("fk_mcq_updated_by", "mcq_draft_batch", type_="foreignkey")
    op.drop_column("mcq_draft_batch", "updated_by")
    op.drop_column("mcq_draft_batch", "updated_at")
    op.drop_column("mcq_draft_batch", "version")
