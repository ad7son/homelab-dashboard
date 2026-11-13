"""歷史查詢用例：決定時間區間與解析度；Repository 負責實際儲存存取。"""
import time
from ..domain.history import HistoricalMetrics, HistoryRange
from ..domain.aggregation import BUCKET_5_MIN_MS, BUCKET_30_MIN_MS, aggregate_metric_samples
from .ports import MetricsRepository
from .exceptions import RepositoryUnavailableError, HistoricalMetricsUnavailableError

RANGE_DURATION_MS = {
    HistoryRange.M15: 15 * 60 * 1000,
    HistoryRange.H1: 60 * 60 * 1000,
    HistoryRange.H24: 24 * 60 * 60 * 1000,
    HistoryRange.D7: 7 * 24 * 60 * 60 * 1000,
}
RANGE_AGGREGATION_BUCKET_MS = {
    HistoryRange.M15: None, HistoryRange.H1: None,
    HistoryRange.H24: BUCKET_5_MIN_MS, HistoryRange.D7: BUCKET_30_MIN_MS,
}


class HistoryService:
    def __init__(self, repository: MetricsRepository, clock=None):
        self.repository = repository
        self.clock = clock or (lambda: time.time())

    def get_historical_metrics(self, history_range: HistoryRange, *, now_ms=None, read_only=False) -> HistoricalMetrics:
        # 以現在時間為準，不追隨最後樣本，才能看見停止採集的時間缺口。
        end = int(self.clock() * 1000) if now_ms is None else int(now_ms)
        start = end - RANGE_DURATION_MS[history_range]
        try:
            records = self.repository.read(start, end, read_only=read_only)
        except RepositoryUnavailableError as exc:
            raise HistoricalMetricsUnavailableError("Historical metrics database unavailable") from exc
        bucket = RANGE_AGGREGATION_BUCKET_MS[history_range]
        if bucket is not None:
            records = aggregate_metric_samples(records, bucket)
        return HistoricalMetrics(history_range, start, end, records)
