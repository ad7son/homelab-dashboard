"""即時總覽用例：組合各項快照，不了解 psutil、GPU 指令或 HTTP。"""
from ..domain.metrics import Overview
from .ports import MetricsSource


class OverviewService:
    def __init__(self, source: MetricsSource):
        self.source = source

    def get_overview(self) -> Overview:
        return Overview(
            cpu=self.source.cpu(), memory=self.source.memory(), network=self.source.network(),
            gpu=self.source.gpu(), disk_io=self.source.disk_io(),
        )
