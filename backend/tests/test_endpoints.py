import httpx
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Logara AI API", "status": "active"}

@patch("main.redis_client.ping")
@patch("services.health.qdrant_client.get_collections")
@patch("services.health.ollama_client.health_check")
def test_health_endpoint_all_healthy(mock_ollama_health, mock_qdrant_get_collections, mock_redis_ping):
    # Redis: ping succeeds (no exception)
    mock_redis_ping.return_value = True

    # Qdrant: get_collections() succeeds
    mock_qdrant_get_collections.return_value = MagicMock()

    # Ollama: returns HTTP 200
    mock_ollama_health.return_value = {"status_code": 200}

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["qdrant"]["status"] == "healthy"
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("services.health.qdrant_client.get_collections")
@patch("services.health.ollama_client.health_check")
def test_health_redis_unhealthy(mock_ollama_health, mock_qdrant_get_collections, mock_redis_ping):
    # Redis: raises ConnectionError
    mock_redis_ping.side_effect = ConnectionError("Redis unreachable")

    # Qdrant: healthy
    mock_qdrant_get_collections.return_value = MagicMock()

    # Ollama: healthy
    mock_ollama_health.return_value = {"status_code": 200}

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["redis"]["status"] == "unhealthy"
    assert "error" in data["services"]["redis"]
    assert data["services"]["qdrant"]["status"] == "healthy"
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("services.health.qdrant_client.get_collections")
@patch("services.health.ollama_client.health_check")
def test_health_qdrant_unhealthy(mock_ollama_health, mock_qdrant_get_collections, mock_redis_ping):
    # Redis: healthy
    mock_redis_ping.return_value = True

    # Qdrant: get_collections() raises Exception
    mock_qdrant_get_collections.side_effect = Exception("Qdrant unreachable")

    # Ollama: healthy
    mock_ollama_health.return_value = {"status_code": 200}

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["qdrant"]["status"] == "unhealthy"
    assert "error" in data["services"]["qdrant"]
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("services.health.qdrant_client.get_collections")
@patch("services.health.ollama_client.health_check")
def test_health_ollama_unhealthy(mock_ollama_health, mock_qdrant_get_collections, mock_redis_ping):
    # Redis: healthy
    mock_redis_ping.return_value = True

    # Qdrant: healthy
    mock_qdrant_get_collections.return_value = MagicMock()

    # Ollama: raises httpx.ConnectError
    mock_ollama_health.side_effect = httpx.ConnectError("Ollama unreachable")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["qdrant"]["status"] == "healthy"
    assert data["services"]["ollama"]["status"] == "unhealthy"
    assert "error" in data["services"]["ollama"]

def test_ingest_empty_log():
    response = client.post("/ingest", json={"log_data": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "Log message cannot be empty"

def test_ingest_whitespace_log():
    response = client.post("/ingest", json={"log_data": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "Log message cannot be empty"

def test_ingest_raw_fallback():
    response = client.post("/ingest", json={"log_data": "this is not standard log format"})
    assert response.status_code == 200
    assert response.json() == {
        "status": "accepted_raw",
        "message": "this is not standard log format"
    }

@patch("utils.queue.redis_client.lpush")
def test_ingest_valid_standard_log(mock_lpush):
    response = client.post("/ingest", json={"log_data": "[2026-05-16 10:30:00] ERROR: auth-service failed"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success_queued"
    assert data["parsed"]["level"] == "ERROR"
    assert data["parsed"]["message"] == "auth-service failed"
    assert data["metadata"]["service"] == "auth-service"


@patch("utils.queue.redis_client.lpush")
def test_ingest_structured_log(mock_lpush):
    response = client.post(
        "/ingest",
        json={
            "timestamp": "2026-05-16 10:30:00",
            "level": "warning",
            "service": "auth-service",
            "host": "host-1",
            "source": "api-gateway",
            "message": "User test@example.com login failed",
            "request_id": "req-123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success_queued"
    assert data["parsed"]["timestamp"] == "2026-05-16T10:30:00"
    assert data["parsed"]["level"] == "WARN"
    assert data["parsed"]["service"] == "auth-service"
    assert data["parsed"]["host"] == "host-1"
    assert data["parsed"]["source"] == "api-gateway"
    assert data["parsed"]["message"] == "User [REDACTED:EMAIL] login failed"
    assert data["metadata"]["request_id"] == "req-123"
    assert data["metadata"]["service"] == "auth-service"
    assert data["redaction_summary"]["EMAIL"] == 1

    queued_payload = mock_lpush.call_args[0][1]
    assert "structured_input" in queued_payload


@patch("utils.queue.redis_client.lpush")
def test_ingest_batch_structured_logs(mock_lpush):
    response = client.post(
        "/ingest",
        json={
            "logs": [
                {
                    "timestamp": "2026-05-16T10:30:00Z",
                    "level": "INFO",
                    "service": "gateway",
                    "message": "Service started",
                },
                {
                    "level": "error",
                    "service": "billing",
                    "message": "Card 4242 4242 4242 4242 declined",
                },
            ]
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_records"] == 2
    assert data["redaction_summary"]["CREDIT_CARD"] == 1
    assert mock_lpush.call_count == 2


def test_ingest_structured_validation_error():
    response = client.post(
        "/ingest",
        json={
            "timestamp": "2026-05-16 10:30:00",
            "level": "INFO",
            "service": "auth-service",
        },
    )
    assert response.status_code == 422


def test_ingest_batch_empty_validation_error():
    response = client.post("/ingest", json={"logs": []})
    assert response.status_code == 422
