"""
Unit tests for SearchService and GET /search.
"""
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import services.search as search_module
from services.search import SearchService
from schemas.search import SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_qdrant_hit(
    id_: str = "abc-123",
    score: float = 0.91,
    payload: dict | None = None,
) -> MagicMock:
    """Build a mock Qdrant ScoredPoint."""
    hit = MagicMock()
    hit.id = id_
    hit.score = score
    # Use explicit None check — empty dict {} is falsy so `payload or {...}`
    # would incorrectly fall through to the default.
    hit.payload = payload if payload is not None else {
        "message": "connection refused on port 5432",
        "level": "ERROR",
        "timestamp": "2026-05-25T10:00:00Z",
        "service_id": "auth-service",
        "metadata": {"host": "prod-01"},
    }
    return hit


# ---------------------------------------------------------------------------
# SearchService unit tests
# ---------------------------------------------------------------------------

class TestSearchService:
    def setup_method(self):
        self.service = SearchService()

    def test_returns_mapped_results(self):
        """Happy path: Qdrant returns hits → mapped to SearchResult list."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.1] * 384
        )
        search_module._qdrant_client.search.return_value = [_make_qdrant_hit()]

        results = self.service.search(query="database connection error")

        assert len(results) == 1
        r = results[0]
        assert isinstance(r, SearchResult)
        assert r.id == "abc-123"
        assert r.score == pytest.approx(0.91)
        assert r.level == "ERROR"
        assert r.service_id == "auth-service"

    def test_empty_qdrant_response_returns_empty_list(self):
        """Qdrant returns no hits → empty list, no exception."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.return_value = []

        results = self.service.search(query="something obscure")

        assert results == []

    def test_service_id_filter_passed_to_qdrant(self):
        """service_id kwarg must be translated into a Qdrant Filter."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.return_value = []

        self.service.search(query="timeout", service_id="payment-service")

        call_kwargs = search_module._qdrant_client.search.call_args[1]
        assert call_kwargs["query_filter"] is not None

        # Verify the filter targets service_id with the correct value
        must_conditions = call_kwargs["query_filter"].must
        assert len(must_conditions) == 1
        assert must_conditions[0].key == "service_id"
        assert must_conditions[0].match.value == "payment-service"

    def test_no_service_id_filter_is_none(self):
        """When service_id is None the filter must not be sent to Qdrant."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.return_value = []

        self.service.search(query="timeout", service_id=None)

        call_kwargs = search_module._qdrant_client.search.call_args[1]
        assert call_kwargs["query_filter"] is None

    def test_whitespace_service_id_treated_as_no_filter(self):
        """Whitespace-only service_id must not generate a filter."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.return_value = []

        self.service.search(query="timeout", service_id="   ")

        call_kwargs = search_module._qdrant_client.search.call_args[1]
        assert call_kwargs["query_filter"] is None

    def test_qdrant_error_propagates(self):
        """Qdrant failure must propagate — the route layer maps it to 503."""
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.side_effect = Exception("connection refused")

        with pytest.raises(Exception, match="connection refused"):
            self.service.search(query="anything")

    def test_payload_defaults_on_missing_fields(self):
        """Missing payload fields must fall back to safe defaults."""
        hit = _make_qdrant_hit(payload={})  # completely empty payload
        search_module._embedding_model.encode.return_value = MagicMock(
            tolist=lambda: [0.0] * 384
        )
        search_module._qdrant_client.search.return_value = [hit]

        results = self.service.search(query="test")

        assert results[0].message == ""
        assert results[0].level == "UNKNOWN"
        assert results[0].timestamp is None
        assert results[0].service_id == "unknown_service"
        assert results[0].metadata == {}


# ---------------------------------------------------------------------------
# GET /search route integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from main import app
    # Use without context manager to skip lifespan (model already mocked
    # by the autouse fixture in conftest.py)
    return TestClient(app, raise_server_exceptions=False)


class TestSearchRoute:
    def test_valid_query_returns_200(self, client):
        with patch("routes.search._service") as mock_svc:
            mock_svc.search.return_value = [
                SearchResult(
                    id="1",
                    score=0.9,
                    message="OOM error",
                    level="ERROR",
                    timestamp="2026-05-25T10:00:00Z",
                    service_id="auth-service",
                    metadata={},
                )
            ]
            response = client.get("/search?query=out+of+memory")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["service_id"] == "auth-service"

    def test_missing_query_param_returns_422(self, client):
        response = client.get("/search")
        assert response.status_code == 422

    def test_limit_too_high_returns_422(self, client):
        response = client.get("/search?query=test&limit=51")
        assert response.status_code == 422

    def test_limit_zero_returns_422(self, client):
        response = client.get("/search?query=test&limit=0")
        assert response.status_code == 422

    def test_qdrant_failure_returns_503(self, client):
        with patch("routes.search._service") as mock_svc:
            mock_svc.search.side_effect = Exception("Qdrant down")
            response = client.get("/search?query=test")

        assert response.status_code == 503

    def test_service_id_forwarded_to_service(self, client):
        with patch("routes.search._service") as mock_svc:
            mock_svc.search.return_value = []
            client.get("/search?query=timeout&service_id=billing")
            mock_svc.search.assert_called_once_with(
                query="timeout", service_id="billing", limit=10
            )

    def test_empty_results_returns_200_empty_list(self, client):
        with patch("routes.search._service") as mock_svc:
            mock_svc.search.return_value = []
            response = client.get("/search?query=nothing")

        assert response.status_code == 200
        assert response.json() == []
