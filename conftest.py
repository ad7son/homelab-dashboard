"""Put each project's backend directory on sys.path before collection.

This does not import plugins. Paths come from project.json and are removed
from consideration when the manifest cannot be parsed. Nothing here is
Windows-specific.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def pytest_configure(config: object) -> None:
    del config
    projects_root = ROOT / "projects"
    if not projects_root.is_dir():
        return
    for project_dir in sorted(path for path in projects_root.iterdir() if path.is_dir()):
        manifest_path = project_dir / "project.json"
        if not manifest_path.is_file():
            continue
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        package = payload.get("pythonPackage")
        if not isinstance(package, str) or package == "":
            continue
        backend_dir = project_dir / "backend"
        if not (backend_dir / package).is_dir():
            continue
        entry = str(backend_dir.resolve())
        if entry not in sys.path:
            sys.path.insert(0, entry)
