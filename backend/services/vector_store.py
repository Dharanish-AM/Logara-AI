"""Qdrant vector storage helpers with service-scoped filtering."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from utils.service_id import normalize_service_id, validate_service_id


def build_payload_filter(
    service_id: str,
    environment: str | None = None,
    severity: str | None = None,
) -> Filter:
    normalized_service_id = validate_service_id(service_id)

    must_conditions = [
        FieldCondition(
            key="service_id",
            match=MatchValue(value=normalized_service_id),
        )
    ]

    if environment:
        must_conditions.append(
            FieldCondition(
                key="environment",
                match=MatchValue(value=environment),
            )
        )

    if severity:
        must_conditions.append(
            FieldCondition(
                key="level",
                match=MatchValue(value=severity.upper()),
            )
        )

    return Filter(must=must_conditions)


class QdrantVectorStore:
    def __init__(self, client: Any, collection_name: str = "logs"):
        self.client = client
        self.collection_name = collection_name

    def ensure_collection(self, vector_size: int = 384) -> None:
        try:
            if self.client.collection_exists(self.collection_name):
                return
        except Exception:
            try:
                self.client.get_collection(self.collection_name)
                return
            except Exception:
                pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

    def upsert_log(
        self,
        vector: Sequence[float],
        payload: dict[str, Any],
        point_id: str | None = None,
    ) -> str:
        payload = dict(payload)
        service_id = normalize_service_id(payload.get("service_id"))

        if not service_id:
            raise ValueError("Qdrant log payload must include a valid service_id")

        payload["service_id"] = service_id

        point_id = point_id or str(uuid.uuid4())

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=list(vector),
                    payload=payload,
                )
            ],
        )

        return point_id

    def semantic_search(
        self,
        query_vector: Sequence[float],
        service_id: str,
        limit: int = 10,
        environment: str | None = None,
        severity: str | None = None,
    ) -> Any:
        query_filter = build_payload_filter(
            service_id=service_id,
            environment=environment,
            severity=severity,
        )

        search = getattr(self.client, "search", None)

        if callable(search):
            return search(
                collection_name=self.collection_name,
                query_vector=list(query_vector),
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )

        return self.client.query_points(
            collection_name=self.collection_name,
            query=list(query_vector),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )