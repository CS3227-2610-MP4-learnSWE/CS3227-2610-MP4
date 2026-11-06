"""The merged ADM-05/STU-04 graph must upgrade existing installations safely."""
import os
import uuid

import psycopg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from auth_helpers import psycopg_url
from test_shr01_seed_migration import Isolated

MERGE_REVISION = "20261106_merge_adm05_stu04"
PARENTS = ("20261106_adm05_access", "20261105_stu04_practice_attempt")


def test_adm05_stu04_merge_has_one_head_and_preserves_both_parents():
    graph = ScriptDirectory.from_config(Config("alembic.ini"))
    assert graph.get_heads() == [MERGE_REVISION]
    assert set(graph.get_revision(MERGE_REVISION).down_revision) == set(PARENTS)


@pytest.mark.parametrize("parent", PARENTS)
def test_adm05_stu04_merge_upgrades_either_existing_head_without_data_loss(parent):
    base = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    schema = "merge_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        isolated = Isolated(base, schema)
        isolated.migrate("upgrade", parent)
        isolated.sql("INSERT INTO \"user\"(id,display_name,role) VALUES ('merge-student','Retained','student')")
        if parent == PARENTS[0]:
            isolated.sql("UPDATE \"user\" SET access_status='disabled' WHERE id='merge-student'")
        else:
            isolated.sql("INSERT INTO practice_attempt(id,student_id,set_id,status) "
                         "VALUES ('merge-attempt','merge-student','intro-se-1','in_progress')")
        isolated.migrate("upgrade", "head")
        assert isolated.sql("SELECT version_num FROM alembic_version") == [(MERGE_REVISION,)]
        expected_status = "disabled" if parent == PARENTS[0] else "enabled"
        assert isolated.sql("SELECT display_name,access_status FROM \"user\" WHERE id='merge-student'") == [("Retained", expected_status)]
        expected_attempts = [] if parent == PARENTS[0] else [("merge-attempt", "in_progress")]
        assert isolated.sql("SELECT id,status FROM practice_attempt") == expected_attempts
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
