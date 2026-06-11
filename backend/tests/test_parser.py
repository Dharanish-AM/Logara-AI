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

from utils.parser import PARSER_METRICS


def reset_parser_metrics():
    for key in PARSER_METRICS:
        PARSER_METRICS[key] = 0


def test_parser_metrics_standard_log():
    reset_parser_metrics()

    log = "[2026-05-16 10:30:00] INFO: parser metrics test"

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert PARSER_METRICS["parsed_logs"] == 1
    assert PARSER_METRICS["standard_logs"] == 1


def test_parser_metrics_failed_log():
    reset_parser_metrics()

    LogParser.parse_line("invalid parser format")

    assert PARSER_METRICS["failed_logs"] == 1


def test_parser_metrics_empty_log():
    reset_parser_metrics()

    LogParser.parse_line("")

    assert PARSER_METRICS["empty_logs"] == 1
    assert PARSER_METRICS["failed_logs"] == 1


def test_parser_metrics_structured_json():
    reset_parser_metrics()

    log = """
    {
        "timestamp": "2026-05-16T10:30:00Z",
        "level": "INFO",
        "message": "json metrics test"
    }
    """

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert PARSER_METRICS["structured_json_logs"] == 1
    assert PARSER_METRICS["parsed_logs"] == 1


def test_timestamp_failure_metric():
    reset_parser_metrics()

    log = "[invalid-timestamp] INFO: timestamp failure"

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert PARSER_METRICS["timestamp_failures"] == 1


def test_parser_metrics_increment():
    reset_parser_metrics()

    log = "[2026-05-16 10:30:00] ERROR: auth-service failed"

    LogParser.parse_line(log)

    assert PARSER_METRICS["parsed_logs"] == 1
    assert PARSER_METRICS["standard_logs"] == 1


def test_failed_log_metrics_increment():
    reset_parser_metrics()

    LogParser.parse_line("invalid log format")

    assert PARSER_METRICS["failed_logs"] == 1


def test_empty_log_metrics_increment():
    reset_parser_metrics()

    LogParser.parse_line("")

    assert PARSER_METRICS["empty_logs"] == 1
    assert PARSER_METRICS["failed_logs"] == 1


def test_epoch_timestamp_normalization():
    log = """
    {
        "timestamp": "1716746096",
        "level": "INFO",
        "message": "epoch timestamp event"
    }
    """

    parsed = LogParser.parse_line(log)

    assert parsed is not None
    assert parsed["timestamp"] == "2024-05-26T17:54:56+00:00"
