"""ADM-05 additive account-status migration, in disposable schemas only."""
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
    schema = "adm05_" + uuid.uuid4().hex
    with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield Isolated(base, schema)
    finally:
        with psycopg.connect(psycopg_url(base), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def test_adm05_migration_defaults_and_status_constraints(isolated):
    isolated.migrate("upgrade", "head")
    isolated.sql('INSERT INTO "user"(id,display_name,role) VALUES (\'adm05-old\',\'Keep me\',\'student\')')
    assert isolated.sql('SELECT access_status,archived_at FROM "user" WHERE id=\'adm05-old\'') == [("enabled", None)]
    with pytest.raises(psycopg.errors.CheckViolation):
        isolated.sql('UPDATE "user" SET access_status=\'deleted\' WHERE id=\'adm05-old\'')


def test_adm05_migration_populated_upgrade_and_enabled_downgrade_reupgrade(isolated):
    isolated.migrate("upgrade", "head")
    isolated.migrate("downgrade", "-1")
    isolated.sql('INSERT INTO "user"(id,display_name,role,email) VALUES (\'adm05-old\',\'Keep me\',\'student\',\'keep@example.com\')')
    isolated.migrate("upgrade", "head")
    assert isolated.sql('SELECT display_name,email,access_status FROM "user" WHERE id=\'adm05-old\'') == [("Keep me", "keep@example.com", "enabled")]
    isolated.migrate("downgrade", "-1")
    assert isolated.sql('SELECT display_name,email FROM "user" WHERE id=\'adm05-old\'') == [("Keep me", "keep@example.com")]
    isolated.migrate("upgrade", "head")
    assert isolated.sql('SELECT access_status FROM "user" WHERE id=\'adm05-old\'') == [("enabled",)]


@pytest.mark.parametrize("status", ["disabled", "archived"])
def test_adm05_migration_refuses_downgrade_that_would_reactivate_accounts(isolated, status):
    isolated.migrate("upgrade", "head")
    isolated.sql('INSERT INTO "user"(id,display_name,role,access_status) VALUES (\'adm05-inactive\',\'Inactive\',\'student\',%s)', (status,))
    response = isolated.migrate("downgrade", "-1", check=False)
    assert response.returncode != 0
    assert isolated.sql('SELECT access_status FROM "user" WHERE id=\'adm05-inactive\'') == [(status,)]
