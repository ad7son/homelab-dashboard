"""採集與保留政策用例；背景程序只安排何時呼叫，不直接讀硬體或執行 SQL。"""

from __future__ import annotations

from collections.abc import Callable
import time

from ..domain import history
from . import ports


class CollectionService:
    """將一次主機採集寫成歷史樣本，並記錄成功或失敗的服務。

    Attributes:
        source: 共用取樣基準及來源快取的主機採集介面。
        repository: 歷史樣本儲存介面。
        status: 採集器最近一次嘗試的診斷旁檔介面。
        retention_ms: 原始樣本保留期間，單位毫秒。
        clock: 回傳 Unix 秒數的時鐘，可由測試替換。
    """

    def __init__(
        self,
        source: ports.MetricsSource,
        repository: ports.MetricsRepository,
        status: ports.CollectorStatusStore,
        retention_ms: int = 7 * 24 * 60 * 60 * 1000,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """建立可替換來源、儲存與時鐘的採集服務。

        Args:
            source: 主機採集來源，採集器與 API 各自保留程序內基準。
            repository: 歷史樣本儲存介面。
            status: 最近採集結果的診斷紀錄介面。
            retention_ms: 原始樣本保留期間，單位毫秒。
            clock: 回傳 Unix 秒數的函式；None 時使用系統時間。
        """
        self.source = source
        self.repository = repository
        self.status = status
        self.retention_ms = retention_ms
        self.clock = clock or (lambda: time.time())

    def collect_once(self) -> history.MetricSampleRecord:
        """採集並寫入一筆樣本，成功後更新診斷紀錄。

        Returns:
            已持久化的樣本；選用值 None 保留為缺值，零值保持有效。

        Raises:
            Exception: 初始化、採集、寫入或診斷介面失敗；先嘗試記錄錯誤再重拋。
                若錯誤紀錄本身亦失敗，依介面行為向外傳遞，呼叫端須隔離單次失敗。
        """
        try:
            self.repository.initialize()
            cpu, memory, network = (
                self.source.cpu(),
                self.source.memory(),
                self.source.network(),
            )
            gpu, disk = self.source.gpu(), self.source.disk_io()
            sample = history.MetricSampleRecord(
                timestamp_ms=int(self.clock() * 1000),
                cpu_usage_percent=float(cpu.usage_percent),
                cpu_temperature_celsius=cpu.temperature,
                memory_usage_percent=float(memory.usage_percent),
                network_download_bytes_per_second=network.download_rate,
                network_upload_bytes_per_second=network.upload_rate,
                gpu_usage_percent=gpu.usage_percent,
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
        """回傳刪除筆數；只刪除嚴格早於目前時間減保留期間的樣本。"""
        return self.repository.delete_before(
            int(self.clock() * 1000) - self.retention_ms
        )
