"""應用層錯誤契約，供 HTTP 與背景入口以各自方式處理。"""
class RepositoryUnavailableError(RuntimeError):
    """歷史儲存來源無法完成查詢。"""

class HistoricalMetricsUnavailableError(RuntimeError):
    """API 可安全回報的歷史查詢失敗。"""

class DuplicateMetricSampleError(RuntimeError):
    """相同時間戳已存在，採集器不可覆蓋既有樣本。"""
