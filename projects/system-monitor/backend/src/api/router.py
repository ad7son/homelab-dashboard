"""組合兩個查詢路由，每次提供新的父 router 供平台掛載。"""

from __future__ import annotations

import fastapi

from .routes import history
from .routes import overview


def build_router() -> fastapi.APIRouter:
    """建立總覽與歷史路由，不建立資料庫或啟動採集器。"""
    router = fastapi.APIRouter()
    router.include_router(overview.router)
    router.include_router(history.router)
    return router
