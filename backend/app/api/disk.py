from typing import List, Optional

from fastapi import APIRouter

from app.schemas.disk import DiskInfo
from app.services.disk_service import get_disk_info

router = APIRouter()


@router.get("/disks", response_model=List[DiskInfo])
def read_disks() -> List[DiskInfo]:
    return get_disk_info()
