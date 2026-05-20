"""
OTel Ingestion Package

This package contains components for parsing and processing OpenTelemetry (OTLP) payloads.
"""

from utils.otel.logs import parse_otel_log_payload

__all__ = ["parse_otel_log_payload"]
