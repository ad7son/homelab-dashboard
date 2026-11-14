"""共用紀錄儲存與保留設定，不在匯入時建立資料庫。"""

from __future__ import annotations

import os
import pathlib

EVENT_RETENTION_DAYS: int | None = 7
CLEANUP_INTERVAL_SECONDS = 86_400
SQLITE_TIMEOUT_SECONDS = 0.25


def database_path() -> pathlib.Path:
    """解析共用資料庫路徑；與個別專案的監測資料分開。"""
    override = os.environ.get("A7LAS_OBSERVABILITY_DB_PATH")
    path = (
        pathlib.Path(override)
        if override
        else (
            pathlib.Path(__file__).resolve().parents[3]
            / "data"
            / "platform"
            / "observability.db"
        )
    )
    return path.expanduser().resolve()
