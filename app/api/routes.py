"""
FastAPI route definitions.

Thin controller layer — all business logic is in services.
Routes handle:
- Request validation (via Pydantic schemas)
- Dependency injection
- HTTP response formatting
- Error mapping
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.core.exceptions import AnalyzerError
from app.schemas.resume import (
    HealthResponse,
    MatchRequest,
    MatchResult,
    ScoreBreakdown,
    SkillMatch,
    UploadResponse,
)
from app.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


def get_orchestrator() -> Orchestrator:
    """
    Provide the singleton Orchestrator instance.

    We lazily import and wire dependencies here rather than at module level
    to avoid import-time side effects (model loading etc.).
    """
    from app.core.dependencies import (
        get_graph_service,
        get_resume_parser,
        get_sbert_service,
        get_scoring_engine,
        get_skill_extractor,
        get_skill_normalizer,
    )

    # Initialize the skill normalizer (builds FAISS index on first call)
    normalizer = get_skill_normalizer()
    normalizer.initialize()

    return Orchestrator(
        parser=get_resume_parser(),
        extractor=get_skill_extractor(),
        normalizer=normalizer,
        sbert=get_sbert_service(),
        graph_service=get_graph_service(),
        scoring_engine=get_scoring_engine(),
    )


# Cache the orchestrator singleton
_orchestrator_instance: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    """Cached orchestrator dependency."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = get_orchestrator()
    return _orchestrator_instance


@router.post("/upload_resume", response_model=UploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    orchestrator: Orchestrator = Depends(_get_orchestrator),
):
    """
    Upload and process a resume (PDF or DOCX).

    Extracts text, identifies skills, and stores the parsed resume
    for subsequent matching requests.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        content = await file.read()
        resume = await orchestrator.process_resume(content, file.filename)
        return UploadResponse(
            resume_id=resume.resume_id,
            filename=resume.filename,
            skill_count=len(resume.skills),
            experience_years=resume.experience_years,
        )
    except AnalyzerError as exc:
        logger.error("Upload failed: %s", exc.message)
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected error during upload")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.post("/match", response_model=MatchResult)
async def match_resume(
    request: MatchRequest,
    orchestrator: Orchestrator = Depends(_get_orchestrator),
):
    """
    Match a previously uploaded resume against a job description.

    Returns a detailed fit score with skill-level breakdown and explanation.
    """
    try:
        jd = request.job_description
        result = await orchestrator.match_resume_to_job(
            resume_id=request.resume_id,
            job_title=jd.title,
            job_description=jd.description,
            required_skills=jd.required_skills,
            preferred_skills=jd.preferred_skills,
            min_experience_years=jd.min_experience_years,
        )

        return MatchResult(
            resume_id=request.resume_id,
            job_title=jd.title,
            overall_score=result.overall,
            fit_label=result.fit_label,
            score_breakdown=ScoreBreakdown(
                semantic_score=result.semantic_score,
                graph_score=result.graph_score,
                experience_score=result.experience_score,
                semantic_weight=0.50,
                graph_weight=0.30,
                experience_weight=0.20,
            ),
            matched_skills=[
                SkillMatch(skill=s, similarity_score=score, matched=True)
                for s, score in result.matched_skills
            ],
            missing_skills=result.missing_skills,
            explanation=result.explanation,
        )
    except AnalyzerError as exc:
        logger.error("Match failed: %s", exc.message)
        status = 404 if exc.code == "RESUME_NOT_FOUND" else 422
        raise HTTPException(status_code=status, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected error during matching")
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Health check endpoint for load balancers and monitoring."""
    # Check if ML models are loaded (best-effort)
    models_loaded = False
    try:
        from app.core.dependencies import get_sbert_service, get_skill_extractor
        models_loaded = (
            get_sbert_service().is_loaded
            and get_skill_extractor().is_loaded
        )
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        models_loaded=models_loaded,
    )
