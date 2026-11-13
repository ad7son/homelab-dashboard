"""每次建立新的父 router，讓正式與相容前綴各自掛載。"""

from __future__ import annotations

import fastapi

from .routes import health
from .routes import history
from .routes import overview


def build_router() -> fastapi.APIRouter:
    """組合總覽、歷史與健康子路由，每次回傳獨立父路由。"""
    router = fastapi.APIRouter()
    router.include_router(overview.router)
    router.include_router(history.router)
    router.include_router(health.router)
    return router
