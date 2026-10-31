from fastapi import APIRouter

from system_monitor.schemas.overview import Overview
from system_monitor.services.overview_service import get_overview

router = APIRouter()


@router.get("/overview", response_model=Overview)
def read_overview() -> Overview:
    return get_overview()
