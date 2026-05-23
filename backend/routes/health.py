"""
Health-check routes.
"""

from fastapi import APIRouter, Depends, Response

from services.health import HealthService


router = APIRouter()


def get_health_service() -> HealthService:
    return HealthService()


@router.get("/health", status_code=200)
async def health_check(
    response: Response,
    health_service: HealthService = Depends(get_health_service),
):
    result = health_service.check_services()
    if result["status"] == "unhealthy":
        response.status_code = 503
    return result
