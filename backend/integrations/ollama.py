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

    async def get_models(self) -> list:
        """
        Get list of available models from Ollama.
        
        Returns:
            List of model names (e.g., ["llama3", "mistral"])
        """
        settings = get_settings()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.ollama_base_url}/api/tags",
                    timeout=settings.health_timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
        except Exception as e:
            raise Exception(f"Failed to fetch models from Ollama: {e}")

    async def pull_model(self, model_name: str) -> dict:
        """
        Pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to pull (e.g., "llama3")
            
        Returns:
            Dictionary with pull operation status
        """
        settings = get_settings()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/pull",
                    json={"name": model_name},
                    timeout=None,
                )
                response.raise_for_status()
                return {"status": "success", "model": model_name}
        except Exception as e:
            raise Exception(f"Failed to pull model '{model_name}': {e}")


ollama_client = OllamaClient()
