"""Ingestion routes."""

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import ValidationError
from utils.parser import PARSER_METRICS
from core.settings import get_settings
from schemas.ingestion import parse_ingest_request, validation_errors_to_detail
from services.ingestion import IngestionService
from utils.redaction import build_default_redactor

router = APIRouter()


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
async def ingest_logs(
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
async def ingest_otel_logs(
    request: Request,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    content_type = request.headers.get("content-type", "")

    if "application/x-protobuf" in content_type:
        from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
        from google.protobuf.json_format import MessageToDict
        
        raw_body = await request.body()
        if not raw_body:
            raise HTTPException(status_code=400, detail="Empty payload")
            
        pb_request = ExportLogsServiceRequest()
        try:
            pb_request.ParseFromString(raw_body)
            payload = MessageToDict(pb_request)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid Protocol Buffer payload") from exc
    else:
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON payload") from exc
            
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="Payload must be a dictionary")

    return ingestion_service.ingest_otel_logs(payload)

@router.get("/metrics/parser")
async def parser_metrics():
    return {
        "parser_metrics": PARSER_METRICS
    }