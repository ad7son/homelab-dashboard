"""A7LAS configuration package.

Central, deployment-oriented settings that are not request/response schemas.
"""

from app.config.monitored_services import (
    MONITORED_SERVICES,
    MonitoredServiceConfig,
)

__all__ = [
    "MONITORED_SERVICES",
    "MonitoredServiceConfig",
]
