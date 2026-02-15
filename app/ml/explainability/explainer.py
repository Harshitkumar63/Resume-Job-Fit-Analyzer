"""
Explainability module.

Generates human-readable explanations for match results.
Designed to be consumed by non-technical stakeholders (recruiters, hiring managers).

Principles:
- Every score component gets a plain-English explanation
- Missing skills are explicitly listed
- Matched skills show how they were matched
- No black boxes — every number is justified
"""
from __future__ import annotations

import logging

from app.models.domain import MatchScore

logger = logging.getLogger(__name__)


class MatchExplainer:
    """Generates structured and natural-language explanations for match results."""

    def explain(
        self,
        match_score: MatchScore,
        resume_skills: list[str],
        job_skills: list[str],
        job_title: str,
        weights: dict[str, float] | None = None,
    ) -> str:
        """
        Generate a comprehensive human-readable explanation.

        Args:
            match_score: The computed match result.
            resume_skills: All canonical skills from resume.
            job_skills: All required/preferred skills from JD.
            job_title: Job title for context.
            weights: Scoring weights for transparency.

        Returns:
            Formatted explanation string.
        """
        weights = weights or {
            "semantic": 0.50,
            "graph": 0.30,
            "experience": 0.20,
        }

        sections: list[str] = []

        # Header
        sections.append(
            f"Match Analysis: Resume → {job_title}\n"
            f"Overall Score: {match_score.overall:.1%} ({match_score.fit_label})"
        )

        # Score Breakdown
        sections.append(self._format_score_breakdown(match_score, weights))

        # Matched Skills
        sections.append(self._format_matched_skills(match_score.matched_skills))

        # Missing Skills
        if match_score.missing_skills:
            sections.append(self._format_missing_skills(match_score.missing_skills))

        # Coverage Summary
        sections.append(self._format_coverage(resume_skills, job_skills, match_score))

        return "\n\n".join(sections)

    def generate_score_contribution(
        self,
        match_score: MatchScore,
        weights: dict[str, float],
    ) -> list[dict]:
        """
        Return a structured score contribution breakdown.

        Useful for frontend visualization (bar charts, etc.).
        """
        return [
            {
                "dimension": "Semantic Similarity",
                "raw_score": match_score.semantic_score,
                "weight": weights.get("semantic", 0.50),
                "weighted_contribution": match_score.semantic_score * weights.get("semantic", 0.50),
                "description": "How well resume skills match job requirements by meaning",
            },
            {
                "dimension": "Graph Structure",
                "raw_score": match_score.graph_score,
                "weight": weights.get("graph", 0.30),
                "weighted_contribution": match_score.graph_score * weights.get("graph", 0.30),
                "description": "Structural overlap in skill categories and relationships",
            },
            {
                "dimension": "Experience Fit",
                "raw_score": match_score.experience_score,
                "weight": weights.get("experience", 0.20),
                "weighted_contribution": match_score.experience_score * weights.get("experience", 0.20),
                "description": "How well candidate experience matches job requirements",
            },
        ]

    @staticmethod
    def _format_score_breakdown(match_score: MatchScore, weights: dict) -> str:
        lines = [
            "Score Breakdown:",
            f"  Semantic Similarity:  {match_score.semantic_score:.1%}"
            f"  (weight: {weights.get('semantic', 0.5):.0%})"
            f"  → contributes {match_score.semantic_score * weights.get('semantic', 0.5):.1%}",
            f"  Graph Structure:      {match_score.graph_score:.1%}"
            f"  (weight: {weights.get('graph', 0.3):.0%})"
            f"  → contributes {match_score.graph_score * weights.get('graph', 0.3):.1%}",
            f"  Experience Fit:       {match_score.experience_score:.1%}"
            f"  (weight: {weights.get('experience', 0.2):.0%})"
            f"  → contributes {match_score.experience_score * weights.get('experience', 0.2):.1%}",
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_matched_skills(matched: list[tuple[str, float]]) -> str:
        if not matched:
            return "Matched Skills: None"
        lines = ["Matched Skills:"]
        for skill, score in sorted(matched, key=lambda x: x[1], reverse=True):
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            lines.append(f"  [{bar}] {score:.1%}  {skill}")
        return "\n".join(lines)

    @staticmethod
    def _format_missing_skills(missing: list[str]) -> str:
        lines = [f"Missing Skills ({len(missing)}):"]
        for skill in sorted(missing):
            lines.append(f"  ✗ {skill}")
        return "\n".join(lines)

    @staticmethod
    def _format_coverage(
        resume_skills: list[str],
        job_skills: list[str],
        match_score: MatchScore,
    ) -> str:
        total_job = len(job_skills)
        matched_count = len(match_score.matched_skills)
        missing_count = len(match_score.missing_skills)
        extra = len(set(resume_skills) - set(job_skills))

        return (
            f"Coverage Summary:\n"
            f"  Job requires {total_job} skills\n"
            f"  Resume matches {matched_count} ({matched_count/total_job:.0%} coverage)\n"
            f"  Missing {missing_count} skills\n"
            f"  Resume has {extra} additional skills not in JD"
        ) if total_job > 0 else "Coverage Summary: No job skills specified"
