from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.history import HistoricalMetricsResponse, HistoryRange
from app.services.history_service import (
    HistoricalMetricsUnavailableError,
    get_historical_metrics,
)

logger = logging.getLogger("a7las.history")

router = APIRouter()


@router.get("/history", response_model=HistoricalMetricsResponse)
def read_history(
    range: HistoryRange = Query(..., description="Historical window: 15m, 1h, 24h, or 7d"),
) -> HistoricalMetricsResponse:
    try:
        return get_historical_metrics(range)
    except HistoricalMetricsUnavailableError:
        logger.exception("Failed to query historical metrics database")
        raise HTTPException(
            status_code=503,
            detail="Historical metrics database unavailable",
        )
