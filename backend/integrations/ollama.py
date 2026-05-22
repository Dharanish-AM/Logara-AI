"""
Ollama integration helpers.
"""

import httpx

from core.settings import get_settings


class OllamaClient:
    def health_check(self) -> dict:
        settings = get_settings()
        response = httpx.get(
            f"{settings.ollama_base_url}{settings.ollama_health_path}",
            timeout=settings.health_timeout_seconds,
        )
        return {"status_code": response.status_code}


ollama_client = OllamaClient()
