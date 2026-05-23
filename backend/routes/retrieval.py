"""
Log retrieval and semantic search routes.
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.log_service import LogService


router = APIRouter()


class LogDTO(BaseModel):
    id: str
    timestamp: Optional[str] = None
    level: str
    message: str
    parser_type: Optional[str] = None
    raw: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class LogListResponse(BaseModel):
    logs: List[LogDTO]
    pagination: PaginationInfo


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = Field(default=5, ge=1, le=50)


class SearchResponse(BaseModel):
    logs: List[LogDTO]
    answer: Optional[str] = None


def get_log_service() -> LogService:
    """
    Retrieve or initialize the global LogService instance.
    """
    from main import app
    
    if not hasattr(app.state, "log_service"):
        from integrations.qdrant import qdrant_client
        app.state.log_service = LogService(qdrant_client)
    
    return app.state.log_service


@router.get("/logs", response_model=LogListResponse)
async def get_logs(
    page: int = 1,
    limit: int = 10,
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
):
    """
    Retrieve logs with support for pagination, level filtering,
    optional timestamp range filtering, and sorting by latest logs.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page number must be 1 or greater")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    try:
        log_service = get_log_service()
        logs, total = log_service.get_logs(
            page=page,
            limit=limit,
            level=level,
            start_time=start_time,
            end_time=end_time
        )
        pages = (total + limit - 1) // limit if total > 0 else 0

        return LogListResponse(
            logs=[LogDTO(**log) for log in logs],
            pagination=PaginationInfo(
                page=page,
                limit=limit,
                total=total,
                pages=pages
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Perform semantic vector search using Qdrant and synthesize a response using local Ollama.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )

    try:
        log_service = get_log_service()
        logs, answer = log_service.semantic_search(
            query=request.query,
            limit=request.limit
        )

        return SearchResponse(
            logs=[LogDTO(**log) for log in logs],
            answer=answer
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute semantic search: {str(e)}"
        )
