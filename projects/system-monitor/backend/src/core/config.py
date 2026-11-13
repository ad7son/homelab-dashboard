"""集中設定與既有預設值；不建立資料庫或啟動採集器。"""
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ENV_METRICS_DB_PATH = "A7LAS_METRICS_DB_PATH"
COLLECTION_INTERVAL_SECONDS = 30
RAW_RETENTION_MS = 7 * 24 * 60 * 60 * 1000
MAINTENANCE_INTERVAL_SECONDS = 60 * 60

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

@dataclass(frozen=True)
class Settings:
    database_path: Path
    project_id: str
    project_name: str
    collection_interval_seconds: float = COLLECTION_INTERVAL_SECONDS
    retention_ms: int = RAW_RETENTION_MS
    maintenance_interval_seconds: float = MAINTENANCE_INTERVAL_SECONDS
    history_stale_after_ms: int = 90_000
    report_cache_seconds: float = 3
    gpu_cache_seconds: float = 3
    gpu_timeout_seconds: float = 2
    disk_sample_interval_seconds: float = 1
    sqlite_busy_timeout_ms: int = 5000

    @classmethod
    def from_environment(cls, database_path=None):
        project = Path(__file__).resolve().parents[3] / "project.json"
        manifest = json.loads(project.read_text(encoding="utf-8"))
        return cls(resolve_metrics_db_path(database_path), manifest["id"], manifest["name"])
