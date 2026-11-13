"""psutil 記憶體適配器，保留系統容量與 Swap 定義。"""
import psutil
from ...domain.metrics import MemoryInfo, SwapInfo

class MemoryReader:
    def read(self) -> MemoryInfo:
        """取得實體記憶體與 Swap，保留 psutil 原本的容量與百分比定義。"""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return MemoryInfo(
            total=vm.total,
            used=vm.used,
            available=vm.available,
            usage_percent=vm.percent,
            swap=SwapInfo(
                total=swap.total,
                used=swap.used,
                usage_percent=swap.percent,
            ),
        )
