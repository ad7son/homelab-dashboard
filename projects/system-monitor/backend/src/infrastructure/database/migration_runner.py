"""SQLite 版本遷移：取得寫入鎖後再讀版本，任一步失敗整筆交易回滾。"""

from __future__ import annotations

import pathlib
import sqlite3

CURRENT_SCHEMA_VERSION = 2


class UnsupportedSchemaVersionError(RuntimeError):
    """資料庫版本不相容，須保留原資料並中止操作。"""


def get_user_version(connection: sqlite3.Connection) -> int:
    """回傳連線的 SQLite user_version，不修改資料庫。"""
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(connection: sqlite3.Connection, version: int) -> None:
    """設定交易中的 user_version；提交或回滾由呼叫端管理。"""
    connection.execute(f"PRAGMA user_version = {int(version)}")


def _statements(name: str) -> list[str]:
    """讀取內建遷移檔，移除整行 SQL 註解並以分號拆成陳述式。

    Args:
        name: migrations 目錄內受版本控制的檔名，不接受使用者輸入。

    Returns:
        非空 SQL 陳述式清單；不支援字串內含分號、觸發器等一般 SQL 語法解析。
    """
    script = (pathlib.Path(__file__).with_name("migrations") / name).read_text(
        encoding="utf-8"
    )
    script = "\n".join(
        line
        for line in script.splitlines()
        if not line.lstrip().startswith("--")
    )
    return [
        statement.strip()
        for statement in script.split(";")
        if statement.strip()
    ]


def initialize_metrics_database(connection: sqlite3.Connection) -> None:
    """在單一寫入交易內將空庫或 v1 升級至目前版本。

    取得 BEGIN IMMEDIATE 鎖後重新讀版本，避免並行啟動重複新增欄位。
    不使用 executescript，以免它隱含提交並破壞整組遷移的回滾能力。

    Args:
        connection: 已開啟且由呼叫端負責關閉的可寫連線。

    Raises:
        UnsupportedSchemaVersionError: 版本不是 0、1 或目前版本。
        sqlite3.Error: 遷移失敗，交易回滾，舊資料及版本保留。
        OSError: 無法讀取內建遷移檔。
    """
    if get_user_version(connection) == CURRENT_SCHEMA_VERSION:
        return
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        version = get_user_version(connection)
        if version == CURRENT_SCHEMA_VERSION:
            return
        if version not in (0, 1):
            raise UnsupportedSchemaVersionError(
                f"Unsupported metrics database schema version {version}; expected 0, 1 or {CURRENT_SCHEMA_VERSION}."
            )
        if version == 0:
            for statement in _statements("001_initial.sql"):
                connection.execute(statement)
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(metric_samples)")
        }
        for statement in _statements("002_gpu_disk_io.sql"):
            # 兼容已有欄位但尚未更新 user_version 的既有資料庫。
            if statement.split()[5] not in columns:
                connection.execute(statement)
        _set_user_version(connection, CURRENT_SCHEMA_VERSION)
