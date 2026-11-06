"""Content-free durable AI attempt metadata and forward-only coverage."""
from alembic import op
import sqlalchemy as sa

revision = "20261106_adm06_ai_usage"
down_revision = "20261106_merge_adm05_stu04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("ai_service_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("feature", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("input_tokens", sa.BigInteger()),
        sa.Column("output_tokens", sa.BigInteger()),
        sa.Column("total_tokens", sa.BigInteger()),
        sa.CheckConstraint("feature in ('STU-03', 'TEA-02', 'ADM-03')", name="ck_ai_attempt_feature"),
        sa.CheckConstraint("outcome in ('pending', 'success', 'rate_limit', 'other_failure')", name="ck_ai_attempt_outcome"),
        sa.CheckConstraint("(outcome = 'pending' and finished_at is null) or (outcome <> 'pending' and finished_at is not null)", name="ck_ai_attempt_finished"),
        sa.CheckConstraint("input_tokens >= 0 and output_tokens >= 0 and total_tokens >= 0", name="ck_ai_attempt_tokens"),
    )
    op.create_index("ix_ai_attempt_feature_started", "ai_service_attempts", ["feature", "started_at"])
    coverage = op.create_table("ai_usage_coverage",
        sa.Column("feature", sa.String(16), primary_key=True),
        sa.Column("covered_since", sa.DateTime(timezone=True)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("incomplete_since", sa.DateTime(timezone=True)),
        sa.CheckConstraint("feature in ('STU-03', 'TEA-02', 'ADM-03')", name="ck_ai_coverage_feature"),
        sa.CheckConstraint("not enabled or covered_since is not null", name="ck_ai_coverage_start"),
    )
    op.bulk_insert(coverage, [{"feature": feature, "enabled": False} for feature in ("STU-03", "TEA-02", "ADM-03")])


def downgrade():
    op.drop_table("ai_service_attempts")
    op.drop_table("ai_usage_coverage")
