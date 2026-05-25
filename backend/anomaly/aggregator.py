from collections import defaultdict
from datetime import datetime, timedelta, UTC


SERVICE_ACTIVITY = defaultdict(list)
SERVICE_HISTORY = defaultdict(list)


WINDOW_MINUTES = 5


def record_event(service_id: str):
    now = datetime.now(UTC)

    SERVICE_ACTIVITY[service_id].append(now)

    cutoff = now - timedelta(minutes=WINDOW_MINUTES)

    SERVICE_ACTIVITY[service_id] = [
        ts for ts in SERVICE_ACTIVITY[service_id]
        if ts > cutoff
    ]

    current_count = len(SERVICE_ACTIVITY[service_id])

    SERVICE_HISTORY[service_id].append(current_count)

    if len(SERVICE_HISTORY[service_id]) > 50:
        SERVICE_HISTORY[service_id] = SERVICE_HISTORY[service_id][-50:]


def get_event_count(service_id: str) -> int:
    return len(SERVICE_ACTIVITY[service_id])


def get_historical_counts(service_id: str):
    return SERVICE_HISTORY[service_id]