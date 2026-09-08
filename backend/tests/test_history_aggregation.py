from __future__ import annotations

from app.db.metrics_database import MetricSampleRecord
from app.services.history_aggregation import (
    BUCKET_5_MIN_MS,
    BUCKET_30_MIN_MS,
    aggregate_metric_samples,
)


def _sample(
    timestamp_ms: int,
    *,
    cpu_usage_percent: float = 10.0,
    cpu_temperature_celsius: float | None = 40.0,
    memory_usage_percent: float = 50.0,
    network_download_bytes_per_second: float | None = 100.0,
    network_upload_bytes_per_second: float | None = 50.0,
) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=cpu_usage_percent,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=memory_usage_percent,
        network_download_bytes_per_second=network_download_bytes_per_second,
        network_upload_bytes_per_second=network_upload_bytes_per_second,
    )


def test_aggregate_averages_cpu_and_memory() -> None:
    samples = [
        _sample(0, cpu_usage_percent=10.0, memory_usage_percent=20.0),
        _sample(30_000, cpu_usage_percent=30.0, memory_usage_percent=40.0),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 1
    assert result[0].cpu_usage_percent == 20.0
    assert result[0].memory_usage_percent == 30.0
    assert result[0].timestamp_ms == 15_000


def test_aggregate_temperature_ignores_nulls() -> None:
    samples = [
        _sample(0, cpu_temperature_celsius=40.0),
        _sample(30_000, cpu_temperature_celsius=None),
        _sample(60_000, cpu_temperature_celsius=50.0),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 1
    assert result[0].cpu_temperature_celsius == 45.0


def test_aggregate_all_null_temperature_remains_null() -> None:
    samples = [
        _sample(0, cpu_temperature_celsius=None),
        _sample(30_000, cpu_temperature_celsius=None),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 1
    assert result[0].cpu_temperature_celsius is None


def test_aggregate_network_averages_valid_values() -> None:
    samples = [
        _sample(
            0,
            network_download_bytes_per_second=100.0,
            network_upload_bytes_per_second=None,
        ),
        _sample(
            30_000,
            network_download_bytes_per_second=300.0,
            network_upload_bytes_per_second=40.0,
        ),
        _sample(
            60_000,
            network_download_bytes_per_second=None,
            network_upload_bytes_per_second=60.0,
        ),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 1
    assert result[0].network_download_bytes_per_second == 200.0
    assert result[0].network_upload_bytes_per_second == 50.0


def test_aggregate_all_null_network_remains_null() -> None:
    samples = [
        _sample(
            0,
            network_download_bytes_per_second=None,
            network_upload_bytes_per_second=None,
        ),
        _sample(
            30_000,
            network_download_bytes_per_second=None,
            network_upload_bytes_per_second=None,
        ),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert result[0].network_download_bytes_per_second is None
    assert result[0].network_upload_bytes_per_second is None


def test_aggregate_keeps_separate_buckets_and_order() -> None:
    samples = [
        _sample(0, cpu_usage_percent=10.0),
        _sample(30_000, cpu_usage_percent=20.0),
        _sample(BUCKET_5_MIN_MS, cpu_usage_percent=30.0),
        _sample(BUCKET_5_MIN_MS + 30_000, cpu_usage_percent=50.0),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 2
    assert result[0].cpu_usage_percent == 15.0
    assert result[1].cpu_usage_percent == 40.0
    assert result[0].timestamp_ms < result[1].timestamp_ms


def test_aggregate_does_not_fabricate_empty_buckets() -> None:
    samples = [
        _sample(0, cpu_usage_percent=10.0),
        # Skip one 5-minute bucket entirely.
        _sample(2 * BUCKET_5_MIN_MS, cpu_usage_percent=20.0),
    ]

    result = aggregate_metric_samples(samples, BUCKET_5_MIN_MS)
    assert len(result) == 2
    assert result[1].timestamp_ms - result[0].timestamp_ms >= BUCKET_5_MIN_MS


def test_aggregate_does_not_mutate_source() -> None:
    samples = [
        _sample(0, cpu_usage_percent=10.0),
        _sample(30_000, cpu_usage_percent=20.0),
    ]
    original = [
        (
            sample.timestamp_ms,
            sample.cpu_usage_percent,
            sample.cpu_temperature_celsius,
        )
        for sample in samples
    ]

    aggregate_metric_samples(samples, BUCKET_5_MIN_MS)

    assert [
        (
            sample.timestamp_ms,
            sample.cpu_usage_percent,
            sample.cpu_temperature_celsius,
        )
        for sample in samples
    ] == original


def test_aggregate_30_minute_buckets_for_7d_resolution() -> None:
    samples = [
        _sample(0, cpu_usage_percent=10.0),
        _sample(10 * 60 * 1000, cpu_usage_percent=20.0),
        _sample(BUCKET_30_MIN_MS, cpu_usage_percent=40.0),
    ]

    result = aggregate_metric_samples(samples, BUCKET_30_MIN_MS)
    assert len(result) == 2
    assert result[0].cpu_usage_percent == 15.0
    assert result[1].cpu_usage_percent == 40.0
