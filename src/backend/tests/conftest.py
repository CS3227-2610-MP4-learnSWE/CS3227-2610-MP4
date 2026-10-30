"""Isolate TEA-01 database tests without touching any existing schema."""

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest


_schema = None
_storage = None
_base_url = None


def _psycopg_url(url):
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _schema_url(url, schema):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query["options"] = f"-csearch_path={schema}"
    return urlunsplit(parts._replace(query=urlencode(query)))


def pytest_sessionstart(session):
    global _schema, _storage, _base_url
    _base_url = os.environ.get("TEA01_TEST_DATABASE_URL")
    if not _base_url:
        return
    import psycopg

    _schema = "tea01_" + uuid.uuid4().hex
    _storage = Path(tempfile.mkdtemp(prefix="tea01-files-"))
    with psycopg.connect(_psycopg_url(_base_url), autocommit=True) as conn:
        conn.execute(f'CREATE SCHEMA "{_schema}"')
    env = os.environ
    env["DATABASE_URL"] = _schema_url(_base_url, _schema)
    env["FILE_STORAGE_DIR"] = str(_storage)
    env["APP_ENV"] = "development"
    env["ALLOW_DEMO_IDENTITY"] = "true"
    backend = Path(__file__).resolve().parents[1]
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend, env=env, check=True)
        subprocess.run([sys.executable, "-m", "teacher_materials.seed"], cwd=backend, env=env, check=True)
    except BaseException:
        _cleanup()
        raise


def _cleanup():
    global _schema, _storage
    if _schema and _base_url:
        import psycopg

        with psycopg.connect(_psycopg_url(_base_url), autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{_schema}" CASCADE')
        _schema = None
    if _storage:
        shutil.rmtree(_storage, ignore_errors=True)
        _storage = None


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
def tea01_storage():
    if not _storage:
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    return _storage
