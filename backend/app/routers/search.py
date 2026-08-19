"""
KnowledgeHub — Search Routes
============================
Endpoints for vector-based semantic retrieval over document chunks.
"""

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.search import (
    SearchResultItem,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.services import document_repository, embedding_service
from app.services.embedding_service import EmbeddingServiceError

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    summary="Semantic vector search over document chunks",
)
async def semantic_search(
    request: SemanticSearchRequest,
) -> SemanticSearchResponse:
    """
    Perform dense vector search against embedded document chunks:
    1. Embeds the user query using the same embedding model (BAAI/bge-small-en-v1.5).
    2. Performs cosine distance query (<=>) in pgvector with HNSW indexing.
    3. Returns top_k chunks ordered by highest cosine similarity (1 - distance).
    """
    # 1. Generate query embedding vector (384 dimensions)
    try:
        query_vector = embedding_service.embed_text(request.query)
    except EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query embedding generation failed: {exc}",
        ) from exc

    # 2. Query PostgreSQL with pgvector cosine distance
    try:
        raw_results = await document_repository.semantic_search(
            query_vector=query_vector,
            top_k=request.top_k,
            min_score=request.min_score,
            document_id=request.document_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search database query failed: {exc}",
        ) from exc

    # 3. Format response items
    items = [SearchResultItem(**row) for row in raw_results]

    return SemanticSearchResponse(
        query=request.query,
        embedding_model=settings.embedding_model,
        total_results=len(items),
        results=items,
    )
