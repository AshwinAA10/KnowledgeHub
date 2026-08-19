"""
KnowledgeHub — Document Repository
==================================
Direct raw asyncpg SQL queries for Document and DocumentChunk records.
Handles atomic transactions, batch insertions, and cascading deletes.
"""

from typing import Any
import uuid
from app.database import get_pool
from app.services.chunking_service import DocumentChunkItem


async def create_document(
    filename: str,
    original_filename: str,
    file_type: str,
    file_size: int,
    file_path: str,
    source: str = "upload",
    processing_status: str = "pending",
    page_count: int | None = None,
) -> dict[str, Any]:
    """
    Insert a new document record.
    """
    query = """
    INSERT INTO documents (
        filename,
        original_filename,
        file_type,
        file_size,
        file_path,
        source,
        processing_status,
        page_count
    )
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    RETURNING
        id,
        filename,
        original_filename,
        file_type,
        file_size,
        file_path,
        source,
        processing_status,
        error_message,
        page_count,
        created_at,
        updated_at;
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            query,
            filename,
            original_filename,
            file_type,
            file_size,
            file_path,
            source,
            processing_status,
            page_count,
        )
    return dict(row) if row else {}


async def insert_chunks(
    document_id: uuid.UUID | str,
    chunks: list[DocumentChunkItem],
) -> int:
    """
    Batch insert document chunks.
    """
    if not chunks:
        return 0

    doc_uuid = uuid.UUID(str(document_id))
    pool = get_pool()

    records = [
        (
            doc_uuid,
            chunk.chunk_index,
            chunk.content,
            chunk.page_number,
            chunk.character_count,
        )
        for chunk in chunks
    ]

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(
                """
                INSERT INTO document_chunks (
                    document_id,
                    chunk_index,
                    content,
                    page_number,
                    character_count
                )
                VALUES ($1, $2, $3, $4, $5);
                """,
                records,
            )

    return len(records)


async def update_document_status(
    document_id: uuid.UUID | str,
    status: str,
    error_message: str | None = None,
    page_count: int | None = None,
) -> dict[str, Any] | None:
    """
    Update the processing status and error message of a document.
    """
    doc_uuid = uuid.UUID(str(document_id))
    pool = get_pool()

    query = """
    UPDATE documents
    SET
        processing_status = $2,
        error_message = $3,
        page_count = COALESCE($4, page_count),
        updated_at = NOW()
    WHERE id = $1
    RETURNING
        id,
        filename,
        original_filename,
        file_type,
        file_size,
        file_path,
        source,
        processing_status,
        error_message,
        page_count,
        created_at,
        updated_at;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, doc_uuid, status, error_message, page_count)
    return dict(row) if row else None


async def get_documents(
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Fetch paginated list of documents with aggregated chunk counts.

    Returns:
        tuple of (list_of_documents, total_count)
    """
    pool = get_pool()

    count_query = "SELECT COUNT(*) FROM documents;"

    query = """
    SELECT
        d.id,
        d.filename,
        d.original_filename,
        d.file_type,
        d.file_size,
        d.file_path,
        d.source,
        d.processing_status,
        d.error_message,
        d.page_count,
        COUNT(c.id)::int AS chunk_count,
        d.created_at,
        d.updated_at
    FROM documents d
    LEFT JOIN document_chunks c ON d.id = c.document_id
    GROUP BY d.id
    ORDER BY d.created_at DESC
    LIMIT $1 OFFSET $2;
    """

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query)
        rows = await conn.fetch(query, limit, offset)

    return [dict(r) for r in rows], total or 0


async def get_document_by_id(document_id: uuid.UUID | str) -> dict[str, Any] | None:
    """
    Fetch a single document and all of its chunks ordered by chunk_index.
    """
    try:
        doc_uuid = uuid.UUID(str(document_id))
    except (ValueError, TypeError):
        return None

    pool = get_pool()

    doc_query = """
    SELECT
        id,
        filename,
        original_filename,
        file_type,
        file_size,
        file_path,
        source,
        processing_status,
        error_message,
        page_count,
        created_at,
        updated_at
    FROM documents
    WHERE id = $1;
    """

    chunks_query = """
    SELECT
        id,
        document_id,
        chunk_index,
        content,
        page_number,
        character_count,
        created_at
    FROM document_chunks
    WHERE document_id = $1
    ORDER BY chunk_index ASC;
    """

    async with pool.acquire() as conn:
        doc_row = await conn.fetchrow(doc_query, doc_uuid)
        if not doc_row:
            return None

        chunk_rows = await conn.fetch(chunks_query, doc_uuid)

    doc_dict = dict(doc_row)
    doc_dict["chunks"] = [dict(c) for c in chunk_rows]
    doc_dict["chunk_count"] = len(chunk_rows)
    return doc_dict


async def delete_document(document_id: uuid.UUID | str) -> dict[str, Any] | None:
    """
    Delete a document by ID. Cascades to document_chunks automatically.
    Returns the deleted document row or None if not found.
    """
    try:
        doc_uuid = uuid.UUID(str(document_id))
    except (ValueError, TypeError):
        return None

    pool = get_pool()
    query = """
    DELETE FROM documents
    WHERE id = $1
    RETURNING
        id,
        filename,
        original_filename,
        file_path;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, doc_uuid)

    return dict(row) if row else None


async def get_chunks_for_embedding(
    document_id: uuid.UUID | str | None = None,
    force: bool = False,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """
    Fetch chunks that need embedding generation.

    Args:
        document_id: Optional document ID to filter chunks.
        force: If True, returns all chunks for document regardless of embedding status.
               If False, only returns chunks where embedding IS NULL.
        limit: Max number of chunks to return (for backfill).
    """
    pool = get_pool()

    if document_id is not None:
        doc_uuid = uuid.UUID(str(document_id))
        if force:
            query = """
            SELECT id, document_id, chunk_index, content, page_number
            FROM document_chunks
            WHERE document_id = $1
            ORDER BY chunk_index ASC;
            """
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, doc_uuid)
        else:
            query = """
            SELECT id, document_id, chunk_index, content, page_number
            FROM document_chunks
            WHERE document_id = $1 AND embedding IS NULL
            ORDER BY chunk_index ASC;
            """
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, doc_uuid)
    else:
        query = """
        SELECT id, document_id, chunk_index, content, page_number
        FROM document_chunks
        WHERE embedding IS NULL
        ORDER BY created_at ASC
        LIMIT $1;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, limit)

    return [dict(r) for r in rows]


async def update_chunk_embeddings(
    updates: list[tuple[uuid.UUID | str, list[float], str]],
) -> int:
    """
    Batch update embeddings for document chunks.

    Args:
        updates: List of (chunk_id, vector_floats, model_name).

    Returns:
        Number of updated chunk records.
    """
    if not updates:
        return 0

    pool = get_pool()

    # Format records for asyncpg: (chunk_uuid, vector_str, model_name)
    records = [
        (
            uuid.UUID(str(chunk_id)),
            f"[{','.join(f'{x:.8f}' for x in vec)}]",
            model_name,
        )
        for chunk_id, vec, model_name in updates
    ]

    query = """
    UPDATE document_chunks
    SET
        embedding = $2::vector,
        embedding_model = $3,
        embedded_at = NOW()
    WHERE id = $1;
    """

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(query, records)

    return len(records)


async def get_embedding_status() -> dict[str, Any]:
    """
    Get aggregated counts for embedding coverage across all document chunks.
    """
    pool = get_pool()
    query = """
    SELECT
        COUNT(*)::int AS total_chunks,
        COUNT(embedding)::int AS embedded_chunks,
        (COUNT(*) - COUNT(embedding))::int AS unembedded_chunks
    FROM document_chunks;
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query)

    return dict(row) if row else {
        "total_chunks": 0,
        "embedded_chunks": 0,
        "unembedded_chunks": 0,
    }


async def semantic_search(
    query_vector: list[float],
    top_k: int = 5,
    min_score: float = 0.0,
    document_id: uuid.UUID | str | None = None,
) -> list[dict[str, Any]]:
    """
    Perform semantic similarity search over document chunks using cosine distance (<=>).

    Args:
        query_vector: 384-dimensional dense float vector.
        top_k: Maximum number of results to return.
        min_score: Minimum similarity score threshold (1 - distance).
        document_id: Optional document ID to filter results.

    Returns:
        List of matched chunks with metadata, similarity_score, and distance.
    """
    pool = get_pool()
    vec_str = f"[{','.join(f'{x:.8f}' for x in query_vector)}]"

    if document_id is not None:
        doc_uuid = uuid.UUID(str(document_id))
        query = """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.filename,
            d.original_filename,
            c.chunk_index,
            c.page_number,
            c.content,
            (1 - (c.embedding <=> $1::vector))::float AS similarity_score,
            (c.embedding <=> $1::vector)::float AS distance
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
          AND (1 - (c.embedding <=> $1::vector)) >= $2
          AND c.document_id = $3
        ORDER BY c.embedding <=> $1::vector ASC
        LIMIT $4;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, vec_str, min_score, doc_uuid, top_k)
    else:
        query = """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.filename,
            d.original_filename,
            c.chunk_index,
            c.page_number,
            c.content,
            (1 - (c.embedding <=> $1::vector))::float AS similarity_score,
            (c.embedding <=> $1::vector)::float AS distance
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.embedding IS NOT NULL
          AND (1 - (c.embedding <=> $1::vector)) >= $2
        ORDER BY c.embedding <=> $1::vector ASC
        LIMIT $3;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, vec_str, min_score, top_k)

    return [dict(r) for r in rows]
