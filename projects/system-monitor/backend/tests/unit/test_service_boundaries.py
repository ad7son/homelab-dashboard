"""應用服務只使用介面替身，不需要 SQLite、psutil 或 GPU 驅動。"""

import types

import pytest

import monitor_backend

models = monitor_backend.module("domain.metrics")
domain_history = monitor_backend.module("domain.history")
services_history = monitor_backend.module("services.history")
services_collection = monitor_backend.module("services.collection")
errors = monitor_backend.module("services.exceptions")


def source():
    """建立固定零負載來源，驗證有效零值及可選讀值不被改寫。"""
    return types.SimpleNamespace(
        cpu=lambda: models.CpuInfo(0, 4, 8, None, None, None),
        memory=lambda: models.MemoryInfo(
            100, 50, 50, 50, models.SwapInfo(0, 0, 0)
        ),
        network=lambda: models.NetworkInfo("eth0", None, 0, 0),
        gpu=lambda: models.GpuInfo(status="unsupported"),
        disk_io=lambda: models.DiskIoInfo(status="warming_up"),
    )


class Repository:
    """保留樣本及呼叫順序的記憶體儲存替身。

    Attributes:
        samples: 已寫入的不可變樣本，測試可直接檢視結果。
        calls: 初始化與查詢參數的有序紀錄。
    """

    def __init__(self):
        """建立獨立樣本與呼叫紀錄，避免不同測試互相影響。"""
        self.samples = []
        self.calls = []

    def initialize(self):
        """記錄初始化呼叫，不建立資料庫。"""
        self.calls.append("initialize")

    def insert(self, sample):
        """保留傳入樣本本身，供測試確認未被重新造值。"""
        self.samples.append(sample)

    def read(self, start, end, *, read_only=False):
        """回傳包含起訖邊界的樣本，並保留唯讀參數供驗證。"""
        self.calls.append((start, end, read_only))
        return [
            sample
            for sample in self.samples
            if start <= sample.timestamp_ms <= end
        ]

    def delete_before(self, cutoff):
        """回傳刪除筆數，保留等於 cutoff 的樣本。"""
        before = len(self.samples)
        self.samples = [
            sample for sample in self.samples if sample.timestamp_ms >= cutoff
        ]
        return before - len(self.samples)


class Status:
    """依呼叫順序保留診斷結果的替身。

    Attributes:
        results: 含 sample 或 error 的每次呼叫參數。
    """

    def __init__(self):
        """建立本測試獨立使用的結果清單。"""
        self.results = []

    def record(self, **result):
        """保留一次診斷呼叫的完整具名參數。"""
        self.results.append(result)


def test_collection_preserves_zeroes_and_optional_values_without_sql():
    repository, status = Repository(), Status()
    service = services_collection.CollectionService(
        source(), repository, status, clock=lambda: 10
    )
    sample = service.collect_once()
    assert sample.timestamp_ms == 10_000
    assert sample.cpu_usage_percent == 0
    assert sample.network_download_bytes_per_second == 0
    assert sample.gpu_usage_percent is None
    assert sample.disk_read_bytes_per_second is None
    assert repository.samples == [sample]
    assert status.results == [{"sample": sample}]


def test_failed_source_is_recorded_and_later_collection_can_recover():
    repository, status, readers = Repository(), Status(), source()

    def fail():
        raise OSError("read denied")

    readers.cpu = fail
    service = services_collection.CollectionService(
        readers, repository, status, clock=lambda: 10
    )
    with pytest.raises(OSError, match="read denied"):
        service.collect_once()
    assert repository.samples == []
    assert str(status.results[-1]["error"]) == "read denied"
    readers.cpu = source().cpu
    service.collect_once()
    assert len(repository.samples) == 1
    assert "sample" in status.results[-1]


def test_history_query_passes_window_and_read_only_policy_to_repository():
    repository = Repository()
    result = services_history.HistoryService(
        repository, clock=lambda: 1000
    ).get_historical_metrics(domain_history.HistoryRange.M15, read_only=True)
    assert repository.calls == [(100_000, 1_000_000, True)]
    assert result.samples == []


def test_repository_failure_becomes_application_error_with_original_cause():
    class Broken(Repository):
        """模擬儲存不可用，保留底層錯誤以驗證例外鏈。"""

        def read(self, *args, **kwargs):
            """每次讀取均回報 RepositoryUnavailableError，不查詢記憶體樣本。"""
            raise errors.RepositoryUnavailableError("private storage detail")

    with pytest.raises(errors.HistoricalMetricsUnavailableError) as raised:
        services_history.HistoryService(Broken()).get_historical_metrics(
            domain_history.HistoryRange.H1
        )
    assert str(raised.value) == "Historical metrics database unavailable"
    assert str(raised.value.__cause__) == "private storage detail"
