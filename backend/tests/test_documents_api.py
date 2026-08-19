"""
Tests — Document API Endpoints
===============================
Integration tests for:
- POST /documents/upload
- GET /documents
- GET /documents/{id}
- DELETE /documents/{id}
- File & cascading DB cleanup
"""

import io
import uuid
import pytest
from pathlib import Path
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.main import app
from app.database import create_pool, set_pool, clear_pool, init_db_schema
from app.services import document_repository, storage_service


def _make_pdf_bytes(pages: list[str]) -> bytes:
    """Helper to generate a valid PDF in memory."""
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=300, height=300)
        content = f"BT /F1 12 Tf 50 250 Td ({text}) Tj ET"
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin1", errors="replace"))
        page[NameObject("/Contents")] = stream

        fonts = DictionaryObject()
        font_f1 = DictionaryObject()
        font_f1[NameObject("/Type")] = NameObject("/Font")
        font_f1[NameObject("/Subtype")] = NameObject("/Type1")
        font_f1[NameObject("/BaseFont")] = NameObject("/Helvetica")
        fonts[NameObject("/F1")] = font_f1

        resources = DictionaryObject()
        resources[NameObject("/Font")] = fonts
        page[NameObject("/Resources")] = resources

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture(autouse=True)
async def setup_db_pool():
    """Ensure database pool and schema are initialized for tests."""
    pool = await create_pool()
    set_pool(pool)
    await init_db_schema()
    yield
    await pool.close()
    clear_pool()


@pytest.fixture
async def client():
    """Provide an async HTTP client wired directly to the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac


async def test_reject_non_pdf_file(client: AsyncClient):
    """Uploading a non-PDF file should be rejected with 400 Bad Request."""
    files = {
        "file": ("notes.txt", b"Plain text content", "text/plain")
    }
    response = await client.post("/documents/upload", files=files)
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


async def test_upload_valid_pdf_and_inspect_chunks(client: AsyncClient):
    """Uploading a valid multi-page PDF extracts text, creates chunks, and persists in DB."""
    pdf_bytes = _make_pdf_bytes([
        "KnowledgeHub architecture overview and goals.",
        "Detailed vector database design using PostgreSQL.",
    ])

    files = {
        "file": ("test_doc.pdf", pdf_bytes, "application/pdf")
    }

    # 1. Upload
    response = await client.post("/documents/upload", files=files)
    assert response.status_code == 201, f"Upload failed: {response.text}"

    upload_data = response.json()
    doc_id = upload_data["id"]
    assert upload_data["original_filename"] == "test_doc.pdf"
    assert upload_data["processing_status"] == "completed"
    assert upload_data["page_count"] == 2
    assert upload_data["chunk_count"] >= 2

    # 2. GET /documents
    list_response = await client.get("/documents")
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["total"] >= 1
    matching = [d for d in list_data["documents"] if d["id"] == doc_id]
    assert len(matching) == 1
    assert matching[0]["chunk_count"] == upload_data["chunk_count"]

    # 3. GET /documents/{id}
    detail_response = await client.get(f"/documents/{doc_id}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["id"] == doc_id
    assert len(detail_data["chunks"]) == upload_data["chunk_count"]

    # Verify chunk attributes
    first_chunk = detail_data["chunks"][0]
    assert first_chunk["chunk_index"] == 0
    assert first_chunk["page_number"] == 1
    assert "KnowledgeHub architecture" in first_chunk["content"]

    # 4. DELETE /documents/{id}
    delete_response = await client.delete(f"/documents/{doc_id}")
    assert delete_response.status_code == 200

    # 5. Verify deleted from DB and 404 on subsequent GET
    get_after_delete = await client.get(f"/documents/{doc_id}")
    assert get_after_delete.status_code == 404

    # Verify file is deleted from disk
    stored_path = Path(detail_data["file_path"])
    assert not stored_path.exists(), "Uploaded file should have been deleted from disk."


async def test_get_document_not_found(client: AsyncClient):
    """GET /documents/{random_uuid} returns 404."""
    random_id = str(uuid.uuid4())
    response = await client.get(f"/documents/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_delete_document_not_found(client: AsyncClient):
    """DELETE /documents/{random_uuid} returns 404."""
    random_id = str(uuid.uuid4())
    response = await client.delete(f"/documents/{random_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
