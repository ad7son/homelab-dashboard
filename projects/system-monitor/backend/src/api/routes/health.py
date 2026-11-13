"""功能健康報告 HTTP 入口；將同次檢查結果轉成公開 Schema。"""

from __future__ import annotations

import fastapi

from .. import dependencies
from ...domain import serialization
from ...services import health as services_health
from ..schemas import health

router = fastapi.APIRouter()


@router.get("/feature-health", response_model=health.ProjectHealthReport)
def feature_health(
    force: bool = False,
    service: services_health.HealthService = fastapi.Depends(
        dependencies.get_health_service
    ),
) -> health.ProjectHealthReport:
    """回傳此專案功能的同次檢查結果與原始證據。

    Args:
        force: True 時略過整份報告快取，重新執行檢查。
        service: 共用快取與最近成功時間的健康服務。

    Returns:
        單一專案的功能健康報告；各項失敗由服務隔離。
    """
    return health.ProjectHealthReport.model_validate(
        serialization.to_dict(service.get_feature_health(force=force))
    )
