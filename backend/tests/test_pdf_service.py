"""
Tests — PDF Extraction Service
================================
Verifies page-by-page text extraction, multi-page parsing,
and error handling (empty, corrupt, encrypted).
"""

import io
import pytest
from pathlib import Path
from pypdf import PdfWriter

from app.services.pdf_service import (
    extract_text_from_pdf,
    PDFExtractionError,
    ExtractedPage,
)


def _create_sample_pdf(pages_text: list[str], password: str | None = None) -> bytes:
    """Helper to generate a valid PDF in memory using pypdf."""
    from pypdf.generic import DictionaryObject, NameObject, create_string_object, ArrayObject, DecodedStreamObject

    writer = PdfWriter()
    for text in pages_text:
        # Create a simple blank page and add a stream containing text
        page = writer.add_blank_page(width=300, height=300)
        # Add basic text content stream in PDF syntax
        content = f"BT /F1 12 Tf 50 250 Td ({text}) Tj ET"
        stream = DecodedStreamObject()
        stream.set_data(content.encode("latin1", errors="replace"))
        page[NameObject("/Contents")] = stream

        # Add minimal font resource
        fonts = DictionaryObject()
        font_f1 = DictionaryObject()
        font_f1[NameObject("/Type")] = NameObject("/Font")
        font_f1[NameObject("/Subtype")] = NameObject("/Type1")
        font_f1[NameObject("/BaseFont")] = NameObject("/Helvetica")
        fonts[NameObject("/F1")] = font_f1

        resources = DictionaryObject()
        resources[NameObject("/Font")] = fonts
        page[NameObject("/Resources")] = resources

    if password:
        writer.encrypt(password)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_extract_valid_single_page_pdf(tmp_path: Path):
    pdf_bytes = _create_sample_pdf(["KnowledgeHub AI Engineering Project"])
    pdf_file = tmp_path / "valid_sample.pdf"
    pdf_file.write_bytes(pdf_bytes)

    result = extract_text_from_pdf(pdf_file)

    assert result.page_count == 1
    assert result.has_extractable_text is True
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert "KnowledgeHub AI Engineering Project" in result.pages[0].text


def test_extract_multi_page_pdf(tmp_path: Path):
    pages = [
        "Page 1: Architecture and Design",
        "Page 2: Vector Search & Chunking",
        "Page 3: Evaluation Metrics",
    ]
    pdf_bytes = _create_sample_pdf(pages)
    pdf_file = tmp_path / "multipage.pdf"
    pdf_file.write_bytes(pdf_bytes)

    result = extract_text_from_pdf(pdf_file)

    assert result.page_count == 3
    assert len(result.pages) == 3
    assert result.pages[0].page_number == 1
    assert "Page 1: Architecture and Design" in result.pages[0].text
    assert result.pages[1].page_number == 2
    assert "Page 2: Vector Search & Chunking" in result.pages[1].text
    assert result.pages[2].page_number == 3
    assert "Page 3: Evaluation Metrics" in result.pages[2].text


def test_extract_corrupted_pdf(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"NOT A REAL PDF FILE CONTENT AT ALL %PDF-1.4 INVALID GARBAGE")

    with pytest.raises(PDFExtractionError) as exc_info:
        extract_text_from_pdf(corrupt_file)

    assert "corrupted" in str(exc_info.value).lower() or "failed" in str(exc_info.value).lower()


def test_extract_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")

    with pytest.raises(PDFExtractionError) as exc_info:
        extract_text_from_pdf(empty_file)

    assert "empty" in str(exc_info.value).lower() or "zero bytes" in str(exc_info.value).lower()


def test_extract_encrypted_pdf(tmp_path: Path):
    pdf_bytes = _create_sample_pdf(["Secret Document"], password="SuperSecretPassword123")
    encrypted_file = tmp_path / "encrypted.pdf"
    encrypted_file.write_bytes(pdf_bytes)

    with pytest.raises(PDFExtractionError) as exc_info:
        extract_text_from_pdf(encrypted_file)

    assert "password" in str(exc_info.value).lower() or "encrypted" in str(exc_info.value).lower()


def test_extract_nonexistent_file():
    with pytest.raises(PDFExtractionError) as exc_info:
        extract_text_from_pdf("nonexistent_file_path_12345.pdf")

    assert "not found" in str(exc_info.value).lower()
