"""
POST /explain — RAG-powered error explanation endpoint.
"""
import logging

import httpx
from fastapi import APIRouter, HTTPException

from schemas.explain import ExplainRequest, ExplainResponse
from services.explain import ExplainService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explain", tags=["explain"])

_service = ExplainService()


@router.post("", response_model=ExplainResponse)
async def explain_error(request: ExplainRequest) -> ExplainResponse:
    """
    Generate a root-cause analysis for the supplied error message.

    Retrieves semantically similar context logs from Qdrant and passes them
    to Ollama together with the error to produce a structured explanation.
    """
    try:
        return await _service.explain(request)
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(
            status_code=503,
            detail=(
                "LLM engine (Ollama) is unreachable. "
                "Ensure Ollama is running and OLLAMA_BASE_URL is correct."
            ),
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="LLM engine timed out generating a response. Try again or reduce context_limit.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM engine returned HTTP {e.response.status_code}.",
        )
    except Exception as e:
        logger.error(f"Explain request failed unexpectedly: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {e}")
