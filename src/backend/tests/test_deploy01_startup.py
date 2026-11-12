"""DEPLOY-01 startup must reject unusable configuration before HTTP serving."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def run_start(tmp_path, overrides):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><h1>shell</h1>", encoding="utf-8")
    env = dict(os.environ)
    env.update(APP_ENV="production", SESSION_COOKIE_SECURE="true", SESSION_COOKIE_SAMESITE="lax", ALLOWED_ORIGINS="https://learnswe.example", DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:1/test?connect_timeout=1", FRONTEND_DIST_DIR=str(dist))
    env.update(overrides)
    return subprocess.run([sys.executable, "-m", "deployment.start"], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=12)


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port", "-1", "8000.5"])
def test_deploy01_ac1_invalid_port_fails_closed(tmp_path, port):
    result = run_start(tmp_path, {"PORT": port})
    assert result.returncode != 0
    assert "No module named" not in result.stderr
    assert "Uvicorn running" not in result.stdout + result.stderr
    assert "postgresql+psycopg://test:test" not in result.stdout + result.stderr


def test_deploy01_ac1_production_insecure_cookie_fails_closed(tmp_path):
    result = run_start(tmp_path, {"SESSION_COOKIE_SECURE": "false"})
    assert result.returncode != 0
    assert "No module named" not in result.stderr
    assert "Uvicorn running" not in result.stdout + result.stderr


def test_deploy01_ac1_missing_production_build_fails_closed(tmp_path):
    result = run_start(tmp_path, {"FRONTEND_DIST_DIR": str(tmp_path / "missing")})
    assert result.returncode != 0
    assert "No module named" not in result.stderr
    assert "Uvicorn running" not in result.stdout + result.stderr


def test_deploy01_ac4_database_connection_failure_blocks_start_without_credentials(tmp_path):
    result = run_start(tmp_path, {"PORT": "8000"})
    assert result.returncode != 0
    assert "No module named" not in result.stderr
    assert "Uvicorn running" not in result.stdout + result.stderr
    assert "test:test" not in result.stdout + result.stderr


class FakeConnection:
    def __init__(self, events): self.events = events
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, statement, *args, **kwargs):
        text = str(statement).lower()
        if "unlock" in text: self.events.append("unlock")
        elif "advisory" in text: self.events.append("lock")
        class Result:
            def scalar(self): return True
            def scalar_one(self): return True
        return Result()
    def commit(self): pass
    def rollback(self): pass


def test_deploy01_ac4_migration_is_inside_db_lock_and_unlocks_on_failure(monkeypatch):
    import deployment.start as start
    events = []
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    class Engine:
        def connect(self): return FakeConnection(events)
        def dispose(self): events.append("dispose")
    monkeypatch.setattr(start, "create_engine", lambda *a, **kw: Engine())
    def fail(*args, **kwargs):
        events.append("upgrade")
        raise RuntimeError("migration failed")
    monkeypatch.setattr(start.command, "upgrade", fail)
    with pytest.raises(Exception):
        start.migrate("postgresql+psycopg://test:test@localhost/test")
    assert "upgrade" in events
    assert events.index("lock") < events.index("upgrade") < events.index("unlock")


def test_deploy01_ac4_migration_contract_constants():
    from deployment.start import MIGRATION_LOCK_KEY, LOCK_TIMEOUT_SECONDS
    assert MIGRATION_LOCK_KEY == 3227261001
    assert LOCK_TIMEOUT_SECONDS == 60


def test_deploy01_ac4_lock_cannot_target_different_database(monkeypatch):
    import deployment.start as start
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/configured")
    calls = []
    monkeypatch.setattr(start, "create_engine", lambda *a, **kw: calls.append(a))
    with pytest.raises(Exception):
        start.migrate("postgresql+psycopg://test:test@localhost/other")
    assert not calls
