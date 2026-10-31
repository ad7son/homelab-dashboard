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

`pythonPackage` is a separate Python identifier. A hyphenated directory cannot be imported, so `system-monitor` uses the package name `system_monitor`:

```text
projects/system-monitor/backend/system_monitor/plugin.py
```

Directories under `projects/` that do not contain `project.json` are ignored.

## 3. project.json Schema

Schema version is the integer `1`. Unknown fields are rejected. `enabled` defaults to `true`. `description` defaults to an empty string.

```json
{
  "schemaVersion": 1,
  "id": "system-monitor",
  "name": "Home Lab",
  "description": "Real-time system monitoring dashboard",
  "pythonPackage": "system_monitor",
  "routeBase": "/system-monitor",
  "apiPrefix": "/api/system-monitor",
  "legacyRouteBases": ["/homelab"],
  "legacyApiPrefix": "/api",
  "enabled": true,
  "nav": {
    "section": "Infrastructure",
    "order": 10,
    "items": [
      {
        "path": "",
        "label": "Home Lab",
        "icon": "server",
        "end": true,
        "documentTitle": "Home Lab"
      },
      {
        "path": "services",
        "label": "Services",
        "icon": "boxes",
        "documentTitle": "Services"
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
- Nav `path` is relative. An empty string is the project index page. `/services` is invalid; `services` is valid.
- `icon` must be one of: `activity`, `bot`, `boxes`, `database`, `folder`, `layout-dashboard`, `server`.
- `nav.items` contains at least one item, and paths inside one manifest are unique.
- Enabled projects cannot share `id`, `routeBase`, `apiPrefix`, or `pythonPackage`.
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
    { path: 'services', element: <ServicesPage /> },
  ],
}

export default module
```

Paths are relative to `routeBase`, so the example above is `/system-monitor` and `/system-monitor/services`.

The shell alias `@shell` points at `frontend/src`. Project code may import shared layout primitives from `@shell/...`. It must not import the shell router, `AppShell`, or `Sidebar`, and it must not create its own `createBrowserRouter`.

`frontend/src/modules/loadProjects.ts` reads manifests with an eager Vite glob and page modules with a lazy glob. Both globs use forward slashes. The shell calls `loadDiscoveredProjects()` once, builds routes from `routeBase` and `nav.items`, and builds the Sidebar from `buildProjectNavigation()`. A manifest error is shown in the shell and logged. It does not remove Settings. `/` redirects to the first enabled project. Project pages stay behind `React.lazy` and a per-page error boundary.

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

`build_router()` must return a new FastAPI `APIRouter` on every call. Route paths inside that router are relative (`/overview`, `/services`). The loader mounts one router at `apiPrefix`. When `legacyApiPrefix` is set, it calls `build_router()` again and mounts that second router at the legacy prefix. The plugin does not hardcode `/api` or `/api/system-monitor`.

The loader adds that project's `backend/` directory to `sys.path` and imports `{pythonPackage}.plugin`. Package names must be unique. If the same package is already imported from another location, loading fails. A failed batch removes the modules it imported and the `sys.path` entries it added.

Plugin route paths must stay under `apiPrefix`. A path such as `/../health` is rejected. Only HTTP routes are accepted.

These plugins are trusted local source. This is not a sandbox for uploaded code.

## 6. API Namespace Rules

Platform routes stay in `backend/app`. `GET /api/health` is one of them.

Project routes are mounted only at that project's `apiPrefix`:

| Manifest field | Example | Mounted path |
|---|---|---|
| `apiPrefix` | `/api/system-monitor` | prefix owned by the loader |
| router path | `/overview` | `GET /api/system-monitor/overview` |
| router path | `/services` | `GET /api/system-monitor/services` |

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

1. Create `projects/{project-id}/project.json` using schema version 1.
2. Add `frontend/index.tsx` that default-exports `{ routes }`.
3. Add `backend/{pythonPackage}/plugin.py` with `build_router()`.
4. Restart the Vite dev server and Uvicorn. Discovery is build-time on the frontend and startup-time on the backend. It is not hot-plug.

Do not edit `Sidebar.tsx`, `frontend/src/router/router.tsx`, or `backend/app/main.py` to register that project. Those files read the manifest and mount whatever `projects/` contains.

## 9. Current Development Status

Home Lab monitoring is the `system-monitor` project. The shell and `backend/app/main.py` load it through the module contract.

- `/system-monitor` and `/system-monitor/services` are the current pages. `/homelab` and `/homelab/services` redirect there because `legacyRouteBases` contains `/homelab`.
- Monitoring APIs are mounted at `/api/system-monitor/...` and, for this project only, at the previous `/api/...` paths. `GET /api/health` stays on the platform.
- The default SQLite file remains `<repository>/backend/data/metrics.db`. `A7LAS_METRICS_DB_PATH` still overrides it. The schema is unchanged.
- Linux `fcntl.flock` is imported only when the collector takes its process lock. The lock test is skipped on Windows. The collector implementation was not replaced with a Windows lock.
- `deploy/systemd/a7las-metrics-collector.service` still starts `python -m app.collector.metrics_collector`. That unit is intentionally unchanged in this commit and will not match the moved module until a later deployment update.

