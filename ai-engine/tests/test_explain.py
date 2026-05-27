"""
Unit tests for ExplainService and POST /explain.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from schemas.explain import ExplainRequest, ExplainResponse
from schemas.search import SearchResult
from services.explain import ExplainService, _build_prompt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context_log(**kwargs) -> SearchResult:
    defaults = dict(
        id="log-1",
        score=0.88,
        message="database connection pool exhausted",
        level="ERROR",
        timestamp="2026-05-25T09:55:00Z",
        service_id="auth-service",
        metadata={},
    )
    defaults.update(kwargs)
    return SearchResult(**defaults)


def _mock_search_service(logs: list[SearchResult]) -> MagicMock:
    svc = MagicMock()
    svc.search.return_value = logs
    return svc


def _mock_incident_memory_service(result=None) -> MagicMock:
    svc = MagicMock()
    svc.search_similar_incident.return_value = result
    svc.store_incident = MagicMock()
    return svc


def _make_async_ollama_mock(response_text: str = "Root cause: DB pool exhausted."):
    """Return a patched httpx.AsyncClient context manager that returns a
    successful Ollama /api/generate response."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": response_text}
    mock_response.raise_for_status = MagicMock()  # no-op

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


# ---------------------------------------------------------------------------
# _build_prompt pure-function tests
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_contains_error_message(self):
        prompt = _build_prompt("OOM at 0x1234", [])
        assert "OOM at 0x1234" in prompt

    def test_no_context_logs_skips_context_section(self):
        prompt = _build_prompt("error", [])
        assert "Context logs" not in prompt

    def test_context_logs_numbered_and_present(self):
        logs = [_make_context_log(message="msg-a"), _make_context_log(message="msg-b")]
        prompt = _build_prompt("error", logs)
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "msg-a" in prompt
        assert "msg-b" in prompt

    def test_service_id_included_in_context(self):
        logs = [_make_context_log(service_id="payment-service")]
        prompt = _build_prompt("error", logs)
        assert "payment-service" in prompt


# ---------------------------------------------------------------------------
# ExplainService unit tests
# ---------------------------------------------------------------------------


class TestExplainService:
    @pytest.mark.asyncio
    async def test_happy_path_returns_explanation(self):
        """Full pipeline: search → prompt → Ollama → ExplainResponse."""
        context = [_make_context_log()]
        mock_search = _mock_search_service(context)
        mock_http_client = _make_async_ollama_mock("Root cause: DB pool exhausted.")

        with patch("services.explain.httpx.AsyncClient", return_value=mock_http_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            result = await service.explain(
                ExplainRequest(
                    error_message="connection refused", service_id="auth-service"
                )
            )

        assert isinstance(result, ExplainResponse)
        assert result.explanation == "Root cause: DB pool exhausted."
        assert result.context_logs == context
        assert result.model  # model name populated from settings

    @pytest.mark.asyncio
    async def test_search_service_called_with_request_params(self):
        """service_id and context_limit must be forwarded to SearchService."""
        mock_search = _mock_search_service([])
        mock_http_client = _make_async_ollama_mock()

        with patch("services.explain.httpx.AsyncClient", return_value=mock_http_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            await service.explain(
                ExplainRequest(
                    error_message="timeout",
                    service_id="billing",
                    context_limit=3,
                )
            )

        mock_search.search.assert_called_once_with(
            query="timeout",
            service_id="billing",
            limit=3,
        )

    @pytest.mark.asyncio
    async def test_uses_cached_incident_without_calling_ollama(self):
        """
        If a highly similar incident already exists in memory,
        ExplainService should reuse the cached explanation
        and skip Ollama generation.
        """

        cached_incident = MagicMock()
        cached_incident.score = 0.96
        cached_incident.explanation = "Cached RCA explanation"

        mock_memory = _mock_incident_memory_service(cached_incident)

        with patch("services.explain.httpx.AsyncClient.post") as mock_post:

            service = ExplainService(
                search_service=_mock_search_service([]),
                incident_memory_service=mock_memory,
            )

            result = await service.explain(
                ExplainRequest(error_message="database timeout")
            )

        assert result.explanation == "Cached RCA explanation"

        mock_memory.search_similar_incident.assert_called_once()

        # MOST IMPORTANT ASSERTION
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_ollama_and_stores_incident(self):
        """
        If no similar incident exists,
        Ollama should generate a fresh explanation
        and the result should be stored in incident memory.
        """

        mock_memory = _mock_incident_memory_service(None)

        mock_http_client = _make_async_ollama_mock("Fresh RCA explanation")

        with patch(
            "services.explain.httpx.AsyncClient",
            return_value=mock_http_client,
        ):

            service = ExplainService(
                search_service=_mock_search_service([]),
                incident_memory_service=mock_memory,
            )

            result = await service.explain(
                ExplainRequest(error_message="redis connection refused")
            )

        assert result.explanation == "Fresh RCA explanation"

        mock_memory.store_incident.assert_called_once()

    @pytest.mark.asyncio
    async def test_low_similarity_does_not_use_cache(self):
        """
        Cached incidents below the similarity threshold
        should not bypass Ollama generation.
        """

        cached_incident = MagicMock()
        cached_incident.score = 0.72
        cached_incident.explanation = "Old unrelated explanation"

        mock_memory = _mock_incident_memory_service(cached_incident)

        mock_http_client = _make_async_ollama_mock("Fresh explanation from Ollama")

        with patch(
            "services.explain.httpx.AsyncClient",
            return_value=mock_http_client,
        ):

            service = ExplainService(
                search_service=_mock_search_service([]),
                incident_memory_service=mock_memory,
            )

            result = await service.explain(
                ExplainRequest(error_message="new unseen failure")
            )

        assert result.explanation == "Fresh explanation from Ollama"

        mock_memory.store_incident.assert_called_once()

    @pytest.mark.asyncio
    async def test_ollama_connect_error_propagates(self):
        """ConnectError from Ollama must propagate (route maps it to 503)."""
        mock_search = _mock_search_service([])
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("services.explain.httpx.AsyncClient", return_value=mock_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            with pytest.raises(httpx.ConnectError):
                await service.explain(ExplainRequest(error_message="test"))

    @pytest.mark.asyncio
    async def test_ollama_timeout_propagates(self):
        """TimeoutException from Ollama must propagate (route maps it to 504)."""
        mock_search = _mock_search_service([])
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ReadTimeout("timed out", request=MagicMock())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("services.explain.httpx.AsyncClient", return_value=mock_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            with pytest.raises(httpx.TimeoutException):
                await service.explain(ExplainRequest(error_message="test"))

    @pytest.mark.asyncio
    async def test_empty_context_still_calls_ollama(self):
        """Even with zero context logs Ollama should still be called."""
        mock_search = _mock_search_service([])
        mock_http_client = _make_async_ollama_mock("No context available.")

        with patch("services.explain.httpx.AsyncClient", return_value=mock_http_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            result = await service.explain(ExplainRequest(error_message="OOM"))

        assert result.explanation == "No context available."
        assert result.context_logs == []

    @pytest.mark.asyncio
    async def test_empty_ollama_response_returns_empty_string(self):
        """An empty Ollama 'response' field should not raise — return '' ."""
        mock_search = _mock_search_service([])
        mock_http_client = _make_async_ollama_mock("")

        with patch("services.explain.httpx.AsyncClient", return_value=mock_http_client):
            mock_incident_memory = MagicMock()
            mock_incident_memory.search_similar_incident.return_value = None

            service = ExplainService(
                search_service=mock_search,
                incident_memory_service=mock_incident_memory,
            )
            result = await service.explain(ExplainRequest(error_message="OOM"))

        assert result.explanation == ""


# ---------------------------------------------------------------------------
# POST /explain route integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    from main import app

    return TestClient(app, raise_server_exceptions=False)


class TestExplainRoute:
    def test_missing_body_returns_422(self, client):
        response = client.post("/explain", json={})
        assert response.status_code == 422

    def test_context_limit_too_high_returns_422(self, client):
        response = client.post(
            "/explain",
            json={"error_message": "test", "context_limit": 21},
        )
        assert response.status_code == 422

    def test_context_limit_zero_returns_422(self, client):
        response = client.post(
            "/explain",
            json={"error_message": "test", "context_limit": 0},
        )
        assert response.status_code == 422

    def test_valid_request_returns_200(self, client):
        mock_response = ExplainResponse(
            explanation="The DB connection pool is exhausted.",
            context_logs=[],
            model="llama3",
        )
        with patch("routes.explain._service") as mock_svc:
            mock_svc.explain = AsyncMock(return_value=mock_response)
            response = client.post(
                "/explain",
                json={"error_message": "connection refused"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert data["model"] == "llama3"

    def test_ollama_unreachable_returns_503(self, client):
        with patch("routes.explain._service") as mock_svc:
            mock_svc.explain = AsyncMock(side_effect=httpx.ConnectError("refused"))
            response = client.post("/explain", json={"error_message": "test"})
        assert response.status_code == 503

    def test_ollama_timeout_returns_504(self, client):
        with patch("routes.explain._service") as mock_svc:
            mock_svc.explain = AsyncMock(
                side_effect=httpx.ReadTimeout("timed out", request=MagicMock())
            )
            response = client.post("/explain", json={"error_message": "test"})
        assert response.status_code == 504

    def test_ollama_http_error_returns_502(self, client):
        mock_http_error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )
        with patch("routes.explain._service") as mock_svc:
            mock_svc.explain = AsyncMock(side_effect=mock_http_error)
            response = client.post("/explain", json={"error_message": "test"})
        assert response.status_code == 502
