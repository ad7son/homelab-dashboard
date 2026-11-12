"""將時間範圍轉為歷史回應；長範圍降採樣，不建立額外彙總資料表。

所有 SQL 與連線規則交由 database.py，正常查詢與健康探測共用此流程。
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional, Sequence, Union

from .database import UnsupportedSchemaVersionError, connect_metrics_database, read_metric_samples
from .models import MetricSampleRecord, HistoricalMetricSample, HistoricalMetricsResponse, HistoryRange


# ── 降採樣：空缺維持空缺，None 不參與平均 ──

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


# ── 範圍查詢與 API 回應 ──

RANGE_DURATION_MS = {
    HistoryRange.M15: 15 * 60 * 1000,
    HistoryRange.H1: 60 * 60 * 1000,
    HistoryRange.H24: 24 * 60 * 60 * 1000,
    HistoryRange.D7: 7 * 24 * 60 * 60 * 1000,
}

# 查詢時才降採樣；None 表示直接回傳原始樣本。
RANGE_AGGREGATION_BUCKET_MS: dict[HistoryRange, Optional[int]] = {
    HistoryRange.M15: None,
    HistoryRange.H1: None,
    HistoryRange.H24: BUCKET_5_MIN_MS,
    HistoryRange.D7: BUCKET_30_MIN_MS,
}


class HistoricalMetricsUnavailableError(RuntimeError):
    """歷史資料庫無法查詢；API 將此例外轉為既有的 503 回應。"""


def get_historical_metrics(
    history_range: HistoryRange,
    *,
    db_path: Optional[Union[str, Path]] = None,
    now_ms: Optional[int] = None,
    clock_ms: Optional[Callable[[], int]] = None,
    read_only: bool = False,
) -> HistoricalMetricsResponse:
    """以現在時間計算查詢區間，必要時降採樣並組成回應。

    區間不跟隨最新樣本移動，讓停止採集後的缺資料仍可被看見。
    健康檢查傳入 read_only=True，使用同一流程但不建立或遷移資料庫。"""
    end_timestamp_ms = _resolve_now_ms(now_ms=now_ms, clock_ms=clock_ms)
    start_timestamp_ms = end_timestamp_ms - RANGE_DURATION_MS[history_range]

    try:
        connection = connect_metrics_database(db_path, read_only=read_only)
        try:
            records = read_metric_samples(
                connection,
                start_timestamp_ms,
                end_timestamp_ms,
            )
        finally:
            connection.close()
    except (sqlite3.Error, OSError, UnsupportedSchemaVersionError) as exc:
        raise HistoricalMetricsUnavailableError(
            "Historical metrics database unavailable"
        ) from exc

    bucket_ms = RANGE_AGGREGATION_BUCKET_MS[history_range]
    if bucket_ms is not None:
        records = aggregate_metric_samples(records, bucket_ms)

    samples = [
        HistoricalMetricSample(
            timestamp_ms=record.timestamp_ms,
            cpu_usage_percent=record.cpu_usage_percent,
            cpu_temperature_celsius=record.cpu_temperature_celsius,
            memory_usage_percent=record.memory_usage_percent,
            network_download_bytes_per_second=record.network_download_bytes_per_second,
            network_upload_bytes_per_second=record.network_upload_bytes_per_second,
            gpu_usage_percent=record.gpu_usage_percent,
            disk_read_bytes_per_second=record.disk_read_bytes_per_second,
            disk_write_bytes_per_second=record.disk_write_bytes_per_second,
        )
        for record in records
    ]

    return HistoricalMetricsResponse(
        range=history_range,
        start_timestamp_ms=start_timestamp_ms,
        end_timestamp_ms=end_timestamp_ms,
        samples=samples,
    )


def _resolve_now_ms(
    *,
    now_ms: Optional[int],
    clock_ms: Optional[Callable[[], int]],
) -> int:
    if now_ms is not None:
        return int(now_ms)
    if clock_ms is not None:
        return int(clock_ms())
    return int(time.time() * 1000)
