"""即時總覽用例：組合各項快照，不了解 psutil、GPU 指令或 HTTP。"""

from __future__ import annotations

from ..domain import metrics
from . import ports


class OverviewService:
    """組合五種主機採集結果的即時總覽服務。

    Attributes:
        source: 共用取樣基準及來源快取的主機採集介面。
    """

    def __init__(self, source: ports.MetricsSource) -> None:
        """建立使用指定來源的總覽服務。

        Args:
            source: 共用既有取樣基準的主機採集來源。
        """
        self.source = source

    def get_overview(self) -> metrics.Overview:
        """回傳依序採集的五項資源快照；不同資源並非原子同時取樣。

        來源未處理的錯誤會向外傳遞，由呼叫端決定呈現方式。
        """
        return metrics.Overview(
            cpu=self.source.cpu(),
            memory=self.source.memory(),
            network=self.source.network(),
            gpu=self.source.gpu(),
            disk_io=self.source.disk_io(),
        )
