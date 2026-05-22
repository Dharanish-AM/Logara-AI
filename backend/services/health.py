"""
Health-check service helpers.
"""

import httpx

from integrations.ollama import ollama_client
from integrations.qdrant import qdrant_client
from integrations.redis import redis_client


class HealthService:
    def check_services(self) -> dict:
        services = {}

        try:
            redis_client.ping()
            services["redis"] = {"status": "healthy"}
        except Exception as exc:
            services["redis"] = {"status": "unhealthy", "error": str(exc)}

        try:
            qdrant_client.get_collections()
            services["qdrant"] = {"status": "healthy"}
        except Exception as exc:
            services["qdrant"] = {"status": "unhealthy", "error": str(exc)}

        try:
            result = ollama_client.health_check()
            if result["status_code"] == 200:
                services["ollama"] = {"status": "healthy"}
            else:
                services["ollama"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {result['status_code']}",
                }
        except httpx.HTTPError as exc:
            services["ollama"] = {"status": "unhealthy", "error": str(exc)}
        except Exception as exc:
            services["ollama"] = {"status": "unhealthy", "error": str(exc)}

        overall = (
            "unhealthy"
            if any(service["status"] == "unhealthy" for service in services.values())
            else "healthy"
        )

        return {
            "status": overall,
            "services": services,
        }
