"""A7LAS 平台的後端載入入口。"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import fastapi

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
