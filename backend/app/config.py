"""平台設定；各專案業務設定由各專案自行管理。"""

from __future__ import annotations

import os
import pathlib

A7LAS_VERSION = "0.5.0-dev"
CORS_ALLOW_ORIGINS = ("http://localhost:5173",)
CORS_ALLOW_METHODS = ("GET",)

EVENT_RETENTION_DAYS: int | None = 7
EVENT_CLEANUP_INTERVAL_SECONDS = 86_400
EVENT_SQLITE_TIMEOUT_SECONDS = 0.25


def event_database_path() -> pathlib.Path:
    """解析共用資料庫路徑；與個別專案的監測資料分開。"""
    override = os.environ.get("A7LAS_OBSERVABILITY_DB_PATH")
    path = (
        pathlib.Path(override)
        if override
        else (
            pathlib.Path(__file__).resolve().parents[2]
            / "data"
            / "platform"
            / "observability.db"
        )
    )
    return path.expanduser().resolve()
