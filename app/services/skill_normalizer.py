"""
Skill normalization service.

Maps raw extracted skill strings to canonical skill names from an ontology.
Uses SBERT embeddings + FAISS nearest neighbor search to handle:
- Synonyms ("JS" → "JavaScript")
- Abbreviations ("ML" → "Machine Learning")
- Typos ("Pytohn" → "Python")
- Variant forms ("React.js" → "React")

The ontology is loaded at startup, embedded, and indexed in FAISS.
At inference time, each extracted skill is embedded and matched to the
nearest canonical skill above a similarity threshold.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from app.core.exceptions import AnalyzerError
from app.ml.embeddings.sbert_service import SBERTService
from app.vectorstore.faiss_store import FAISSStore

logger = logging.getLogger(__name__)


class SkillNormalizer:
    """
    Normalizes raw skill strings to canonical forms using embedding similarity.

    Ontology JSON format:
    {
        "skills": [
            {
                "canonical": "Python",
                "aliases": ["python3", "py", "cpython"],
                "category": "Programming Language"
            },
            ...
        ]
    }
    """

    def __init__(
        self,
        ontology_path: Path,
        sbert_service: SBERTService,
        faiss_store: FAISSStore,
        similarity_threshold: float = 0.75,
    ):
        self._ontology_path = ontology_path
        self._sbert = sbert_service
        self._faiss = faiss_store
        self._threshold = similarity_threshold
        self._canonical_skills: list[str] = []
        self._skill_categories: dict[str, str] = {}
        self._initialized = False

    def initialize(self) -> None:
        """
        Load ontology, embed canonical skills + aliases, build FAISS index.

        Called once at application startup (not per request).
        """
        if self._initialized:
            return

        ontology = self._load_ontology()
        texts_to_embed: list[str] = []
        labels: list[str] = []

        for entry in ontology.get("skills", []):
            canonical = entry["canonical"]
            category = entry.get("category", "Unknown")
            self._canonical_skills.append(canonical)
            self._skill_categories[canonical] = category

            # Embed the canonical name
            texts_to_embed.append(canonical)
            labels.append(canonical)

            # Also embed each alias, mapping back to canonical
            for alias in entry.get("aliases", []):
                texts_to_embed.append(alias)
                labels.append(canonical)

        if not texts_to_embed:
            raise AnalyzerError("Ontology is empty — no skills to index")

        logger.info("Embedding %d skill terms (%d canonical)", len(texts_to_embed), len(self._canonical_skills))
        embeddings = self._sbert.encode(texts_to_embed, show_progress=True)
        self._faiss.build_index(embeddings, labels)
        self._initialized = True
        logger.info("Skill normalizer initialized with %d canonical skills", len(self._canonical_skills))

    def normalize(self, raw_skills: list[str], top_k: int = 1) -> list[dict]:
        """
        Normalize a batch of raw skill strings.

        Args:
            raw_skills: List of raw skill text from extraction.
            top_k: Number of candidates to consider per skill.

        Returns:
            List of dicts: {raw, canonical, similarity, category}
        """
        if not self._initialized:
            self.initialize()

        if not raw_skills:
            return []

        embeddings = self._sbert.encode(raw_skills)
        search_results = self._faiss.search(embeddings, top_k=top_k)

        normalized: list[dict] = []
        for raw, candidates in zip(raw_skills, search_results):
            if candidates and candidates[0][1] >= self._threshold:
                best_canonical, best_score = candidates[0]
                normalized.append({
                    "raw": raw,
                    "canonical": best_canonical,
                    "similarity": round(best_score, 4),
                    "category": self._skill_categories.get(best_canonical, "Unknown"),
                    "matched": True,
                })
            else:
                # Below threshold — keep raw as canonical (unknown skill)
                best_score = candidates[0][1] if candidates else 0.0
                normalized.append({
                    "raw": raw,
                    "canonical": raw,  # Passthrough
                    "similarity": round(best_score, 4),
                    "category": "Unknown",
                    "matched": False,
                })

        matched = sum(1 for n in normalized if n["matched"])
        logger.info("Normalized %d/%d skills above threshold %.2f", matched, len(normalized), self._threshold)
        return normalized

    def _load_ontology(self) -> dict:
        """Load skill ontology from JSON file."""
        path = Path(self._ontology_path)
        if not path.exists():
            logger.warning("Ontology file not found at %s — using empty ontology", path)
            return {"skills": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded ontology from %s (%d skills)", path, len(data.get("skills", [])))
            return data
        except (json.JSONDecodeError, IOError) as exc:
            raise AnalyzerError(f"Failed to load ontology: {exc}") from exc

    @property
    def canonical_skills(self) -> list[str]:
        """Return the list of canonical skill names."""
        return list(self._canonical_skills)

    def get_category(self, canonical_skill: str) -> str:
        """Look up the category for a canonical skill."""
        return self._skill_categories.get(canonical_skill, "Unknown")
