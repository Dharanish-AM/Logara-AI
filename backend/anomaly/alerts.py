from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Optional, Dict, List, Any
from abc import ABC, abstractmethod
import json
import logging

from schemas import AlertSeverity, AnomalyEvent

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"
    PAGERDUTY = "pagerduty"


@dataclass
class AlertRule:
    id: str
    name: str
    description: str
    condition: Callable[[AnomalyEvent], bool]
    severity: AlertSeverity
    enabled: bool = True
    notification_channels: List[NotificationChannel] = field(
        default_factory=lambda: [NotificationChannel.LOG]
    )
    tags: List[str] = field(default_factory=list)

    def matches(self, event: AnomalyEvent) -> bool:
        if not self.enabled:
            return False
        try:
            return self.condition(event)
        except Exception as e:
            logger.error(f"Error evaluating alert rule {self.id}: {str(e)}")
            return False


@dataclass
class AlertNotification:
    rule_id: str
    event: AnomalyEvent
    triggered_at: datetime
    channels: List[NotificationChannel]
    deduplication_key: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "event": self.event.dict(),
            "triggered_at": self.triggered_at.isoformat(),
            "channels": [ch.value for ch in self.channels],
            "deduplication_key": self.deduplication_key,
        }


class NotificationHandler(ABC):
    @abstractmethod
    async def send(self, notification: AlertNotification) -> bool:
        pass


class LogNotificationHandler(NotificationHandler):
    async def send(self, notification: AlertNotification) -> bool:
        logger.info(
            f"Alert triggered: {notification.rule_id} - "
            f"Severity: {notification.event.severity} - "
            f"Message: {notification.event.message}"
        )
        return True


class EmailNotificationHandler(NotificationHandler):
    def __init__(self, smtp_config: Optional[Dict[str, str]] = None):
        self.smtp_config = smtp_config or {}

    async def send(self, notification: AlertNotification) -> bool:
        if not self.smtp_config.get("enabled"):
            logger.warning("Email notifications not configured")
            return False

        try:
            logger.info(
                f"Email notification sent for alert {notification.rule_id} "
                f"to {self.smtp_config.get('recipients', [])}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False


class SlackNotificationHandler(NotificationHandler):
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    async def send(self, notification: AlertNotification) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            payload = {
                "text": f"Alert: {notification.rule_id}",
                "attachments": [
                    {
                        "color": self._get_color(notification.event.severity),
                        "title": notification.rule_id,
                        "text": notification.event.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": notification.event.severity,
                                "short": True,
                            },
                            {
                                "title": "Service",
                                "value": notification.event.service_id,
                                "short": True,
                            },
                            {
                                "title": "Anomaly Score",
                                "value": str(notification.event.anomaly_score),
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": notification.event.timestamp.isoformat(),
                                "short": True,
                            },
                        ],
                    }
                ],
            }

            logger.info(
                f"Slack notification sent for alert {notification.rule_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
            return False

    @staticmethod
    def _get_color(severity: AlertSeverity) -> str:
        colors = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.FATAL: "#8b0000",
        }
        return colors.get(severity, "#808080")


class WebhookNotificationHandler(NotificationHandler):
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    async def send(self, notification: AlertNotification) -> bool:
        if not self.webhook_url:
            logger.warning("Webhook URL not configured")
            return False

        try:
            payload = notification.to_dict()
            logger.info(f"Webhook notification sent to {self.webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error sending webhook notification: {str(e)}")
            return False


class AlertDeduplicator:
    def __init__(self, dedup_window_seconds: int = 300):
        self.dedup_window_seconds = dedup_window_seconds
        self.alert_history: Dict[str, datetime] = {}

    def should_deduplicate(self, dedup_key: str) -> bool:
        if dedup_key not in self.alert_history:
            return False

        time_since_last = datetime.now() - self.alert_history[dedup_key]
        if time_since_last.total_seconds() < self.dedup_window_seconds:
            return True

        return False

    def record_alert(self, dedup_key: str) -> None:
        self.alert_history[dedup_key] = datetime.now()

    def cleanup_old_entries(self) -> None:
        cutoff_time = datetime.now() - timedelta(
            seconds=self.dedup_window_seconds * 2
        )
        self.alert_history = {
            k: v for k, v in self.alert_history.items()
            if v > cutoff_time
        }


class AlertManager:
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.notification_handlers: Dict[
            NotificationChannel, NotificationHandler
        ] = {
            NotificationChannel.LOG: LogNotificationHandler(),
        }
        self.deduplicator = AlertDeduplicator()
        self.alert_history: List[AlertNotification] = []

    def register_rule(self, rule: AlertRule) -> None:
        self.rules[rule.id] = rule
        logger.info(f"Alert rule registered: {rule.id}")

    def unregister_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Alert rule unregistered: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            logger.info(f"Alert rule enabled: {rule_id}")
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            logger.info(f"Alert rule disabled: {rule_id}")
            return True
        return False

    def register_notification_handler(
        self,
        channel: NotificationChannel,
        handler: NotificationHandler,
    ) -> None:
        self.notification_handlers[channel] = handler
        logger.info(f"Notification handler registered: {channel.value}")

    async def process_event(self, event: AnomalyEvent) -> List[AlertNotification]:
        triggered_alerts: List[AlertNotification] = []

        for rule in self.rules.values():
            if rule.matches(event):
                dedup_key = f"{rule.id}:{event.service_id}:{event.level}"

                if self.deduplicator.should_deduplicate(dedup_key):
                    logger.debug(f"Alert deduplicated: {dedup_key}")
                    continue

                notification = AlertNotification(
                    rule_id=rule.id,
                    event=event,
                    triggered_at=datetime.now(),
                    channels=rule.notification_channels,
                    deduplication_key=dedup_key,
                )

                await self._send_notifications(notification)
                self.deduplicator.record_alert(dedup_key)
                self.alert_history.append(notification)
                triggered_alerts.append(notification)

                logger.info(f"Alert triggered: {rule.id} for {event.service_id}")

        return triggered_alerts

    async def _send_notifications(
        self, notification: AlertNotification
    ) -> None:
        for channel in notification.channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    await handler.send(notification)
                except Exception as e:
                    logger.error(
                        f"Error sending {channel.value} notification: {str(e)}"
                    )

    def get_alert_history(
        self,
        limit: int = 100,
        rule_id: Optional[str] = None,
        service_id: Optional[str] = None,
    ) -> List[AlertNotification]:
        history = self.alert_history

        if rule_id:
            history = [a for a in history if a.rule_id == rule_id]
        if service_id:
            history = [a for a in history if a.event.service_id == service_id]

        return history[-limit:]

    def get_rules(self) -> Dict[str, AlertRule]:
        return self.rules.copy()

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        return self.rules.get(rule_id)


alert_manager = AlertManager()
