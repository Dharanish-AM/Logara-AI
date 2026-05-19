"""
parser.py - Orchestration layer for parsing raw logs into structured JSON payloads.
"""
import json
import logging
from typing import Dict, Optional, Any

from utils.patterns import PARSERS
from utils.metadata import extract_metadata
from utils.timestamp import normalize_timestamp

logger = logging.getLogger(__name__)

VALID_LEVELS = {
    "INFO",
    "WARN",
    "WARNING",
    "ERROR",
    "DEBUG",
    "CRITICAL"
}


class LogParser:
    """
    Parses raw log lines into standardized structured payloads.
    """

    @staticmethod
    def _normalize_level(level: str) -> str:
        if not level:
            return "INFO"

        normalized = level.upper()

        if normalized == "WARNING":
            return "WARN"

        return normalized if normalized in VALID_LEVELS else "INFO"

    @staticmethod
    def _parse_json_log(clean_line: str) -> Optional[Dict[str, Any]]:
        """
        Safely parses JSON log payloads.
        """
        try:
            parsed = json.loads(clean_line)

            if not isinstance(parsed, dict):
                return None

            raw_timestamp = parsed.get("timestamp", "")
            timestamp = normalize_timestamp(raw_timestamp) or raw_timestamp

            level = LogParser._normalize_level(parsed.get("level", "INFO"))
            message = parsed.get("message", "")

            reserved_keys = {"timestamp", "level", "message"}

            metadata = {
                key: value
                for key, value in parsed.items()
                if key not in reserved_keys
            }

            extracted_metadata = extract_metadata(message)
            metadata.update(extracted_metadata)

            return {
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "metadata": metadata,
                "parser_type": "structured_json",
                "raw": clean_line
            }

        except json.JSONDecodeError:
            logger.debug("Malformed JSON log detected.")
            return None

        except Exception as e:
            logger.warning(f"Unexpected JSON parsing error: {e}", exc_info=True)
            return None

    @staticmethod
    def parse_line(line: str) -> Optional[Dict[str, Any]]:
        """
        Parses a single log line into a standardized dictionary.
        """
        if not line or not line.strip():
            return None

        clean_line = line.strip()

        if clean_line.startswith("{") and clean_line.endswith("}"):
            parsed_json = LogParser._parse_json_log(clean_line)

            if parsed_json:
                return parsed_json

        for parser_name, pattern in PARSERS:
            match = pattern.match(clean_line)

            if match:
                data = match.groupdict()

                raw_ts = data.get("timestamp", "")
                level = LogParser._normalize_level(
                    data.get("level", "INFO")
                )

                message = data.get("message", "")

                timestamp = normalize_timestamp(raw_ts) or raw_ts

                metadata = extract_metadata(message)

                return {
                    "timestamp": timestamp,
                    "level": level,
                    "message": message,
                    "metadata": metadata,
                    "parser_type": parser_name,
                    "raw": clean_line
                }

        logger.debug(
            f"Unparseable log line (no patterns matched): {clean_line[:100]}..."
        )

        return None