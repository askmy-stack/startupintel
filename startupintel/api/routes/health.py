"""Health check endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from startupintel.api.dependencies import DbDep
from startupintel.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(status="healthy")


@router.get("/health/ready")
async def readiness_check(db: DbDep) -> dict:
    """Readiness probe - checks database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "checks": {"database": "connected"}}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": {"database": f"error: {str(e)}"}}
        )


@router.get("/health/live")
async def liveness_check() -> dict:
    """Liveness probe - basic service check."""
    return {"status": "alive"}

