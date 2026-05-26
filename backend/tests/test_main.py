import json
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

@patch("utils.queue.redis_client.lpush")
def test_ingest_success_queued(mock_lpush):
    # Setup
    test_log = "[2026-05-17 21:16:00] INFO: Database connection established successfully user_id=123"
    
    # Execute
    response = client.post(
        "/ingest",
        json={"log_data": test_log}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success_queued"
    assert data["parsed"]["level"] == "INFO"
    assert data["parsed"]["message"] == "Database connection established successfully user_id=123"
    
    # Verify that lpush was called exactly once on the redis client mock
    mock_lpush.assert_called_once()
    
    # Verify the arguments passed to lpush
    args, kwargs = mock_lpush.call_args
    assert args[0] == "log_queue"
    
    # Check that the payload string pushed into Redis contains the correct data
    payload = json.loads(args[1])
    assert payload["parsed"]["level"] == "INFO"
    assert payload["parsed"]["message"] == "Database connection established successfully user_id=123"

@patch("utils.queue.redis_client.lpush")
def test_ingest_redis_failure(mock_lpush):
    # Setup a mock to simulate Redis connection failure
    mock_lpush.side_effect = Exception("Redis is down")
    
    test_log = "[2026-05-17 21:16:00] INFO: Something happened"
    
    # Execute
    response = client.post(
        "/ingest",
        json={"log_data": test_log}
    )
    
    # Assert
    assert response.status_code == 500
    assert "Failed to queue log" in response.json()["detail"]


@patch("utils.queue.redis_client.lpush")
def test_ingest_structured_redis_failure(mock_lpush):
    mock_lpush.side_effect = Exception("Redis is down")

    response = client.post(
        "/ingest",
        json={
            "timestamp": "2026-05-17 21:16:00",
            "level": "INFO",
            "service": "orders",
            "message": "Something happened",
        }
    )

    assert response.status_code == 500
    assert "Failed to queue log" in response.json()["detail"]

def test_parser_metrics_endpoint():
    response = client.get("/metrics/parser")

    assert response.status_code == 200

    data = response.json()

    assert "parser_metrics" in data