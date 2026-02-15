"""
FastAPI dependency injection providers.

Centralizes object lifecycle management. Services are lazily initialized
and cached at the module level (singleton pattern without a DI container).
"""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.config import get_settings

if TYPE_CHECKING:
    from app.ml.embeddings.sbert_service import SBERTService
    from app.ml.ner.skill_extractor import SkillExtractor
    from app.services.resume_parser import ResumeParser
    from app.services.skill_normalizer import SkillNormalizer
    from app.vectorstore.faiss_store import FAISSStore
    from app.graph.graph_service import GraphService
    from app.ml.matching.scoring_engine import ScoringEngine


@lru_cache(maxsize=1)
def get_resume_parser() -> "ResumeParser":
    from app.services.resume_parser import ResumeParser
    return ResumeParser()


@lru_cache(maxsize=1)
def get_sbert_service() -> "SBERTService":
    from app.ml.embeddings.sbert_service import SBERTService
    settings = get_settings()
    return SBERTService(
        model_name=settings.sbert_model_name,
        device=settings.ner_device,
        batch_size=settings.batch_size,
    )


@lru_cache(maxsize=1)
def get_skill_extractor() -> "SkillExtractor":
    from app.ml.ner.skill_extractor import SkillExtractor
    settings = get_settings()
    return SkillExtractor(
        model_name=settings.ner_model_name,
        device=settings.ner_device,
        confidence_threshold=settings.ner_confidence_threshold,
    )


@lru_cache(maxsize=1)
def get_faiss_store() -> "FAISSStore":
    from app.vectorstore.faiss_store import FAISSStore
    settings = get_settings()
    return FAISSStore(
        dimension=settings.embedding_dimension,
        m=settings.faiss_m,
        ef_construction=settings.faiss_ef_construction,
        ef_search=settings.faiss_ef_search,
    )


@lru_cache(maxsize=1)
def get_skill_normalizer() -> "SkillNormalizer":
    from app.services.skill_normalizer import SkillNormalizer
    settings = get_settings()
    sbert = get_sbert_service()
    faiss_store = get_faiss_store()
    return SkillNormalizer(
        ontology_path=settings.ontology_path,
        sbert_service=sbert,
        faiss_store=faiss_store,
        similarity_threshold=settings.skill_similarity_threshold,
    )


@lru_cache(maxsize=1)
def get_graph_service() -> "GraphService":
    from app.graph.graph_service import GraphService
    settings = get_settings()
    return GraphService(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )


@lru_cache(maxsize=1)
def get_scoring_engine() -> "ScoringEngine":
    from app.ml.matching.scoring_engine import ScoringEngine
    settings = get_settings()
    return ScoringEngine(
        weight_semantic=settings.weight_semantic,
        weight_graph=settings.weight_graph,
        weight_experience=settings.weight_experience,
    )
