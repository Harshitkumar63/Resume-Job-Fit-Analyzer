"""
Resume parsing service.

Extracts raw text from PDF and DOCX files using dedicated libraries,
then runs the text cleaning pipeline. Strategy pattern: each file type
has its own extractor function, dispatched by extension.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Callable, Union

import pdfplumber
from docx import Document as DocxDocument

from app.core.exceptions import ParsingError, UnsupportedFileTypeError
from app.utils.file_utils import validate_file_extension
from app.utils.text_cleaning import clean_resume_text, extract_experience_years

logger = logging.getLogger(__name__)

# Type alias for extractor functions
ExtractorFn = Callable[[Union[Path, bytes]], str]


def _extract_pdf_text(source: Union[Path, bytes]) -> str:
    """
    Extract text from a PDF using pdfplumber.

    pdfplumber chosen over PyPDF2 for superior table/layout handling.
    """
    try:
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        with pdfplumber.open(source) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n".join(pages)
    except Exception as exc:
        raise ParsingError(f"PDF extraction failed: {exc}") from exc


def _extract_docx_text(source: Union[Path, bytes]) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        doc = DocxDocument(source)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        raise ParsingError(f"DOCX extraction failed: {exc}") from exc


# Dispatch table — easy to extend with new formats
_EXTRACTORS: dict[str, ExtractorFn] = {
    ".pdf": _extract_pdf_text,
    ".docx": _extract_docx_text,
}


class ResumeParser:
    """
    Stateless service that converts a resume file into structured text.

    Usage:
        parser = ResumeParser()
        raw, cleaned, experience = parser.parse(file_path)
    """

    def parse(
        self,
        source: Union[Path, bytes],
        filename: str | None = None,
    ) -> tuple[str, str, float | None]:
        """
        Parse a resume file.

        Args:
            source: File path or raw bytes.
            filename: Original filename (required if source is bytes).

        Returns:
            Tuple of (raw_text, cleaned_text, experience_years).

        Raises:
            UnsupportedFileTypeError: If file type is not supported.
            ParsingError: If text extraction fails.
        """
        if isinstance(source, Path):
            ext = validate_file_extension(source.name)
        elif filename:
            ext = validate_file_extension(filename)
        else:
            raise ParsingError("Filename required when source is bytes")

        extractor = _EXTRACTORS.get(ext)
        if extractor is None:
            raise UnsupportedFileTypeError(ext)

        logger.info("Parsing resume: %s (type=%s)", filename or source, ext)
        raw_text = extractor(source)

        if not raw_text.strip():
            raise ParsingError("Extracted text is empty — file may be scanned/image-based")

        cleaned_text = clean_resume_text(raw_text)
        experience_years = extract_experience_years(cleaned_text)

        logger.info(
            "Parsed %d chars → %d cleaned chars, experience=%.1f yrs",
            len(raw_text),
            len(cleaned_text),
            experience_years or 0.0,
        )
        return raw_text, cleaned_text, experience_years
