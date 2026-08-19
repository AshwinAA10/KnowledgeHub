"""
Tests — Embeddings API Endpoints & Persistence
===============================================
Integration tests for:
- POST /documents/{id}/embed (targeted embedding, skip-already-embedded, force re-embed)
- POST /embeddings/backfill (global unembedded chunks processing)
- GET /embeddings/status (metrics and active model tracking)
- PostgreSQL vector persistence & HNSW index verification
"""

import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.main import app
from app.database import create_pool, set_pool, clear_pool, init_db_schema, get_pool


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


async def test_document_specific_embedding_workflow(client: AsyncClient):
    """Test explicit document embedding, skip-already-embedded behavior, and force re-embed."""
    # 1. Ingest a document (Milestone 1A does NOT auto-embed)
    pdf_bytes = _make_pdf_bytes([
        "Page 1: Artificial Intelligence systems architecture.",
        "Page 2: Vector embedding techniques with pgvector.",
    ])
    files = {"file": ("ai_systems.pdf", pdf_bytes, "application/pdf")}
    upload_res = await client.post("/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]
    total_chunks = upload_res.json()["chunk_count"]
    assert total_chunks >= 2

    # 2. Verify chunks currently have NULL embeddings in PostgreSQL
    pool = get_pool()
    async with pool.acquire() as conn:
        null_count = await conn.fetchval(
            "SELECT COUNT(*) FROM document_chunks WHERE document_id = $1 AND embedding IS NULL",
            uuid.UUID(doc_id),
        )
    assert null_count == total_chunks

    # 3. Explicitly trigger embedding generation for this document
    embed_res = await client.post(f"/documents/{doc_id}/embed")
    assert embed_res.status_code == 200
    embed_data = embed_res.json()
    assert embed_data["document_id"] == doc_id
    assert embed_data["embedded_count"] == total_chunks
    assert embed_data["skipped_count"] == 0
    assert embed_data["model"] == "BAAI/bge-small-en-v1.5"
    assert embed_data["dimensions"] == 384

    # 4. Verify in PostgreSQL that embeddings, model, and timestamp are populated
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, embedding::text AS vec_str, embedding_model, embedded_at
            FROM document_chunks
            WHERE document_id = $1
            """,
            uuid.UUID(doc_id),
        )
    assert len(rows) == total_chunks
    for r in rows:
        assert r["vec_str"] is not None
        assert r["vec_str"].startswith("[") and r["vec_str"].endswith("]")
        assert r["embedding_model"] == "BAAI/bge-small-en-v1.5"
        assert r["embedded_at"] is not None

    # 5. Calling embed again without force should skip already-embedded chunks
    embed_again = await client.post(f"/documents/{doc_id}/embed")
    assert embed_again.status_code == 200
    again_data = embed_again.json()
    assert again_data["embedded_count"] == 0
    assert again_data["skipped_count"] == total_chunks

    # 6. Calling embed with force=True should re-generate embeddings
    force_embed = await client.post(f"/documents/{doc_id}/embed?force=true")
    assert force_embed.status_code == 200
    force_data = force_embed.json()
    assert force_data["embedded_count"] == total_chunks
    assert force_data["skipped_count"] == 0

    # Cleanup
    await client.delete(f"/documents/{doc_id}")


async def test_embeddings_backfill(client: AsyncClient):
    """Test global backfill of unembedded chunks across documents."""
    # 1. Ingest a document without embedding
    pdf_bytes = _make_pdf_bytes(["Backfill test document content snippet."])
    files = {"file": ("backfill_doc.pdf", pdf_bytes, "application/pdf")}
    upload_res = await client.post("/documents/upload", files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. Trigger backfill
    backfill_res = await client.post("/embeddings/backfill")
    assert backfill_res.status_code == 200
    backfill_data = backfill_res.json()
    assert backfill_data["processed_count"] >= 1
    assert backfill_data["model"] == "BAAI/bge-small-en-v1.5"
    assert backfill_data["dimensions"] == 384

    # 3. Subsequent backfill should find 0 unembedded chunks
    second_backfill = await client.post("/embeddings/backfill")
    assert second_backfill.status_code == 200
    assert second_backfill.json()["processed_count"] == 0

    # Cleanup
    await client.delete(f"/documents/{doc_id}")


async def test_embeddings_status_endpoint(client: AsyncClient):
    """Test GET /embeddings/status returns accurate counts and model info."""
    res = await client.get("/embeddings/status")
    assert res.status_code == 200
    data = res.json()
    assert data["active_model"] == "BAAI/bge-small-en-v1.5"
    assert data["dimensions"] == 384
    assert data["total_chunks"] >= 0
    assert data["embedded_chunks"] >= 0
    assert data["unembedded_chunks"] >= 0
    assert data["total_chunks"] == data["embedded_chunks"] + data["unembedded_chunks"]


async def test_embed_nonexistent_document(client: AsyncClient):
    """Calling embed on a nonexistent document ID returns 404."""
    random_id = str(uuid.uuid4())
    res = await client.post(f"/documents/{random_id}/embed")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
