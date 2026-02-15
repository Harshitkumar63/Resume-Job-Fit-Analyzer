"""
FastAPI application entry point.

Configures:
- CORS middleware
- Exception handlers
- Lifespan events (startup/shutdown)
- Route registration
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AnalyzerError
from app.core.logging import setup_logging

settings = get_settings()

# Configure logging before anything else
setup_logging(level=settings.log_level, json_format=not settings.debug)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup: pre-load models so the first request isn't slow.
    Shutdown: cleanup resources.
    """
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Create upload directory
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    # Optionally pre-load models at startup
    if not settings.debug:
        try:
            logger.info("Pre-loading ML models...")
            from app.core.dependencies import get_sbert_service, get_skill_extractor
            get_sbert_service().encode("warmup")  # Trigger lazy load
            get_skill_extractor().extract_rule_based("warmup")
            logger.info("ML models pre-loaded successfully")
        except Exception as exc:
            logger.warning("Model pre-loading failed (will load on first request): %s", exc)

    yield  # Application runs here

    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "AI-Powered Resume–Job Fit Analyzer using transformer-based "
            "skill extraction, FAISS vector search, and knowledge graph reasoning."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ────────────────────────────────────────────
    @app.exception_handler(AnalyzerError)
    async def analyzer_error_handler(request: Request, exc: AnalyzerError):
        return JSONResponse(
            status_code=422,
            content={
                "error": exc.code,
                "message": exc.message,
            },
        )

    # ── Routes ────────────────────────────────────────────────────────
    from app.api.routes import router
    app.include_router(router, prefix=settings.api_prefix)

    return app


# Module-level app instance for uvicorn
app = create_app()
