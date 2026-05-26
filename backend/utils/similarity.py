"""Similarity utilities for semantic duplicate detection."""

from __future__ import annotations

import json
import math
import re
from typing import Any

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b"
)
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_NUMBER_RE = re.compile(r"\b\d+\b")
_WHITESPACE_RE = re.compile(r"\s+")


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for two equal-length numeric vectors."""
    if not left or not right or len(left) != len(right):
        return 0.0

    dot_product = sum(x * y for x, y in zip(left, right))
    left_norm = math.sqrt(sum(x * x for x in left))
    right_norm = math.sqrt(sum(y * y for y in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return max(0.0, min(1.0, dot_product / (left_norm * right_norm)))


def normalize_vector(vector: list[float] | tuple[float, ...] | Any) -> list[float]:
    """Return a normalized vector suitable for cosine-based search."""
    if not vector:
        return []

    values = [float(value) for value in vector if value is not None]
    if not values:
        return []

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values

    return [value / norm for value in values]


def normalize_log_text(text: Any, *, metadata: dict[str, Any] | None = None) -> str:
    """Normalize log text to reduce drift from IDs, timestamps, and formatting."""
    metadata = metadata or {}

    if text is None:
        text = ""

    if isinstance(text, (dict, list)):
        try:
            text = json.dumps(text, sort_keys=True, default=str)
        except TypeError:
            text = str(text)

    text = str(text).strip()

    if not text and metadata:
        text = json.dumps(metadata, sort_keys=True, default=str)

    if not text:
        return ""

    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                message = parsed.get("message") or parsed.get("msg") or parsed.get("content")
                if message:
                    text = str(message)
                else:
                    text = json.dumps(parsed, sort_keys=True, default=str)
        except json.JSONDecodeError:
            pass

    text = _UUID_RE.sub("<uuid>", text)
    text = _TIMESTAMP_RE.sub("<timestamp>", text)
    text = _IP_RE.sub("<ip>", text)
    text = _EMAIL_RE.sub("<email>", text)
    text = _NUMBER_RE.sub("<number>", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text


def build_semantic_log_text(
    message: str | None,
    level: str | None = None,
    service_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Create a robust semantic text payload for embedding and clustering."""
    components: list[str] = []

    if level:
        components.append(f"level={level}")

    if service_name:
        components.append(f"service={service_name}")

    if message:
        components.append(str(message))

    if metadata:
        metadata_text = json.dumps(metadata, sort_keys=True, default=str)
        if metadata_text:
            components.append(metadata_text)

    combined = " ".join(filter(None, components))
    return normalize_log_text(combined, metadata=metadata or {})
