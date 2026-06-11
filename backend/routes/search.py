"""Semantic search routes with service-scoped Qdrant filtering."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from integrations.qdrant import qdrant_client
from services.vector_store import QdrantVectorStore
from utils.service_id import normalize_service_id
from worker import get_embedding_model

router = APIRouter()


def _vectorize_query(query: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode(query)

    if hasattr(vector, "tolist"):
        return vector.tolist()

    return list(vector)


def _serialize_result(result: Any) -> dict[str, Any]:
    payload = getattr(result, "payload", {}) or {}

    return {
        "id": str(getattr(result, "id", "")),
        "score": getattr(result, "score", None),
        "payload": payload,
    }


@router.get("/search")
async def semantic_search(
    query: str = Query(..., min_length=1),
    service_id: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    environment: str | None = None,
    severity: str | None = None,
):
    normalized_service_id = normalize_service_id(service_id)

    if not normalized_service_id:
        raise HTTPException(
            status_code=400,
            detail="service_id must contain only letters, numbers, '.', '_', ':', or '-'",
        )

    if not query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")

    try:
        query_vector = _vectorize_query(query.strip())
        store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=os.getenv("QDRANT_COLLECTION", "logs"),
        )

        results = store.semantic_search(
            query_vector=query_vector,
            service_id=normalized_service_id,
            limit=limit,
            environment=environment,
            severity=severity,
        )

        if hasattr(results, "points"):
            results = results.points

        return {
            "query": query.strip(),
            "service_id": normalized_service_id,
            "limit": limit,
            "results": [_serialize_result(result) for result in results],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(exc)}",
        ) from exc
