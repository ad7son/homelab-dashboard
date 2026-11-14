"""讀取實體記憶體與 Swap；Swap 失敗不丟棄實體記憶體資料。"""

from __future__ import annotations

import logging

import psutil

_logger = logging.getLogger(__name__)


class MemoryReader:
    """無跨輪取樣狀態的記憶體讀取器。"""

    def read_info(self) -> dict[str, int]:
        """回傳啟動時的實體記憶體容量，單位 bytes。"""
        return {"memory_total_bytes": psutil.virtual_memory().total}

    def read(self) -> dict[str, int | float]:
        """回傳 psutil 定義的容量與使用率；缺少的 Swap 欄位交由組合器補 None。"""
        memory = psutil.virtual_memory()
        values = {
            "memory_used_bytes": memory.used,
            "memory_available_bytes": memory.available,
            "memory_usage_percent": memory.percent,
        }
        try:
            swap = psutil.swap_memory()
        except (OSError, NotImplementedError, AttributeError):
            _logger.warning("Swap information unavailable", exc_info=True)
        else:
            values.update(
                swap_total_bytes=swap.total,
                swap_used_bytes=swap.used,
                swap_usage_percent=swap.percent,
            )
        return values
