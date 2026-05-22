"""
FastAPI application factory and lifecycle hooks.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.settings import get_settings
from integrations.qdrant import qdrant_client
from routes.health import router as health_router
from routes.ingestion import router as ingestion_router
from services.ingestion import IngestionService
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    return app
