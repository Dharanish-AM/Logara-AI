from enum import Enum
from datetime import datetime

from pydantic import BaseModel


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class AnomalyEvent(BaseModel):
    service_id: str
    level: str
    message: str
    anomaly_score: float
    severity: AlertSeverity
    timestamp: datetime