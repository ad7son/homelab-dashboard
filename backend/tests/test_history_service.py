from __future__ import annotations

from pathlib import Path

from app.db.metrics_database import MetricSampleRecord, connect_metrics_database, insert_metric_sample
from app.schemas.history import HistoryRange
from app.services.history_service import RANGE_DURATION_MS, get_historical_metrics


def _sample(timestamp_ms: int) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=11.0,
        cpu_temperature_celsius=None,
        memory_usage_percent=22.0,
        network_download_bytes_per_second=None,
        network_upload_bytes_per_second=None,
    )


def test_history_window_calculations(tmp_path: Path) -> None:
    now_ms = 1_700_000_000_000
    db_path = tmp_path / "metrics.db"

    cases = [
        (HistoryRange.M15, RANGE_DURATION_MS[HistoryRange.M15]),
        (HistoryRange.H1, RANGE_DURATION_MS[HistoryRange.H1]),
        (HistoryRange.H24, RANGE_DURATION_MS[HistoryRange.H24]),
        (HistoryRange.D7, RANGE_DURATION_MS[HistoryRange.D7]),
    ]

    for history_range, duration in cases:
        result = get_historical_metrics(
            history_range,
            db_path=db_path,
            now_ms=now_ms,
        )
        assert result.range == history_range
        assert result.end_timestamp_ms == now_ms
        assert result.start_timestamp_ms == now_ms - duration
        assert result.samples == []


def test_history_service_returns_rows_in_window(tmp_path: Path) -> None:
    now_ms = 1_000_000
    db_path = tmp_path / "metrics.db"
    connection = connect_metrics_database(db_path)
    try:
        # 15m window: now-900_000 .. now
        insert_metric_sample(connection, _sample(now_ms - 901_000))  # outside
        insert_metric_sample(connection, _sample(now_ms - 900_000))  # boundary
        insert_metric_sample(connection, _sample(now_ms - 30_000))
        insert_metric_sample(connection, _sample(now_ms))  # boundary
        insert_metric_sample(connection, _sample(now_ms + 1))  # outside
    finally:
        connection.close()

    result = get_historical_metrics(
        HistoryRange.M15,
        db_path=db_path,
        now_ms=now_ms,
    )
    assert [sample.timestamp_ms for sample in result.samples] == [
        now_ms - 900_000,
        now_ms - 30_000,
        now_ms,
    ]
    assert result.samples[0].cpu_temperature_celsius is None
    assert result.samples[0].network_download_bytes_per_second is None
