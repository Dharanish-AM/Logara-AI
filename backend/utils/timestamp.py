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
    Handles timezone-aware ISO 8601 timestamps with offsets (+HH:MM, -HH:MM).
    Falls back safely to the raw value if parsing fails.
    """
    if not ts_str:
        return None

    clean_ts = ts_str.strip()
    
    # Return None if string is empty after stripping
    if not clean_ts:
        return None

    # Attempt ISO 8601 parsing first (handles timezone offsets)
    # Convert a trailing UTC "Z" designator to "+00:00" for fromisoformat compatibility
    iso_ts = clean_ts[:-1] + "+00:00" if clean_ts.endswith("Z") else clean_ts
    
    try:
        parsed_dt = datetime.fromisoformat(iso_ts)
        # For timezone-aware datetimes, isoformat() includes offset
        # For naive datetimes, isoformat() returns simple format
        return parsed_dt.isoformat()
    except ValueError:
        logger.debug("ISO 8601 parse failed, falling back to legacy formats")
        

    # Fall back to legacy format support
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