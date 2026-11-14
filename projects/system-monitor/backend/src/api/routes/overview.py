"""即時 API 只查詢資料庫最新資料，不匯入或啟動硬體讀取器。"""

from __future__ import annotations

import logging
import sqlite3

import fastapi

from app.observability import events

from ... import config
from ...database import repository
from .. import schemas

router = fastapi.APIRouter()
_logger = logging.getLogger(__name__)


@router.get("/overview", response_model=schemas.Overview)
def read_overview() -> schemas.Overview:
    """回傳基本資訊及最新指標；缺少資料或資料庫不可讀時回傳 503。"""
    with events.execution("system-monitor", "overview-query", source=__name__):
        settings = config.Settings.from_environment()
        store = repository.HostRepository(
            settings.database_path, settings.sqlite_timeout_seconds
        )
        try:
            latest = store.get_latest()
        except sqlite3.Error as exc:
            _logger.exception("Overview database unavailable")
            raise fastapi.HTTPException(
                503, "Metrics database unavailable"
            ) from exc
        if latest is None:
            raise fastapi.HTTPException(503, "No host metrics collected yet")
        return schemas.Overview(
            info=schemas.HostInfo.model_validate(latest),
            metrics=schemas.HostMetrics.model_validate(latest),
        )
