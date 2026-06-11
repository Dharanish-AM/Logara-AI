from unittest.mock import MagicMock

import pytest

from services.vector_store import QdrantVectorStore, build_payload_filter


def test_build_payload_filter_includes_service_id():
    query_filter = build_payload_filter("payments-api")

    assert query_filter.must[0].key == "service_id"
    assert query_filter.must[0].match.value == "payments-api"


def test_build_payload_filter_includes_optional_filters():
    query_filter = build_payload_filter(
        service_id="payments-api",
        environment="production",
        severity="error",
    )

    keys = [condition.key for condition in query_filter.must]
    assert "service_id" in keys
    assert "environment" in keys
    assert "level" in keys


def test_upsert_log_stores_service_id_payload():
    client = MagicMock()
    store = QdrantVectorStore(client=client, collection_name="logs")

    point_id = store.upsert_log(
        vector=[0.1, 0.2, 0.3],
        payload={
            "service_id": "payments-api",
            "message": "database timeout",
        },
        point_id="point-1",
    )

    assert point_id == "point-1"

    kwargs = client.upsert.call_args.kwargs
    assert kwargs["collection_name"] == "logs"

    point = kwargs["points"][0]
    assert point.payload["service_id"] == "payments-api"
    assert point.payload["message"] == "database timeout"


def test_upsert_log_rejects_missing_service_id():
    client = MagicMock()
    store = QdrantVectorStore(client=client, collection_name="logs")

    with pytest.raises(ValueError):
        store.upsert_log(
            vector=[0.1, 0.2, 0.3],
            payload={"message": "missing service"},
        )


def test_semantic_search_applies_service_filter():
    client = MagicMock()
    client.search.return_value = []

    store = QdrantVectorStore(client=client, collection_name="logs")

    store.semantic_search(
        query_vector=[0.1, 0.2, 0.3],
        service_id="payments-api",
        limit=5,
    )

    kwargs = client.search.call_args.kwargs
    assert kwargs["collection_name"] == "logs"
    assert kwargs["limit"] == 5
    assert kwargs["query_filter"].must[0].key == "service_id"
    assert kwargs["query_filter"].must[0].match.value == "payments-api"
