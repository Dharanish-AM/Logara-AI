"""
AI service routes including Ollama model status.
"""

import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def get_ai_status(request: Request):
    """
    Get the status of AI models (particularly Ollama).
    
    Returns current state of the Ollama model manager including:
    - status: Current state (idle, checking, pulling, ready, failed)
    - model: Model name being managed
    - progress: Download progress percentage (0-100)
    - error: Error message if status is failed
    """
    try:
        ollama_manager = request.app.state.ollama_manager
        status = ollama_manager.get_status()
        
        return {
            "status": status["status"],
            "model": status["model"],
            "progress": status["progress"],
            "error": status["error"],
        }
    except AttributeError:
        logger.error("Ollama manager not initialized")
        return {
            "status": "failed",
            "model": None,
            "progress": 0,
            "error": "Ollama manager not initialized",
        }
    except Exception as e:
        logger.error(f"Error getting AI status: {e}", exc_info=True)
        return {
            "status": "failed",
            "model": None,
            "progress": 0,
            "error": str(e),
        }
