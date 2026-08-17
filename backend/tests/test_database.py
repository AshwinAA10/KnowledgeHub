"""
Tests — Database Connectivity
==============================
Verifies that:
  1. A connection to PostgreSQL can be established.
  2. The pgvector extension is installed and its version is reported.

These tests require Docker Compose to be running:
  docker compose up -d

If the database is unreachable, tests are skipped with a clear message
rather than failing with a cryptic error.
"""

import pytest
import asyncpg

from app.config import settings
from app.database import check_database_connectivity


async def _can_reach_database() -> bool:
    """Quick probe: return True if a single connection succeeds."""
    try:
        conn = await asyncpg.connect(dsn=settings.database_url, timeout=3)
        await conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_connection():
    """
    Open a direct asyncpg connection for use in tests.
    Skips all tests that depend on this fixture if the DB is unreachable.
    """
    if not await _can_reach_database():
        pytest.skip(
            "Database is not reachable. "
            "Start it with: docker compose up -d"
        )
    conn = await asyncpg.connect(dsn=settings.database_url, timeout=5)
    yield conn
    await conn.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_postgres_connection(db_connection: asyncpg.Connection) -> None:
    """A raw query must succeed, confirming basic PostgreSQL connectivity."""
    result = await db_connection.fetchval("SELECT 1")
    assert result == 1, f"Expected 1 from 'SELECT 1', got {result!r}"


async def test_postgres_version_readable(db_connection: asyncpg.Connection) -> None:
    """PostgreSQL version string must be readable and non-empty."""
    version = await db_connection.fetchval("SELECT version()")
    assert version is not None, "version() returned None"
    assert "PostgreSQL" in version, f"Unexpected version string: {version!r}"


async def test_pgvector_extension_enabled(db_connection: asyncpg.Connection) -> None:
    """
    pgvector must be installed as a PostgreSQL extension.
    If this fails, check that the init SQL ran:
      docker compose logs db | grep pgvector
    """
    pgvector_version = await db_connection.fetchval(
        "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
    )
    assert pgvector_version is not None, (
        "pgvector extension is NOT installed. "
        "The init SQL may not have run. Try: docker compose down -v && docker compose up -d"
    )
    print(f"\n   ✅ pgvector version: {pgvector_version}")


async def test_check_database_connectivity_helper_connected() -> None:
    """
    The check_database_connectivity() helper (used by /health) must return
    a connected=True result when the DB is running.

    This test initialises a temporary pool rather than relying on the app
    lifespan so it runs independently.
    """
    if not await _can_reach_database():
        pytest.skip("Database is not reachable. Start it with: docker compose up -d")

    import app.database as db_module  # noqa: PLC0415

    # Temporarily set a pool for the helper
    pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=1, max_size=2)
    original_pool = db_module._pool
    db_module._pool = pool

    try:
        result = await check_database_connectivity()
    finally:
        db_module._pool = original_pool
        await pool.close()

    assert result["connected"] is True, f"Expected connected=True, got: {result}"
    assert result["error"] is None, f"Expected no error, got: {result['error']}"
    assert result["pgvector_version"] not in (None, "not installed"), (
        f"pgvector not available: {result['pgvector_version']}"
    )


async def test_check_database_connectivity_helper_disconnected() -> None:
    """
    check_database_connectivity() must gracefully return connected=False
    (not raise) when the database pool contains a bad connection.
    """
    import app.database as db_module  # noqa: PLC0415

    # Point to a non-existent database to force failure
    bad_pool = None
    try:
        bad_pool = await asyncpg.create_pool(
            dsn="postgresql://invalid:invalid@localhost:19999/nonexistent",
            min_size=1,
            max_size=1,
            timeout=2,
        )
    except Exception:  # noqa: BLE001
        pass  # Pool creation itself may fail — that's fine for this test

    original_pool = db_module._pool
    db_module._pool = bad_pool  # May be None if creation failed

    try:
        result = await check_database_connectivity()
    finally:
        db_module._pool = original_pool
        if bad_pool is not None:
            await bad_pool.close()

    assert result["connected"] is False, (
        f"Expected connected=False on bad connection, got: {result}"
    )
    assert result["error"] is not None, "Expected an error message for bad connection"
