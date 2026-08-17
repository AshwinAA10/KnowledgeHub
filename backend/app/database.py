"""
KnowledgeHub — Database Layer
==============================
Manages an asyncpg connection pool and exposes helper functions used
by the application and tests.

Design decisions:
- asyncpg is used directly (no ORM, no SQLAlchemy) for explicitness.
- A single global pool is created at startup and closed at shutdown.
- Connection failures surface clearly rather than being swallowed.
"""

import asyncpg
from asyncpg import Pool

from app.config import settings

# Module-level pool reference — populated by lifespan() in main.py
_pool: Pool | None = None


async def create_pool() -> Pool:
    """
    Create and return an asyncpg connection pool.
    Raises asyncpg.PostgresError or OSError on connection failure.
    """
    pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        # Fail fast if the database is unreachable at startup
        timeout=10,
        command_timeout=30,
    )
    return pool


async def close_pool(pool: Pool) -> None:
    """Gracefully close all connections in the pool."""
    await pool.close()


def get_pool() -> Pool:
    """
    Return the active connection pool.
    Raises RuntimeError if called before the pool is initialized.
    """
    if _pool is None:
        raise RuntimeError(
            "Database pool is not initialized. "
            "Ensure the application lifespan has started."
        )
    return _pool


def set_pool(pool: Pool) -> None:
    """Store the pool reference (called from lifespan startup)."""
    global _pool
    _pool = pool


def clear_pool() -> None:
    """Clear the pool reference (called from lifespan shutdown)."""
    global _pool
    _pool = None


async def check_database_connectivity() -> dict:
    """
    Run a lightweight connectivity check.

    Returns a dict with:
      - connected (bool)
      - postgres_version (str)
      - pgvector_version (str)
      - error (str | None)

    Never raises — always returns a structured result so the /health
    endpoint can safely include database status.
    """
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    version()                                          AS pg_version,
                    (SELECT extversion FROM pg_extension
                     WHERE extname = 'vector')                        AS pgvector_version
                """
            )
        return {
            "connected": True,
            "postgres_version": row["pg_version"],
            "pgvector_version": row["pgvector_version"] or "not installed",
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "connected": False,
            "postgres_version": None,
            "pgvector_version": None,
            "error": str(exc),
        }
