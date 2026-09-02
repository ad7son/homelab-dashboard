from typing import Optional

from pydantic import BaseModel


class SystemInfo(BaseModel):
    hostname: str
    operating_system: str
    os_version: Optional[str]
    kernel: str
    architecture: str
    uptime: float
