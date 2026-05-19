from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware

from utils.parser import LogParser
from utils.queue import redis_client

import json

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
    Accepts raw log strings, parses them into structured data,
    and pushes the payload to the Redis queue for asynchronous processing.
    """
    if not log_data or not log_data.strip():
        raise HTTPException(
            status_code=400,
            detail="Log message cannot be empty"
        )

    parsed = LogParser.parse_line(log_data)

    if not parsed:
        return {
            "status": "accepted_raw",
            "message": log_data
        }

    metadata = parsed.get("metadata", {})

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
        "metadata": metadata
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}