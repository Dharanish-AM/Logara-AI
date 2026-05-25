import logging
from datetime import datetime, timezone

from anomaly.aggregator import (
    record_event,
    get_event_count,
    get_historical_counts,
)

from anomaly.scoring import calculate_z_score

from anomaly.schemas import (
    AnomalyEvent,
    AlertSeverity,
)

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 1.2


def analyze_log(
    service_id: str,
    level: str,
    message: str,
):

    if level not in ["ERROR", "CRITICAL", "FATAL"]:
        return None

    record_event(service_id)

    current_count = get_event_count(service_id)

    historical_counts = get_historical_counts(service_id)

    score = calculate_z_score(
        current_count,
        historical_counts,
    )

    if score < ANOMALY_THRESHOLD:
        return None

    event = AnomalyEvent(
        service_id=service_id,
        level=level,
        message=message,
        anomaly_score=round(score, 2),
        severity=AlertSeverity.CRITICAL,
        timestamp=datetime.now(timezone.utc),
    )

    logger.warning(
        f"ANOMALY DETECTED | "
        f"service={service_id} | "
        f"score={score:.2f}"
    )

    return event