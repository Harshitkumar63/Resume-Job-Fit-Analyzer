"""
Custom exception hierarchy.

All domain exceptions inherit from AnalyzerError so callers can
catch broad or narrow as needed. FastAPI exception handlers map
these to appropriate HTTP responses.
"""
from __future__ import annotations


class AnalyzerError(Exception):
    """Base exception for the Resume Job Fit Analyzer."""

    def __init__(self, message: str = "An unexpected error occurred", code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ParsingError(AnalyzerError):
    """Raised when resume parsing fails."""

    def __init__(self, message: str = "Failed to parse resume"):
        super().__init__(message=message, code="PARSING_ERROR")


class UnsupportedFileTypeError(AnalyzerError):
    """Raised for unsupported file formats."""

    def __init__(self, file_type: str):
        super().__init__(
            message=f"Unsupported file type: {file_type}. Supported: PDF, DOCX",
            code="UNSUPPORTED_FILE_TYPE",
        )


class ModelLoadError(AnalyzerError):
    """Raised when an ML model fails to load."""

    def __init__(self, model_name: str, reason: str = ""):
        detail = f" — {reason}" if reason else ""
        super().__init__(
            message=f"Failed to load model '{model_name}'{detail}",
            code="MODEL_LOAD_ERROR",
        )


class ExtractionError(AnalyzerError):
    """Raised when skill extraction fails."""

    def __init__(self, message: str = "Skill extraction failed"):
        super().__init__(message=message, code="EXTRACTION_ERROR")


class VectorStoreError(AnalyzerError):
    """Raised on FAISS index operations failure."""

    def __init__(self, message: str = "Vector store operation failed"):
        super().__init__(message=message, code="VECTORSTORE_ERROR")


class GraphError(AnalyzerError):
    """Raised on knowledge graph operations failure."""

    def __init__(self, message: str = "Graph operation failed"):
        super().__init__(message=message, code="GRAPH_ERROR")
