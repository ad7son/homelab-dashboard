"""GPU 卡片資料；未知使用率以 null 表示，與閒置的 0% 明確區分。"""

from typing import Literal

from pydantic import BaseModel, Field


class GpuInfo(BaseModel):
    status: Literal["available", "unavailable", "unsupported"] = "unavailable"
    usage_percent: float | None = Field(default=None, ge=0, le=100)
    name: str | None = None
    device_count: int = 0

