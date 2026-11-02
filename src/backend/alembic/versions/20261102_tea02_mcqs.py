"""Add private generated MCQ batches and ordered questions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261102_tea02_mcqs"
down_revision = "20261102_tea03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("mcq_draft_batch",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("source_material_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("source_title", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_material_id", "course_id"], ["material.id", "material.course_id"]))
    op.create_table("mcq_draft_question",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("mcq_draft_batch.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(200), nullable=False),
        sa.Column("choices", JSONB(), nullable=False),
        sa.Column("correct_choice_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.String(200), nullable=False),
        sa.UniqueConstraint("batch_id", "position"),
        sa.CheckConstraint("position between 1 and 3", name="ck_mcq_position"),
        sa.CheckConstraint("correct_choice_index between 0 and 3", name="ck_mcq_answer"),
        sa.CheckConstraint("char_length(question) between 1 and 200", name="ck_mcq_question_length"),
        sa.CheckConstraint("char_length(explanation) between 1 and 200", name="ck_mcq_explanation_length"),
        sa.CheckConstraint("CASE WHEN jsonb_typeof(choices) = 'array' THEN jsonb_array_length(choices) = 4 ELSE false END", name="ck_mcq_choices_count"),
        *[sa.CheckConstraint(f"jsonb_typeof(choices->{i}) = 'string' AND char_length(choices->>{i}) between 1 and 80", name=f"ck_mcq_choice_{i}") for i in range(4)])


def downgrade():
    op.drop_table("mcq_draft_question")
    op.drop_table("mcq_draft_batch")
