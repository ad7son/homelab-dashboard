"""A7LAS configuration package.

Central, deployment-oriented settings that are not request/response schemas.
"""

from app.config.monitored_services import (
    MONITORED_SERVICES,
    MonitoredServiceConfig,
)
from app.config.version import A7LAS_VERSION

__all__ = [
    "A7LAS_VERSION",
    "MONITORED_SERVICES",
    "MonitoredServiceConfig",
]
