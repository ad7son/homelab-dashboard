from typing import Optional

from pydantic import BaseModel


class DiskInfo(BaseModel):
    device: Optional[str]
    mount_point: str
    filesystem_type: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float
