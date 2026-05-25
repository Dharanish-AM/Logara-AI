"""
Pydantic schemas for the /search endpoint.
"""
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """A single log result returned from semantic similarity search."""

    id: str
    score: float
    message: str
    level: str
    timestamp: str | None = None
    service_id: str
    metadata: dict


class SearchRequest(BaseModel):
    """Query parameters for semantic log search."""

    query: str = Field(..., description="Natural language search query")
    service_id: str | None = Field(
        None, description="Filter results to a specific service partition"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )
