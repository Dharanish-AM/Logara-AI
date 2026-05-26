"""
Application settings loaded from environment variables.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Logara AI API"
    app_description: str = (
        "Backend for ingestion and analysis of distributed system logs"
    )
    app_version: str = "0.1.0"
    redis_queue_name: str = "log_queue"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None

    qdrant_url: str = "http://localhost:6333"
    qdrant_timeout_seconds: float = 3.0
    qdrant_collection: str = "logs"
    qdrant_cluster_collection: str = "log_clusters"

    duplicate_similarity_threshold: float = 0.92
    max_cluster_sample_size: int = 5
    enable_duplicate_clustering: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_health_path: str = "/api/tags"
    health_timeout_seconds: float = 3.0

    redact_enabled: bool = True
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            "jwt",
            "aws_access_key",
            "api_key",
            "bearer",
            "email",
            "credit_card",
        ]
    )
    redact_ipv4: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
