from app_factory import create_app

from integrations.ollama import ollama_client
from integrations.qdrant import qdrant_client
from integrations.redis import redis_client
from qdrant_client import QdrantClient
from utils.parser import PARSER_METRICS
import httpx


app = create_app()


@app.get("/metrics/parser")
async def parser_metrics():
    return {
        "parser_metrics": PARSER_METRICS
    }