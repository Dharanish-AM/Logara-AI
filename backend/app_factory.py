"""FastAPI application factory and lifecycle hooks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from core.settings import get_settings
from integrations.qdrant import qdrant_client
from routes.health import router as health_router
from routes.ingestion import router as ingestion_router
from routes.search import router as search_router
from routes.retrieval import router as retrieval_router
from routes.ai import router as ai_router
from routes.parsing import router as parsing_router
from routes.performance import router as performance_router
from routes.alerts import router as alerts_router
from routes.security import router as security_router
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

    import asyncio
    # Initialize Ollama manager for model bootstrap
    app.state.ollama_manager = OllamaModelManager()
    asyncio.create_task(app.state.ollama_manager.bootstrap())

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
        else ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from fastapi import Request
    from fastapi.responses import JSONResponse
    import logging

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logging.error(f"Unhandled Exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "Internal Server Error", "details": str(exc) if settings.debug else "An unexpected error occurred."},
        )

    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Logara AI API",
            "status": "active",
        }

    app.include_router(ingestion_router)
    app.include_router(search_router)
    app.include_router(health_router)
    app.include_router(retrieval_router)
    app.include_router(ai_router)
    app.include_router(parsing_router)
    app.include_router(performance_router)
    app.include_router(alerts_router)
    app.include_router(security_router)

    return app
