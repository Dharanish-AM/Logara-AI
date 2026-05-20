import os
import json

import httpx
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware

from qdrant_client import QdrantClient
from utils.parser import LogParser
from utils.queue import redis_client
from utils.redaction import build_default_redactor
from utils.constants import REDACT_ENABLED, REDACT_PATTERNS, REDACT_IPV4

redactor = build_default_redactor(
    enabled=REDACT_ENABLED,
    pattern_names=REDACT_PATTERNS,
    include_ipv4=REDACT_IPV4,
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

app = FastAPI(
    title="Logara AI API",
    description="Backend for ingestion and analysis of distributed system logs",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Logara AI API",
        "status": "active"
    }


@app.post("/ingest")
async def ingest_logs(log_data: str = Body(..., embed=True)):
    """
    Accepts raw log strings, scrubs secrets/PII, parses them into structured data,
    and pushes the payload to the Redis queue for asynchronous processing.
    """
    if not log_data or not log_data.strip():
        raise HTTPException(
            status_code=400,
            detail="Log message cannot be empty"
        )
    
    # Scrub secrets/PII before any downstream processing
    redaction_result = redactor.redact_with_summary(log_data)

    clean_log = redaction_result.text

    parsed = LogParser.parse_line(clean_log)

    if not parsed:
        return {
            "status": "accepted_raw",
            "message": clean_log
        }

    metadata = parsed.get("metadata", {})
    
    # Scrub nested JSON values too (parser may have extracted secret
    # fields from structured logs that wouldn't match the raw-text regex)
    parsed = redactor.redact_dict(parsed)

    payload = {
        "parsed": parsed,
        "metadata": metadata
    }

    try:
        redis_client.lpush("log_queue", json.dumps(payload))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue log: {str(e)}"
        )

    return {
    "status": "success_queued",
    "parsed": parsed,
    "metadata": metadata,
    "redaction_summary": redaction_result.matches
}

@app.get("/health", status_code=200)
async def health_check(response: Response):
    services = {}
    # Redis check (sync client, already imported as redis_client)
    try:
        redis_client.ping()
        services["redis"] = {"status": "healthy"}
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}
    # Qdrant check (initialize inline, lightweight collections call)
    try:
        qclient = QdrantClient(url=QDRANT_URL, timeout=3)
        qclient.get_collections()
        services["qdrant"] = {"status": "healthy"}
    except Exception as e:
        services["qdrant"] = {"status": "unhealthy", "error": str(e)}
    # Ollama check (HTTP GET to /api/tags with tight timeout)
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3.0)
        if r.status_code == 200:
            services["ollama"] = {"status": "healthy"}
        else:
            services["ollama"] = {"status": "unhealthy", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        services["ollama"] = {"status": "unhealthy", "error": str(e)}
    # Determine overall status
    overall = "unhealthy" if any(
        s["status"] == "unhealthy" for s in services.values()
    ) else "healthy"
    if overall == "unhealthy":
        response.status_code = 503
    return {
        "status": overall,
        "services": services
    }
