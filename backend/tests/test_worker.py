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
    assert mock_q_client.upsert.call_count == 2
    first_call = mock_q_client.upsert.call_args_list[0].kwargs
    second_call = mock_q_client.upsert.call_args_list[1].kwargs
    assert first_call["collection_name"] == "log_clusters"
    assert second_call["collection_name"] == "logs"

    first_points = first_call["points"]
    second_points = second_call["points"]
    assert len(first_points) == 1
    assert len(second_points) == 1

    assert first_points[0].payload["service_name"] == "auth-service"
    assert second_points[0].payload["service_id"] == "auth-service"
    assert second_points[0].payload["level"] == "ERROR"
    assert second_points[0].payload["message"] == "Out of memory exception at address 0x1234"
    assert second_points[0].vector == [0.1] * 384


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


@patch("worker.get_settings")
@patch("worker.process_log")
@patch("worker.redis_client.brpop")
def test_run_worker_uses_configured_queue(
    mock_brpop,
    mock_process_log,
    mock_get_settings,
):
    mock_settings = MagicMock()
    mock_settings.redis_queue_name = "custom_queue"

    mock_get_settings.return_value = mock_settings

    mock_brpop.side_effect = [
        ("custom_queue", '{"test": "data"}'),
        KeyboardInterrupt(),
    ]

    run_worker()

    mock_brpop.assert_any_call(
        "custom_queue",
        timeout=1,
    )

    assert mock_brpop.call_count == 2

    mock_process_log.assert_called_once_with(
        '{"test": "data"}'
    )

def test_init_qdrant_collection_creates_index():
    from worker import init_qdrant_collection
    mock_client = MagicMock()
    
    # Test case 1: Collection does not exist
    mock_client.collection_exists.return_value = False
    init_qdrant_collection(mock_client, "test_collection")
    
    mock_client.create_collection.assert_called_once()
    mock_client.create_payload_index.assert_called_once_with(
        collection_name="test_collection",
        field_name="service_id",
        field_schema="keyword"
    )


def test_init_qdrant_collection_already_exists():
    from worker import init_qdrant_collection
    mock_client = MagicMock()
    
    # Test case 2: Collection exists
    mock_client.collection_exists.return_value = True
    init_qdrant_collection(mock_client, "test_collection")
    
    mock_client.create_collection.assert_not_called()
    mock_client.create_payload_index.assert_not_called()