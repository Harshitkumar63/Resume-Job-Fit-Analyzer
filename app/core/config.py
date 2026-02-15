"""
Application configuration management.

Uses pydantic-settings for environment variable binding with type validation.
All config is centralized here to avoid scattered os.getenv() calls.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Resume Job Fit Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = ["*"]

    # ── ML Models ─────────────────────────────────────────────────────
    ner_model_name: str = "dslim/bert-base-NER"
    sbert_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # MiniLM-L6-v2 output dim
    ner_device: str = "cpu"  # "cuda" if GPU available
    batch_size: int = 32

    # ── FAISS ─────────────────────────────────────────────────────────
    faiss_index_path: Optional[str] = None
    faiss_nprobe: int = 10
    faiss_ef_search: int = 64
    faiss_ef_construction: int = 200
    faiss_m: int = 32  # HNSW M parameter

    # ── Neo4j ─────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # ── PostgreSQL ────────────────────────────────────────────────────
    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/resume_analyzer"

    # ── Redis ─────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600

    # ── Paths ─────────────────────────────────────────────────────────
    data_dir: Path = Path("data")
    ontology_path: Path = Path("data/ontology/skill_ontology.json")
    upload_dir: Path = Path("data/uploads")

    # ── Scoring Weights ───────────────────────────────────────────────
    weight_semantic: float = 0.50
    weight_graph: float = 0.30
    weight_experience: float = 0.20

    # ── Thresholds ────────────────────────────────────────────────────
    skill_similarity_threshold: float = 0.75
    ner_confidence_threshold: float = 0.60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings factory. Cached after first call."""
    return Settings()
