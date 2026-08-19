"""
KnowledgeHub — PDF Extraction Service
======================================
Extracts text from PDF documents page-by-page using pypdf.
Preserves page numbers (1-indexed) for downstream citation and retrieval.

Handles:
- Valid standard PDFs
- Multi-page PDFs
- Encrypted/password-protected PDFs
- Corrupted/malformed files
- Empty PDFs or PDFs with no extractable text
"""

from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError, EmptyFileError


class PDFExtractionError(Exception):
    """Custom exception raised when PDF extraction fails."""
    pass


@dataclass
class ExtractedPage:
    """Represents text extracted from a single page of a PDF."""
    page_number: int  # 1-indexed
    text: str
    character_count: int


@dataclass
class PDFExtractionResult:
    """Result of full document text extraction."""
    page_count: int
    total_character_count: int
    pages: list[ExtractedPage]
    has_extractable_text: bool


def extract_text_from_pdf(file_path: str | Path) -> PDFExtractionResult:
    """
    Extract text page-by-page from a PDF file on disk.

    Args:
        file_path: Path to the PDF file on disk.

    Returns:
        PDFExtractionResult containing page count, total characters, and per-page text.

    Raises:
        PDFExtractionError: If the file is missing, empty, corrupted, or encrypted.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise PDFExtractionError(f"PDF file not found at path: {file_path}")

    try:
        reader = PdfReader(str(path))
    except (EmptyFileError, ValueError) as exc:
        raise PDFExtractionError("PDF file is empty or has zero bytes.") from exc
    except (PdfReadError, PdfStreamError) as exc:
        raise PDFExtractionError("Invalid or corrupted PDF file structure.") from exc
    except Exception as exc:
        raise PDFExtractionError(f"Failed to read PDF file: {exc}") from exc

    # Check for encryption / password protection
    if reader.is_encrypted:
        raise PDFExtractionError(
            "PDF is encrypted or password-protected and cannot be read."
        )

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise PDFExtractionError("PDF file contains no pages.")

    pages: list[ExtractedPage] = []
    total_chars = 0

    for idx, page in enumerate(reader.pages):
        page_number = idx + 1
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:
            # Fall back to empty string if a specific page fails to decode
            print(f"[KnowledgeHub PDF] WARNING: Failed extracting text from page {page_number}: {exc}")
            raw_text = ""

        # Normalize line endings and whitespace
        clean_text = raw_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        char_count = len(clean_text)
        total_chars += char_count

        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=clean_text,
                character_count=char_count,
            )
        )

    has_text = total_chars > 0

    return PDFExtractionResult(
        page_count=total_pages,
        total_character_count=total_chars,
        pages=pages,
        has_extractable_text=has_text,
    )
