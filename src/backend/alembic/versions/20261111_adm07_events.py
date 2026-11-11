"""ADM-07 event collection: request log, login events, first-save and first-publication events, with backfill."""
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa

revision = "20261111_adm07_events"
down_revision = "20261110_adm01_privacy"
branch_labels = None
depends_on = None

META_KEYS = ("request_log_started_at", "login_events_started_at", "practice_draft_started_started_at",
             "practice_published_started_at", "request_log_categories_started_at")


def _timestamp(name):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def upgrade():
    op.create_table("analytics_request_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source_id", sa.BigInteger()),
        _timestamp("occurred_at"),
        sa.Column("outcome", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("failure_category", sa.Text()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind in ('chatbot','generation_notes','generation_mcq')", name="ck_request_log_kind"),
        sa.CheckConstraint("outcome in ('pending','success','failure')", name="ck_request_log_outcome"),
        sa.CheckConstraint("failure_category is null or failure_category in "
                           "('timeout','rate_limited','invalid_output','upstream','unclassified')",
                           name="ck_request_log_category"),
        sa.CheckConstraint("(outcome in ('pending','success') and failure_category is null) "
                           "or (outcome = 'failure' and failure_category is not null)", name="ck_request_log_state"))
    op.create_index("uq_request_log_source", "analytics_request_log", ["kind", "source_id"], unique=True,
                    postgresql_where=sa.text("source_id is not null"))
    op.create_index("ix_request_log_occurred", "analytics_request_log", ["occurred_at"])

    op.create_table("analytics_login_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        _timestamp("occurred_at"),
        sa.CheckConstraint("role in ('student','teacher')", name="ck_login_event_role"))
    op.create_index("ix_login_event_occurred", "analytics_login_event", ["occurred_at"])
    op.create_index("ix_login_event_user", "analytics_login_event", ["user_id", "occurred_at"])

    for table, column in (("analytics_practice_draft_started", "started_at"),
                          ("analytics_practice_published", "published_at")):
        op.create_table(table,
            sa.Column("practice_set_id", sa.Text(), primary_key=True),
            sa.Column("teacher_id", sa.String(64), sa.ForeignKey("user.id"), nullable=False),
            _timestamp(column),
            sa.CheckConstraint("char_length(practice_set_id) between 1 and 100", name=f"ck_{table}_id"))
        op.create_index(f"ix_{table}_time", table, [column])

    now = datetime.now(timezone.utc)
    op.execute(sa.text("""
        INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms)
        SELECT 'chatbot', id, received_at, outcome,
               CASE WHEN outcome = 'failure' THEN 'unclassified' END, duration_ms
        FROM analytics_chat_request WHERE received_at >= now() - interval '30 days'
        ON CONFLICT (kind, source_id) WHERE source_id IS NOT NULL DO NOTHING"""))
    op.execute(sa.text("""
        INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category, duration_ms)
        SELECT CASE workflow WHEN 'study_notes' THEN 'generation_notes' ELSE 'generation_mcq' END,
               id, accepted_at, outcome, CASE WHEN outcome = 'failure' THEN 'unclassified' END, duration_ms
        FROM analytics_generation_attempt WHERE accepted_at >= now() - interval '30 days'
        ON CONFLICT (kind, source_id) WHERE source_id IS NOT NULL DO NOTHING"""))
    # First save of a practice set = creation of its draft batch; first publication = its published snapshot.
    # Both are keyed by the draft batch id so one set has one identity in both series.
    op.execute(sa.text("""
        INSERT INTO analytics_practice_draft_started (practice_set_id, teacher_id, started_at)
        SELECT CAST(id AS text), created_by, created_at FROM mcq_draft_batch ON CONFLICT DO NOTHING"""))
    op.execute(sa.text("""
        INSERT INTO analytics_practice_published (practice_set_id, teacher_id, published_at)
        SELECT CAST(source_draft_id AS text), published_by, published_at FROM published_practice_set
        ON CONFLICT DO NOTHING"""))

    bind = op.get_bind()
    starts = {key: now.isoformat() for key in META_KEYS}
    # The request log is backfilled for 30 days, so it starts at the later of the ADM-01 recording start and 30 days ago.
    recorded = bind.scalar(sa.text("SELECT value FROM analytics_meta WHERE key = 'recording_started_at'"))
    backfill_from = now - timedelta(days=30)
    if recorded is not None:
        parsed = datetime.fromisoformat(recorded)
        parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        backfill_from = max(backfill_from, parsed)
    starts["request_log_started_at"] = backfill_from.astimezone(timezone.utc).isoformat()
    for key, table, column in (("practice_draft_started_started_at", "analytics_practice_draft_started", "started_at"),
                               ("practice_published_started_at", "analytics_practice_published", "published_at")):
        earliest = bind.scalar(sa.text(f"SELECT min({column}) FROM {table}"))
        if earliest is not None:
            starts[key] = earliest.astimezone(timezone.utc).isoformat()
    for key, value in starts.items():
        bind.execute(sa.text("INSERT INTO analytics_meta (key, value) VALUES (:key, :value) "
                             "ON CONFLICT (key) DO NOTHING"), {"key": key, "value": value})


def downgrade():
    for table in ("analytics_practice_published", "analytics_practice_draft_started", "analytics_login_event",
                  "analytics_request_log"):
        op.drop_table(table)
    op.get_bind().execute(sa.text("DELETE FROM analytics_meta WHERE key = ANY(:keys)"), {"keys": list(META_KEYS)})
