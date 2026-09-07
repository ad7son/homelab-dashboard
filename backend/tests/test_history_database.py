from __future__ import annotations

from pathlib import Path

from app.db.metrics_database import (
    MetricSampleRecord,
    connect_metrics_database,
    insert_metric_sample,
    read_metric_samples,
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


def test_read_metric_samples_range_boundaries_and_ordering(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(connection, _sample(1_000, cpu_usage_percent=1.0))
        insert_metric_sample(connection, _sample(2_000, cpu_usage_percent=2.0))
        insert_metric_sample(connection, _sample(3_000, cpu_usage_percent=3.0))
        insert_metric_sample(connection, _sample(4_000, cpu_usage_percent=4.0))
        insert_metric_sample(connection, _sample(5_000, cpu_usage_percent=5.0))

        rows = read_metric_samples(connection, 2_000, 4_000)
        assert [row.timestamp_ms for row in rows] == [2_000, 3_000, 4_000]
        assert [row.cpu_usage_percent for row in rows] == [2.0, 3.0, 4.0]
    finally:
        connection.close()


def test_read_metric_samples_excludes_outside_range(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(connection, _sample(100))
        insert_metric_sample(connection, _sample(200))
        insert_metric_sample(connection, _sample(300))

        rows = read_metric_samples(connection, 150, 250)
        assert [row.timestamp_ms for row in rows] == [200]
    finally:
        connection.close()


def test_read_metric_samples_preserves_nulls_and_empty_range(tmp_path: Path) -> None:
    connection = connect_metrics_database(tmp_path / "metrics.db")
    try:
        insert_metric_sample(
            connection,
            _sample(
                10_000,
                cpu_temperature_celsius=None,
                network_download_bytes_per_second=None,
                network_upload_bytes_per_second=None,
            ),
        )

        rows = read_metric_samples(connection, 10_000, 10_000)
        assert len(rows) == 1
        assert rows[0].cpu_temperature_celsius is None
        assert rows[0].network_download_bytes_per_second is None
        assert rows[0].network_upload_bytes_per_second is None

        assert read_metric_samples(connection, 20_000, 30_000) == []
    finally:
        connection.close()
