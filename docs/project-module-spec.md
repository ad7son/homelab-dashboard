# Project Module Specification

The shell and the FastAPI app discover projects from `projects/`. Home Lab monitoring lives in `projects/system-monitor`. Adding another project does not require editing the Sidebar, the React router, or `backend/app/main.py`.

## 1. Modular Architecture

A7LAS is one React application and one FastAPI process.

- `frontend/` is the shared shell: layout, header, sidebar, and the Vite app.
- `backend/` is the shared FastAPI application, health endpoint, and module loader.
- `projects/{project-id}/` is one showcase module. It is source code inside this repository, not a separate npm package and not a separate virtual environment.

Adding a module later means adding a folder that matches this contract, then restarting the dev servers or rebuilding. Discovery is build-time in Vite and startup-time in FastAPI.

## 2. Project Directory Contract

```text
projects/{project-id}/
  project.json
  frontend/index.tsx
  backend/{pythonPackage}/plugin.py
```

`project-id` is lowercase kebab-case and must equal `project.json` `id`. Example: `system-monitor`.

`pythonPackage` is a Python identifier naming the directory under `backend/`. System Monitor uses `src`, with no additional `app/` or project-named package underneath:

```text
projects/system-monitor/backend/src/plugin.py
```

Directories under `projects/` that do not contain `project.json` are ignored.

## 3. project.json Schema

Schema version is the integer `1`. Unknown fields are rejected. `enabled` defaults to `true`. `description` defaults to an empty string.

```json
{
  "schemaVersion": 1,
  "id": "system-monitor",
  "name": "System Monitor",
  "description": "Real-time system monitoring dashboard",
  "pythonPackage": "src",
  "routeBase": "/system-monitor",
  "apiPrefix": "/api/system-monitor",
  "legacyRouteBases": [
    "/homelab"
  ],
  "legacyApiPrefix": "/api",
  "enabled": true,
  "nav": {
    "section": "Infrastructure",
    "order": 10,
    "items": [
      {
        "path": "",
        "label": "System Monitor",
        "icon": "activity",
        "end": false,
        "documentTitle": "System Monitor"
      }
    ]
  }
}
```

Rules:

- `id` matches `^[a-z0-9]+(?:-[a-z0-9]+)*$` and the directory name.
- `pythonPackage` matches `^[a-z][a-z0-9_]*$` and is not a Python keyword.
- `routeBase` is an absolute kebab-case path such as `/system-monitor`. `/` and `/settings` are reserved by the shell, including paths under `/settings/`.
- `apiPrefix` starts with `/api/` and cannot be `/api`. `/api/health` is reserved by the platform.
- `routeBase`, `apiPrefix`, and nav paths reject `\`, `%`, NUL, and `.` or `..` segments.
- Nav `path` is relative. An empty string is the project index page. `/details` is invalid; `details` is valid.
- `icon` must be one of: `activity`, `bot`, `boxes`, `database`, `folder`, `layout-dashboard`, `server`.
- `nav.items` contains at least one item, and paths inside one manifest are unique.
- Enabled projects cannot share `id`, `routeBase`, or `apiPrefix`. Package names may repeat because each project has an isolated import namespace.
- `legacyRouteBases` is an optional array of absolute paths. Each entry uses the same rules as `routeBase`. A legacy path must not equal or nest inside that project's `routeBase`, and it must not collide with another project's `routeBase` or legacy path. The shell redirects each legacy path, including child paths, to the project's `routeBase`.
- `legacyApiPrefix` is optional. The value `/api` is allowed only when `id` is `system-monitor`, so an existing client can keep calling `/api/overview` and the other monitoring paths. Any other project must use a namespaced prefix, and no project may use `legacyApiPrefix` to claim `/api/health`. The loader calls `build_router()` again and mounts that second router at `legacyApiPrefix`. The plugin must not hardcode either prefix.

`project.json` is parsed as JSON. Its values are not executed.

The same rules are implemented in `backend/app/modules/manifest.py` and `frontend/src/modules/loadProjects.ts`.

## 4. Frontend Entry Point Contract

`projects/{project-id}/frontend/index.tsx` default-exports:

```ts
import type { ProjectFrontendModule } from '@shell/modules/types'

const module: ProjectFrontendModule = {
  routes: [
    { index: true, element: <OverviewPage /> },
    { path: 'health/:projectId', element: <ProjectHealthPage /> },
  ],
}

export default module
```

Paths are relative to `routeBase`, so the example above matches `/system-monitor` and `/system-monitor/health/system-monitor`.

The shell alias `@shell` points at `frontend/src`. Project code may import shared layout primitives from `@shell/...`. It must not import the shell router, `AppShell`, or `Sidebar`, and it must not create its own `createBrowserRouter`.

`frontend/src/modules/loadProjects.ts` reads manifests with an eager Vite glob and page modules with a lazy glob. Both globs use forward slashes. The shell calls `loadDiscoveredProjects()` once, mounts each module under `routeBase` and uses its exported `routes` for page matching, and builds the Sidebar from `nav.items` through `buildProjectNavigation()`. A manifest error is shown in the shell and logged. It does not remove Settings. `/` redirects to the first enabled project. Project routes stay behind `React.lazy` and an error boundary that resets when the path changes. Module routes may include detail paths such as `health/:projectId` without adding sidebar entries; unmatched module paths show the shell’s not-found page.

Enabled projects must have `frontend/index.tsx`. Disabled projects are validated and then omitted.

## 5. Backend Plugin Contract

`projects/{project-id}/backend/{pythonPackage}/plugin.py` defines:

```python
from fastapi import APIRouter

def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(overview_router)
    return router
```

`build_router()` must return a new FastAPI `APIRouter` on every call. Route paths inside that router are relative (`/overview`, `/history`). The loader mounts one router at `apiPrefix`. When `legacyApiPrefix` is set, it calls `build_router()` again and mounts that second router at the legacy prefix. The plugin does not hardcode `/api` or `/api/system-monitor`.

The loader imports `{pythonPackage}.plugin` inside an isolated namespace derived from the project id and resolved path. It does not add project backends to `sys.path`; project-local imports should be relative. Multiple projects can use `src` or `app` without colliding with one another or the platform `app`. A failed batch removes only newly imported modules in the affected project namespaces.

### Optional Project Lifespan

Plugin 可額外提供 `lifespan(app)`，回傳非同步情境管理器。平台在 FastAPI
啟動時依專案排序進入，關閉時反向退出；後續專案啟動失敗也會退出先前
已啟動的專案。背景工作只能在 lifespan 內啟動，不可在匯入或 build_router
時啟動。未提供此介面的專案只掛載路由，無須修改。

同一專案的正式與相容 API 前綴只共用一次 plugin 生命週期，不會啟動兩次。
生命週期在每個 API worker 各自執行；需要單例背景工作的專案，必須自行
處理跨 worker 互斥與資源回收。平台不硬編碼個別專案的啟動指令。

Plugin route paths must stay under `apiPrefix`. A path such as `/../health` is rejected. Only HTTP routes are accepted.

These plugins are trusted local source. This is not a sandbox for uploaded code.

## 6. API Namespace Rules

Platform routes stay in `backend/app`. `GET /api/health` is one of them.

Project routes are mounted only at that project's `apiPrefix`:

| Manifest field | Example | Mounted path |
|---|---|---|
| `apiPrefix` | `/api/system-monitor` | prefix owned by the loader |
| router path | `/overview` | `GET /api/system-monitor/overview` |
| router path | `/history` | `GET /api/system-monitor/history` |

A project cannot choose an `apiPrefix` of `/api` or `/api/health`. `legacyApiPrefix: "/api"` is the one exception, and only `system-monitor` may set it. The loader computes every `HTTP method + full path` for both mounts and rejects duplicates, including duplicates against routes already on the FastAPI app such as `GET /api/health`. It also rejects two different prefixes that expand to the same path, such as `/api/team` + `/alpha/ping` and `/api/team/alpha` + `/ping`.

If any manifest, plugin, or route check fails, no project router from that batch is mounted.

## 7. Module Validation

Backend entry points:

- `load_project_manifest(project_dir)` reads one `project.json`.
- `discover_project_manifests(projects_root)` scans a projects directory.
- `register_project_routers(app, projects_root)` imports plugins and mounts routers.
- `default_repository_root()` is `Path(__file__).resolve().parents[3]` from `backend/app/modules/loader.py`, so it does not depend on the process working directory.
- `default_projects_root()` is `{repository}/projects`.

A missing projects directory discovers zero modules. A directory without `project.json` is skipped. `enabled: false` is still schema-checked, then ignored. Validation errors name the file, field, and project id.

Frontend validation lives in `loadProjects()` and uses the same field rules. Icon names are resolved only through `frontend/src/modules/icons.ts`.

## 8. Adding a New Project

A new project is a folder under `projects/`. It is not a second Vite app, React root, FastAPI application, or virtual environment.

Minimum layout:

```text
projects/my-project/
  project.json
  frontend/index.tsx
  backend/my_project/plugin.py
```

`project.json`:

```json
{
  "schemaVersion": 1,
  "id": "my-project",
  "name": "My Project",
  "description": "Short description shown by the project.",
  "pythonPackage": "my_project",
  "routeBase": "/my-project",
  "apiPrefix": "/api/my-project",
  "enabled": true,
  "nav": {
    "section": "Projects",
    "order": 30,
    "items": [
      {
        "path": "",
        "label": "Overview",
        "icon": "folder",
        "end": true,
        "documentTitle": "My Project"
      }
    ]
  }
}
```

`frontend/index.tsx`:

```tsx
import type { ProjectFrontendModule } from '@shell/modules/types'

const myProjectModule: ProjectFrontendModule = {
  routes: [{ index: true, element: <p>My Project</p> }],
}

export default myProjectModule
```

`backend/my_project/plugin.py`:

```python
from fastapi import APIRouter

def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/info")
    def read_info() -> dict[str, str]:
        return {"id": "my-project", "status": "ok"}

    return router
```

That plugin route is mounted at `GET /api/my-project/info`. The `/api/my-project` prefix comes from `apiPrefix`. Do not put the prefix inside `build_router()`.

Do not edit `Sidebar.tsx`, `frontend/src/router/router.tsx`, or `backend/app/main.py` to register the project. Those files already discover every valid folder under `projects/`.

### Required fields

`schemaVersion`, `id`, `name`, `pythonPackage`, `routeBase`, `apiPrefix`, and `nav` are required. `description` defaults to `""`. `enabled` defaults to `true`. `legacyRouteBases` and `legacyApiPrefix` are optional and are not part of a new project. `/api` as a legacy prefix is reserved for `system-monitor`.

### Naming

- Directory name and `id`: lowercase kebab-case, for example `my-project`.
- `pythonPackage`: a Python identifier such as `my_project`. It cannot contain hyphens and cannot be a keyword.
- `routeBase`: absolute kebab-case, for example `/my-project`. The shell owns `/` and `/settings`.
- `apiPrefix`: starts with `/api/` and is not `/api` or `/api/health`.
- Nav `path`: relative to `routeBase`. Use `""` for the index page and `reports` for `/my-project/reports`.

### Navigation and icons

`nav.section` groups sidebar links. `nav.order` sorts sections. `nav.items` needs at least one item, and paths inside one manifest must be unique. `icon` must be one of `activity`, `bot`, `boxes`, `database`, `folder`, `layout-dashboard`, `server`. The shell maps those names in `frontend/src/modules/icons.ts`. Adding an icon means updating that registry and the matching backend allowlist together.

`end: true` marks an exact NavLink match, which is appropriate for the index item. `documentTitle` sets the browser title for that item.

### Dependencies

Use the shared virtual environment at `backend/.venv`. Platform packages live in `backend/requirements.txt`. A project that needs extra packages lists them in `projects/{project-id}/backend/requirements.txt` and they are installed into the same environment. System Monitor adds `psutil`; the platform requirements apply shared version constraints.

Frontend code under `projects/` imports React through the aliases in `frontend/vite.config.ts` and `frontend/tsconfig.app.json`. Do not add a second `package.json` or `node_modules` inside a project. Shared layout components are imported from `@shell/...`.

### Restart and rebuild

Putting a folder in `projects/` does not attach it to an already running process. Vite discovers `project.json` and `frontend/index.tsx` when the dev server starts or when a production build runs. FastAPI discovers plugins when Uvicorn starts. After adding or changing a module:

1. Install any new Python requirements into `backend/.venv`.
2. Restart Uvicorn.
3. Restart `npm run dev`, or run `npm run build` for a production bundle.

This is not a hot-plug system. A running server does not pick up a new folder until it is restarted, and a production bundle does not include it until it is rebuilt.

### Errors

- An invalid manifest, a missing `frontend/index.tsx`, a missing plugin, a failed import, or a plugin that does not return an `APIRouter` fails that load and names the project. The backend refuses to finish startup. The frontend shell shows the discovery error and keeps Settings available.
- `enabled: false` is validated and then omitted from routes, navigation, and API registration.
- One project page that throws at runtime is caught by the shell's per-page error boundary. The sidebar and the other project stay available.
- Local plugins are trusted source in this repository. The loader does not claim to sandbox arbitrary third-party code.

### Validation rules

Enabled projects cannot share `id`, `routeBase`, `apiPrefix`, or a final `HTTP method + path`. Their `pythonPackage` values may match. `id` must equal the directory name, so two folders cannot claim the same id. Duplicate route bases and API prefixes are rejected. A plugin path that escapes its prefix, including a path that would cover `GET /api/health`, is rejected. If one project in the batch fails, none of that batch is mounted.

## 9. Current Development Status

目前 `projects/` 啟用的模組：

- `system-monitor` — System Monitor at `/system-monitor` and project health details at `/system-monitor/health/system-monitor`. `/homelab` redirects to the project base, preserving child paths. Monitoring APIs are mounted at `/api/system-monitor/...` and, for this project only, at the previous `/api/...` paths.

`GET /api/health` stays on the platform. Settings remains a shell page at `/settings`.

System Monitor 原始碼位於 `projects/system-monitor/backend/src/`，採用
`api/`、`collector/`、`database/` 三部分。`plugin.py` 僅提供平台掛載入口。
API 只查 SQLite，獨立採集器使用 `python -m src.collector`。

SQL 集中於 `database/repository.py`；連線與建表位於
`database/connection.py`、`database/schema.sql`。預設資料庫為
`data/system-monitor/metrics.db`，可透過 `A7LAS_METRICS_DB_PATH` 覆寫。
每三秒採集，目前 `None` 永久保留，可改成正整數天數；啟動時不清理，
運行滿 24 小時後才第一次清理。不遷移舊開發資料，API 格式以新設計為準。

採集器使用 OS 程序鎖；POSIX 使用 flock，Windows 使用 byte-range lock。
Linux unit 已改為 `python -m src.collector`，修改檔案不代表已部署到伺服器。

目前專案健康度的前端設計與路由保留，後端檢測 API 已移除，待共用 log
系統完成後重新串接。前端與新 API 的差異已列於
[System Monitor 後端](../projects/system-monitor/backend/README.md)。
