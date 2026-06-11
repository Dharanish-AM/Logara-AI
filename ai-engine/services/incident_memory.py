import uuid

try:
    from qdrant_client.models import PointStruct
except ImportError:
    from qdrant_client.http.models import PointStruct  # type: ignore

from core.settings import get_settings
from schemas.incident_memory import IncidentMemoryResult
from services.search import (
    get_embedding_model,
    get_qdrant_client,
)


class IncidentMemoryService:

    def search_similar_incident(
        self,
        query: str,
    ):

        settings = get_settings()

        model = get_embedding_model()

        vector = model.encode(query).tolist()

        client = get_qdrant_client()

        hits = client.search(
            collection_name=settings.incident_memory_collection,
            query_vector=vector,
            limit=1,
            with_payload=True,
        )

        if not hits:
            return None

        hit = hits[0]

        payload = hit.payload or {}

        return IncidentMemoryResult(
            id=str(hit.id),
            score=float(hit.score),
            error_message=payload.get("error_message", ""),
            explanation=payload.get("explanation", ""),
            service_id=payload.get("service_id"),
        )

    def store_incident(
        self,
        error_message: str,
        explanation: str,
        service_id: str | None = None,
    ):

        settings = get_settings()

        model = get_embedding_model()

        vector = model.encode(error_message).tolist()

        client = get_qdrant_client()

        client.upsert(
            collection_name=settings.incident_memory_collection,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "error_message": error_message,
                        "explanation": explanation,
                        "service_id": service_id,
                    },
                )
            ],
        )
