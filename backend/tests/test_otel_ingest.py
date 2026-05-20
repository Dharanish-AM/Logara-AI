import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from utils.otel.logs import (
    parse_any_value,
    parse_attributes,
    severity_number_to_text,
    parse_time,
    parse_otel_log_payload,
)

client = TestClient(app)


def test_parse_any_value_primitives():
    assert parse_any_value({"stringValue": "hello"}) == "hello"
    assert parse_any_value({"boolValue": True}) is True
    assert parse_any_value({"intValue": "123"}) == 123
    assert parse_any_value({"doubleValue": "12.34"}) == 12.34
    assert parse_any_value("raw_string") == "raw_string"


def test_parse_any_value_nested():
    # Array
    arr_val = {
        "arrayValue": {
            "values": [
                {"stringValue": "val1"},
                {"intValue": "42"}
            ]
        }
    }
    assert parse_any_value(arr_val) == ["val1", 42]

    # Kvlist
    kv_val = {
        "kvlistValue": {
            "values": [
                {"key": "name", "value": {"stringValue": "logara"}},
                {"key": "active", "value": {"boolValue": True}}
            ]
        }
    }
    assert parse_any_value(kv_val) == {"name": "logara", "active": True}


def test_severity_number_to_text():
    assert severity_number_to_text(1) == "TRACE"
    assert severity_number_to_text(4) == "TRACE"
    assert severity_number_to_text(5) == "DEBUG"
    assert severity_number_to_text(8) == "DEBUG"
    assert severity_number_to_text(9) == "INFO"
    assert severity_number_to_text(12) == "INFO"
    assert severity_number_to_text(13) == "WARN"
    assert severity_number_to_text(16) == "WARN"
    assert severity_number_to_text(17) == "ERROR"
    assert severity_number_to_text(20) == "ERROR"
    assert severity_number_to_text(21) == "FATAL"
    assert severity_number_to_text(24) == "FATAL"
    assert severity_number_to_text(99) == "INFO"  # default out-of-bounds
    assert severity_number_to_text("invalid") == "INFO"  # parsing exception fallback


def test_parse_time():
    # Valid timestamp conversion: 1682124012 seconds (in nano: 1682124012000000000)
    # 1682124012 corresponds to 2023-04-22T00:40:12Z
    ts = parse_time(1682124012000000000)
    assert "2023-04-22T00:40:12" in ts
    
    # Missing / None fallback
    ts_none = parse_time(None)
    assert ts_none.endswith("Z")

    # Invalid timestamp fallback
    ts_invalid = parse_time("not-a-number")
    assert ts_invalid.endswith("Z")


def test_parse_otel_log_payload_full():
    otel_payload = {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "auth-service"}},
                        {"key": "env", "value": {"stringValue": "production"}}
                    ]
                },
                "scopeLogs": [
                    {
                        "logRecords": [
                            {
                                "timeUnixNano": "1682124012000000000",
                                "severityNumber": 17,
                                "severityText": "ERROR",
                                "body": {"stringValue": "Database connection failed"},
                                "attributes": [
                                    {"key": "db.system", "value": {"stringValue": "postgresql"}},
                                    {"key": "env", "value": {"stringValue": "staging"}}  # Record attribute overrides resource attribute
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    records = parse_otel_log_payload(otel_payload)
    assert len(records) == 1
    rec = records[0]
    
    assert rec["level"] == "ERROR"
    assert "2023-04-22" in rec["timestamp"]
    assert rec["message"] == "Database connection failed"
    assert rec["parser_type"] == "otlp_log"
    assert rec["raw"] == "Database connection failed"
    
    # Check attributes merged
    assert rec["metadata"]["db.system"] == "postgresql"
    assert rec["metadata"]["env"] == "staging"
    assert rec["metadata"]["service"] == "auth-service"


def test_parse_otel_log_payload_regex_parsing():
    # If the OTel body itself follows the standard Logara pattern: [timestamp] LEVEL: message
    # We test that LogParser parses it and extracts metadata.
    otel_payload = {
        "resourceLogs": [
            {
                "scopeLogs": [
                    {
                        "logRecords": [
                            {
                                "body": {"stringValue": "[2026-05-16 10:30:00] ERROR: payment-service failed"},
                            }
                        ]
                    }
                ]
            }
        ]
    }
    records = parse_otel_log_payload(otel_payload)
    assert len(records) == 1
    rec = records[0]
    
    assert rec["level"] == "ERROR"
    assert rec["message"] == "payment-service failed"
    assert rec["metadata"]["service"] == "payment-service"
    assert rec["parser_type"] == "standard"


@patch("main.redis_client.lpush")
def test_ingest_otel_logs_endpoint_success(mock_lpush):
    payload = {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "gateway"}}
                    ]
                },
                "scopeLogs": [
                    {
                        "logRecords": [
                            {
                                "timeUnixNano": "1682124012000000000",
                                "severityText": "INFO",
                                # Include email to test redaction
                                "body": {"stringValue": "User test@example.com logged in successfully"},
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    response = client.post("/v1/logs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_records"] == 1
    assert data["redaction_summary"]["EMAIL"] == 1

    # Verify Redis push payload contains the redacted message and standard format
    assert mock_lpush.called
    called_args = mock_lpush.call_args[0]
    assert called_args[0] == "log_queue"
    
    queued_payload = json.loads(called_args[1])
    assert queued_payload["parsed"]["message"] == "User [REDACTED:EMAIL] logged in successfully"
    assert queued_payload["parsed"]["metadata"]["service"] == "gateway"


def test_ingest_otel_logs_empty_payload():
    response = client.post("/v1/logs", json={})
    assert response.status_code == 400
