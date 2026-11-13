"""歷史查詢用例：決定時間區間與解析度；Repository 負責實際儲存存取。"""

from __future__ import annotations

from collections.abc import Callable
import time
import types

from ..domain import aggregation
from ..domain import history
from . import exceptions
from . import ports

RANGE_DURATION_MS = types.MappingProxyType(
    {
        history.HistoryRange.M15: 15 * 60 * 1000,
        history.HistoryRange.H1: 60 * 60 * 1000,
        history.HistoryRange.H24: 24 * 60 * 60 * 1000,
        history.HistoryRange.D7: 7 * 24 * 60 * 60 * 1000,
    }
)
RANGE_AGGREGATION_BUCKET_MS = types.MappingProxyType(
    {
        history.HistoryRange.M15: None,
        history.HistoryRange.H1: None,
        history.HistoryRange.H24: aggregation.BUCKET_5_MIN_MS,
        history.HistoryRange.D7: aggregation.BUCKET_30_MIN_MS,
    }
)


class HistoryService:
    """決定歷史時間窗及降採樣解析度的查詢服務。

    Attributes:
        repository: 歷史樣本儲存介面。
        clock: 回傳 Unix 秒數的時鐘，可由測試替換。
    """

    def __init__(
        self,
        repository: ports.MetricsRepository,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """建立歷史查詢服務。

        Args:
            repository: 歷史樣本儲存介面。
            clock: 回傳 Unix 秒數的函式；None 時使用系統時間。
        """
        self.repository = repository
        self.clock = clock or (lambda: time.time())

    def get_historical_metrics(
        self,
        history_range: history.HistoryRange,
        *,
        now_ms: int | None = None,
        read_only: bool = False,
    ) -> history.HistoricalMetrics:
        """查詢固定時間窗，必要時降採樣；停止採集時保留可見缺口。

        Args:
            history_range: 15m／1h 使用原始樣本，24h／7d 分別使用 5／30 分鐘桶。
            now_ms: 查詢終點的 Unix 毫秒時間戳；None 時讀取注入時鐘。
            read_only: True 時不建立資料庫或執行版本遷移。

        Returns:
            包含起訖時間及樣本的結果；空資料仍是成功查詢。

        Raises:
            exceptions.HistoricalMetricsUnavailableError: 儲存來源無法完成查詢。
        """
        end = int(self.clock() * 1000) if now_ms is None else int(now_ms)
        start = end - RANGE_DURATION_MS[history_range]
        try:
            records = self.repository.read(start, end, read_only=read_only)
        except exceptions.RepositoryUnavailableError as exc:
            raise exceptions.HistoricalMetricsUnavailableError(
                "Historical metrics database unavailable"
            ) from exc
        bucket = RANGE_AGGREGATION_BUCKET_MS[history_range]
        if bucket is not None:
            records = aggregation.aggregate_metric_samples(records, bucket)
        return history.HistoricalMetrics(history_range, start, end, records)
