"""
Pydantic schemas for the /explain endpoint.
"""
from pydantic import BaseModel, Field

from schemas.search import SearchResult


class ExplainRequest(BaseModel):
    """Request body for RAG-powered error explanation."""

    error_message: str = Field(
        ..., description="The error message or log line to explain"
    )
    service_id: str | None = Field(
        None, description="Restrict context retrieval to a specific service"
    )
    context_limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of similar context logs to retrieve for the prompt",
    )


class ExplainResponse(BaseModel):
    """LLM-generated explanation with supporting context logs."""

    explanation: str
    context_logs: list[SearchResult]
    model: str
