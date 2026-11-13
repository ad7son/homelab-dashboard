"""歷史查詢 HTTP 入口；參數與例外轉換在此邊界完成。"""
from fastapi import APIRouter, Depends, Query
from ..dependencies import get_history_service
from ..exception_handlers import history_unavailable
from ..schemas.history import HistoricalMetricsResponse, HistoryRange
from ...domain.history import HistoryRange as DomainRange
from ...domain.serialization import to_dict
from ...services.history import HistoryService
from ...services.exceptions import HistoricalMetricsUnavailableError

router = APIRouter()


@router.get("/history", response_model=HistoricalMetricsResponse)
def read_history(
    range: HistoryRange = Query(..., description="Historical window: 15m, 1h, 24h, or 7d"),
    service: HistoryService = Depends(get_history_service),
) -> HistoricalMetricsResponse:
    try:
        result = service.get_historical_metrics(DomainRange(range.value))
        return HistoricalMetricsResponse.model_validate(to_dict(result))
    except HistoricalMetricsUnavailableError as exc:
        raise history_unavailable(exc) from exc
