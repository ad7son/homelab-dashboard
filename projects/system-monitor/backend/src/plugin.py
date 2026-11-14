"""A7LAS 平台的後端載入入口。"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import fastapi

from app.observability import models

from . import config
from .api import router
from .collector import process


def build_router() -> fastapi.APIRouter:
    """回傳新的查詢路由；不執行硬體或資料庫操作。"""
    return router.build_router()


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI) -> AsyncIterator[None]:
    """由平台啟動採集器管理工作；離開時等待子程序釋放資源。"""
    del app  # 採集程序不需要存取平台應用實例。
    stop = asyncio.Event()
    supervisor = asyncio.create_task(
        process.supervise(config.Settings.from_environment(), stop)
    )
    try:
        yield
    finally:
        stop.set()
        await supervisor


def get_health_features() -> tuple[models.FeatureDefinition, ...]:
    """宣告監測功能；平台統一判定，專案不建立自己的健康查詢 API。"""
    features = (
        ("cpu", "CPU 採集", "CPU 使用率與附加資訊"),
        ("memory", "記憶體採集", "實體記憶體資訊，Swap 為選用資訊"),
        ("network", "網路採集", "啟動時選定介面的上傳與下載速率"),
        ("gpu", "GPU 採集", "GPU 來源是否支援及有效使用率"),
        ("disk-io", "磁碟採集", "磁碟讀寫速率"),
        ("metrics-collection", "歷史寫入", "完整採集輪次是否成功寫入 SQLite"),
    )
    scheduled = tuple(
        models.FeatureDefinition(
            id=identifier,
            name=name,
            description=description,
            mode="scheduled",
            stale_after_seconds=15,
        )
        for identifier, name, description in features
    )
    return (
        *scheduled,
        models.FeatureDefinition(
            id="overview-query",
            name="最新資訊查詢",
            description="最近一次實際總覽請求的結果",
            mode="request",
        ),
        models.FeatureDefinition(
            id="history-query",
            name="歷史資訊查詢",
            description="最近一次實際歷史請求的結果",
            mode="request",
        ),
    )
