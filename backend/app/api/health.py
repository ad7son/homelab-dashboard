from fastapi import APIRouter

from app.config import A7LAS_VERSION
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    """僅回報平台存活狀態，不執行各專案的採集與健康檢查。"""
    return HealthResponse(status="ok", version=A7LAS_VERSION)
