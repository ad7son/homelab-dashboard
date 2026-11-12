"""集中 SQLite 路徑、連線、交易、版本遷移與樣本讀寫。

一般連線維持自動建表與遷移；健康探測使用唯讀連線，不建立空資料庫。
保留既有 schema v2、WAL 與鎖定重試行為，重構不更動磁碟上的資料。
"""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .models import MetricSampleRecord

CURRENT_SCHEMA_VERSION = 2
ENV_METRICS_DB_PATH = "A7LAS_METRICS_DB_PATH"
BUSY_TIMEOUT_MS = 5000

_CREATE_METRIC_SAMPLES_SQL = """
CREATE TABLE IF NOT EXISTS metric_samples (
    timestamp_ms INTEGER PRIMARY KEY,
    cpu_usage_percent REAL NOT NULL,
    cpu_temperature_celsius REAL,
    memory_usage_percent REAL NOT NULL,
    network_download_bytes_per_second REAL,
    network_upload_bytes_per_second REAL,
    gpu_usage_percent REAL,
    disk_read_bytes_per_second REAL,
    disk_write_bytes_per_second REAL
)
"""

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


class UnsupportedSchemaVersionError(RuntimeError):
    """資料庫版本不受目前程式支援時回報。"""


class DuplicateMetricSampleError(RuntimeError):
    """樣本時間戳已存在時回報，避免靜默覆蓋歷史資料。"""


def default_metrics_db_path() -> Path:
    """尋找含 app/modules/loader.py 的平台 backend，沿用既有 metrics.db。

    不使用固定父目錄層數，避免模組搬移或工作目錄不同時誤建第二份資料庫。"""
    for parent in Path(__file__).resolve().parents:
        platform_backend = parent / "backend"
        if (platform_backend / "app" / "modules" / "loader.py").is_file():
            return platform_backend / "data" / "metrics.db"
    raise RuntimeError(
        "Unable to locate the repository backend directory for metrics.db"
    )


def resolve_metrics_db_path(
    override: Optional[str | Path] = None,
) -> Path:
    """解析資料庫路徑，優先順序為明確參數、環境變數、平台預設位置。"""
    if override is not None:
        return Path(override).expanduser().resolve()

    env_path = os.environ.get(ENV_METRICS_DB_PATH)
    if env_path:
        return Path(env_path).expanduser().resolve()

    return default_metrics_db_path().resolve()


def _get_user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row is not None else 0


def _set_user_version(connection: sqlite3.Connection, version: int) -> None:
    # PRAGMA user_version 不支援參數綁定，先轉為整數再組合。
    connection.execute(f"PRAGMA user_version = {int(version)}")


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    # 切換 journal mode 時，SQLite 可能不遵守 busy_timeout 而立即回報 BUSY。
    # 只重試鎖定錯誤，以既有連線逾時作為重試期限，其他錯誤照常回報。
    deadline = time.monotonic() + BUSY_TIMEOUT_MS / 1000
    while True:
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            break
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", 0) & 0xFF
            remaining = deadline - time.monotonic()
            if code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or remaining <= 0:
                raise
            time.sleep(min(0.01, remaining))


def initialize_metrics_database(connection: sqlite3.Connection) -> None:
    """建立 v2 或原地升級 v1；新增欄位允許 NULL，既有歷史資料不補零。

    取得寫入鎖後再次確認版本，避免 API 與 collector 同時升級時重複加欄位。
    欄位變更與版本更新放在同一交易內，任一步失敗都回滾。
    """
    if _get_user_version(connection) == CURRENT_SCHEMA_VERSION:
        return
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        version = _get_user_version(connection)
        if version == CURRENT_SCHEMA_VERSION:
            return
        if version not in (0, 1):
            raise UnsupportedSchemaVersionError(
                f"Unsupported metrics database schema version {version}; "
                f"expected 0, 1 or {CURRENT_SCHEMA_VERSION}."
            )
        if version == 0:
            connection.execute(_CREATE_METRIC_SAMPLES_SQL)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_samples)")}
        for column in ("gpu_usage_percent", "disk_read_bytes_per_second", "disk_write_bytes_per_second"):
            if column not in columns:
                connection.execute(f"ALTER TABLE metric_samples ADD COLUMN {column} REAL")
        _set_user_version(connection, CURRENT_SCHEMA_VERSION)


def connect_metrics_database(
    path: Optional[str | Path] = None,
    *,
    read_only: bool = False,
) -> sqlite3.Connection:
    """開啟短生命週期連線；唯讀模式只驗證版本，不寫入或執行遷移。"""
    db_path = resolve_metrics_db_path(path)
    if read_only:
        connection = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True, timeout=1)
        connection.row_factory = sqlite3.Row
        try:
            if _get_user_version(connection) != CURRENT_SCHEMA_VERSION:
                raise UnsupportedSchemaVersionError("Historical schema requires migration")
        except Exception:
            connection.close()
            raise
        return connection
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000.0)
    try:
        _configure_connection(connection)
        initialize_metrics_database(connection)
    except Exception:
        connection.close()
        raise

    return connection


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


def get_schema_version(connection: sqlite3.Connection) -> int:
    """讀取 SQLite user_version，供版本檢查與測試使用。"""
    return _get_user_version(connection)


def get_journal_mode(connection: sqlite3.Connection) -> str:
    """讀取 journal mode，供確認 WAL 設定使用。"""
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower()


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



def latest_metric_sample(path: Optional[str | Path] = None) -> dict | None:
    """唯讀取得最新原始資料列，供健康檢查判斷新鮮度；保留 SQLite 原值。"""
    connection = connect_metrics_database(path, read_only=True)
    try:
        row = connection.execute("SELECT * FROM metric_samples ORDER BY timestamp_ms DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        connection.close()
