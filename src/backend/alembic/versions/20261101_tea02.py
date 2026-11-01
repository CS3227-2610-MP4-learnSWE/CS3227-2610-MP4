"""Persist unpublished teacher study-note drafts."""
from alembic import op
import sqlalchemy as sa

revision = "20261101_tea02"
down_revision = "20261030_tea01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_material_id_course", "material", ["id", "course_id"])
    op.create_table(
        "study_note_draft",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("source_material_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_material_id", "course_id"], ["material.id", "material.course_id"]),
        sa.CheckConstraint("char_length(content) between 1 and 2000", name="ck_note_content_length"),
    )


def downgrade():
    op.drop_table("study_note_draft")
    op.drop_constraint("uq_material_id_course", "material", type_="unique")
