"""專案組裝入口：建立具體實作並注入服務，API 與採集器各有自己的程序實例。

設定相同時共用同一 Runtime，避免每次請求重設取樣基準；更換資料庫設定時
使用另一個 Runtime。此處只建立物件，沒有硬體讀取、建表或背景排程。
"""

from __future__ import annotations

import dataclasses
import functools
import pathlib
import threading

from .core import config
from .infrastructure.metrics import cpu
from .infrastructure.metrics import disk_io
from .infrastructure.metrics import gpu
from .infrastructure.metrics import memory
from .infrastructure.metrics import network
from .infrastructure.metrics import source as metrics_source
from .infrastructure.repositories import metrics_repository
from .infrastructure.storage import collector_status
from .services import collection as services_collection
from .services import health as services_health
from .services import history as services_history
from .services import overview as services_overview


@dataclasses.dataclass(frozen=True)
class Runtime:
    """同一設定共用的一組採集器、儲存介面與應用服務。

    Attributes:
        settings: 此組服務共用的不可變設定。
        source: 共用取樣基準及來源快取的主機採集介面。
        repository: 歷史樣本儲存介面。
        status: 採集器最近一次嘗試的診斷旁檔介面。
        overview: 即時快照組合服務。
        history: 歷史資料查詢服務。
        health: 保留檢查快取與最近成功時間的健康服務。
        collection: 單次採集與保留政策服務。
    """

    settings: config.Settings
    source: metrics_source.SystemMetricsSource
    repository: metrics_repository.SQLiteMetricsRepository
    status: collector_status.JsonCollectorStatusStore
    overview: services_overview.OverviewService
    history: services_history.HistoryService
    health: services_health.HealthService
    collection: services_collection.CollectionService


_runtime_lock = threading.RLock()


@functools.lru_cache(maxsize=16)
def _build_runtime(settings: config.Settings) -> Runtime:
    """依設定快取並建立整組服務，不讀取硬體或初始化資料庫。

    Args:
        settings: 作為快取鍵的不可變設定。

    Returns:
        同一設定在快取有效期間共用的 Runtime；最多保留 16 組。
    """
    source = metrics_source.SystemMetricsSource(
        cpu.CpuReader(),
        memory.MemoryReader(),
        network.NetworkReader(),
        gpu.GpuReader(settings.gpu_cache_seconds, settings.gpu_timeout_seconds),
        disk_io.DiskIoReader(settings.disk_sample_interval_seconds),
    )
    repository = metrics_repository.SQLiteMetricsRepository(
        settings.database_path, settings.sqlite_busy_timeout_ms
    )
    status = collector_status.JsonCollectorStatusStore(settings.database_path)
    history = services_history.HistoryService(repository)
    return Runtime(
        settings,
        source,
        repository,
        status,
        services_overview.OverviewService(source),
        history,
        services_health.HealthService(
            source, repository, status, history, settings
        ),
        services_collection.CollectionService(
            source, repository, status, settings.retention_ms
        ),
    )


def get_runtime(database_path: str | pathlib.Path | None = None) -> Runtime:
    """取得目前設定的共用 Runtime，並序列化首次建構。

    Args:
        database_path: 明確指定的資料庫位置；None 時依環境與平台預設解析。

    Returns:
        設定相同時共用同一組讀取基準、快取及鎖的 Runtime。
    """
    settings = config.Settings.from_environment(database_path)
    # lru_cache 允許同時未命中的呼叫各自執行建構；外層鎖確保只建立一組取樣狀態。
    with _runtime_lock:
        return _build_runtime(settings)
