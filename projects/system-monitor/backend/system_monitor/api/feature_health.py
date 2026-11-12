"""回報本專案實際功能檢查，功能失敗仍保留其餘檢查結果。"""
from fastapi import APIRouter
from system_monitor.schemas.feature_health import ProjectHealthReport
from system_monitor.services.feature_health_service import get_feature_health

router = APIRouter()

@router.get("/feature-health", response_model=ProjectHealthReport)
def feature_health(force: bool = False) -> ProjectHealthReport:
    return get_feature_health(force=force)
