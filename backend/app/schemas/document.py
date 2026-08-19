"""
KnowledgeHub — Document Schemas
================================
Pydantic response models for Document and Chunk endpoints.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ChunkResponse(BaseModel):
    """Pydantic model representing a single document chunk."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int | None
    character_count: int
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response returned upon initiating / completing document upload."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_size: int
    processing_status: str
    page_count: int | None
    chunk_count: int
    created_at: datetime


class DocumentListItem(BaseModel):
    """Summary representation of a document for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    processing_status: str
    error_message: str | None = None
    page_count: int | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list response for documents."""
    total: int
    documents: list[DocumentListItem]


class DocumentDetailResponse(BaseModel):
    """Full document details including its list of chunks."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    file_path: str
    source: str
    processing_status: str
    error_message: str | None = None
    page_count: int | None = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime
    chunks: list[ChunkResponse] = []
