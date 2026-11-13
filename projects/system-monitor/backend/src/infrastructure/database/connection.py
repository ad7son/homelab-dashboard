"""短生命週期 SQLite 連線；唯讀不建檔、不遷移，寫入使用 WAL 與既有重試。"""
import sqlite3
import time
from pathlib import Path
from typing import Optional
from ...core.config import resolve_metrics_db_path
from .migration_runner import CURRENT_SCHEMA_VERSION, UnsupportedSchemaVersionError, initialize_metrics_database, _get_user_version

BUSY_TIMEOUT_MS = 5000

def _configure_connection(connection: sqlite3.Connection, busy_timeout_ms: int = BUSY_TIMEOUT_MS) -> None:
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
            if code not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or remaining <= 0:
                raise
            time.sleep(min(0.01, remaining))

def connect_metrics_database(
    path: Optional[str | Path] = None,
    *,
    read_only: bool = False,
    busy_timeout_ms: int = BUSY_TIMEOUT_MS,
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

    connection = sqlite3.connect(str(db_path), timeout=busy_timeout_ms / 1000.0)
    try:
        _configure_connection(connection, busy_timeout_ms)
        initialize_metrics_database(connection)
    except Exception:
        connection.close()
        raise

    return connection

def get_schema_version(connection: sqlite3.Connection) -> int:
    """讀取 SQLite user_version，供版本檢查與測試使用。"""
    return _get_user_version(connection)


def get_journal_mode(connection: sqlite3.Connection) -> str:
    """讀取 journal mode，供確認 WAL 設定使用。"""
    row = connection.execute("PRAGMA journal_mode").fetchone()
    return str(row[0]).lower()
