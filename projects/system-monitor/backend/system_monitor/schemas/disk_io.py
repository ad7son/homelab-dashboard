"""磁碟 I/O 回應；速率單位為 bytes/s，首次取樣不回傳假造的零值。"""

from typing import Literal

from pydantic import BaseModel, Field


class DiskIoInfo(BaseModel):
    status: Literal["available", "warming_up", "unavailable"] = "unavailable"
    read_bytes_per_second: float | None = Field(default=None, ge=0)
    write_bytes_per_second: float | None = Field(default=None, ge=0)

