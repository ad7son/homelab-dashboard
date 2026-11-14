"""集中兩張主機資料表的 SQL；不讀硬體、不安排採集或清理時間。"""

from __future__ import annotations

import pathlib
from typing import Any

from . import connection

INFO_COLUMNS = (
    "updated_at_ms",
    "cpu_physical_cores",
    "cpu_logical_cores",
    "memory_total_bytes",
    "gpu_name",
    "gpu_device_count",
    "network_interface",
    "network_ip_address",
)
METRIC_COLUMNS = (
    "timestamp_ms",
    "cpu_usage_percent",
    "cpu_frequency_mhz",
    "cpu_temperature_celsius",
    "cpu_load_1",
    "cpu_load_5",
    "cpu_load_15",
    "memory_used_bytes",
    "memory_available_bytes",
    "memory_usage_percent",
    "swap_total_bytes",
    "swap_used_bytes",
    "swap_usage_percent",
    "network_download_bytes_per_second",
    "network_upload_bytes_per_second",
    "gpu_status",
    "gpu_usage_percent",
    "disk_io_status",
    "disk_read_bytes_per_second",
    "disk_write_bytes_per_second",
)
HISTORY_COLUMNS = (
    "cpu_usage_percent",
    "cpu_temperature_celsius",
    "memory_usage_percent",
    "network_download_bytes_per_second",
    "network_upload_bytes_per_second",
    "gpu_usage_percent",
    "disk_read_bytes_per_second",
    "disk_write_bytes_per_second",
)


class HostRepository:
    """以每次操作各自的連線存取主機資料。

    Attributes:
        path: SQLite 檔案位置。
        timeout_seconds: 等待資料庫鎖的秒數。
    """

    def __init__(self, path: pathlib.Path, timeout_seconds: float = 5) -> None:
        """保留路徑及 timeout，不立即開啟資料庫。"""
        self.path = path
        self.timeout_seconds = timeout_seconds

    def update_info(self, info: dict[str, Any]) -> None:
        """更新唯一一筆基本資訊；僅在採集器啟動時呼叫。

        Args:
            info: 包含 INFO_COLUMNS 全部欄位的基本資訊。
        """
        columns = ", ".join(INFO_COLUMNS)
        placeholders = ", ".join("?" for _ in INFO_COLUMNS)
        updates = ", ".join(
            f"{name} = excluded.{name}" for name in INFO_COLUMNS
        )
        with connection.connect(
            self.path, timeout_seconds=self.timeout_seconds
        ) as database:
            database.execute(
                f"INSERT INTO host_info (id, {columns}) "
                f"VALUES (1, {placeholders}) "
                f"ON CONFLICT(id) DO UPDATE SET {updates}",
                tuple(info[name] for name in INFO_COLUMNS),
            )

    def insert(self, sample: dict[str, Any]) -> None:
        """寫入一筆指標；重複時間戳引發 sqlite3.IntegrityError，不覆蓋。"""
        columns = ", ".join(METRIC_COLUMNS)
        placeholders = ", ".join("?" for _ in METRIC_COLUMNS)
        with connection.connect(
            self.path, timeout_seconds=self.timeout_seconds
        ) as database:
            database.execute(
                f"INSERT INTO host_metrics ({columns}) VALUES ({placeholders})",
                tuple(sample[name] for name in METRIC_COLUMNS),
            )

    def get_latest(self) -> dict[str, Any] | None:
        """以同一 SELECT 取得基本資訊及最新指標；任一表無資料時為 None。

        唯讀操作不建立資料庫；SQLite 錯誤向呼叫端傳遞。
        基本資訊只有目前版本，不表示歷史樣本當時的硬體配置。
        """
        with connection.connect(
            self.path, read_only=True, timeout_seconds=self.timeout_seconds
        ) as database:
            row = database.execute(
                "SELECT info.*, metrics.* FROM host_info AS info "
                "CROSS JOIN host_metrics AS metrics WHERE info.id = 1 "
                "ORDER BY metrics.timestamp_ms DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row is not None else None

    def get_history(
        self, start_ms: int, end_ms: int, bucket_ms: int = 0
    ) -> list[dict[str, Any]]:
        """查詢包含起訖邊界的數值；可依 UTC 固定時間桶回傳平均值。

        Args:
            start_ms: 非負 Unix 毫秒起點。
            end_ms: 不小於起點的 Unix 毫秒終點。
            bucket_ms: 0 表示原始資料，正整數表示彙整桶的毫秒寬度。

        Returns:
            時間遞增的歷史指標。AVG 忽略 NULL，全缺值仍為 NULL；
            不補空桶。彙整 timestamp_ms 為桶起點，可能早於查詢起點。
        """
        if start_ms < 0 or end_ms < start_ms or bucket_ms < 0:
            raise ValueError("Invalid history window or bucket")
        if bucket_ms:
            fields = ", ".join(
                f"AVG({name}) AS {name}" for name in HISTORY_COLUMNS
            )
            sql = (
                "SELECT (timestamp_ms / ?) * ? AS timestamp_ms, "
                f"{fields} FROM host_metrics "
                "WHERE timestamp_ms BETWEEN ? AND ? "
                "GROUP BY (timestamp_ms / ?) ORDER BY timestamp_ms"
            )
            parameters = (bucket_ms, bucket_ms, start_ms, end_ms, bucket_ms)
        else:
            sql = (
                f"SELECT timestamp_ms, {', '.join(HISTORY_COLUMNS)} "
                "FROM host_metrics WHERE timestamp_ms BETWEEN ? AND ? "
                "ORDER BY timestamp_ms"
            )
            parameters = (start_ms, end_ms)
        # 動態 SQL 欄位只取自模組常數，使用者數值一律以參數傳入。
        with connection.connect(
            self.path, read_only=True, timeout_seconds=self.timeout_seconds
        ) as database:
            return [dict(row) for row in database.execute(sql, parameters)]

    def delete_before(self, cutoff_ms: int) -> int:
        """刪除嚴格早於 cutoff_ms 的指標，保留基本資訊，回傳刪除筆數。"""
        with connection.connect(
            self.path, timeout_seconds=self.timeout_seconds
        ) as database:
            cursor = database.execute(
                "DELETE FROM host_metrics WHERE timestamp_ms < ?", (cutoff_ms,)
            )
            return cursor.rowcount
