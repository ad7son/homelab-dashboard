from fastapi import APIRouter

from system_monitor.schemas.services import ServicesResponse
from system_monitor.services.services_service import get_services_response

router = APIRouter()


@router.get("/services", response_model=ServicesResponse)
def read_services() -> ServicesResponse:
    return get_services_response()
