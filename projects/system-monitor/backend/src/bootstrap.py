"""專案組裝入口：建立具體實作並注入服務，API 與採集器各有自己的程序實例。

設定相同時共用同一 Runtime，避免每次請求重設取樣基準；更換資料庫設定時
使用另一個 Runtime。此處只建立物件，沒有硬體讀取、建表或背景排程。
"""
from dataclasses import dataclass
from functools import lru_cache
from threading import RLock

from .core.config import Settings
from .infrastructure.metrics.cpu import CpuReader
from .infrastructure.metrics.memory import MemoryReader
from .infrastructure.metrics.network import NetworkReader
from .infrastructure.metrics.disk_io import DiskIoReader
from .infrastructure.metrics.gpu import GpuReader
from .infrastructure.metrics.source import SystemMetricsSource
from .infrastructure.repositories.metrics_repository import SQLiteMetricsRepository
from .infrastructure.storage.collector_status import JsonCollectorStatusStore
from .services.overview import OverviewService
from .services.history import HistoryService
from .services.health import HealthService
from .services.collection import CollectionService


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    source: SystemMetricsSource
    repository: SQLiteMetricsRepository
    status: JsonCollectorStatusStore
    overview: OverviewService
    history: HistoryService
    health: HealthService
    collection: CollectionService


_runtime_lock = RLock()


@lru_cache(maxsize=16)
def _build_runtime(settings: Settings) -> Runtime:
    source = SystemMetricsSource(
        CpuReader(), MemoryReader(), NetworkReader(),
        GpuReader(settings.gpu_cache_seconds, settings.gpu_timeout_seconds),
        DiskIoReader(settings.disk_sample_interval_seconds),
    )
    repository = SQLiteMetricsRepository(settings.database_path, settings.sqlite_busy_timeout_ms)
    status = JsonCollectorStatusStore(settings.database_path)
    history = HistoryService(repository)
    return Runtime(settings, source, repository, status, OverviewService(source), history,
        HealthService(source, repository, status, history, settings),
        CollectionService(source, repository, status, settings.retention_ms))


def get_runtime(database_path=None) -> Runtime:
    settings = Settings.from_environment(database_path)
    # lru_cache 允許同時未命中的呼叫各自執行建構；外層鎖確保只建立一組取樣狀態。
    with _runtime_lock:
        return _build_runtime(settings)
