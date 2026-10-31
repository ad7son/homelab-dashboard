from fastapi import APIRouter

from system_monitor.schemas.network import NetworkInfo
from system_monitor.services.network_service import get_network_info

router = APIRouter()


@router.get("/network", response_model=NetworkInfo)
def read_network() -> NetworkInfo:
    return get_network_info()
