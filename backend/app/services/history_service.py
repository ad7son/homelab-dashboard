from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional, Union

from app.db.metrics_database import (
    UnsupportedSchemaVersionError,
    connect_metrics_database,
    read_metric_samples,
)
from app.schemas.history import (
    HistoricalMetricSample,
    HistoricalMetricsResponse,
    HistoryRange,
)

logger = logging.getLogger("a7las.history")

RANGE_DURATION_MS = {
    HistoryRange.M15: 15 * 60 * 1000,
    HistoryRange.H1: 60 * 60 * 1000,
    HistoryRange.H24: 24 * 60 * 60 * 1000,
    HistoryRange.D7: 7 * 24 * 60 * 60 * 1000,
}


class HistoricalMetricsUnavailableError(RuntimeError):
    """Raised when the historical metrics database cannot be queried."""


def get_historical_metrics(
    history_range: HistoryRange,
    *,
    db_path: Optional[Union[str, Path]] = None,
    now_ms: Optional[int] = None,
    clock_ms: Optional[Callable[[], int]] = None,
) -> HistoricalMetricsResponse:
    """
    Build a historical metrics response for the requested range.

    The window is anchored to current wall-clock time (or injected now_ms),
    not to the newest database row.
    """
    end_timestamp_ms = _resolve_now_ms(now_ms=now_ms, clock_ms=clock_ms)
    start_timestamp_ms = end_timestamp_ms - RANGE_DURATION_MS[history_range]

    try:
        connection = connect_metrics_database(db_path)
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

    samples = [
        HistoricalMetricSample(
            timestamp_ms=record.timestamp_ms,
            cpu_usage_percent=record.cpu_usage_percent,
            cpu_temperature_celsius=record.cpu_temperature_celsius,
            memory_usage_percent=record.memory_usage_percent,
            network_download_bytes_per_second=record.network_download_bytes_per_second,
            network_upload_bytes_per_second=record.network_upload_bytes_per_second,
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
