"""
Ingestion service for raw, structured, batch, and OTLP log payloads.
"""

import json
from typing import Any

from fastapi import HTTPException

from core.settings import get_settings
from integrations.redis import redis_client
from schemas.ingestion import (
    BatchLogIngestRequest,
    LegacyRawLogIngestRequest,
    NormalizedLog,
    QueuePayload,
    StructuredLogIngestRequest,
)
from utils.otel import parse_otel_log_payload
from utils.parser import LogParser
from utils.redaction import Redactor
from utils.timestamp import normalize_timestamp


VALID_LEVELS = {
    "INFO",
    "WARN",
    "WARNING",
    "ERROR",
    "DEBUG",
    "CRITICAL",
    "TRACE",
    "FATAL",
}


class IngestionService:
    def __init__(self, redactor: Redactor):
        self.redactor = redactor

    def ingest_request(
        self,
        request_model: LegacyRawLogIngestRequest | StructuredLogIngestRequest | BatchLogIngestRequest,
    ) -> dict[str, Any]:
        if isinstance(request_model, LegacyRawLogIngestRequest):
            return self.ingest_raw_log(request_model.log_data)

        if isinstance(request_model, BatchLogIngestRequest):
            return self.ingest_batch_logs(request_model.logs)

        return self.ingest_structured_log(request_model)

    def ingest_raw_log(self, log_data: str) -> dict[str, Any]:
        if not log_data or not log_data.strip():
            raise HTTPException(status_code=400, detail="Log message cannot be empty")

        redaction_result = self.redactor.redact_with_summary(log_data)
        clean_log = redaction_result.text
        parsed = LogParser.parse_line(clean_log)

        if not parsed:
            raw_payload = {
                "timestamp": None,
                "level": "INFO",
                "message": clean_log,
                "metadata": {},
                "parser_type": "raw_input",
                "raw": clean_log,
            }
            self._queue_normalized_payload(raw_payload)
            return {
                "status": "accepted_raw_queued",
                "message": clean_log,
                "redaction_summary": redaction_result.matches,
            }

        metadata = parsed.get("metadata", {})
        parsed = self.redactor.redact_dict(parsed)
        self._queue_normalized_payload(parsed)

        return {
            "status": "success_queued",
            "parsed": parsed,
            "metadata": metadata,
            "redaction_summary": redaction_result.matches,
        }

    def ingest_structured_log(self, request_model: StructuredLogIngestRequest) -> dict[str, Any]:
        normalized_log, redaction_summary = self._normalize_structured_log(request_model)
        self._queue_normalized_payload(normalized_log.model_dump())
        return {
            "status": "success_queued",
            "parsed": normalized_log.model_dump(),
            "metadata": normalized_log.metadata,
            "redaction_summary": redaction_summary,
        }

    def ingest_batch_logs(self, logs: list[StructuredLogIngestRequest]) -> dict[str, Any]:
        processed_records = 0
        total_redaction_summary: dict[str, int] = {}

        for log in logs:
            normalized_log, redaction_summary = self._normalize_structured_log(log)
            self._queue_normalized_payload(normalized_log.model_dump())
            processed_records += 1
            for key, value in redaction_summary.items():
                total_redaction_summary[key] = total_redaction_summary.get(key, 0) + value

        return {
            "status": "success",
            "processed_records": processed_records,
            "redaction_summary": total_redaction_summary,
        }

    def ingest_otel_logs(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            raise HTTPException(status_code=400, detail="Empty payload")

        try:
            records = parse_otel_log_payload(payload)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse OTel logs: {str(exc)}",
            ) from exc

        if not records:
            return {
                "status": "success",
                "processed_records": 0,
                "redaction_summary": {},
            }

        queued_count = 0
        total_redaction_matches: dict[str, int] = {}

        for record in records:
            redact_res = self.redactor.redact_with_summary(record["message"])
            record["message"] = redact_res.text
            record["raw"] = redact_res.text

            for label, count in redact_res.matches.items():
                total_redaction_matches[label] = total_redaction_matches.get(label, 0) + count

            record = self.redactor.redact_dict(record)
            self._queue_normalized_payload(record)
            queued_count += 1

        return {
            "status": "success",
            "processed_records": queued_count,
            "redaction_summary": total_redaction_matches,
        }

    def _normalize_structured_log(
        self,
        request_model: StructuredLogIngestRequest,
    ) -> tuple[NormalizedLog, dict[str, int]]:
        if not request_model.message or not request_model.message.strip():
            raise HTTPException(status_code=400, detail="Log message cannot be empty")

        redaction_result = self.redactor.redact_with_summary(request_model.message)
        clean_message = redaction_result.text

        metadata = dict(request_model.metadata)
        if request_model.service:
            metadata["service"] = request_model.service
        if request_model.host:
            metadata["host"] = request_model.host
        if request_model.source:
            metadata["source"] = request_model.source

        normalized_log = NormalizedLog(
            timestamp=normalize_timestamp(request_model.timestamp or "") or request_model.timestamp,
            level=self._normalize_level(request_model.level),
            service=request_model.service,
            host=request_model.host,
            message=clean_message,
            source=request_model.source,
            metadata=self.redactor.redact_dict(metadata),
            parser_type="structured_input",
            raw=json.dumps(request_model.model_dump(mode="json"), default=str),
        )

        return normalized_log, redaction_result.matches

    def _queue_normalized_payload(self, parsed: dict[str, Any]) -> None:
        payload = QueuePayload(parsed=parsed, metadata=parsed.get("metadata", {}))
        settings = get_settings()
        try:
            redis_client.lpush(
                settings.redis_queue_name,
                json.dumps(payload.model_dump()),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue log: {str(exc)}",
            ) from exc

    @staticmethod
    def _normalize_level(level: str | None) -> str:
        if not level:
            return "INFO"

        normalized = level.upper().strip()
        if normalized == "WARNING":
            return "WARN"
        return normalized if normalized in VALID_LEVELS else "INFO"
