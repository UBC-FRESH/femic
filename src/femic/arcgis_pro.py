"""Shared ArcGIS Pro Python resolution and subprocess helpers."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

DEFAULT_ARCGIS_PRO_PYTHON_CANDIDATES: tuple[Path, ...] = (
    Path(r"C:/Program Files/ArcGIS/Pro/bin/Python/Scripts/propy.bat"),
    Path(r"C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe"),
)
BLANK_APRX_RELATIVE_PATH = Path(
    "Resources/ArcToolBox/Services/routingservices/data/Blank.aprx"
)


def find_arcgis_pro_python() -> Path | None:
    """Return the first usable ArcGIS Pro Python entrypoint."""
    candidates = [
        Path(os.environ.get("ARCGIS_PRO_PYTHON", "")).expanduser()
        if os.environ.get("ARCGIS_PRO_PYTHON")
        else None,
        Path(os.environ.get("ARCGIS_PRO_PYTHON_WRAPPER", "")).expanduser()
        if os.environ.get("ARCGIS_PRO_PYTHON_WRAPPER")
        else None,
        *DEFAULT_ARCGIS_PRO_PYTHON_CANDIDATES,
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def find_arcgis_blank_project_template(
    python_path: Path | None = None,
) -> Path | None:
    """Resolve the ArcGIS Pro blank project template path when available."""
    explicit_default = Path(
        r"C:/Program Files/ArcGIS/Pro/Resources/ArcToolBox/Services/routingservices/data/Blank.aprx"
    )
    if explicit_default.exists():
        return explicit_default
    resolved_python = python_path or find_arcgis_pro_python()
    if resolved_python is None:
        return None
    for ancestor in resolved_python.parents:
        candidate = ancestor / BLANK_APRX_RELATIVE_PATH
        if candidate.exists():
            return candidate
    return None


def run_arcgis_python(
    *, code: str, args: list[str]
) -> subprocess.CompletedProcess[str]:
    """Run a short ArcGIS Pro Python snippet via propy/python.exe."""
    python_path = find_arcgis_pro_python()
    if python_path is None:
        raise FileNotFoundError("ArcGIS Pro Python not found.")
    if python_path.suffix.lower() == ".bat":
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as script_file:
            script_file.write(code)
            script_path = Path(script_file.name)
        cmd = [str(python_path), str(script_path), *args]
        last_error: subprocess.CalledProcessError | None = None
        try:
            for attempt in range(3):
                try:
                    return subprocess.run(
                        cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as exc:
                    last_error = exc
                    if exc.returncode != 246 or attempt == 2:
                        raise
                    time.sleep(2.0 * (attempt + 1))
            assert last_error is not None
            raise last_error
        finally:
            script_path.unlink(missing_ok=True)
    cmd = [str(python_path), "-c", code, *args]
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
