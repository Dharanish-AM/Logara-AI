"""
Log Processor Worker

Consumes log payloads from the Redis queue and processes them for
vectorization and storage in Qdrant.
"""
from anomaly.detector import analyze_log
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional

from sentence_transformers import SentenceTransformer

try:
    from qdrant_client import QdrantClient
    try:
        from qdrant_client.models import PointStruct, VectorParams, Distance
    except ImportError:
        from qdrant_client.http.models import PointStruct, VectorParams, Distance
except ImportError:
    class QdrantClient:
        """Fallback Qdrant client for environments without qdrant-client installed."""

    @dataclass
    class PointStruct:
        id: Any
        vector: Any
        payload: dict[str, Any]

    class VectorParams:
        def __init__(self, size: int, distance: Any):
            self.size = size
            self.distance = distance

    class Distance:
        COSINE = "Cosine"

from core.settings import get_settings
from services.duplicate_detector import DuplicateClusteringService
from utils.queue import redis_client
from utils.similarity import build_semantic_log_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker: %(message)s"
)

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "logs")

# Lazy-loaded globals to keep unit tests fast/offline
_embedding_model = None
_qdrant_client = None
_duplicate_clustering_service = None

# Guards against repeated collection-init RPCs on every log in the hot path
_collection_initialized: bool = False


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        _qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            timeout=settings.qdrant_timeout_seconds,
        )
    return _qdrant_client


def get_duplicate_clustering_service() -> DuplicateClusteringService:
    global _duplicate_clustering_service
    if _duplicate_clustering_service is None:
        settings = get_settings()
        _duplicate_clustering_service = DuplicateClusteringService(
            qdrant_client=get_qdrant_client(),
            similarity_threshold=settings.duplicate_similarity_threshold,
            max_cluster_sample_size=settings.max_cluster_sample_size,
            enable_duplicate_clustering=settings.enable_duplicate_clustering,
            logs_collection=settings.qdrant_collection,
            clusters_collection=settings.qdrant_cluster_collection,
        )
    return _duplicate_clustering_service


def _create_service_id_index(client: QdrantClient, collection_name: str) -> None:
    """
    Idempotently create a keyword payload index on 'service_id'.
    Qdrant treats duplicate index creation as a no-op, so this is safe
    to call on both new and pre-existing collections.
    """
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="service_id",
            field_schema="keyword"
        )
        logger.info(
            f"Payload index on 'service_id' ensured for collection '{collection_name}'"
        )
    except Exception as index_err:
        logger.error(
            f"Failed to create payload index on 'service_id' "
            f"for collection '{collection_name}': {index_err}"
        )


def init_qdrant_collection(client: QdrantClient, collection_name: str) -> None:
    """
    Ensure the target Qdrant collection exists, is configured for
    384-dimensional cosine-similarity vectors, and has a keyword payload
    index on 'service_id' for O(1) partition-based filtering.

    Safe to call on pre-existing collections — both collection creation
    and index creation are idempotent operations in Qdrant.
    """
    try:
        collection_exists = client.collection_exists(collection_name)
    except Exception:
        # Older qdrant-client versions may not expose collection_exists;
        # fall back to get_collection to determine existence.
        try:
            client.get_collection(collection_name)
            collection_exists = True
        except Exception:
            collection_exists = False

    if not collection_exists:
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection '{collection_name}'")
        except Exception as create_err:
            logger.error(
                f"Failed to create Qdrant collection '{collection_name}': {create_err}"
            )
            return

    # Always ensure the index exists — new or pre-existing collection.
    _create_service_id_index(client, collection_name)


# Lightweight in-memory worker metrics
WORKER_METRICS: Dict[str, int] = {
    "processed_logs": 0,
    "failed_logs": 0,
    "malformed_payloads": 0
}


# Ordered list of metadata keys that may carry the originating service name.
# Checked in priority order: internal canonical key first, then OTel variants.
_SERVICE_ID_KEYS = ("service", "service.name", "service_id")


def _extract_service_id(metadata: Dict[str, Any]) -> str:
    """
    Derive a non-empty service identifier from a log's metadata dict.

    Resolution order:
      1. ``service``       — canonical key written by the ingestion service
      2. ``service.name``  — standard OpenTelemetry resource attribute
      3. ``service_id``    — explicit override (e.g. from raw structured logs)
      4. ``"unknown_service"`` sentinel when none of the above are present
                             or when the resolved value is empty / whitespace.
    """
    if not isinstance(metadata, dict):
        return "unknown_service"

    for key in _SERVICE_ID_KEYS:
        value = metadata.get(key)
        if value and isinstance(value, str) and value.strip():
            return value.strip()

    return "unknown_service"


def _ensure_collection_initialized(client: QdrantClient) -> None:
    """
    Call ``init_qdrant_collection`` exactly once per worker process.

    Caches the result in the module-level ``_collection_initialized`` flag
    so that the collection-existence check and index-creation RPC are not
    repeated on every log in the hot path.
    """
    global _collection_initialized
    if not _collection_initialized:
        init_qdrant_collection(client, QDRANT_COLLECTION)
        _collection_initialized = True


def increment_metric(metric_name: str):
    """
    Safely increment worker metrics.
    """
    if metric_name in WORKER_METRICS:
        WORKER_METRICS[metric_name] += 1


def process_log(payload_str: str) -> bool:
    """
    Deserialize, process, vectorize, and store a log payload in Qdrant.
    """
    if not payload_str or not payload_str.strip():
        logger.warning("Received empty payload from queue.")
        increment_metric("malformed_payloads")
        return False

    try:
        data = json.loads(payload_str)

        if not isinstance(data, dict):
            logger.warning("Received non-dictionary JSON payload.")
            increment_metric("malformed_payloads")
            return False

        parsed = data.get("parsed")

        if not isinstance(parsed, dict):
            logger.warning("Payload missing valid 'parsed' structure.")
            increment_metric("malformed_payloads")
            return False

        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        parsed_metadata = parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}
        if parsed_metadata:
            metadata = {**metadata, **parsed_metadata}

        level = str(parsed.get("level") or metadata.get("level") or "UNKNOWN")
        parser_type = str(parsed.get("parser_type") or "unknown")
        timestamp = parsed.get("timestamp") or metadata.get("timestamp")
        message = parsed.get("message") or parsed.get("msg") or parsed.get("content")
        if not message:
            message = json.dumps(parsed, sort_keys=True, default=str)
        message = str(message)

        service_name = (
            parsed.get("service")
            or metadata.get("service")
            or metadata.get("service.name")
            or metadata.get("service_id")
            or "unknown_service"
        )

        semantic_text = build_semantic_log_text(
            message=message,
            level=level,
            service_name=str(service_name),
            metadata=metadata,
        )

        logger.info(
            "Processing log | level=%s | parser=%s | message=%s",
            level,
            parser_type,
            message[:100],
        )

        try:
            model = get_embedding_model()
            vector = model.encode(semantic_text).tolist()
        except Exception as e:
            logger.error("Failed to generate embedding: %s", e)
            increment_metric("failed_logs")
            return False

        try:
            settings = get_settings()
            q_client = get_qdrant_client()
            _ensure_collection_initialized(q_client)

            point_id = str(uuid.uuid4())

            # Extract service_id for partitioning.
            # Priority: 'service' (canonical internal key set by ingestion)
            # → 'service.name' (OTel resource attribute)
            # → 'service_id' (explicit override)
            # → 'unknown_service' sentinel when no service is identified.
            service_id = _extract_service_id(metadata)

            clustering_service = get_duplicate_clustering_service()
            decision = clustering_service.assign_to_cluster(
                log_text=message,
                embedding=vector,
                service_name=str(service_name),
                timestamp=str(timestamp) if timestamp else None,
                log_source=semantic_text,
            )

            if decision.is_duplicate:
                logger.info(
                    "Duplicate log clustered | cluster_id=%s | similarity_score=%.4f",
                    decision.cluster_id,
                    decision.similarity_score,
                )
            else:
                point_id = str(uuid.uuid4())
                payload = {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    "parser_type": parser_type,
                    "metadata": metadata,
                    "service_id": str(service_name),
                    "cluster_id": decision.cluster_id,
                    "is_cluster": False,
                }
                q_client.upsert(
                    collection_name=settings.qdrant_collection,
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=vector,
                            payload=payload,
                        )
                    ],
                )
                logger.info(
                    "Successfully vectorized and indexed log to Qdrant | id=%s | service_id=%s",
                    point_id,
                    service_name,
                )
        except Exception as e:
            logger.error("Failed to store log in Qdrant: %s", e)
            increment_metric("failed_logs")
            return False

        increment_metric("processed_logs")
        return True

    except json.JSONDecodeError as e:
        logger.error("Failed to parse payload as JSON: %s", e)
        increment_metric("failed_logs")
        return False

    except Exception as e:
        logger.error("Unexpected error processing payload: %s", e)
        increment_metric("failed_logs")
        return False


def run_worker():
    """
    Continuously consume payloads from the Redis queue.
    """
    logger.info("Starting Log Processor worker. Waiting for logs...")

    settings = get_settings()
    queue_name = settings.redis_queue_name

    while True:
        try:
            result = redis_client.brpop(
                queue_name,
                timeout=1,
            )

            if result:
                queue_name, payload = result

                logger.info(
                    f"Dequeued payload from queue='{queue_name}'"
                )

                process_log(payload)

        except KeyboardInterrupt:
            logger.info("Worker shutting down gracefully.")
            break

        except Exception as e:
            logger.error(f"Queue connection error: {e}")

            time.sleep(5)


if __name__ == "__main__":
    run_worker()