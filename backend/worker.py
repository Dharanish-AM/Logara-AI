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
from dataclasses import dataclass
from typing import Dict, Any

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

# Lazy-loaded globals to keep unit tests fast/offline
_embedding_model = None
_qdrant_client = None
_duplicate_clustering_service = None


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


def init_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    payload_index_field: str = "service_id",
):
    """
    Ensure the target Qdrant collection exists and is configured for 384-dimensional cosine similarity vectors.
    Creates a payload index for efficient filtering on the configured field.
    """
    try:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=payload_index_field,
                    field_schema="keyword",
                )
            except Exception as index_err:
                logger.error(
                    "Failed to create payload index on %s: %s",
                    payload_index_field,
                    index_err,
                )
    except Exception:
        # Fallback query check for older client libraries
        try:
            client.get_collection(collection_name)
        except Exception:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            try:
                client.create_payload_index(
                    collection_name=collection_name,
                    field_name=payload_index_field,
                    field_schema="keyword",
                )
            except Exception as index_err:
                logger.error(
                    "Failed to create fallback payload index on %s: %s",
                    payload_index_field,
                    index_err,
                )


# Lightweight in-memory worker metrics
WORKER_METRICS: Dict[str, int] = {
    "processed_logs": 0,
    "failed_logs": 0,
    "malformed_payloads": 0
}


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
            init_qdrant_collection(q_client, settings.qdrant_collection, "service_id")
            init_qdrant_collection(
                q_client,
                settings.qdrant_cluster_collection,
                "service_name",
            )

            anomaly_event = analyze_log(
                service_id=str(service_name),
                level=level,
                message=message,
            )

            if anomaly_event:
                logger.warning(
                    "Critical anomaly detected: %s",
                    anomaly_event.model_dump_json(),
                )

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

    while True:
        try:
            result = redis_client.brpop("log_queue", timeout=1)

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