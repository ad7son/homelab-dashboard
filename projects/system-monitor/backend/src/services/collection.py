"""採集與保留政策用例；背景程序只安排何時呼叫，不直接讀硬體或執行 SQL。"""
import time
from ..domain.history import MetricSampleRecord
from .ports import MetricsSource, MetricsRepository, CollectorStatusStore


class CollectionService:
    def __init__(self, source: MetricsSource, repository: MetricsRepository, status: CollectorStatusStore,
                 retention_ms: int = 7 * 24 * 60 * 60 * 1000, clock=None):
        self.source = source
        self.repository = repository
        self.status = status
        self.retention_ms = retention_ms
        self.clock = clock or (lambda: time.time())

    def collect_once(self) -> MetricSampleRecord:
        """一次取得並儲存快照，成功或失敗都記錄原始結果；例外交由程序邊界處理。"""
        try:
            self.repository.initialize()
            cpu, memory, network = self.source.cpu(), self.source.memory(), self.source.network()
            gpu, disk = self.source.gpu(), self.source.disk_io()
            sample = MetricSampleRecord(
                timestamp_ms=int(self.clock() * 1000), cpu_usage_percent=float(cpu.usage_percent),
                cpu_temperature_celsius=cpu.temperature, memory_usage_percent=float(memory.usage_percent),
                network_download_bytes_per_second=network.download_rate,
                network_upload_bytes_per_second=network.upload_rate, gpu_usage_percent=gpu.usage_percent,
                disk_read_bytes_per_second=disk.read_bytes_per_second,
                disk_write_bytes_per_second=disk.write_bytes_per_second,
            )
            self.repository.insert(sample)
            self.status.record(sample=sample)
            return sample
        except Exception as exc:
            self.status.record(error=exc)
            raise

    def cleanup(self) -> int:
        return self.repository.delete_before(int(self.clock() * 1000) - self.retention_ms)
