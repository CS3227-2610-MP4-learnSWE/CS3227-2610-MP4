"""ADM-07 AC42: the one-off AI usage cleanup command `python -m ai_usage.cleanup` (task P4-10a).

Contract: workflow/specs/ADM-07/plan.md "[P4] AI usage cleanup". These tests run the command ONLY against a
disposable schema of the test database (TEA01_TEST_DATABASE_URL); the command is never pointed at any other
database and `--apply` is never used on a real one. Output wording is not specified, so output checks are
limited to the feature names, the counts and the approver name.
"""
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated

UTC = timezone.utc
APPROVER = "Reviewer-Quinn"


@pytest.fixture
def db():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "adm07cl_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    iso = Isolated(base, schema)
    assert schema in iso.url  # the command only ever sees the disposable test schema
    iso.migrate("upgrade", "head")
    try:
        yield iso
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def attempt(iso, feature, age, outcome):
    ident = uuid.uuid4()
    iso.sql("INSERT INTO ai_service_attempts (id, feature, started_at, outcome) VALUES (%s,%s,%s,%s)",
            (ident, feature, datetime.now(UTC) - age, outcome))
    return ident


def coverage(iso):
    return {r[0]: (r[1], r[2], r[3]) for r in iso.sql(
        "SELECT feature, enabled, covered_since, incomplete_since FROM ai_usage_coverage ORDER BY feature")}


def set_coverage(iso, feature, covered_since, incomplete_since, enabled=True):
    iso.sql("UPDATE ai_usage_coverage SET enabled=%s, covered_since=%s, incomplete_since=%s WHERE feature=%s",
            (enabled, covered_since, incomplete_since, feature))


def utc(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def next_midnight(moment):
    return (moment + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def rows(iso):
    return {r[0]: (r[1], r[2]) for r in iso.sql("SELECT id, feature, outcome FROM ai_service_attempts")}


def run(iso, *args, check=False):
    return iso.run("-m", "ai_usage.cleanup", *args, check=check)


def seed(iso):
    """STU-03: stale pending (25 h, 48 h), fresh pending (23 h 59 m), terminal rows (30 h) with a gap marker.
    TEA-02: a stale pending row and a coverage start later than the next midnight.
    ADM-03: only terminal rows and no marker.  ADM-01: a stale pending row and no coverage start yet."""
    now = datetime.now(UTC)
    ids = {
        "stu_stale_25": attempt(iso, "STU-03", timedelta(hours=25), "pending"),
        "stu_stale_48": attempt(iso, "STU-03", timedelta(hours=48), "pending"),
        "stu_fresh": attempt(iso, "STU-03", timedelta(hours=23, minutes=59), "pending"),
        "stu_success": attempt(iso, "STU-03", timedelta(hours=30), "success"),
        "stu_rate": attempt(iso, "STU-03", timedelta(hours=30), "rate_limit"),
        "stu_other": attempt(iso, "STU-03", timedelta(hours=30), "other_failure"),
        "tea_stale": attempt(iso, "TEA-02", timedelta(hours=100), "pending"),
        "adm03_success": attempt(iso, "ADM-03", timedelta(hours=90), "success"),
        "adm01_stale": attempt(iso, "ADM-01", timedelta(hours=26), "pending"),
    }
    set_coverage(iso, "STU-03", now - timedelta(days=10), now - timedelta(days=2))
    set_coverage(iso, "TEA-02", now + timedelta(days=5), now - timedelta(days=1))
    set_coverage(iso, "ADM-03", now - timedelta(days=4), None)
    set_coverage(iso, "ADM-01", None, None, enabled=False)
    return ids


def snapshot(iso):
    return (rows(iso), coverage(iso))


def test_adm07_ac42_dry_run_changes_nothing_and_prints_per_feature_counts(db):
    seed(db)
    before = snapshot(db)
    r = run(db, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert snapshot(db) == before
    out = r.stdout + r.stderr
    assert "Traceback" not in out
    for feature in ("STU-03", "TEA-02", "ADM-01"):
        assert feature in out
    assert re.search(r"STU-03[^\n]*\b2\b", out), out  # two stale pending rows would be deleted for STU-03
    assert APPROVER not in out


def test_adm07_ac42_apply_without_the_approval_flag_refuses_and_changes_nothing(db):
    seed(db)
    before = snapshot(db)
    r = run(db, "--apply")
    assert r.returncode != 0
    assert snapshot(db) == before


@pytest.mark.parametrize("approved_by", ["", "   "])
def test_adm07_ac42_apply_with_an_empty_approver_refuses(db, approved_by):
    seed(db)
    before = snapshot(db)
    r = run(db, "--apply", "--approved-by", approved_by)
    assert r.returncode != 0
    assert snapshot(db) == before


def test_adm07_ac42_running_without_dry_run_or_apply_changes_nothing(db):
    seed(db)
    before = snapshot(db)
    run(db)
    assert snapshot(db) == before


def test_adm07_ac42_approval_flag_alone_without_apply_changes_nothing(db):
    seed(db)
    before = snapshot(db)
    run(db, "--approved-by", APPROVER)
    assert snapshot(db) == before


def test_adm07_ac42_apply_deletes_only_pending_attempts_older_than_24_hours(db):
    ids = seed(db)
    r = run(db, "--apply", "--approved-by", APPROVER)
    assert r.returncode == 0, r.stdout + r.stderr
    left = rows(db)
    deleted = {"stu_stale_25", "stu_stale_48", "tea_stale", "adm01_stale"}
    assert set(left) == {v for k, v in ids.items() if k not in deleted}
    assert ids["stu_fresh"] in left  # 23 h 59 m: may still be in flight
    for name in ("stu_success", "stu_rate", "stu_other", "adm03_success"):
        assert ids[name] in left  # terminal rows are never deleted


def test_adm07_ac42_apply_prints_deleted_counts_and_logs_the_approver_without_row_content(db):
    ids = seed(db)
    r = run(db, "--apply", "--approved-by", APPROVER)
    out = r.stdout + r.stderr
    assert APPROVER in out and "STU-03" in out
    for ident in ids.values():
        assert str(ident) not in out  # counts and approver only, no row content


def test_adm07_ac42_apply_clears_incomplete_since_and_sets_covered_since_to_the_next_utc_midnight(db):
    seed(db)
    t0 = datetime.now(UTC)
    run(db, "--apply", "--approved-by", APPROVER)
    t1 = datetime.now(UTC)
    cov = coverage(db)
    allowed = {next_midnight(t0), next_midnight(t1)}
    for feature in ("STU-03", "ADM-01"):  # a deleted row and/or a marker
        enabled, covered, incomplete = cov[feature]
        assert incomplete is None, feature
        assert utc(covered) in allowed, (feature, covered)
    assert cov["STU-03"][0] is True and cov["ADM-01"][0] is False  # `enabled` is unchanged


def test_adm07_ac42_a_coverage_start_is_never_moved_earlier(db):
    seed(db)
    later = coverage(db)["TEA-02"][1]
    run(db, "--apply", "--approved-by", APPROVER)
    enabled, covered, incomplete = coverage(db)["TEA-02"]
    assert utc(covered) == utc(later) and utc(covered) > next_midnight(datetime.now(UTC))
    assert incomplete is None


def test_adm07_ac42_a_feature_with_nothing_to_delete_and_no_marker_is_untouched(db):
    seed(db)
    before = coverage(db)["ADM-03"]
    run(db, "--apply", "--approved-by", APPROVER)
    assert coverage(db)["ADM-03"] == before
    assert coverage(db)["ADM-03"][2] is None


def test_adm07_ac42_a_second_apply_is_a_no_op(db):
    seed(db)
    run(db, "--apply", "--approved-by", APPROVER)
    after_first = snapshot(db)
    r = run(db, "--apply", "--approved-by", APPROVER)
    assert r.returncode == 0, r.stdout + r.stderr
    assert snapshot(db) == after_first


def test_adm07_ac42_dry_run_after_apply_reports_nothing_left_to_delete_and_changes_nothing(db):
    seed(db)
    run(db, "--apply", "--approved-by", APPROVER)
    after = snapshot(db)
    r = run(db, "--dry-run")
    assert r.returncode == 0
    assert snapshot(db) == after


def test_adm07_ac42_no_backup_archive_or_restore_path_exists(db):
    seed(db)
    before = {r[0] for r in db.sql("SELECT table_name FROM information_schema.tables WHERE table_schema=%s", (db.schema,))}
    run(db, "--apply", "--approved-by", APPROVER)
    after = {r[0] for r in db.sql("SELECT table_name FROM information_schema.tables WHERE table_schema=%s", (db.schema,))}
    assert after == before  # no archive or backup table was created
    assert not any(word in t for t in after for word in ("archive", "backup", "deleted_attempt"))
    restore = run(db, "--restore")
    assert restore.returncode != 0  # there is no --restore
    assert len(rows(db)) == 5


def test_adm07_ac42_other_tables_are_not_touched(db):
    seed(db)
    db.sql('INSERT INTO "user"(id,display_name,role,email,access_status) '
           "VALUES ('cl-user','cl','student','cl@example.com','enabled')")
    db.sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, outcome) "
           "VALUES ('cl-user','student','lesson',NULL, now() - interval '3 days','pending')")
    users = db.sql('SELECT count(*) FROM "user"')
    chats = db.sql("SELECT count(*) FROM analytics_chat_request")
    run(db, "--apply", "--approved-by", APPROVER)
    assert db.sql('SELECT count(*) FROM "user"') == users
    assert db.sql("SELECT count(*) FROM analytics_chat_request") == chats
    assert db.sql("SELECT outcome FROM analytics_chat_request") == [("pending",)]  # only ai_service_attempts is cleaned


def test_adm07_ac42_the_command_does_not_run_on_import_or_at_migration_time(db):
    """Alembic ran in the fixture with stale pending rows absent; creating them afterwards and migrating again deletes nothing."""
    ids = seed(db)
    db.migrate("upgrade", "head")
    assert len(rows(db)) == len(ids)
