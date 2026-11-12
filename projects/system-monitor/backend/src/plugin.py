"""System Monitor 的平台入口：集中宣告三組 API，不執行背景排程。

每次 build_router 都建立新 router，供外殼分別掛載正式與相容前綴。
硬體採集、歷史查詢與健康檢查由對應功能模組處理。
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from .machine import readers
from .machine.models import Overview
from .history import query
from .history.models import HistoricalMetricsResponse, HistoryRange
from .health import checks
from .health.models import ProjectHealthReport

logger = logging.getLogger("a7las.history")


def build_router() -> APIRouter:
    """建立獨立 API 集合；前綴由外殼決定，專案內不寫死 /api。"""
    router = APIRouter()

    @router.get("/overview", response_model=Overview)
    def read_overview() -> Overview:
        return readers.get_overview()

    @router.get("/history", response_model=HistoricalMetricsResponse)
    def read_history(
        range: HistoryRange = Query(..., description="Historical window: 15m, 1h, 24h, or 7d"),
    ) -> HistoricalMetricsResponse:
        try:
            return query.get_historical_metrics(range)
        except query.HistoricalMetricsUnavailableError:
            # HTTP 回應維持原有 503 訊息，底層錯誤只寫入日誌。
            logger.exception("Failed to query historical metrics database")
            raise HTTPException(status_code=503, detail="Historical metrics database unavailable")

    @router.get("/feature-health", response_model=ProjectHealthReport)
    def feature_health(force: bool = False) -> ProjectHealthReport:
        return checks.get_feature_health(force=force)

    return router
