"""
Logara AI - Pytest Configuration and Centralized Fixtures.

This module acts as the core testing infrastructure for the Logara AI backend.
It handles safe import path resolution, centralized logging configuration,
and provides reusable fixtures for testing log ingestion, semantic processing,
and API routing in isolated environments.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# -------------------------------------------------------------------------
# Path Configuration
# -------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# -------------------------------------------------------------------------
# Pytest Session Configuration
# -------------------------------------------------------------------------
def pytest_configure(config: pytest.Config) -> None:
    """
    Global configuration for the pytest session.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger("faker").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info("🚀 Logara AI Test Session Initialized.")


# -------------------------------------------------------------------------
# Environment & Infrastructure Fixtures
# -------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def isolated_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Automatically applies isolated environment variables to tests.
    """
    monkeypatch.setenv("LOGARA_ENV", "testing")
    monkeypatch.setenv("DEBUG", "true")

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("QDRANT_URL", "http://localhost:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "test_qdrant_key")

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key-do-not-use")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-mock-key")


# -------------------------------------------------------------------------
# Data Payload Fixtures (Valid Data)
# -------------------------------------------------------------------------
@pytest.fixture
def sample_log_entry() -> Dict[str, Any]:
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
    payload = {
        "logs": [sample_log_entry]
    }

    return json.dumps(payload)


@pytest.fixture
def complex_batch_logs() -> List[Dict[str, Any]]:
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
# Data Payload Fixtures (Malformed Data)
# -------------------------------------------------------------------------
@pytest.fixture
def malformed_json_payload() -> str:
    return """{"logs": [{"level": "INFO", "message": "Unfinished string...]"""


@pytest.fixture
def missing_fields_log_entry() -> Dict[str, Any]:
    return {
        "service": "unknown-service",
        "level": "DEBUG",
        "metadata": {"corrupted": True}
    }


# -------------------------------------------------------------------------
# Async & Integration Testing Preparation
# -------------------------------------------------------------------------
@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"