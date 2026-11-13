"""驗證平台掛載的正式／相容前綴、路由唯一性及已移除入口。"""

from __future__ import annotations

from fastapi import testclient
import pytest

from app import config
from app import main
from app.modules import loader
import monitor_backend

plugin = monitor_backend.module("plugin")

# 此檔共用輕量 API 用戶端；資料庫與服務狀態由各測試 fixture 隔離。
_client = testclient.TestClient(main.app)

LIVE_PATHS = ("overview",)


def assert_same_shape(left: object, right: object) -> None:
    """遞迴比較 JSON 結構，忽略即時數值差異及選用來源的空值。

    Args:
        left: 舊前綴的 API 回應。
        right: 專案正式前綴的 API 回應。

    Raises:
        AssertionError: 欄位集合、清單長度或可比較的葉節點型別不同。
    """
    if isinstance(left, dict) and isinstance(right, dict):
        assert set(left) == set(right)
        for key in left:
            assert_same_shape(left[key], right[key])
        return
    if isinstance(left, list) and isinstance(right, list):
        assert len(left) == len(right)
        for item, other in zip(left, right, strict=True):
            assert_same_shape(item, other)
        return
    if left is None or right is None:
        return
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return
    assert type(left) is type(right)


def test_system_monitor_manifest_is_discovered() -> None:
    manifests = loader.discover_project_manifests(
        loader.default_projects_root()
    )
    match = next(item for item in manifests if item.id == "system-monitor")
    assert match.api_prefix == "/api/system-monitor"
    assert match.legacy_api_prefix == "/api"
    assert list(match.legacy_route_bases) == ["/homelab"]
    assert match.route_base == "/system-monitor"
    assert match.python_package == "src"


def test_build_router_returns_a_new_parent_each_call() -> None:
    first = plugin.build_router()
    second = plugin.build_router()
    assert first is not second


@pytest.mark.parametrize("path", LIVE_PATHS)
def test_legacy_and_namespaced_routes_share_a_shape(path: str) -> None:
    legacy = _client.get(f"/api/{path}")
    current = _client.get(f"/api/system-monitor/{path}")
    assert legacy.status_code == 200
    assert current.status_code == 200
    assert_same_shape(legacy.json(), current.json())


def test_history_prefix_is_compatible() -> None:
    legacy = _client.get("/api/history", params={"range": "15m"})
    current = _client.get(
        "/api/system-monitor/history", params={"range": "15m"}
    )
    assert legacy.status_code == current.status_code
    assert legacy.status_code in {200, 503}
    if legacy.status_code == 200:
        assert_same_shape(legacy.json(), current.json())


def test_health_stays_on_the_platform_prefix() -> None:
    response = _client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": config.A7LAS_VERSION}
    assert _client.get("/api/system-monitor/health").status_code == 404


def _mounted_http_paths() -> list[str]:
    paths: list[str] = []

    def walk(route: object, prefix: str) -> None:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if isinstance(path, str) and methods:
            paths.append(f"{prefix}{path}")
            return
        include = getattr(route, "include_context", None)
        next_prefix = prefix
        if include is not None:
            extra = getattr(include, "prefix", "") or ""
            next_prefix = f"{prefix}{extra}"
        original = getattr(route, "original_router", None)
        children = (
            getattr(original, "routes", None) if original is not None else None
        )
        if not children:
            return
        for child in children:
            walk(child, next_prefix)

    for route in main.app.routes:
        walk(route, "")
    return paths


def test_each_monitoring_route_is_mounted_once_per_prefix() -> None:
    paths = _mounted_http_paths()
    for path in (*LIVE_PATHS, "history", "feature-health"):
        assert paths.count(f"/api/{path}") == 1
        assert paths.count(f"/api/system-monitor/{path}") == 1
    assert paths.count("/api/health") == 1


@pytest.mark.parametrize("prefix", ["/api", "/api/system-monitor"])
@pytest.mark.parametrize(
    "name", ["services", "system", "disks", "cpu", "memory", "network"]
)
def test_removed_unused_api_is_not_available(prefix: str, name: str) -> None:
    """未使用入口已移除，新舊前綴都不得再提供路由或 API 文件。"""
    path = f"{prefix}/{name}"
    assert _client.get(path).status_code == 404
    assert path not in main.app.openapi()["paths"]
