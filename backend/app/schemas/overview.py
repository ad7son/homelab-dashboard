from typing import List

from pydantic import BaseModel

from app.schemas.cpu import CpuInfo
from app.schemas.disk import DiskInfo
from app.schemas.memory import MemoryInfo
from app.schemas.network import NetworkInfo
from app.schemas.system import SystemInfo


class Overview(BaseModel):
    system: SystemInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disks: List[DiskInfo]
    network: NetworkInfo
