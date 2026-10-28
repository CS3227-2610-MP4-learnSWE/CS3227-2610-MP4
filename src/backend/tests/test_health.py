"""Exercise the HTTP boundary through the real ASGI app, without a network server."""
import asyncio

import httpx
from main import app


def request(method: str, path: str) -> httpx.Response:
    async def send() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path)

    return asyncio.run(send())


def test_liveness():
    response = request("GET", "/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness():
    response = request("GET", "/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_no_business_endpoints():
    assert request("POST", "/api/login").status_code == 404
    assert request("GET", "/api/courses").status_code == 404
