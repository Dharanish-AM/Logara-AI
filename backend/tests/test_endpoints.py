import httpx
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Logara AI API", "status": "active"}

@patch("services.health.redis_client.ping")
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


@patch("services.health.redis_client.ping")
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


@patch("services.health.redis_client.ping")
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


@patch("services.health.redis_client.ping")
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

@patch("utils.queue.redis_client.lpush")
def test_ingest_raw_fallback(mock_lpush):
    response = client.post("/ingest", json={"log_data": "this is not standard log format"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "accepted_raw_queued"
    assert res_data["message"] == "this is not standard log format"
    assert res_data["redaction_summary"] == {}
    assert "structured_output" in res_data
    mock_lpush.assert_called_once()

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


# ============================================================================
# Retrieval and Semantic Search Endpoints Tests
# ============================================================================

@patch("routes.retrieval.LogService.get_logs")
def test_get_logs_success(mock_get_logs):
    mock_get_logs.return_value = (
        [
            {
                "id": "1",
                "timestamp": "2026-05-16T10:30:00",
                "level": "ERROR",
                "message": "auth-service failed",
                "parser_type": "standard",
                "raw": "[2026-05-16 10:30:00] ERROR: auth-service failed",
                "metadata": {"service": "auth-service"}
            }
        ],
        1
    )

    response = client.get("/logs?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 1
    assert data["logs"][0]["id"] == "1"
    assert data["logs"][0]["level"] == "ERROR"
    assert data["pagination"]["total"] == 1
    assert data["pagination"]["pages"] == 1


def test_get_logs_invalid_pagination():
    response = client.get("/logs?page=0&limit=10")
    assert response.status_code == 400
    assert "Page number must be 1 or greater" in response.json()["detail"]

    response = client.get("/logs?page=1&limit=101")
    assert response.status_code == 400
    assert "Limit must be between 1 and 100" in response.json()["detail"]


@patch("routes.retrieval.LogService.semantic_search")
def test_semantic_search_success(mock_semantic_search):
    mock_semantic_search.return_value = (
        [
            {
                "id": "1",
                "timestamp": "2026-05-16T10:30:00",
                "level": "ERROR",
                "message": "auth-service failed",
                "parser_type": "standard",
                "raw": "[2026-05-16 10:30:00] ERROR: auth-service failed",
                "metadata": {"service": "auth-service"}
            }
        ],
        "The authentication service failed to start."
    )

    response = client.post("/search", json={"query": "auth failed", "limit": 5})
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 1
    assert data["logs"][0]["id"] == "1"
    assert data["answer"] == "The authentication service failed to start."


def test_semantic_search_empty_query():
    response = client.post("/search", json={"query": ""})
    assert response.status_code == 400
    assert "Search query cannot be empty" in response.json()["detail"]

@patch("integrations.redis.redis_client.lpush")
def test_batch_ingestion_partial_success(mock_lpush):
    payload = {
        "logs": [
            {
                "timestamp": "2026-05-20T10:00:00Z",
                "level": "INFO",
                "message": "valid log entry",
            },
            {
                "timestamp": "2026-05-20T10:01:00Z",
                "level": "INFO",
                "message": "",
            },
        ]
    }

    response = client.post(
        "/ingest",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "partial_success"
    assert data["processed_records"] == 1
    assert data["failed_records"] == 1

    assert len(data["failures"]) == 1
    assert data["failures"][0]["record_index"] == 1

@patch("integrations.redis.redis_client.lpush")
def test_batch_ingestion_full_success(mock_lpush):
    payload = {
        "logs": [
            {
                "timestamp": "2026-05-20T10:00:00Z",
                "level": "INFO",
                "message": "service started",
            },
            {
                "timestamp": "2026-05-20T10:01:00Z",
                "level": "ERROR",
                "message": "database timeout",
            },
        ]
    }

    response = client.post(
        "/ingest",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["processed_records"] == 2
    assert data["failed_records"] == 0
    assert data["failures"] == []
