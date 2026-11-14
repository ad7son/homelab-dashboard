"""指定時間視窗的歷史 API；長視窗在 SQL 內降採樣，限制回應筆數。"""

from __future__ import annotations

import logging
import math
import sqlite3
import time
from typing import Literal

import fastapi

from ... import config
from ...database import repository
from .. import schemas

router = fastapi.APIRouter()
_logger = logging.getLogger(__name__)
_RANGE_SECONDS = {"15m": 900, "1h": 3600, "24h": 86400, "7d": 604800}
_RANGE_BUCKET_MS = {"15m": 0, "1h": 0, "24h": 300_000, "7d": 1_800_000}
_MAX_RAW_SAMPLES = 2000


@router.get("/history", response_model=schemas.History)
def read_history(
    range_name: Literal["15m", "1h", "24h", "7d"] = fastapi.Query(
        "1h", alias="range"
    ),
    start_ms: int | None = fastapi.Query(
        None, ge=0, le=9_223_372_036_854_775_807
    ),
    end_ms: int | None = fastapi.Query(
        None, ge=0, le=9_223_372_036_854_775_807
    ),
) -> schemas.History:
    """查詢預設範圍，或同時提供 start_ms/end_ms 的自訂 UTC 毫秒視窗。

    自訂視窗優先於 range，最多七天；超過約 2000 筆時自動彙整。
    起訖包含邊界，空資料回傳空清單；缺少資料庫回傳 503，不建檔。
    """
    settings = config.Settings.from_environment()
    interval_ms = int(settings.collection_interval_seconds * 1000)
    if (start_ms is None) != (end_ms is None):
        raise fastapi.HTTPException(
            422, "start_ms and end_ms must be supplied together"
        )
    selected_range: str | None = range_name
    if start_ms is None:
        end_ms = int(time.time() * 1000)
        start_ms = max(0, end_ms - _RANGE_SECONDS[range_name] * 1000)
        bucket_ms = _RANGE_BUCKET_MS[range_name]
    else:
        if end_ms < start_ms or end_ms - start_ms > 604_800_000:
            raise fastapi.HTTPException(
                422, "History window must be ordered and at most seven days"
            )
        selected_range = None
        bucket_ms = 0
    # 以毫秒為最小粒度；即使日後縮短採集間隔也限制長視窗的輸出量。
    if (end_ms - start_ms) / max(1, interval_ms) > _MAX_RAW_SAMPLES:
        minimum_bucket = math.ceil((end_ms - start_ms) / (_MAX_RAW_SAMPLES - 1))
        bucket_ms = max(bucket_ms, minimum_bucket)
    store = repository.HostRepository(
        settings.database_path, settings.sqlite_timeout_seconds
    )
    try:
        samples = store.get_history(start_ms, end_ms, bucket_ms)
    except sqlite3.Error as exc:
        _logger.exception("Historical database unavailable")
        raise fastapi.HTTPException(
            503, "Historical metrics database unavailable"
        ) from exc
    return schemas.History(
        range=selected_range,
        start_ms=start_ms,
        end_ms=end_ms,
        interval_seconds=(bucket_ms or interval_ms) / 1000,
        samples=[
            schemas.HistorySample.model_validate(sample) for sample in samples
        ],
    )
