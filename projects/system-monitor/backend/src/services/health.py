"""功能健康用例：取得證據、呼叫純規則、隔離失敗並保留同次檢查快照。

快取、最近成功時間與鎖歸屬實例，兩個 API 前綴共用同一服務。
領域規則不依賴此服務；SQL、檔案與硬體操作透過注入介面完成。
"""
import threading
import time
import traceback
from ..core.config import Settings
from ..domain.health import FeatureError, FeatureHealth, ProjectHealthReport
from ..domain import health_rules as rules
from ..domain.history import HistoryRange
from ..domain.serialization import to_dict
from .ports import MetricsSource, MetricsRepository, CollectorStatusStore
from .history import HistoryService

SPECS = [
    ("cpu", "CPU 資訊採集", "讀取 CPU 使用率、核心數及可用的頻率、溫度資訊。", "使用率為 0–100 的有限數值，實體與邏輯核心數皆大於零；溫度與頻率屬選用資訊。", "infrastructure.metrics.cpu.CpuReader.read"),
    ("memory", "記憶體資訊採集", "讀取主機記憶體容量、可用空間、使用率與 Swap 資訊。", "總容量大於零，已用與可用容量介於零和總容量之間，使用率為 0–100 的有限數值。", "infrastructure.metrics.memory.MemoryReader.read"),
    ("gpu", "GPU 資訊採集", "取得支援的 GPU 使用率，多卡時顯示有效讀值中最忙碌的一張。", "來源可用且使用率為 0–100 的有限數值時正常；無支援硬體為 Unavailable，已偵測到裝置卻無有效讀值為 Issues。", "infrastructure.metrics.gpu.GpuReader.read"),
    ("disk-io", "Disk I/O 資訊採集", "利用兩次磁碟計數器取樣計算全機每秒讀寫量。", "讀寫速度皆為非負有限數值；首次取樣為 Unknown，讀取失敗為 Issues，0 B/s 為正常。", "infrastructure.metrics.disk_io.DiskIoReader.read"),
    ("network", "網路流量採集", "選擇主要網路介面並計算每秒上下載量。", "有監控介面且上下傳速度皆為非負有限數值；首次取樣為 Unknown，無可用介面為 Unavailable。", "infrastructure.metrics.network.NetworkReader.read"),
    ("history-write", "歷史資料採集", "確認獨立採集器持續將新樣本寫入 SQLite，並讀取最近一次採集結果。", "資料庫最新樣本距現在不超過 90 秒，且沒有更新的採集失敗紀錄；程序存在不等於寫入正常。", "SQLite latest sample + collector status"),
    ("history-query", "歷史資料查詢", "唯讀查詢最近一小時的完整歷史樣本，檢查結構與必要數值。", "資料庫版本與查詢正常，樣本必要數值有效；空清單仍屬查詢成功，寫入新鮮度由歷史資料採集獨立判定。", "SQLite read_metric_samples / range=1h"),
]

class HealthService:
    def __init__(self, source: MetricsSource, repository: MetricsRepository, status: CollectorStatusStore,
                 history: HistoryService, settings: Settings, clock=None, monotonic=None):
        self.source = source
        self.repository = repository
        self.status = status
        self.history = history
        self.settings = settings
        self.clock = clock or (lambda: time.time())
        self.monotonic = monotonic or (lambda: time.monotonic())
        self._lock = threading.Lock()
        self._cached = None
        self._last_success = {}

    def _history_write(self, now):
        row = self.repository.latest()
        collector, diagnostic_error = self.status.read()
        timestamp = row["timestamp_ms"] if row else None
        return {
            "database_path": str(self.settings.database_path), "schema_version": 2,
            "latest_sample": row, "latest_sample_at_ms": timestamp,
            "sample_age_ms": now - timestamp if timestamp is not None else None,
            "expected_interval_seconds": self.settings.collection_interval_seconds,
            "stale_after_ms": self.settings.history_stale_after_ms,
            "collector": collector, "collector_status_error": diagnostic_error,
        }

    def _history_query(self, now):
        return to_dict(self.history.get_historical_metrics(HistoryRange.H1, now_ms=now, read_only=True))

    def _run_check(self, spec, reader, check, now):
        feature_id, name, description, criteria, source = spec
        started = self.monotonic()
        data, error = None, None
        try:
            data = to_dict(reader())
            status, message = check(data)
            if status == "healthy":
                self._last_success[feature_id] = now
            if feature_id == "history-write":
                collector_error = (data.get("collector") or {}).get("error")
                if status == "issues" and isinstance(collector_error, dict):
                    error = FeatureError(**collector_error)
        except Exception as exc:
            status, message = "issues", f"功能檢查失敗：{type(exc).__name__}"
            error = FeatureError(type(exc).__name__, str(exc), traceback.format_exc())
        last_success = self._last_success.get(feature_id)
        if feature_id == "history-write" and isinstance(data, dict):
            last_success = data.get("latest_sample_at_ms")
        return FeatureHealth(
            id=feature_id, name=name, description=description, criteria=criteria, status=status,
            message=message, checked_at_ms=now, last_success_at_ms=last_success,
            duration_ms=round((self.monotonic() - started) * 1000), source=source,
            raw_data=rules._json_safe(data), error=error,
        )

    def get_feature_health(self, *, force=False):
        with self._lock:
            if not force and self._cached and self.monotonic() - self._cached[0] < self.settings.report_cache_seconds:
                return self._cached[1]
            now = int(self.clock() * 1000)
            checks = [
                (self.source.cpu, rules.check_cpu), (self.source.memory, rules.check_memory),
                (self.source.gpu, rules.check_gpu), (self.source.disk_io, rules.check_disk_io),
                (self.source.network, rules.check_network),
                (lambda: self._history_write(now), lambda data: rules.check_history_write(data, stale_after_ms=self.settings.history_stale_after_ms)),
                (lambda: self._history_query(now), rules.check_history_query),
            ]
            report = ProjectHealthReport(self.settings.project_id, self.settings.project_name, now,
                [self._run_check(spec, reader, check, now) for spec, (reader, check) in zip(SPECS, checks, strict=True)])
            self._cached = (self.monotonic(), report)
            return report
