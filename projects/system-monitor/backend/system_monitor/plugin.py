"""System monitor API plugin.

Each ``build_router()`` call returns a new parent router. The loader applies
``apiPrefix`` and, for this project, ``legacyApiPrefix``. Prefixes are not
hardcoded here.
"""

from fastapi import APIRouter

from system_monitor.api import (
    cpu,
    disk,
    history,
    memory,
    network,
    overview,
    services,
    system,
)


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(overview.router)
    router.include_router(system.router)
    router.include_router(cpu.router)
    router.include_router(memory.router)
    router.include_router(disk.router)
    router.include_router(network.router)
    router.include_router(history.router)
    router.include_router(services.router)
    return router
