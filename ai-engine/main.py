"""
AI Engine — FastAPI application entry point.

Exposes:
  GET  /search   — Semantic log search
  POST /explain  — RAG-powered error explanation
  GET  /health   — Liveness + dependency health check
"""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from core.settings import get_settings
from routes.explain import router as explain_router
from routes.search import router as search_router
from services.search import get_embedding_model, get_qdrant_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] AI-Engine: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Warms up the sentence-transformer embedding model during startup so
    that the first /search or /explain request does not incur model-load
    latency (~2 s for all-MiniLM-L6-v2).
    """
    logger.info("AI Engine starting up — warming up embedding model...")
    get_embedding_model()
    logger.info("Embedding model ready.")
    yield
    logger.info("AI Engine shut down.")


settings = get_settings()

app = FastAPI(
    title="Logara AI Engine",
    description=(
        "Semantic log search and RAG-powered error explanation service "
        "for the Logara AI observability platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(search_router)
app.include_router(explain_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Liveness and dependency health check.

    Probes Qdrant (list collections) and Ollama (GET /api/tags).
    Returns overall status 'ok' only when both dependencies are reachable.
    """
    qdrant_ok = False
    ollama_ok = False

    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_ok = True
    except Exception as e:
        logger.warning(f"Qdrant health probe failed: {e}")

    try:
        async with httpx.AsyncClient(timeout=3.0) as http_client:
            resp = await http_client.get(
                f"{settings.ollama_base_url.rstrip('/')}/api/tags"
            )
            ollama_ok = resp.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health probe failed: {e}")

    return {
        "status": "ok" if (qdrant_ok and ollama_ok) else "degraded",
        "qdrant": qdrant_ok,
        "ollama": ollama_ok,
    }
