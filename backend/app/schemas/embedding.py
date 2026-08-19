"""
KnowledgeHub — Embedding Schemas
=================================
Pydantic schemas for embedding operations and status responses.
"""

from uuid import UUID
from pydantic import BaseModel, ConfigDict


class DocumentEmbedResponse(BaseModel):
    """Response returned when embedding chunks for a specific document."""
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    total_chunks: int
    embedded_count: int
    skipped_count: int
    model: str
    dimensions: int


class BackfillResponse(BaseModel):
    """Response returned when running a batch embedding backfill."""
    model_config = ConfigDict(from_attributes=True)

    processed_count: int
    remaining_unembedded_count: int
    model: str
    dimensions: int


class EmbeddingStatusResponse(BaseModel):
    """Response reporting overall embedding coverage across the knowledge base."""
    model_config = ConfigDict(from_attributes=True)

    active_model: str
    dimensions: int
    batch_size: int
    total_chunks: int
    embedded_chunks: int
    unembedded_chunks: int
