"""
timestamp.py - Utilities for handling and normalizing log timestamps.
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]


def normalize_timestamp(ts_str: str) -> Optional[str]:
    """
    Attempts to normalize timestamps into ISO 8601 format.
    Falls back safely to the raw value if parsing fails.
    """
    if not ts_str:
        return None

    clean_ts = ts_str.strip()

    for fmt in SUPPORTED_FORMATS:
        try:
            parsed_dt = datetime.strptime(clean_ts, fmt)
            return parsed_dt.isoformat()
        except ValueError:
            continue

    logger.debug(
        f"Timestamp '{ts_str}' did not match supported formats. Returning raw."
    )

    return ts_str