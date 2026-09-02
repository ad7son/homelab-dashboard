# Home Lab Dashboard

A read-only web dashboard for monitoring a Home Lab server. V1 focuses on real-time system metrics with a clean separation between a FastAPI backend and a React frontend.

## V1 Features

- **System information** — hostname, OS, kernel, architecture, uptime
- **CPU metrics** — usage, cores, frequency, temperature (when available), load average
- **Memory metrics** — RAM and swap usage
- **Storage** — mounted filesystem usage with a detailed storage list
- **Network** — interface, local IPv4, download/upload rates
- **Auto-refresh** — dashboard polls every ~3 seconds with connection status (Online / Unstable / Offline)
- **Graceful degradation** — unavailable optional metrics display as N/A

## Architecture

```text
Ubuntu/macOS system
        ↓
      psutil
        ↓
 Backend services  →  Pydantic schemas  →  FastAPI endpoints
                                                ↓
                                          /api/overview
                                                ↓
                                    frontend api.ts
                                                ↓
                                    useSystemOverview hook
                                                ↓
                                      Dashboard + UI components
```

- **Backend**: Thin API routes delegate to service modules that collect metrics via psutil.
- **Frontend**: A single custom hook manages polling and connection state; UI components receive data via props.

## Technology Stack

| Layer    | Technologies                          |
|----------|---------------------------------------|
| Frontend | React, TypeScript, Vite, standard CSS |
| Backend  | Python, FastAPI, Uvicorn, psutil      |
| Testing  | pytest, httpx (TestClient)            |

## Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.9+

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Frontend Setup

```bash
cd frontend
npm install
```

## Running Locally

Start the backend (from `backend/`):

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Start the frontend (from `frontend/`):

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` requests to the backend at `http://localhost:8000`.

## API Endpoints

| Method | Path            | Description                    |
|--------|-----------------|--------------------------------|
| GET    | `/api/overview` | All V1 metrics (primary)       |
| GET    | `/api/system`   | System information             |
| GET    | `/api/cpu`      | CPU metrics                    |
| GET    | `/api/memory`   | Memory and swap                |
| GET    | `/api/disks`    | Mounted filesystems            |
| GET    | `/api/network`  | Network interface and rates    |

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Running Tests

Backend tests (from `backend/`):

```bash
source .venv/bin/activate
pytest
```

Frontend type-check and production build (from `frontend/`):

```bash
npm run build
```

## Platform Notes

- **Production target**: Ubuntu Linux Home Lab server
- **Development**: macOS is supported; some optional metrics may show **N/A** on macOS (e.g. CPU temperature, network throughput on the first sample)
- Network download/upload rates require at least two API samples before values appear

## Future Roadmap (not in V1)

- Docker / container monitoring
- Historical metrics and charts
- Authentication and multi-user access
- Alerts and notifications
- Production deployment (Docker Compose, Nginx, HTTPS)
- Minecraft server integration
