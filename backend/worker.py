"""
Log Processor Worker

This script runs as a background service to consume log payloads from the Redis
queue that were pushed by the FastAPI ingestor. It acts as the bridge between 
ingestion and the upcoming vectorization/LLM processing layers.
"""

import json
import logging
import time
from utils.queue import redis_client

# Configure basic logging for the worker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] Worker: %(message)s'
)
logger = logging.getLogger(__name__)

def process_log(payload_str: str) -> bool:
    """
    Deserialize and process a log payload from the queue.
    
    Note: Currently, this acts as a placeholder that simply acknowledges
    and logs the payload. In the future, this function will format the 
    data and send it to Qdrant for vectorization and Ollama for LLM analysis.
    """
    try:
        data = json.loads(payload_str)
        
        # Placeholder for vectorization and LLM logic
        level = data.get("parsed", {}).get("level", "UNKNOWN")
        msg = data.get("parsed", {}).get("message", "No message")
        
        logger.info(f"Processed {level} log: {msg[:100]}")
        return True
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse payload as JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing payload: {e}")
        return False

def run_worker():
    """
    Main loop to continuously block and pop from the Redis queue.
    """
    logger.info("Starting Log Processor worker. Waiting for logs...")
    
    while True:
        try:
            # brpop returns a tuple (queue_name, item)
            # block for 1 second so we can gracefully handle KeyboardInterrupt
            result = redis_client.brpop("log_queue", timeout=1)
            
            if result:
                queue_name, payload = result
                process_log(payload)
                
        except KeyboardInterrupt:
            logger.info("Worker shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Queue connection error: {e}")
            time.sleep(5)  # Prevent tight loop, allow Redis to recover

if __name__ == "__main__":
    run_worker()
