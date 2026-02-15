"""
File I/O helpers.

Isolated here so parsing services don't directly depend on
filesystem details — easier to swap with S3/GCS later.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import UnsupportedFileTypeError

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def validate_file_extension(filename: str) -> str:
    """
    Validate and return the lowercase extension.

    Raises:
        UnsupportedFileTypeError: If file extension is not supported.
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(ext)
    return ext


def generate_resume_id(filename: str) -> str:
    """Generate a deterministic-ish ID combining UUID and filename hash."""
    name_hash = hashlib.sha256(filename.encode()).hexdigest()[:8]
    short_uuid = uuid.uuid4().hex[:8]
    return f"res_{name_hash}_{short_uuid}"


async def save_upload(file: BinaryIO, filename: str, upload_dir: Path) -> Path:
    """
    Persist an uploaded file to disk.

    Args:
        file: File-like object with read().
        filename: Original filename.
        upload_dir: Target directory.

    Returns:
        Path to the saved file.
    """
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    content = file.read() if hasattr(file, "read") else file
    dest.write_bytes(content if isinstance(content, bytes) else content.encode())
    return dest
