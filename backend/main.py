from app_factory import create_app
from integrations.ollama import ollama_client
from integrations.qdrant import qdrant_client
from integrations.redis import redis_client
from qdrant_client import QdrantClient
import httpx

app = create_app()