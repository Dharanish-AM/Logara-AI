from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


@patch("routes.search.QdrantVectorStore")
@patch("routes.search.get_embedding_model")
def test_semantic_search_filters_by_service_id(mock_get_model, mock_store_cls):
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
    mock_get_model.return_value = mock_model

    mock_store = MagicMock()
    mock_store.semantic_search.return_value = [
        SimpleNamespace(
            id="point-1",
            score=0.98,
            payload={
                "service_id": "payments-api",
                "message": "database timeout",
            },
        )
    ]
    mock_store_cls.return_value = mock_store

    response = client.get(
        "/search",
        params={
            "query": "database timeout",
            "service_id": "payments-api",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["service_id"] == "payments-api"
    assert len(data["results"]) == 1
    assert data["results"][0]["payload"]["service_id"] == "payments-api"

    kwargs = mock_store.semantic_search.call_args.kwargs
    assert kwargs["service_id"] == "payments-api"
    assert kwargs["limit"] == 5


def test_semantic_search_rejects_invalid_service_id():
    response = client.get(
        "/search",
        params={
            "query": "database timeout",
            "service_id": "bad service id",
        },
    )

    assert response.status_code == 400
