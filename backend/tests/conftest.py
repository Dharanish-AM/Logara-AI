"""
feat/enhanced-log-parser
Logara AI - Pytest Configuration and Centralized Fixtures.

This module acts as the core testing infrastructure for the Logara AI backend.
It handles safe import path resolution, centralized logging configuration, 
and provides reusable fixtures for testing log ingestion, semantic processing, 
and API routing in isolated environments.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# -------------------------------------------------------------------------
# Path Configuration
# -------------------------------------------------------------------------
# Defensively resolve the absolute path to the backend root directory to
# ensure tests can be run from any working directory (e.g., project root, 
# backend root, or inside tests/) without ModuleNotFoundError.
BACKEND_ROOT = Path(__file__).resolve().parent.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# -------------------------------------------------------------------------
# Pytest Session Configuration
# -------------------------------------------------------------------------
def pytest_configure(config: pytest.Config) -> None:
    """
    Global configuration for the pytest session.
    Configures centralized standard Python logging to improve visibility 
    and debugging during complex backend test runs.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Silence overly verbose third-party loggers if necessary
    logging.getLogger("faker").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logging.info("🚀 Logara AI Test Session Initialized.")


# -------------------------------------------------------------------------
# Environment & Infrastructure Fixtures
# -------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def isolated_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Automatically applies a safe, isolated set of environment variables 
    to every test. Prevents tests from accidentally hitting production 
    databases or live LLM/Vector DB providers.
    """
    monkeypatch.setenv("LOGARA_ENV", "testing")
    monkeypatch.setenv("DEBUG", "true")
    
    # Mock Database & Vector Store URIs
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test_qdrant_key")
    
    # Mock LLM API Keys
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key-do-not-use")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-mock-key")


# -------------------------------------------------------------------------
# Data Payload Fixtures (Valid Data)
# -------------------------------------------------------------------------
@pytest.fixture
def sample_log_entry() -> Dict[str, Any]:
    """
    Provides a standardized, valid dictionary representation of a log entry.
    Useful for testing core data models, parsers, and semantic processors.
    """
    return {
        "timestamp": "2026-05-21T19:30:55.000Z",
        "service": "payment-gateway",
        "level": "ERROR",
        "message": "Connection timeout while attempting to reach Stripe API.",
        "metadata": {
            "trace_id": "tr_1092830192",
            "user_id": "usr_99812",
            "latency_ms": 5002
        }
    }

@pytest.fixture
def sample_json_log_payload(sample_log_entry: Dict[str, Any]) -> str:
    """
    Provides a valid JSON string containing an array of log entries.
    Ideal for simulating incoming HTTP requests to the ingestion API.
    """
    payload = {
        "logs": [sample_log_entry]
    }
    return json.dumps(payload)

@pytest.fixture
def complex_batch_logs() -> List[Dict[str, Any]]:
    """
    Provides a batch of multiple log entries with varying severity levels 
    to test aggregation, filtering, and bulk insert workflows.
    """
    return [
        {
            "timestamp": "2026-05-21T19:30:50.000Z",
            "service": "auth-service",
            "level": "INFO",
            "message": "User login successful.",
        },
        {
            "timestamp": "2026-05-21T19:30:51.000Z",
            "service": "auth-service",
            "level": "WARN",
            "message": "Rate limit threshold approaching for IP 192.168.1.5",
        },
        {
            "timestamp": "2026-05-21T19:30:55.000Z",
            "service": "payment-gateway",
            "level": "ERROR",
            "message": "Connection timeout while attempting to reach Stripe API.",
        }
    ]


# -------------------------------------------------------------------------
# Data Payload Fixtures (Edge Cases & Malformed Data)
# -------------------------------------------------------------------------
@pytest.fixture
def malformed_json_payload() -> str:
    """
    Provides an invalid JSON string (missing closing brace/quotes).
    Used to verify that the ingestion endpoints fail gracefully and 
    return appropriate 400 Bad Request responses.
    """
    return """{"logs": [{"level": "INFO", "message": "Unfinished string...]"""

@pytest.fixture
def missing_fields_log_entry() -> Dict[str, Any]:
    """
    Provides a log entry dictionary missing required schema fields 
    (e.g., missing 'timestamp' and 'message'). Tests Pydantic validation.
    """
    return {
        "service": "unknown-service",
        "level": "DEBUG",
        # Missing 'timestamp'
        # Missing 'message'
        "metadata": {"corrupted": True}
    }


# -------------------------------------------------------------------------
# Async & Integration Testing Preparation
# -------------------------------------------------------------------------
@pytest.fixture
def anyio_backend() -> str:
    """
    Configuration for AnyIO, enabling asynchronous testing support for FastAPI 
    routers and async background tasks. Defaults to using asyncio.
    """
    return "asyncio"
  
Pytest configuration for backend tests.
Ensures backend modules are importable during test execution.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
