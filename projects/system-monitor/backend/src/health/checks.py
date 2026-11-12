"""實際功能檢查：逐項隔離失敗，不以資源使用量高低判定採集功能好壞。

每次報告保存原始證據、例外及檢查時間；前端不得另查資料後冒充同次結果。
歷史檢查僅使用唯讀 SQLite 連線，不建立資料庫、不執行遷移或測試寫入。
"""

import json
import math
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from ..machine import readers, gpu
from ..history import database, query
from ..history.models import HistoryRange
from ..collector.status import read_collector_status
from .models import FeatureError, FeatureHealth, FeatureStatus, ProjectHealthReport

COLLECTION_INTERVAL_SECONDS = 30
HISTORY_STALE_AFTER_MS = 90_000
REPORT_CACHE_SECONDS = 3
_lock = threading.Lock()
_cached: tuple[float, ProjectHealthReport] | None = None
_last_success: dict[str, int] = {}

# 說明、判定條件與採集來源由專案本身宣告，外殼只負責顯示。
SPECS = [
    ("cpu", "CPU 資訊採集", "讀取 CPU 使用率、核心數及可用的頻率、溫度資訊。", "使用率為 0–100 的有限數值，實體與邏輯核心數皆大於零；溫度與頻率屬選用資訊。", "psutil / readers.get_cpu_info"),
    ("memory", "記憶體資訊採集", "讀取主機記憶體容量、可用空間、使用率與 Swap 資訊。", "總容量大於零，已用與可用容量介於零和總容量之間，使用率為 0–100 的有限數值。", "psutil / readers.get_memory_info"),
    ("gpu", "GPU 資訊採集", "取得支援的 GPU 使用率，多卡時顯示有效讀值中最忙碌的一張。", "來源可用且使用率為 0–100 的有限數值時正常；無支援硬體為 Unavailable，已偵測到裝置卻無有效讀值為 Issues。", "gpu.get_gpu_info"),
    ("disk-io", "Disk I/O 資訊採集", "利用兩次磁碟計數器取樣計算全機每秒讀寫量。", "讀寫速度皆為非負有限數值；首次取樣為 Unknown，讀取失敗為 Issues，0 B/s 為正常。", "psutil / readers.get_disk_io_info"),
    ("network", "網路流量採集", "選擇主要網路介面並計算每秒上下載量。", "有監控介面且上下傳速度皆為非負有限數值；首次取樣為 Unknown，無可用介面為 Unavailable。", "psutil / readers.get_network_info"),
    ("history-write", "歷史資料採集", "確認獨立採集器持續將新樣本寫入 SQLite，並讀取最近一次採集結果。", "資料庫最新樣本距現在不超過 90 秒，且沒有更新的採集失敗紀錄；程序存在不等於寫入正常。", "SQLite latest sample + collector status"),
    ("history-query", "歷史資料查詢", "唯讀查詢最近一小時的完整歷史樣本，檢查結構與必要數值。", "資料庫版本與查詢正常，樣本必要數值有效；空清單仍屬查詢成功，寫入新鮮度由歷史資料採集獨立判定。", "SQLite read_metric_samples / range=1h"),
]


def _finite(value: Any, minimum: float = 0, maximum: float | None = None) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum and (maximum is None or value <= maximum)


def _json_safe(value: Any) -> Any:
    """無效浮點保留為明確字串供排錯，不把 NaN／Infinity 偷換成零。"""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _history_write(now: int) -> dict:
    """組合寫入證據；資料庫與旁檔的實際讀取各由其所屬模組負責。"""
    row = database.latest_metric_sample()
    path = database.resolve_metrics_db_path()
    collector, diagnostic_error = read_collector_status(path)
    timestamp = row["timestamp_ms"] if row else None
    return {
        "database_path": str(path), "schema_version": database.CURRENT_SCHEMA_VERSION,
        "latest_sample": row,
        "latest_sample_at_ms": timestamp,
        "sample_age_ms": now - timestamp if timestamp is not None else None,
        "expected_interval_seconds": COLLECTION_INTERVAL_SECONDS,
        "stale_after_ms": HISTORY_STALE_AFTER_MS,
        "collector": collector, "collector_status_error": diagnostic_error,
    }


def _history_query(now: int) -> dict:
    return query.get_historical_metrics(HistoryRange.H1, now_ms=now, read_only=True).model_dump(mode="json")


def check_cpu(data: dict) -> tuple[FeatureStatus, str]:
    """檢查採集結果是否有效；負載高低不影響採集功能的健康判定。"""
    valid = _finite(data.get("usage_percent"), maximum=100) and _finite(data.get("physical_cores"), 1) and _finite(data.get("logical_cores"), 1)
    return ("healthy", "已取得有效的 CPU 使用率與核心資訊") if valid else ("issues", "CPU 回應包含無效使用率或核心數")


def check_memory(data: dict) -> tuple[FeatureStatus, str]:
    """驗證容量與百分比範圍，保留 psutil 已用與可用容量的原定義。"""
    total = data.get("total")
    valid = _finite(total, 1) and _finite(data.get("used"), maximum=total) and _finite(data.get("available"), maximum=total) and _finite(data.get("usage_percent"), maximum=100)
    return ("healthy", "已取得有效的記憶體容量與使用率") if valid else ("issues", "記憶體容量或使用率超出有效範圍")


def check_gpu(data: dict) -> tuple[FeatureStatus, str]:
    """區分平台不支援、無可用來源，以及裝置存在卻沒有有效使用率。"""
    if data.get("status") == "unsupported":
        return "unavailable", "目前作業系統不支援此 GPU 採集方式"
    if data.get("status") == "unavailable":
        return ("issues", "已偵測到 GPU，但來源未提供有效使用率") if data.get("device_count", 0) > 0 else ("unavailable", "未取得支援的 GPU 讀值，請確認硬體與驅動")
    if data.get("status") == "available" and _finite(data.get("usage_percent"), maximum=100):
        return "healthy", "已取得有效的 GPU 使用率"
    return "issues", "GPU 回應的狀態或使用率無效"


def check_disk_io(data: dict) -> tuple[FeatureStatus, str]:
    """首次建立基準為 Unknown；有效的 0 B/s 為正常閒置。"""
    if data.get("status") == "warming_up":
        return "unknown", "正在建立磁碟取樣基準，等待下一筆資料"
    if data.get("status") == "available" and _finite(data.get("read_bytes_per_second")) and _finite(data.get("write_bytes_per_second")):
        return "healthy", "已取得有效的磁碟讀寫速度"
    return "issues", "磁碟計數器無法讀取，或讀寫速度無效"


def check_network(data: dict) -> tuple[FeatureStatus, str]:
    """沒有可用介面為 Unavailable，尚未取得兩次取樣為 Unknown。"""
    if not data.get("interface"):
        return "unavailable", "沒有可供監控的網路介面"
    rates = [data.get("download_rate"), data.get("upload_rate")]
    if all(rate is None for rate in rates):
        return "unknown", "正在建立網路取樣基準，等待下一筆資料"
    return ("healthy", "已取得有效的網路傳輸速率") if all(_finite(rate) for rate in rates) else ("issues", "網路傳輸速率包含缺值或無效數值")


def check_history_write(data: dict) -> tuple[FeatureStatus, str]:
    """依最新樣本與採集器錯誤判斷寫入是否正常，不以程序是否存活取代證據。"""
    age = data.get("sample_age_ms")
    if age is None:
        return "issues", "資料庫尚無採集紀錄，請確認採集器已啟動"
    if age < -5000:
        return "issues", "最新樣本時間超前，請檢查主機時間"
    collector = data.get("collector") or {}
    attempt = collector.get("last_attempt_at_ms")
    if collector.get("error") and _finite(attempt) and attempt >= data["latest_sample_at_ms"]:
        return "issues", "採集器最近一次採集或寫入失敗"
    if age > HISTORY_STALE_AFTER_MS:
        return "issues", f"已超過 {int(age / 1000)} 秒未寫入新樣本"
    return "healthy", "最近 90 秒內有新樣本成功寫入"


def check_history_query(data: dict) -> tuple[FeatureStatus, str]:
    """查詢成功與資料新鮮度分開判定；空清單仍代表查詢正常完成。"""
    for sample in data["samples"]:
        if not _finite(sample["cpu_usage_percent"], maximum=100) or not _finite(sample["memory_usage_percent"], maximum=100):
            return "issues", "查詢成功，但歷史樣本包含無效使用率"
        for key in ("gpu_usage_percent", "network_download_bytes_per_second", "network_upload_bytes_per_second", "disk_read_bytes_per_second", "disk_write_bytes_per_second"):
            value = sample[key]
            if value is not None and not _finite(value, maximum=100 if key == "gpu_usage_percent" else None):
                return "issues", f"歷史樣本的 {key} 包含無效數值"
    return "healthy", f"查詢成功，最近一小時共 {len(data['samples'])} 筆樣本"


def _run_check(spec: tuple, reader: Callable, check: Callable, now: int) -> FeatureHealth:
    """隔離單項失敗並保留同次原始證據、例外、耗時與最近成功時間。"""
    feature_id, name, description, criteria, source = spec
    started = time.monotonic()
    data = None
    error = None
    try:
        value = reader()
        data = value.model_dump() if hasattr(value, "model_dump") else value
        status, message = check(data)
        if status == "healthy":
            _last_success[feature_id] = now
        if feature_id == "history-write":
            collector_error = (data.get("collector") or {}).get("error")
            if status == "issues" and isinstance(collector_error, dict):
                error = FeatureError(**collector_error)
    except Exception as exc:
        status, message = "issues", f"功能檢查失敗：{type(exc).__name__}"
        error = FeatureError(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    last_success = _last_success.get(feature_id)
    if feature_id == "history-write" and isinstance(data, dict):
        last_success = data.get("latest_sample_at_ms")
    return FeatureHealth(
        id=feature_id, name=name, description=description, criteria=criteria,
        status=status, message=message, checked_at_ms=now, last_success_at_ms=last_success,
        duration_ms=round((time.monotonic() - started) * 1000), source=source,
        raw_data=_json_safe(data), error=error,
    )


def get_feature_health(*, force: bool = False) -> ProjectHealthReport:
    """小量快取避免多個頁面重複採集；手動刷新可強制建立一份新報告。"""
    global _cached
    with _lock:
        if not force and _cached and time.monotonic() - _cached[0] < REPORT_CACHE_SECONDS:
            return _cached[1]
        now = int(time.time() * 1000)
        # 每項保留獨立取得與判定；共通函式只處理例外、時間與快照。
        checks = [
            (readers.get_cpu_info, check_cpu),
            (readers.get_memory_info, check_memory),
            (gpu.get_gpu_info, check_gpu),
            (readers.get_disk_io_info, check_disk_io),
            (readers.get_network_info, check_network),
            (lambda: _history_write(now), check_history_write),
            (lambda: _history_query(now), check_history_query),
        ]
        manifest = json.loads((Path(__file__).resolve().parents[3] / "project.json").read_text(encoding="utf-8"))
        report = ProjectHealthReport(project_id=manifest["id"], project_name=manifest["name"], checked_at_ms=now,
            features=[_run_check(spec, reader, check, now) for spec, (reader, check) in zip(SPECS, checks, strict=True)])
        _cached = (time.monotonic(), report)
        return report
