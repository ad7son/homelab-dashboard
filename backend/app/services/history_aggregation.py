"""Query-time historical metric aggregation (no rollup tables)."""

from __future__ import annotations

from typing import Optional, Sequence

from app.db.metrics_database import MetricSampleRecord

BUCKET_5_MIN_MS = 5 * 60 * 1000
BUCKET_30_MIN_MS = 30 * 60 * 1000


def aggregate_metric_samples(
    samples: Sequence[MetricSampleRecord],
    bucket_ms: int,
) -> list[MetricSampleRecord]:
    """
    Aggregate raw samples into fixed-duration buckets.

    Empty buckets are omitted so missing periods remain genuine gaps.
    Does not mutate the input sequence.
    """
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
