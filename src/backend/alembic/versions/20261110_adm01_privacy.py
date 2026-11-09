"""Purge legacy analytics text and reasons before the local-DLP worker is enabled."""
from alembic import op
import sqlalchemy as sa

revision = "20261110_adm01_privacy"
down_revision = "20261109_adm01_analytics"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("analytics_grading_item", sa.Column("privacy_policy_version", sa.Text(), nullable=True))
    op.drop_constraint("ck_analytics_item_status", "analytics_grading_item", type_="check")
    op.create_check_constraint("ck_analytics_item_status", "analytics_grading_item", "status in ('pending','graded','grading_failed','privacy_blocked')")
    op.execute("DELETE FROM analytics_grade")
    op.execute("UPDATE analytics_grading_item SET request_text=NULL,response_text=NULL,context_text=NULL,status='privacy_blocked',failure_code='privacy_source_excluded',graded_at=NULL")
    op.execute("UPDATE analytics_grading_run SET status='failed',failure_code='privacy_scanner_unavailable',finished_at=now() WHERE status IN ('queued','running')")


def downgrade():
    op.execute("DELETE FROM analytics_grade WHERE item_id IN (SELECT id FROM analytics_grading_item WHERE status='privacy_blocked')")
    op.execute("DELETE FROM analytics_grading_item WHERE status='privacy_blocked'")
    op.drop_constraint("ck_analytics_item_status", "analytics_grading_item", type_="check")
    op.create_check_constraint("ck_analytics_item_status", "analytics_grading_item", "status in ('pending','graded','grading_failed')")
    op.drop_column("analytics_grading_item", "privacy_policy_version")
