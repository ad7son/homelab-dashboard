"""歷史降採樣純運算；保留空桶、None 與時間邊界的既有行為。"""
from typing import Optional, Sequence
from .history import MetricSampleRecord

BUCKET_5_MIN_MS = 5 * 60 * 1000
BUCKET_30_MIN_MS = 30 * 60 * 1000

def aggregate_metric_samples(
    samples: Sequence[MetricSampleRecord],
    bucket_ms: int,
) -> list[MetricSampleRecord]:
    """依固定時間桶合併樣本，不修改輸入。

    空桶不補資料；選用指標的 None 不參與平均，整桶無讀值時維持 None。"""
    if bucket_ms <= 0:
        raise ValueError("bucket_ms must be positive")

    if not samples:
        return []

    buckets: dict[int, list[MetricSampleRecord]] = {}
    bucket_order: list[int] = []

    for sample in samples:
        bucket_key = (sample.timestamp_ms // bucket_ms) * bucket_ms
        if bucket_key not in buckets:
            buckets[bucket_key] = []
            bucket_order.append(bucket_key)
        buckets[bucket_key].append(sample)

    return [_aggregate_bucket(buckets[key]) for key in bucket_order]


def _aggregate_bucket(samples: Sequence[MetricSampleRecord]) -> MetricSampleRecord:
    timestamp_ms = int(round(_mean([sample.timestamp_ms for sample in samples])))

    return MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        # 不支援或升級前的 NULL 不參與平均；整桶無資料時仍為 NULL。
        gpu_usage_percent=_mean_optional([sample.gpu_usage_percent for sample in samples]),
        disk_read_bytes_per_second=_mean_optional([sample.disk_read_bytes_per_second for sample in samples]),
        disk_write_bytes_per_second=_mean_optional([sample.disk_write_bytes_per_second for sample in samples]),
        cpu_usage_percent=_mean([sample.cpu_usage_percent for sample in samples]),
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
    return float(sum(values) / len(values))


def _mean_optional(values: Sequence[Optional[float]]) -> Optional[float]:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(sum(present) / len(present))
