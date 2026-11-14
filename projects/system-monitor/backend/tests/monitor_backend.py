"""取得平台實際隔離載入的模組，避免測試匯入另一份 src。"""

import importlib
import pathlib

from app import main
from app.plugins import loader


def module(name):
    """取得已註冊專案的模組，不另建採集器或變更 sys.path。"""
    if main.app is None:
        raise RuntimeError("Platform app has not been initialized")
    project = pathlib.Path(__file__).resolve().parents[2]
    package = loader.project_package_name(project, "src")
    return importlib.import_module(f"{package}.{name}")
