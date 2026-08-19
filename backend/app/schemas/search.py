"""
KnowledgeHub — Semantic Search Schemas
======================================
Pydantic models for semantic vector search requests and responses.
"""

from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SemanticSearchRequest(BaseModel):
    """Payload for POST /search/semantic."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Search query in natural language",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of relevant chunks to return",
    )
    document_id: UUID | None = Field(
        default=None,
        description="Optional filter to restrict search to chunks of a specific document",
    )
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold (1 - distance)",
    )

    @field_validator("query")
    @classmethod
    def validate_query_not_whitespace(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Query string must not be empty or whitespace only.")
        return trimmed


class SearchResultItem(BaseModel):
    """A single retrieved chunk match with similarity scores and document metadata."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID
    document_id: UUID
    filename: str
    original_filename: str
    chunk_index: int
    page_number: int | None
    content: str
    similarity_score: float
    distance: float


class SemanticSearchResponse(BaseModel):
    """Response returned from semantic vector search."""
    model_config = ConfigDict(from_attributes=True)

    query: str
    embedding_model: str
    total_results: int
    results: list[SearchResultItem]
