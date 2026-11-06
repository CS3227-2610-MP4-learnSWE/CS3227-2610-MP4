"""ADM-02 additive upgrade from the approved pre-feature head, isolated schemas only."""
import os
import uuid

import psycopg
import pytest

from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated


@pytest.fixture
def isolated_adm02():
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "adm02_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_adm02_ac06_22_additive_upgrade_preserves_users_progress_and_usage(isolated_adm02):
    db = isolated_adm02
    db.migrate("upgrade", "20261106_adm06_ai_usage")
    db.seed_teacher()
    db.sql('INSERT INTO "user"(id,display_name,role,email,access_status) '
           "VALUES ('adm02-preserve','Preserved','student','adm02-preserve@example.com','disabled')")
    db.sql("INSERT INTO practice_attempt(id,student_id,set_id,status) VALUES "
           "('adm02-preserve-attempt','adm02-preserve','intro-se-1','in_progress')")
    baseline = {table: db.sql(f'SELECT t::text FROM "{table}" t ORDER BY t::text')
                for table in ("user", "course_membership", "practice_attempt", "ai_usage_coverage")}
    db.migrate("upgrade", "head")
    for table, before in baseline.items():
        assert db.sql(f'SELECT t::text FROM "{table}" t ORDER BY t::text') == before
    for table in ("feedback_forms", "feedback_recipients", "feedback_response_drafts", "feedback_responses"):
        assert db.sql("SELECT to_regclass(%s)::text", (table,))[0][0] == table
        assert db.sql(f"SELECT count(*) FROM {table}")[0][0] == 0
    # A fresh Python/DB process sees the additive schema and unchanged history.
    db.run("-c", "import os,psycopg; c=psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://','postgresql://')); "
           "assert c.execute('SELECT count(*) FROM feedback_response_drafts').fetchone()[0] == 0; "
           "assert c.execute(\"SELECT count(*) FROM practice_attempt WHERE id='adm02-preserve-attempt'\").fetchone()[0] == 1; c.close()")
