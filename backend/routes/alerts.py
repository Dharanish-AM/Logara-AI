from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from anomaly.alerts import (
    alert_manager,
    AlertRule,
    AlertSeverity,
    NotificationChannel,
    AlertNotification,
)
from anomaly.schemas import AnomalyEvent

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class CreateAlertRuleRequest(BaseModel):
    id: str
    name: str
    description: str
    severity: AlertSeverity
    notification_channels: List[NotificationChannel] = [NotificationChannel.LOG]
    tags: List[str] = []
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    id: str
    name: str
    description: str
    severity: AlertSeverity
    notification_channels: List[NotificationChannel]
    tags: List[str]
    enabled: bool


class AlertNotificationResponse(BaseModel):
    rule_id: str
    event: dict
    triggered_at: datetime
    channels: List[str]
    deduplication_key: str


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(request: CreateAlertRuleRequest) -> AlertRuleResponse:
    if request.id in alert_manager.rules:
        raise HTTPException(
            status_code=400,
            detail=f"Alert rule with ID '{request.id}' already exists",
        )

    def condition_func(event: AnomalyEvent) -> bool:
        return event.severity == request.severity

    rule = AlertRule(
        id=request.id,
        name=request.name,
        description=request.description,
        condition=condition_func,
        severity=request.severity,
        enabled=request.enabled,
        notification_channels=request.notification_channels,
        tags=request.tags,
    )

    alert_manager.register_rule(rule)

    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        severity=rule.severity,
        notification_channels=rule.notification_channels,
        tags=rule.tags,
        enabled=rule.enabled,
    )


@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules() -> List[AlertRuleResponse]:
    rules = alert_manager.get_rules()
    return [
        AlertRuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            notification_channels=rule.notification_channels,
            tags=rule.tags,
            enabled=rule.enabled,
        )
        for rule in rules.values()
    ]


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: str) -> AlertRuleResponse:
    rule = alert_manager.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        severity=rule.severity,
        notification_channels=rule.notification_channels,
        tags=rule.tags,
        enabled=rule.enabled,
    )


@router.put("/rules/{rule_id}/enable")
async def enable_alert_rule(rule_id: str) -> dict:
    if not alert_manager.enable_rule(rule_id):
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return {"message": f"Alert rule '{rule_id}' enabled"}


@router.put("/rules/{rule_id}/disable")
async def disable_alert_rule(rule_id: str) -> dict:
    if not alert_manager.disable_rule(rule_id):
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return {"message": f"Alert rule '{rule_id}' disabled"}


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: str) -> dict:
    if not alert_manager.unregister_rule(rule_id):
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return {"message": f"Alert rule '{rule_id}' deleted"}


@router.get("/history", response_model=List[AlertNotificationResponse])
async def get_alert_history(
    limit: int = Query(100, ge=1, le=1000),
    rule_id: Optional[str] = None,
    service_id: Optional[str] = None,
) -> List[AlertNotificationResponse]:
    alerts = alert_manager.get_alert_history(
        limit=limit, rule_id=rule_id, service_id=service_id
    )

    return [
        AlertNotificationResponse(
            rule_id=alert.rule_id,
            event=alert.event.dict(),
            triggered_at=alert.triggered_at,
            channels=[ch.value for ch in alert.channels],
            deduplication_key=alert.deduplication_key,
        )
        for alert in alerts
    ]


@router.post("/test")
async def test_alert() -> dict:
    from anomaly.schemas import AnomalyEvent, AlertSeverity
    from datetime import datetime

    test_event = AnomalyEvent(
        service_id="test-service",
        level="ERROR",
        message="Test alert event",
        anomaly_score=0.95,
        severity=AlertSeverity.WARNING,
        timestamp=datetime.now(),
    )

    triggered_alerts = await alert_manager.process_event(test_event)

    return {
        "message": "Test alert processed",
        "triggered_alerts": len(triggered_alerts),
        "alerts": [
            {
                "rule_id": alert.rule_id,
                "event": alert.event.dict(),
                "triggered_at": alert.triggered_at.isoformat(),
            }
            for alert in triggered_alerts
        ],
    }


@router.get("/health")
async def alert_system_health() -> dict:
    return {
        "status": "healthy",
        "rules_count": len(alert_manager.rules),
        "alert_history_count": len(alert_manager.alert_history),
    }
