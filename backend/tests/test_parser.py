"""
test_parser.py - Unit tests for the LogParser orchestration system.
"""

from utils.parser import LogParser


def test_standard_log_parsing():
    log = "[2026-05-16 10:30:00] ERROR: auth-service failed"

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["level"] == "ERROR"
    assert parsed["message"] == "auth-service failed"
    assert parsed["parser_type"] == "standard"


def test_empty_log_returns_none():
    parsed = LogParser.parse_line("")

    assert parsed is None


def test_invalid_log_returns_none():
    log = "this is not a valid log format"

    parsed = LogParser.parse_line(log)

    assert parsed is None


def test_timestamp_normalization():
    log = "[2026-05-16 14:24:49] INFO: service started"

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["timestamp"] == "2026-05-16T14:24:49"


def test_iso_timestamp_normalization():
    log = "[2026-05-16T14:24:49] INFO: service started"

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["timestamp"] == "2026-05-16T14:24:49"


def test_zulu_timestamp_normalization():
    log = '[2026-05-16T14:24:49Z] INFO: deployment completed'

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    # Z is normalized to +00:00 for ISO 8601 compliance
    assert parsed["timestamp"] == "2026-05-16T14:24:49+00:00"


def test_json_structured_log_parsing():
    log = """
    {
        "timestamp": "2026-05-16T10:30:00Z",
        "level": "error",
        "message": "payment-service timeout",
        "request_id": "abc123"
    }
    """

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["parser_type"] == "structured_json"
    assert parsed["level"] == "ERROR"
    assert parsed["message"] == "payment-service timeout"
    assert parsed["metadata"]["request_id"] == "abc123"


def test_malformed_json_returns_none():
    log = '{"timestamp":"2026","level":"INFO",'

    parsed = LogParser.parse_line(log)

    assert parsed is None


def test_unknown_log_level_defaults_to_info():
    log = """
    {
        "timestamp": "2026-05-16T10:30:00Z",
        "level": "TRACE",
        "message": "trace event"
    }
    """

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["level"] == "INFO"


def test_warning_level_normalization():
    log = """
    {
        "timestamp": "2026-05-16T10:30:00Z",
        "level": "WARNING",
        "message": "memory usage high"
    }
    """

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["level"] == "WARN"