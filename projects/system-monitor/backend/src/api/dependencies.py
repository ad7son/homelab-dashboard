"""HTTP 依賴入口：取得既有服務實例，測試可用 dependency_overrides 替換。"""

from __future__ import annotations

from .. import bootstrap
from ..services import health as health_service
from ..services import history as history_service
from ..services import overview as overview_service


def get_overview_service() -> overview_service.OverviewService:
    """回傳目前設定共用的即時總覽服務，供 FastAPI 注入與測試替換。"""
    return bootstrap.get_runtime().overview


def get_history_service() -> history_service.HistoryService:
    """回傳目前設定共用的歷史查詢服務，供 FastAPI 注入與測試替換。"""
    return bootstrap.get_runtime().history


def get_health_service() -> health_service.HealthService:
    """回傳目前設定共用的功能健康服務，供 FastAPI 注入與測試替換。"""
    return bootstrap.get_runtime().health
