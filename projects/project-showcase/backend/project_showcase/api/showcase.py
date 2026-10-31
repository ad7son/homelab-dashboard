"""Read-only Project Showcase info route.

The route path is ``/info``. The platform loader adds ``apiPrefix``.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from project_showcase.schemas.showcase import ShowcaseInfo

router = APIRouter()

_LOADED_MESSAGE = "Project module loaded successfully"


def manifest_path() -> Path:
    """Return ``projects/project-showcase/project.json``.

    ``api/showcase.py`` lives four levels below that directory:
    ``api`` -> ``project_showcase`` -> ``backend`` -> ``project-showcase``.
    """
    return Path(__file__).resolve().parents[3] / "project.json"


def get_showcase_info() -> ShowcaseInfo:
    """Build the info payload from ``project.json``.

    ``status`` and ``message`` describe this read. The id, name, and
    description are taken from the manifest so they are not copied here.
    """
    path = manifest_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Project manifest was not found: {path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Project manifest is not valid JSON: {path}",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Project manifest could not be read: {path}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=500,
            detail=f"Project manifest must be a JSON object: {path}",
        )

    project_id = payload.get("id")
    name = payload.get("name")
    description = payload.get("description", "")
    if not isinstance(project_id, str) or project_id == "":
        raise HTTPException(status_code=500, detail="Project manifest id is missing")
    if not isinstance(name, str) or name == "":
        raise HTTPException(status_code=500, detail="Project manifest name is missing")
    if not isinstance(description, str):
        raise HTTPException(
            status_code=500,
            detail="Project manifest description must be a string",
        )

    return ShowcaseInfo(
        id=project_id,
        name=name,
        description=description,
        status="ok",
        message=_LOADED_MESSAGE,
    )


@router.get("/info", response_model=ShowcaseInfo)
def read_showcase_info() -> ShowcaseInfo:
    """Return this module's manifest identity and a successful load status."""
    return get_showcase_info()
