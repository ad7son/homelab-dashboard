"""標準 FastAPI 獨立啟動入口；平台整合時直接載入 plugin.py。

在本專案 backend/ 執行 uvicorn src.main:app，可獨立提供相同專案 API。
不匯入平台的 app，不在 API 程序內啟動背景採集器。
"""
import json
from pathlib import Path

from fastapi import FastAPI

from .plugin import build_router


def create_app() -> FastAPI:
    manifest = json.loads((Path(__file__).resolve().parents[2] / "project.json").read_text(encoding="utf-8"))
    application = FastAPI(title=manifest["name"])
    application.include_router(build_router(), prefix=manifest["apiPrefix"])
    if manifest.get("legacyApiPrefix"):
        application.include_router(build_router(), prefix=manifest["legacyApiPrefix"])
    return application


app = create_app()
