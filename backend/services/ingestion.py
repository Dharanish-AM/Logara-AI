"""Ingestion service for raw, structured, batch, and OTLP log payloads."""

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
from utils.service_id import extract_service_id
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

    # ---------------------------
    # 🔥 NEW FEATURE ADDED HERE
    # ---------------------------
    def format_ai_response(self, message: str) -> dict:
        """
        Convert raw log into structured AI explanation format
        """
        return {
            "Problem Summary": f"Detected issue in logs: {message[:120]}",
            "Possible Cause": "System error, timeout, invalid request, or service failure.",
            "Affected Component": "Backend ingestion pipeline / API / service layer",
            "Suggested Fix": "Check logs, validate input, monitor service health, and retry request."
        }

    def ingest_request(
        self,
        request_model: LegacyRawLogIngestRequest
        | StructuredLogIngestRequest
        | BatchLogIngestRequest,
    ) -> dict[str, Any]:
        if isinstance(request_model, LegacyRawLogIngestRequest):
            return self.ingest_raw_log(
                request_model.log_data,
                service_id=request_model.service_id,
                metadata=request_model.metadata,
            )

        if isinstance(request_model, BatchLogIngestRequest):
            return self.ingest_batch_logs(request_model.logs)

        return self.ingest_structured_log(request_model)

    def ingest_raw_log(
        self,
        log_data: str,
        service_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not log_data or not log_data.strip():
            raise HTTPException(status_code=400, detail="Log message cannot be empty")

        base_metadata = dict(metadata or {})
        if service_id:
            base_metadata["service_id"] = service_id
            base_metadata.setdefault("service", service_id)

        redaction_result = self.redactor.redact_with_summary(log_data)
        clean_log = redaction_result.text
        parsed = LogParser.parse_line(clean_log)

        # ---------------- RAW FALLBACK ----------------
        if not parsed:
            final_service_id = extract_service_id(
                metadata=base_metadata,
                default="unknown_service",
            )

            base_metadata["service_id"] = final_service_id
            base_metadata.setdefault("service", final_service_id)

            raw_payload = {
                "timestamp": None,
                "level": "INFO",
                "service_id": final_service_id,
                "service": final_service_id,
                "message": clean_log,
                "metadata": self.redactor.redact_dict(base_metadata),
                "parser_type": "raw_input",
                "raw": clean_log,
            }

            self._queue_normalized_payload(raw_payload)

            structured_output = self.format_ai_response(clean_log)

            return {
                "status": "accepted_raw_queued",
                "message": clean_log,
                "structured_output": structured_output,
                "redaction_summary": redaction_result.matches,
            }

        parsed_metadata = parsed.get("metadata", {})
        if not isinstance(parsed_metadata, dict):
            parsed_metadata = {}

        merged_metadata = {**parsed_metadata, **base_metadata}
        final_service_id = extract_service_id(
            parsed=parsed,
            metadata=merged_metadata,
            default="unknown_service",
        )

        merged_metadata["service_id"] = final_service_id
        merged_metadata.setdefault("service", final_service_id)

        parsed["service_id"] = final_service_id
        parsed["service"] = parsed.get("service") or merged_metadata.get("service")
        parsed["metadata"] = self.redactor.redact_dict(merged_metadata)
        parsed = self.redactor.redact_dict(parsed)

        self._queue_normalized_payload(parsed)

        structured_output = self.format_ai_response(clean_log)

        return {
            "status": "success_queued",
            "parsed": parsed,
            "structured_output": structured_output,
            "metadata": parsed["metadata"],
            "redaction_summary": redaction_result.matches,
        }

    def ingest_structured_log(
        self,
        request_model: StructuredLogIngestRequest,
    ) -> dict[str, Any]:
        normalized_log, redaction_summary = self._normalize_structured_log(request_model)
        self._queue_normalized_payload(normalized_log.model_dump())

        structured_output = self.format_ai_response(normalized_log.message)

        return {
            "status": "success_queued",
            "parsed": normalized_log.model_dump(),
            "structured_output": structured_output,
            "metadata": normalized_log.metadata,
            "redaction_summary": redaction_summary,
        }

    def ingest_batch_logs(
        self,
        logs: list[StructuredLogIngestRequest],
    ) -> dict[str, Any]:
        processed_records = 0
        failed_records = 0
        failures: list[dict[str, Any]] = []
        total_redaction_summary: dict[str, int] = {}

        for index, log in enumerate(logs):
            try:
                normalized_log, redaction_summary = (
                    self._normalize_structured_log(log)
                )

                self._queue_normalized_payload(
                    normalized_log.model_dump()
                )

                processed_records += 1

                for key, value in redaction_summary.items():
                    total_redaction_summary[key] = (
                        total_redaction_summary.get(key, 0) + value
                    )

            except Exception as exc:
                failed_records += 1
                failures.append({
                    "record_index": index,
                    "error": str(exc),
                })

        status = (
            "success"
            if failed_records == 0
            else "partial_success"
        )

        return {
            "status": status,
            "processed_records": processed_records,
            "failed_records": failed_records,
            "failures": failures,
            "redaction_summary": total_redaction_summary,
            "fallback_used": False,
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
                "message": "No logs found in payload",
                "processed_records": 0,
                "redaction_summary": {},
                "fallback_used": True,
            }

        queued_count = 0
        total_redaction_matches: dict[str, int] = {}

        for record in records:
            record_metadata = record.get("metadata", {})
            if not isinstance(record_metadata, dict):
                record_metadata = {}

            final_service_id = extract_service_id(
                parsed=record,
                metadata=record_metadata,
                default="unknown_service",
            )

            record_metadata["service_id"] = final_service_id
            record_metadata.setdefault("service", final_service_id)

            record["service_id"] = final_service_id
            record["service"] = record.get("service") or record_metadata.get("service")
            record["metadata"] = record_metadata

            redact_res = self.redactor.redact_with_summary(record["message"])

            record["message"] = redact_res.text
            record["raw"] = redact_res.text

            for label, count in redact_res.matches.items():
                total_redaction_matches[label] = (
                    total_redaction_matches.get(label, 0) + count
                )

            record = self.redactor.redact_dict(record)

            self._queue_normalized_payload(record)

            queued_count += 1

        return {
            "status": "success",
            "message": "OTel logs processed successfully",
            "processed_records": queued_count,
            "redaction_summary": total_redaction_matches,
            "fallback_used": False,
        }

    def _normalize_structured_log(
        self,
        request_model: StructuredLogIngestRequest,
    ) -> tuple[NormalizedLog, dict[str, int]]:
        if not request_model.message or not request_model.message.strip():
            raise HTTPException(
                status_code=400,
                detail="Log message cannot be empty",
            )

        redaction_result = self.redactor.redact_with_summary(
            request_model.message
        )

        clean_message = redaction_result.text

        service_id = request_model.service_id
        metadata = dict(request_model.metadata)
        metadata["service_id"] = service_id
        metadata.setdefault("service", request_model.service or service_id)

        if request_model.host:
            metadata["host"] = request_model.host

        if request_model.source:
            metadata["source"] = request_model.source

        normalized_log = NormalizedLog(
            timestamp=normalize_timestamp(request_model.timestamp or "")
            or request_model.timestamp,
            level=self._normalize_level(request_model.level),
            service_id=service_id,
            service=request_model.service or service_id,
            host=request_model.host,
            message=clean_message,
            source=request_model.source,
            metadata=self.redactor.redact_dict(metadata),
            parser_type="structured_input",
            raw=json.dumps(
                request_model.model_dump(mode="json"),
                default=str,
            ),
        )

        return normalized_log, redaction_result.matches

    def _queue_normalized_payload(self, parsed: dict[str, Any]) -> None:
        metadata = parsed.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}

        payload = QueuePayload(parsed=parsed, metadata=metadata)
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
