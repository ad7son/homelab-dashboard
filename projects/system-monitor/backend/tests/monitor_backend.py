"""測試取得平台實際載入的專案模組，避免另建一份 app 與取樣狀態。"""

import importlib
import pathlib
import types

from app.modules import loader
from app.modules import manifest

# 先讓平台完成正常啟動，使 monkeypatch 作用於實際路由使用的同一份模組。
importlib.import_module("app.main")

_PROJECT = pathlib.Path(__file__).resolve().parents[2]
_PACKAGE = loader.project_package_name(
    _PROJECT, manifest.load_project_manifest(_PROJECT).python_package
)


def module(name: str) -> types.ModuleType:
    """取得平台已隔離載入的專案子模組，不另建未隔離的 src 套件。

    Args:
        name: 相對於專案套件的點分路徑，例如 services.history。

    Returns:
        與正式路由共用物件及取樣狀態的模組。

    Raises:
        ModuleNotFoundError: 指定的專案子模組不存在。
    """
    return importlib.import_module(f"{_PACKAGE}.{name}")
