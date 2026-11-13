"""健康判定與診斷數值正規化；只處理傳入資料，不執行任何 I/O。"""
import math
from typing import Any
from .health import FeatureStatus

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


def check_history_write(data: dict, *, stale_after_ms: int = 90_000) -> tuple[FeatureStatus, str]:
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
    if age > stale_after_ms:
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
