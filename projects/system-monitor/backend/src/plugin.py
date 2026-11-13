"""平台整合入口；HTTP 路由由 api 層管理，執行依賴由 bootstrap 組裝。"""
from fastapi import APIRouter
from .api.router import build_router as build_api_router


def build_router() -> APIRouter:
    return build_api_router()
