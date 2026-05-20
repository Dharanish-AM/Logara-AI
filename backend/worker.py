"""
Log Processor Worker

Consumes log payloads from the Redis queue and processes them for
future vectorization and LLM analysis workflows.
"""

import json
import logging
import time
from typing import Dict

from utils.queue import redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] Worker: %(message)s"
)

logger = logging.getLogger(__name__)

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
    Deserialize and process a log payload from the queue.
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

        logger.info(
            f"Processed log | level={level} | "
            f"parser={parser_type} | "
            f"message={message[:100]}"
        )

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