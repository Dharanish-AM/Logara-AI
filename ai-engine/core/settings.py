"""
Application settings for the AI Engine, loaded from environment variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the root .env shared across all services
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "logs"
    incident_memory_collection: str = "incident_memory"
    incident_similarity_threshold: float = 0.95

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_timeout_seconds: float = 60.0

    # Embedding
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Service defaults
    ai_engine_search_limit: int = 10
    ai_engine_context_limit: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
