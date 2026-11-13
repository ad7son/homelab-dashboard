"""集中設定與既有預設值；不建立資料庫或啟動採集器。"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib

ENV_METRICS_DB_PATH = "A7LAS_METRICS_DB_PATH"
COLLECTION_INTERVAL_SECONDS = 30
RAW_RETENTION_MS = 7 * 24 * 60 * 60 * 1000
MAINTENANCE_INTERVAL_SECONDS = 60 * 60


def default_metrics_db_path() -> pathlib.Path:
    """回傳平台 backend/data/metrics.db 的預設絕對路徑。

    不依賴目前工作目錄，也不建立目錄或資料庫。

    Raises:
        RuntimeError: 沿來源檔案父目錄找不到平台 backend。
    """
    for parent in pathlib.Path(__file__).resolve().parents:
        platform_backend = parent / "backend"
        if (platform_backend / "app" / "modules" / "loader.py").is_file():
            return platform_backend / "data" / "metrics.db"
    raise RuntimeError(
        "Unable to locate the repository backend directory for metrics.db"
    )


def resolve_metrics_db_path(
    override: str | pathlib.Path | None = None,
) -> pathlib.Path:
    """解析資料庫路徑，優先使用明確參數，其次環境變數及平台預設。

    Args:
        override: 可含 ~ 的路徑；None 時讀取 A7LAS_METRICS_DB_PATH。

    Returns:
        展開使用者目錄並解析後的絕對路徑；不建立任何檔案。

    Raises:
        RuntimeError: 使用預設位置時找不到平台 backend。
    """
    if override is not None:
        return pathlib.Path(override).expanduser().resolve()

    env_path = os.environ.get(ENV_METRICS_DB_PATH)
    if env_path:
        return pathlib.Path(env_path).expanduser().resolve()

    return default_metrics_db_path().resolve()


@dataclasses.dataclass(frozen=True)
class Settings:
    """從環境與專案 manifest 解析出的不可變執行設定。

    Attributes:
        database_path: 歷史資料庫的絕對路徑。
        project_id: project.json 中的專案識別碼。
        project_name: project.json 中的專案顯示名稱。
        collection_interval_seconds: 採集完成後的等待秒數。
        retention_ms: 原始樣本保留期間，單位毫秒。
        maintenance_interval_seconds: 保留政策維護工作的間隔秒數。
        history_stale_after_ms: 最新樣本容許的最大資料年齡，單位毫秒。
        report_cache_seconds: 整份健康報告的快取有效秒數。
        gpu_cache_seconds: GPU 成功或失敗結果的快取有效秒數。
        gpu_timeout_seconds: 單次 nvidia-smi 指令的逾時秒數。
        disk_sample_interval_seconds: 磁碟計數器兩次實際取樣的最短間隔秒數。
        sqlite_busy_timeout_ms: SQLite 等待鎖定解除的最長時間，單位毫秒。
    """

    database_path: pathlib.Path
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
    def from_environment(
        cls, database_path: str | pathlib.Path | None = None
    ) -> Settings:
        """建立讀取環境與 manifest 後的設定，不修改環境變數。

        Args:
            database_path: 明確資料庫位置；None 時採用環境或平台預設。

        Returns:
            包含專案名稱、資料庫路徑及預設採集政策的新設定。

        Raises:
            OSError: 無法讀取 project.json。
            json.JSONDecodeError: manifest 不是有效 JSON。
            RuntimeError: 需要預設資料庫位置但找不到平台目錄。
        """
        project = pathlib.Path(__file__).resolve().parents[3] / "project.json"
        manifest = json.loads(project.read_text(encoding="utf-8"))
        return cls(
            resolve_metrics_db_path(database_path),
            manifest["id"],
            manifest["name"],
        )
