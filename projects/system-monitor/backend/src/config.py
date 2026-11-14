"""集中可直接修改的採集、保留政策與資料庫設定。"""

from __future__ import annotations

import dataclasses
import math
import os
import pathlib

COLLECTION_INTERVAL_SECONDS = 3.0
RETENTION_DAYS: int | None = None
CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60
SQLITE_TIMEOUT_SECONDS = 5.0
GPU_TIMEOUT_SECONDS = 2.0


def default_database_path() -> pathlib.Path:
    """回傳平台 backend/data/system-monitor.db，不建立檔案。

    使用新檔名，避免將開發階段的舊 schema 當成新資料庫。
    """
    return (
        pathlib.Path(__file__).resolve().parents[4]
        / "backend"
        / "data"
        / "system-monitor.db"
    )


@dataclasses.dataclass(frozen=True)
class Settings:
    """不可變的採集設定；時間間隔使用秒，保留期限使用天。

    Attributes:
        database_path: SQLite 絕對路徑。
        collection_interval_seconds: 相鄰排程起點的目標秒數。
        retention_days: 保留天數；None 表示永久保留。
        cleanup_interval_seconds: 清理間隔，首次清理也等待相同時間。
        sqlite_timeout_seconds: 連線等待資料庫鎖的秒數。
        gpu_timeout_seconds: GPU 子程序最長等待秒數。
    """

    database_path: pathlib.Path
    collection_interval_seconds: float = COLLECTION_INTERVAL_SECONDS
    retention_days: int | None = RETENTION_DAYS
    cleanup_interval_seconds: float = CLEANUP_INTERVAL_SECONDS
    sqlite_timeout_seconds: float = SQLITE_TIMEOUT_SECONDS
    gpu_timeout_seconds: float = GPU_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        """拒絕零、負數與非有限間隔，以及無效保留天數。"""
        for value in (
            self.collection_interval_seconds,
            self.cleanup_interval_seconds,
            self.sqlite_timeout_seconds,
            self.gpu_timeout_seconds,
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Time intervals must be finite and positive")
        if self.retention_days is not None and (
            not isinstance(self.retention_days, int)
            or isinstance(self.retention_days, bool)
            or self.retention_days <= 0
        ):
            raise ValueError(
                "retention_days must be a positive integer or None"
            )

    @classmethod
    def from_environment(cls) -> Settings:
        """讀取路徑覆寫；其他政策由本模組常數調整，重啟程序後生效。"""
        path = os.environ.get("A7LAS_METRICS_DB_PATH")
        return cls(
            database_path=(
                pathlib.Path(path) if path else default_database_path()
            )
            .expanduser()
            .resolve(),
            collection_interval_seconds=COLLECTION_INTERVAL_SECONDS,
            retention_days=RETENTION_DAYS,
            cleanup_interval_seconds=CLEANUP_INTERVAL_SECONDS,
            sqlite_timeout_seconds=SQLITE_TIMEOUT_SECONDS,
            gpu_timeout_seconds=GPU_TIMEOUT_SECONDS,
        )
