"""SQLite 初始化與短生命週期連線；唯讀查詢不建檔或建表。"""

from __future__ import annotations

import contextlib
import pathlib
import sqlite3
from collections.abc import Iterator


@contextlib.contextmanager
def connect(
    path: pathlib.Path,
    *,
    read_only: bool = False,
    timeout_seconds: float = 5.0,
) -> Iterator[sqlite3.Connection]:
    """提供操作所需連線，成功提交、失敗回滾，最後一律關閉。

    Args:
        path: 資料庫路徑；讀寫模式的父目錄需已存在。
        read_only: True 時使用 SQLite mode=ro，不建立缺少的資料庫。
        timeout_seconds: 等待鎖定的最長秒數。

    Yields:
        使用具名欄位 Row 的連線，由此情境管理器負責關閉。

    Raises:
        sqlite3.Error: 開啟、操作或提交失敗。
    """
    target = path.resolve().as_uri() + "?mode=ro" if read_only else str(path)
    database = sqlite3.connect(target, uri=read_only, timeout=timeout_seconds)
    database.row_factory = sqlite3.Row
    try:
        with database:
            yield database
    finally:
        database.close()


def initialize(path: pathlib.Path, timeout_seconds: float = 5.0) -> None:
    """建立父目錄、新表與 WAL；只由採集器啟動流程呼叫。

    不遷移舊表、不清理資料；重複初始化不刪除既有紀錄。

    Raises:
        OSError: 無法建立目錄或讀取 schema.sql。
        sqlite3.Error: 初始化資料庫失敗。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = (
        pathlib.Path(__file__)
        .with_name("schema.sql")
        .read_text(encoding="utf-8")
    )
    with connect(path, timeout_seconds=timeout_seconds) as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.executescript(schema)
