"""平台整合入口；HTTP 路由由 api 層管理，執行依賴由 bootstrap 組裝。"""

from __future__ import annotations

import fastapi

from .api import router


def build_router() -> fastapi.APIRouter:
    """建立供平台掛載的新路由集合；不啟動採集器或讀取硬體。"""
    return router.build_router()
