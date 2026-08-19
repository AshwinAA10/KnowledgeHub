"""
KnowledgeHub — Storage Service
===============================
Handles streaming file storage to disk and cleanup for uploaded documents.
Files are stored under `backend/uploads/` with UUID-prefixed filenames
to prevent collisions and directory traversal issues.
"""

import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

from app.config import settings


def get_upload_dir() -> Path:
    """Return the absolute Path to the uploads directory."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    upload_path = base_dir / settings.upload_dir
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_uploaded_file(file: UploadFile) -> tuple[str, str, int]:
    """
    Stream an UploadFile to disk.

    Returns:
        tuple of (stored_filename, absolute_file_path_str, total_bytes_written)

    Raises:
        HTTPException: If file size exceeds max_upload_size_bytes or if write fails.
    """
    upload_dir = get_upload_dir()

    # Sanitize and create a unique stored filename
    original_name = file.filename or "document.pdf"
    safe_name = "".join(c for c in original_name if c.isalnum() or c in (".", "_", "-")).strip()
    if not safe_name:
        safe_name = "document.pdf"

    unique_prefix = uuid.uuid4().hex[:12]
    stored_filename = f"{unique_prefix}_{safe_name}"
    file_path = upload_dir / stored_filename

    total_bytes = 0
    chunk_size = 64 * 1024  # 64 KB stream chunks

    try:
        with open(file_path, "wb") as out_file:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_size_bytes:
                    # Clean up partially written file
                    out_file.close()
                    delete_file(str(file_path))
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"File size exceeds maximum allowed limit of "
                            f"{settings.max_upload_size_bytes // (1024 * 1024)} MB."
                        ),
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        delete_file(str(file_path))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write uploaded file to disk: {exc}",
        ) from exc

    return stored_filename, str(file_path), total_bytes


def delete_file(file_path: str) -> bool:
    """
    Safely delete a file from disk.
    Returns True if removed, False if file did not exist.
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
    except Exception as exc:
        print(f"[KnowledgeHub Storage] WARNING: Failed to delete file {file_path}: {exc}")
        return False
