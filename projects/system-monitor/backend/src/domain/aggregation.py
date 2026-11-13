"""歷史降採樣純運算；保留空桶、None 與時間邊界的既有行為。"""

from __future__ import annotations

from typing import Optional, Sequence

from . import history

BUCKET_5_MIN_MS = 5 * 60 * 1000
BUCKET_30_MIN_MS = 30 * 60 * 1000


def aggregate_metric_samples(
    samples: Sequence[history.MetricSampleRecord],
    bucket_ms: int,
) -> list[history.MetricSampleRecord]:
    """依固定時間桶合併樣本，不修改輸入或補造空桶。

    Args:
        samples: 原始樣本序列；輸出桶順序依首次出現順序決定。
        bucket_ms: 正數時間桶寬度，單位毫秒，以 Unix 時間原點對齊。

    Returns:
        每桶一筆平均樣本；時間戳平均後四捨五入為整數毫秒。
        None 不參與平均，整桶無有效選用值時保留 None；零值參與平均。
    """
    if bucket_ms <= 0:
        raise ValueError("bucket_ms must be positive")

    if not samples:
        return []

    buckets: dict[int, list[history.MetricSampleRecord]] = {}
    bucket_order: list[int] = []

    for sample in samples:
        bucket_key = (sample.timestamp_ms // bucket_ms) * bucket_ms
        if bucket_key not in buckets:
            buckets[bucket_key] = []
            bucket_order.append(bucket_key)
        buckets[bucket_key].append(sample)

    return [_aggregate_bucket(buckets[key]) for key in bucket_order]


def _aggregate_bucket(
    samples: Sequence[history.MetricSampleRecord],
) -> history.MetricSampleRecord:
    """將非空桶合併成一筆樣本；所有欄位各自計算平均。"""
    timestamp_ms = int(
        round(_mean([sample.timestamp_ms for sample in samples]))
    )

    return history.MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        # 不支援或升級前的 NULL 不參與平均；整桶無資料時仍為 NULL。
        gpu_usage_percent=_mean_optional(
            [sample.gpu_usage_percent for sample in samples]
        ),
        disk_read_bytes_per_second=_mean_optional(
            [sample.disk_read_bytes_per_second for sample in samples]
        ),
        disk_write_bytes_per_second=_mean_optional(
            [sample.disk_write_bytes_per_second for sample in samples]
        ),
        cpu_usage_percent=_mean(
            [sample.cpu_usage_percent for sample in samples]
        ),
        cpu_temperature_celsius=_mean_optional(
            [sample.cpu_temperature_celsius for sample in samples]
        ),
        memory_usage_percent=_mean(
            [sample.memory_usage_percent for sample in samples]
        ),
        network_download_bytes_per_second=_mean_optional(
            [sample.network_download_bytes_per_second for sample in samples]
        ),
        network_upload_bytes_per_second=_mean_optional(
            [sample.network_upload_bytes_per_second for sample in samples]
        ),
    )


def _mean(values: Sequence[float]) -> float:
    """回傳非空數值序列的算術平均值。"""
    return float(sum(values) / len(values))


def _mean_optional(values: Sequence[float | None]) -> float | None:
    """回傳排除 None 後的平均值；全部缺值時回傳 None。"""
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(sum(present) / len(present))
