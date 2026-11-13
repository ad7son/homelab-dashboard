"""即時總覽 HTTP 入口；不執行硬體與儲存操作。"""

from __future__ import annotations

import fastapi

from .. import dependencies
from ...domain import serialization
from ...services import overview as services_overview
from ..schemas import overview

router = fastapi.APIRouter()


@router.get("/overview", response_model=overview.Overview)
def read_overview(
    service: services_overview.OverviewService = fastapi.Depends(
        dependencies.get_overview_service
    ),
) -> overview.Overview:
    """取得並驗證五項主機快照。

    Args:
        service: 由平台設定取得的總覽服務。

    Returns:
        公開總覽模型；選用資料未提供時保留 None，不補成零。
    """
    return overview.Overview.model_validate(
        serialization.to_dict(service.get_overview())
    )
