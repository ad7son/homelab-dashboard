# A7LAS Modular Project Showcase Platform

A7LAS is one web application that hosts more than one project. A shared React shell and a shared FastAPI process discover projects from `projects/`. Each project keeps its own pages, API routes, and manifest.

The first project is System Monitor, the Home Lab dashboard. It reports live CPU, memory, GPU, disk I/O and network metrics, historical charts.

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
deploy/systemd/                  Linux unit for the metrics collector
docs/project-module-spec.md      Module contract
docs/ai-collaboration.md         Course AI collaboration record
conftest.py                      Exposes project test helpers to pytest
pytest.ini                       Runs platform tests and project tests
```

## Frontend Shell

The shell provides the header, sidebar, page layout, settings route, and unknown-route page. It builds project links from each manifest `nav` block and project routes from `routeBase`. `/` redirects to the first enabled project's first page. Settings stays at `/settings`.

A page that throws is contained by the project error boundary. The shell and the other project stay available. An invalid manifest is reported and does not remove Settings.

## Backend Core

`backend/app/main.py` creates the FastAPI app, allows `GET` from `http://localhost:5173`, mounts `GET /api/health`, and then calls the project loader. It does not hardcode project imports.

The loader rejects duplicate ids, route bases, API prefixes, and final HTTP paths. A failed manifest or plugin aborts startup and names the project. These plugins are trusted source in this repository. The loader is not a sandbox for uploaded code.

## Project Modules

A module is a directory under `projects/` with `project.json`, `frontend/index.tsx`, and `backend/{pythonPackage}/plugin.py`. The directory name equals `id`. `pythonPackage` names the directory under `backend/` that contains `plugin.py`. System Monitor uses `src`; other projects may retain their own package name. The loader isolates each project, so matching package names do not collide.

`build_router()` returns a new `APIRouter` whose paths are relative, such as `/info`. The loader adds `apiPrefix`.

## Existing Modules

### System Monitor

- Id: `system-monitor`
- Pages: `/system-monitor` and `/system-monitor/health/system-monitor`
- Legacy base: `/homelab` redirects to `/system-monitor`, preserving child paths.
- API prefix: `/api/system-monitor`
- Legacy API prefix: `/api`, so older clients can keep calling `/api/overview` and the other monitoring paths
- Live overview polls about every 3 seconds. Project Health 前端設計保留；後端檢測 API 已移除，待共用 log 系統完成後重新串接。目前健康區塊顯示尚未啟用，並暫停健康檢測請求。
- Historical ranges are `15m`, `1h`, `24h`, and `7d`.
- The collector samples every 3 seconds; retention is currently unlimited and can be set to a positive number of days.
- The new backend stores basic information and dynamic metrics separately. No migration of development data is provided. The frontend maps the new API response to the existing dashboard and marks stale samples.

## System Monitor 後端結構

後端使用 `api/`、`collector/`、`database/` 三個資料夾。採集器每三秒
寫入 SQLite 的 `host_info` 與 `host_metrics`；兩個 API 只查資料庫。
基本資訊僅在採集器啟動時更新。目前 `RETENTION_DAYS = None`
表示永久保留，可改成正整數天數；運行滿 24 小時後第一次清理，不在啟動時清理。

架構、資料流與維護邊界見
[System Monitor 後端](projects/system-monitor/backend/README.md)。

## Installation

Use Windows PowerShell from the repository root. The commands below create the shared virtual environment if it does not exist yet.

```powershell
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt -r projects\system-monitor\backend\requirements.txt
cd frontend
npm install
```

`backend/requirements.txt` 會套用共用的 `backend/constraints.txt` 已驗證版本約束；專案依賴也在同一次安裝中解析。

On Linux, create the same shared environment with `python3 -m venv backend/.venv` and install the same requirements files into it. The collector unit expects that environment at `/srv/homelab-dashboard/backend/.venv`.

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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Interactive docs are at `http://localhost:8000/docs`. Restart Uvicorn after adding or changing a project plugin.

System Monitor API 由上方平台指令啟動；不再提供 `src.main:app`。

後端啟動時會透過 System Monitor plugin 自動管理採集器，不需另開第三個
終端機。關閉後端也會停止其管理的採集器；多 worker 只會有一個管理者。

需要獨立診斷時，仍可從儲存庫根目錄執行採集器（macOS／Linux）：

```bash
PYTHONPATH=projects/system-monitor/backend backend/.venv/bin/python -m src.collector
```


The collector remains a separate child process managed by the plugin. For standalone diagnosis in PowerShell:

```powershell
$env:PYTHONPATH = "projects\system-monitor\backend"
.\backend\.venv\Scripts\python.exe -m src.collector
```

The default database path is `backend/data/system-monitor.db`. `A7LAS_METRICS_DB_PATH` overrides it. Windows uses a byte-range file lock; systemd deployment remains Linux-only.

## Running Tests

From the repository root in PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest -v
```

The root `pytest.ini` collects `backend/tests` and tests under `projects/`. `conftest.py` exposes project test helpers; those helpers use the same isolated modules that the platform loads, avoiding duplicate sampling state.

Collector tests use temporary databases and simulated clocks; GPU hardware still needs validation on the deployment host.

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
| GET | `/api/system-monitor/history?range=15m` | System Monitor. `range` is `15m`, `1h`, `24h`, or `7d`. |

The same System Monitor paths are also mounted at `/api/overview` and `/api/history`. Query parameters and response schemas match the namespaced routes. `GET /api/health` is not one of those project routes.

`/overview` returns `info` and `metrics`, including the real sample timestamp. `/history` supports the preset range or a custom `start_ms` / `end_ms` window. The frontend adapts this schema at the request boundary and uses the sample timestamp to detect stale data.

## Linux Deployment Notes

These steps apply to Linux only. They were not run from this Windows workspace, and this repository change does not reload a live server.

The collector unit in `deploy/systemd/a7las-metrics-collector.service` keeps the existing user, group, restart policy, database path, and `/srv` mount requirement. Its working directory and module path now match the moved package:

```text
WorkingDirectory=/srv/homelab-dashboard/projects/system-monitor/backend
Environment=A7LAS_METRICS_DB_PATH=/srv/a7las/data/system-monitor.db
ExecStart=/srv/homelab-dashboard/backend/.venv/bin/python -m src.collector
```

The interpreter remains the shared virtual environment. The working directory puts `src` on Python's module path. The collector uses the three-second interval and configurable retention in `src/config.py`; the unit now points to the new development database filename.

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
- The systemd unit requires Linux. Windows collector locking uses the OS byte-range lock and still needs validation on Windows.
- The collector unit in this repository was updated. A live Linux service was not reloaded from this workspace.
- The repository root contains a file named `exit`. It is a saved diff dump from commit `d2ed581`. It is not part of the application.
