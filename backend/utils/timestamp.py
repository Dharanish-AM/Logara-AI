"""
timestamp.py - Utilities for handling and normalizing log timestamps.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
]
def _normalize_epoch_timestamp(clean_ts: str) -> Optional[str]:
    """
    Normalize Unix epoch timestamps (seconds or milliseconds)
    into ISO 8601 UTC format.
    """
    if not clean_ts.isdigit():
        return None

    try:
        epoch_value = int(clean_ts)

        # Milliseconds precision epoch
        if len(clean_ts) >= 13:
            epoch_value = epoch_value / 1000

        parsed_dt = datetime.fromtimestamp(
            epoch_value,
            tz=timezone.utc,
        )

        return parsed_dt.isoformat()

    except (ValueError, OSError, OverflowError):
        logger.debug(
            f"Invalid epoch timestamp detected: {clean_ts}"
        )
        return None 

def normalize_timestamp(ts_str: str) -> Optional[str]:
    """
    Attempts to normalize timestamps into ISO 8601 format.
    Handles timezone-aware ISO 8601 timestamps with offsets (+HH:MM, -HH:MM).
    Falls back safely to the raw value if parsing fails.
    """
    if not ts_str:
        return None

    # Detect Unix epoch (seconds or milliseconds)
    try:
        val = float(ts_str.strip())
        if val > 1e10:  # epoch-ms, convert to seconds
            val = val / 1000
        return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
    except (ValueError, OSError):
        pass
    
    clean_ts = ts_str.strip()

    # Return None if string is empty after stripping
    if not clean_ts:
        return None

    epoch_result = _normalize_epoch_timestamp(clean_ts)

    if epoch_result:
        return epoch_result

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