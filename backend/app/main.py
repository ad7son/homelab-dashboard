"""A7LAS 平台組裝入口；專案行為由各自 plugin 提供。"""

from __future__ import annotations

import logging
import pathlib

import fastapi
from fastapi.middleware import cors

from app import api
from app import config
from app import lifecycle
from app.plugins import loader
from app.plugins import manifest

_logger = logging.getLogger(__name__)


def create_app(projects_root: pathlib.Path | None = None) -> fastapi.FastAPI:
    """建立平台並掛載啟用專案；無效專案使建立流程失敗。"""
    application = fastapi.FastAPI(
        title="Home Lab Dashboard API", lifespan=lifecycle.lifespan
    )
    application.add_middleware(
        cors.CORSMiddleware,
        allow_origins=list(config.CORS_ALLOW_ORIGINS),
        allow_credentials=True,
        allow_methods=list(config.CORS_ALLOW_METHODS),
        allow_headers=["*"],
    )
    application.include_router(api.router, prefix="/api")
    root = (
        loader.default_projects_root()
        if projects_root is None
        else pathlib.Path(projects_root)
    )
    try:
        loader.register_project_routers(application, root)
    except manifest.ProjectModuleError:
        _logger.exception(
            "Refusing to start because a project module failed to load"
        )
        raise
    return application


app = create_app()
