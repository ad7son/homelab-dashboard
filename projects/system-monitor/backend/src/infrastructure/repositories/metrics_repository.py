"""樣本 SQL 的唯一入口；Repository 管理操作範圍，connection 管理連線設定。"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import Any

from ...domain import history
from ...services import exceptions
from ..database import connection as database_connection
from ..database import migration_runner

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
    sample: history.MetricSampleRecord,
) -> None:
    """在單一交易中寫入一筆樣本，不以新資料覆蓋重複時間戳。

    Args:
        connection: 呼叫端持有的可寫連線，不由此函式關閉。
        sample: 不可變樣本；None 欄位寫成 SQL NULL。

    Raises:
        exceptions.DuplicateMetricSampleError: 插入發生完整性衝突。
        sqlite3.Error: 其他儲存錯誤，保留原始例外供上層處理。
    """
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
        raise exceptions.DuplicateMetricSampleError(
            f"metric sample already exists for timestamp_ms={sample.timestamp_ms}"
        ) from exc


def count_metric_samples(connection: sqlite3.Connection) -> int:
    """計算樣本筆數，供資料庫與採集測試驗證寫入結果。"""
    row = connection.execute(
        "SELECT COUNT(*) AS n FROM metric_samples"
    ).fetchone()
    return int(row["n"] if isinstance(row, sqlite3.Row) else row[0])


def fetch_metric_sample(
    connection: sqlite3.Connection,
    timestamp_ms: int,
) -> history.MetricSampleRecord | None:
    """依精確時間戳讀取一筆樣本。

    Args:
        connection: 由呼叫端負責關閉的連線。
        timestamp_ms: Unix 毫秒時間戳。

    Returns:
        對應樣本；找不到時為 None，SQL NULL 保留為 None。
    """
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
) -> list[history.MetricSampleRecord]:
    """依包含起訖邊界的時間窗讀取樣本，不執行降採樣。

    Args:
        connection: 由呼叫端負責關閉的連線。
        start_timestamp_ms: 起始 Unix 毫秒時間戳，包含此邊界。
        end_timestamp_ms: 結束 Unix 毫秒時間戳，包含此邊界。

    Returns:
        依時間遞增的樣本清單；無資料時為空清單。
    """
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
    """刪除嚴格早於截止時間的樣本，保留剛好等於邊界的資料。

    Args:
        connection: 由呼叫端負責關閉的可寫連線。
        cutoff_timestamp_ms: 採集服務依保留政策計算的 Unix 毫秒時間戳。

    Returns:
        交易內實際刪除的筆數。
    """
    with connection:
        cursor = connection.execute(
            "DELETE FROM metric_samples WHERE timestamp_ms < ?",
            (int(cutoff_timestamp_ms),),
        )
    return int(cursor.rowcount)


def _row_to_metric_sample(row: sqlite3.Row) -> history.MetricSampleRecord:
    """將一筆完整 SQLite Row 轉為不可變樣本，保留 NULL 與有效零值。"""
    return history.MetricSampleRecord(
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
    """每次操作自行開啟並關閉連線的 SQLite 歷史儲存介面。

    Attributes:
        path: 此實例使用的資料庫路徑，不是已開啟的連線。
    """

    def __init__(self, path: pathlib.Path, busy_timeout_ms: int = 5000) -> None:
        """建立儲存介面，不立即開啟連線。

        Args:
            path: 資料庫位置，通常由組裝層傳入絕對路徑。
            busy_timeout_ms: 可寫連線等待資料庫鎖的毫秒上限。
        """
        self.path = path
        self._busy_timeout_ms = busy_timeout_ms

    def _connect(self, read_only: bool = False) -> sqlite3.Connection:
        """回傳新連線；read_only 決定是否允許建檔與遷移，呼叫端負責關閉。"""
        return database_connection.connect_metrics_database(
            self.path,
            read_only=read_only,
            busy_timeout_ms=self._busy_timeout_ms,
        )

    def initialize(self) -> None:
        """初始化或升級資料庫後關閉連線，不持有跨操作的連線。"""
        connection = self._connect()
        connection.close()

    def insert(self, sample: history.MetricSampleRecord) -> None:
        """寫入一筆樣本並關閉連線；重複時間戳不覆蓋既有紀錄。"""
        connection = self._connect()
        try:
            insert_metric_sample(connection, sample)
        finally:
            connection.close()

    def read(
        self, start_ms: int, end_ms: int, *, read_only: bool = False
    ) -> list[history.MetricSampleRecord]:
        """讀取時間窗內樣本，並將底層不可用錯誤轉為應用層例外。

        Args:
            start_ms: 包含在範圍內的起始 Unix 毫秒時間戳。
            end_ms: 包含在範圍內的結束 Unix 毫秒時間戳。
            read_only: True 時不建立或遷移資料庫。

        Returns:
            依時間遞增的樣本；連線在回傳前關閉。

        Raises:
            exceptions.RepositoryUnavailableError: 開啟、版本檢查或查詢失敗。
        """
        try:
            connection = self._connect(read_only)
            try:
                return read_metric_samples(connection, start_ms, end_ms)
            finally:
                connection.close()
        except (
            sqlite3.Error,
            OSError,
            migration_runner.UnsupportedSchemaVersionError,
        ) as exc:
            raise exceptions.RepositoryUnavailableError(
                "Historical metrics database unavailable"
            ) from exc

    def latest(self) -> dict[str, Any] | None:
        """回傳最新樣本字典或 None；唯讀開啟，完成後關閉連線。"""
        connection = self._connect(read_only=True)
        try:
            row = connection.execute(
                "SELECT * FROM metric_samples ORDER BY timestamp_ms DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            connection.close()

    def delete_before(self, cutoff_ms: int) -> int:
        """回傳刪除筆數；刪除嚴格早於 cutoff_ms 的樣本並關閉連線。"""
        connection = self._connect()
        try:
            return delete_metric_samples_before(connection, cutoff_ms)
        finally:
            connection.close()
