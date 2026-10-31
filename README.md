# A7LAS Modular Project Showcase Platform

A7LAS is one web application that hosts more than one project. A shared React shell and a shared FastAPI process discover projects from `projects/`. Each project keeps its own pages, API routes, and manifest.

The first project is System Monitor, the Home Lab dashboard. It reports live CPU, memory, storage, and network metrics, historical charts, and selected systemd services. The second project is Project Showcase, a small read-only module that demonstrates the same discovery path.

## System Architecture

```text
projects/*/project.json
        │
        ├── frontend/*/index.tsx ──► Vite shell (sidebar, router, layout)
        │
        └── backend/*/plugin.py ──► FastAPI (health + mounted project routers)
                                        │
                                        └── system-monitor collector
                                              SQLite metrics.db
```

- The shell reads every `projects/*/project.json` and lazy-loads `projects/*/frontend/index.tsx`.
- The API process reads the same manifests, imports each `build_router()`, and mounts it at that project's `apiPrefix`.
- Project code does not edit the sidebar, the shared router, or `backend/app/main.py`.
- Discovery runs when Vite starts or builds, and when FastAPI starts. A new folder is not attached to an already running process.

## Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend shell | React 19, TypeScript, Vite, React Router 7, standard CSS |
| System Monitor charts | Recharts |
| Backend | Python 3.12, FastAPI, Pydantic, Uvicorn |
| System metrics | psutil, installed for the System Monitor module |
| History | SQLite, written by the System Monitor collector |
| Tests | pytest, FastAPI TestClient, httpx |

There is one Node app in `frontend/` and one virtual environment in `backend/.venv`. Project folders do not have their own Vite app or virtual environment.

## Directory Structure

```text
backend/                         Shared FastAPI app, health route, module loader
frontend/                        Shared Vite shell
projects/system-monitor/         Home Lab frontend, API, collector, and tests
projects/project-showcase/       Showcase frontend, read-only API, and tests
deploy/systemd/                  Linux unit for the metrics collector
docs/project-module-spec.md      Module contract
docs/ai-collaboration.md         Course AI collaboration record
conftest.py                      Adds each project backend to the pytest path
pytest.ini                       Runs platform tests and project tests
```

## Frontend Shell

The shell provides the header, sidebar, page layout, settings route, and unknown-route page. It builds project links from each manifest `nav` block and project routes from `routeBase`. `/` redirects to the first enabled project's first page. Settings stays at `/settings`.

A page that throws is contained by the project error boundary. The shell and the other project stay available. An invalid manifest is reported and does not remove Settings.

## Backend Core

`backend/app/main.py` creates the FastAPI app, allows `GET` from `http://localhost:5173`, mounts `GET /api/health`, and then calls the project loader. It does not import `system_monitor` or `project_showcase`.

The loader rejects duplicate ids, route bases, API prefixes, and final HTTP paths. A failed manifest or plugin aborts startup and names the project. These plugins are trusted source in this repository. The loader is not a sandbox for uploaded code.

## Project Modules

A module is a directory under `projects/` with `project.json`, `frontend/index.tsx`, and `backend/{pythonPackage}/plugin.py`. The directory name equals `id`. The Python package name uses underscores because a hyphenated directory cannot be imported.

`build_router()` returns a new `APIRouter` whose paths are relative, such as `/info`. The loader adds `apiPrefix`.

## Existing Modules

### System Monitor

- Id: `system-monitor`
- Pages: `/system-monitor` and `/system-monitor/services`
- Legacy pages: `/homelab` and `/homelab/services` redirect to the pages above
- API prefix: `/api/system-monitor`
- Legacy API prefix: `/api`, so older clients can keep calling `/api/overview` and the other monitoring paths
- Live overview polls about every 3 seconds. The services page polls about every 15 seconds.
- Historical ranges are `15m`, `1h`, `24h`, and `7d`.
- The collector samples every 30 seconds and keeps raw samples for 7 days.

### Project Showcase

- Id: `project-showcase`
- Page: `/project-showcase`
- API: `GET /api/project-showcase/info`
- The info payload reads `id`, `name`, and `description` from that project's `project.json`.
- The page shows a loading state, the response body, or a visible error. It does not invent a successful response.
- This module has no legacy route and no legacy API prefix.

## Installation

Use Windows PowerShell from the repository root. The commands below create the shared virtual environment if it does not exist yet.

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r projects\system-monitor\backend\requirements.txt -r projects\project-showcase\backend\requirements.txt
cd frontend
npm install
```

`projects/project-showcase/backend/requirements.txt` has no extra packages. It is included so a new environment installs every project requirements file the same way.

On Linux, create the same shared environment with `python3 -m venv backend/.venv` and install the same three requirements files into it. The collector unit expects that environment at `/srv/homelab-dashboard/backend/.venv`.

## Running Frontend

From `frontend/` in PowerShell:

```powershell
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`.

`npm run build` typechecks the shell and the project frontends, then writes a production bundle. Restart the dev server or rebuild after adding a project. The running dev server does not treat a new `projects/` folder as a hot-plug.

## Running Backend

From `backend/` in PowerShell, using the shared environment:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive docs are at `http://localhost:8000/docs`. Restart Uvicorn after adding or changing a project plugin.

The System Monitor collector is a separate process. From the repository root in PowerShell it can be started for a local database, but its file lock uses Linux `fcntl.flock` and will not take that lock on Windows:

```powershell
$env:PYTHONPATH = "projects\system-monitor\backend"
.\backend\.venv\Scripts\python.exe -m system_monitor.collector.metrics_collector
```

The default database path is `backend/data/metrics.db`. `A7LAS_METRICS_DB_PATH` overrides it. Windows does not provide systemd or `flock`.

## Running Tests

From the repository root in PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

The root `pytest.ini` collects `backend/tests` and tests under `projects/`. `conftest.py` adds each project's `backend/` directory to the Python path.

The collector lock test is skipped on Windows because it requires Linux `fcntl.flock`. That test is still part of the suite. Do not treat a skip as a pass.

From `frontend/`:

```powershell
npm run build
```

The tests do not call external internet services.

## Adding a New Project

1. Create `projects/{project-id}/` with `project.json`, `frontend/index.tsx`, and `backend/{pythonPackage}/plugin.py`.
2. Install any new Python requirements into `backend/.venv`.
3. Restart Uvicorn and the Vite dev server, or run `npm run build`.

Do not edit `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/router/router.tsx`, or `backend/app/main.py` for that project. The contract and a minimal example are in `docs/project-module-spec.md`.

## Module Manifest

`schemaVersion` is `1`. Required fields are `id`, `name`, `pythonPackage`, `routeBase`, `apiPrefix`, and `nav`. `enabled` defaults to true. Icons are limited to `activity`, `bot`, `boxes`, `database`, `folder`, `layout-dashboard`, and `server`.

`legacyRouteBases` and `legacyApiPrefix` exist for System Monitor compatibility. A new project should leave them unset. Only `system-monitor` may use `legacyApiPrefix` value `/api`.

## API Endpoints

| Method | Path | Owner |
| --- | --- | --- |
| GET | `/api/health` | Platform. Body includes `status` and `version`. |
| GET | `/api/system-monitor/overview` | System Monitor |
| GET | `/api/system-monitor/system` | System Monitor |
| GET | `/api/system-monitor/cpu` | System Monitor |
| GET | `/api/system-monitor/memory` | System Monitor |
| GET | `/api/system-monitor/disks` | System Monitor |
| GET | `/api/system-monitor/network` | System Monitor |
| GET | `/api/system-monitor/history?range=15m` | System Monitor. `range` is `15m`, `1h`, `24h`, or `7d`. |
| GET | `/api/system-monitor/services` | System Monitor |
| GET | `/api/project-showcase/info` | Project Showcase |

The same System Monitor paths are also mounted at `/api/overview`, `/api/system`, `/api/cpu`, `/api/memory`, `/api/disks`, `/api/network`, `/api/history`, and `/api/services`. Query parameters and response schemas match the namespaced routes. `GET /api/health` is not one of those project routes.

## Linux Deployment Notes

These steps apply to Linux only. They were not run from this Windows workspace, and this repository change does not reload a live server.

The collector unit in `deploy/systemd/a7las-metrics-collector.service` keeps the existing user, group, restart policy, database path, and `/srv` mount requirement. Its working directory and module path now match the moved package:

```text
WorkingDirectory=/srv/homelab-dashboard/projects/system-monitor/backend
Environment=A7LAS_METRICS_DB_PATH=/srv/a7las/data/metrics.db
ExecStart=/srv/homelab-dashboard/backend/.venv/bin/python -m system_monitor.collector.metrics_collector
```

The interpreter remains the shared virtual environment. The working directory puts `system_monitor` on Python's module path. The unit does not change the 30-second sample interval, the SQLite schema, the 7-day retention rule, or the `A7LAS_METRICS_DB_PATH` value. Those behaviors live in the collector code and the environment variable.

After copying the unit into systemd's unit directory, a Linux administrator can load it with:

```bash
sudo systemctl daemon-reload
sudo systemctl restart a7las-metrics-collector.service
sudo systemctl status a7las-metrics-collector.service
```

Confirm the service is active before treating the deployment as updated. This README does not record that those commands succeeded on a server.

## AI-Assisted Development

Cursor AI Coding Agent implemented the module loader, the System Monitor move, and the Project Showcase module from requirements written by the developer. The developer owns requirements, architecture choices, review, acceptance tests, and Git history. `docs/ai-collaboration.md` records the three commit stages and leaves room for prompt screenshots and manual test notes.

## Known Limitations

- Adding a project requires a backend restart and a frontend restart or rebuild.
- Settings is a shell placeholder. It does not save preferences.
- There is no authentication, alerting, or container monitoring.
- CORS allows `GET` from `http://localhost:5173` only.
- Service inventory reads systemd on Linux. Other platforms do not provide that inventory.
- Windows cannot run this repository's systemd unit or `fcntl.flock`. The collector lock test is skipped there.
- The collector unit in this repository was updated. A live Linux service was not reloaded from this workspace.
- The repository root contains a file named `exit`. It is a saved diff dump from commit `d2ed581`. It is not part of the application.
