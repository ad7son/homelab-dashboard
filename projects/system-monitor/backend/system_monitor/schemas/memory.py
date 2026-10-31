from pydantic import BaseModel


class SwapInfo(BaseModel):
    total: int
    used: int
    usage_percent: float


class MemoryInfo(BaseModel):
    total: int
    used: int
    available: int
    usage_percent: float
    swap: SwapInfo
