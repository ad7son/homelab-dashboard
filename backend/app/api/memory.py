from fastapi import APIRouter

from app.schemas.memory import MemoryInfo
from app.services.memory_service import get_memory_info

router = APIRouter()


@router.get("/memory", response_model=MemoryInfo)
def read_memory() -> MemoryInfo:
    return get_memory_info()
