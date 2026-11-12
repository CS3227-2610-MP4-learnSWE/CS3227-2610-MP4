"""DEPLOY-01 DB probes expose availability only and have bounded work."""
from types import SimpleNamespace
import threading
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient


class Connection:
    def __init__(self, execute): self.execute = execute
    def __enter__(self): return self
    def __exit__(self, *args): return False


def client_for(monkeypatch, execute):
    import deployment.health as health
    monkeypatch.setattr(health, "load_settings", lambda: SimpleNamespace(database_url="postgresql+psycopg://private:secret@db/private"))
    engine = SimpleNamespace(connect=lambda: Connection(execute))
    monkeypatch.setattr(health, "engine_for", lambda url: engine)
    app = FastAPI()
    app.get("/api/health/database")(health.database_health)
    return TestClient(app)


def test_deploy01_ac6_successful_probe_is_public_fixed_shape(monkeypatch):
    statements = []
    client = client_for(monkeypatch, lambda sql, *a, **kw: statements.append(str(sql)))
    response = client.get("/api/health/database")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert any("select 1" in sql.lower() for sql in statements)


def test_deploy01_ac6_database_error_is_redacted_503(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("postgresql://private:secret@db/private SELECT sensitive")
    client = client_for(monkeypatch, fail)
    response = client.get("/api/health/database")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "secret" not in response.text


def test_deploy01_ac6_probe_deadline_and_no_unbounded_parallel_work(monkeypatch):
    release = threading.Event()
    entered = threading.Event()
    calls = []
    def blocked(*args, **kwargs):
        calls.append(1); entered.set(); release.wait(12)
    client = client_for(monkeypatch, blocked)
    started = time.monotonic()
    try:
        response = client.get("/api/health/database")
        assert entered.is_set()
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
        assert time.monotonic() - started < 6.5
        again = client.get("/api/health/database")
        assert again.status_code == 503
        assert len(calls) == 1
    finally:
        release.set()
