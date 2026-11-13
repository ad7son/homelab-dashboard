"""即時總覽 HTTP 入口；不執行硬體與儲存操作。"""
from fastapi import APIRouter, Depends
from ..dependencies import get_overview_service
from ..schemas.overview import Overview
from ...domain.serialization import to_dict
from ...services.overview import OverviewService

router = APIRouter()


@router.get("/overview", response_model=Overview)
def read_overview(service: OverviewService = Depends(get_overview_service)) -> Overview:
    return Overview.model_validate(to_dict(service.get_overview()))
