from fastapi import APIRouter

from app.schemas.network import NetworkInfo
from app.services.network_service import get_network_info

router = APIRouter()


@router.get("/network", response_model=NetworkInfo)
def read_network() -> NetworkInfo:
    return get_network_info()
