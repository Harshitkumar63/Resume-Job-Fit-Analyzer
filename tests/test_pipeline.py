"""
Integration tests for the Resume Job Fit Analyzer pipeline.

Tests are organized by module:
1. Text cleaning
2. FAISS vector store
3. Scoring engine
4. Skill extraction (rule-based only — avoids model download in CI)
5. End-to-end pipeline smoke test

Pytest fixtures provide shared test data.
Run with: pytest tests/ -v
"""
from __future__ import annotations

import numpy as np
import pytest

from app.ml.matching.scoring_engine import ScoringEngine
from app.ml.ner.skill_extractor import SkillExtractor
from app.ml.explainability.explainer import MatchExplainer
from app.models.domain import MatchScore
from app.utils.text_cleaning import (
    clean_resume_text,
    collapse_whitespace,
    extract_experience_years,
    remove_emails,
    remove_urls,
)
from app.vectorstore.faiss_store import FAISSStore


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def sample_resume_text() -> str:
    return (
        "Senior Software Engineer with 5+ years of experience in Python, "
        "JavaScript, and React. Proficient in AWS, Docker, Kubernetes, "
        "and CI/CD pipelines. Experience with machine learning, PyTorch, "
        "and NLP. Built microservices using FastAPI and PostgreSQL. "
        "Email: john@example.com | https://github.com/john"
    )


@pytest.fixture
def sample_job_skills() -> list[str]:
    return ["Python", "React", "AWS", "Docker", "Machine Learning", "PostgreSQL"]


@pytest.fixture
def scoring_engine() -> ScoringEngine:
    return ScoringEngine(weight_semantic=0.50, weight_graph=0.30, weight_experience=0.20)


@pytest.fixture
def faiss_store() -> FAISSStore:
    return FAISSStore(dimension=4, m=4, ef_construction=10, ef_search=5)


# ──────────────────────────────────────────────────────────────
# Text Cleaning Tests
# ──────────────────────────────────────────────────────────────


class TestTextCleaning:
    def test_remove_urls(self):
        text = "Visit https://github.com/user and http://linkedin.com/in/user"
        result = remove_urls(text)
        assert "https://" not in result
        assert "http://" not in result

    def test_remove_emails(self):
        text = "Contact me at john@example.com for details"
        result = remove_emails(text)
        assert "@" not in result

    def test_collapse_whitespace(self):
        text = "  hello   world   "
        assert collapse_whitespace(text) == "hello world"

    def test_clean_resume_text(self, sample_resume_text):
        cleaned = clean_resume_text(sample_resume_text)
        assert "john@example.com" not in cleaned
        assert "https://github.com" not in cleaned
        assert len(cleaned) > 50  # Meaningful content remains

    def test_extract_experience_years(self):
        assert extract_experience_years("5 years of experience in Python") == 5.0
        assert extract_experience_years("10+ years experience") == 10.0
        assert extract_experience_years("No experience info") is None

    def test_extract_experience_years_multiple(self):
        text = "3 years in Python, 5 years of experience in ML"
        result = extract_experience_years(text)
        assert result == 5.0  # Should return max


# ──────────────────────────────────────────────────────────────
# FAISS Store Tests
# ──────────────────────────────────────────────────────────────


class TestFAISSStore:
    def test_build_and_search(self, faiss_store):
        embeddings = np.random.randn(10, 4).astype(np.float32)
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        labels = [f"skill_{i}" for i in range(10)]

        faiss_store.build_index(embeddings, labels)
        assert faiss_store.is_built
        assert faiss_store.size == 10

        # Search with first vector — should return itself as top match
        query = embeddings[:1]
        results = faiss_store.search(query, top_k=3)
        assert len(results) == 1
        assert len(results[0]) == 3
        assert results[0][0][0] == "skill_0"  # Top match should be itself
        assert results[0][0][1] > 0.99  # Near-perfect similarity

    def test_dimension_mismatch(self, faiss_store):
        wrong_dim = np.random.randn(5, 8).astype(np.float32)
        with pytest.raises(Exception, match="Dimension mismatch"):
            faiss_store.build_index(wrong_dim, ["a"] * 5)

    def test_search_before_build(self, faiss_store):
        query = np.random.randn(1, 4).astype(np.float32)
        with pytest.raises(Exception, match="not built"):
            faiss_store.search(query)


# ──────────────────────────────────────────────────────────────
# Scoring Engine Tests
# ──────────────────────────────────────────────────────────────


class TestScoringEngine:
    def test_semantic_score_perfect_match(self, scoring_engine):
        """Identical embeddings should yield score ≈ 1.0."""
        dim = 8
        embeddings = np.random.randn(5, dim).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms

        score, alignments = scoring_engine.compute_semantic_score(embeddings, embeddings)
        assert score > 0.95
        assert len(alignments) == 5

    def test_semantic_score_orthogonal(self, scoring_engine):
        """Orthogonal embeddings should yield low score."""
        a = np.eye(4, dtype=np.float32)[:2]  # 2 orthogonal vectors
        b = np.eye(4, dtype=np.float32)[2:]  # 2 different orthogonal vectors
        score, _ = scoring_engine.compute_semantic_score(a, b)
        assert score < 0.5

    def test_experience_score(self, scoring_engine):
        assert scoring_engine.compute_experience_score(5.0, 3.0) == 1.0
        assert scoring_engine.compute_experience_score(3.0, 3.0) == 1.0
        assert scoring_engine.compute_experience_score(None, 3.0) == 0.3
        assert scoring_engine.compute_experience_score(5.0, None) == 1.0
        assert 0.5 < scoring_engine.compute_experience_score(2.0, 3.0) < 1.0

    def test_overall_score(self, scoring_engine):
        result = scoring_engine.compute_overall(
            semantic_score=0.8,
            graph_score=0.6,
            experience_score=1.0,
            resume_skills=["Python", "React", "AWS"],
            job_skills=["Python", "React", "Java"],
            matched_skills=[("Python", 0.95), ("React", 0.90)],
        )
        assert isinstance(result, MatchScore)
        assert 0.0 <= result.overall <= 1.0
        assert result.fit_label in {"Strong Fit", "Moderate Fit", "Potential Fit", "Weak Fit"}
        assert "Java" in result.missing_skills

    def test_fit_labels(self, scoring_engine):
        """Verify fit label assignment at boundaries."""
        high = scoring_engine.compute_overall(0.9, 0.9, 1.0, [], [], [])
        assert high.fit_label == "Strong Fit"

        low = scoring_engine.compute_overall(0.1, 0.1, 0.1, [], [], [])
        assert low.fit_label == "Weak Fit"


# ──────────────────────────────────────────────────────────────
# Skill Extractor Tests (Rule-Based Only)
# ──────────────────────────────────────────────────────────────


class TestSkillExtractor:
    def test_rule_based_extraction(self, sample_resume_text):
        extractor = SkillExtractor()
        results = extractor.extract_rule_based(sample_resume_text)
        skill_names = {r["text"] for r in results}
        assert "python" in skill_names
        assert "react" in skill_names
        assert "aws" in skill_names
        assert "docker" in skill_names

    def test_rule_based_no_false_positives(self):
        extractor = SkillExtractor()
        results = extractor.extract_rule_based("The cat sat on the mat.")
        assert len(results) == 0

    def test_chunk_text(self):
        text = "Hello world. " * 200  # ~2600 chars
        chunks = SkillExtractor._chunk_text(text, max_chars=500)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 600  # Allow some tolerance for sentence boundaries


# ──────────────────────────────────────────────────────────────
# Explainability Tests
# ──────────────────────────────────────────────────────────────


class TestExplainer:
    def test_explanation_generation(self):
        explainer = MatchExplainer()
        score = MatchScore(
            overall=0.78,
            semantic_score=0.85,
            graph_score=0.65,
            experience_score=1.0,
            matched_skills=[("Python", 0.95), ("React", 0.88)],
            missing_skills=["Java", "Spring Boot"],
            fit_label="Strong Fit",
        )
        explanation = explainer.explain(
            match_score=score,
            resume_skills=["Python", "React", "AWS"],
            job_skills=["Python", "React", "Java", "Spring Boot"],
            job_title="Senior Backend Engineer",
        )
        assert "Senior Backend Engineer" in explanation
        assert "78.0%" in explanation
        assert "Strong Fit" in explanation
        assert "Python" in explanation
        assert "Java" in explanation

    def test_score_contribution(self):
        explainer = MatchExplainer()
        score = MatchScore(
            overall=0.7, semantic_score=0.8, graph_score=0.6,
            experience_score=0.5, matched_skills=[], missing_skills=[],
        )
        contributions = explainer.generate_score_contribution(
            score, {"semantic": 0.5, "graph": 0.3, "experience": 0.2},
        )
        assert len(contributions) == 3
        assert contributions[0]["dimension"] == "Semantic Similarity"
        assert contributions[0]["weighted_contribution"] == pytest.approx(0.4, abs=0.01)
