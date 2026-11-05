"""STU-01 AC15: additive Alembic revision 20261104_stu01_lessons, each case in a throwaway schema."""
import os
import uuid

import psycopg
import pytest
from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated

NEW_REVISION = "20261104_stu01_lessons"
PREVIOUS_REVISION = "20261104_tea03_mcq_edit"
NEW_TABLES = {"published_lesson", "lesson_completion"}
COURSE_A = "11111111-1111-4111-8111-111111111111"
TOPIC_A = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def iso():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "stu01_" + uuid.uuid4().hex
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
    """Every row of the given tables, as sorted text, to compare before and after."""
    out = {}
    for name in sorted(names):
        rows = iso.sql(f'SELECT t::text FROM "{name}" t')
        out[name] = sorted(r[0] for r in rows)
    return out


def columns(iso, table):
    return {r[0]: (r[1], r[2]) for r in iso.sql(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s", (iso.schema, table))}


def test_stu01_ac15_upgrade_on_a_fresh_schema_creates_exactly_the_two_tables(iso):
    iso.migrate("upgrade", PREVIOUS_REVISION)
    before = tables(iso)
    iso.migrate("upgrade", NEW_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    assert tables(iso) - before == NEW_TABLES
    assert before - tables(iso) == set()


def test_stu01_ac15_columns_and_nullability_follow_the_plan(migrated):
    lesson = columns(migrated, "published_lesson")
    assert set(lesson) == {"id", "course_id", "topic_id", "title", "content", "source_draft_id", "published_by",
                           "published_at", "withdrawn_at"}
    nullable = {k for k, v in lesson.items() if v[1] == "YES"}
    assert nullable == {"topic_id", "source_draft_id", "withdrawn_at"}
    assert lesson["id"][0] == "uuid" and lesson["published_at"][0] == "timestamp with time zone"
    comp = columns(migrated, "lesson_completion")
    assert set(comp) == {"user_id", "lesson_id", "course_id", "completed", "completed_at", "updated_at"}
    assert {k for k, v in comp.items() if v[1] == "YES"} == {"completed_at"}
    assert comp["completed"][0] == "boolean"


def test_stu01_ac15_named_constraints_and_indexes_exist(migrated):
    idx = {r[0] for r in migrated.sql("SELECT indexname FROM pg_indexes WHERE schemaname = %s",
                                      (migrated.schema,))}
    assert {"ix_published_lesson_course", "ix_lesson_completion_user_course", "ix_lesson_completion_lesson"} <= idx
    cons = {r[0] for r in migrated.sql(
        "SELECT conname FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = %s",
        (migrated.schema,))}
    assert {"uq_published_lesson_id_course", "ck_lesson_completion_state"} <= cons
    pk = migrated.sql(
        "SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indisprimary AND i.indrelid = 'lesson_completion'::regclass ORDER BY a.attname")
    assert [r[0] for r in pk] == ["lesson_id", "user_id"]


def test_stu01_ac15_populated_schema_keeps_every_existing_row_through_upgrade_downgrade_and_reupgrade(iso):
    iso.migrate("upgrade", PREVIOUS_REVISION)
    iso.seed_teacher()
    mid, did = str(uuid.uuid4()), str(uuid.uuid4())
    iso.sql("INSERT INTO material(id, course_id, uploaded_by, title, original_filename, media_type, size_bytes) "
            "VALUES (%s, %s, 'demo-teacher', 'Src', 's.txt', 'text/plain', 1)", (mid, COURSE_A))
    iso.sql("INSERT INTO study_note_draft(id, course_id, source_material_id, created_by, title, content, "
            "source_title, updated_by) VALUES (%s, %s, %s, 'demo-teacher', 'D', 'Keep me', 'Src', 'demo-teacher')",
            (did, COURSE_A, mid))
    old = tables(iso) - {"alembic_version"}
    before = snapshot(iso, old)
    assert before["study_note_draft"] and before["course"] and before["user"]

    iso.migrate("upgrade", NEW_REVISION)
    assert tables(iso) - {"alembic_version"} == old | NEW_TABLES
    assert snapshot(iso, old) == before

    iso.migrate("downgrade", PREVIOUS_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == PREVIOUS_REVISION
    assert tables(iso) - {"alembic_version"} == old
    assert snapshot(iso, old) == before

    iso.migrate("upgrade", NEW_REVISION)
    assert iso.sql("SELECT version_num FROM alembic_version")[0][0] == NEW_REVISION
    assert snapshot(iso, old) == before
    assert NEW_TABLES <= tables(iso)


def test_stu01_ac15_downgrade_with_lessons_and_completions_present_drops_only_the_new_tables(iso):
    # STU-04: head is now a later revision, so stop explicitly at the STU-01 revision.
    iso.migrate("upgrade", NEW_REVISION)
    iso.seed_teacher()
    migrated = iso
    lid = str(uuid.uuid4())
    migrated.sql("INSERT INTO published_lesson(id, course_id, title, content, published_by) "
                 "VALUES (%s, %s, 'T', 'C', 'demo-teacher')", (lid, COURSE_A))
    migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                 "VALUES ('demo-student', %s, %s, true, now())", (lid, COURSE_A))
    old = tables(migrated) - NEW_TABLES - {"alembic_version"}
    before = snapshot(migrated, old)
    migrated.migrate("downgrade", PREVIOUS_REVISION)
    assert tables(migrated) - {"alembic_version"} == old
    assert snapshot(migrated, old) == before


def test_stu01_ac15_migration_file_is_additive_and_history_is_not_edited():
    from pathlib import Path

    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    text = (versions / f"{NEW_REVISION}.py").read_text(encoding="utf-8")
    assert f'down_revision = "{PREVIOUS_REVISION}"' in text
    assert (versions / f"{PREVIOUS_REVISION}.py").exists()


# ------------------------------------------------------------------ schema rules (AC15 "FKs and the CHECK work")
def insert_lesson(iso, *, course=COURSE_A, topic=None, title="T", content="C", lid=None):
    lid = lid or str(uuid.uuid4())
    iso.sql("INSERT INTO published_lesson(id, course_id, topic_id, title, content, published_by) "
            "VALUES (%s, %s, %s, %s, %s, 'demo-teacher')", (lid, course, topic, title, content))
    return lid


def test_stu01_ac15_a_lesson_topic_must_belong_to_the_lessons_course(migrated):
    other_course = str(uuid.uuid4())
    migrated.sql("INSERT INTO course(id, title) VALUES (%s, 'Other')", (other_course,))
    insert_lesson(migrated, course=COURSE_A, topic=TOPIC_A)  # the right pair works
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_lesson(migrated, course=other_course, topic=TOPIC_A)  # topic of another course
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_lesson(migrated, course=str(uuid.uuid4()))  # unknown course


def test_stu01_ac15_lesson_title_and_content_limits(migrated):
    insert_lesson(migrated, title="t" * 200, content="c" * 2000)
    for kwargs in ({"title": ""}, {"content": ""}, {"content": "c" * 2001}):
        with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.DataError)):
            insert_lesson(migrated, **kwargs)
    with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.DataError)):
        insert_lesson(migrated, title="t" * 201)


def test_stu01_ac15_published_by_must_be_a_user(migrated):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        migrated.sql("INSERT INTO published_lesson(id, course_id, title, content, published_by) "
                     "VALUES (%s, %s, 'T', 'C', 'nobody')", (str(uuid.uuid4()), COURSE_A))


def test_stu01_ac15_completion_state_check_and_primary_key(migrated):
    lid = insert_lesson(migrated)
    with pytest.raises(psycopg.errors.CheckViolation):  # completed true needs completed_at
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES ('demo-student', %s, %s, true, NULL)", (lid, COURSE_A))
    with pytest.raises(psycopg.errors.CheckViolation):  # completed false must not have completed_at
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES ('demo-student', %s, %s, false, now())", (lid, COURSE_A))
    migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                 "VALUES ('demo-student', %s, %s, true, now())", (lid, COURSE_A))
    migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                 "VALUES ('demo-teacher', %s, %s, false, NULL)", (lid, COURSE_A))
    with pytest.raises(psycopg.errors.UniqueViolation):  # one row per student and lesson
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES ('demo-student', %s, %s, false, NULL)", (lid, COURSE_A))


def test_stu01_ac15_a_completion_row_cannot_carry_another_courses_id(migrated):
    other_course = str(uuid.uuid4())
    migrated.sql("INSERT INTO course(id, title) VALUES (%s, 'Other')", (other_course,))
    lid = insert_lesson(migrated)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES ('demo-student', %s, %s, false, NULL)", (lid, other_course))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # unknown user
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES ('nobody', %s, %s, false, NULL)", (lid, COURSE_A))


def test_stu01_ac15_deleting_a_user_removes_their_completion_rows_only(migrated):
    lid = insert_lesson(migrated)
    uid_ = "u-" + "e" * 32
    migrated.sql('INSERT INTO "user"(id, display_name, role) VALUES (%s, %s, %s)', (uid_, "Gone", "student"))
    for user in (uid_, "demo-student"):
        migrated.sql("INSERT INTO lesson_completion(user_id, lesson_id, course_id, completed, completed_at) "
                     "VALUES (%s, %s, %s, true, now())", (user, lid, COURSE_A))
    migrated.sql('DELETE FROM "user" WHERE id = %s', (uid_,))
    assert migrated.sql("SELECT user_id FROM lesson_completion WHERE lesson_id = %s", (lid,)) == [("demo-student",)]


def seed_draft(iso):
    mid, did = str(uuid.uuid4()), str(uuid.uuid4())
    iso.sql("INSERT INTO material(id, course_id, uploaded_by, title, original_filename, media_type, size_bytes) "
            "VALUES (%s, %s, 'demo-teacher', 'Src', 's.txt', 'text/plain', 1)", (mid, COURSE_A))
    iso.sql("INSERT INTO study_note_draft(id, course_id, source_material_id, created_by, title, content, "
            "source_title, updated_by) VALUES (%s, %s, %s, 'demo-teacher', 'D', 'C', 'Src', 'demo-teacher')",
            (did, COURSE_A, mid))
    return did


def test_stu01_ac15_deleting_a_draft_with_a_published_lesson_is_restricted(migrated):
    did = seed_draft(migrated)
    lid = str(uuid.uuid4())
    migrated.sql("INSERT INTO published_lesson(id, course_id, title, content, published_by, source_draft_id) "
                 "VALUES (%s, %s, 'T', 'C', 'demo-teacher', %s)", (lid, COURSE_A, did))
    with pytest.raises(psycopg.errors.ForeignKeyViolation) as exc:
        migrated.sql("DELETE FROM study_note_draft WHERE id = %s", (did,))
    assert exc.value.sqlstate == "23503"
    assert migrated.sql("SELECT source_draft_id::text FROM published_lesson WHERE id = %s", (lid,)) == [(did,)]
    assert migrated.sql("SELECT count(*) FROM study_note_draft WHERE id = %s", (did,)) == [(1,)]


def test_stu01_ac15_deleting_an_unreferenced_draft_works_and_null_source_is_allowed(migrated):
    lone = seed_draft(migrated)
    referenced = seed_draft(migrated)
    lid, orphan = str(uuid.uuid4()), insert_lesson(migrated)  # NULL source_draft_id is allowed
    migrated.sql("INSERT INTO published_lesson(id, course_id, title, content, published_by, source_draft_id) "
                 "VALUES (%s, %s, 'T', 'C', 'demo-teacher', %s)", (lid, COURSE_A, referenced))
    migrated.sql("DELETE FROM study_note_draft WHERE id = %s", (lone,))
    assert migrated.sql("SELECT count(*) FROM study_note_draft WHERE id = %s", (lone,)) == [(0,)]
    assert migrated.sql("SELECT source_draft_id FROM published_lesson WHERE id = %s", (orphan,)) == [(None,)]
