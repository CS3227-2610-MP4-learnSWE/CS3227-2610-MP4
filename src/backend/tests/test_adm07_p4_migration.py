"""ADM-07 phase 4 migration `20261111_adm07_events` (AC36) and privacy schema inspection (AC4, AC22, AC35).

Contract: workflow/specs/ADM-07/plan.md "[P4] Migration 20261111_adm07_events". The migration runs in a
disposable schema only; the revision id is taken to be the file stem `20261111_adm07_events` (same convention
as `20261106_merge_adm05_stu04`). Migration tests need TEA01_TEST_DATABASE_URL; the schema inspection runs on
the suite's database.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

from adm07_p4_helpers import META_KEYS, NEW_TABLES
from auth_helpers import psycopg_url, sql
from test_shr01_seed_migration import Isolated

REVISION = "20261111_adm07_events"
UTC = timezone.utc


@pytest.fixture
def isolated():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "adm07p4_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def tables(iso):
    return {r[0] for r in iso.sql("SELECT table_name FROM information_schema.tables WHERE table_schema=%s",
                                  (iso.schema,))}


def populate(iso):
    """Users plus chat and generation rows around the 30-day boundary; returns the source ids by name."""
    now = datetime.now(UTC)
    for uid_, role in (("p4-student", "student"), ("p4-teacher", "teacher")):
        iso.sql('INSERT INTO "user"(id,display_name,role,email,access_status) VALUES (%s,%s,%s,%s,\'enabled\')',
                (uid_, uid_, role, uid_ + "@example.com"))
    ids = {}

    def chat(name, age, outcome, duration):
        at = now - age
        done = None if outcome == "pending" else at + timedelta(milliseconds=duration or 0)
        ids[name] = iso.sql(
            "INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, "
            "completed_at, duration_ms, outcome) VALUES ('p4-student','student','lesson',NULL,%s,%s,%s,%s) RETURNING id",
            (at, done, duration if outcome != "pending" else None, outcome))[0][0]

    def gen(name, workflow, age, outcome, duration):
        at = now - age
        done = at + timedelta(milliseconds=duration)
        ids[name] = iso.sql(
            "INSERT INTO analytics_generation_attempt (workflow, user_id, accepted_at, completed_at, duration_ms, "
            "outcome) VALUES (%s,'p4-teacher',%s,%s,%s,%s) RETURNING id", (workflow, at, done, duration, outcome))[0][0]

    chat("chat_ok", timedelta(days=5), "success", 1200)
    chat("chat_fail", timedelta(days=10), "failure", 300)
    chat("chat_pending", timedelta(hours=1), "pending", None)
    chat("chat_old", timedelta(days=40), "success", 800)  # outside the 30-day backfill
    chat("chat_edge_in", timedelta(days=29, hours=23), "success", 700)
    gen("gen_notes_ok", "study_notes", timedelta(days=3), "success", 9000)
    gen("gen_mcq_fail", "mcq_batch", timedelta(days=2), "failure", 4000)
    gen("gen_old", "mcq_batch", timedelta(days=45), "success", 5000)
    return ids


def prior_head(iso):
    iso.migrate("upgrade", f"{REVISION}-1")


def test_adm07_ac36_upgrade_creates_the_four_tables_and_the_five_meta_keys(isolated):
    prior_head(isolated)
    assert not (set(NEW_TABLES) & tables(isolated))
    isolated.migrate("upgrade", "head")
    assert set(NEW_TABLES) <= tables(isolated)
    keys = {r[0] for r in isolated.sql("SELECT key FROM analytics_meta")}
    assert set(META_KEYS) <= keys
    now = datetime.now(UTC)
    for key in META_KEYS:
        value = datetime.fromisoformat(isolated.sql("SELECT value FROM analytics_meta WHERE key=%s", (key,))[0][0])
        assert abs((now - value.astimezone(UTC)).total_seconds()) < 600, key  # "migration time in UTC, ISO 8601"


def test_adm07_ac36_backfill_copies_the_last_30_days_of_chat_and_generation_rows(isolated):
    prior_head(isolated)
    ids = populate(isolated)
    before_chat = isolated.sql("SELECT t::text FROM analytics_chat_request t ORDER BY id")
    before_gen = isolated.sql("SELECT t::text FROM analytics_generation_attempt t ORDER BY id")
    isolated.migrate("upgrade", "head")
    rows = {(k, s): (o, c, d) for k, s, o, c, d in isolated.sql(
        "SELECT kind, source_id, outcome, failure_category, duration_ms FROM analytics_request_log")}
    assert rows == {
        ("chatbot", ids["chat_ok"]): ("success", None, 1200),
        ("chatbot", ids["chat_fail"]): ("failure", "unclassified", 300),
        ("chatbot", ids["chat_pending"]): ("pending", None, None),  # copied as pending; the read-time rule expires it
        ("chatbot", ids["chat_edge_in"]): ("success", None, 700),
        ("generation_notes", ids["gen_notes_ok"]): ("success", None, 9000),
        ("generation_mcq", ids["gen_mcq_fail"]): ("failure", "unclassified", 4000),
    }
    # the time of each log row is the time of its source row
    times = isolated.sql("SELECT l.occurred_at = c.received_at FROM analytics_request_log l "
                         "JOIN analytics_chat_request c ON l.kind='chatbot' AND l.source_id=c.id")
    assert times and all(t[0] for t in times)
    # the backfill never touches the source tables
    assert isolated.sql("SELECT t::text FROM analytics_chat_request t ORDER BY id") == before_chat
    assert isolated.sql("SELECT t::text FROM analytics_generation_attempt t ORDER BY id") == before_gen


def test_adm07_ac36_the_migration_keeps_no_user_id_on_backfilled_rows(isolated):
    prior_head(isolated)
    populate(isolated)
    isolated.migrate("upgrade", "head")
    columns = {r[0] for r in isolated.sql(
        "SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name='analytics_request_log'",
        (isolated.schema,))}
    assert not any("user" in c or "email" in c or "ip" == c for c in columns)


def test_adm07_ac36_rerunning_the_backfill_adds_nothing_downgrade_then_upgrade_is_stable(isolated):
    prior_head(isolated)
    populate(isolated)
    isolated.migrate("upgrade", "head")
    first = isolated.sql("SELECT kind, source_id, outcome, failure_category, duration_ms FROM analytics_request_log "
                         "ORDER BY kind, source_id")
    isolated.migrate("downgrade", f"{REVISION}-1")
    assert not (set(NEW_TABLES) & tables(isolated))
    isolated.migrate("upgrade", "head")
    again = isolated.sql("SELECT kind, source_id, outcome, failure_category, duration_ms FROM analytics_request_log "
                         "ORDER BY kind, source_id")
    assert again == first and len(first) == 6


def test_adm07_ac36_insert_on_conflict_makes_the_backfill_statement_idempotent_against_the_unique_index(isolated):
    isolated.migrate("upgrade", "head")
    isolated.sql("INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome) "
                 "VALUES ('chatbot', 77, now(), 'pending')")
    with pytest.raises(psycopg.errors.UniqueViolation):
        isolated.sql("INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome) "
                     "VALUES ('chatbot', 77, now(), 'pending')")
    # rate-limited rows have no source id: any number of them may exist
    for _ in range(3):
        isolated.sql("INSERT INTO analytics_request_log (kind, source_id, occurred_at, outcome, failure_category) "
                     "VALUES ('generation_notes', NULL, now(), 'failure', 'rate_limited')")


def test_adm07_ac36_downgrade_drops_the_four_tables_and_deletes_the_meta_keys_but_keeps_source_data(isolated):
    prior_head(isolated)
    populate(isolated)
    isolated.migrate("upgrade", "head")
    isolated.migrate("downgrade", f"{REVISION}-1")
    assert not (set(NEW_TABLES) & tables(isolated))
    keys = {r[0] for r in isolated.sql("SELECT key FROM analytics_meta")}
    assert not (set(META_KEYS) & keys)
    assert isolated.sql("SELECT count(*) FROM analytics_chat_request")[0][0] == 5
    assert isolated.sql("SELECT count(*) FROM analytics_generation_attempt")[0][0] == 3
    assert "recording_started_at" in keys  # existing keys are untouched


def test_adm07_ac36_upgrade_on_an_empty_database_works_and_the_tables_are_empty(isolated):
    isolated.migrate("upgrade", "head")
    for table in NEW_TABLES:
        assert isolated.sql(f"SELECT count(*) FROM {table}")[0][0] == 0


def test_adm07_ac36_schema_constraints_match_the_contract(isolated):
    isolated.migrate("upgrade", "head")
    # outcome/category CHECK
    bad = [("success", "timeout"), ("pending", "timeout"), ("failure", None), ("bogus", None), ("failure", "bogus")]
    for outcome, category in bad:
        with pytest.raises(psycopg.errors.CheckViolation):
            isolated.sql("INSERT INTO analytics_request_log (kind, occurred_at, outcome, failure_category) "
                         "VALUES ('chatbot', now(), %s, %s)", (outcome, category))
    with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.NotNullViolation)):
        isolated.sql("INSERT INTO analytics_request_log (kind, occurred_at, outcome) VALUES ('bogus', now(), 'pending')")
    # login role CHECK and FK
    isolated.sql('INSERT INTO "user"(id,display_name,role,email,access_status) '
                 "VALUES ('p4-u','p4','student','p4u@example.com','enabled')")
    with pytest.raises(psycopg.errors.CheckViolation):
        isolated.sql("INSERT INTO analytics_login_event (user_id, role, occurred_at) VALUES ('p4-u','admin',now())")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        isolated.sql("INSERT INTO analytics_login_event (user_id, role, occurred_at) VALUES ('nobody','student',now())")
    # primary keys make draft-started and published once per set
    for table, column in (("analytics_practice_draft_started", "started_at"), ("analytics_practice_published", "published_at")):
        isolated.sql(f"INSERT INTO {table} (practice_set_id, teacher_id, {column}) VALUES ('s1','p4-u',now())")
        with pytest.raises(psycopg.errors.UniqueViolation):
            isolated.sql(f"INSERT INTO {table} (practice_set_id, teacher_id, {column}) VALUES ('s1','p4-u',now())")
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            isolated.sql(f"INSERT INTO {table} (practice_set_id, teacher_id, {column}) VALUES ('s2','nobody',now())")


# ================================================================== AC4 / AC22 privacy: schema inspection (suite database)

def columns_of(table):
    return {r[0]: r[1] for r in sql(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema=current_schema() "
        "AND table_name=%s", (table,))}


def test_adm07_ac35_request_log_has_exactly_the_contract_columns_and_no_user_id_or_text():
    cols = columns_of("analytics_request_log")
    assert set(cols) == {"id", "kind", "source_id", "occurred_at", "outcome", "failure_category", "duration_ms",
                         "created_at"}
    assert not any(k in c for c in cols for k in ("user", "email", "ip", "text", "message", "content", "session"))


def test_adm07_ac22_login_event_stores_user_id_role_and_time_and_nothing_else():
    assert set(columns_of("analytics_login_event")) == {"id", "user_id", "role", "occurred_at"}


@pytest.mark.parametrize("table,time_column", [("analytics_practice_draft_started", "started_at"),
                                               ("analytics_practice_published", "published_at")])
def test_adm07_ac22_practice_events_store_set_id_teacher_id_and_time_and_nothing_else(table, time_column):
    assert set(columns_of(table)) == {"practice_set_id", "teacher_id", time_column}


def test_adm07_ac4_no_new_table_has_an_ip_agent_email_or_free_text_column():
    banned = ("ip", "ip_address", "user_agent", "agent", "email", "text", "message", "prompt", "response", "content",
              "name", "title", "body", "reason", "note", "comment")
    for table in NEW_TABLES:
        cols = columns_of(table)
        assert not (set(cols) & set(banned)), (table, cols)
        free_text = [c for c, t in cols.items() if t in ("text", "character varying") and c not in
                     ("kind", "outcome", "failure_category", "role", "practice_set_id", "user_id", "teacher_id")]
        assert free_text == [], (table, free_text)


def test_adm07_ac4_request_log_rows_hold_only_enumerated_text():
    kinds = {r[0] for r in sql("SELECT DISTINCT kind FROM analytics_request_log")}
    assert kinds <= {"chatbot", "generation_notes", "generation_mcq"}
    cats = {r[0] for r in sql("SELECT DISTINCT failure_category FROM analytics_request_log") if r[0] is not None}
    assert cats <= {"timeout", "rate_limited", "invalid_output", "upstream", "unclassified"}
