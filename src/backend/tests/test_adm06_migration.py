"""ADM-06 additive migration and persistence; disposable schemas only."""
import os
import uuid

import psycopg
import pytest

from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated


@pytest.fixture
def isolated():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "adm06_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_adm06_ac11_additive_upgrade_preserves_populated_user_and_attempt_history(isolated):
    isolated.migrate("upgrade", "20261106_merge_adm05_stu04")
    isolated.seed_teacher()
    isolated.sql('INSERT INTO "user"(id,display_name,role,email,access_status) '
                 'VALUES (\'adm06-existing\',\'Preserve\',\'student\',\'adm06-keep@example.com\',\'disabled\')')
    isolated.sql("INSERT INTO practice_attempt(id,student_id,set_id,status) "
                 "VALUES ('adm06-preserved-attempt','adm06-existing','intro-se-1','in_progress')")
    before = isolated.sql('SELECT t::text FROM "user" t ORDER BY id')
    attempts_before = isolated.sql("SELECT t::text FROM practice_attempt t ORDER BY id")
    isolated.migrate("upgrade", "head")
    assert isolated.sql('SELECT t::text FROM "user" t ORDER BY id') == before
    assert isolated.sql("SELECT t::text FROM practice_attempt t ORDER BY id") == attempts_before
    assert isolated.sql("SELECT feature,enabled,covered_since,incomplete_since FROM ai_usage_coverage ORDER BY feature") == [
        ("ADM-01", False, None, None), ("ADM-03", False, None, None),
        ("STU-03", False, None, None), ("TEA-02", False, None, None)]


def test_adm06_ac11_attempts_and_coverage_survive_fresh_process_and_idempotent_activation(isolated):
    isolated.migrate("upgrade", "head")
    isolated.run("-m", "ai_usage.activate", "--feature", "STU-03", "--feature", "TEA-02")
    original = isolated.sql("SELECT feature,enabled,covered_since,incomplete_since FROM ai_usage_coverage ORDER BY feature")
    isolated.run("-m", "ai_usage.activate", "--feature", "STU-03", "--feature", "TEA-02")
    assert isolated.sql("SELECT feature,enabled,covered_since,incomplete_since FROM ai_usage_coverage ORDER BY feature") == original
    isolated.run("-c", "from ai_usage.service import reserve_attempt,finish_attempt; "
                 "a=reserve_attempt('STU-03'); assert finish_attempt(a,'success',input_tokens=0,total_tokens=9)")
    isolated.run("-c", "from ai_usage.service import read_usage_report; from datetime import datetime,timezone; "
                 "d=datetime.now(timezone.utc).date(); r=read_usage_report('STU-03',d,d); "
                 "assert r['rows'][0]['requests']['reason']=='incomplete_coverage'")
    assert isolated.sql("SELECT feature,outcome,input_tokens,total_tokens FROM ai_service_attempts") == [
        ("STU-03", "success", 0, 9)]


@pytest.mark.parametrize("column,value", [("input_tokens", -1), ("output_tokens", -1), ("total_tokens", -1)])
def test_adm06_ac5_schema_enforces_nonnegative_token_fields(isolated, column, value):
    isolated.migrate("upgrade", "head")
    with pytest.raises(psycopg.errors.CheckViolation):
        isolated.sql(f"INSERT INTO ai_service_attempts (id,feature,started_at,outcome,{column}) "
                     "VALUES (%s,'STU-03',now(),'pending',%s)", (uuid.uuid4(), value))
