"""Discover local project folders and mount their API routers.

Plugins are trusted local source code. ``project.json`` is parsed as JSON and
is never evaluated. A failed project aborts the batch before any of that
batch is mounted.
"""

from __future__ import annotations

import hashlib
import importlib
from importlib import machinery
import sys
import dataclasses
import pathlib
import types
from collections.abc import Callable, Iterator
from typing import AsyncContextManager

import fastapi
from fastapi import routing

from app.observability import models as observability_models
from app.plugins import manifest as project_manifest

# backend/app/plugins/loader.py -> parents[3] is the repository root.
_REPOSITORY_ROOT_PARENT_LEVEL = 3

Lifespan = Callable[[fastapi.FastAPI], AsyncContextManager[None]]


@dataclasses.dataclass(frozen=True)
class LoadedProjectRouter:
    """已驗證且等待掛載的專案路由。"""

    manifest: project_manifest.ProjectManifest
    project_dir: pathlib.Path
    router: fastapi.APIRouter
    mount_prefix: str


@dataclasses.dataclass
class _ImportSession:
    """記錄本次觸及的專案命名空間；失敗只撤回新載入的模組。"""

    namespaces: list[str]
    modules_before: set[str]

    def rollback(self) -> None:
        """撤回本次新增的專案模組，保留既有匯入。"""
        for name in list(sys.modules):
            if name in self.modules_before:
                continue
            if any(
                name == namespace or name.startswith(namespace + ".")
                for namespace in self.namespaces
            ):
                del sys.modules[name]


def project_package_name(project_dir: pathlib.Path, package: str) -> str:
    """為專案套件建立獨立匯入名稱，不占用平台 app 或其他專案的同名套件。

    專案 id 供辨識，實際路徑摘要區分不同專案根目錄中的同名專案。
    實體目錄不需配合此名稱改名；專案內的相對匯入可原樣使用。
    """
    directory = pathlib.Path(project_dir).resolve()
    digest = hashlib.sha256(str(directory).encode()).hexdigest()[:12]
    project_id = directory.name.replace("-", "_")
    return f"_a7las_project_{project_id}_{digest}.{package}"


def default_repository_root() -> pathlib.Path:
    """取得儲存庫根目錄，不依賴執行時的工作目錄。"""
    return (
        pathlib.Path(__file__).resolve().parents[_REPOSITORY_ROOT_PARENT_LEVEL]
    )


def default_projects_root() -> pathlib.Path:
    """取得儲存庫的預設專案目錄。"""
    return default_repository_root() / "projects"


def discover_project_manifests(
    projects_root: pathlib.Path,
) -> list[project_manifest.ProjectManifest]:
    """Validate every manifest under ``projects_root``.

    Directories without ``project.json`` are ignored. ``enabled: false``
    manifests are validated and then omitted. Duplicate identifiers or route
    prefixes among enabled projects raise ProjectModuleError.
    """
    projects_root = pathlib.Path(projects_root)
    if not projects_root.exists():
        return []
    if not projects_root.is_dir():
        raise project_manifest.ProjectModuleError(
            f"projects root is not a directory: {projects_root}"
        )

    errors: list[str] = []
    manifests: list[project_manifest.ProjectManifest] = []
    for project_dir in _project_directories(projects_root):
        if not (project_dir / "project.json").is_file():
            continue
        try:
            manifests.append(
                project_manifest.load_project_manifest(project_dir)
            )
        except project_manifest.ProjectModuleError as exc:
            errors.append(str(exc))
    if errors:
        raise project_manifest.ProjectModuleError("\n".join(errors))

    enabled = [manifest for manifest in manifests if manifest.enabled]
    _reject_duplicate_fields(enabled)
    enabled.sort(key=lambda manifest: (manifest.nav.order, manifest.id))
    return enabled


# 批次註冊同時保留路由、生命週期與匯入回復狀態。
# pylint: disable=too-many-locals
def register_project_routers(
    app: fastapi.FastAPI,
    projects_root: pathlib.Path,
) -> list[project_manifest.ProjectManifest]:
    """掛載全部啟用專案；驗證或掛載失敗時保留原本路由與已存在的模組。

    各專案可使用相同的 src 或 app 套件名稱，載入過程不修改 sys.path。
    """
    projects_root = pathlib.Path(projects_root)
    manifests = discover_project_manifests(projects_root)
    session = _ImportSession(namespaces=[], modules_before=set(sys.modules))
    loaded: list[LoadedProjectRouter] = []
    lifespans: list[tuple[str, Lifespan]] = []
    health_projects: list[observability_models.ProjectDefinition] = []
    namespaces: list[tuple[str, str]] = []
    try:
        for manifest in manifests:
            project_dir = projects_root / manifest.id
            _require_plugin_file(project_dir, manifest)
            router = _import_build_router(session, project_dir, manifest)
            package = project_package_name(project_dir, manifest.python_package)
            module_name = f"{package}.plugin"
            feature_factory = getattr(
                sys.modules[module_name], "get_health_features", None
            )
            if feature_factory is not None and not callable(feature_factory):
                raise project_manifest.ProjectModuleError(
                    f"project '{manifest.id}': get_health_features must be"
                    " callable"
                )
            try:
                health_projects.append(
                    observability_models.ProjectDefinition(
                        id=manifest.id,
                        name=manifest.name,
                        features=feature_factory() if feature_factory else (),
                    )
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise project_manifest.ProjectModuleError(
                    f"project '{manifest.id}': invalid health features ({exc})"
                ) from exc
            namespaces.append((package, manifest.id))
            factory = getattr(sys.modules[module_name], "lifespan", None)
            if factory is not None:
                if not callable(factory):
                    raise project_manifest.ProjectModuleError(
                        f"project '{manifest.id}': lifespan must be callable"
                    )
                lifespans.append((manifest.id, factory))
            loaded.append(
                LoadedProjectRouter(
                    manifest=manifest,
                    project_dir=project_dir,
                    router=router,
                    mount_prefix=manifest.api_prefix,
                )
            )
            if manifest.legacy_api_prefix is not None:
                loaded.append(
                    LoadedProjectRouter(
                        manifest=manifest,
                        project_dir=project_dir,
                        router=_build_additional_router(project_dir, manifest),
                        mount_prefix=manifest.legacy_api_prefix,
                    )
                )
        _reject_duplicate_http_routes(app, loaded)
    except Exception:
        session.rollback()
        raise

    snapshot = list(app.router.routes)
    try:
        for item in loaded:
            app.include_router(item.router, prefix=item.mount_prefix)
    except Exception as exc:
        app.router.routes[:] = snapshot
        session.rollback()
        raise project_manifest.ProjectModuleError(
            f"failed while mounting project routers: {exc}"
        ) from exc
    previous = getattr(app.state, "project_lifespans", ())
    app.state.project_lifespans = (*previous, *lifespans)
    app.state.health_projects = (
        *getattr(app.state, "health_projects", ()),
        *health_projects,
    )
    app.state.project_log_namespaces = (
        *getattr(app.state, "project_log_namespaces", ()),
        *namespaces,
    )
    return manifests


def _project_directories(projects_root: pathlib.Path) -> Iterator[pathlib.Path]:
    """依名稱排序列出專案目錄。"""
    for child in sorted(projects_root.iterdir(), key=lambda path: path.name):
        if child.is_dir():
            yield child


def _reject_duplicate_fields(
    manifests: list[project_manifest.ProjectManifest],
) -> None:
    """拒絕啟用專案之間的識別碼與前綴衝突。"""
    seen_ids: dict[str, str] = {}
    seen_routes: dict[str, str] = {}
    seen_prefixes: dict[str, str] = {}
    for manifest in manifests:
        _remember_unique(seen_ids, manifest.id, manifest.id, "id")
        _remember_unique(
            seen_routes, manifest.route_base, manifest.id, "routeBase"
        )
        for legacy_route in manifest.legacy_route_bases:
            _remember_unique(
                seen_routes, legacy_route, manifest.id, "legacyRouteBases"
            )
        _remember_unique(
            seen_prefixes, manifest.api_prefix, manifest.id, "apiPrefix"
        )
        if manifest.legacy_api_prefix is not None:
            _remember_unique(
                seen_prefixes,
                manifest.legacy_api_prefix,
                manifest.id,
                "legacyApiPrefix",
            )


def _remember_unique(
    seen: dict[str, str],
    value: str,
    project_id: str,
    field_name: str,
) -> None:
    """記錄唯一欄位，重複時加入錯誤訊息。"""
    previous = seen.get(value)
    if previous is not None:
        raise project_manifest.ProjectModuleError(
            f"duplicate {field_name} '{value}' used by projects '{previous}'"
            f" and '{project_id}'"
        )
    seen[value] = project_id


def _require_plugin_file(
    project_dir: pathlib.Path, manifest: project_manifest.ProjectManifest
) -> pathlib.Path:
    """確認 plugin 存在且沒有逃出專案目錄。"""
    plugin_path = (
        project_dir / "backend" / manifest.python_package / "plugin.py"
    )
    if not plugin_path.is_file():
        raise project_manifest.ProjectModuleError(
            f"{plugin_path}: enabled project '{manifest.id}' is missing"
            f" plugin.py (expected backend/{manifest.python_package}/plugin.py)"
        )
    return plugin_path


def _import_build_router(
    session: _ImportSession,
    project_dir: pathlib.Path,
    manifest: project_manifest.ProjectManifest,
) -> fastapi.APIRouter:
    """在隔離命名空間匯入 plugin 並建立路由。"""
    backend_dir = (project_dir / "backend").resolve()
    package = project_package_name(project_dir, manifest.python_package)
    namespace = package.rpartition(".")[0]
    module_name = f"{package}.plugin"
    session.namespaces.append(namespace)
    existing = sys.modules.get(namespace)
    if existing is None:
        # namespace 只提供這個專案的 backend 搜尋位置，不執行其他專案程式。
        existing = types.ModuleType(namespace)
        existing.__package__ = namespace
        existing.__path__ = [str(backend_dir)]
        spec = machinery.ModuleSpec(namespace, loader=None, is_package=True)
        spec.submodule_search_locations = [str(backend_dir)]
        existing.__spec__ = spec
        sys.modules[namespace] = existing
    elif list(getattr(existing, "__path__", [])) != [str(backend_dir)]:
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': namespace belongs to a different"
            " location"
        )
    try:
        module = importlib.import_module(module_name)
    except project_manifest.ProjectModuleError:
        raise
    except Exception as exc:
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': failed to import {module_name} ({exc})"
        ) from exc

    loaded_file = getattr(module, "__file__", None)
    if (
        loaded_file is None
        or pathlib.Path(loaded_file).resolve().parent
        != backend_dir / manifest.python_package
    ):
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': imported {module_name} from an"
            " unexpected location"
        )
    build_router = getattr(module, "build_router", None)
    if not callable(build_router):
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': {module_name} must define build_router()"
        )
    try:
        router = build_router()
    except Exception as exc:
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': build_router() failed ({exc})"
        ) from exc
    if not isinstance(router, fastapi.APIRouter):
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': build_router() must return an"
            " fastapi.APIRouter"
        )
    return router


def _build_additional_router(
    project_dir: pathlib.Path, manifest: project_manifest.ProjectManifest
) -> fastapi.APIRouter:
    """為歷史相容前綴建立獨立的路由實例。"""
    module = sys.modules.get(
        f"{project_package_name(project_dir, manifest.python_package)}.plugin"
    )
    if module is None:
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': plugin was not imported before the"
            " legacy mount"
        )
    build_router = getattr(module, "build_router", None)
    if not callable(build_router):
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': {manifest.python_package}.plugin must"
            " define build_router()"
        )
    try:
        router = build_router()
    except Exception as exc:
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': build_router() failed ({exc})"
        ) from exc
    if not isinstance(router, fastapi.APIRouter):
        raise project_manifest.ProjectModuleError(
            f"project '{manifest.id}': build_router() must return an"
            " fastapi.APIRouter"
        )
    return router


def _reject_duplicate_http_routes(
    app: fastapi.FastAPI,
    loaded: list[LoadedProjectRouter],
) -> None:
    """檢查既有路由與待掛載專案的 HTTP 路徑衝突。"""
    owners: dict[tuple[str, str], str] = {}
    for method, path in _iter_existing_route_keys(app):
        owners[(method, path)] = "application"
    for item in loaded:
        for method, path in _iter_plugin_route_keys(item):
            key = (method, path)
            previous = owners.get(key)
            if previous is not None:
                raise project_manifest.ProjectModuleError(
                    f"duplicate route {method} {path} claimed by "
                    f"'{previous}' and '{item.manifest.id}'"
                )
            owners[key] = item.manifest.id


def _iter_existing_route_keys(
    app: fastapi.FastAPI,
) -> Iterator[tuple[str, str]]:
    """列出平台既有路由識別鍵。"""
    yield from _iter_route_keys(
        app.router, prefix=None, project_id="application"
    )


def _iter_plugin_route_keys(
    item: LoadedProjectRouter,
) -> Iterator[tuple[str, str]]:
    """列出專案掛載後的路由識別鍵。"""
    yield from _iter_route_keys(
        item.router,
        prefix=item.mount_prefix,
        project_id=item.manifest.id,
    )


def _iter_route_keys(
    router: fastapi.APIRouter,
    *,
    prefix: str | None,
    project_id: str,
) -> Iterator[tuple[str, str]]:
    """展開路由及子路由的 HTTP 方法與路徑。"""
    for route in router.routes:
        effective = getattr(route, "effective_candidates", None)
        if callable(effective):
            for candidate in effective():
                path = getattr(candidate, "path", None)
                methods = getattr(candidate, "methods", None)
                if not isinstance(path, str) or not methods:
                    raise project_manifest.ProjectModuleError(
                        f"project '{project_id}': only HTTP routes can be"
                        " registered"
                    )
                yield from _keys_for_path(prefix, path, methods, project_id)
            continue
        if isinstance(route, routing.APIRoute) or (
            isinstance(getattr(route, "path", None), str)
            and getattr(route, "methods", None)
        ):
            yield from _keys_for_path(
                prefix,
                route.path,
                route.methods or set(),
                project_id,
            )
            continue
        raise project_manifest.ProjectModuleError(
            f"project '{project_id}': unsupported route type"
            f" {type(route).__name__}"
        )


def _keys_for_path(
    prefix: str | None,
    route_path: str,
    methods: set[str],
    project_id: str,
) -> Iterator[tuple[str, str]]:
    """產生單一路徑對應的 HTTP 路由識別鍵。"""
    if prefix is None:
        full_path = route_path
    else:
        full_path = _namespaced_path(prefix, route_path, project_id)
    for method in methods:
        yield method.upper(), full_path


def _namespaced_path(prefix: str, route_path: str, project_id: str) -> str:
    """組合掛載前綴並驗證專案路徑邊界。"""
    if not route_path.startswith("/"):
        raise project_manifest.ProjectModuleError(
            f"project '{project_id}': route path '{route_path}' must start"
            " with '/'"
        )
    segments = [segment for segment in route_path.split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise project_manifest.ProjectModuleError(
            f"project '{project_id}': route '{route_path}' escapes apiPrefix"
            f" '{prefix}'"
        )
    if "\\" in route_path or "%" in route_path or "\x00" in route_path:
        raise project_manifest.ProjectModuleError(
            f"project '{project_id}': route '{route_path}' contains an unsafe"
            " path segment"
        )
    full_path = prefix + route_path
    if full_path != prefix and not full_path.startswith(prefix + "/"):
        raise project_manifest.ProjectModuleError(
            f"project '{project_id}': route '{full_path}' is outside apiPrefix"
            f" '{prefix}'"
        )
    return full_path
