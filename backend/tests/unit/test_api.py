from unittest.mock import patch

from fastapi import APIRouter

from football_ai.core.errors import NotFoundError
from football_ai.main import create_app


async def test_health_reports_degraded_when_db_down(client) -> None:
    with patch("football_ai.api.v1.health.check_database", return_value=False):
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"
    assert body["ai_provider"] == "mock"


async def test_health_ok_when_db_up(client) -> None:
    with patch("football_ai.api.v1.health.check_database", return_value=True):
        resp = await client.get("/api/v1/health")
    assert resp.json()["status"] == "ok"


async def test_request_id_generated_and_echoed(client) -> None:
    with patch("football_ai.api.v1.health.check_database", return_value=True):
        generated = await client.get("/api/v1/health")
        echoed = await client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
        rejected = await client.get("/api/v1/health", headers={"X-Request-ID": "bad id<script>"})
    assert len(generated.headers["X-Request-ID"]) == 32
    assert echoed.headers["X-Request-ID"] == "abc-123"
    assert rejected.headers["X-Request-ID"] != "bad id<script>"


async def test_unknown_route_returns_problem_json(client) -> None:
    resp = await client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["status"] == 404


async def test_app_error_mapped_to_problem_json(settings) -> None:
    from httpx import ASGITransport, AsyncClient

    app = create_app(settings)
    router = APIRouter()

    @router.get("/boom")
    async def boom() -> None:
        raise NotFoundError("Squadra non trovata")

    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        resp = await ac.get("/boom")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Squadra non trovata"
    assert resp.json()["type"].endswith("non_trovato")


async def test_cors_allows_only_configured_origin(client) -> None:
    allowed = await client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    denied = await client.options(
        "/api/v1/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers
