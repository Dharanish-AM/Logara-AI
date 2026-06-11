"""Schemas for legacy, structured, and batch log ingestion."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from utils.service_id import extract_service_id, validate_service_id


class LegacyRawLogIngestRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    log_data: str
    service_id: str | None = None
    service: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_optional_service_id(self):
        if self.model_extra:
            self.metadata = {**self.metadata, **self.model_extra}

        candidate = self.service_id or self.service or self.metadata.get("service_id")
        if candidate is not None:
            service_id = validate_service_id(candidate)
            self.service_id = service_id
            self.service = self.service or service_id
            self.metadata["service_id"] = service_id
            self.metadata.setdefault("service", service_id)

        return self


class StructuredLogIngestRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str | None = None
    level: str | None = None
    service_id: str | None = None
    service: str | None = None
    host: str | None = None
    message: str
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def merge_extra_and_validate_service_id(self):
        if self.model_extra:
            self.metadata = {**self.metadata, **self.model_extra}

        service_id = extract_service_id(
            parsed={
                "service_id": self.service_id,
                "service": self.service,
                "metadata": self.metadata,
            },
            metadata=self.metadata,
        )

        if not service_id:
            raise ValueError("service_id is required for structured log ingestion")

        self.service_id = service_id
        self.service = self.service or service_id
        self.metadata["service_id"] = service_id
        self.metadata.setdefault("service", self.service)

        return self


class BatchLogIngestRequest(BaseModel):
    logs: list[StructuredLogIngestRequest] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_non_empty_batch(self):
        if not self.logs:
            raise ValueError("Batch log payload must contain at least one log")
        return self


class NormalizedLog(BaseModel):
    timestamp: str | None = None
    level: str
    service_id: str
    service: str | None = None
    host: str | None = None
    message: str
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    parser_type: str
    raw: str


class QueuePayload(BaseModel):
    parsed: NormalizedLog | dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


def parse_ingest_request(
    payload: dict[str, Any],
) -> LegacyRawLogIngestRequest | StructuredLogIngestRequest | BatchLogIngestRequest:
    has_logs = "logs" in payload
    has_log_data = "log_data" in payload

    if has_logs and has_log_data:
        raise ValueError("Ambiguous payload: cannot contain both 'logs' and 'log_data'")

    if has_logs:
        return BatchLogIngestRequest.model_validate(payload)

    if has_log_data:
        return LegacyRawLogIngestRequest.model_validate(payload)

    return StructuredLogIngestRequest.model_validate(payload)


def validation_errors_to_detail(exc: ValidationError) -> list[dict[str, Any]]:
    details = []

    for error in exc.errors():
        safe_error = dict(error)
        ctx = safe_error.get("ctx")

        if isinstance(ctx, dict):
            safe_error["ctx"] = {key: str(value) for key, value in ctx.items()}

        details.append(safe_error)

    return details
