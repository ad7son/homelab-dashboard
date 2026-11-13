"""SQLite 版本遷移：取得寫入鎖後再讀版本，任一步失敗整筆交易回滾。"""
from pathlib import Path
import sqlite3

CURRENT_SCHEMA_VERSION = 2


class UnsupportedSchemaVersionError(RuntimeError):
    """資料庫版本不相容，須保留原資料並中止操作。"""


def _get_user_version(connection):
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _set_user_version(connection, version):
    connection.execute(f"PRAGMA user_version = {int(version)}")


def _statements(name):
    script = (Path(__file__).with_name("migrations") / name).read_text(encoding="utf-8")
    script = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("--"))
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def initialize_metrics_database(connection: sqlite3.Connection) -> None:
    if _get_user_version(connection) == CURRENT_SCHEMA_VERSION:
        return
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        version = _get_user_version(connection)
        if version == CURRENT_SCHEMA_VERSION:
            return
        if version not in (0, 1):
            raise UnsupportedSchemaVersionError(
                f"Unsupported metrics database schema version {version}; expected 0, 1 or {CURRENT_SCHEMA_VERSION}."
            )
        if version == 0:
            for statement in _statements("001_initial.sql"):
                connection.execute(statement)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_samples)")}
        for statement in _statements("002_gpu_disk_io.sql"):
            # 兼容已有欄位但尚未更新 user_version 的既有資料庫。
            if statement.split()[5] not in columns:
                connection.execute(statement)
        _set_user_version(connection, CURRENT_SCHEMA_VERSION)
