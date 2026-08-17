"""
Tests — GET /health endpoint
==============================
Verifies that the health endpoint:
  - Returns HTTP 200
  - Returns the correct JSON structure
  - Reports the expected fields

These tests use httpx.AsyncClient with FastAPI's ASGITransport so they
run fully in-process without needing a live server.

The database may or may not be running during these tests.
We assert structure and status code, NOT that the DB is connected,
because the DB connectivity is tested separately in test_database.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Provide an async HTTP client wired directly to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health must return HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. Body: {response.text}"
    )


async def test_health_json_structure(client: AsyncClient) -> None:
    """GET /health must return the expected top-level JSON keys."""
    response = await client.get("/health")
    body = response.json()

    assert "status" in body, "Missing 'status' key"
    assert "environment" in body, "Missing 'environment' key"
    assert "uptime_seconds" in body, "Missing 'uptime_seconds' key"
    assert "database" in body, "Missing 'database' key"


async def test_health_status_is_ok(client: AsyncClient) -> None:
    """GET /health must always report status == 'ok' (app-level, not DB-level)."""
    response = await client.get("/health")
    body = response.json()
    assert body["status"] == "ok", f"Expected status='ok', got {body['status']!r}"


async def test_health_database_section_structure(client: AsyncClient) -> None:
    """GET /health database section must contain expected keys regardless of DB state."""
    response = await client.get("/health")
    db = response.json()["database"]

    assert "connected" in db, "Missing 'database.connected'"
    assert "postgres_version" in db, "Missing 'database.postgres_version'"
    assert "pgvector_version" in db, "Missing 'database.pgvector_version'"
    assert "error" in db, "Missing 'database.error'"
    assert isinstance(db["connected"], bool), "'connected' must be a bool"


async def test_health_uptime_is_positive_number(client: AsyncClient) -> None:
    """Uptime must be a non-negative number."""
    response = await client.get("/health")
    uptime = response.json()["uptime_seconds"]
    assert isinstance(uptime, (int, float)), "uptime_seconds must be numeric"
    assert uptime >= 0, "uptime_seconds must be non-negative"
