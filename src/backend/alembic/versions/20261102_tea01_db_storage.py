"""Store original materials atomically in PostgreSQL; start with an empty database."""
from alembic import op
import sqlalchemy as sa

revision = "20261102_tea01_db_storage"
down_revision = "20261102_tea02_mcqs"
branch_labels = None
depends_on = None


def upgrade():
    # Hold the emptiness decision stable against concurrent legacy uploads.
    op.execute("LOCK TABLE material IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM material)")):
        raise RuntimeError("Existing materials cannot be converted automatically. Configure a fresh empty database; keep the previous database and uploaded files unchanged.")
    op.create_table("material_file",
        sa.Column("material_id", sa.Uuid(), sa.ForeignKey("material.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.CheckConstraint("octet_length(content) between 1 and 10485760", name="ck_material_file_length"))
    op.drop_column("material", "storage_key")


def downgrade():
    op.execute("LOCK TABLE material IN ACCESS EXCLUSIVE MODE")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM material)")):
        raise RuntimeError("Cannot downgrade file storage while materials exist. Keep this database and restore the previous code, database and files instead.")
    op.drop_table("material_file")
    op.add_column("material", sa.Column("storage_key", sa.String(255), nullable=False))
    op.create_unique_constraint("material_storage_key_key", "material", ["storage_key"])
