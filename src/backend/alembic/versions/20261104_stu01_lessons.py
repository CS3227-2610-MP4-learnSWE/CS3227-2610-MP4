"""Add published_lesson and lesson_completion (STU-01)."""
from alembic import op
import sqlalchemy as sa

revision = "20261104_stu01_lessons"
down_revision = "20261104_tea03_mcq_edit"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("published_lesson",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("topic_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_draft_id", sa.Uuid(), sa.ForeignKey("study_note_draft.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("published_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]),
        sa.CheckConstraint("char_length(title) between 1 and 200", name="ck_published_lesson_title_length"),
        sa.CheckConstraint("char_length(content) between 1 and 2000", name="ck_published_lesson_content_length"),
        sa.UniqueConstraint("id", "course_id", name="uq_published_lesson_id_course"))
    op.create_index("ix_published_lesson_course", "published_lesson", ["course_id", "withdrawn_at"])
    op.create_table("lesson_completion",
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lesson_id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id", "course_id"], ["published_lesson.id", "published_lesson.course_id"]),
        sa.CheckConstraint("completed = (completed_at is not null)", name="ck_lesson_completion_state"))
    op.create_index("ix_lesson_completion_user_course", "lesson_completion", ["user_id", "course_id"])
    op.create_index("ix_lesson_completion_lesson", "lesson_completion", ["lesson_id"])


def downgrade():
    op.drop_table("lesson_completion")
    op.drop_table("published_lesson")
