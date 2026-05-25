"""
Logara AI - Reusable Testing Utility Module

This module provides a centralized library of production-ready helper functions, 
assertion wrappers, mock generators, and testing context managers. It streamlines 
the verification of logs, metadata payloads, environment isolations, and parsers 
across the Logara AI test suite.
"""

import os
import json
import uuid
import random
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Generator, Union, Set

# Initialize logger for tracking test execution details
logger = logging.getLogger("logara.test_utils")

# Standard observability log levels recognized by the platform
VALID_LOG_LEVELS: Set[str] = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"}


# =============================================================================
# 1. LOG VALIDATION HELPERS
# =============================================================================

def validate_log_schema(log: Dict[str, Any], strict: bool = False) -> bool:
    """
    Validates if a log payload conforms to the minimum required schema structure.
    
    Args:
        log: The log dictionary to validate.
        strict: If True, validates metadata schema structure as well.
        
    Returns:
        bool: True if log fits the schema, False otherwise.
    """
    required_fields = {"timestamp", "service", "level", "message"}
    
    # 1. Check top-level field existence
    if not all(field in log for field in required_fields):
        missing = required_fields - set(log.keys())
        logger.warning(f"Schema validation failed. Missing fields: {missing}")
        return False
        
    # 2. Check metadata field structure if present
    if "metadata" in log and not isinstance(log["metadata"], dict):
        logger.warning("Schema validation failed. 'metadata' field is not a dictionary.")
        return False
        
    if strict and "metadata" not in log:
        logger.warning("Strict validation failed. 'metadata' field is missing.")
        return False
        
    return True


def validate_iso_timestamp(timestamp_str: str) -> bool:
    """
    Asserts whether a timestamp string conforms to normalized ISO 8601 formatting.
    Supports formats like 'YYYY-MM-DDTHH:MM:SS.fffZ' and offsets.
    
    Args:
        timestamp_str: String value representing the timestamp.
        
    Returns:
        bool: True if the format is valid, False otherwise.
    """
    if not timestamp_str or not isinstance(timestamp_str, str):
        return False
        
    # Normalize common 'Z' suffix to UTC offset format for standard isoformat validation
    normalized = timestamp_str.replace("Z", "+00:00").strip()
    
    try:
        datetime.fromisoformat(normalized)
        return True
    except ValueError:
        logger.debug(f"Timestamp standard ISO validation failed for value: '{timestamp_str}'")
        return False


def assert_metadata_keys(log: Dict[str, Any], required_keys: List[str]) -> None:
    """
    Asserts that the metadata dictionary of a log contains specific keys.
    Raises AssertionError with precise debugging information on failure.
    
    Args:
        log: The parsed log payload.
        required_keys: Keys expected within the metadata dictionary.
    """
    assert "metadata" in log, "Log payload does not contain a 'metadata' dictionary."
    metadata = log["metadata"]
    assert isinstance(metadata, dict), "'metadata' field is not a dictionary object."
    
    missing_keys = [key for key in required_keys if key not in metadata]
    assert not missing_keys, f"Metadata is missing expected test keys: {missing_keys}. Current metadata: {metadata}"


# =============================================================================
# 2. PARSER ASSERTION HELPERS
# =============================================================================

def assert_payload_equivalence(
    actual: Dict[str, Any], 
    expected: Dict[str, Any], 
    ignored_keys: Optional[List[str]] = None
) -> None:
    """
    Safely asserts equality between parsed and expected log structures, 
    allowing dynamically generated elements (e.g. dynamic IDs, UUIDs, trace times)
    to be ignored in comparative tests.
    
    Args:
        actual: The generated parsed log payload.
        expected: The gold standard expected log dictionary.
        ignored_keys: List of keys to ignore during comparison.
    """
    ignored = set(ignored_keys) if ignored_keys else set()
    
    # Create copies to prevent mutating source parameters
    actual_clean = {k: v for k, v in actual.items() if k not in ignored}
    expected_clean = {k: v for k, v in expected.items() if k not in ignored}
    
    assert actual_clean == expected_clean, (
        f"Parsed payload mismatch!\n"
        f"Expected (cleansed): {json.dumps(expected_clean, indent=2)}\n"
        f"Actual (cleansed): {json.dumps(actual_clean, indent=2)}"
    )


def assert_valid_severity(level: str) -> None:
    """
    Asserts that the log level is recognized within the platform's standardized list.
    Handles case-insensitivity checks gracefully.
    
    Args:
        level: Severity string (e.g. 'WARN', 'ERROR').
    """
    assert isinstance(level, str), "Log severity level must be a string."
    normalized_level = level.upper().strip()
    assert normalized_level in VALID_LOG_LEVELS, (
        f"Unsupported or unrecognized severity level detected: '{level}'. "
        f"Supported standards: {VALID_LOG_LEVELS}"
    )


# =============================================================================
# 3. MOCK DATA UTILITIES
# =============================================================================

def generate_random_message(service: str, level: str) -> str:
    """
    Generates realistic, randomized logs matching specified service and severity.
    
    Args:
        service: Target mock service name.
        level: Severity level.
        
    Returns:
        str: Realistic message context.
    """
    messages_by_level = {
        "INFO": [
            "HTTP request processed successfully.",
            "Background synchronization task finished.",
            "Connected securely to master database cluster.",
            "Caching layer warm up initialized."
        ],
        "WARN": [
            "Connection pool size reached 80% capability.",
            "API endpoint processing exceeded SLA target threshold.",
            "Disk block usage reaching limit boundaries.",
            "Slow query response detected on analytics database."
        ],
        "ERROR": [
            "Stripe gateway authentication failed.",
            "Resource lookup returned HTTP 404.",
            "Socket connection interrupted mid-request.",
            "Deadlock detected during transaction execution."
        ],
        "CRITICAL": [
            "Primary database instance went offline.",
            "Host storage space exhausted (0% left).",
            "Hardware kernel panic detected.",
            "Infiltration attempts trigger active security block rules."
        ]
    }
    
    # Default message bank
    default_pool = [f"Generic diagnostic event executed for service '{service}'."]
    pool = messages_by_level.get(level.upper(), default_pool)
    return random.choice(pool)


def create_synthetic_log(
    service: Optional[str] = None,
    level: Optional[str] = None,
    message: Optional[str] = None,
    custom_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates a dynamic, valid synthetic log object ready for parser injection tests.
    
    Args:
        service: Mock service name. Falls back to a random service if None.
        level: Severity level. Falls back to 'INFO' if None.
        message: Log message. Falls back to a generated contextual message if None.
        custom_metadata: Optional dictionary to update/overrule default metadata.
        
    Returns:
        Dict[str, Any]: Standardized dynamic log dict.
    """
    mock_services = ["auth-service", "payment-service", "gateway-api", "worker-pool-b"]
    resolved_service = service or random.choice(mock_services)
    resolved_level = (level or "INFO").upper()
    resolved_message = message or generate_random_message(resolved_service, resolved_level)
    
    default_meta = {
        "environment": "testing",
        "uuid": str(uuid.uuid4()),
        "build_version": "v3.1.2-beta"
    }
    
    if custom_metadata:
        default_meta.update(custom_metadata)
        
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "service": resolved_service,
        "level": resolved_level,
        "message": resolved_message,
        "metadata": default_meta
    }


def generate_corrupted_payload(raw_json: str, corruption_type: str = "truncation") -> str:
    """
    Intentionally corrupts structural strings to facilitate negative validation testing.
    
    Args:
        raw_json: Normal valid string representation.
        corruption_type: String strategy: 'truncation', 'unmatched_braces', 'bad_characters'.
        
    Returns:
        str: Intentionally broken text payload.
    """
    if not raw_json:
        return ""
        
    if corruption_type == "truncation":
        # Truncate string roughly in half
        return raw_json[:len(raw_json) // 2]
    elif corruption_type == "unmatched_braces":
        # Remove final wrapping brace
        return raw_json.strip().rstrip("}")
    elif corruption_type == "bad_characters":
        # Introduce control characters inside structural delimiters
        return raw_json.replace('"', '\x00"')
    else:
        return raw_json + " - INVALID APPENDED DATA"


# =============================================================================
# 4. TEST ENVIRONMENT UTILITIES
# =============================================================================

@contextmanager
def temporary_env_variables(env_vars: Dict[str, str]) -> Generator[None, None, None]:
    """
    Safely overrides system environment variables inside a thread-safe context scope,
    completely restoring old values back to their original state upon exit.
    
    Args:
        env_vars: Dict mapping environment variables to temporary string values.
    """
    original_state = {}
    
    try:
        # Cache current configurations
        for key, val in env_vars.items():
            original_state[key] = os.environ.get(key)
            os.environ[key] = val
        yield
    finally:
        # Revert configurations back to absolute original states
        for key, val in original_state.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


@contextmanager
def create_temp_log_file(content: str, prefix: str = "test_log_", suffix: str = ".log") -> Generator[Path, None, None]:
    """
    Creates an isolated temporary file containing the mock logs text, 
    yields the Path reference, and cleans up the storage disk on context exit.
    
    Args:
        content: Text content to write immediately into the temporary file.
        prefix: File prefix string.
        suffix: File extension suffix.
        
    Yields:
        Path: Secure path pointer to the active temporary test file.
    """
    temp_file = tempfile.NamedTemporaryFile(mode="w+", prefix=prefix, suffix=suffix, delete=False)
    file_path = Path(temp_file.name)
    
    try:
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()  # Close the file handle to prevent locks on Windows platform
        yield file_path
    finally:
        # Safely detach filesystem assets after testing phase completes
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as e:
                logger.error(f"Failed to delete test-scope temporary file at {file_path}: {e}")


# =============================================================================
# 5. JSON & SERIALIZATION UTILITIES
# =============================================================================

def is_valid_json(payload: Union[str, bytes]) -> bool:
    """
    Quietly asserts whether string or byte-sequence evaluates to valid standard JSON structure.
    
    Args:
        payload: Binary or unicode text representations.
        
    Returns:
        bool: True if parsed without structure violations, False otherwise.
    """
    if not payload:
        return False
    try:
        json.loads(payload)
        return True
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def safe_serialize_log(log: Dict[str, Any]) -> str:
    """
    Safely converts dictionaries into JSON strings, handling internal types 
    like datetimes and UUID structures gracefully.
    
    Args:
        log: Input dict containing logs data.
        
    Returns:
        str: Fully serialized JSON string.
    """
    class LogaraTestEncoder(json.JSONEncoder):
        def default(self, obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat() + "Z"
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, set):
                return list(obj)
            return super().default(obj)
            
    try:
        return json.dumps(log, cls=LogaraTestEncoder)
    except TypeError as e:
        logger.error(f"Critical serialization mismatch on log schema payload: {e}")
        return "{}"


# =============================================================================
# 6. DEBUGGING & TRACEABILITY HELPERS
# =============================================================================

def pretty_format_log(log: Dict[str, Any]) -> str:
    """
    Generates a human-readable YAML-like formatted output of JSON logs.
    Highly beneficial for reading assertion debug results in console.
    
    Args:
        log: Log dictionary payload.
        
    Returns:
        str: Pretty formatted string output.
    """
    if not log:
        return "<Empty Log Payload>"
        
    lines = []
    # Force top-level visibility ordering
    ordered_keys = ["timestamp", "service", "level", "message", "metadata"]
    extra_keys = sorted(list(set(log.keys()) - set(ordered_keys)))
    
    for key in (ordered_keys + extra_keys):
        if key not in log:
            continue
        val = log[key]
        if isinstance(val, dict):
            lines.append(f"{key}:")
            for sub_k, sub_v in sorted(val.items()):
                lines.append(f"  {sub_k}: {sub_v}")
        else:
            lines.append(f"{key}: {val}")
            
    return "\n".join(lines)


def log_test_step(step_name: str, details: Optional[str] = None) -> None:
    """
    Writes a formatted, easily searchable milestone trace message directly 
    to the active standard output execution stream.
    
    Args:
        step_name: High-level identifier representing current execution stage.
        details: Additional contextual data for log diagnostics.
    """
    border = "=" * 80
    details_str = f"| Details: {details}\n" if details else ""
    logger.info(
        f"\n{border}\n"
        f"🏁 [TEST STEP] {step_name.upper()}\n"
        f"{details_str}"
        f"{border}"
    )