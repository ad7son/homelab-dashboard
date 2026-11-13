"""健康判定與診斷數值正規化；只處理傳入資料，不執行任何 I/O。"""

from __future__ import annotations

import math
from typing import Any

from . import health


def _finite(
    value: Any, minimum: float = 0, maximum: float | None = None
) -> bool:
    """判定是否為範圍內的有限數值，明確排除 bool。"""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= minimum
        and (maximum is None or value <= maximum)
    )


def json_safe(value: Any) -> Any:
    """將 NaN／Infinity 轉為明確字串，保留原始異常供排錯。

    Args:
        value: 採集證據，可包含巢狀字典、清單或 tuple。

    Returns:
        遞迴轉換後的新容器；有效葉節點維持原值，不將缺值或異常改成零。
    """
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def check_cpu(data: dict[str, Any]) -> tuple[health.FeatureStatus, str]:
    """檢查 CPU 使用率及核心數；高負載不代表採集功能異常。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    valid = (
        _finite(data.get("usage_percent"), maximum=100)
        and _finite(data.get("physical_cores"), 1)
        and _finite(data.get("logical_cores"), 1)
    )
    return (
        ("healthy", "已取得有效的 CPU 使用率與核心資訊")
        if valid
        else ("issues", "CPU 回應包含無效使用率或核心數")
    )


def check_memory(data: dict[str, Any]) -> tuple[health.FeatureStatus, str]:
    """檢查記憶體容量與百分比範圍，不假設 used 加 available 等於 total。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    total = data.get("total")
    valid = (
        _finite(total, 1)
        and _finite(data.get("used"), maximum=total)
        and _finite(data.get("available"), maximum=total)
        and _finite(data.get("usage_percent"), maximum=100)
    )
    return (
        ("healthy", "已取得有效的記憶體容量與使用率")
        if valid
        else ("issues", "記憶體容量或使用率超出有效範圍")
    )


def check_gpu(data: dict[str, Any]) -> tuple[health.FeatureStatus, str]:
    """依平台支援度、裝置數與有效使用率區分不可用與異常。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    if data.get("status") == "unsupported":
        return "unavailable", "目前作業系統不支援此 GPU 採集方式"
    if data.get("status") == "unavailable":
        return (
            ("issues", "已偵測到 GPU，但來源未提供有效使用率")
            if data.get("device_count", 0) > 0
            else ("unavailable", "未取得支援的 GPU 讀值，請確認硬體與驅動")
        )
    if data.get("status") == "available" and _finite(
        data.get("usage_percent"), maximum=100
    ):
        return "healthy", "已取得有效的 GPU 使用率"
    return "issues", "GPU 回應的狀態或使用率無效"


def check_disk_io(data: dict[str, Any]) -> tuple[health.FeatureStatus, str]:
    """將首次取樣判為 unknown、有效零速率判為 healthy。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    if data.get("status") == "warming_up":
        return "unknown", "正在建立磁碟取樣基準，等待下一筆資料"
    if (
        data.get("status") == "available"
        and _finite(data.get("read_bytes_per_second"))
        and _finite(data.get("write_bytes_per_second"))
    ):
        return "healthy", "已取得有效的磁碟讀寫速度"
    return "issues", "磁碟計數器無法讀取，或讀寫速度無效"


def check_network(data: dict[str, Any]) -> tuple[health.FeatureStatus, str]:
    """區分無可用介面、尚無基準與有效的上下傳速率。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    if not data.get("interface"):
        return "unavailable", "沒有可供監控的網路介面"
    rates = [data.get("download_rate"), data.get("upload_rate")]
    if all(rate is None for rate in rates):
        return "unknown", "正在建立網路取樣基準，等待下一筆資料"
    return (
        ("healthy", "已取得有效的網路傳輸速率")
        if all(_finite(rate) for rate in rates)
        else ("issues", "網路傳輸速率包含缺值或無效數值")
    )


def check_history_write(
    data: dict[str, Any], *, stale_after_ms: int = 90_000
) -> tuple[health.FeatureStatus, str]:
    """以樣本新鮮度與採集器錯誤紀錄判斷寫入是否正常。

    Args:
        data: 包含樣本時間、資料年齡及採集器旁檔的同次證據。
        stale_after_ms: 允許的最大資料年齡，單位毫秒，等於邊界仍有效。

    Returns:
        (狀態, 中文結果摘要) 的 tuple。樣本超前逾 5 秒視為主機時間異常；
        最新採集失敗與過期樣本皆為 issues，不以程序存在取代寫入證據。
    """
    age = data.get("sample_age_ms")
    if age is None:
        return "issues", "資料庫尚無採集紀錄，請確認採集器已啟動"
    if age < -5000:
        return "issues", "最新樣本時間超前，請檢查主機時間"
    collector = data.get("collector") or {}
    attempt = collector.get("last_attempt_at_ms")
    if (
        collector.get("error")
        and _finite(attempt)
        and attempt >= data["latest_sample_at_ms"]
    ):
        return "issues", "採集器最近一次採集或寫入失敗"
    if age > stale_after_ms:
        return "issues", f"已超過 {int(age / 1000)} 秒未寫入新樣本"
    return "healthy", "最近 90 秒內有新樣本成功寫入"


def check_history_query(
    data: dict[str, Any],
) -> tuple[health.FeatureStatus, str]:
    """驗證歷史樣本必要及選用數值；空結果仍代表查詢成功。

    Args:
        data: 與此功能相符的採集或查詢字典，不在此執行 I/O。

    Returns:
        (狀態, 中文結果摘要) 的 tuple；此處不修改資料或保存快取。
    """
    for sample in data["samples"]:
        if not _finite(sample["cpu_usage_percent"], maximum=100) or not _finite(
            sample["memory_usage_percent"], maximum=100
        ):
            return "issues", "查詢成功，但歷史樣本包含無效使用率"
        for key in (
            "gpu_usage_percent",
            "network_download_bytes_per_second",
            "network_upload_bytes_per_second",
            "disk_read_bytes_per_second",
            "disk_write_bytes_per_second",
        ):
            value = sample[key]
            if value is not None and not _finite(
                value, maximum=100 if key == "gpu_usage_percent" else None
            ):
                return "issues", f"歷史樣本的 {key} 包含無效數值"
    return "healthy", f"查詢成功，最近一小時共 {len(data['samples'])} 筆樣本"
