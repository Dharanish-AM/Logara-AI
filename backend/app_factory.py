"""
FastAPI application factory and lifecycle hooks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from flask import app

from core.settings import get_settings
from integrations.qdrant import qdrant_client
from routes.health import router as health_router
from routes.ingestion import router as ingestion_router
from routes.retrieval import router as retrieval_router
from routes.ai import router as ai_router
from services.ingestion import IngestionService
from services.log_service import LogService
from utils.ollama_manager import OllamaModelManager
from utils.redaction import build_default_redactor


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.ingestion_service = IngestionService(
        redactor=build_default_redactor(
            enabled=settings.redact_enabled,
            pattern_names=settings.redact_patterns,
            include_ipv4=settings.redact_ipv4,
        )
    )

    app.state.log_service = LogService(qdrant_client)

    # Initialize Ollama manager for model bootstrap
    app.state.ollama_manager = OllamaModelManager()
    await app.state.ollama_manager.bootstrap()

    yield
    qdrant_client.close()

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    allowed_origins = (
        settings.cors_allowed_origins.split(",")
        if hasattr(settings, "cors_allowed_origins")
        else ["http://localhost:3000"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Logara AI API",
            "status": "active",
        }

    app.include_router(ingestion_router)
    app.include_router(health_router)
    app.include_router(retrieval_router)
    app.include_router(ai_router)


    return app
