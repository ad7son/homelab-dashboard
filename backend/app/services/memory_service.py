import psutil

from app.schemas.memory import MemoryInfo, SwapInfo


def get_memory_info() -> MemoryInfo:
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
