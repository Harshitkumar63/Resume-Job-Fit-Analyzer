"""
Matching pipeline orchestrator.

Coordinates the full resume–job matching flow:
1. Extract skills from resume text
2. Normalize skills via ontology + FAISS
3. Embed resume and job skills
4. Build knowledge graph
5. Compute multi-stage scores
6. Generate explanation

This is the central coordinator — it owns no business logic, only orchestration.
Each step delegates to a specialized service.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from app.ml.embeddings.sbert_service import SBERTService
from app.ml.explainability.explainer import MatchExplainer
from app.ml.matching.scoring_engine import ScoringEngine
from app.ml.ner.skill_extractor import SkillExtractor
from app.graph.graph_service import GraphService
from app.models.domain import MatchScore, ResumeDocument, JobDescriptionDoc
from app.services.skill_normalizer import SkillNormalizer

logger = logging.getLogger(__name__)


class MatchingPipeline:
    """
    End-to-end matching pipeline.

    Stateless — all state is passed in via arguments.
    Dependencies are injected via constructor.
    """

    def __init__(
        self,
        skill_extractor: SkillExtractor,
        skill_normalizer: SkillNormalizer,
        sbert_service: SBERTService,
        graph_service: GraphService,
        scoring_engine: ScoringEngine,
        explainer: Optional[MatchExplainer] = None,
    ):
        self._extractor = skill_extractor
        self._normalizer = skill_normalizer
        self._sbert = sbert_service
        self._graph = graph_service
        self._scorer = scoring_engine
        self._explainer = explainer or MatchExplainer()

    def extract_and_normalize_skills(self, text: str) -> list[dict]:
        """
        Run skill extraction + normalization on a text.

        Returns list of normalized skill dicts.
        """
        raw_skills = self._extractor.extract(text)
        raw_texts = [s["text"] for s in raw_skills]

        if not raw_texts:
            logger.warning("No skills extracted from text")
            return []

        normalized = self._normalizer.normalize(raw_texts)

        # Merge extraction metadata with normalization results
        for norm, raw in zip(normalized, raw_skills):
            norm["source"] = raw.get("source", "unknown")
            norm["ner_confidence"] = raw.get("confidence", 0.0)

        return normalized

    def match(
        self,
        resume: ResumeDocument,
        job: JobDescriptionDoc,
    ) -> MatchScore:
        """
        Execute the full matching pipeline.

        Args:
            resume: Parsed and skill-extracted resume.
            job: Job description with required skills.

        Returns:
            Fully populated MatchScore with explanation.
        """
        logger.info(
            "Starting match: resume=%s (%d skills) → job=%s (%d required + %d preferred skills)",
            resume.resume_id,
            len(resume.skills),
            job.title,
            len(job.required_skills),
            len(job.preferred_skills),
        )

        # Collect canonical skill names
        resume_skill_names = [s.canonical_name for s in resume.skills]
        job_skill_names = list(set(job.required_skills + job.preferred_skills))

        if not job_skill_names:
            logger.warning("No job skills provided — returning zero score")
            return MatchScore(
                overall=0.0,
                semantic_score=0.0,
                graph_score=0.0,
                experience_score=0.0,
                matched_skills=[],
                missing_skills=[],
                explanation="No job skills specified for matching.",
                fit_label="Weak Fit",
            )

        # ── Stage 1: Semantic Scoring ─────────────────────────────────
        resume_embeddings = self._sbert.encode(resume_skill_names)
        job_embeddings = self._sbert.encode(job_skill_names)

        semantic_score, alignments = self._scorer.compute_semantic_score(
            resume_embeddings, job_embeddings,
        )

        # Build matched skills list from alignments
        matched_skills: list[tuple[str, float]] = []
        similarity_threshold = 0.5
        for job_idx, resume_idx, sim in alignments:
            if sim >= similarity_threshold:
                matched_skills.append((job_skill_names[job_idx], round(float(sim), 4)))

        # ── Stage 2: Graph Scoring ────────────────────────────────────
        skill_categories = {s.canonical_name: "Unknown" for s in resume.skills}
        graph = self._graph.build_skill_graph(
            resume_skills=resume_skill_names,
            job_skills=job_skill_names,
            skill_categories=skill_categories,
        )
        graph_score = self._graph.compute_graph_similarity(
            graph, resume_skill_names, job_skill_names,
        )

        # ── Stage 3: Experience Scoring ───────────────────────────────
        experience_score = self._scorer.compute_experience_score(
            resume.experience_years,
            job.min_experience_years,
        )

        # ── Combine ──────────────────────────────────────────────────
        match_result = self._scorer.compute_overall(
            semantic_score=semantic_score,
            graph_score=graph_score,
            experience_score=experience_score,
            resume_skills=resume_skill_names,
            job_skills=job_skill_names,
            matched_skills=matched_skills,
        )

        # ── Generate Explanation ──────────────────────────────────────
        match_result.explanation = self._explainer.explain(
            match_score=match_result,
            resume_skills=resume_skill_names,
            job_skills=job_skill_names,
            job_title=job.title,
            weights={
                "semantic": self._scorer.w_semantic,
                "graph": self._scorer.w_graph,
                "experience": self._scorer.w_experience,
            },
        )

        return match_result
