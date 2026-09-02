from typing import Optional

from pydantic import BaseModel


class NetworkInfo(BaseModel):
    interface: Optional[str]
    ip_address: Optional[str]
    download_rate: Optional[float]
    upload_rate: Optional[float]
