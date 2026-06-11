"""
ExplainService — RAG pipeline that retrieves relevant context logs from
Qdrant and feeds them to Ollama to generate a root-cause explanation.
"""

import logging
from typing import Optional

import httpx

from core.settings import get_settings
from schemas.explain import ExplainRequest, ExplainResponse
from schemas.search import SearchResult
from services.search import SearchService
from services.incident_memory import IncidentMemoryService

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert site reliability engineer analyzing distributed system logs. "
    "Given context logs and an error message, provide:\n"
    "1. A concise explanation of what the error means\n"
    "2. The likely root cause based on the context logs\n"
    "3. Actionable remediation steps\n\n"
    "Be specific and technical. Prioritise patterns visible in the context logs."
)


def _build_prompt(error_message: str, context_logs: list[SearchResult]) -> str:
    """
    Construct the RAG prompt from the error and retrieved context logs.

    When context logs are available they are numbered and prefixed with
    their level, timestamp, and service so the LLM can reason about timing
    and service boundaries.
    """
    parts: list[str] = []

    if context_logs:
        parts.append("Context logs from the system:")
        for i, log in enumerate(context_logs, 1):
            ts = log.timestamp or "unknown time"
            parts.append(
                f"  [{i}] [{log.level}] {ts} (service: {log.service_id}): {log.message}"
            )
        parts.append("")  # blank line separator

    parts.append(f"Error to explain:\n{error_message}")
    return "\n".join(parts)


class ExplainService:
    """
    RAG-powered error explanation using Ollama for local LLM inference.

    Steps:
      1. Retrieve the top-K semantically similar logs via SearchService.
      2. Build a structured prompt embedding those context logs.
      3. POST to Ollama's /api/generate endpoint (non-streaming).
      4. Return the explanation alongside the context logs used.

    Ollama is called directly with httpx.AsyncClient — no LangChain
    dependency — keeping the service footprint small.
    """


    def __init__(
        self,
        search_service: Optional[SearchService] = None,
        incident_memory_service: Optional[IncidentMemoryService] = None,
    ) -> None:

        self._search = search_service or SearchService()

        self._incident_memory = incident_memory_service or IncidentMemoryService()

    async def explain(self, request: ExplainRequest) -> ExplainResponse:
        """
        Generate a root-cause explanation for the given error message.

        Args:
            request: ExplainRequest containing error_message, optional
                     service_id filter, and context_limit.

        Returns:
            ExplainResponse with LLM explanation, context logs, and model name.

        Raises:
            httpx.ConnectError:     Ollama is not reachable.
            httpx.TimeoutException: Ollama took too long to respond.
            httpx.HTTPStatusError:  Ollama returned a non-2xx status.
        """
        settings = get_settings()

        cached_incident = self._incident_memory.search_similar_incident(
            request.error_message
        )

        if (
            cached_incident
            and cached_incident.score >= settings.incident_similarity_threshold
        ):

            logger.info(
                f"Using cached RCA explanation " f"(score={cached_incident.score:.2f})"
            )

            return ExplainResponse(
                explanation=cached_incident.explanation,
                context_logs=[],
                model=f"{settings.ollama_model} (cached)",
            )

        # Step 1: Retrieve relevant context logs
        context_logs = self._search.search(
            query=request.error_message,
            service_id=request.service_id,
            limit=request.context_limit,
        )

        # Step 2: Build prompt
        prompt = _build_prompt(request.error_message, context_logs)

        # Step 3: Call Ollama /api/generate
        ollama_url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"

        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(
                ollama_url,
                json={
                    "model": settings.ollama_model,
                    "system": _SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()

        explanation = data.get("response", "").strip()
        if not explanation:
            logger.warning(
                "Ollama returned an empty 'response' field — "
                "check that the model is pulled and the prompt is valid."
            )

        else:
            self._incident_memory.store_incident(
                error_message=request.error_message,
                explanation=explanation,
                service_id=request.service_id,
            )

        return ExplainResponse(
            explanation=explanation,
            context_logs=context_logs,
            model=settings.ollama_model,
        )
