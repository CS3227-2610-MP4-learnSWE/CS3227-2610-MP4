"""TEA-01 historical schema, independent of later live model metadata."""
from alembic import op
import sqlalchemy as sa

revision = "20261030_tea01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("user", sa.Column("id", sa.String(64), primary_key=True), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.CheckConstraint("role in ('student', 'teacher', 'admin')"))
    op.create_table("course", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("course_membership", sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), primary_key=True), sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id"), primary_key=True))
    op.create_table("topic", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("course_id", "name"), sa.UniqueConstraint("id", "course_id"))
    op.create_table("material", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False), sa.Column("topic_id", sa.Uuid(), nullable=True), sa.Column("uploaded_by", sa.String(64), sa.ForeignKey("user.id"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("media_type", sa.String(64), nullable=False), sa.Column("size_bytes", sa.BigInteger(), nullable=False), sa.Column("storage_key", sa.String(255), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["topic_id", "course_id"], ["topic.id", "topic.course_id"]), sa.CheckConstraint("size_bytes between 1 and 10485760"))


def downgrade():
    for name in ("material", "topic", "course_membership", "course", "user"):
        op.drop_table(name)
