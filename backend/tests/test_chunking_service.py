"""
Tests — Chunking Service
=========================
Verifies deterministic window chunking, page preservation,
boundary conditions, and parameter validation.
"""

import pytest
from app.services.chunking_service import (
    chunk_text,
    chunk_extracted_pages,
    DocumentChunkItem,
)
from app.services.pdf_service import ExtractedPage


def test_chunk_text_shorter_than_chunk_size():
    text = "Short sentence."
    chunks = chunk_text(text, page_number=1, start_chunk_index=0, chunk_size=500, chunk_overlap=50)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert chunks[0].content == "Short sentence."
    assert chunks[0].character_count == len("Short sentence.")


def test_chunk_text_exact_chunk_size():
    text = "A" * 500
    chunks = chunk_text(text, page_number=1, start_chunk_index=0, chunk_size=500, chunk_overlap=50)

    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].character_count == 500


def test_chunk_text_with_overlap():
    # 100 characters total, chunk_size=40, overlap=10 -> step = 30
    # Chunk 0: [0:40]
    # Chunk 1: [30:70]
    # Chunk 2: [60:100]
    text = "0123456789" * 10
    chunks = chunk_text(text, page_number=2, start_chunk_index=5, chunk_size=40, chunk_overlap=10)

    assert len(chunks) == 3
    assert chunks[0].chunk_index == 5
    assert chunks[0].page_number == 2
    assert chunks[0].content == text[0:40]

    assert chunks[1].chunk_index == 6
    assert chunks[1].page_number == 2
    assert chunks[1].content == text[30:70]

    assert chunks[2].chunk_index == 7
    assert chunks[2].page_number == 2
    assert chunks[2].content == text[60:100]


def test_chunk_text_deterministic_output():
    text = "Machine Learning Engineering in Practice. " * 20
    run1 = chunk_text(text, page_number=1, start_chunk_index=0, chunk_size=200, chunk_overlap=30)
    run2 = chunk_text(text, page_number=1, start_chunk_index=0, chunk_size=200, chunk_overlap=30)

    assert len(run1) == len(run2)
    for c1, c2 in zip(run1, run2):
        assert c1.chunk_index == c2.chunk_index
        assert c1.content == c2.content
        assert c1.character_count == c2.character_count


def test_chunk_extracted_pages_preserves_page_numbers_and_global_index():
    pages = [
        ExtractedPage(page_number=1, text="Page 1 text that is relatively short.", character_count=38),
        ExtractedPage(page_number=2, text="Page 2 text " * 30, character_count=360),
        ExtractedPage(page_number=3, text="Page 3 concluding remarks.", character_count=26),
    ]

    # chunk_size 150, overlap 20 -> step 130
    chunks = chunk_extracted_pages(pages, chunk_size=150, chunk_overlap=20)

    assert len(chunks) >= 4

    # Assert sequential continuous chunk_index starting from 0
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx

    # Check page 1
    assert chunks[0].page_number == 1
    assert "Page 1 text" in chunks[0].content

    # Check last chunk
    last_chunk = chunks[-1]
    assert last_chunk.page_number == 3
    assert "Page 3 concluding remarks." in last_chunk.content


def test_chunk_text_empty_input():
    chunks = chunk_text("", page_number=1, start_chunk_index=0)
    assert chunks == []

    whitespace_chunks = chunk_text("   \n\t  ", page_number=1, start_chunk_index=0)
    assert whitespace_chunks == []


def test_chunk_text_invalid_parameters():
    with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
        chunk_text("Hello", page_number=1, start_chunk_index=0, chunk_size=0)

    with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
        chunk_text("Hello", page_number=1, start_chunk_index=0, chunk_size=100, chunk_overlap=-5)

    with pytest.raises(ValueError, match="chunk_overlap .* must be strictly less than chunk_size"):
        chunk_text("Hello", page_number=1, start_chunk_index=0, chunk_size=50, chunk_overlap=50)
