"""
GET /search — Semantic log search endpoint.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from schemas.search import SearchResult
from services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])

# Module-level instance — lazy model/client initialisation happens inside
# SearchService on first call, not at import time.
_service = SearchService()


@router.get("", response_model=list[SearchResult])
def search_logs(
    query: str = Query(..., description="Natural language search query"),
    service_id: Optional[str] = Query(
        None, description="Filter results by service partition"
    ),
    limit: int = Query(
        10, ge=1, le=50, description="Maximum number of results (1-50)"
    ),
) -> list[SearchResult]:
    """
    Perform semantic similarity search over stored log vectors.

    Returns the top-`limit` most similar log records, ranked by cosine
    similarity.  When `service_id` is provided the search is restricted to
    that service partition using the Qdrant keyword payload index.
    """
    try:
        return _service.search(query=query, service_id=service_id, limit=limit)
    except Exception as e:
        logger.error(f"Search request failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Search unavailable: {e}",
        )
