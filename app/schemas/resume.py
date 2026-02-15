"""
Pydantic schemas for resume-related API contracts.

Separating request/response schemas from internal domain models
ensures API stability even as internal representations evolve.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Schemas ───────────────────────────────────────────────────


class JobDescription(BaseModel):
    """Job description input for matching."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_experience_years: Optional[float] = Field(default=None, ge=0)


class MatchRequest(BaseModel):
    """Request body for /match endpoint."""

    resume_id: str = Field(..., description="ID returned from /upload_resume")
    job_description: JobDescription


# ── Response Schemas ──────────────────────────────────────────────────


class ExtractedSkill(BaseModel):
    """A single extracted skill with metadata."""

    raw: str = Field(..., description="Original text span from resume")
    canonical: str = Field(..., description="Normalized skill name from ontology")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., description="Extraction method: 'ner' | 'rule_based'")


class ParsedResume(BaseModel):
    """Structured representation of a parsed resume."""

    resume_id: str
    filename: str
    raw_text: str
    cleaned_text: str
    extracted_skills: list[ExtractedSkill] = Field(default_factory=list)
    experience_years: Optional[float] = None
    parsed_at: datetime = Field(default_factory=datetime.utcnow)


class SkillMatch(BaseModel):
    """Detailed skill-level match info."""

    skill: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    matched: bool


class ScoreBreakdown(BaseModel):
    """Decomposed scoring explanation."""

    semantic_score: float = Field(..., ge=0.0, le=1.0)
    graph_score: float = Field(..., ge=0.0, le=1.0)
    experience_score: float = Field(..., ge=0.0, le=1.0)
    semantic_weight: float
    graph_weight: float
    experience_weight: float


class MatchResult(BaseModel):
    """Full match result returned to the client."""

    resume_id: str
    job_title: str
    overall_score: float = Field(..., ge=0.0, le=1.0)
    fit_label: str = Field(..., description="Strong Fit | Moderate Fit | Weak Fit")
    score_breakdown: ScoreBreakdown
    matched_skills: list[SkillMatch]
    missing_skills: list[str]
    explanation: str


class UploadResponse(BaseModel):
    """Response from resume upload."""

    resume_id: str
    filename: str
    skill_count: int
    experience_years: Optional[float]
    message: str = "Resume processed successfully"


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    models_loaded: bool
