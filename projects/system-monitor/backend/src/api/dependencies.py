"""HTTP 依賴入口：取得既有服務實例，測試可用 dependency_overrides 替換。"""
from ..bootstrap import get_runtime


def get_overview_service():
    return get_runtime().overview


def get_history_service():
    return get_runtime().history


def get_health_service():
    return get_runtime().health
