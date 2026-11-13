"""應用服務需要的外部能力；實作由 bootstrap 注入，介面不依賴 FastAPI 或 SQLite。"""

from __future__ import annotations

from typing import Any, Protocol

from ..domain import history
from ..domain import metrics


class MetricsSource(Protocol):
    """應用服務讀取五種主機資源快照的介面。"""

    def cpu(self) -> metrics.CpuInfo:
        """回傳 CPU 快照；選用來源不可讀時保留缺值語意。"""
        ...

    def memory(self) -> metrics.MemoryInfo:
        """回傳記憶體與 Swap 快照；選用來源不可讀時保留缺值語意。"""
        ...

    def network(self) -> metrics.NetworkInfo:
        """回傳主要介面與流量快照；選用來源不可讀時保留缺值語意。"""
        ...

    def gpu(self) -> metrics.GpuInfo:
        """回傳 GPU 平台狀態與讀值；選用來源不可讀時保留缺值語意。"""
        ...

    def disk_io(self) -> metrics.DiskIoInfo:
        """回傳磁碟速率與取樣狀態；選用來源不可讀時保留缺值語意。"""
        ...


class MetricsRepository(Protocol):
    """歷史樣本初始化、寫入、查詢與保留政策的儲存介面。"""

    def initialize(self) -> None:
        """建立或升級儲存結構；成功後不保留已開啟連線。"""
        ...

    def insert(self, sample: history.MetricSampleRecord) -> None:
        """寫入樣本，不覆蓋相同時間戳的既有紀錄。

        Args:
            sample: 需持久化的不可變樣本。

        Raises:
            exceptions.DuplicateMetricSampleError: 時間戳已存在。
        """
        ...

    def read(
        self, start_ms: int, end_ms: int, *, read_only: bool = False
    ) -> list[history.MetricSampleRecord]:
        """讀取包含起訖邊界的樣本並依時間遞增排列。

        Args:
            start_ms: 起始 Unix 毫秒時間戳。
            end_ms: 結束 Unix 毫秒時間戳。
            read_only: True 時禁止建檔與遷移。

        Returns:
            範圍內樣本；無資料時回傳空清單。

        Raises:
            exceptions.RepositoryUnavailableError: 無法開啟或查詢儲存來源。
        """
        ...

    def latest(self) -> dict[str, Any] | None:
        """回傳最新樣本的完整欄位字典；無樣本時為 None，不建立資料庫。"""
        ...

    def delete_before(self, cutoff_ms: int) -> int:
        """刪除嚴格早於截止時間的樣本，回傳刪除筆數。

        Args:
            cutoff_ms: Unix 毫秒時間戳；剛好等於此時間的樣本保留。
        """
        ...


class CollectorStatusStore(Protocol):
    """採集器最近成功或失敗紀錄的旁檔介面。"""

    def read(self) -> tuple[dict[str, Any] | None, str | None]:
        """回傳 (診斷字典或 None, 讀取錯誤或 None)；缺檔不是讀取錯誤。"""
        ...

    def record(
        self,
        *,
        sample: history.MetricSampleRecord | None = None,
        error: Exception | None = None,
    ) -> None:
        """記錄一次成功或失敗的採集嘗試。

        Args:
            sample: 成功寫入的樣本；失敗時不傳入。
            error: 原始錯誤；成功時為 None。
        """
        ...
