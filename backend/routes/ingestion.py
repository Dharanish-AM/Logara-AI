"""Ingestion routes."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import ValidationError
from utils.parser import PARSER_METRICS
from core.settings import get_settings
from schemas.ingestion import parse_ingest_request, validation_errors_to_detail
from services.ingestion import IngestionService
from utils.redaction import build_default_redactor

router = APIRouter()

# Rate limiter — imported lazily to allow the app to start without slowapi.
try:
    from app_factory import limiter as _limiter
except ImportError:  # pragma: no cover
    _limiter = None

_INGEST_LIMIT = "120/minute"  # per-IP: enough for any agent, blocks trivial floods


def rate_limit(limit_value: str):
    def decorator(func):
        if _limiter is not None:
            return _limiter.limit(limit_value)(func)
        return func
    return decorator


def get_ingestion_service() -> IngestionService:
    from main import app

    if not hasattr(app.state, "ingestion_service"):
        settings = get_settings()
        app.state.ingestion_service = IngestionService(
            redactor=build_default_redactor(
                enabled=settings.redact_enabled,
                pattern_names=settings.redact_patterns,
                include_ipv4=settings.redact_ipv4,
            )
        )

    return app.state.ingestion_service


@router.post("/ingest")
@rate_limit(_INGEST_LIMIT)
async def ingest_logs(
    request: Request,
    payload: dict = Body(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    try:
        request_model = parse_ingest_request(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=validation_errors_to_detail(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ingestion_service.ingest_request(request_model)


@router.post("/v1/logs")
@rate_limit(_INGEST_LIMIT)
async def ingest_otel_logs(
    request: Request,
    payload: dict = Body(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    return ingestion_service.ingest_otel_logs(payload)

@router.get("/metrics/parser")
async def parser_metrics():
    return {
        "parser_metrics": PARSER_METRICS
    }