"""以固定時鐘與暫存資料庫驗證歷史時間窗及降採樣解析度。"""

from __future__ import annotations

import pathlib

import monitor_backend
import monitor_support

database_connection = monitor_backend.module(
    "infrastructure.database.connection"
)
metrics_repository = monitor_backend.module(
    "infrastructure.repositories.metrics_repository"
)
domain_history = monitor_backend.module("domain.history")

aggregation = monitor_backend.module("domain.aggregation")

services_history = monitor_backend.module("services.history")


def _sample(
    timestamp_ms: int,
    *,
    cpu_usage_percent: float = 11.0,
    cpu_temperature_celsius: float | None = None,
    memory_usage_percent: float = 22.0,
) -> domain_history.MetricSampleRecord:
    """建立指定 Unix 毫秒時間與百分比的樣本，選用指標預設缺值。"""
    return domain_history.MetricSampleRecord(
        timestamp_ms=timestamp_ms,
        cpu_usage_percent=cpu_usage_percent,
        cpu_temperature_celsius=cpu_temperature_celsius,
        memory_usage_percent=memory_usage_percent,
        network_download_bytes_per_second=None,
        network_upload_bytes_per_second=None,
    )


def test_history_window_calculations(tmp_path: pathlib.Path) -> None:
    now_ms = 1_700_000_000_000
    db_path = tmp_path / "metrics.db"

    cases = [
        (
            domain_history.HistoryRange.M15,
            services_history.RANGE_DURATION_MS[domain_history.HistoryRange.M15],
        ),
        (
            domain_history.HistoryRange.H1,
            services_history.RANGE_DURATION_MS[domain_history.HistoryRange.H1],
        ),
        (
            domain_history.HistoryRange.H24,
            services_history.RANGE_DURATION_MS[domain_history.HistoryRange.H24],
        ),
        (
            domain_history.HistoryRange.D7,
            services_history.RANGE_DURATION_MS[domain_history.HistoryRange.D7],
        ),
    ]

    for history_range, duration in cases:
        result = monitor_support.get_historical_metrics(
            history_range,
            db_path=db_path,
            now_ms=now_ms,
        )
        assert result.range == history_range
        assert result.end_timestamp_ms == now_ms
        assert result.start_timestamp_ms == now_ms - duration
        assert result.samples == []


def test_history_query_returns_rows_in_window(tmp_path: pathlib.Path) -> None:
    now_ms = 1_000_000
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        # 15 分鐘時間窗：now-900_000 到 now，包含兩端。
        metrics_repository.insert_metric_sample(
            connection, _sample(now_ms - 901_000)
        )  # 範圍外。
        metrics_repository.insert_metric_sample(
            connection, _sample(now_ms - 900_000)
        )  # 包含的邊界。
        metrics_repository.insert_metric_sample(
            connection, _sample(now_ms - 30_000)
        )
        metrics_repository.insert_metric_sample(
            connection, _sample(now_ms)
        )  # 包含的邊界。
        metrics_repository.insert_metric_sample(
            connection, _sample(now_ms + 1)
        )  # 範圍外。
    finally:
        connection.close()

    result = monitor_support.get_historical_metrics(
        domain_history.HistoryRange.M15,
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


def test_history_15m_and_1h_remain_raw(tmp_path: pathlib.Path) -> None:
    now_ms = 10_000_000
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        for offset in (0, 30_000, 60_000, 90_000):
            metrics_repository.insert_metric_sample(
                connection,
                _sample(
                    now_ms - offset, cpu_usage_percent=float(offset // 1000)
                ),
            )
    finally:
        connection.close()

    for history_range in (
        domain_history.HistoryRange.M15,
        domain_history.HistoryRange.H1,
    ):
        result = monitor_support.get_historical_metrics(
            history_range,
            db_path=db_path,
            now_ms=now_ms,
        )
        assert len(result.samples) == 4
        assert [sample.timestamp_ms for sample in result.samples] == [
            now_ms - 90_000,
            now_ms - 60_000,
            now_ms - 30_000,
            now_ms,
        ]


def test_history_24h_applies_5_minute_aggregation(
    tmp_path: pathlib.Path,
) -> None:
    now_ms = 100_000_000
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        # Two raw samples in the same 5-minute bucket, one in the next.
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 4 * 60 * 1000, cpu_usage_percent=10.0),
        )
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 3 * 60 * 1000, cpu_usage_percent=30.0),
        )
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 60_000, cpu_usage_percent=50.0),
        )
    finally:
        connection.close()

    result = monitor_support.get_historical_metrics(
        domain_history.HistoryRange.H24,
        db_path=db_path,
        now_ms=now_ms,
    )
    assert len(result.samples) == 2
    assert result.samples[0].cpu_usage_percent == 20.0
    assert result.samples[1].cpu_usage_percent == 50.0
    assert result.samples[0].timestamp_ms < result.samples[1].timestamp_ms


def test_history_7d_applies_30_minute_aggregation(
    tmp_path: pathlib.Path,
) -> None:
    now_ms = 200_000_000
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 20 * 60 * 1000, cpu_usage_percent=10.0),
        )
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 10 * 60 * 1000, cpu_usage_percent=30.0),
        )
        metrics_repository.insert_metric_sample(
            connection,
            _sample(now_ms - 60_000, cpu_usage_percent=70.0),
        )
    finally:
        connection.close()

    result = monitor_support.get_historical_metrics(
        domain_history.HistoryRange.D7,
        db_path=db_path,
        now_ms=now_ms,
    )
    assert len(result.samples) == 2
    assert result.samples[0].cpu_usage_percent == 20.0
    assert result.samples[1].cpu_usage_percent == 70.0


def test_history_24h_point_count_bounded_with_dense_seed(
    tmp_path: pathlib.Path,
) -> None:
    now_ms = aggregation.BUCKET_5_MIN_MS * 300
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        # Two raw samples in each 5-minute bucket across 24h (when both fit).
        start = (
            now_ms
            - services_history.RANGE_DURATION_MS[
                domain_history.HistoryRange.H24
            ]
        )
        bucket = start
        while bucket <= now_ms:
            metrics_repository.insert_metric_sample(
                connection, _sample(bucket, cpu_usage_percent=10.0)
            )
            second = bucket + 30_000
            if second <= now_ms:
                metrics_repository.insert_metric_sample(
                    connection,
                    _sample(second, cpu_usage_percent=20.0),
                )
            bucket += aggregation.BUCKET_5_MIN_MS
    finally:
        connection.close()

    result = monitor_support.get_historical_metrics(
        domain_history.HistoryRange.H24,
        db_path=db_path,
        now_ms=now_ms,
    )
    assert len(result.samples) <= 289
    assert len(result.samples) >= 280
    # Interior buckets with two samples average to 15%.
    assert result.samples[0].cpu_usage_percent == 15.0
    assert result.samples[1].cpu_usage_percent == 15.0


def test_history_7d_point_count_bounded_with_sparse_seed(
    tmp_path: pathlib.Path,
) -> None:
    now_ms = aggregation.BUCKET_30_MIN_MS * 400
    db_path = tmp_path / "metrics.db"
    connection = database_connection.connect_metrics_database(db_path)
    try:
        # One sample near the start of each 30-minute bucket across 7 days.
        start = (
            now_ms
            - services_history.RANGE_DURATION_MS[domain_history.HistoryRange.D7]
        )
        timestamp = start
        while timestamp <= now_ms:
            metrics_repository.insert_metric_sample(
                connection, _sample(timestamp)
            )
            timestamp += aggregation.BUCKET_30_MIN_MS
    finally:
        connection.close()

    result = monitor_support.get_historical_metrics(
        domain_history.HistoryRange.D7,
        db_path=db_path,
        now_ms=now_ms,
    )
    assert len(result.samples) <= 337
    assert len(result.samples) >= 330
