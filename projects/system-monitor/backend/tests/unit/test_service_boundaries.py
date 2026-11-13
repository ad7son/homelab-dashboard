"""應用服務只使用介面替身，不需要 SQLite、psutil 或 GPU 驅動。"""
from types import SimpleNamespace

import pytest
from monitor_backend import module

models = module('domain.metrics')
HistoryRange = module('domain.history').HistoryRange
HistoryService = module('services.history').HistoryService
CollectionService = module('services.collection').CollectionService
errors = module('services.exceptions')


def source():
    return SimpleNamespace(
        cpu=lambda: models.CpuInfo(0, 4, 8, None, None, None),
        memory=lambda: models.MemoryInfo(100, 50, 50, 50, models.SwapInfo(0, 0, 0)),
        network=lambda: models.NetworkInfo('eth0', None, 0, 0),
        gpu=lambda: models.GpuInfo(status='unsupported'),
        disk_io=lambda: models.DiskIoInfo(status='warming_up'),
    )


class Repository:
    def __init__(self):
        self.samples = []
        self.calls = []

    def initialize(self):
        self.calls.append('initialize')

    def insert(self, sample):
        self.samples.append(sample)

    def read(self, start, end, *, read_only=False):
        self.calls.append((start, end, read_only))
        return [sample for sample in self.samples if start <= sample.timestamp_ms <= end]

    def delete_before(self, cutoff):
        before = len(self.samples)
        self.samples = [sample for sample in self.samples if sample.timestamp_ms >= cutoff]
        return before - len(self.samples)


class Status:
    def __init__(self):
        self.results = []

    def record(self, **result):
        self.results.append(result)


def test_collection_preserves_zeroes_and_optional_values_without_sql():
    repository, status = Repository(), Status()
    service = CollectionService(source(), repository, status, clock=lambda: 10)
    sample = service.collect_once()
    assert sample.timestamp_ms == 10_000
    assert sample.cpu_usage_percent == 0
    assert sample.network_download_bytes_per_second == 0
    assert sample.gpu_usage_percent is None
    assert sample.disk_read_bytes_per_second is None
    assert repository.samples == [sample]
    assert status.results == [{'sample': sample}]


def test_failed_source_is_recorded_and_later_collection_can_recover():
    repository, status, readers = Repository(), Status(), source()
    def fail():
        raise OSError('read denied')
    readers.cpu = fail
    service = CollectionService(readers, repository, status, clock=lambda: 10)
    with pytest.raises(OSError, match='read denied'):
        service.collect_once()
    assert repository.samples == []
    assert str(status.results[-1]['error']) == 'read denied'
    readers.cpu = source().cpu
    service.collect_once()
    assert len(repository.samples) == 1
    assert 'sample' in status.results[-1]


def test_history_query_passes_window_and_read_only_policy_to_repository():
    repository = Repository()
    result = HistoryService(repository, clock=lambda: 1000).get_historical_metrics(HistoryRange.M15, read_only=True)
    assert repository.calls == [(100_000, 1_000_000, True)]
    assert result.samples == []


def test_repository_failure_becomes_application_error_with_original_cause():
    class Broken(Repository):
        def read(self, *args, **kwargs):
            raise errors.RepositoryUnavailableError('private storage detail')
    with pytest.raises(errors.HistoricalMetricsUnavailableError) as raised:
        HistoryService(Broken()).get_historical_metrics(HistoryRange.H1)
    assert str(raised.value) == 'Historical metrics database unavailable'
    assert str(raised.value.__cause__) == 'private storage detail'
