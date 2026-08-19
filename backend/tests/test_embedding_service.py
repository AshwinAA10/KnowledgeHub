"""
Tests — Embedding Service
==========================
Unit tests for local embedding generation using fastembed and BAAI/bge-small-en-v1.5:
- Single text embedding
- Batch text embedding
- 384-dimensional output validation
- Deterministic output verification
- Empty / whitespace input handling
- Model info
"""

import pytest
from app.config import settings
from app.services.embedding_service import (
    embed_text,
    embed_batch,
    get_embedding_model_info,
    EmbeddingServiceError,
)


def test_embed_single_text():
    """Generating embedding for a single text string returns a 384-dimensional vector."""
    text = "KnowledgeHub is an AI-powered personal knowledge engine."
    vector = embed_text(text)

    assert isinstance(vector, list)
    assert len(vector) == settings.embedding_dimensions
    assert len(vector) == 384
    assert all(isinstance(val, float) for val in vector)


def test_embed_batch_texts():
    """Batch embedding returns vectors matching the input batch size and dimensions."""
    texts = [
        "First chunk about PostgreSQL and pgvector.",
        "Second chunk about deterministic text chunking.",
        "Third chunk about vector cosine distance.",
    ]
    vectors = embed_batch(texts)

    assert isinstance(vectors, list)
    assert len(vectors) == len(texts)
    for vec in vectors:
        assert isinstance(vec, list)
        assert len(vec) == 384
        assert all(isinstance(val, float) for val in vec)


def test_embed_deterministic_output():
    """Identical text must produce identical vector embeddings."""
    text = "Deterministic vector embeddings are essential for reproducible retrieval."
    vec1 = embed_text(text)
    vec2 = embed_text(text)

    assert len(vec1) == len(vec2)
    # Vectors should match float values
    for val1, val2 in zip(vec1, vec2):
        assert pytest.approx(val1, abs=1e-6) == val2


def test_embed_empty_and_whitespace_input():
    """Empty or whitespace-only text produces a valid 384-dimensional zero vector."""
    empty_vec = embed_text("")
    assert len(empty_vec) == 384
    assert all(v == 0.0 for v in empty_vec)

    ws_vec = embed_text("   \n\t  ")
    assert len(ws_vec) == 384
    assert all(v == 0.0 for v in ws_vec)


def test_embed_batch_with_empty_strings():
    """Batch embedding handles mixed valid and empty strings gracefully."""
    texts = [
        "Valid text snippet.",
        "",
        "Another valid passage.",
    ]
    vectors = embed_batch(texts)

    assert len(vectors) == 3
    assert len(vectors[0]) == 384
    assert any(v != 0.0 for v in vectors[0])

    assert len(vectors[1]) == 384
    assert all(v == 0.0 for v in vectors[1])

    assert len(vectors[2]) == 384
    assert any(v != 0.0 for v in vectors[2])


def test_get_embedding_model_info():
    """Model info accurately reports active model and dimension settings."""
    info = get_embedding_model_info()
    assert info["model"] == "BAAI/bge-small-en-v1.5"
    assert info["dimensions"] == 384
    assert info["batch_size"] >= 1
