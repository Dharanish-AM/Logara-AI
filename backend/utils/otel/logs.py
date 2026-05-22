"""
logs.py - Utilities for parsing OpenTelemetry (OTLP) log records from HTTP JSON payloads.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.parser import LogParser
from utils.constants import META_SERVICE

logger = logging.getLogger(__name__)


def parse_any_value(val: Any) -> Any:
    """
    Parses OTel AnyValue structures recursively to return Python primitives.
    Supports stringValue, boolValue, intValue, doubleValue, arrayValue, and kvlistValue.
    """
    if isinstance(val, dict):
        if "stringValue" in val:
            return val["stringValue"]
        if "boolValue" in val:
            return val["boolValue"]
        if "intValue" in val:
            try:
                return int(val["intValue"])
            except (ValueError, TypeError):
                return val["intValue"]
        if "doubleValue" in val:
            try:
                return float(val["doubleValue"])
            except (ValueError, TypeError):
                return val["doubleValue"]
        if "arrayValue" in val:
            arr_val = val["arrayValue"]
            values = arr_val.get("values", []) if isinstance(arr_val, dict) else (arr_val if isinstance(arr_val, list) else [])
            return [parse_any_value(v) for v in values]
        if "kvlistValue" in val:
            kv_val = val["kvlistValue"]
            values = kv_val.get("values", []) if isinstance(kv_val, dict) else (kv_val if isinstance(kv_val, list) else [])
            result = {}
            for item in values:
                if isinstance(item, dict) and "key" in item:
                    result[item["key"]] = parse_any_value(item.get("value"))
            return result
        # Fallback for flat dictionary
        return {k: parse_any_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [parse_any_value(v) for v in val]
    return val


def parse_attributes(attributes_list: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Converts standard OTel attributes list [{"key": "...", "value": {...}}] into a flat Python dict.
    """
    if not attributes_list or not isinstance(attributes_list, list):
        return {}
    attrs = {}
    for item in attributes_list:
        if isinstance(item, dict) and "key" in item:
            attrs[item["key"]] = parse_any_value(item.get("value"))
    return attrs


def severity_number_to_text(severity_num: int) -> str:
    """
    Maps OTel numeric severity levels (1-24) to standardized severity names.
    """
    if not isinstance(severity_num, int):
        try:
            severity_num = int(severity_num)
        except (ValueError, TypeError):
            return "INFO"

    if 1 <= severity_num <= 4:
        return "TRACE"
    elif 5 <= severity_num <= 8:
        return "DEBUG"
    elif 9 <= severity_num <= 12:
        return "INFO"
    elif 13 <= severity_num <= 16:
        return "WARN"
    elif 17 <= severity_num <= 20:
        return "ERROR"
    elif 21 <= severity_num <= 24:
        return "FATAL"
    return "INFO"


def parse_time(time_unix_nano: Optional[Any]) -> str:
    """
    Converts Unix nanosecond timestamp to an ISO 8601 string.
    """
    if not time_unix_nano:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        seconds = float(time_unix_nano) / 1e9
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_otel_log_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses a batch OTLP log HTTP JSON payload.
    Extracts log records, severity, timestamps, attributes, and formats them to the standard schema.
    """
    parsed_records = []
    if not isinstance(payload, dict):
        return parsed_records

    resource_logs = payload.get("resourceLogs", [])
    if not isinstance(resource_logs, list):
        return parsed_records

    for r_log in resource_logs:
        if not isinstance(r_log, dict):
            continue

        resource = r_log.get("resource", {})
        resource_attrs = parse_attributes(resource.get("attributes", [])) if isinstance(resource, dict) else {}

        scope_logs = r_log.get("scopeLogs", [])
        if not isinstance(scope_logs, list):
            continue

        for s_log in scope_logs:
            if not isinstance(s_log, dict):
                continue

            log_records = s_log.get("logRecords", [])
            if not isinstance(log_records, list):
                continue

            for record in log_records:
                if not isinstance(record, dict):
                    continue

                # 1. Parse log message body
                body_val = parse_any_value(record.get("body"))
                if body_val is None:
                    body_str = ""
                elif isinstance(body_val, (dict, list)):
                    body_str = json.dumps(body_val)
                else:
                    body_str = str(body_val)

                # 2. Parse severity/level
                severity_text = record.get("severityText")
                severity_num = record.get("severityNumber")
                if severity_text and isinstance(severity_text, str) and severity_text.strip():
                    level = severity_text.strip().upper()
                elif severity_num is not None:
                    level = severity_number_to_text(severity_num)
                else:
                    level = "INFO"

                # 3. Parse timestamp
                time_nano = record.get("timeUnixNano") or record.get("observedTimeUnixNano")
                timestamp = parse_time(time_nano)

                # 4. Parse attributes
                record_attrs = parse_attributes(record.get("attributes", []))
                combined_metadata = {}
                combined_metadata.update(resource_attrs)
                combined_metadata.update(record_attrs)

                # Preserve service name mapping
                service_name = combined_metadata.get("service.name") or combined_metadata.get("service")
                if service_name:
                    combined_metadata[META_SERVICE] = service_name

                # 5. Extract schema components, attempting regex parser on the body
                parsed_standard = LogParser.parse_line(body_str)
                if parsed_standard:
                    # Merge parsed details if standard pattern matched
                    parsed_metadata = parsed_standard.get("metadata", {})
                    combined_metadata.update(parsed_metadata)
                    
                    timestamp_final = parsed_standard.get("timestamp") or timestamp
                    level_final = parsed_standard.get("level") or level
                    message_final = parsed_standard.get("message") or body_str
                    parser_type = parsed_standard.get("parser_type") or "otlp_log"
                else:
                    timestamp_final = timestamp
                    level_final = level
                    message_final = body_str
                    parser_type = "otlp_log"

                parsed_records.append({
                    "timestamp": timestamp_final,
                    "level": level_final,
                    "message": message_final,
                    "metadata": combined_metadata,
                    "parser_type": parser_type,
                    "raw": body_str
                })

    return parsed_records
