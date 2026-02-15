"""
Skill extraction module.

Two-stage approach:
1. Transformer-based NER (primary) — uses a fine-tuned BERT model to detect
   skill-like entities. We map generic NER labels (MISC, ORG) as skill
   candidates and filter by confidence.
2. Rule-based fallback — pattern matching against a curated skill lexicon
   catches skills the NER model misses (common with niche/new technologies).

The fallback complements, not replaces, the NER output.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from app.core.exceptions import ExtractionError, ModelLoadError

logger = logging.getLogger(__name__)

# Curated skill lexicon for rule-based fallback.
# In production, load from DB or config file.
_SKILL_LEXICON: set[str] = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "swift", "kotlin", "scala", "r", "matlab", "sql", "nosql",
    "html", "css", "react", "angular", "vue", "svelte", "next.js", "nuxt",
    "node.js", "express", "django", "flask", "fastapi", "spring boot",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "git", "linux",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "kafka", "rabbitmq", "graphql", "rest", "grpc", "microservices",
    "machine learning", "deep learning", "nlp", "computer vision",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "numpy", "spark",
    "airflow", "dbt", "snowflake", "bigquery", "redshift",
    "agile", "scrum", "kanban", "jira", "confluence",
    "data engineering", "data science", "mlops", "devops", "sre",
    "neo4j", "faiss", "langchain", "llm", "transformers", "huggingface",
    "bert", "gpt", "rag", "vector database", "embeddings",
    "figma", "tableau", "power bi", "excel", "powerpoint",
}

# NER labels that may represent skills/technologies
_SKILL_NER_LABELS = {"MISC", "ORG", "B-MISC", "I-MISC", "B-ORG", "I-ORG"}


class SkillExtractor:
    """
    Hybrid skill extraction: transformer NER + rule-based fallback.

    Thread-safety note: The HuggingFace pipeline is thread-safe for inference.
    """

    def __init__(
        self,
        model_name: str = "dslim/bert-base-NER",
        device: str = "cpu",
        confidence_threshold: float = 0.60,
        skill_lexicon: Optional[set[str]] = None,
    ):
        self._model_name = model_name
        self._device = device
        self._confidence_threshold = confidence_threshold
        self._skill_lexicon = skill_lexicon or _SKILL_LEXICON
        self._pipeline: Optional[pipeline] = None

    def _load_model(self) -> None:
        """Lazy-load the NER pipeline. Called once on first extraction."""
        if self._pipeline is not None:
            return
        try:
            logger.info("Loading NER model: %s on %s", self._model_name, self._device)
            device_id = 0 if self._device == "cuda" and torch.cuda.is_available() else -1
            self._pipeline = pipeline(
                "ner",
                model=self._model_name,
                tokenizer=self._model_name,
                aggregation_strategy="simple",
                device=device_id,
            )
            logger.info("NER model loaded successfully")
        except Exception as exc:
            raise ModelLoadError(self._model_name, str(exc)) from exc

    def extract_ner(self, text: str) -> list[dict]:
        """
        Extract skill candidates using transformer NER.

        Returns list of dicts with keys: text, label, confidence, source.
        """
        self._load_model()
        try:
            # Truncate to model max length (512 tokens ≈ 2000 chars)
            # Process in chunks for long resumes
            chunks = self._chunk_text(text, max_chars=1800)
            results: list[dict] = []
            seen: set[str] = set()

            for chunk in chunks:
                entities = self._pipeline(chunk)
                for ent in entities:
                    label = ent.get("entity_group", ent.get("entity", ""))
                    score = float(ent.get("score", 0.0))
                    word = ent.get("word", "").strip()

                    if not word or len(word) < 2:
                        continue
                    if score < self._confidence_threshold:
                        continue

                    normalized = word.lower().strip()
                    if normalized in seen:
                        continue
                    seen.add(normalized)

                    results.append({
                        "text": word,
                        "label": label,
                        "confidence": round(score, 4),
                        "source": "ner",
                    })

            return results
        except Exception as exc:
            logger.warning("NER extraction failed: %s — falling back to rule-based", exc)
            return []

    def extract_rule_based(self, text: str) -> list[dict]:
        """
        Rule-based skill extraction using lexicon matching.

        Uses word-boundary regex for precision. Case-insensitive.
        """
        text_lower = text.lower()
        results: list[dict] = []
        seen: set[str] = set()

        for skill in self._skill_lexicon:
            if skill in seen:
                continue
            # Escape regex special chars in skill name
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                seen.add(skill)
                results.append({
                    "text": skill,
                    "label": "SKILL",
                    "confidence": 0.85,  # Fixed confidence for lexicon matches
                    "source": "rule_based",
                })

        return results

    def extract(self, text: str) -> list[dict]:
        """
        Full hybrid extraction: NER + rule-based, deduplicated.

        NER results take priority; rule-based fills gaps.
        """
        ner_results = self.extract_ner(text)
        rule_results = self.extract_rule_based(text)

        # Merge: NER results take priority
        seen_normalized: set[str] = set()
        merged: list[dict] = []

        for item in ner_results:
            key = item["text"].lower().strip()
            if key not in seen_normalized:
                seen_normalized.add(key)
                merged.append(item)

        for item in rule_results:
            key = item["text"].lower().strip()
            if key not in seen_normalized:
                seen_normalized.add(key)
                merged.append(item)

        logger.info(
            "Extracted %d skills (NER=%d, rule_based=%d, merged=%d)",
            len(merged), len(ner_results), len(rule_results), len(merged),
        )
        return merged

    @property
    def is_loaded(self) -> bool:
        """Check if the NER model is loaded."""
        return self._pipeline is not None

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 1800) -> list[str]:
        """Split text into chunks respecting sentence boundaries."""
        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                current_chunk += " " + sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks or [text[:max_chars]]
