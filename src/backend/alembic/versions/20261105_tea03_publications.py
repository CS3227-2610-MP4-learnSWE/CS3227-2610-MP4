"""Immutable MCQ publication snapshots and note-version provenance."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261105_tea03_publications"
down_revision = "20261104_stu01_lessons"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("published_lesson", sa.Column("source_version", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_lesson_source_version", "published_lesson", "source_version IS NULL OR source_version >= 1")
    op.create_unique_constraint("uq_mcq_batch_id_course", "mcq_draft_batch", ["id", "course_id"])
    op.create_table("published_practice_set",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_draft_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("published_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]),
        sa.ForeignKeyConstraint(["source_draft_id", "course_id"], ["mcq_draft_batch.id", "mcq_draft_batch.course_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("source_version >= 1", name="ck_published_set_version"),
        sa.CheckConstraint("char_length(title) between 1 and 200", name="ck_published_set_title"))
    op.create_table("published_practice_question",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("set_id", sa.Uuid(), sa.ForeignKey("published_practice_set.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_question_id", sa.Uuid(), sa.ForeignKey("mcq_draft_question.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(200), nullable=False),
        sa.Column("choices", postgresql.JSONB(), nullable=False),
        sa.Column("correct_choice_index", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.String(200), nullable=False),
        sa.UniqueConstraint("set_id", "position"), sa.UniqueConstraint("set_id", "source_question_id"),
        sa.CheckConstraint("position between 1 and 3", name="ck_published_question_position"),
        sa.CheckConstraint("correct_choice_index between 0 and 3", name="ck_published_question_answer"),
        sa.CheckConstraint("char_length(question) between 1 and 200", name="ck_published_question_text"),
        sa.CheckConstraint("char_length(explanation) between 1 and 200", name="ck_published_question_explanation"),
        sa.CheckConstraint("CASE WHEN jsonb_typeof(choices) = 'array' THEN jsonb_array_length(choices) = 4 ELSE false END", name="ck_published_choices_count"),
        *[sa.CheckConstraint(f"jsonb_typeof(choices->{i}) = 'string' AND char_length(choices->>{i}) between 1 and 80", name=f"ck_published_choice_{i}") for i in range(4)])


def downgrade():
    op.execute("LOCK TABLE published_practice_set, published_lesson IN ACCESS EXCLUSIVE MODE")
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM published_practice_set) OR EXISTS (SELECT 1 FROM published_lesson WHERE source_version IS NOT NULL)")):
        raise RuntimeError("Cannot downgrade publication storage while published sets or recorded note publication provenance exist. Preserve the database or restore a backup instead.")
    op.drop_table("published_practice_question")
    op.drop_table("published_practice_set")
    op.drop_constraint("uq_mcq_batch_id_course", "mcq_draft_batch", type_="unique")
    op.drop_constraint("ck_lesson_source_version", "published_lesson", type_="check")
    op.drop_column("published_lesson", "source_version")
