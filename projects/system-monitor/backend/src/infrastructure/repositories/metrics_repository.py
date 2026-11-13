"""樣本 SQL 的唯一入口；Repository 管理操作範圍，connection 管理連線設定。"""
import sqlite3
from pathlib import Path
from typing import Optional
from ...domain.history import MetricSampleRecord
from ...services.exceptions import DuplicateMetricSampleError, RepositoryUnavailableError
from ..database import connection as db
from ..database.migration_runner import UnsupportedSchemaVersionError

_INSERT_METRIC_SAMPLE_SQL = """
INSERT INTO metric_samples (
    timestamp_ms,
    cpu_usage_percent,
    cpu_temperature_celsius,
    memory_usage_percent,
    network_download_bytes_per_second,
    network_upload_bytes_per_second,
    gpu_usage_percent,
    disk_read_bytes_per_second,
    disk_write_bytes_per_second
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

def insert_metric_sample(
    connection: sqlite3.Connection,
    sample: MetricSampleRecord,
) -> None:
    """在單一交易寫入樣本；重複時間戳維持原有專用例外。"""
    try:
        with connection:
            connection.execute(
                _INSERT_METRIC_SAMPLE_SQL,
                (
                    sample.timestamp_ms,
                    sample.cpu_usage_percent,
                    sample.cpu_temperature_celsius,
                    sample.memory_usage_percent,
                    sample.network_download_bytes_per_second,
                    sample.network_upload_bytes_per_second,
                    sample.gpu_usage_percent,
                    sample.disk_read_bytes_per_second,
                    sample.disk_write_bytes_per_second,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise DuplicateMetricSampleError(
            f"metric sample already exists for timestamp_ms={sample.timestamp_ms}"
        ) from exc


def count_metric_samples(connection: sqlite3.Connection) -> int:
    """計算樣本筆數，供資料庫與採集測試驗證寫入結果。"""
    row = connection.execute("SELECT COUNT(*) AS n FROM metric_samples").fetchone()
    return int(row["n"] if isinstance(row, sqlite3.Row) else row[0])


def fetch_metric_sample(
    connection: sqlite3.Connection,
    timestamp_ms: int,
) -> Optional[MetricSampleRecord]:
    """依時間戳取得單筆樣本，供採集與遷移測試確認欄位。"""
    row = connection.execute(
        """
        SELECT
            timestamp_ms,
            cpu_usage_percent,
            cpu_temperature_celsius,
            memory_usage_percent,
            network_download_bytes_per_second,
            network_upload_bytes_per_second,
            gpu_usage_percent,
            disk_read_bytes_per_second,
            disk_write_bytes_per_second
        FROM metric_samples
        WHERE timestamp_ms = ?
        """,
        (timestamp_ms,),
    ).fetchone()

    if row is None:
        return None

    return _row_to_metric_sample(row)


def read_metric_samples(
    connection: sqlite3.Connection,
    start_timestamp_ms: int,
    end_timestamp_ms: int,
) -> list[MetricSampleRecord]:
    """依包含起訖邊界的時間區間讀取樣本，按時間遞增排列。

    15m／1h 等範圍的定義由 query.py 處理，此處只執行 SQL。"""
    rows = connection.execute(
        """
        SELECT
            timestamp_ms,
            cpu_usage_percent,
            cpu_temperature_celsius,
            memory_usage_percent,
            network_download_bytes_per_second,
            network_upload_bytes_per_second,
            gpu_usage_percent,
            disk_read_bytes_per_second,
            disk_write_bytes_per_second
        FROM metric_samples
        WHERE timestamp_ms >= ?
          AND timestamp_ms <= ?
        ORDER BY timestamp_ms ASC
        """,
        (start_timestamp_ms, end_timestamp_ms),
    ).fetchall()

    return [_row_to_metric_sample(row) for row in rows]


def delete_metric_samples_before(
    connection: sqlite3.Connection,
    cutoff_timestamp_ms: int,
) -> int:
    """刪除嚴格早於截止時間的資料，等於邊界的樣本保留。

    保留天數由採集器決定，此處只套用截止時間並回傳刪除筆數。"""
    with connection:
        cursor = connection.execute(
            "DELETE FROM metric_samples WHERE timestamp_ms < ?",
            (int(cutoff_timestamp_ms),),
        )
    return int(cursor.rowcount)


def _row_to_metric_sample(row: sqlite3.Row) -> MetricSampleRecord:
    return MetricSampleRecord(
        timestamp_ms=int(row["timestamp_ms"]),
        cpu_usage_percent=float(row["cpu_usage_percent"]),
        cpu_temperature_celsius=(
            None
            if row["cpu_temperature_celsius"] is None
            else float(row["cpu_temperature_celsius"])
        ),
        memory_usage_percent=float(row["memory_usage_percent"]),
        network_download_bytes_per_second=(
            None
            if row["network_download_bytes_per_second"] is None
            else float(row["network_download_bytes_per_second"])
        ),
        gpu_usage_percent=row["gpu_usage_percent"],
        disk_read_bytes_per_second=row["disk_read_bytes_per_second"],
        disk_write_bytes_per_second=row["disk_write_bytes_per_second"],
        network_upload_bytes_per_second=(
            None
            if row["network_upload_bytes_per_second"] is None
            else float(row["network_upload_bytes_per_second"])
        ),
    )

class SQLiteMetricsRepository:
    def __init__(self, path: Path, busy_timeout_ms: int = 5000):
        self.path = path
        self._busy_timeout_ms = busy_timeout_ms

    def _connect(self, read_only=False):
        return db.connect_metrics_database(self.path, read_only=read_only, busy_timeout_ms=self._busy_timeout_ms)

    def initialize(self):
        connection = self._connect()
        connection.close()

    def insert(self, sample: MetricSampleRecord):
        connection = self._connect()
        try:
            insert_metric_sample(connection, sample)
        finally:
            connection.close()

    def read(self, start_ms: int, end_ms: int, *, read_only=False):
        try:
            connection = self._connect(read_only)
            try:
                return read_metric_samples(connection, start_ms, end_ms)
            finally:
                connection.close()
        except (sqlite3.Error, OSError, UnsupportedSchemaVersionError) as exc:
            raise RepositoryUnavailableError("Historical metrics database unavailable") from exc

    def latest(self):
        connection = self._connect(read_only=True)
        try:
            row = connection.execute("SELECT * FROM metric_samples ORDER BY timestamp_ms DESC LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def delete_before(self, cutoff_ms: int):
        connection = self._connect()
        try:
            return delete_metric_samples_before(connection, cutoff_ms)
        finally:
            connection.close()
