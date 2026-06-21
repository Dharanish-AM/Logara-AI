"""
Tests for SlackNotificationHandler and WebhookNotificationHandler HTTP delivery.

Both handlers previously built payloads and returned True
without making any HTTP call. These tests assert the POST actually happens,
that success/failure is reflected in the return value, and that the success
log line only appears after a 2xx response.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from anomaly.alerts import (
    SlackNotificationHandler,
    WebhookNotificationHandler,
    LogNotificationHandler,
    AlertNotification,
    NotificationChannel,
)
from anomaly.schemas import AlertSeverity, AnomalyEvent


def _make_notification() -> AlertNotification:
    event = AnomalyEvent(
        service_id="payment-gateway",
        level="ERROR",
        message="Latency spike detected",
        anomaly_score=0.92,
        severity=AlertSeverity.CRITICAL,
        timestamp=datetime(2026, 6, 21, 10, 30, tzinfo=timezone.utc),
    )
    return AlertNotification(
        rule_id="rule-latency",
        event=event,
        triggered_at=datetime(2026, 6, 21, 10, 30, tzinfo=timezone.utc),
        channels=[NotificationChannel.SLACK, NotificationChannel.WEBHOOK],
        deduplication_key="rule-latency:payment-gateway",
    )


def _mock_client(post_mock: AsyncMock):
    """Build a MagicMock that works as an async context manager wrapping
    httpx.AsyncClient, with .post replaced by post_mock."""
    client = MagicMock()
    client.post = post_mock
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _ok_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()  # 2xx: does nothing
    return resp


def _error_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    request = httpx.Request("POST", "https://example.test/hook")
    response = httpx.Response(status_code, request=request)
    resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            f"HTTP {status_code}", request=request, response=response
        )
    )
    return resp


# --------------------------------------------------------------------------
# SlackNotificationHandler
# --------------------------------------------------------------------------
class TestSlackNotificationHandler:
    @pytest.mark.anyio
    async def test_posts_payload_and_returns_true_on_2xx(self):
        post = AsyncMock(return_value=_ok_response())
        handler = SlackNotificationHandler(webhook_url="https://hooks.test/slack")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(_make_notification())

        assert result is True
        post.assert_awaited_once()
        args, kwargs = post.call_args
        # Posted to the configured URL with a JSON payload
        assert args[0] == "https://hooks.test/slack"
        assert "json" in kwargs
        assert kwargs["json"]["text"] == "Alert: rule-latency"

    @pytest.mark.anyio
    async def test_returns_false_and_logs_status_on_non_2xx(self, caplog):
        post = AsyncMock(return_value=_error_response(500))
        handler = SlackNotificationHandler(webhook_url="https://hooks.test/slack")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(_make_notification())

        assert result is False
        assert "500" in caplog.text

    @pytest.mark.anyio
    async def test_returns_false_on_network_error(self):
        post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        handler = SlackNotificationHandler(webhook_url="https://hooks.test/slack")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(_make_notification())

        assert result is False

    @pytest.mark.anyio
    async def test_returns_false_when_no_url_configured(self):
        handler = SlackNotificationHandler(webhook_url=None)
        result = await handler.send(_make_notification())
        assert result is False

    @pytest.mark.anyio
    async def test_success_log_only_after_2xx(self, caplog):
        # On failure, the "sent" confirmation must NOT appear.
        post = AsyncMock(return_value=_error_response(502))
        handler = SlackNotificationHandler(webhook_url="https://hooks.test/slack")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            await handler.send(_make_notification())
        assert "notification sent" not in caplog.text.lower()


# --------------------------------------------------------------------------
# WebhookNotificationHandler
# --------------------------------------------------------------------------
class TestWebhookNotificationHandler:
    @pytest.mark.anyio
    async def test_posts_to_dict_payload_and_returns_true_on_2xx(self):
        post = AsyncMock(return_value=_ok_response())
        notification = _make_notification()
        handler = WebhookNotificationHandler(webhook_url="https://hooks.test/webhook")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(notification)

        assert result is True
        post.assert_awaited_once()
        args, kwargs = post.call_args
        assert args[0] == "https://hooks.test/webhook"
        assert kwargs["json"] == notification.to_dict()
        assert kwargs["headers"]["Content-Type"] == "application/json"

    @pytest.mark.anyio
    async def test_returns_false_and_logs_status_on_non_2xx(self, caplog):
        post = AsyncMock(return_value=_error_response(404))
        handler = WebhookNotificationHandler(webhook_url="https://hooks.test/webhook")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(_make_notification())

        assert result is False
        assert "404" in caplog.text

    @pytest.mark.anyio
    async def test_returns_false_on_network_error(self):
        post = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
        handler = WebhookNotificationHandler(webhook_url="https://hooks.test/webhook")
        with patch("anomaly.alerts.httpx.AsyncClient", return_value=_mock_client(post)):
            result = await handler.send(_make_notification())

        assert result is False

    @pytest.mark.anyio
    async def test_returns_false_when_no_url_configured(self):
        handler = WebhookNotificationHandler(webhook_url=None)
        result = await handler.send(_make_notification())
        assert result is False


# --------------------------------------------------------------------------
# LogNotificationHandler — unchanged behaviour
# --------------------------------------------------------------------------
class TestLogNotificationHandlerUnchanged:
    @pytest.mark.anyio
    async def test_log_handler_still_returns_true_without_http(self):
        handler = LogNotificationHandler()
        with patch("anomaly.alerts.httpx.AsyncClient") as client_cls:
            result = await handler.send(_make_notification())
        assert result is True
        client_cls.assert_not_called()  # LogHandler must not make HTTP calls