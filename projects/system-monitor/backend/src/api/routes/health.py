"""功能健康報告 HTTP 入口；將同次檢查結果轉成公開 Schema。"""
from fastapi import APIRouter, Depends
from ..dependencies import get_health_service
from ..schemas.health import ProjectHealthReport
from ...domain.serialization import to_dict
from ...services.health import HealthService

router = APIRouter()


@router.get("/feature-health", response_model=ProjectHealthReport)
def feature_health(force: bool = False, service: HealthService = Depends(get_health_service)) -> ProjectHealthReport:
    return ProjectHealthReport.model_validate(to_dict(service.get_feature_health(force=force)))
