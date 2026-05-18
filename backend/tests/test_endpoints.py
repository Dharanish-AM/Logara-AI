from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Logara AI API", "status": "active"}

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

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
