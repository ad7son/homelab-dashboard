from fastapi import APIRouter

from app.schemas.overview import Overview
from app.services.overview_service import get_overview

router = APIRouter()


@router.get("/overview", response_model=Overview)
def read_overview() -> Overview:
    return get_overview()
