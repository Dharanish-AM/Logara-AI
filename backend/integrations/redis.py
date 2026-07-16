"""
Redis client integration layer.
"""

import logging

try:
    import redis
except ImportError:  # pragma: no cover
    class _RedisFallback:
        class RedisError(Exception):
            pass

        class Redis:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("redis package is not installed")

    redis = _RedisFallback()

from core.settings import get_settings

logger = logging.getLogger(__name__)

class RedisQueueClient:
    """
    Lazily initializes the shared Redis client when first used.

    Callers should handle connection errors when invoking queue operations or
    explicitly call connect() if they want to fail fast.
    """

    def __init__(self):
        self._client = None

    def connect(self):
        if self._client is None:
            settings = get_settings()
            try:
                self._client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password,
                    decode_responses=True,
                )
            except redis.RedisError as exc:
                logger.error("Failed to initialize Redis client: %s", exc)
                raise RuntimeError("Failed to initialize Redis client") from exc
        return self._client

    @property
    def client(self):
        return self.connect()

    def lpush(self, queue_name: str, payload: str):
        return self.client.lpush(queue_name, payload)

    def brpop(self, queue_name: str, timeout: int = 0):
        return self.client.brpop(queue_name, timeout=timeout)

    def ping(self):
        return self.client.ping()

    def llen(self, queue_name: str) -> int:
        """Return the current length of the named list (queue depth)."""
        return int(self.client.llen(queue_name) or 0)

    def ltrim(self, queue_name: str, start: int, stop: int) -> None:
        """Trim the list so it contains only elements from start to stop."""
        self.client.ltrim(queue_name, start, stop)


# Shared lazy Redis client; callers may call connect() up front or handle
# connection errors on first queue operation if Redis is not yet reachable.
logger = logging.getLogger(__name__)
redis_client = RedisQueueClient()

# Hard cap on Redis queue depth. If the worker is lagging and the queue
# grows beyond this threshold, new log payloads are rejected with HTTP 429
# rather than being enqueued — protecting against OOM exhaustion (#119, #198).
MAX_QUEUE_SIZE: int = 50_000
