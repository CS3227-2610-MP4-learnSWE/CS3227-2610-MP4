"""Isolate TEA-01 database tests without touching any existing schema."""

import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest


_schema = None
_base_url = None


def _psycopg_url(url):
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _schema_url(url, schema):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["options"] = f"-csearch_path={schema}"
    return urlunsplit(parts._replace(query=urlencode(query)))


def pytest_sessionstart(session):
    global _schema, _base_url
    _base_url = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not _base_url:
        return
    import psycopg

    _schema = "tea01_" + uuid.uuid4().hex
    with psycopg.connect(_psycopg_url(_base_url), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{_schema}"')
    env = os.environ
    env["DATABASE_URL"] = _schema_url(_base_url, _schema)
    env.pop("FILE_STORAGE_DIR", None)
    env["APP_ENV"] = "development"
    env["ALLOW_DEMO_IDENTITY"] = "true"
    # SHR-01: auth settings and test-only seed credentials (never real passwords).
    from auth_helpers import AUTH_ENV, SEED_ENV, seed_state

    env.update(AUTH_ENV)
    env.update(SEED_ENV)
    backend = Path(__file__).resolve().parents[1]
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend, env=env, check=True)
        subprocess.run([sys.executable, "-m", "teacher_materials.seed"], cwd=backend, env=env, check=True)
        # Not check=True: before the auth code exists the failure must surface per auth test
        # (see auth_helpers.require_db), not abort the whole session and the older suites.
        seeded = subprocess.run([sys.executable, "-m", "auth.seed"], cwd=backend, env=env,
                                capture_output=True, text=True)
        seed_state["ready"] = seeded.returncode == 0
        seed_state["error"] = (seeded.stderr or seeded.stdout)[-600:]
    except BaseException:
        _cleanup()
        raise


def _cleanup():
    global _schema
    if _schema and _base_url:
        import psycopg

        with psycopg.connect(_psycopg_url(_base_url), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{_schema}" CASCADE')
        _schema = None


def pytest_sessionfinish(session, exitstatus):
    _cleanup()


@pytest.fixture
def tea01_database():
    if not _schema:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    import psycopg

    with psycopg.connect(_psycopg_url(os.environ["DATABASE_URL"])) as conn:
        yield conn


@pytest.fixture
def fake():
    """A fake LLM injected in place of the shared client (STU-03 tests).

    Imports are lazy so the older suites still collect without llm_client.
    """
    from companion_helpers import FakeLlm, install, uninstall

    f = FakeLlm()
    install(f)
    yield f
    uninstall()


@pytest.fixture
def fake_provider():
    """STU-02-published-sets: a FakeSetProvider (FIXTURE_SET, every student a member) replaces the DB provider.

    Tests that need the real DbSetProvider (test_stu02ps_db_*, seed, TEA-03 route agreement) do not use it.
    """
    from fake_sets import install_fake, uninstall_fake

    fake = install_fake()
    yield fake
    uninstall_fake()


@pytest.fixture
def fake_lessons():
    """STU-03-grounding: a FakeLessonProvider (every student a member of every course) replaces the DB provider."""
    from grounding_helpers import install_lessons, uninstall_lessons

    provider = install_lessons()
    yield provider
    uninstall_lessons()
