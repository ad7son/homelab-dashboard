"""功能健康用例：取得證據、呼叫純規則、隔離失敗並保留同次檢查快照。

快取、最近成功時間與鎖歸屬實例，兩個 API 前綴共用同一服務。
領域規則不依賴此服務；SQL、檔案與硬體操作透過注入介面完成。
"""

from __future__ import annotations

from collections.abc import Callable
import threading
import time
import traceback
from typing import Any

from ..core import config
from ..domain import health
from ..domain import health_rules
from ..domain import history as domain_history
from ..domain import serialization
from . import history as module_history
from . import ports

_FEATURE_SPECS = (
    (
        "cpu",
        "CPU 資訊採集",
        "讀取 CPU 使用率、核心數及可用的頻率、溫度資訊。",
        "使用率為 0–100 的有限數值，實體與邏輯核心數皆大於零；溫度與頻率屬選用資訊。",
        "infrastructure.metrics.cpu.CpuReader.read",
    ),
    (
        "memory",
        "記憶體資訊採集",
        "讀取主機記憶體容量、可用空間、使用率與 Swap 資訊。",
        "總容量大於零，已用與可用容量介於零和總容量之間，使用率為 0–100 的有限數值。",
        "infrastructure.metrics.memory.MemoryReader.read",
    ),
    (
        "gpu",
        "GPU 資訊採集",
        "取得支援的 GPU 使用率，多卡時顯示有效讀值中最忙碌的一張。",
        "來源可用且使用率為 0–100 的有限數值時正常；無支援硬體為 Unavailable，已偵測到裝置卻無有效讀值為 Issues。",
        "infrastructure.metrics.gpu.GpuReader.read",
    ),
    (
        "disk-io",
        "Disk I/O 資訊採集",
        "利用兩次磁碟計數器取樣計算全機每秒讀寫量。",
        "讀寫速度皆為非負有限數值；首次取樣為 Unknown，讀取失敗為 Issues，0 B/s 為正常。",
        "infrastructure.metrics.disk_io.DiskIoReader.read",
    ),
    (
        "network",
        "網路流量採集",
        "選擇主要網路介面並計算每秒上下載量。",
        "有監控介面且上下傳速度皆為非負有限數值；首次取樣為 Unknown，無可用介面為 Unavailable。",
        "infrastructure.metrics.network.NetworkReader.read",
    ),
    (
        "history-write",
        "歷史資料採集",
        "確認獨立採集器持續將新樣本寫入 SQLite，並讀取最近一次採集結果。",
        "資料庫最新樣本距現在不超過 90 秒，且沒有更新的採集失敗紀錄；程序存在不等於寫入正常。",
        "SQLite latest sample + collector status",
    ),
    (
        "history-query",
        "歷史資料查詢",
        "唯讀查詢最近一小時的完整歷史樣本，檢查結構與必要數值。",
        "資料庫版本與查詢正常，樣本必要數值有效；空清單仍屬查詢成功，寫入新鮮度由歷史資料採集獨立判定。",
        "SQLite read_metric_samples / range=1h",
    ),
)


class HealthService:
    """序列化執行功能檢查並保留快取與最近成功時間的服務。

    Attributes:
        source: 共用取樣基準及來源快取的主機採集介面。
        repository: 歷史樣本儲存介面。
        status: 採集器最近一次嘗試的診斷旁檔介面。
        history: 歷史資料查詢服務。
        settings: 此組服務共用的不可變設定。
        clock: 回傳 Unix 秒數的時鐘，可由測試替換。
        monotonic: 回傳單調秒數的時鐘，用於快取與耗時計算。
    """

    def __init__(
        self,
        source: ports.MetricsSource,
        repository: ports.MetricsRepository,
        status: ports.CollectorStatusStore,
        history: module_history.HistoryService,
        settings: config.Settings,
        clock: Callable[[], float] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        """建立保留快取、最近成功時間及執行鎖的健康服務。

        Args:
            source: 五項資源的採集來源。
            repository: 用於讀取最新已儲存樣本的介面。
            status: 採集器最近一次嘗試的紀錄介面。
            history: 用於唯讀驗證查詢能力的歷史服務。
            settings: 專案名稱、快取期限與資料新鮮度設定。
            clock: 回傳 Unix 秒數的函式；None 時使用系統時間。
            monotonic: 回傳單調秒數的函式；None 時使用 time.monotonic。
        """
        self.source = source
        self.repository = repository
        self.status = status
        self.history = history
        self.settings = settings
        self.clock = clock or (lambda: time.time())
        self.monotonic = monotonic or (lambda: time.monotonic())
        self._lock = threading.Lock()
        self._cached: tuple[float, health.ProjectHealthReport] | None = None
        self._last_success: dict[str, int] = {}

    def _history_write(self, now: int) -> dict[str, Any]:
        """組合最新樣本與診斷旁檔；now 為 Unix 毫秒，不建立或修復資料庫。"""
        row = self.repository.latest()
        collector, diagnostic_error = self.status.read()
        timestamp = row["timestamp_ms"] if row else None
        return {
            "database_path": str(self.settings.database_path),
            "schema_version": 2,
            "latest_sample": row,
            "latest_sample_at_ms": timestamp,
            "sample_age_ms": now - timestamp if timestamp is not None else None,
            "expected_interval_seconds": self.settings.collection_interval_seconds,
            "stale_after_ms": self.settings.history_stale_after_ms,
            "collector": collector,
            "collector_status_error": diagnostic_error,
        }

    def _history_query(self, now: int) -> dict[str, Any]:
        """回傳以 now 為終點的最近一小時唯讀證據，不用新鮮度取代查詢健康。"""
        return serialization.to_dict(
            self.history.get_historical_metrics(
                domain_history.HistoryRange.H1, now_ms=now, read_only=True
            )
        )

    def _run_check(
        self,
        spec: tuple[str, str, str, str, str],
        reader: Callable[[], Any],
        check: Callable[[dict[str, Any]], tuple[health.FeatureStatus, str]],
        now: int,
    ) -> health.FeatureHealth:
        """隔離單一功能失敗，將判定與同次證據封裝為功能報告。

        Args:
            spec: (識別碼, 名稱, 說明, 判定依據, 來源) 的固定中繼資料。
            reader: 無參數的採集或查詢函式。
            check: 接收證據字典並回傳 (狀態, 摘要) 的純判定函式。
            now: 本次整份報告共用的 Unix 毫秒時間戳。

        Returns:
            單項報告；失敗含原始堆疊，並保留先前已知的最近成功時間。
        """
        feature_id, name, description, criteria, source = spec
        started = self.monotonic()
        data, error = None, None
        try:
            data = serialization.to_dict(reader())
            status, message = check(data)
            if status == "healthy":
                self._last_success[feature_id] = now
            if feature_id == "history-write":
                collector_error = (data.get("collector") or {}).get("error")
                if status == "issues" and isinstance(collector_error, dict):
                    error = health.FeatureError(**collector_error)
        except Exception as exc:
            status, message = "issues", f"功能檢查失敗：{type(exc).__name__}"
            error = health.FeatureError(
                type(exc).__name__, str(exc), traceback.format_exc()
            )
        last_success = self._last_success.get(feature_id)
        if feature_id == "history-write" and isinstance(data, dict):
            last_success = data.get("latest_sample_at_ms")
        return health.FeatureHealth(
            id=feature_id,
            name=name,
            description=description,
            criteria=criteria,
            status=status,
            message=message,
            checked_at_ms=now,
            last_success_at_ms=last_success,
            duration_ms=round((self.monotonic() - started) * 1000),
            source=source,
            raw_data=health_rules.json_safe(data),
            error=error,
        )

    def get_feature_health(
        self, *, force: bool = False
    ) -> health.ProjectHealthReport:
        """序列化執行全部功能檢查，或回傳仍有效的同次報告快取。

        Args:
            force: True 時重新檢查；仍遵守底層 GPU／磁碟來源本身的快取規則。

        Returns:
            僅含目前專案的報告；各功能錯誤互相隔離，不中止後續檢查。
        """
        with self._lock:
            if (
                not force
                and self._cached
                and self.monotonic() - self._cached[0]
                < self.settings.report_cache_seconds
            ):
                return self._cached[1]
            now = int(self.clock() * 1000)
            checks = [
                (self.source.cpu, health_rules.check_cpu),
                (self.source.memory, health_rules.check_memory),
                (self.source.gpu, health_rules.check_gpu),
                (self.source.disk_io, health_rules.check_disk_io),
                (self.source.network, health_rules.check_network),
                (
                    lambda: self._history_write(now),
                    lambda data: health_rules.check_history_write(
                        data,
                        stale_after_ms=self.settings.history_stale_after_ms,
                    ),
                ),
                (
                    lambda: self._history_query(now),
                    health_rules.check_history_query,
                ),
            ]
            report = health.ProjectHealthReport(
                self.settings.project_id,
                self.settings.project_name,
                now,
                [
                    self._run_check(spec, reader, check, now)
                    for spec, (reader, check) in zip(
                        _FEATURE_SPECS, checks, strict=True
                    )
                ],
            )
            self._cached = (self.monotonic(), report)
            return report
