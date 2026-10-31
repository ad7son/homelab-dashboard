"""Project Showcase API plugin.

``build_router()`` returns a new parent router. Route paths stay relative.
The loader mounts the router at the manifest ``apiPrefix``.
"""

from fastapi import APIRouter

from project_showcase.api.showcase import router as showcase_router


def build_router() -> APIRouter:
    """Return a new router that exposes the showcase info route."""
    router = APIRouter()
    router.include_router(showcase_router)
    return router
