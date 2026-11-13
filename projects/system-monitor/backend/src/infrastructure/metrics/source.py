"""將五種實際採集器組合成應用層需要的 MetricsSource。"""

from __future__ import annotations

from ...domain import metrics
from . import cpu as cpu_metrics
from . import disk_io as disk_io_metrics
from . import gpu as gpu_metrics
from . import memory as memory_metrics
from . import network as network_metrics


class SystemMetricsSource:
    """將五個具狀態的硬體採集器轉接為應用服務介面的來源。

    Attributes:
        cpu_reader: 保留 CPU 預熱狀態的採集器。
        memory_reader: 記憶體採集器。
        network_reader: 保留主要介面前次計數的採集器。
        gpu_reader: 保留 GPU 快取的採集器。
        disk_io_reader: 保留磁碟計數基準的採集器。
    """

    def __init__(
        self,
        cpu: cpu_metrics.CpuReader,
        memory: memory_metrics.MemoryReader,
        network: network_metrics.NetworkReader,
        gpu: gpu_metrics.GpuReader,
        disk_io: disk_io_metrics.DiskIoReader,
    ) -> None:
        """組合既有採集器實例，不重設其基準或快取。

        Args:
            cpu: CPU 採集器。
            memory: 記憶體採集器。
            network: 網路採集器。
            gpu: GPU 採集器。
            disk_io: 磁碟 I/O 採集器。
        """
        self.cpu_reader, self.memory_reader = cpu, memory
        self.network_reader, self.gpu_reader, self.disk_io_reader = (
            network,
            gpu,
            disk_io,
        )

    def cpu(self) -> metrics.CpuInfo:
        """回傳既有採集器的CPU快照，不另建採集器實例。"""
        return self.cpu_reader.read()

    def memory(self) -> metrics.MemoryInfo:
        """回傳既有採集器的記憶體與 Swap快照，不另建採集器實例。"""
        return self.memory_reader.read()

    def network(self) -> metrics.NetworkInfo:
        """回傳既有採集器的主要介面流量快照，不另建採集器實例。"""
        return self.network_reader.read()

    def gpu(self) -> metrics.GpuInfo:
        """回傳既有採集器的GPU快照，不另建採集器實例。"""
        return self.gpu_reader.read()

    def disk_io(self) -> metrics.DiskIoInfo:
        """回傳既有採集器的磁碟 I/O快照，不另建採集器實例。"""
        return self.disk_io_reader.read()
