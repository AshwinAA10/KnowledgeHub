"""
Tests — Semantic Search API Endpoints & Retrieval Quality
==========================================================
Integration tests for:
- POST /search/semantic
- Semantic relevance ranking
- Top-K bounding and pagination limits
- Document ID filtering
- Minimum similarity score filtering (min_score)
- Empty / whitespace query validation (422)
- Metadata preservation (filename, chunk_index, page_number, similarity, distance)
- Cosine similarity + distance mathematical consistency
"""

import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.main import app
from app.database import create_pool, set_pool, clear_pool, init_db_schema


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


async def test_semantic_ranking_relevance(client: AsyncClient):
    """
    Verify that semantically related chunks rank higher than unrelated chunks.
    """
    # 1. Ingest AI/ML document
    ai_pdf = _make_pdf_bytes([
        "Artificial intelligence systems utilize neural networks and backpropagation for gradient optimization.",
    ])
    ai_up = await client.post(
        "/documents/upload",
        files={"file": ("ai_research.pdf", ai_pdf, "application/pdf")},
    )
    assert ai_up.status_code == 201
    ai_doc_id = ai_up.json()["id"]

    # 2. Ingest Cooking/Culinary document
    cook_pdf = _make_pdf_bytes([
        "Traditional Neapolitan pizza requires finely milled wheat flour, San Marzano tomatoes, and mozzarella.",
    ])
    cook_up = await client.post(
        "/documents/upload",
        files={"file": ("italian_cooking.pdf", cook_pdf, "application/pdf")},
    )
    assert cook_up.status_code == 201
    cook_doc_id = cook_up.json()["id"]

    # 3. Embed both documents
    await client.post(f"/documents/{ai_doc_id}/embed")
    await client.post(f"/documents/{cook_doc_id}/embed")

    # 4. Search for AI concept
    ai_query_res = await client.post(
        "/search/semantic",
        json={"query": "deep learning architectures and neural network training", "top_k": 5},
    )
    assert ai_query_res.status_code == 200
    ai_data = ai_query_res.json()
    assert ai_data["total_results"] >= 2
    assert ai_data["results"][0]["document_id"] == ai_doc_id
    assert ai_data["results"][0]["similarity_score"] > ai_data["results"][1]["similarity_score"]

    # 5. Search for Recipe concept
    cook_query_res = await client.post(
        "/search/semantic",
        json={"query": "how to prepare classic pizza dough and tomato sauce", "top_k": 5},
    )
    assert cook_query_res.status_code == 200
    cook_data = cook_query_res.json()
    assert cook_data["total_results"] >= 2
    assert cook_data["results"][0]["document_id"] == cook_doc_id
    assert cook_data["results"][0]["similarity_score"] > cook_data["results"][1]["similarity_score"]

    # Cleanup
    await client.delete(f"/documents/{ai_doc_id}")
    await client.delete(f"/documents/{cook_doc_id}")


async def test_top_k_bounds_and_limit(client: AsyncClient):
    """Verify top_k bounds validation and that top_k restricts result count."""
    # Ingest document with multiple pages/chunks
    pdf = _make_pdf_bytes([
        "Section 1: Operating systems concepts and memory management.",
        "Section 2: File system architecture and inodes.",
        "Section 3: Distributed consensus algorithms and Raft protocol.",
    ])
    up = await client.post(
        "/documents/upload",
        files={"file": ("os_notes.pdf", pdf, "application/pdf")},
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]
    await client.post(f"/documents/{doc_id}/embed")

    # top_k = 1
    res1 = await client.post(
        "/search/semantic",
        json={"query": "computer systems architecture", "top_k": 1},
    )
    assert res1.status_code == 200
    assert len(res1.json()["results"]) == 1

    # top_k = 2
    res2 = await client.post(
        "/search/semantic",
        json={"query": "computer systems architecture", "top_k": 2},
    )
    assert res2.status_code == 200
    assert len(res2.json()["results"]) == 2

    # Validation: top_k < 1 -> 422
    res_zero = await client.post(
        "/search/semantic",
        json={"query": "computer systems", "top_k": 0},
    )
    assert res_zero.status_code == 422

    # Validation: top_k > 50 -> 422
    res_high = await client.post(
        "/search/semantic",
        json={"query": "computer systems", "top_k": 51},
    )
    assert res_high.status_code == 422

    # Cleanup
    await client.delete(f"/documents/{doc_id}")


async def test_document_id_filtering(client: AsyncClient):
    """Filtering by document_id must only return chunks from that specific document."""
    pdf1 = _make_pdf_bytes(["Database indexing strategies using B-trees and LSM-trees."])
    up1 = await client.post("/documents/upload", files={"file": ("db1.pdf", pdf1, "application/pdf")})
    doc1_id = up1.json()["id"]
    await client.post(f"/documents/{doc1_id}/embed")

    pdf2 = _make_pdf_bytes(["Database replication, sharding and high availability."])
    up2 = await client.post("/documents/upload", files={"file": ("db2.pdf", pdf2, "application/pdf")})
    doc2_id = up2.json()["id"]
    await client.post(f"/documents/{doc2_id}/embed")

    # Search with document_id filter for doc1
    res = await client.post(
        "/search/semantic",
        json={"query": "database architectures", "top_k": 10, "document_id": doc1_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_results"] > 0
    assert all(r["document_id"] == doc1_id for r in data["results"])

    # Search with nonexistent document_id returns empty results
    random_doc_id = str(uuid.uuid4())
    res_empty = await client.post(
        "/search/semantic",
        json={"query": "database architectures", "top_k": 10, "document_id": random_doc_id},
    )
    assert res_empty.status_code == 200
    assert res_empty.json()["total_results"] == 0

    # Cleanup
    await client.delete(f"/documents/{doc1_id}")
    await client.delete(f"/documents/{doc2_id}")


async def test_min_score_filtering(client: AsyncClient):
    """min_score threshold excludes results with lower similarity scores."""
    pdf = _make_pdf_bytes(["PostgreSQL pgvector extension for high-performance vector search."])
    up = await client.post("/documents/upload", files={"file": ("pgvector.pdf", pdf, "application/pdf")})
    doc_id = up.json()["id"]
    await client.post(f"/documents/{doc_id}/embed")

    # High min_score (e.g. 0.999) filters out non-identical matches
    strict_res = await client.post(
        "/search/semantic",
        json={"query": "quantum gravity theoretical physics", "min_score": 0.99},
    )
    assert strict_res.status_code == 200
    assert strict_res.json()["total_results"] == 0

    # Permissive min_score (e.g. 0.0) includes matches
    permissive_res = await client.post(
        "/search/semantic",
        json={"query": "pgvector search", "min_score": 0.0},
    )
    assert permissive_res.status_code == 200
    assert permissive_res.json()["total_results"] >= 1
    assert permissive_res.json()["results"][0]["similarity_score"] >= 0.0

    # Validation: min_score out of bounds -> 422
    assert (await client.post("/search/semantic", json={"query": "test", "min_score": -0.1})).status_code == 422
    assert (await client.post("/search/semantic", json={"query": "test", "min_score": 1.1})).status_code == 422

    # Cleanup
    await client.delete(f"/documents/{doc_id}")


async def test_empty_and_whitespace_query_validation(client: AsyncClient):
    """Empty or whitespace-only queries must return HTTP 422 Unprocessable Entity."""
    # Empty string
    res_empty = await client.post("/search/semantic", json={"query": ""})
    assert res_empty.status_code == 422

    # Whitespace-only string
    res_ws = await client.post("/search/semantic", json={"query": "   \n\t  "})
    assert res_ws.status_code == 422


async def test_metadata_and_score_consistency(client: AsyncClient):
    """Verify all expected metadata fields are present and similarity + distance = 1.0."""
    pdf = _make_pdf_bytes(["Metadata verification content for semantic search retrieval."])
    up = await client.post("/documents/upload", files={"file": ("meta_doc.pdf", pdf, "application/pdf")})
    doc_id = up.json()["id"]
    await client.post(f"/documents/{doc_id}/embed")

    res = await client.post(
        "/search/semantic",
        json={"query": "metadata verification test", "top_k": 5, "document_id": doc_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert data["total_results"] >= 1

    item = data["results"][0]
    assert "chunk_id" in item
    assert item["document_id"] == doc_id
    assert "meta_doc" in item["filename"]
    assert item["original_filename"] == "meta_doc.pdf"
    assert item["chunk_index"] == 0
    assert item["page_number"] == 1
    assert "metadata verification" in item["content"].lower()

    # Similarity + Distance consistency
    sim = item["similarity_score"]
    dist = item["distance"]
    assert pytest.approx(sim + dist, abs=1e-4) == 1.0

    # Cleanup
    await client.delete(f"/documents/{doc_id}")


async def test_ignore_unembedded_chunks(client: AsyncClient):
    """Search must ignore chunks where embedding IS NULL."""
    # Ingest document without triggering embed
    pdf = _make_pdf_bytes(["Unembedded raw chunk content that should not match search."])
    up = await client.post("/documents/upload", files={"file": ("unembedded.pdf", pdf, "application/pdf")})
    doc_id = up.json()["id"]

    res = await client.post(
        "/search/semantic",
        json={"query": "Unembedded raw chunk content", "document_id": doc_id},
    )
    assert res.status_code == 200
    assert res.json()["total_results"] == 0

    # Cleanup
    await client.delete(f"/documents/{doc_id}")
