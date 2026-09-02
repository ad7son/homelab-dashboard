from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cpu, disk, memory, network, overview, system

app = FastAPI(title="Home Lab Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(overview.router, prefix="/api", tags=["overview"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(cpu.router, prefix="/api", tags=["cpu"])
app.include_router(memory.router, prefix="/api", tags=["memory"])
app.include_router(disk.router, prefix="/api", tags=["disk"])
app.include_router(network.router, prefix="/api", tags=["network"])
