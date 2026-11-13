"""歷史查詢 HTTP 入口；參數與例外轉換在此邊界完成。"""

from __future__ import annotations

import fastapi

from .. import dependencies
from ...domain import history as domain_history
from ...domain import serialization
from .. import exception_handlers
from ...services import exceptions
from ...services import history as services_history
from ..schemas import history

router = fastapi.APIRouter()


@router.get("/history", response_model=history.HistoricalMetricsResponse)
def read_history(
    range: history.HistoryRange = fastapi.Query(
        ..., description="Historical window: 15m, 1h, 24h, or 7d"
    ),
    service: services_history.HistoryService = fastapi.Depends(
        dependencies.get_history_service
    ),
) -> history.HistoricalMetricsResponse:
    """查詢指定時間範圍，將儲存失敗轉成安全的 HTTP 錯誤。

    Args:
        range: 公開查詢參數，支援 15m、1h、24h、7d。
        service: 由依賴注入提供的歷史服務。

    Returns:
        含起訖時間與樣本的公開回應；空樣本仍是成功結果。

    Raises:
        fastapi.HTTPException: 歷史來源無法使用，狀態碼為 503。
    """
    try:
        result = service.get_historical_metrics(
            domain_history.HistoryRange(range.value)
        )
        return history.HistoricalMetricsResponse.model_validate(
            serialization.to_dict(result)
        )
    except exceptions.HistoricalMetricsUnavailableError as exc:
        raise exception_handlers.history_unavailable(exc) from exc
