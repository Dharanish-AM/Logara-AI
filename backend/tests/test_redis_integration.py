from unittest.mock import MagicMock, patch

import pytest
import redis

from integrations.redis import RedisQueueClient


@patch("integrations.redis.redis.Redis")
def test_redis_client_connects_lazily(mock_redis):
    mock_client = MagicMock()
    mock_redis.return_value = mock_client

    client = RedisQueueClient()

    mock_redis.assert_not_called()
    client.ping()
    mock_redis.assert_called_once()
    mock_client.ping.assert_called_once()


@patch("integrations.redis.redis.Redis")
def test_redis_client_raises_descriptive_error_on_connect_failure(mock_redis):
    mock_redis.side_effect = redis.RedisError("boom")

    client = RedisQueueClient()

    with pytest.raises(RuntimeError, match="Failed to initialize Redis client"):
        client.ping()
