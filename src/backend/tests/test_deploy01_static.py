"""DEPLOY-01: public SPA hosting must never turn API failures into HTML."""
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from deployment.static import attach_frontend

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><h1>DEPLOY01 shell</h1>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('DEPLOY01');", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("DEPLOY01 outside secret", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/protected")
    def protected():
        raise HTTPException(401, "Sign in required")

    @app.post("/api/mutation")
    def mutation():
        raise HTTPException(403, "CSRF token required")

    attach_frontend(app, dist)
    with TestClient(app) as result:
        yield result


@pytest.mark.parametrize("path", ["/", "/login", "/student/lessons/123", "/admin/analytics"])
def test_deploy01_ac2_html_routes_support_refresh(client, path):
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "DEPLOY01 shell" in response.text


def test_deploy01_ac2_head_returns_headers_without_body(client):
    response = client.head("/student/overview", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert response.content == b""


@pytest.mark.parametrize("path", ["/api", "/api/unknown", "/api/unknown/deeper"])
def test_deploy01_ac2_unknown_api_is_json_404(client, path):
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_deploy01_ac2_api_unsupported_method_is_405(client):
    response = client.get("/api/mutation", headers={"Accept": "text/html"})
    assert response.status_code == 405
    assert "text/html" not in response.headers["content-type"]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_deploy01_ac2_static_cannot_accept_mutations(client, method):
    response = client.request(method, "/login", headers={"Accept": "text/html"})
    assert response.status_code == 405
    assert "DEPLOY01 shell" not in response.text


@pytest.mark.parametrize("path", ["/assets/missing.js", "/assets", "/favicon.ico", "/missing.css", "/.env", "/missing/index.html"])
def test_deploy01_ac2_missing_files_and_asset_prefix_never_fallback(client, path):
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code == 404
    assert "DEPLOY01 shell" not in response.text


def test_deploy01_ac2_existing_asset_bytes_are_served(client):
    response = client.get("/assets/app.js")
    assert response.status_code == 200
    assert response.text == "console.log('DEPLOY01');"
    assert client.head("/assets/app.js").content == b""


@pytest.mark.parametrize("accept", ["application/json", "*/*", "text/plain"])
def test_deploy01_ac2_non_html_route_does_not_fallback(client, accept):
    response = client.get("/student/overview", headers={"Accept": accept})
    assert response.status_code == 404
    assert "DEPLOY01 shell" not in response.text


def test_deploy01_ac2_root_allows_browser_wildcard(client):
    assert client.get("/", headers={"Accept": "*/*"}).status_code == 200


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "/assets/%2e%2e/%2e%2e/secret.txt", "/%2e%2e%5csecret.txt", "/assets/%252e%252e/secret.txt"])
def test_deploy01_ac2_traversal_cannot_read_outside_build(client, path):
    response = client.get(path, headers={"Accept": "text/html"})
    assert response.status_code in (400, 404)
    assert "DEPLOY01 outside secret" not in response.text
    assert "DEPLOY01 shell" not in response.text


def test_deploy01_ac5_existing_auth_and_csrf_errors_preserved(client):
    assert client.get("/api/protected", headers={"Accept": "text/html"}).json() == {"detail": "Sign in required"}
    response = client.post("/api/mutation", headers={"Accept": "text/html"})
    assert response.status_code == 403
    assert response.json() == {"detail": "CSRF token required"}


def test_deploy01_ac2_missing_build_does_not_invent_shell(tmp_path):
    from deployment.static import attach_frontend
    app = FastAPI()
    attach_frontend(app, tmp_path / "absent")
    with TestClient(app) as client:
        assert client.get("/login", headers={"Accept": "text/html"}).status_code == 404


@pytest.mark.parametrize("method", ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@pytest.mark.parametrize("path", ["/api", "/api/unknown", "/api/unknown/deeper"])
def test_deploy01_ac2_unknown_api_methods_preserve_framework_behavior(tmp_path, method, path):
    """Adding static hosting must not change the API-only router's errors."""
    from deployment.static import attach_frontend

    reference = FastAPI()
    hosted = FastAPI()
    attach_frontend(hosted, tmp_path)
    with TestClient(reference) as before, TestClient(hosted) as after:
        expected = before.request(method, path, follow_redirects=False)
        actual = after.request(method, path, follow_redirects=False)
    assert actual.status_code == expected.status_code
    assert actual.content == expected.content
    assert actual.headers.get("content-type") == expected.headers.get("content-type")
    assert actual.headers.get("allow") == expected.headers.get("allow")


@pytest.mark.parametrize("method", ["GET", "HEAD", "POST", "OPTIONS", "DELETE"])
@pytest.mark.parametrize("path", ["/api/read", "/api/read/", "/api/mutation", "/api/mutation/"])
def test_deploy01_ac2_existing_api_slash_and_method_behavior_unchanged(tmp_path, method, path):
    """Framework redirects and 405 responses belong to the existing API."""
    from deployment.static import attach_frontend

    def api_app():
        app = FastAPI()

        @app.get("/api/read")
        def read():
            return {"status": "read"}

        @app.post("/api/mutation")
        def mutate():
            raise HTTPException(403, "CSRF token required")

        return app

    reference, hosted = api_app(), api_app()
    attach_frontend(hosted, tmp_path)
    with TestClient(reference) as before, TestClient(hosted) as after:
        expected = before.request(method, path, follow_redirects=False)
        actual = after.request(method, path, follow_redirects=False)
    assert actual.status_code == expected.status_code
    assert actual.content == expected.content
    for header in ("content-type", "location", "allow"):
        assert actual.headers.get(header) == expected.headers.get(header)
