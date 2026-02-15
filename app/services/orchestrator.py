"""
Request orchestration service.

Bridges the API layer with the ML pipeline. Handles:
- File upload + parsing
- In-memory resume storage (production: swap with PostgreSQL)
- Match request coordination

This service owns the request lifecycle; the pipeline owns the ML logic.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import AnalyzerError
from app.ml.matching.pipeline import MatchingPipeline
from app.ml.ner.skill_extractor import SkillExtractor
from app.ml.embeddings.sbert_service import SBERTService
from app.graph.graph_service import GraphService
from app.ml.matching.scoring_engine import ScoringEngine
from app.ml.explainability.explainer import MatchExplainer
from app.models.domain import JobDescriptionDoc, MatchScore, ResumeDocument, Skill
from app.services.resume_parser import ResumeParser
from app.services.skill_normalizer import SkillNormalizer
from app.utils.file_utils import generate_resume_id

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Central orchestration service.

    In-memory resume store is intentional for v1 — swap with
    async PostgreSQL repository in production.
    """

    def __init__(
        self,
        parser: ResumeParser,
        extractor: SkillExtractor,
        normalizer: SkillNormalizer,
        sbert: SBERTService,
        graph_service: GraphService,
        scoring_engine: ScoringEngine,
    ):
        self._parser = parser
        self._extractor = extractor
        self._normalizer = normalizer
        self._sbert = sbert
        self._graph = graph_service
        self._scorer = scoring_engine
        self._pipeline = MatchingPipeline(
            skill_extractor=extractor,
            skill_normalizer=normalizer,
            sbert_service=sbert,
            graph_service=graph_service,
            scoring_engine=scoring_engine,
            explainer=MatchExplainer(),
        )
        # In-memory resume store (production: use DB)
        self._resume_store: dict[str, ResumeDocument] = {}

    async def process_resume(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> ResumeDocument:
        """
        Full resume processing: parse → extract → normalize → store.

        Args:
            file_bytes: Raw file content.
            filename: Original filename with extension.

        Returns:
            Processed ResumeDocument.
        """
        resume_id = generate_resume_id(filename)
        logger.info("Processing resume: %s (id=%s)", filename, resume_id)

        # Step 1: Parse
        raw_text, cleaned_text, experience_years = self._parser.parse(
            file_bytes, filename=filename,
        )

        # Step 2: Extract + normalize skills
        normalized_skills = self._pipeline.extract_and_normalize_skills(cleaned_text)

        # Convert to domain Skill objects
        skills = [
            Skill(
                raw_text=ns["raw"],
                canonical_name=ns["canonical"],
                confidence=ns.get("ner_confidence", ns.get("similarity", 0.0)),
                source=ns.get("source", "unknown"),
            )
            for ns in normalized_skills
        ]

        # Build domain object
        resume = ResumeDocument(
            resume_id=resume_id,
            filename=filename,
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            skills=skills,
            experience_years=experience_years,
        )

        # Store for later matching
        self._resume_store[resume_id] = resume
        logger.info(
            "Resume stored: %s — %d skills, %.1f yrs experience",
            resume_id, len(skills), experience_years or 0.0,
        )
        return resume

    async def match_resume_to_job(
        self,
        resume_id: str,
        job_title: str,
        job_description: str,
        required_skills: list[str],
        preferred_skills: list[str],
        min_experience_years: Optional[float] = None,
    ) -> MatchScore:
        """
        Match a stored resume against a job description.

        Args:
            resume_id: ID from process_resume().
            job_title: Job title.
            job_description: Full JD text.
            required_skills: Hard requirements.
            preferred_skills: Nice-to-haves.
            min_experience_years: Minimum experience.

        Returns:
            MatchScore with full breakdown.

        Raises:
            AnalyzerError: If resume_id not found.
        """
        resume = self._resume_store.get(resume_id)
        if resume is None:
            raise AnalyzerError(
                message=f"Resume not found: {resume_id}",
                code="RESUME_NOT_FOUND",
            )

        # Normalize JD skills through the same pipeline
        all_jd_skills = list(set(required_skills + preferred_skills))
        if all_jd_skills:
            normalized_jd = self._normalizer.normalize(all_jd_skills)
            required_skills = [
                n["canonical"]
                for n, orig in zip(normalized_jd, all_jd_skills)
                if orig in required_skills
            ]
            preferred_skills = [
                n["canonical"]
                for n, orig in zip(normalized_jd, all_jd_skills)
                if orig in preferred_skills
            ]

        job = JobDescriptionDoc(
            title=job_title,
            description=job_description,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            min_experience_years=min_experience_years,
        )

        return self._pipeline.match(resume, job)

    def get_resume(self, resume_id: str) -> Optional[ResumeDocument]:
        """Retrieve a stored resume by ID."""
        return self._resume_store.get(resume_id)
