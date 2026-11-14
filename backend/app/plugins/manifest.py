"""Version 1 project manifest schema and file validation."""

from __future__ import annotations

import json
import keyword
import re
import pathlib

import pydantic

ALLOWED_PROJECT_ICONS = frozenset(
    {
        "server",
        "boxes",
        "activity",
        "folder",
        "database",
        "bot",
        "layout-dashboard",
    }
)

# Shell routes owned by the platform, not by a project module.
RESERVED_ROUTE_BASES = frozenset({"/settings"})

# Platform endpoints that must stay outside every project apiPrefix.
RESERVED_API_PREFIXES = frozenset(
    {"/api/health", "/api/project-health", "/api/logs"}
)

# The pre-modular dashboard served monitoring at /api. Only system-monitor
# may keep that prefix. Other projects must use a namespaced /api/{id} prefix.
LEGACY_API_ROOT = "/api"
LEGACY_API_ROOT_PROJECT_ID = "system-monitor"

_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PACKAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_ROUTE_BASE_PATTERN = re.compile(
    r"^/[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$"
)
_API_PREFIX_PATTERN = re.compile(
    r"^/api/[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$"
)
_NAV_PATH_PATTERN = re.compile(
    r"^(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$"
)

_FIELD_NAMES = {
    "schema_version": "schemaVersion",
    "python_package": "pythonPackage",
    "route_base": "routeBase",
    "api_prefix": "apiPrefix",
    "legacy_route_bases": "legacyRouteBases",
    "legacy_api_prefix": "legacyApiPrefix",
    "document_title": "documentTitle",
}


class ProjectModuleError(Exception):
    """A project manifest or plugin failed validation."""


class ProjectNavItem(pydantic.BaseModel):
    """專案側邊欄的單一導覽項目。"""

    model_config = pydantic.ConfigDict(extra="forbid", populate_by_name=True)

    path: str
    label: str
    icon: str
    end: bool = False
    document_title: str = pydantic.Field(alias="documentTitle")

    @pydantic.field_validator("path")
    @classmethod
    def validate_path(cls, value: object) -> str:
        """驗證相對導覽路徑，不接受路徑跳脫。"""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        if value == "":
            return value
        if _contains_unsafe_path_text(value) or value.startswith("/"):
            raise ValueError(
                "must be a relative kebab-case path without '.' or '..'"
                " segments"
            )
        if _NAV_PATH_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "must be a relative kebab-case path such as 'services'"
            )
        return value

    @pydantic.field_validator("label", "document_title")
    @classmethod
    def validate_required_text(cls, value: object) -> str:
        """要求非空白文字。"""
        return _required_text(value)

    @pydantic.field_validator("icon")
    @classmethod
    def validate_icon(cls, value: object) -> str:
        """限制為平台支援的圖示。"""
        if not isinstance(value, str) or value not in ALLOWED_PROJECT_ICONS:
            allowed = ", ".join(sorted(ALLOWED_PROJECT_ICONS))
            raise ValueError(f"must be one of: {allowed}")
        return value

    @pydantic.field_validator("end")
    @classmethod
    def validate_end(cls, value: object) -> bool:
        """僅接受布林值。"""
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value


class ProjectNav(pydantic.BaseModel):
    """專案導覽分組與排序。"""

    model_config = pydantic.ConfigDict(extra="forbid", populate_by_name=True)

    section: str
    order: int
    items: list[ProjectNavItem]

    @pydantic.field_validator("section")
    @classmethod
    def validate_section(cls, value: object) -> str:
        """驗證導覽分組名稱。"""
        return _required_text(value)

    @pydantic.field_validator("order")
    @classmethod
    def validate_order(cls, value: object) -> int:
        """驗證排序為整數。"""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be an integer")
        return value

    @pydantic.field_validator("items")
    @classmethod
    def validate_items(cls, value: object) -> object:
        """拒絕空導覽清單。"""
        if isinstance(value, list) and len(value) == 0:
            raise ValueError("must contain at least one item")
        return value

    @pydantic.model_validator(mode="after")
    def reject_duplicate_paths(self) -> "ProjectNav":
        """拒絕重複導覽路徑。"""
        seen: set[str] = set()
        for item in self.items:
            if item.path in seen:
                raise ValueError(f"duplicate nav path '{item.path}'")
            seen.add(item.path)
        return self


class ProjectManifest(pydantic.BaseModel):
    """Manifest contract shared with frontend/src/modules/loadProjects.ts."""

    model_config = pydantic.ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = pydantic.Field(alias="schemaVersion")
    id: str
    name: str
    description: str = ""
    python_package: str = pydantic.Field(alias="pythonPackage")
    route_base: str = pydantic.Field(alias="routeBase")
    api_prefix: str = pydantic.Field(alias="apiPrefix")
    legacy_route_bases: list[str] = pydantic.Field(
        default_factory=list,
        alias="legacyRouteBases",
    )
    legacy_api_prefix: str | None = pydantic.Field(
        default=None, alias="legacyApiPrefix"
    )
    enabled: bool = True
    nav: ProjectNav

    @pydantic.field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: object) -> int:
        """僅接受目前支援的宣告格式版本。"""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("must be the integer 1")
        if value != 1:
            raise ValueError("must be 1")
        return value

    @pydantic.field_validator("id")
    @classmethod
    def validate_id(cls, value: object) -> str:
        """驗證專案識別碼。"""
        if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
            raise ValueError(
                "must be lowercase kebab-case (for example 'system-monitor')"
            )
        return value

    @pydantic.field_validator("name")
    @classmethod
    def validate_name(cls, value: object) -> str:
        """驗證專案顯示名稱。"""
        return _required_text(value)

    @pydantic.field_validator("description")
    @classmethod
    def validate_description(cls, value: object) -> str:
        """驗證選用的專案說明。"""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        return value

    @pydantic.field_validator("python_package")
    @classmethod
    def validate_python_package(cls, value: object) -> str:
        """限制為合法且不衝突的 Python 套件名稱。"""
        if (
            not isinstance(value, str)
            or _PACKAGE_PATTERN.fullmatch(value) is None
            or keyword.iskeyword(value)
        ):
            raise ValueError(
                "must be a lowercase Python package name (letters, digits, and"
                " underscores; for example 'system_monitor')"
            )
        return value

    @pydantic.field_validator("route_base")
    @classmethod
    def validate_route_base(cls, value: object) -> str:
        """驗證專案頁面前綴。"""
        return _validate_public_route(value)

    @pydantic.field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: object) -> str:
        """驗證專案 API 前綴。"""
        return _validate_namespaced_api_prefix(value)

    @pydantic.field_validator("legacy_route_bases")
    @classmethod
    def validate_legacy_route_bases(cls, value: object) -> list[str]:
        """驗證相容路由並拒絕重複。"""
        if not isinstance(value, list):
            raise ValueError("must be an array of absolute paths")
        cleaned = [_validate_public_route(item) for item in value]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("must not contain duplicate paths")
        return cleaned

    @pydantic.field_validator("legacy_api_prefix")
    @classmethod
    def validate_legacy_api_prefix(
        cls,
        value: object,
        info: pydantic.ValidationInfo,
    ) -> str | None:
        """只允許指定專案使用歷史 API 根前綴。"""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("must be a string")
        if value == info.data.get("api_prefix"):
            raise ValueError("must differ from apiPrefix")
        if value == LEGACY_API_ROOT:
            if info.data.get("id") != LEGACY_API_ROOT_PROJECT_ID:
                raise ValueError(
                    "only project 'system-monitor' may set legacyApiPrefix to"
                    " '/api'"
                )
            return value
        return _validate_namespaced_api_prefix(value)

    @pydantic.field_validator("enabled")
    @classmethod
    def validate_enabled(cls, value: object) -> bool:
        """驗證專案啟用旗標。"""
        if not isinstance(value, bool):
            raise ValueError("must be a boolean")
        return value


def load_project_manifest(project_dir: pathlib.Path) -> ProjectManifest:
    """Read and validate ``project_dir / project.json``.

    ``id`` must equal ``project_dir.name``. The JSON document is parsed only;
    its string values are never executed.
    """
    project_dir = pathlib.Path(project_dir)
    manifest_path = project_dir / "project.json"
    payload = _read_manifest_object(manifest_path)
    try:
        manifest = ProjectManifest.model_validate(payload)
    except pydantic.ValidationError as exc:
        raise ProjectModuleError(
            _format_validation_error(manifest_path, exc)
        ) from exc
    if manifest.id != project_dir.name:
        raise ProjectModuleError(
            f"{manifest_path}: id '{manifest.id}' does not match "
            f"project directory name '{project_dir.name}'"
        )
    _reject_overlapping_routes(manifest, manifest_path)
    return manifest


def _read_manifest_object(manifest_path: pathlib.Path) -> object:
    """讀取 JSON 並要求根節點為物件。"""
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectModuleError(
            f"{manifest_path}: project.json must be UTF-8 text"
        ) from exc
    except OSError as exc:
        raise ProjectModuleError(
            f"{manifest_path}: unable to read project manifest ({exc})"
        ) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProjectModuleError(
            f"{manifest_path}: invalid JSON ({exc.msg} at line {exc.lineno})"
        ) from exc
    if not isinstance(payload, dict):
        raise ProjectModuleError(
            f"{manifest_path}: project manifest must be a JSON object"
        )
    return payload


def _format_validation_error(
    manifest_path: pathlib.Path, exc: pydantic.ValidationError
) -> str:
    """將驗證錯誤對應至 manifest 欄位名稱。"""
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(
            _FIELD_NAMES.get(str(item), str(item)) for item in error["loc"]
        )
        message = str(error["msg"])
        prefix = "Value error, "
        if message.startswith(prefix):
            message = message[len(prefix) :]
        parts.append(f"{location}: {message}")
    detail = "; ".join(parts) if parts else str(exc)
    return f"{manifest_path}: invalid project manifest ({detail})"


def _required_text(value: object) -> str:
    """驗證並回傳非空白字串。"""
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError("must be a non-empty string")
    return value


def _contains_unsafe_path_text(value: str) -> bool:
    """辨認可能造成路徑跳脫的內容。"""
    if "\\" in value or "\x00" in value or "%" in value:
        return True
    return any(segment in {".", ".."} for segment in value.split("/"))


def _validate_public_route(value: object) -> str:
    """驗證公開頁面路徑格式。"""
    if not isinstance(value, str) or _contains_unsafe_path_text(value):
        raise ValueError(
            "must be an absolute kebab-case path such as '/system-monitor'"
        )
    if value == "/" or _is_reserved_path(value, RESERVED_ROUTE_BASES):
        raise ValueError(
            "is reserved by the platform shell; '/' and '/settings' cannot be"
            " used"
        )
    if _ROUTE_BASE_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "must be an absolute kebab-case path such as '/system-monitor'"
        )
    return value


def _validate_namespaced_api_prefix(value: object) -> str:
    """驗證帶有專案命名空間的 API 前綴。"""
    if not isinstance(value, str) or _contains_unsafe_path_text(value):
        raise ValueError(
            "must start with '/api/' and name a project namespace "
            "such as '/api/system-monitor'"
        )
    if value in {"/api", "/api/"}:
        raise ValueError("must name a project namespace and cannot be '/api'")
    if _is_reserved_path(value, RESERVED_API_PREFIXES):
        raise ValueError(f"'{value}' is reserved by the platform")
    if _API_PREFIX_PATTERN.fullmatch(value) is None:
        raise ValueError(
            "must start with '/api/' and use kebab-case segments "
            "such as '/api/system-monitor'"
        )
    return value


def _reject_overlapping_routes(
    manifest: ProjectManifest, manifest_path: pathlib.Path
) -> None:
    """拒絕專案路由與平台保留路徑重疊。"""
    labeled = [("routeBase", manifest.route_base)]
    labeled.extend(
        ("legacyRouteBases", item) for item in manifest.legacy_route_bases
    )
    for index, (left_field, left) in enumerate(labeled):
        for right_field, right in labeled[index + 1 :]:
            if (
                left == right
                or left.startswith(right + "/")
                or right.startswith(left + "/")
            ):
                raise ProjectModuleError(
                    f"{manifest_path}: invalid project manifest "
                    f"({left_field} '{left}' overlaps {right_field} '{right}')"
                )


def _is_reserved_path(value: str, reserved: frozenset[str]) -> bool:
    """檢查路徑是否涵蓋平台保留端點。"""
    for item in reserved:
        if value == item or value.startswith(item + "/"):
            return True
    return False
