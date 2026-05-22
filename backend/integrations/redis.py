"""
Redis client integration layer.
"""

import redis

from core.settings import get_settings


class RedisQueueClient:
    def __init__(self):
        settings = get_settings()
        self._client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=True,
        )

    def lpush(self, queue_name: str, payload: str):
        return self._client.lpush(queue_name, payload)

    def brpop(self, queue_name: str, timeout: int = 0):
        return self._client.brpop(queue_name, timeout=timeout)

    def ping(self):
        return self._client.ping()


redis_client = RedisQueueClient()
