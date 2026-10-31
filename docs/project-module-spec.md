# Project Module Specification

Commit 1 adds the module contract, validation, and loaders. The running Home Lab Dashboard still uses its existing static routes. A new project folder is not shown in the Sidebar yet, and it is not mounted by `backend/app/main.py`.

## 1. Modular Architecture

A7LAS is one React application and one FastAPI process.

- `frontend/` is the shared shell: layout, header, sidebar, and the Vite app.
- `backend/` is the shared FastAPI application, health endpoint, and module loader.
- `projects/{project-id}/` is one showcase module. It is source code inside this repository, not a separate npm package and not a separate virtual environment.

Adding a module later means adding a folder that matches this contract, then restarting the dev servers or rebuilding. Commit 1 does not wire that folder into the shell.

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
  "description": "System monitoring dashboard",
  "pythonPackage": "system_monitor",
  "routeBase": "/system-monitor",
  "apiPrefix": "/api/system-monitor",
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

`frontend/src/modules/loadProjects.ts` reads manifests with an eager Vite glob and page modules with a lazy glob. Both globs use forward slashes. `loadProjects()` and `buildProjectNavigation()` are ready for a later commit. Nothing in the current shell calls them, so they do not change the running dashboard.

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

`build_router()` must return a FastAPI `APIRouter`. Route paths inside that router are relative (`/overview`, `/services`). The loader mounts the router at `apiPrefix`.

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

A project cannot choose a prefix of `/api` or `/api/health`. The loader computes every `HTTP method + full path` and rejects duplicates, including duplicates against routes already on the FastAPI app. It also rejects two different prefixes that expand to the same path, such as `/api/team` + `/alpha/ping` and `/api/team/alpha` + `/ping`.

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

When the shell is connected in a later commit, the steps will be:

1. Create `projects/{project-id}/project.json` using schema version 1.
2. Add `frontend/index.tsx` that default-exports `{ routes }`.
3. Add `backend/{pythonPackage}/plugin.py` with `build_router()`.
4. Restart the Vite dev server and Uvicorn. Discovery is build-time on the frontend and startup-time on the backend. It is not hot-plug.

Do not edit `Sidebar.tsx`, `frontend/src/router/router.tsx`, or `backend/app/main.py` to register that project. Those files still own the current dashboard and are intentionally unchanged in Commit 1.

Until the shell calls `loadProjects()` and `main.py` calls `register_project_routers()`, a new folder has no effect on the running UI or API.

## 9. Current Development Status

This is Commit 1 of 3.

- Manifest schema, backend discovery, backend router loader, frontend types, frontend discovery, and the icon registry exist.
- `backend/app/main.py` still registers the existing monitoring routers statically.
- The React router and Sidebar still point at `/homelab`, `/homelab/services`, and `/settings`.
- There is no `projects/system-monitor` folder yet. Home Lab monitoring has not been moved.
- `legacyRouteBases` and `legacyApiPrefix` are not part of schema version 1.

The next commit can move the current monitoring feature into `projects/system-monitor` and switch the shell over to the loaders. That move should keep the existing pytest coverage, account for `metrics_database.py` deriving its default SQLite path from `Path.parents`, and treat `fcntl` in the metrics collector as Linux-only.
