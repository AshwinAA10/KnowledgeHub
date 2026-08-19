"""
KnowledgeHub — Embedding Routes
================================
Endpoints for triggering chunk embedding, batch backfilling,
and checking vector index coverage.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.schemas.embedding import (
    BackfillResponse,
    DocumentEmbedResponse,
    EmbeddingStatusResponse,
)
from app.services import document_repository, embedding_service
from app.services.embedding_service import EmbeddingServiceError

router = APIRouter(tags=["Embeddings"])


@router.post(
    "/documents/{document_id}/embed",
    response_model=DocumentEmbedResponse,
    summary="Generate embeddings for a document's chunks",
)
async def embed_document_chunks(
    document_id: UUID,
    force: bool = Query(
        default=False,
        description="If True, re-embeds all chunks even if already embedded. If False, only embeds chunks with NULL embeddings.",
    ),
) -> DocumentEmbedResponse:
    """
    Generate and store vector embeddings for chunks of a specific document.
    """
    # 1. Verify document exists
    doc = await document_repository.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found.",
        )

    all_chunks = doc.get("chunks", [])
    total_chunks = len(all_chunks)

    if total_chunks == 0:
        return DocumentEmbedResponse(
            document_id=document_id,
            total_chunks=0,
            embedded_count=0,
            skipped_count=0,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    # 2. Filter chunks that need embedding
    chunks_to_embed = await document_repository.get_chunks_for_embedding(
        document_id=document_id,
        force=force,
    )

    if not chunks_to_embed:
        # All chunks are already embedded and force is False
        return DocumentEmbedResponse(
            document_id=document_id,
            total_chunks=total_chunks,
            embedded_count=0,
            skipped_count=total_chunks,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    # 3. Generate embeddings
    texts = [c["content"] for c in chunks_to_embed]
    try:
        vectors = embedding_service.embed_batch(texts)
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {exc}",
        ) from exc

    # 4. Batch persist to PostgreSQL
    updates = [
        (c["id"], vectors[idx], settings.embedding_model)
        for idx, c in enumerate(chunks_to_embed)
    ]
    try:
        updated_count = await document_repository.update_chunk_embeddings(updates)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist vector embeddings to database: {exc}",
        ) from exc

    skipped_count = total_chunks - updated_count

    return DocumentEmbedResponse(
        document_id=document_id,
        total_chunks=total_chunks,
        embedded_count=updated_count,
        skipped_count=skipped_count,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


@router.post(
    "/embeddings/backfill",
    response_model=BackfillResponse,
    summary="Batch generate embeddings for all unembedded chunks",
)
async def backfill_embeddings(
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
        description="Max number of unembedded chunks to process in this run",
    ),
) -> BackfillResponse:
    """
    Find chunks across all documents where embedding IS NULL,
    generate embeddings in batches, and update PostgreSQL.
    """
    # 1. Fetch chunks with NULL embeddings
    chunks_to_embed = await document_repository.get_chunks_for_embedding(
        document_id=None,
        force=False,
        limit=limit,
    )

    if not chunks_to_embed:
        status_info = await document_repository.get_embedding_status()
        return BackfillResponse(
            processed_count=0,
            remaining_unembedded_count=status_info["unembedded_chunks"],
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    # 2. Generate embeddings
    texts = [c["content"] for c in chunks_to_embed]
    try:
        vectors = embedding_service.embed_batch(texts)
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {exc}",
        ) from exc

    # 3. Batch persist updates
    updates = [
        (c["id"], vectors[idx], settings.embedding_model)
        for idx, c in enumerate(chunks_to_embed)
    ]
    try:
        processed_count = await document_repository.update_chunk_embeddings(updates)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist vector embeddings to database: {exc}",
        ) from exc

    status_info = await document_repository.get_embedding_status()

    return BackfillResponse(
        processed_count=processed_count,
        remaining_unembedded_count=status_info["unembedded_chunks"],
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
    )


@router.get(
    "/embeddings/status",
    response_model=EmbeddingStatusResponse,
    summary="Get embedding coverage statistics",
)
async def get_embedding_status() -> EmbeddingStatusResponse:
    """
    Return active embedding model info and total / embedded chunk counts.
    """
    status_info = await document_repository.get_embedding_status()
    return EmbeddingStatusResponse(
        active_model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
        total_chunks=status_info["total_chunks"],
        embedded_chunks=status_info["embedded_chunks"],
        unembedded_chunks=status_info["unembedded_chunks"],
    )
