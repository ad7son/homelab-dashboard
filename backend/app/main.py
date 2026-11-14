import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.modules import lifecycle
from app.observability import router as observability_router
from app.modules.loader import default_projects_root, register_project_routers
from app.modules.manifest import ProjectModuleError

logger = logging.getLogger("a7las")


def create_app(projects_root: Path | None = None) -> FastAPI:
    """Create the platform app and mount every enabled project.

    An invalid enabled project raises ``ProjectModuleError`` before this
    function returns. The raised error names the manifest or plugin problem.
    """
    application = FastAPI(
        title="Home Lab Dashboard API", lifespan=lifecycle.project_lifespan
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.include_router(health.router, prefix="/api", tags=["health"])
    application.include_router(observability_router.router, prefix="/api", tags=["observability"])
    root = default_projects_root() if projects_root is None else Path(projects_root)
    try:
        register_project_routers(application, root)
    except ProjectModuleError:
        logger.exception("Refusing to start because a project module failed to load")
        raise
    return application


app = create_app()
