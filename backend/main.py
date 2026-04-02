from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from utils.parser import LogParser

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
    return {"message": "Welcome to Logara AI API", "status": "active"}

@app.post("/ingest")
async def ingest_logs(log_data: str = Body(..., embed=True)):
    """
    Accepts raw log strings and parses them into structured data.
    In production, this would queue for vectorization.
    """
    parsed = LogParser.parse_line(log_data)
    if not parsed:
         return {"status": "accepted_raw", "message": log_data}
    
    metadata = LogParser.extract_metadata(parsed["message"])
    return {
        "status": "success",
        "parsed": parsed,
        "metadata": metadata
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
