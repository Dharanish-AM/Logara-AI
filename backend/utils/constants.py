"""
constants.py - Shared constants for the log parsing system.
"""

# Schema field names
SCHEMA_TIMESTAMP = "timestamp"
SCHEMA_LEVEL = "level"
SCHEMA_MESSAGE = "message"
SCHEMA_METADATA = "metadata"
SCHEMA_PARSER_TYPE = "parser_type"
SCHEMA_RAW = "raw"

# Metadata keys
META_SERVICE = "service"

# Default values
DEFAULT_LEVEL = "INFO"

import os

REDACT_ENABLED = os.getenv("REDACT_ENABLED", "true").lower() == "true"
REDACT_PATTERNS = os.getenv(
    "REDACT_PATTERNS",
    "jwt,aws_access_key,api_key,bearer,email,credit_card"
).split(",")
REDACT_IPV4 = os.getenv("REDACT_IPV4", "false").lower() == "true"