"""測試取得平台實際載入的專案模組，避免另建一份 app 與取樣狀態。"""
from importlib import import_module
from pathlib import Path

# 先讓平台完成正常啟動，再取得同一命名空間的模組，讓 monkeypatch 作用於實際路由。
from app.modules.loader import project_package_name
from app.modules.manifest import load_project_manifest

import_module("app.main")

_PROJECT = Path(__file__).resolve().parents[2]
_PACKAGE = project_package_name(_PROJECT, load_project_manifest(_PROJECT).python_package)


def module(name: str):
    return import_module(f"{_PACKAGE}.{name}")
