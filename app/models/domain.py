"""
Internal domain models.

These are *not* Pydantic schemas for the API — they represent
the internal data structures passed between services.
Keeping them separate from API schemas prevents coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class Skill:
    """Domain representation of a skill."""

    raw_text: str
    canonical_name: str
    confidence: float
    source: str  # "ner" | "rule_based"
    embedding: Optional[np.ndarray] = field(default=None, repr=False)


@dataclass
class ResumeDocument:
    """Internal representation of a parsed resume through the pipeline."""

    resume_id: str
    filename: str
    raw_text: str
    cleaned_text: str
    skills: list[Skill] = field(default_factory=list)
    experience_years: Optional[float] = None
    skill_embeddings: Optional[np.ndarray] = field(default=None, repr=False)


@dataclass
class JobDescriptionDoc:
    """Internal representation of a job description."""

    title: str
    description: str
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_experience_years: Optional[float] = None
    skill_embeddings: Optional[np.ndarray] = field(default=None, repr=False)


@dataclass
class MatchScore:
    """Composite match score with breakdown."""

    overall: float
    semantic_score: float
    graph_score: float
    experience_score: float
    matched_skills: list[tuple[str, float]]  # (skill_name, similarity)
    missing_skills: list[str]
    explanation: str = ""
    fit_label: str = ""
