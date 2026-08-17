-- =============================================================================
-- KnowledgeHub — Database Initialization
-- Runs automatically on first container start via docker-entrypoint-initdb.d
-- =============================================================================

-- Enable the pgvector extension so vector operations are available.
-- This is a one-time setup; subsequent container starts skip already-run scripts.
CREATE EXTENSION IF NOT EXISTS vector;

-- Confirm both PostgreSQL and pgvector are ready.
-- This output is visible in `docker compose logs db` during startup.
DO $$
BEGIN
    RAISE NOTICE 'pgvector extension enabled. Version: %', (SELECT extversion FROM pg_extension WHERE extname = 'vector');
END $$;
