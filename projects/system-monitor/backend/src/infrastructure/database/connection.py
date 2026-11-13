"""短生命週期 SQLite 連線；唯讀不建檔、不遷移，寫入使用 WAL 與既有重試。"""

from __future__ import annotations

import pathlib
import sqlite3
import time

from ...core import config
from . import migration_runner

BUSY_TIMEOUT_MS = 5000


def _configure_connection(
    connection: sqlite3.Connection, busy_timeout_ms: int = BUSY_TIMEOUT_MS
) -> None:
    """設定 Row、busy timeout 與 WAL；只重試 BUSY／LOCKED 錯誤。

    Args:
        connection: 呼叫端持有且負責關閉的連線。
        busy_timeout_ms: 鎖定等待與 WAL 重試上限，單位毫秒。

    Raises:
        sqlite3.OperationalError: 非鎖定錯誤，或鎖定超過期限。
    """
    connection.row_factory = sqlite3.Row
    connection.execute(f"PRAGMA busy_timeout = {busy_timeout_ms}")
    # 切換 journal mode 時，SQLite 可能不遵守 busy_timeout 而立即回報 BUSY。
    # 只重試鎖定錯誤，以既有連線逾時作為重試期限，其他錯誤照常回報。
    deadline = time.monotonic() + busy_timeout_ms / 1000
    while True:
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            break
        except sqlite3.OperationalError as exc:
            code = getattr(exc, "sqlite_errorcode", 0) & 0xFF
            remaining = deadline - time.monotonic()
            if (
                code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                or remaining <= 0
            ):
                raise
            time.sleep(min(0.01, remaining))


def connect_metrics_database(
    path: str | pathlib.Path | None = None,
    *,
    read_only: bool = False,
    busy_timeout_ms: int = BUSY_TIMEOUT_MS,
) -> sqlite3.Connection:
    """開啟由呼叫端負責關閉的短生命週期 SQLite 連線。

    Args:
        path: 明確資料庫路徑；None 時採用環境變數或平台預設。
        read_only: True 時只驗證版本，不建檔、不設定 WAL、不執行遷移。
        busy_timeout_ms: 寫入連線等待鎖定的最長毫秒數。

    Returns:
        使用 sqlite3.Row 的開啟連線；離開 connection 的交易區塊不等於關閉連線。

    Raises:
        OSError: 無法建立資料目錄。
        sqlite3.Error: 無法開啟、設定或遷移資料庫。
        migration_runner.UnsupportedSchemaVersionError: 版本不支援或唯讀時需要遷移。
        RuntimeError: 無法定位預設資料庫目錄。
    """
    db_path = config.resolve_metrics_db_path(path)
    if read_only:
        connection = sqlite3.connect(
            db_path.as_uri() + "?mode=ro", uri=True, timeout=1
        )
        connection.row_factory = sqlite3.Row
        try:
            if (
                migration_runner.get_user_version(connection)
                != migration_runner.CURRENT_SCHEMA_VERSION
            ):
                raise migration_runner.UnsupportedSchemaVersionError(
                    "Historical schema requires migration"
                )
        except Exception:
            connection.close()
            raise
        return connection
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path), timeout=busy_timeout_ms / 1000.0)
    try:
        _configure_connection(connection, busy_timeout_ms)
        migration_runner.initialize_metrics_database(connection)
    except Exception:
        connection.close()
        raise

    return connection


def get_schema_version(connection: sqlite3.Connection) -> int:
    """讀取 SQLite user_version，供版本檢查與測試使用。"""
    return migration_runner.get_user_version(connection)


def get_journal_mode(connection: sqlite3.Connection) -> str:
    """讀取 journal mode，供確認 WAL 設定使用。"""
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower()
