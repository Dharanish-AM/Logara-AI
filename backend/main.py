import os
import json
import threading

import httpx
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware

from qdrant_client import QdrantClient
from utils.parser import LogParser
from utils.otel import parse_otel_log_payload
from utils.queue import redis_client
from utils.redaction import build_default_redactor
from utils.constants import REDACT_ENABLED, REDACT_PATTERNS, REDACT_IPV4
from services.log_service import LogService
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

redactor = build_default_redactor(
    enabled=REDACT_ENABLED,
    pattern_names=REDACT_PATTERNS,
    include_ipv4=REDACT_IPV4,
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

class ThreadSafeQdrantClient:
    """
    Thread-safe, lazy-initialized, and mock-friendly wrapper for QdrantClient.
    Acts as a transparent proxy to optimize connection pooling in production
    while staying compatible with runtime test mocks.
    """
    def __init__(self):
        self._client = None
        self._last_class = None
        self._lock = threading.Lock()

    @property
    def client(self) -> QdrantClient:
        # If QdrantClient class in global namespace changes (e.g. mock patching),
        # re-instantiate it so that the new mock/stub is properly used.
        if self._client is None or self._last_class is not QdrantClient:
            with self._lock:
                if self._client is None or self._last_class is not QdrantClient:
                    self._client = QdrantClient(url=QDRANT_URL, timeout=3)
                    self._last_class = QdrantClient
        return self._client

    def close(self):
        """
        Close the underlying Qdrant client connection if initialized.
        """
        if self._client is not None:
            try:
                self._client.close()
            except AttributeError:
                pass

    def __getattr__(self, name):
        return getattr(self.client, name)

qclient = ThreadSafeQdrantClient()
log_service = LogService(qclient)


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


@app.post("/v1/logs")
async def ingest_otel_logs(payload: dict = Body(...)):
    """
    Accepts batch OpenTelemetry (OTLP) log records, parses and normalizes them,
    scrubs PII/secrets, and queues each record into Redis for asynchronous processing.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    try:
        records = parse_otel_log_payload(payload)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse OTel logs: {str(e)}"
        )

    if not records:
        return {
            "status": "success",
            "processed_records": 0,
            "redaction_summary": {}
        }

    queued_count = 0
    total_redaction_matches = {}

    for record in records:
        # Scrub secrets/PII from the main message
        redact_res = redactor.redact_with_summary(record["message"])
        record["message"] = redact_res.text
        record["raw"] = redact_res.text

        # Merge redaction summaries for overall reporting
        for label, count in redact_res.matches.items():
            total_redaction_matches[label] = total_redaction_matches.get(label, 0) + count

        # Scrub nested JSON fields recursively
        record = redactor.redact_dict(record)

        queue_payload = {
            "parsed": record,
            "metadata": record.get("metadata", {})
        }

        try:
            redis_client.lpush("log_queue", json.dumps(queue_payload))
            queued_count += 1
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue log record at index {queued_count}: {str(e)}"
            )

    return {
        "status": "success",
        "processed_records": queued_count,
        "redaction_summary": total_redaction_matches
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
    # Qdrant check (reusable thread-safe global client, lightweight collections call)
    try:
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


class LogDTO(BaseModel):
    id: str
    timestamp: Optional[str] = None
    level: str
    message: str
    parser_type: Optional[str] = None
    raw: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class LogListResponse(BaseModel):
    logs: List[LogDTO]
    pagination: PaginationInfo


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = Field(default=5, ge=1, le=50)


class SearchResponse(BaseModel):
    logs: List[LogDTO]
    answer: Optional[str] = None


@app.get("/logs", response_model=LogListResponse)
async def get_logs(
    page: int = 1,
    limit: int = 10,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
):
    """
    Retrieve logs with support for pagination, level filtering,
    optional timestamp range filtering, and sorting by latest logs.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page number must be 1 or greater")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        logs, total = log_service.get_logs(
            page=page,
            limit=limit,
            level=level,
            start_time=start_time,
            end_time=end_time
        )
        pages = (total + limit - 1) // limit if total > 0 else 0

        return LogListResponse(
            logs=[LogDTO(**log) for log in logs],
            pagination=PaginationInfo(
                page=page,
                limit=limit,
                total=total,
                pages=pages
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@app.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic vector search using Qdrant and synthesize a response using local Ollama.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )

    try:
        logs, answer = log_service.semantic_search(
            query=request.query,
            limit=request.limit
        )

        return SearchResponse(
            logs=[LogDTO(**log) for log in logs],
            answer=answer
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute semantic search: {str(e)}"
        )
