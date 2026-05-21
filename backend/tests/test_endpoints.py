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
@patch("main.QdrantClient")
@patch("main.httpx.get")
def test_health_endpoint_all_healthy(mock_httpx, mock_qdrant, mock_redis_ping):
    # Redis: ping succeeds (no exception)
    mock_redis_ping.return_value = True

    # Qdrant: client instantiates and get_collections() succeeds
    mock_qdrant_instance = MagicMock()
    mock_qdrant.return_value = mock_qdrant_instance

    # Ollama: returns HTTP 200
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx.return_value = mock_response

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["qdrant"]["status"] == "healthy"
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("main.QdrantClient")
@patch("main.httpx.get")
def test_health_redis_unhealthy(mock_httpx, mock_qdrant, mock_redis_ping):
    # Redis: raises ConnectionError
    mock_redis_ping.side_effect = ConnectionError("Redis unreachable")

    # Qdrant: healthy
    mock_qdrant_instance = MagicMock()
    mock_qdrant.return_value = mock_qdrant_instance

    # Ollama: healthy
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx.return_value = mock_response

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["redis"]["status"] == "unhealthy"
    assert "error" in data["services"]["redis"]
    assert data["services"]["qdrant"]["status"] == "healthy"
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("main.QdrantClient")
@patch("main.httpx.get")
def test_health_qdrant_unhealthy(mock_httpx, mock_qdrant, mock_redis_ping):
    # Redis: healthy
    mock_redis_ping.return_value = True

    # Qdrant: get_collections() raises Exception
    mock_qdrant_instance = MagicMock()
    mock_qdrant_instance.get_collections.side_effect = Exception("Qdrant unreachable")
    mock_qdrant.return_value = mock_qdrant_instance

    # Ollama: healthy
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx.return_value = mock_response

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["redis"]["status"] == "healthy"
    assert data["services"]["qdrant"]["status"] == "unhealthy"
    assert "error" in data["services"]["qdrant"]
    assert data["services"]["ollama"]["status"] == "healthy"


@patch("main.redis_client.ping")
@patch("main.QdrantClient")
@patch("main.httpx.get")
def test_health_ollama_unhealthy(mock_httpx, mock_qdrant, mock_redis_ping):
    # Redis: healthy
    mock_redis_ping.return_value = True

    # Qdrant: healthy
    mock_qdrant_instance = MagicMock()
    mock_qdrant.return_value = mock_qdrant_instance

    # Ollama: raises httpx.ConnectError
    mock_httpx.side_effect = httpx.ConnectError("Ollama unreachable")

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


@patch("main.log_service.get_logs")
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


@patch("main.log_service.semantic_search")
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

