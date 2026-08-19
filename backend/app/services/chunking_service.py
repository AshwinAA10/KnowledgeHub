"""
KnowledgeHub — Chunking Service
================================
Splits extracted document text into deterministic, overlapping chunks.
Preserves page numbers and assigns continuous global chunk indices.

Design choices:
- Character-based sliding window: simple, predictable, language-agnostic.
- Configurable chunk size and overlap.
- Zero external dependencies.
"""

from dataclasses import dataclass
from app.services.pdf_service import ExtractedPage


@dataclass
class DocumentChunkItem:
    """Represents a generated text chunk ready for persistence."""
    chunk_index: int
    page_number: int
    content: str
    character_count: int


def chunk_text(
    text: str,
    page_number: int,
    start_chunk_index: int,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[DocumentChunkItem]:
    """
    Deterministically split a single text block into overlapping chunks.

    Args:
        text: The clean string content to split.
        page_number: 1-indexed page number where this text originated.
        start_chunk_index: The starting global index for chunks produced in this call.
        chunk_size: Maximum character length per chunk (default 500).
        chunk_overlap: Number of characters to overlap between consecutive chunks (default 50).

    Returns:
        List of DocumentChunkItem instances.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    # Validation
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size}).")

    # If text is smaller than or equal to chunk_size, return a single chunk
    if len(clean_text) <= chunk_size:
        return [
            DocumentChunkItem(
                chunk_index=start_chunk_index,
                page_number=page_number,
                content=clean_text,
                character_count=len(clean_text),
            )
        ]

    chunks: list[DocumentChunkItem] = []
    step = chunk_size - chunk_overlap
    current_idx = start_chunk_index
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_content = clean_text[start:end]

        chunks.append(
            DocumentChunkItem(
                chunk_index=current_idx,
                page_number=page_number,
                content=chunk_content,
                character_count=len(chunk_content),
            )
        )
        current_idx += 1

        # If we reached the end of the text, break
        if end >= text_len:
            break

        start += step

    return chunks


def chunk_extracted_pages(
    pages: list[ExtractedPage],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[DocumentChunkItem]:
    """
    Chunk an entire document's list of extracted pages deterministically.

    Args:
        pages: List of ExtractedPage objects.
        chunk_size: Target characters per chunk.
        chunk_overlap: Overlapping characters between consecutive chunks.

    Returns:
        List of DocumentChunkItem objects with continuous global chunk_index (0, 1, 2, ...).
    """
    all_chunks: list[DocumentChunkItem] = []
    current_global_index = 0

    for page in pages:
        page_chunks = chunk_text(
            text=page.text,
            page_number=page.page_number,
            start_chunk_index=current_global_index,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(page_chunks)
        current_global_index += len(page_chunks)

    return all_chunks
