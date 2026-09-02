from typing import Optional

from pydantic import BaseModel


class LoadAverage(BaseModel):
    load_1: float
    load_5: float
    load_15: float


class CpuInfo(BaseModel):
    usage_percent: float
    physical_cores: int
    logical_cores: int
    frequency: Optional[float]
    temperature: Optional[float]
    load_average: Optional[LoadAverage]
