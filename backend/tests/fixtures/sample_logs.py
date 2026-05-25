"""
Logara AI - Reusable Sample Log Fixtures

This module provides a centralized, scalable library of realistic log payloads
for testing ingestion, parsing, semantic search, and observability workflows.

The logs are categorized by functional areas (Standard, Infrastructure, Security, 
Performance, JSON, and Malformed) to ensure comprehensive test coverage of the 
Logara AI backend services.
"""

from typing import Any, Dict, List

# =============================================================================
# 1. STANDARD LOGS (Grouped by Severity)
# =============================================================================

LOG_INFO_STARTUP: Dict[str, Any] = {
    "timestamp": "2026-05-21T08:15:30.123Z",
    "service": "user-service",
    "level": "INFO",
    "message": "Application started successfully. Listening on port 8080.",
    "metadata": {"environment": "production", "version": "v2.1.4"}
}

LOG_DEBUG_PAYLOAD: Dict[str, Any] = {
    "timestamp": "2026-05-21T08:16:01.002Z",
    "service": "payment-gateway",
    "level": "DEBUG",
    "message": "Processing Stripe webhook payload.",
    "metadata": {"event_id": "evt_90210", "processing_time_ms": 12}
}

LOG_WARN_DEPRECATION: Dict[str, Any] = {
    "timestamp": "2026-05-21T08:20:45.000Z",
    "service": "api-gateway",
    "level": "WARN",
    "message": "Client is using deprecated API endpoint /v1/users.",
    "metadata": {"client_ip": "198.51.100.23", "user_agent": "axios/0.21.1"}
}

LOG_ERROR_DB_TIMEOUT: Dict[str, Any] = {
    "timestamp": "2026-05-21T08:25:12.450Z",
    "service": "inventory-service",
    "level": "ERROR",
    "message": "PostgreSQL connection timeout after 5000ms.",
    "metadata": {"db_host": "db-pool.internal", "query": "SELECT * FROM inventory"}
}

LOG_CRITICAL_OOM: Dict[str, Any] = {
    "timestamp": "2026-05-21T08:25:13.001Z",
    "service": "inventory-service",
    "level": "CRITICAL",
    "message": "Out of Memory (OOM) Killer terminated process.",
    "metadata": {"memory_usage_mb": 4096, "limit_mb": 4096, "pid": 1042}
}


# =============================================================================
# 2. INFRASTRUCTURE & SERVICE LOGS
# =============================================================================

INFRA_K8S_RESTART: Dict[str, Any] = {
    "timestamp": "2026-05-21T09:01:10.000Z",
    "service": "kubelet",
    "level": "WARN",
    "message": "Pod inventory-service-deployment-85b8c9d-abc12 restarting due to Liveness probe failure.",
    "metadata": {"pod_name": "inventory-service", "namespace": "prod"}
}

INFRA_REDIS_CONN_FAIL: Dict[str, Any] = {
    "timestamp": "2026-05-21T09:05:00.222Z",
    "service": "cache-layer",
    "level": "ERROR",
    "message": "Failed to connect to Redis cluster: Connection refused.",
    "metadata": {"host": "redis-cluster.internal", "port": 6379, "retry_count": 3}
}

INFRA_OTEL_TRACE: Dict[str, Any] = {
    "timestamp": "2026-05-21T09:10:05.111Z",
    "service": "checkout-service",
    "level": "INFO",
    "message": "Checkout transaction completed.",
    "metadata": {
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
        "span_id": "00f067aa0ba902b7",
        "duration_ms": 142.5
    }
}


# =============================================================================
# 3. SECURITY & AUTHENTICATION LOGS
# =============================================================================

SEC_AUTH_FAIL_BRUTE: Dict[str, Any] = {
    "timestamp": "2026-05-21T10:15:30.000Z",
    "service": "auth-service",
    "level": "WARN",
    "message": "Multiple failed login attempts detected.",
    "metadata": {"username": "admin", "client_ip": "203.0.113.45", "attempts": 15}
}

SEC_SUSPICIOUS_IP: Dict[str, Any] = {
    "timestamp": "2026-05-21T10:16:05.000Z",
    "service": "waf-proxy",
    "level": "CRITICAL",
    "message": "Blocked request from known malicious IP address.",
    "metadata": {"client_ip": "198.51.100.99", "rule_id": "WAF_BLOCK_THREAT_INTEL"}
}

SEC_TOKEN_EXPIRED: Dict[str, Any] = {
    "timestamp": "2026-05-21T10:20:00.000Z",
    "service": "api-gateway",
    "level": "INFO",
    "message": "Access token expired.",
    "metadata": {"user_id": "usr_789", "token_jti": "jti_445566"}
}


# =============================================================================
# 4. PERFORMANCE & OBSERVABILITY LOGS
# =============================================================================

PERF_HIGH_LATENCY: Dict[str, Any] = {
    "timestamp": "2026-05-21T11:00:15.500Z",
    "service": "search-service",
    "level": "WARN",
    "message": "Query execution time exceeded SLA threshold.",
    "metadata": {"query_time_ms": 2500, "threshold_ms": 1000, "endpoint": "/search"}
}

PERF_CPU_WARN: Dict[str, Any] = {
    "timestamp": "2026-05-21T11:05:00.000Z",
    "service": "ml-inference-worker",
    "level": "WARN",
    "message": "CPU utilization sustained above 90% for 5 minutes.",
    "metadata": {"cpu_utilization": 94.2, "worker_node": "node-ml-03"}
}


# =============================================================================
# 5. STRUCTURED JSON LOGS (Raw Strings for Parser Tests)
# =============================================================================

JSON_LOG_STANDARD: str = (
    '{"timestamp": "2026-05-21T12:00:00Z", "service": "billing", '
    '"level": "INFO", "message": "Invoice generated successfully", '
    '"metadata": {"invoice_id": "inv_123"}}'
)

JSON_LOG_NESTED_METADATA: str = (
    '{"timestamp": "2026-05-21T12:01:00Z", "service": "billing", '
    '"level": "ERROR", "message": "Payment failed", '
    '"metadata": {"user": {"id": 1, "tier": "pro"}, "error": {"code": 500, "reason": "gateway_timeout"}}}'
)


# =============================================================================
# 6. EDGE CASES & MALFORMED LOGS (Negative Testing)
# =============================================================================

EDGE_EMPTY_LOG: Dict[str, Any] = {}

EDGE_WHITESPACE_LOG: Dict[str, Any] = {
    "timestamp": "   ",
    "service": "   ",
    "level": "   ",
    "message": "   "
}

EDGE_INCOMPLETE_TIMESTAMP: Dict[str, Any] = {
    "timestamp": "2026-05-21",  # Missing time component
    "service": "frontend-app",
    "level": "INFO",
    "message": "App loaded."
}

MALFORMED_MISSING_LEVEL: Dict[str, Any] = {
    "timestamp": "2026-05-21T13:00:00Z",
    "service": "frontend-app",
    # "level" is missing entirely
    "message": "User clicked checkout."
}

MALFORMED_CORRUPTED_JSON: str = (
    '{"timestamp": "2026-05-21T13:05:00Z", "service": "auth", '
    '"level": "INFO", "message": "Missing closing quote for this string, '
    '"metadata": {}}'
)


# =============================================================================
# 7. EXPORTED COLLECTIONS (For parameterizing tests)
# =============================================================================

ALL_STANDARD_LOGS: List[Dict[str, Any]] = [
    LOG_INFO_STARTUP,
    LOG_DEBUG_PAYLOAD,
    LOG_WARN_DEPRECATION,
    LOG_ERROR_DB_TIMEOUT,
    LOG_CRITICAL_OOM
]

ALL_SECURITY_LOGS: List[Dict[str, Any]] = [
    SEC_AUTH_FAIL_BRUTE,
    SEC_SUSPICIOUS_IP,
    SEC_TOKEN_EXPIRED
]

ALL_MALFORMED_LOGS: List[Dict[str, Any]] = [
    EDGE_EMPTY_LOG,
    EDGE_WHITESPACE_LOG,
    EDGE_INCOMPLETE_TIMESTAMP,
    MALFORMED_MISSING_LEVEL
]