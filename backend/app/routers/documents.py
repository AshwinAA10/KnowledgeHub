"""
KnowledgeHub — Document Routes
===============================
Endpoints for uploading, listing, retrieving, and deleting documents.
"""

from uuid import UUID
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.config import settings
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services import (
    chunking_service,
    document_repository,
    pdf_service,
    storage_service,
)
from app.services.pdf_service import PDFExtractionError

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
) -> DocumentUploadResponse:
    """
    Upload a PDF document.

    Pipeline:
    1. Validate file extension and MIME type
    2. Stream file to disk (backend/uploads/)
    3. Insert initial document record (status: processing)
    4. Extract text page-by-page (pypdf)
    5. Deterministically chunk text
    6. Batch insert chunks into PostgreSQL
    7. Mark document completed
    """
    # 1. Validation
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files (.pdf) are supported.",
        )

    # 2. Save file to disk
    stored_filename, file_path, file_size = await storage_service.save_uploaded_file(file)

    # 3. Create document record in DB
    try:
        doc_record = await document_repository.create_document(
            filename=stored_filename,
            original_filename=filename,
            file_type="application/pdf",
            file_size=file_size,
            file_path=file_path,
            source="upload",
            processing_status="processing",
        )
    except Exception as exc:
        storage_service.delete_file(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record document metadata in database: {exc}",
        ) from exc

    doc_id = doc_record["id"]

    # 4. Extract text per page
    try:
        extraction_result = pdf_service.extract_text_from_pdf(file_path)
    except PDFExtractionError as exc:
        await document_repository.update_document_status(
            document_id=doc_id,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF extraction failed: {exc}",
        ) from exc
    except Exception as exc:
        await document_repository.update_document_status(
            document_id=doc_id,
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during PDF processing: {exc}",
        ) from exc

    # 5. Chunk text
    chunks = chunking_service.chunk_extracted_pages(
        pages=extraction_result.pages,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # 6. Persist chunks
    chunk_count = 0
    if chunks:
        try:
            chunk_count = await document_repository.insert_chunks(
                document_id=doc_id,
                chunks=chunks,
            )
        except Exception as exc:
            await document_repository.update_document_status(
                document_id=doc_id,
                status="failed",
                error_message=f"Failed to save document chunks: {exc}",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist chunks in database: {exc}",
            ) from exc

    # 7. Mark completed
    final_status = "completed"
    error_msg = None
    if not extraction_result.has_extractable_text:
        error_msg = "PDF contains no extractable text (it may be image-only or scanned)."

    await document_repository.update_document_status(
        document_id=doc_id,
        status=final_status,
        error_message=error_msg,
        page_count=extraction_result.page_count,
    )

    return DocumentUploadResponse(
        id=doc_id,
        filename=stored_filename,
        original_filename=filename,
        file_size=file_size,
        processing_status=final_status,
        page_count=extraction_result.page_count,
        chunk_count=chunk_count,
        created_at=doc_record["created_at"],
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
)
async def list_documents(
    limit: int = Query(default=50, ge=1, le=100, description="Max documents to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> DocumentListResponse:
    """
    Return a paginated list of documents with metadata and chunk counts.
    """
    docs, total = await document_repository.get_documents(limit=limit, offset=offset)
    return DocumentListResponse(total=total, documents=docs)


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details and chunks",
)
async def get_document(document_id: UUID) -> DocumentDetailResponse:
    """
    Retrieve full document details and its extracted chunks by ID.
    """
    doc = await document_repository.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found.",
        )
    return DocumentDetailResponse(**doc)


@router.delete(
    "/{document_id}",
    summary="Delete a document",
)
async def delete_document(document_id: UUID) -> dict[str, str]:
    """
    Delete a document from database and disk.
    Cascades to all associated chunks automatically.
    """
    deleted = await document_repository.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' was not found.",
        )

    # Remove the physical file on disk
    storage_service.delete_file(deleted["file_path"])

    return {
        "message": "Document deleted successfully",
        "id": str(document_id),
    }
