from fastapi import APIRouter

from app.schemas.system import SystemInfo
from app.services.system_service import get_system_info

router = APIRouter()


@router.get("/system", response_model=SystemInfo)
def read_system() -> SystemInfo:
    return get_system_info()
