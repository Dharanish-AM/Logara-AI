"""Helpers for extracting and validating service-scoped log identifiers."""

from __future__ import annotations

import re
from typing import Any, Mapping

SERVICE_ID_KEYS = (
    "service_id",
    "serviceId",
    "service",
    "service.name",
    "service.namespace",
)

_SERVICE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def normalize_service_id(value: Any) -> str | None:
    if value is None:
        return None

    service_id = str(value).strip()

    if not service_id:
        return None

    if not _SERVICE_ID_RE.fullmatch(service_id):
        return None

    return service_id


def validate_service_id(value: Any) -> str:
    service_id = normalize_service_id(value)

    if not service_id:
        raise ValueError(
            "service_id is required and must contain only letters, numbers, '.', '_', ':', or '-'"
        )

    return service_id


def extract_service_id(
    parsed: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    default: str | None = None,
) -> str | None:
    parsed = parsed or {}
    metadata = metadata or {}

    for key in SERVICE_ID_KEYS:
        service_id = normalize_service_id(parsed.get(key))
        if service_id:
            return service_id

    parsed_metadata = parsed.get("metadata")
    if isinstance(parsed_metadata, Mapping):
        for key in SERVICE_ID_KEYS:
            service_id = normalize_service_id(parsed_metadata.get(key))
            if service_id:
                return service_id

    for key in SERVICE_ID_KEYS:
        service_id = normalize_service_id(metadata.get(key))
        if service_id:
            return service_id

    return normalize_service_id(default)