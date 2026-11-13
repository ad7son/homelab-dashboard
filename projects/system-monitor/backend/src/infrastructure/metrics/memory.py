"""psutil 記憶體適配器，保留系統容量與 Swap 定義。"""

from __future__ import annotations

import psutil

from ...domain import metrics


class MemoryReader:
    """沿用 psutil 容量定義的記憶體採集器。"""

    def read(self) -> metrics.MemoryInfo:
        """取得實體記憶體與 Swap，保留 psutil 原本的容量與百分比定義。

        Raises:
            OSError: 作業系統拒絕或無法提供記憶體／Swap 資訊。
        """
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return metrics.MemoryInfo(
            total=vm.total,
            used=vm.used,
            available=vm.available,
            usage_percent=vm.percent,
            swap=metrics.SwapInfo(
                total=swap.total,
                used=swap.used,
                usage_percent=swap.percent,
            ),
        )
