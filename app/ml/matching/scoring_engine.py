"""
Multi-stage hybrid scoring engine.

Combines three independent scoring dimensions:
1. Semantic score — embedding similarity between resume and JD skills
2. Graph score — structural overlap from the knowledge graph
3. Experience score — years-of-experience fit

Each scorer is a pure function. The engine computes a weighted combination
and assigns a fit label. Weights are configurable via Settings.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from app.models.domain import MatchScore

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Computes composite match scores from multiple signal dimensions.

    Design:
        - Each scoring dimension is independent (can be computed in parallel)
        - Weights are configurable, must sum to ~1.0
        - Score output is always in [0, 1]
    """

    FIT_LABELS = {
        (0.75, 1.01): "Strong Fit",
        (0.50, 0.75): "Moderate Fit",
        (0.25, 0.50): "Potential Fit",
        (0.00, 0.25): "Weak Fit",
    }

    def __init__(
        self,
        weight_semantic: float = 0.50,
        weight_graph: float = 0.30,
        weight_experience: float = 0.20,
    ):
        total = weight_semantic + weight_graph + weight_experience
        # Normalize weights to sum to 1.0 (defensive)
        self.w_semantic = weight_semantic / total
        self.w_graph = weight_graph / total
        self.w_experience = weight_experience / total

    def compute_semantic_score(
        self,
        resume_embeddings: np.ndarray,
        job_skill_embeddings: np.ndarray,
    ) -> tuple[float, list[tuple[int, int, float]]]:
        """
        Compute semantic similarity between resume skills and job skills.

        Strategy: For each job skill, find the best-matching resume skill.
        The semantic score is the mean of best-match similarities.

        This captures "how well does the resume cover the job requirements"
        rather than simple pairwise average.

        Args:
            resume_embeddings: (n_resume, dim) normalized embeddings.
            job_skill_embeddings: (n_job, dim) normalized embeddings.

        Returns:
            Tuple of (score, alignment_details).
            alignment_details: List of (job_idx, resume_idx, similarity).
        """
        if resume_embeddings.size == 0 or job_skill_embeddings.size == 0:
            return 0.0, []

        # Similarity matrix: (n_job, n_resume)
        sim_matrix = job_skill_embeddings @ resume_embeddings.T

        # For each job skill, find the best matching resume skill
        best_resume_idx = np.argmax(sim_matrix, axis=1)
        best_scores = sim_matrix[np.arange(len(best_resume_idx)), best_resume_idx]

        alignments = [
            (j_idx, int(r_idx), float(score))
            for j_idx, (r_idx, score) in enumerate(zip(best_resume_idx, best_scores))
        ]

        # Mean of best matches, clipped to [0, 1]
        score = float(np.clip(np.mean(best_scores), 0.0, 1.0))

        logger.debug("Semantic score: %.4f (from %d job skills)", score, len(best_scores))
        return score, alignments

    @staticmethod
    def compute_experience_score(
        resume_years: Optional[float],
        required_years: Optional[float],
    ) -> float:
        """
        Score experience fit using a smooth sigmoid-like curve.

        - If no requirement, return 1.0 (experience is not a factor).
        - If resume has more than required, score is 1.0.
        - If resume has less, score decays smoothly (not a cliff).

        This avoids penalizing candidates who are 0.5 years short.
        """
        if required_years is None or required_years <= 0:
            return 1.0  # No requirement specified

        if resume_years is None:
            return 0.3  # Unknown experience → conservative estimate

        if resume_years >= required_years:
            return 1.0

        # Smooth decay: ratio with minimum floor
        ratio = resume_years / required_years
        # Apply a gentle curve so 80% of required → ~0.7 score
        return float(np.clip(ratio ** 0.7, 0.0, 1.0))

    def compute_overall(
        self,
        semantic_score: float,
        graph_score: float,
        experience_score: float,
        resume_skills: list[str],
        job_skills: list[str],
        matched_skills: list[tuple[str, float]],
    ) -> MatchScore:
        """
        Compute the weighted overall score and build the MatchScore result.

        Args:
            semantic_score: [0, 1] from embedding similarity.
            graph_score: [0, 1] from knowledge graph overlap.
            experience_score: [0, 1] from experience comparison.
            resume_skills: Canonical skill names from resume.
            job_skills: All required + preferred skills from JD.
            matched_skills: List of (skill, similarity) pairs.

        Returns:
            Fully populated MatchScore.
        """
        overall = (
            self.w_semantic * semantic_score
            + self.w_graph * graph_score
            + self.w_experience * experience_score
        )
        overall = float(np.clip(overall, 0.0, 1.0))

        # Determine fit label
        fit_label = "Weak Fit"
        for (low, high), label in self.FIT_LABELS.items():
            if low <= overall < high:
                fit_label = label
                break

        # Compute missing skills
        matched_names = {s.lower() for s, _ in matched_skills}
        missing = [s for s in job_skills if s.lower() not in matched_names]

        match_score = MatchScore(
            overall=round(overall, 4),
            semantic_score=round(semantic_score, 4),
            graph_score=round(graph_score, 4),
            experience_score=round(experience_score, 4),
            matched_skills=matched_skills,
            missing_skills=missing,
            fit_label=fit_label,
        )

        logger.info(
            "Overall score: %.4f (%s) — semantic=%.3f graph=%.3f exp=%.3f",
            overall, fit_label, semantic_score, graph_score, experience_score,
        )
        return match_score
