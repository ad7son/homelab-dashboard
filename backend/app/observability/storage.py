"""跨程序共用 SQLite 事件與狀態，SQL 僅存在本模組。"""

from __future__ import annotations

import contextlib
import json
import pathlib
import sqlite3
from collections.abc import Iterator, Sequence
from typing import Any

from app.observability import config
from app.observability import models


@contextlib.contextmanager
def _connect(
    path: pathlib.Path, *, read_only: bool = False
) -> Iterator[sqlite3.Connection]:
    """每次操作開關連線；查詢不建檔，寫入成功提交、失敗回滾。"""
    target = path.as_uri() + "?mode=ro" if read_only else str(path)
    with contextlib.closing(
        sqlite3.connect(
            target, uri=read_only, timeout=config.SQLITE_TIMEOUT_SECONDS
        )
    ) as database:
        database.row_factory = sqlite3.Row
        with database:
            yield database


class EventStore:
    """持久化共用事件，不依賴 API 或專案程式。

    Attributes:
        path: 共用 SQLite 的絕對路徑。
    """

    def __init__(self, path: pathlib.Path | None = None) -> None:
        """只解析路徑，不建立資料庫。"""
        self.path = (path or config.database_path()).resolve()

    def initialize(self) -> None:
        """建立 WAL 與表結構，允許多程序重複呼叫，不清理資料。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        schema = (
            pathlib.Path(__file__)
            .with_name("schema.sql")
            .read_text(encoding="utf-8")
        )
        with _connect(self.path) as database:
            database.execute("PRAGMA journal_mode=WAL")
            database.executescript(schema)

    def register(
        self, projects: Sequence[models.ProjectDefinition], now_ms: int
    ) -> None:
        """登記功能首次出現時間；重啟不重設成功紀錄或時效基準。"""
        self.initialize()
        rows = [
            (project.id, feature.id, now_ms)
            for project in projects
            for feature in project.features
        ]
        with _connect(self.path) as database:
            database.executemany(
                "INSERT OR IGNORE INTO feature_state "
                "(project_id, feature_id, first_seen_at_ms) VALUES (?, ?, ?)",
                rows,
            )

    def append(self, event: models.Event) -> int:
        """在同一交易保存事件與健康狀態，避免狀態與證據錯置。

        一般 log 沒有 outcome，不改變功能狀態。較舊事件可以補成功時間，
        但不能覆蓋較新的執行結果。SQLite 錯誤向呼叫端傳遞。
        """
        payload = json.dumps(
            event.model_dump(mode="json"), ensure_ascii=False, allow_nan=False
        )
        self.initialize()
        with _connect(self.path) as database:
            cursor = database.execute(
                "INSERT INTO events (timestamp_ms, project_id, feature_id, "
                "level, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    event.timestamp_ms,
                    event.project_id,
                    event.feature_id,
                    event.level,
                    payload,
                ),
            )
            event_id = cursor.lastrowid
            if event.feature_id is not None and event.outcome is not None:
                database.execute(
                    "INSERT INTO feature_state "
                    "(project_id, feature_id, first_seen_at_ms, "
                    "last_event_at_ms, "
                    "last_event_id, last_success_at_ms, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(project_id, "
                    "feature_id) DO UPDATE SET "
                    "first_seen_at_ms = MIN(feature_state.first_seen_at_ms, "
                    "excluded.first_seen_at_ms), "
                    "last_event_at_ms = "
                    "MAX(COALESCE(feature_state.last_event_at_ms, 0), "
                    "excluded.last_event_at_ms), "
                    "last_event_id = CASE WHEN excluded.last_event_at_ms >= "
                    "COALESCE(feature_state.last_event_at_ms, 0) "
                    "THEN excluded.last_event_id ELSE "
                    "feature_state.last_event_id END, "
                    "payload_json = CASE WHEN excluded.last_event_at_ms >= "
                    "COALESCE(feature_state.last_event_at_ms, 0) "
                    "THEN excluded.payload_json ELSE "
                    "feature_state.payload_json END, "
                    "last_success_at_ms = CASE WHEN "
                    "excluded.last_success_at_ms IS NULL "
                    "THEN feature_state.last_success_at_ms ELSE "
                    "MAX(COALESCE(feature_state.last_success_at_ms, 0), "
                    "excluded.last_success_at_ms) END",
                    (
                        event.project_id,
                        event.feature_id,
                        event.timestamp_ms,
                        event.timestamp_ms,
                        event_id,
                        (
                            event.timestamp_ms
                            if event.outcome == "success"
                            else None
                        ),
                        payload,
                    ),
                )
        return event_id

    def snapshot(self) -> dict[tuple[str, str], dict[str, Any]]:
        """以同一 SELECT 讀取全部最新狀態；無資料庫時回傳空集合，不建檔。"""
        if not self.path.exists():
            return {}
        with _connect(self.path, read_only=True) as database:
            rows = database.execute("SELECT * FROM feature_state").fetchall()
        return {
            (row["project_id"], row["feature_id"]): dict(row) for row in rows
        }

    def recent(
        self,
        *,
        project_id: str | None = None,
        feature_id: str | None = None,
        level: str | None = None,
        before_id: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """依寫入識別碼遞減查詢，支援游標翻頁；不依訊息文字篩選。"""
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if not self.path.exists():
            return []
        filters, parameters = [], []
        for name, value in (
            ("project_id", project_id),
            ("feature_id", feature_id),
            ("level", level),
        ):
            if value is not None:
                filters.append(f"{name} = ?")
                parameters.append(value)
        if before_id is not None:
            filters.append("id < ?")
            parameters.append(before_id)
        where = " WHERE " + " AND ".join(filters) if filters else ""
        with _connect(self.path, read_only=True) as database:
            rows = database.execute(
                "SELECT id, payload_json FROM events"
                + where
                + " ORDER BY id DESC LIMIT ?",
                (*parameters, limit),
            ).fetchall()
        return [
            {"id": row["id"], **json.loads(row["payload_json"])} for row in rows
        ]

    def delete_before(self, cutoff_ms: int) -> int:
        """只清理過期事件，保留最新狀態與最近成功時間，不自動縮檔。"""
        with _connect(self.path) as database:
            cursor = database.execute(
                "DELETE FROM events WHERE timestamp_ms < ?", (cutoff_ms,)
            )
            return cursor.rowcount
