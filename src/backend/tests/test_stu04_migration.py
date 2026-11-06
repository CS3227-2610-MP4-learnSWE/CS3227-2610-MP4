"""STU-04 AC18: additive Alembic revision 20261105_stu04_practice_attempt, each case in a throwaway schema."""
import os
import uuid

import psycopg
import pytest
from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated

NEW_REVISION = "20261105_stu04_practice_attempt"
PREVIOUS_REVISION = "20261105_tea03_publications"
NEW_TABLES = {"practice_attempt"}
COURSE_A = "11111111-1111-4111-8111-111111111111"
SE_BASICS_TOPIC = "66666666-6666-4666-8666-666666666661"
STUDENT = "demo-student"


@pytest.fixture
def iso():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "stu04_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture
def migrated(iso):
    iso.migrate("upgrade", "head")
    iso.seed_teacher()
    return iso


def tables(iso):
    return {r[0] for r in iso.sql("SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                                  (iso.schema,))}


def snapshot(iso, names):
    out = {}
    for name in sorted(names):
        rows = iso.sql(f'SELECT t::text FROM "{name}" t')
        out[name] = sorted(r[0] for r in rows)
    return out


def columns(iso, table):
    return {r[0]: (r[1], r[2]) for r in iso.sql(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s", (iso.schema, table))}


def new_attempt(iso, *, aid=None, student=STUDENT, status="in_progress", answers="{}", correct=None, total=None,
                key_version=None, correct_ids="[]", submitted_at=None, set_id="a0000000-0000-4000-8000-000000000001"):
    aid = aid or "a-" + uuid.uuid4().hex[:20]
    iso.sql("INSERT INTO practice_attempt(id, student_id, set_id, status, answers, score_correct, score_total, "
            "key_version, correct_question_ids, submitted_at) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, "
            "%s::jsonb, %s)", (aid, student, set_id, status, answers, correct, total, key_version, correct_ids,
                               submitted_at))
    return aid


def submitted_attempt(iso, **kw):
    kw = {"status": "submitted", "correct": 2, "total": 3, "key_version": "v1", "correct_ids": '["q1","q2"]',
          "submitted_at": "2026-03-01T10:00:00Z", **kw}
    return new_attempt(iso, **kw)


# ------------------------------------------------------------------ revision, tables, columns
def test_stu04_ac18_upgrade_on_a_fresh_schema_creates_exactly_practice_attempt(iso):
    iso.migrate("upgrade", PREVIOUS_REVISION)
    before = tables(iso)
    iso.migrate("upgrade", "head")
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    assert tables(iso) - before == NEW_TABLES
    assert before - tables(iso) == set()


def test_stu04_ac18_columns_types_and_nullability_follow_the_plan(migrated):
    cols = columns(migrated, "practice_attempt")
    assert set(cols) == {"id", "seq", "student_id", "set_id", "status", "answers", "score_correct", "score_total",
                         "key_version", "correct_question_ids", "created_at", "submitted_at"}
    assert {k for k, v in cols.items() if v[1] == "YES"} == {"score_correct", "score_total", "key_version",
                                                              "submitted_at"}
    assert cols["id"][0] == "character varying" and cols["student_id"][0] == "character varying"
    assert cols["seq"][0] == "bigint"
    assert cols["answers"][0] == "jsonb" and cols["correct_question_ids"][0] == "jsonb"
    assert cols["created_at"][0] == "timestamp with time zone" and cols["submitted_at"][0] == "timestamp with time zone"
    assert cols["score_correct"][0] == "integer" and cols["score_total"][0] == "integer"


def test_stu04_ac18_named_constraints_indexes_and_primary_key_exist(migrated):
    idx = {r[0] for r in migrated.sql("SELECT indexname FROM pg_indexes WHERE schemaname = %s",
                                      (migrated.schema,))}
    assert {"ix_practice_attempt_student_set", "ix_practice_attempt_submitted"} <= idx
    cons = {r[0] for r in migrated.sql(
        "SELECT conname FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = %s",
        (migrated.schema,))}
    assert {"uq_practice_attempt_seq", "ck_practice_attempt_status", "ck_practice_attempt_state",
            "ck_practice_attempt_score"} <= cons
    pk = migrated.sql(
        "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indisprimary AND i.indrelid = 'practice_attempt'::regclass")
    assert [r[0] for r in pk] == ["id"]


def test_stu04_ac18_seq_is_generated_always_and_follows_creation_order(migrated):
    first, second = new_attempt(migrated), new_attempt(migrated)
    rows = dict(migrated.sql("SELECT id, seq FROM practice_attempt"))
    assert rows[second] > rows[first]
    with pytest.raises(psycopg.Error):  # GENERATED ALWAYS refuses an explicit value
        migrated.sql("INSERT INTO practice_attempt(id, seq, student_id, set_id, status) "
                     "VALUES ('x-explicit', 99, %s, 'a0000000-0000-4000-8000-000000000001', 'in_progress')", (STUDENT,))


def test_stu04_ac18_defaults_are_filled_in(migrated):
    aid = new_attempt(migrated)
    row = migrated.sql("SELECT answers::text, correct_question_ids::text, created_at IS NOT NULL, status "
                       "FROM practice_attempt WHERE id = %s", (aid,))[0]
    assert row == ("{}", "[]", True, "in_progress")
    migrated.sql("INSERT INTO practice_attempt(id, student_id, set_id, status) VALUES ('x-defaults', %s, 's', "
                 "'in_progress')", (STUDENT,))
    assert migrated.sql("SELECT answers::text, correct_question_ids::text FROM practice_attempt "
                        "WHERE id = 'x-defaults'") == [("{}", "[]")]


def test_stu04_ac18_populated_schema_keeps_every_existing_row_through_upgrade_downgrade_and_reupgrade(iso):
    iso.migrate("upgrade", PREVIOUS_REVISION)
    iso.seed_teacher()
    lid = str(uuid.uuid4())
    iso.sql("INSERT INTO published_lesson(id, course_id, title, content, published_by) "
            "VALUES (%s, %s, 'T', 'Keep me', 'demo-teacher')", (lid, COURSE_A))
    iso.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
            "VALUES ('demo-student', %s, %s, true, now())", (lid, COURSE_A))
    old = tables(iso) - {"alembic_version"}
    before = snapshot(iso, old)
    assert before["published_lesson"] and before["lesson_completion"] and before["user"]

    iso.migrate("upgrade", "head")
    assert tables(iso) - {"alembic_version"} == old | NEW_TABLES
    assert snapshot(iso, old) == before

    iso.migrate("downgrade", PREVIOUS_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == PREVIOUS_REVISION
    assert tables(iso) - {"alembic_version"} == old
    assert snapshot(iso, old) == before

    iso.migrate("upgrade", "head")
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    assert snapshot(iso, old) == before
    assert NEW_TABLES <= tables(iso)


def test_stu04_ac18_downgrade_with_attempts_present_drops_only_practice_attempt(migrated):
    submitted_attempt(migrated)
    new_attempt(migrated)
    old = tables(migrated) - NEW_TABLES - {"alembic_version"}
    before = snapshot(migrated, old)
    migrated.migrate("downgrade", PREVIOUS_REVISION)
    assert tables(migrated) - {"alembic_version"} == old
    assert snapshot(migrated, old) == before


def test_stu04_ac18_there_is_a_single_head_and_history_is_not_edited():
    from pathlib import Path

    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    text = (versions / f"{NEW_REVISION}.py").read_text(encoding="utf-8")
    assert f'down_revision = "{PREVIOUS_REVISION}"' in text
    assert (versions / f"{PREVIOUS_REVISION}.py").exists()
    heads = [p for p in versions.glob("*.py") if f'down_revision = "{NEW_REVISION}"' in p.read_text(encoding="utf-8")]
    assert heads == []


# ------------------------------------------------------------------ schema rules
def test_stu04_ac18_status_must_be_in_progress_or_submitted(migrated):
    with pytest.raises(psycopg.errors.CheckViolation):
        new_attempt(migrated, status="done")
    with pytest.raises(psycopg.errors.CheckViolation):
        new_attempt(migrated, status="")


def test_stu04_ac18_a_submitted_row_needs_score_key_version_and_timestamp(migrated):
    full = {"status": "submitted", "correct": 2, "total": 3, "key_version": "v1",
            "submitted_at": "2026-03-01T10:00:00Z"}
    submitted_attempt(migrated)  # complete row works
    for missing in ("correct", "total", "key_version", "submitted_at"):
        kw = {**full, missing: None}
        with pytest.raises(psycopg.errors.CheckViolation):
            new_attempt(migrated, **kw)


def test_stu04_ac18_an_in_progress_row_must_not_carry_score_or_timestamp(migrated):
    for kw in ({"correct": 1, "total": 3}, {"key_version": "v1"}, {"submitted_at": "2026-03-01T10:00:00Z"}):
        with pytest.raises(psycopg.errors.CheckViolation):
            new_attempt(migrated, **kw)


def test_stu04_ac18_score_correct_must_be_between_zero_and_score_total(migrated):
    submitted_attempt(migrated, correct=0, total=3)
    submitted_attempt(migrated, correct=3, total=3)
    with pytest.raises(psycopg.errors.CheckViolation):
        submitted_attempt(migrated, correct=4, total=3)
    with pytest.raises(psycopg.errors.CheckViolation):
        submitted_attempt(migrated, correct=-1, total=3)


def test_stu04_ac18_answers_must_be_a_json_object_and_correct_ids_a_json_array(migrated):
    with pytest.raises(psycopg.errors.CheckViolation):
        new_attempt(migrated, answers="[]")
    with pytest.raises(psycopg.errors.CheckViolation):
        new_attempt(migrated, answers='"text"')
    with pytest.raises(psycopg.errors.CheckViolation):
        new_attempt(migrated, correct_ids="{}")
    new_attempt(migrated, answers='{"q1": "a"}')  # in progress: correct ids stay []
    submitted_attempt(migrated, answers='{"q1": "a", "q2": "b"}', correct_ids='["q1"]')


def test_stu04_ac18_student_must_be_a_user_and_deleting_a_user_removes_only_their_attempts(migrated):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        new_attempt(migrated, student="nobody")
    gone = "u-" + "f" * 32
    migrated.sql('INSERT INTO "user"(id, display_name, role) VALUES (%s, %s, %s)', (gone, "Gone", "student"))
    keep = new_attempt(migrated)
    new_attempt(migrated, student=gone)
    submitted_attempt(migrated, student=gone)
    migrated.sql('DELETE FROM "user" WHERE id = %s', (gone,))
    assert migrated.sql("SELECT count(*) FROM practice_attempt WHERE student_id = %s", (gone,)) == [(0,)]
    assert migrated.sql("SELECT id FROM practice_attempt WHERE id = %s", (keep,)) == [(keep,)]


def test_stu04_ac18_the_id_is_unique(migrated):
    new_attempt(migrated, aid="dup-id")
    with pytest.raises(psycopg.errors.UniqueViolation):
        new_attempt(migrated, aid="dup-id")


# ------------------------------------------------------------------ seed
def test_stu04_ac18_the_dev_seed_adds_the_basics_topic_idempotently(migrated):
    rows = migrated.sql("SELECT course_id::text, name FROM topic WHERE id = %s", (SE_BASICS_TOPIC,))
    assert rows == [(COURSE_A, "Software engineering basics")]
    migrated.seed_teacher()  # run again: no error, no duplicate
    assert migrated.sql("SELECT count(*) FROM topic WHERE id = %s", (SE_BASICS_TOPIC,)) == [(1,)]
