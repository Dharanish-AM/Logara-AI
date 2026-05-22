"""
Schemas for legacy, structured, and batch log ingestion.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class LegacyRawLogIngestRequest(BaseModel):
    log_data: str


class StructuredLogIngestRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str | None = None
    level: str | None = None
    service: str | None = None
    host: str | None = None
    message: str
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def merge_extra_into_metadata(self):
        extra = dict(self.model_extra or {})
        if extra:
            merged_metadata = dict(self.metadata)
            merged_metadata.update(extra)
            self.metadata = merged_metadata
        return self


class BatchLogIngestRequest(BaseModel):
    logs: list[StructuredLogIngestRequest]

    @model_validator(mode="after")
    def validate_non_empty_batch(self):
        if not self.logs:
            raise ValueError("Batch log payload must contain at least one log")
        return self


class NormalizedLog(BaseModel):
    timestamp: str | None = None
    level: str
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


def parse_ingest_request(payload: dict[str, Any]) -> (
    LegacyRawLogIngestRequest | StructuredLogIngestRequest | BatchLogIngestRequest
):
    if "logs" in payload:
        return BatchLogIngestRequest.model_validate(payload)

    if "log_data" in payload:
        return LegacyRawLogIngestRequest.model_validate(payload)

    return StructuredLogIngestRequest.model_validate(payload)


def validation_errors_to_detail(exc: ValidationError) -> list[dict[str, Any]]:
    details = []
    for error in exc.errors():
        safe_error = dict(error)
        ctx = safe_error.get("ctx")
        if isinstance(ctx, dict):
            safe_error["ctx"] = {
                key: str(value) for key, value in ctx.items()
            }
        details.append(safe_error)
    return details
