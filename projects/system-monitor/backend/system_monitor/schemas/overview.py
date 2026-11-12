from typing import List

from pydantic import BaseModel

from system_monitor.schemas.cpu import CpuInfo
from system_monitor.schemas.disk import DiskInfo
from system_monitor.schemas.memory import MemoryInfo
from system_monitor.schemas.network import NetworkInfo
from system_monitor.schemas.system import SystemInfo
from system_monitor.schemas.gpu import GpuInfo
from system_monitor.schemas.disk_io import DiskIoInfo


class Overview(BaseModel):
    system: SystemInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disks: List[DiskInfo]
    network: NetworkInfo
    gpu: GpuInfo
    disk_io: DiskIoInfo
