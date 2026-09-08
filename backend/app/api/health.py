from fastapi import APIRouter

from app.config import A7LAS_VERSION
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    """Backend liveness only — does not inspect monitored systemd services."""
    return HealthResponse(status="ok", version=A7LAS_VERSION)
