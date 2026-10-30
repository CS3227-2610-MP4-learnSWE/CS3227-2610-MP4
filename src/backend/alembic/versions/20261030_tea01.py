"""TEA-01 shared course and material tables."""
from alembic import op
from teacher_materials.models import Base

revision = "20261030_tea01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    for table in Base.metadata.sorted_tables:
        table.create(op.get_bind())


def downgrade():
    for table in reversed(Base.metadata.sorted_tables):
        table.drop(op.get_bind())
