"""
Log Processor Worker

Consumes log payloads from the Redis queue and processes them for
future vectorization and LLM analysis workflows.
"""

import json
import logging
import os
import time
import uuid
from typing import Dict, Any

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
try:
    from qdrant_client.models import PointStruct, VectorParams, Distance
except ImportError:
    from qdrant_client.http.models import PointStruct, VectorParams, Distance

from utils.queue import redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker: %(message)s"
)

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "logs")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# Lazy-loaded globals to keep unit tests fast/offline
_embedding_model = None
_qdrant_client = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL, timeout=3)
    return _qdrant_client


def init_qdrant_collection(client: QdrantClient, collection_name: str):
    """
    Ensure the target Qdrant collection exists and is configured for 384-dimensional cosine similarity vectors.
    """
    try:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
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

        level = parsed.get("level", "UNKNOWN")
        message = parsed.get("message", "No message")
        parser_type = parsed.get("parser_type", "unknown")
        timestamp = parsed.get("timestamp")

        metadata = data.get("metadata", {})

        logger.info(
            f"Processing log | level={level} | "
            f"parser={parser_type} | "
            f"message={message[:100]}"
        )

        # 1. Generate Embeddings
        try:
            model = get_embedding_model()
            vector = model.encode(message).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            increment_metric("failed_logs")
            return False

        # 2. Store in Qdrant
        try:
            q_client = get_qdrant_client()
            init_qdrant_collection(q_client, QDRANT_COLLECTION)

            point_id = str(uuid.uuid4())
            
            # Extract service_id for partitioning
            service_id = metadata.get("service") or metadata.get("service.name") or "unknown_service"

            payload = {
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "parser_type": parser_type,
                "metadata": metadata,
                "service_id": service_id
            }

            q_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.info(
                f"Successfully vectorized and indexed log to Qdrant | "
                f"id={point_id} | service_id={service_id}"
            )
        except Exception as e:
            logger.error(f"Failed to store log in Qdrant: {e}")
            increment_metric("failed_logs")
            return False

        increment_metric("processed_logs")
        return True

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse payload as JSON: {e}")
        increment_metric("failed_logs")
        return False

    except Exception as e:
        logger.error(f"Unexpected error processing payload: {e}")
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