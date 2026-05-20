import json
import logging

from unittest.mock import patch

from worker import (
    process_log,
    run_worker,
    WORKER_METRICS
)


def reset_metrics():
    WORKER_METRICS["processed_logs"] = 0
    WORKER_METRICS["failed_logs"] = 0
    WORKER_METRICS["malformed_payloads"] = 0


def test_process_log_valid_json(caplog):
    reset_metrics()

    caplog.set_level(logging.INFO)

    valid_payload = json.dumps({
        "parsed": {
            "level": "ERROR",
            "message": "Out of memory exception at address 0x1234",
            "parser_type": "structured_json"
        }
    })

    result = process_log(valid_payload)

    assert result is True
    assert WORKER_METRICS["processed_logs"] == 1

    assert (
        "Processed log | level=ERROR | parser=structured_json"
        in caplog.text
    )


def test_process_log_invalid_json(caplog):
    reset_metrics()

    invalid_payload = "{ this is not json"

    result = process_log(invalid_payload)

    assert result is False
    assert WORKER_METRICS["failed_logs"] == 1

    assert "Failed to parse payload as JSON" in caplog.text


def test_process_log_empty_payload(caplog):
    reset_metrics()

    result = process_log("")

    assert result is False
    assert WORKER_METRICS["malformed_payloads"] == 1

    assert "Received empty payload from queue" in caplog.text


def test_process_log_missing_parsed_structure(caplog):
    reset_metrics()

    payload = json.dumps({
        "invalid": "payload"
    })

    result = process_log(payload)

    assert result is False
    assert WORKER_METRICS["malformed_payloads"] == 1

    assert "Payload missing valid 'parsed' structure" in caplog.text


def test_process_log_non_dict_payload(caplog):
    reset_metrics()

    payload = json.dumps(["invalid", "list"])

    result = process_log(payload)

    assert result is False
    assert WORKER_METRICS["malformed_payloads"] == 1

    assert "Received non-dictionary JSON payload" in caplog.text


@patch("worker.process_log")
@patch("worker.redis_client.brpop")
def test_run_worker_single_iteration(mock_brpop, mock_process_log):
    mock_brpop.side_effect = [
        ("log_queue", '{"test": "data"}'),
        KeyboardInterrupt()
    ]

    run_worker()

    assert mock_brpop.call_count == 2

    mock_process_log.assert_called_once_with(
        '{"test": "data"}'
    )