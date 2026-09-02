from fastapi import APIRouter

from app.schemas.cpu import CpuInfo
from app.services.cpu_service import get_cpu_info

router = APIRouter()


@router.get("/cpu", response_model=CpuInfo)
def read_cpu() -> CpuInfo:
    return get_cpu_info()
