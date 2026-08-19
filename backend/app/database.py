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
async def init_db_schema() -> None:
    """
    Idempotently initialize required database extensions, tables, and indexes.
    Runs on application startup.
    """
    schema_sql = """
    -- Ensure UUID generation and pgvector extensions are available
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 1. documents table
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        filename VARCHAR(255) NOT NULL,
        original_filename VARCHAR(255) NOT NULL,
        file_type VARCHAR(50) NOT NULL DEFAULT 'application/pdf',
        file_size BIGINT NOT NULL,
        file_path VARCHAR(512) NOT NULL,
        source VARCHAR(50) NOT NULL DEFAULT 'upload',
        processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
        error_message TEXT,
        page_count INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- 2. document_chunks table
    CREATE TABLE IF NOT EXISTS document_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        page_number INTEGER,
        character_count INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_document_chunk_index UNIQUE (document_id, chunk_index)
    );

    -- 3. Milestone 1B.1: Vector column and embedding metadata
    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(384);
    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100);
    ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;

    -- 4. Indexes
    CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
    CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_document_chunks_page ON document_chunks(document_id, page_number);

    -- 5. HNSW Vector Index for Cosine Similarity (<=> operator)
    CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(schema_sql)
