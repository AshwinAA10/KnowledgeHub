-- =============================================================================
-- KnowledgeHub — Add Embeddings to Document Chunks
-- Milestone 1B.1: Embedding Generation + Vector Storage
-- =============================================================================

-- 1. Add vector column (384 dimensions for BAAI/bge-small-en-v1.5)
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(384);

-- 2. Add metadata columns for model tracking and re-indexing
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(100);
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ;

-- 3. HNSW Vector Index for Cosine Similarity (<=> operator)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops);
