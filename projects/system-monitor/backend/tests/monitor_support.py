"""以平台實際載入的服務建構測試情境，不建立第二份專案套件。

讀取器與時鐘可逐項替換，未替換者沿用 Runtime。動態服務以 Any 標註，
避免為取得型別另行匯入未經平台隔離的 src。
"""

from __future__ import annotations

from collections.abc import Callable
import pathlib
import sqlite3
import threading
import types
from typing import Any

import monitor_backend


def repository(path: str | pathlib.Path | None = None) -> Any:
    """建立不立即開啟連線的儲存介面；None 時沿用專案路徑解析規則。"""
    config = monitor_backend.module("core.config")
    storage = monitor_backend.module(
        "infrastructure.repositories.metrics_repository"
    )
    return storage.SQLiteMetricsRepository(config.resolve_metrics_db_path(path))


def get_historical_metrics(
    history_range: Any,
    *,
    db_path: str | pathlib.Path | None = None,
    now_ms: int | None = None,
    clock_ms: Callable[[], float] | None = None,
    read_only: bool = False,
) -> Any:
    """以可控時間查詢歷史資料，將測試的毫秒時鐘轉成服務需要的秒數。

    Args:
        history_range: 由平台命名空間載入的 HistoryRange。
        db_path: 測試資料庫位置。
        now_ms: 明確查詢終點，單位 Unix 毫秒。
        clock_ms: 回傳 Unix 毫秒的時鐘；None 時服務使用系統時鐘。
        read_only: True 時禁止建檔或遷移。

    Returns:
        實際歷史服務的查詢結果，不模擬 SQL 或降採樣行為。
    """
    history = monitor_backend.module("services.history")
    service = history.HistoryService(
        repository(db_path),
        clock=(lambda: clock_ms() / 1000) if clock_ms else None,
    )
    return service.get_historical_metrics(
        history_range, now_ms=now_ms, read_only=read_only
    )


def latest_metric_sample(path: str | pathlib.Path | None = None) -> Any:
    """回傳資料庫最新樣本字典或 None；不以假資料取代查詢。"""
    return repository(path).latest()


def collection_service(path: str | pathlib.Path | None, **options: Any) -> Any:
    """建立可逐項替換來源的實際採集服務。

    Args:
        path: 測試資料庫位置；None 時沿用環境與平台預設。
        **options: cpu_reader、memory_reader、network_reader、gpu_reader、
            disk_io_reader 可替換來源；clock 為 Unix 秒時鐘，retention_ms
            為保留毫秒數。未提供者沿用 Runtime 設定。

    Returns:
        保留真實 Repository 與診斷旁檔的採集服務。
    """
    runtime = monitor_backend.module("bootstrap").get_runtime(path)
    source = types.SimpleNamespace(
        **{
            name: options.get(name + "_reader", getattr(runtime.source, name))
            for name in ("cpu", "memory", "network", "gpu", "disk_io")
        }
    )
    collection = monitor_backend.module("services.collection")
    return collection.CollectionService(
        source,
        runtime.repository,
        runtime.status,
        retention_ms=options.get("retention_ms", runtime.settings.retention_ms),
        clock=options.get("clock"),
    )


def collect_once(connection: sqlite3.Connection, **options: Any) -> Any:
    """將採集結果存入連線所屬資料庫，不接管傳入連線。

    Args:
        connection: 已開啟的測試連線，仍由呼叫端關閉。
        **options: collection_service 接受的來源、秒時鐘與保留政策。

    Returns:
        實際寫入的不可變樣本；服務另行管理自己的連線。
    """
    path = connection.execute("PRAGMA database_list").fetchone()[2]
    return collection_service(path, **options).collect_once()


def run_collect_iteration(path: str | pathlib.Path, **options: Any) -> Any:
    """回傳實際採集樣本；options 與 collection_service 相同。"""
    return collection_service(path, **options).collect_once()


def run_retention_cleanup(path: str | pathlib.Path, **options: Any) -> int:
    """回傳實際刪除筆數；options 可替換秒時鐘與保留毫秒數。"""
    return collection_service(path, **options).cleanup()


def run_collector_loop(
    stop_event: threading.Event,
    *,
    db_path: str | pathlib.Path | None = None,
    retention_cleanup: Callable[[pathlib.Path], int] | None = None,
    **options: Any,
) -> None:
    """以可控時鐘與來源執行正式採集迴圈，不建立另一套排程。

    Args:
        stop_event: 用於停止迴圈的事件。
        db_path: 測試資料庫位置。
        retention_cleanup: 接收資料庫 Path 的清理替身；None 時用正式清理。
        **options: collection_service 選項，以及 interval_seconds、
            maintenance_interval_seconds、monotonic_clock 排程選項。
    """
    service = collection_service(db_path, **options)
    scheduling = {
        key: options[key]
        for key in (
            "interval_seconds",
            "maintenance_interval_seconds",
            "monotonic_clock",
        )
        if key in options
    }
    cleanup = (
        (lambda: retention_cleanup(pathlib.Path(db_path)))
        if retention_cleanup
        else None
    )
    runner = monitor_backend.module("collector.runner")
    runner.run_collector_loop(
        stop_event, service, retention_cleanup=cleanup, **scheduling
    )
