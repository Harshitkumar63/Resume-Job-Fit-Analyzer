"""
Text cleaning and normalization utilities.

Designed as pure functions — no side effects, easily testable.
"""
from __future__ import annotations

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters to NFKD form and strip accents."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def remove_urls(text: str) -> str:
    """Strip URLs from text."""
    return re.sub(r"https?://\S+|www\.\S+", " ", text)


def remove_emails(text: str) -> str:
    """Strip email addresses from text."""
    return re.sub(r"\S+@\S+\.\S+", " ", text)


def remove_phone_numbers(text: str) -> str:
    """Strip phone numbers (various formats)."""
    return re.sub(
        r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}",
        " ",
        text,
    )


def collapse_whitespace(text: str) -> str:
    """Replace runs of whitespace with a single space."""
    return re.sub(r"\s+", " ", text).strip()


def remove_special_characters(text: str) -> str:
    """Remove non-alphanumeric characters except common punctuation."""
    return re.sub(r"[^\w\s.,;:!?/\-+()\[\]{}#&@']", " ", text)


def clean_resume_text(text: str) -> str:
    """
    Full cleaning pipeline for resume text.

    Order matters:
    1. Unicode normalization first (handles encoding artifacts)
    2. Remove PII-like patterns (URLs, emails, phones)
    3. Remove special chars
    4. Collapse whitespace last
    """
    text = normalize_unicode(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = remove_phone_numbers(text)
    text = remove_special_characters(text)
    text = collapse_whitespace(text)
    return text


def extract_experience_years(text: str) -> float | None:
    """
    Heuristic extraction of years of experience from resume text.

    Looks for patterns like "5 years of experience", "5+ years", etc.
    Returns the maximum value found, or None.
    """
    patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
        r"(?:experience|exp)\s*(?:of)?\s*(\d+)\+?\s*(?:years?|yrs?)",
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:in|of|working)",
    ]
    years: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                years.append(float(match.group(1)))
            except (ValueError, IndexError):
                continue

    return max(years) if years else None
