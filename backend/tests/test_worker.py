import json
import logging
from unittest.mock import patch, MagicMock

import pytest
from worker import (
    process_log,
    run_worker,
    WORKER_METRICS
)


def reset_metrics():
    WORKER_METRICS["processed_logs"] = 0
    WORKER_METRICS["failed_logs"] = 0
    WORKER_METRICS["malformed_payloads"] = 0


@patch("worker.get_qdrant_client")
@patch("worker.get_embedding_model")
def test_process_log_valid_json(mock_get_model, mock_get_qdrant, caplog):
    reset_metrics()
    caplog.set_level(logging.INFO)

    # Mock SentenceTransformer encode returning a vector
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    mock_get_model.return_value = mock_model

    # Mock Qdrant client methods
    mock_q_client = MagicMock()
    mock_get_qdrant.return_value = mock_q_client

    valid_payload = json.dumps({
        "parsed": {
            "level": "ERROR",
            "message": "Out of memory exception at address 0x1234",
            "parser_type": "structured_json",
            "timestamp": "2026-05-16T10:30:00Z"
        },
        "metadata": {
            "service": "auth-service"
        }
    })

    result = process_log(valid_payload)

    assert result is True
    assert WORKER_METRICS["processed_logs"] == 1

    assert (
        "Processing log | level=ERROR | parser=structured_json"
        in caplog.text
    )
    assert "Successfully vectorized and indexed log to Qdrant" in caplog.text

    # Verify Qdrant upsert parameters
    mock_q_client.upsert.assert_called_once()
    kwargs = mock_q_client.upsert.call_args[1]
    assert kwargs["collection_name"] == "logs"
    points = kwargs["points"]
    assert len(points) == 1
    point = points[0]
    assert point.payload["service_id"] == "auth-service"
    assert point.payload["level"] == "ERROR"
    assert point.payload["message"] == "Out of memory exception at address 0x1234"
    assert point.vector == [0.1] * 384


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


@patch("worker.get_qdrant_client")
@patch("worker.get_embedding_model")
def test_process_log_embedding_failure(mock_get_model, mock_get_qdrant, caplog):
    reset_metrics()
    caplog.set_level(logging.ERROR)

    # Force embedding exception
    mock_model = MagicMock()
    mock_model.encode.side_effect = Exception("Model model loading error")
    mock_get_model.return_value = mock_model

    payload = json.dumps({
        "parsed": {
            "level": "INFO",
            "message": "some log message",
            "parser_type": "standard"
        }
    })

    result = process_log(payload)
    assert result is False
    assert WORKER_METRICS["failed_logs"] == 1
    assert "Failed to generate embedding" in caplog.text


@patch("worker.get_qdrant_client")
@patch("worker.get_embedding_model")
def test_process_log_qdrant_failure(mock_get_model, mock_get_qdrant, caplog):
    reset_metrics()
    caplog.set_level(logging.ERROR)

    # Mock encoder successfully
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    mock_get_model.return_value = mock_model

    # Force Qdrant connection exception
    mock_q_client = MagicMock()
    mock_q_client.upsert.side_effect = Exception("Qdrant write timeout")
    mock_get_qdrant.return_value = mock_q_client

    payload = json.dumps({
        "parsed": {
            "level": "INFO",
            "message": "some log message",
            "parser_type": "standard"
        }
    })

    result = process_log(payload)
    assert result is False
    assert WORKER_METRICS["failed_logs"] == 1
    assert "Failed to store log in Qdrant" in caplog.text


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