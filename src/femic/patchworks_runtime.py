"""Patchworks runtime helpers for Patchworks Matrix Builder execution."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from typing import Any, Literal
import xml.etree.ElementTree as et

import yaml

DEFAULT_LICENSE_ENV = "SPS_LICENSE_SERVER"
DEFAULT_PATCHWORKS_JAR_PATH = Path("reference/Patchworks/patchworks.jar")
DEFAULT_PATCHWORKS_CONFIG_PATH = Path("config/patchworks.runtime.yaml")
DEFAULT_PATCHWORKS_LOG_DIR = Path("vdyp_io/logs")
FATAL_MATRIX_STDERR_PATTERNS = (
    "no mrsidget2_64 in java.library.path",
    "not licensed or no connection to license server",
    "couldn't create component peer",
    "$display is set correctly",
    "sps home directory not found, installation not complete",
    "ip helper library getadaptersaddresses function failed",
)
QMD_ACCOUNT_PATTERN = re.compile(
    r"^feature\.QMD\.(managed|unmanaged)\.([A-Za-z0-9_.]+)$"
)
HEIGHT_ACCOUNT_PATTERN = re.compile(
    r"^feature\.Height\.(managed|unmanaged)\.([A-Za-z0-9_.]+)$"
)
STEMS_PER_HA_ACCOUNT_PATTERN = re.compile(
    r"^feature\.StemsPerHa\.(managed|unmanaged)\.([A-Za-z0-9_.]+)$"
)
STAND_STRUCTURE_BASIC_ACCOUNT_PATTERN = re.compile(
    r"^feature\.(MAI|BasalArea000|DBHg000|SPH000|StemCount000|StemCount125|StemCount175)\.managed\.([A-Za-z0-9_.]+)$"
)
HARVESTED_VOLUME_ACCOUNT_PATTERN = re.compile(
    r"^product\.HarvestedVolume\.managed\..+\.([A-Z0-9_]+)$"
)
AU_EQ_PATTERN = re.compile(r"\bAU eq (\d+)\b")


@dataclass(frozen=True)
class PatchworksRuntimeConfig:
    """Resolved runtime settings for Patchworks execution."""

    config_path: Path
    jar_path: Path
    wine_prefix: Path | None
    license_env: str
    license_value: str
    spshome: str
    use_xvfb: bool
    fragments_path: Path
    matrix_output_dir: Path
    forestmodel_xml_path: Path
    accounts_exclude_regex: tuple[str, ...]
    harvested_volume_utilization_by_treatment: dict[str, float]
    auto_close_window_on_success: bool
    auto_close_settle_seconds: float
    auto_close_timeout_seconds: float


@dataclass(frozen=True)
class PatchworksPreflightResult:
    """Preflight report for Patchworks runtime execution."""

    config: PatchworksRuntimeConfig
    launcher_executable: str | None
    host_mode: str
    license_host: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return `True` when preflight checks reported no errors."""
        return not self.errors


@dataclass(frozen=True)
class PatchworksExecutionResult:
    """Execution outputs for a Patchworks command launch."""

    run_id: str
    command: tuple[str, ...]
    command_string: str
    returncode: int
    stdout_log_path: Path
    stderr_log_path: Path
    manifest_path: Path
    failures: tuple[str, ...]


@dataclass(frozen=True)
class PatchworksBlocksBuildResult:
    """Outputs from preparing a 1:1 stand:block blocks dataset."""

    model_dir: Path
    fragments_shapefile_path: Path
    blocks_shapefile_path: Path
    topology_csv_path: Path | None
    block_count: int
    stand_id_field: str
    topology_edge_count: int
    topology_radius_m: float


class PatchworksConfigError(ValueError):
    """Invalid Patchworks runtime config."""


PatchworksTopologyBackend = Literal["python", "patchworks-raster"]


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise PatchworksConfigError(
            f"Patchworks config must contain a top-level object: {path}"
        )
    return payload


def _as_path(value: Any, *, field: str, base_dir: Path) -> Path:
    if value is None or not str(value).strip():
        raise PatchworksConfigError(f"Missing required field: {field}")
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _as_optional_path(value: Any, *, base_dir: Path) -> Path | None:
    if value is None or not str(value).strip():
        return None
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def load_patchworks_runtime_config(path: Path) -> PatchworksRuntimeConfig:
    """Load and validate Patchworks runtime YAML/JSON config."""

    resolved_path = path.expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"Patchworks config not found: {resolved_path}")

    payload = _load_yaml_or_json(resolved_path)
    patchworks = payload.get("patchworks")
    matrix_builder = payload.get("matrix_builder")
    if not isinstance(patchworks, dict):
        raise PatchworksConfigError("Missing required section: patchworks")
    if not isinstance(matrix_builder, dict):
        raise PatchworksConfigError("Missing required section: matrix_builder")

    base_dir = resolved_path.parent
    jar_path = _as_path(
        patchworks.get("jar_path", DEFAULT_PATCHWORKS_JAR_PATH),
        field="patchworks.jar_path",
        base_dir=base_dir,
    )
    wine_prefix = _as_optional_path(patchworks.get("wine_prefix"), base_dir=base_dir)

    license_env = str(patchworks.get("license_env", DEFAULT_LICENSE_ENV)).strip()
    if not license_env:
        raise PatchworksConfigError("patchworks.license_env must not be empty")

    raw_license_value = patchworks.get("license_value")
    if raw_license_value is None or not str(raw_license_value).strip():
        license_value = str(os.environ.get(license_env, "")).strip()
    else:
        license_value = str(raw_license_value).strip()
    if not license_value:
        raise PatchworksConfigError(
            "Missing license value: set patchworks.license_value or export "
            f"{license_env} in environment"
        )
    spshome = str(patchworks.get("spshome", os.environ.get("SPSHOME", ""))).strip()
    if not spshome:
        raise PatchworksConfigError(
            "Missing Patchworks install home: set patchworks.spshome or export SPSHOME"
        )
    use_xvfb = bool(patchworks.get("use_xvfb", False))

    fragments_path = _as_path(
        matrix_builder.get("fragments_path"),
        field="matrix_builder.fragments_path",
        base_dir=base_dir,
    )
    matrix_output_dir = _as_path(
        matrix_builder.get("output_dir"),
        field="matrix_builder.output_dir",
        base_dir=base_dir,
    )
    forestmodel_xml_path = _as_path(
        matrix_builder.get("forestmodel_xml_path"),
        field="matrix_builder.forestmodel_xml_path",
        base_dir=base_dir,
    )
    raw_accounts_exclude_regex = matrix_builder.get("accounts_exclude_regex", [])
    accounts_exclude_regex: tuple[str, ...]
    if raw_accounts_exclude_regex is None:
        accounts_exclude_regex = ()
    elif isinstance(raw_accounts_exclude_regex, list):
        values = [
            str(value).strip()
            for value in raw_accounts_exclude_regex
            if str(value).strip()
        ]
        accounts_exclude_regex = tuple(values)
    else:
        raise PatchworksConfigError(
            "matrix_builder.accounts_exclude_regex must be a list of regex strings"
        )
    raw_harvest_utilization = matrix_builder.get(
        "harvested_volume_utilization_by_treatment", {}
    )
    harvested_volume_utilization_by_treatment: dict[str, float] = {}
    if raw_harvest_utilization is None:
        harvested_volume_utilization_by_treatment = {}
    elif isinstance(raw_harvest_utilization, dict):
        for raw_treatment, raw_factor in raw_harvest_utilization.items():
            treatment = str(raw_treatment).strip().upper()
            if not treatment:
                raise PatchworksConfigError(
                    "matrix_builder.harvested_volume_utilization_by_treatment keys "
                    "must not be empty"
                )
            try:
                factor = float(raw_factor)
            except (TypeError, ValueError) as exc:
                raise PatchworksConfigError(
                    "matrix_builder.harvested_volume_utilization_by_treatment values "
                    f"must be numeric (bad value for {treatment!r}: {raw_factor!r})"
                ) from exc
            if factor < 0.0:
                raise PatchworksConfigError(
                    "matrix_builder.harvested_volume_utilization_by_treatment values "
                    f"must be >= 0.0 (bad value for {treatment!r}: {factor!r})"
                )
            harvested_volume_utilization_by_treatment[treatment] = factor
    else:
        raise PatchworksConfigError(
            "matrix_builder.harvested_volume_utilization_by_treatment must be a "
            "mapping/object"
        )
    auto_close_window_on_success = bool(
        matrix_builder.get("auto_close_window_on_success", False)
    )
    try:
        auto_close_settle_seconds = float(
            matrix_builder.get("auto_close_settle_seconds", 2.0)
        )
    except (TypeError, ValueError) as exc:
        raise PatchworksConfigError(
            "matrix_builder.auto_close_settle_seconds must be numeric"
        ) from exc
    if auto_close_settle_seconds < 0.0:
        raise PatchworksConfigError(
            "matrix_builder.auto_close_settle_seconds must be >= 0.0"
        )
    try:
        auto_close_timeout_seconds = float(
            matrix_builder.get("auto_close_timeout_seconds", 10.0)
        )
    except (TypeError, ValueError) as exc:
        raise PatchworksConfigError(
            "matrix_builder.auto_close_timeout_seconds must be numeric"
        ) from exc
    if auto_close_timeout_seconds < 0.0:
        raise PatchworksConfigError(
            "matrix_builder.auto_close_timeout_seconds must be >= 0.0"
        )

    return PatchworksRuntimeConfig(
        config_path=resolved_path,
        jar_path=jar_path,
        wine_prefix=wine_prefix,
        license_env=license_env,
        license_value=license_value,
        spshome=spshome,
        use_xvfb=use_xvfb,
        fragments_path=fragments_path,
        matrix_output_dir=matrix_output_dir,
        forestmodel_xml_path=forestmodel_xml_path,
        accounts_exclude_regex=accounts_exclude_regex,
        harvested_volume_utilization_by_treatment=(
            harvested_volume_utilization_by_treatment
        ),
        auto_close_window_on_success=auto_close_window_on_success,
        auto_close_settle_seconds=auto_close_settle_seconds,
        auto_close_timeout_seconds=auto_close_timeout_seconds,
    )


def parse_license_server(value: str) -> tuple[str, str]:
    """Parse `user@server` license format."""

    normalized = value.strip()
    if "@" not in normalized:
        raise PatchworksConfigError(
            "License value must use '<username>@<server>' format"
        )
    username, host = normalized.split("@", 1)
    username = username.strip()
    host = host.strip()
    if not username or not host:
        raise PatchworksConfigError(
            "License value must include both username and server host"
        )
    return username, host


def is_windows_host() -> bool:
    """Return true when running on native Windows."""

    return os.name == "nt"


def find_wine_executable() -> str | None:
    """Return preferred Wine executable path/name on PATH."""

    for candidate in ("wine64", "wine"):
        found = shutil_which(candidate)
        if found:
            return found
    return None


def shutil_which(name: str) -> str | None:
    """Wrapper for monkeypatch-friendly which lookup."""

    from shutil import which

    return which(name)


def to_wine_windows_path(path: Path) -> str:
    """Map absolute path to a Windows-style path for command arguments."""

    text = str(path)
    if len(text) >= 2 and text[1] == ":":
        return text
    normalized = str(path.expanduser().resolve())
    return "Z:" + normalized.replace("/", "\\")


def infer_patchworks_model_dir(config: PatchworksRuntimeConfig) -> Path:
    """Infer Patchworks model root from runtime input/output paths."""

    known_model_subdirs = {
        "analysis",
        "blocks",
        "data",
        "imagery",
        "misc",
        "roads",
        "scenarios",
        "scripts",
        "tracks",
        "yield",
    }
    # Strong signal: `.../tracks` and `.../yield` siblings define model root.
    if (
        config.matrix_output_dir.name.lower() == "tracks"
        and config.forestmodel_xml_path.parent.name.lower() == "yield"
        and config.matrix_output_dir.parent.resolve()
        == config.forestmodel_xml_path.parent.parent.resolve()
    ):
        return config.matrix_output_dir.parent.resolve()
    # K3Z validated layout: fragments and ForestModel XML live together under an
    # `output/patchworks_k3z*_validated/` directory, while compiled tracks stay
    # under `models/.../tracks*`.
    if (
        config.fragments_path.parent.name.lower() == "fragments"
        and config.forestmodel_xml_path.parent.resolve()
        == config.fragments_path.parent.parent.resolve()
        and config.matrix_output_dir.name.lower().startswith("tracks")
    ):
        return config.matrix_output_dir.parent.resolve()

    candidates: list[Path] = []
    for candidate in (
        config.fragments_path.parent,
        config.matrix_output_dir,
        config.forestmodel_xml_path.parent,
    ):
        if candidate.name.lower() in known_model_subdirs:
            candidates.append(candidate.parent)
        else:
            candidates.append(candidate)

    unique_candidates = {path.resolve() for path in candidates}
    if len(unique_candidates) == 1:
        return next(iter(unique_candidates))

    common = Path(os.path.commonpath([str(path) for path in unique_candidates]))
    if common.name.lower() in known_model_subdirs:
        return common.parent
    return common


def build_matrix_builder_command_string(config: PatchworksRuntimeConfig) -> str:
    """Build the Windows CMD command to run Matrix Builder."""

    jar_dir = to_wine_windows_path(config.jar_path.parent)
    fragments = to_wine_windows_path(config.fragments_path)
    output_dir = to_wine_windows_path(config.matrix_output_dir)
    forestmodel_xml = to_wine_windows_path(config.forestmodel_xml_path)
    spshome = config.spshome
    lib_dir = f"{spshome}\\lib"
    return (
        f'cd /d "{jar_dir}" && '
        f'set "SPSHOME={spshome}" && '
        f'set "PATH=%PATH%;{spshome};{lib_dir}" && '
        f'java "-Djava.library.path={lib_dir}" -jar patchworks.jar '
        "ca.spatial.tracks.builder.Process "
        f'"{fragments}" "{output_dir}" "{forestmodel_xml}"'
    )


def build_appchooser_command_string(config: PatchworksRuntimeConfig) -> str:
    """Build Windows CMD command to open Patchworks app chooser."""

    jar_dir = to_wine_windows_path(config.jar_path.parent)
    spshome = config.spshome
    lib_dir = f"{spshome}\\lib"
    return (
        f'cd /d "{jar_dir}" && '
        f'set "SPSHOME={spshome}" && '
        f'set "PATH=%PATH%;{spshome};{lib_dir}" && '
        f'java "-Djava.library.path={lib_dir}" -jar patchworks.jar'
    )


def build_beanshell_command_string(
    *,
    config: PatchworksRuntimeConfig,
    script_path: Path,
    script_args: tuple[str, ...] = (),
) -> str:
    """Build Windows CMD command to run a BeanShell script via IProperties."""

    jar_dir = to_wine_windows_path(config.jar_path.parent)
    script = to_wine_windows_path(script_path)
    spshome = config.spshome
    lib_dir = f"{spshome}\\lib"
    args_fragment = " ".join(f'"{arg}"' for arg in script_args)
    return (
        f'cd /d "{jar_dir}" && '
        f'set "SPSHOME={spshome}" && '
        f'set "PATH=%PATH%;{spshome};{lib_dir}" && '
        f'java "-Djava.library.path={lib_dir}" -jar patchworks.jar '
        f'ca.spatial.util.IProperties BeanShell "{script}"'
        f" {args_fragment}".rstrip()
    )


def run_patchworks_preflight(
    *,
    config: PatchworksRuntimeConfig,
    require_matrix_inputs: bool = True,
) -> PatchworksPreflightResult:
    """Run preflight checks before Patchworks execution."""

    errors: list[str] = []
    warnings: list[str] = []
    if not str(os.environ.get("SPSHOME", "")).strip():
        warnings.append(
            "SPSHOME environment variable is not set; this usually indicates "
            "Patchworks is not correctly installed/registered on this host."
        )

    windows_host = is_windows_host()
    launcher_executable = (
        shutil_which("java") if windows_host else find_wine_executable()
    )
    if launcher_executable is None:
        if windows_host:
            errors.append("java not found on PATH")
        else:
            errors.append("wine64/wine not found on PATH")

    if not config.jar_path.exists():
        errors.append(f"Patchworks jar not found: {config.jar_path}")

    if require_matrix_inputs:
        if not config.fragments_path.exists():
            errors.append(f"Fragments dataset not found: {config.fragments_path}")

        if not config.forestmodel_xml_path.exists():
            errors.append(f"ForestModel XML not found: {config.forestmodel_xml_path}")

    license_host: str | None = None
    try:
        _, license_host = parse_license_server(config.license_value)
    except PatchworksConfigError as exc:
        errors.append(str(exc))

    if launcher_executable is not None:
        java_check_cmd = (
            [launcher_executable, "-version"]
            if windows_host
            else [launcher_executable, "cmd", "/c", "java -version"]
        )
        java_check = subprocess.run(
            java_check_cmd,
            capture_output=True,
            text=True,
            env=_build_base_env(config),
            check=False,
        )
        if java_check.returncode != 0:
            if windows_host:
                errors.append(
                    "Java runtime unavailable on host (command `java -version` failed)"
                )
            else:
                errors.append(
                    "Java runtime unavailable inside Wine context "
                    "(command `java -version` failed)"
                )

    return PatchworksPreflightResult(
        config=config,
        launcher_executable=launcher_executable,
        host_mode="windows" if windows_host else "wine",
        license_host=license_host,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _build_base_env(config: PatchworksRuntimeConfig) -> dict[str, str]:
    env = dict(os.environ)
    env[config.license_env] = config.license_value
    env["SPSHOME"] = config.spshome
    lib_dir = f"{config.spshome}\\lib"
    env["PATH"] = env.get("PATH", "") + f";{config.spshome};{lib_dir}"
    if config.wine_prefix is not None:
        env["WINEPREFIX"] = str(config.wine_prefix)
    return env


def _build_windows_java_command(
    *, launcher_executable: str, config: PatchworksRuntimeConfig, interactive: bool
) -> tuple[str, ...]:
    lib_dir = f"{config.spshome}\\lib"
    base = (
        launcher_executable,
        f"-Djava.library.path={lib_dir}",
        "-jar",
        "patchworks.jar",
    )
    if interactive:
        return base
    return (
        *base,
        "ca.spatial.tracks.builder.Process",
        str(config.fragments_path),
        str(config.matrix_output_dir),
        str(config.forestmodel_xml_path),
    )


def _build_windows_beanshell_command(
    *,
    launcher_executable: str,
    config: PatchworksRuntimeConfig,
    script_path: Path,
    script_args: tuple[str, ...],
) -> tuple[str, ...]:
    lib_dir = f"{config.spshome}\\lib"
    return (
        launcher_executable,
        f"-Djava.library.path={lib_dir}",
        "-jar",
        "patchworks.jar",
        "ca.spatial.util.IProperties",
        "BeanShell",
        str(script_path),
        *script_args,
    )


def _build_windows_raster_topology_command(
    *,
    launcher_executable: str,
    config: PatchworksRuntimeConfig,
    script_path: Path,
) -> tuple[str, ...]:
    lib_dir = f"{config.spshome}\\lib"
    return (
        launcher_executable,
        f"-Djava.library.path={lib_dir}",
        "-jar",
        "patchworks.jar",
        "ca.spatial.util.IProperties",
        "BeanShell",
        str(script_path),
    )


def _build_launch_command(
    *,
    launcher_executable: str,
    host_mode: str,
    command_string: str,
    use_xvfb: bool,
) -> tuple[str, ...]:
    command: tuple[str, ...] = (launcher_executable, "cmd", "/c", command_string)
    if use_xvfb:
        xvfb_run = shutil_which("xvfb-run")
        if xvfb_run is None:
            raise PatchworksConfigError(
                "patchworks.use_xvfb=true but xvfb-run is not available on PATH"
            )
        command = (xvfb_run, "-a", *command)
    return command


def _matrix_output_ready(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def _matrix_output_state(path: Path) -> tuple[bool, int, float]:
    resolved = path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        return False, 0, 0.0
    file_count = 0
    latest_mtime = 0.0
    for child in resolved.iterdir():
        try:
            stat = child.stat()
        except FileNotFoundError:
            continue
        file_count += 1
        latest_mtime = max(latest_mtime, float(stat.st_mtime))
    return file_count > 0, file_count, latest_mtime


def _detect_fatal_output(output_text: str) -> tuple[str, ...]:
    stderr_lower = output_text.lower()
    return tuple(
        pattern for pattern in FATAL_MATRIX_STDERR_PATTERNS if pattern in stderr_lower
    )


def _resolve_run_id(run_id: str | None) -> str:
    if run_id and run_id.strip():
        return run_id.strip()
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return f"patchworks_{stamp}"


def _close_windows_process_main_windows(process_id: int) -> int:
    if not is_windows_host():
        return 0

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    WM_CLOSE = 0x0010
    closed_count = 0

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd: int, _lparam: int) -> bool:
        nonlocal closed_count
        owner_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if int(owner_pid.value) != int(process_id):
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        closed_count += 1
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return closed_count


def _load_windows_process_inventory() -> list[dict[str, Any]]:
    if not is_windows_host():
        return []
    command = (
        "Get-CimInstance Win32_Process | "
        "ForEach-Object { "
        "$gp = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
        "[pscustomobject]@{ "
        "ProcessId = $_.ProcessId; "
        "ParentProcessId = $_.ParentProcessId; "
        "Name = $_.Name; "
        "CommandLine = $_.CommandLine; "
        "MainWindowTitle = if ($gp) { $gp.MainWindowTitle } else { '' } "
        "} "
        "} | "
        "ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not (completed.stdout or "").strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def _find_windows_matrix_builder_process_ids(
    *, fragments_path: Path, matrix_output_dir: Path, forestmodel_xml_path: Path
) -> set[int]:
    if not is_windows_host():
        return set()
    required_substrings = (
        "ca.spatial.tracks.builder.Process",
        str(fragments_path),
        str(matrix_output_dir),
        str(forestmodel_xml_path),
    )
    out: set[int] = set()
    for record in _load_windows_process_inventory():
        name = str(record.get("Name", "")).lower()
        if name not in {"java.exe", "javaw.exe", "java"}:
            continue
        command_line = str(record.get("CommandLine", "") or "")
        if all(fragment in command_line for fragment in required_substrings):
            try:
                process_id = int(record["ProcessId"])
            except (KeyError, TypeError, ValueError):
                continue
            out.add(process_id)
    return out


def _find_windows_patchworks_shell_process_ids(
    *, inventory: list[dict[str, Any]] | None = None
) -> set[int]:
    if not is_windows_host():
        return set()
    records = inventory if inventory is not None else _load_windows_process_inventory()
    records_by_pid: dict[int, dict[str, Any]] = {}
    children_by_parent: dict[int, set[int]] = {}
    for record in records:
        try:
            pid = int(record["ProcessId"])
        except (KeyError, TypeError, ValueError):
            continue
        records_by_pid[pid] = record
        try:
            parent_pid = int(record["ParentProcessId"])
        except (KeyError, TypeError, ValueError):
            parent_pid = -1
        children_by_parent.setdefault(parent_pid, set()).add(pid)

    root_pids: set[int] = set()
    for pid, record in records_by_pid.items():
        name = str(record.get("Name", "")).lower()
        if name not in {"cmd.exe", "cmd"}:
            continue
        command_line = str(record.get("CommandLine", "") or "")
        main_window_title = str(record.get("MainWindowTitle", "") or "")
        command_line_lower = command_line.lower()
        main_window_title_lower = main_window_title.lower().strip()
        if (
            "ca.spatial.patchworks.patchworks" in command_line_lower
            or main_window_title_lower == "ca.spatial.patchworks.patchworks"
            or re.search(
                r"[\\/](?:temp|tmp)[\\/]\s*sps\d+\.bat", command_line, re.IGNORECASE
            )
            or re.search(r"\bsps\d+\.bat\b", command_line, re.IGNORECASE)
        ):
            root_pids.add(pid)

    matched: set[int] = set()
    stack = list(root_pids)
    while stack:
        pid = stack.pop()
        if pid in matched:
            continue
        matched.add(pid)
        stack.extend(sorted(children_by_parent.get(pid, set())))
    return matched


def _force_stop_windows_process(process_id: int) -> bool:
    if not is_windows_host():
        return False
    completed = subprocess.run(
        ["taskkill", "/PID", str(process_id), "/T", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _run_windows_matrix_builder_with_auto_close(
    *,
    command: tuple[str, ...],
    env: dict[str, str],
    cwd: Path,
    stdout_log_path: Path,
    stderr_log_path: Path,
    fragments_path: Path,
    matrix_output_dir: Path,
    forestmodel_xml_path: Path,
    auto_close_window_on_success: bool,
    auto_close_settle_seconds: float,
    auto_close_timeout_seconds: float,
) -> tuple[int, dict[str, Any]]:
    baseline_ready, baseline_file_count, baseline_latest_mtime = _matrix_output_state(
        matrix_output_dir
    )
    baseline_state = (baseline_ready, baseline_file_count, baseline_latest_mtime)
    baseline_process_ids = _find_windows_matrix_builder_process_ids(
        fragments_path=fragments_path,
        matrix_output_dir=matrix_output_dir,
        forestmodel_xml_path=forestmodel_xml_path,
    )
    baseline_shell_process_ids = _find_windows_patchworks_shell_process_ids()
    current_state = baseline_state
    stable_since: float | None = None
    close_attempted = False
    close_method: str | None = None
    closed_window_count = 0
    force_stopped_pids: list[int] = []
    shell_close_method: str | None = None
    closed_shell_window_count = 0
    force_stopped_shell_pids: list[int] = []
    launched_pid: int | None = None

    with (
        stdout_log_path.open("w", encoding="utf-8") as stdout_handle,
        stderr_log_path.open("w", encoding="utf-8") as stderr_handle,
    ):
        proc = subprocess.Popen(
            list(command),
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            env=env,
            cwd=cwd,
        )
        launched_pid = int(proc.pid)
        while True:
            returncode = proc.poll()
            if returncode is not None:
                break

            observed_state = _matrix_output_state(matrix_output_dir)
            now = time.monotonic()
            if observed_state != current_state:
                current_state = observed_state
                stable_since = now
            elif stable_since is None:
                stable_since = now

            output_ready, _file_count, latest_mtime = observed_state
            output_freshened = latest_mtime > baseline_latest_mtime
            stable_long_enough = (
                output_ready
                and stable_since is not None
                and (now - stable_since) >= auto_close_settle_seconds
            )
            if (
                auto_close_window_on_success
                and not close_attempted
                and output_freshened
                and stable_long_enough
            ):
                close_attempted = True
                target_pids = (
                    _find_windows_matrix_builder_process_ids(
                        fragments_path=fragments_path,
                        matrix_output_dir=matrix_output_dir,
                        forestmodel_xml_path=forestmodel_xml_path,
                    )
                    - baseline_process_ids
                )
                if launched_pid is not None:
                    target_pids.add(launched_pid)
                target_pids = {pid for pid in target_pids if pid > 0}
                for pid in sorted(target_pids):
                    closed_window_count += _close_windows_process_main_windows(pid)
                close_method = "wm_close" if closed_window_count else "force_stop"
                try:
                    returncode = proc.wait(timeout=auto_close_timeout_seconds)
                except subprocess.TimeoutExpired:
                    pass
                lingering_pids = (
                    _find_windows_matrix_builder_process_ids(
                        fragments_path=fragments_path,
                        matrix_output_dir=matrix_output_dir,
                        forestmodel_xml_path=forestmodel_xml_path,
                    )
                    - baseline_process_ids
                )
                if launched_pid is not None:
                    lingering_pids.add(launched_pid)
                lingering_pids = {pid for pid in lingering_pids if pid > 0}
                for pid in sorted(lingering_pids):
                    if _force_stop_windows_process(pid):
                        force_stopped_pids.append(pid)
                if force_stopped_pids:
                    close_method = "force_stop"
                try:
                    returncode = proc.wait(timeout=auto_close_timeout_seconds)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    close_method = "kill"
                    returncode = proc.wait(timeout=auto_close_timeout_seconds)

                current_shell_pids = (
                    _find_windows_patchworks_shell_process_ids()
                    - baseline_shell_process_ids
                )
                current_shell_pids = {pid for pid in current_shell_pids if pid > 0}
                for pid in sorted(current_shell_pids):
                    closed_shell_window_count += _close_windows_process_main_windows(
                        pid
                    )
                if current_shell_pids:
                    shell_close_method = (
                        "wm_close" if closed_shell_window_count else "force_stop"
                    )
                time.sleep(0.25)
                lingering_shell_pids = (
                    _find_windows_patchworks_shell_process_ids()
                    - baseline_shell_process_ids
                )
                lingering_shell_pids = {pid for pid in lingering_shell_pids if pid > 0}
                for pid in sorted(lingering_shell_pids):
                    if _force_stop_windows_process(pid):
                        force_stopped_shell_pids.append(pid)
                if force_stopped_shell_pids:
                    shell_close_method = "force_stop"
                break

            time.sleep(0.25)

    return returncode, {
        "auto_close_window_on_success": auto_close_window_on_success,
        "baseline_output_state": {
            "ready": baseline_state[0],
            "file_count": baseline_state[1],
            "latest_mtime": baseline_state[2],
        },
        "baseline_process_ids": sorted(baseline_process_ids),
        "baseline_shell_process_ids": sorted(baseline_shell_process_ids),
        "launched_pid": launched_pid,
        "final_output_state": {
            "ready": current_state[0],
            "file_count": current_state[1],
            "latest_mtime": current_state[2],
        },
        "close_attempted": close_attempted,
        "close_method": close_method,
        "closed_window_count": closed_window_count,
        "force_stopped_pids": force_stopped_pids,
        "shell_close_method": shell_close_method,
        "closed_shell_window_count": closed_shell_window_count,
        "force_stopped_shell_pids": force_stopped_shell_pids,
        "remaining_process_ids": sorted(
            _find_windows_matrix_builder_process_ids(
                fragments_path=fragments_path,
                matrix_output_dir=matrix_output_dir,
                forestmodel_xml_path=forestmodel_xml_path,
            )
            - baseline_process_ids
        ),
        "remaining_shell_process_ids": sorted(
            _find_windows_patchworks_shell_process_ids() - baseline_shell_process_ids
        ),
    }


def _resolve_accounts_backup_path(*, tracks_dir: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    candidate = tracks_dir / f"accounts_backup_{stamp}.csv"
    if not candidate.exists():
        return candidate
    for idx in range(1, 1000):
        alt = tracks_dir / f"accounts_backup_{stamp}_{idx:03d}.csv"
        if not alt.exists():
            return alt
    raise PatchworksConfigError(
        "Unable to allocate unique accounts backup filename in tracks directory"
    )


def _format_account_sum_multiplier(value: float) -> str:
    if not value or value <= 0.0:
        return "1"
    return f"{value:.12g}"


def _parse_account_sum_multiplier(value: str) -> float:
    text = str(value).strip()
    if not text:
        return 1.0
    try:
        return float(text)
    except ValueError:
        return 1.0


def _load_feature_account_au_id_by_token_from_forestmodel(
    *,
    forestmodel_xml_path: Path,
    pattern: re.Pattern[str],
) -> dict[str, int]:
    resolved = forestmodel_xml_path.expanduser().resolve()
    if not resolved.exists():
        return {}
    root = et.parse(resolved).getroot()
    out: dict[str, int] = {}
    for select_node in root.findall("./select"):
        statement = str(select_node.get("statement", ""))
        match = AU_EQ_PATTERN.search(statement)
        if match is None:
            continue
        au_id = int(match.group(1))
        for attribute_node in select_node.findall("./features/attribute"):
            label = str(attribute_node.get("label", ""))
            feature_match = pattern.match(label)
            if feature_match is None:
                continue
            token = feature_match.group(2)
            prior = out.get(token)
            if prior is None or prior == au_id:
                out[token] = au_id
    return out


def _load_feature_account_au_id_by_label_from_forestmodel(
    *,
    forestmodel_xml_path: Path,
    pattern: re.Pattern[str],
) -> dict[str, int]:
    resolved = forestmodel_xml_path.expanduser().resolve()
    if not resolved.exists():
        return {}
    root = et.parse(resolved).getroot()
    out: dict[str, int] = {}
    for select_node in root.findall("./select"):
        statement = str(select_node.get("statement", ""))
        match = AU_EQ_PATTERN.search(statement)
        if match is None:
            continue
        au_id = int(match.group(1))
        for attribute_node in select_node.findall("./features/attribute"):
            label = str(attribute_node.get("label", ""))
            feature_match = pattern.match(label)
            if feature_match is None:
                continue
            prior = out.get(label)
            if prior is None or prior == au_id:
                out[label] = au_id
    return out


def _load_fragments_area_by_au_and_ifm(
    *, fragments_path: Path
) -> dict[tuple[str, int], float]:
    resolved = fragments_path.expanduser().resolve()
    if not resolved.exists():
        return {}
    gpd = _import_geopandas()
    fragments = gpd.read_file(resolved)
    required = {"AU", "AREA_HA", "IFM", "RETENTION"}
    if fragments.empty or not required.issubset(fragments.columns):
        return {}

    out: dict[tuple[str, int], float] = {}
    for row in fragments.itertuples(index=False):
        au_raw = getattr(row, "AU", None)
        area_raw = getattr(row, "AREA_HA", None)
        ifm_raw = getattr(row, "IFM", None)
        retention_raw = getattr(row, "RETENTION", 0.0)
        if au_raw is None or area_raw is None or retention_raw is None:
            continue
        try:
            au_id = int(au_raw)
            area_ha = float(area_raw)
            retention = float(retention_raw)
        except (TypeError, ValueError):
            continue
        if area_ha <= 0.0:
            continue
        retention = min(max(retention, 0.0), 1.0)
        ifm = str(ifm_raw or "").strip().lower()
        if ifm == "managed":
            managed_area = area_ha * (1.0 - retention)
            unmanaged_area = area_ha * retention
            if managed_area > 0.0:
                out[("managed", au_id)] = (
                    out.get(("managed", au_id), 0.0) + managed_area
                )
            if unmanaged_area > 0.0:
                out[("unmanaged", au_id)] = (
                    out.get(("unmanaged", au_id), 0.0) + unmanaged_area
                )
        elif ifm == "unmanaged":
            out[("unmanaged", au_id)] = out.get(("unmanaged", au_id), 0.0) + area_ha
    return out


def _resolve_area_normalized_feature_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
    pattern: re.Pattern[str],
    label_prefix: str,
) -> dict[str, str]:
    au_id_by_token = _load_feature_account_au_id_by_token_from_forestmodel(
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=pattern,
    )
    if not au_id_by_token:
        return {}
    area_by_au_and_ifm = _load_fragments_area_by_au_and_ifm(
        fragments_path=fragments_path
    )
    if not area_by_au_and_ifm:
        return {}

    overrides: dict[str, str] = {}
    for token, au_id in au_id_by_token.items():
        managed_area = area_by_au_and_ifm.get(("managed", au_id), 0.0)
        unmanaged_area = area_by_au_and_ifm.get(("unmanaged", au_id), 0.0)
        if managed_area > 0.0:
            overrides[f"{label_prefix}.managed.{token}"] = (
                _format_account_sum_multiplier(1.0 / managed_area)
            )
        if unmanaged_area > 0.0:
            overrides[f"{label_prefix}.unmanaged.{token}"] = (
                _format_account_sum_multiplier(1.0 / unmanaged_area)
            )
    return overrides


def _resolve_qmd_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
) -> dict[str, str]:
    return _resolve_area_normalized_feature_account_sum_overrides(
        fragments_path=fragments_path,
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=QMD_ACCOUNT_PATTERN,
        label_prefix="feature.QMD",
    )


def _resolve_height_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
) -> dict[str, str]:
    return _resolve_area_normalized_feature_account_sum_overrides(
        fragments_path=fragments_path,
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=HEIGHT_ACCOUNT_PATTERN,
        label_prefix="feature.Height",
    )


def _resolve_stems_per_ha_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
) -> dict[str, str]:
    return _resolve_area_normalized_feature_account_sum_overrides(
        fragments_path=fragments_path,
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=STEMS_PER_HA_ACCOUNT_PATTERN,
        label_prefix="feature.StemsPerHa",
    )


def _resolve_managed_only_feature_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
    pattern: re.Pattern[str],
) -> dict[str, str]:
    au_id_by_label = _load_feature_account_au_id_by_label_from_forestmodel(
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=pattern,
    )
    if not au_id_by_label:
        return {}
    area_by_au_and_ifm = _load_fragments_area_by_au_and_ifm(
        fragments_path=fragments_path
    )
    if not area_by_au_and_ifm:
        return {}

    overrides: dict[str, str] = {}
    for attribute, au_id in au_id_by_label.items():
        managed_area = area_by_au_and_ifm.get(("managed", au_id), 0.0)
        if managed_area > 0.0:
            overrides[attribute] = _format_account_sum_multiplier(1.0 / managed_area)
    return overrides


def _resolve_stand_structure_basic_account_sum_overrides(
    *,
    fragments_path: Path,
    forestmodel_xml_path: Path,
) -> dict[str, str]:
    return _resolve_managed_only_feature_account_sum_overrides(
        fragments_path=fragments_path,
        forestmodel_xml_path=forestmodel_xml_path,
        pattern=STAND_STRUCTURE_BASIC_ACCOUNT_PATTERN,
    )


def _resolve_harvested_volume_sum_multiplier(
    *,
    attribute: str,
    harvested_volume_utilization_by_treatment: dict[str, float],
) -> float | None:
    if not harvested_volume_utilization_by_treatment:
        return None
    match = HARVESTED_VOLUME_ACCOUNT_PATTERN.match(attribute)
    if match is None:
        return None
    treatment = match.group(1).upper()
    return harvested_volume_utilization_by_treatment.get(treatment)


def _count_topology_edges(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        line_count = sum(1 for _ in handle)
    return max(0, line_count - 1)


def _run_patchworks_raster_topology(
    *,
    config: PatchworksRuntimeConfig,
    fragments_shapefile_path: Path,
    topology_id_field: str,
    topology_csv_path: Path,
    topology_radius_m: float,
    cellsize_m: float = 10.0,
) -> int:
    if not is_windows_host():
        raise PatchworksConfigError(
            "topology_backend=patchworks-raster currently requires a native "
            "Windows Patchworks install"
        )

    launcher_executable = shutil_which("java")
    if launcher_executable is None:
        raise PatchworksConfigError(
            "java not found on PATH; required for Patchworks raster topology builder"
        )

    topology_csv_path.parent.mkdir(parents=True, exist_ok=True)
    if topology_csv_path.exists():
        topology_csv_path.unlink()

    script_text = "\n".join(
        (
            f'input = "{fragments_shapefile_path.as_posix()}";',
            f'output = "{topology_csv_path.as_posix()}";',
            "store = ca.spatial.table.GeoRelationalStore.open(input);",
            (
                "pt = new ca.spatial.gis.raster.ProximalTopology("
                f'input, store, {cellsize_m:g}f, "BLOCK", {topology_radius_m:g}f, output);'
            ),
            "pt.execute();",
            "",
        )
    )

    handle, script_name = tempfile.mkstemp(
        prefix="femic_patchworks_topology_", suffix=".bsh"
    )
    script_path = Path(script_name)
    try:
        with os.fdopen(handle, "w", encoding="ascii", newline="\n") as script_handle:
            script_handle.write(script_text)
        command = _build_windows_raster_topology_command(
            launcher_executable=launcher_executable,
            config=config,
            script_path=script_path,
        )
        result = subprocess.run(
            command,
            cwd=config.jar_path.parent,
            env=_build_base_env(config),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        script_path.unlink(missing_ok=True)

    combined_output = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part and part.strip()
    )
    if not topology_csv_path.exists():
        detail = combined_output.strip()
        raise PatchworksConfigError(
            "Patchworks raster topology builder exited without writing topology CSV"
            + (f": {detail}" if detail else "")
        )
    if "Successful completion" not in combined_output:
        detail = combined_output.strip()
        raise PatchworksConfigError(
            "Patchworks raster topology builder wrote topology CSV but did not report "
            "successful completion" + (f": {detail}" if detail else "")
        )
    return _count_topology_edges(topology_csv_path)


def _promote_protoaccounts_to_accounts(
    *,
    matrix_output_dir: Path,
    fragments_path: Path,
    forestmodel_xml_path: Path,
    exclude_regex: tuple[str, ...] = (),
    harvested_volume_utilization_by_treatment: dict[str, float] | None = None,
) -> tuple[Path | None, Path | None, Path, int]:
    tracks_dir = matrix_output_dir.expanduser().resolve()
    protoaccounts_path = tracks_dir / "protoaccounts.csv"
    accounts_path = tracks_dir / "accounts.csv"
    if not protoaccounts_path.exists():
        return None, None, protoaccounts_path, 0

    backup_path: Path | None = None
    if accounts_path.exists():
        backup_path = _resolve_accounts_backup_path(tracks_dir=tracks_dir)
        accounts_path.replace(backup_path)

    patterns = tuple(re.compile(pattern) for pattern in exclude_regex)
    with protoaccounts_path.open("r", encoding="utf-8", newline="") as src:
        reader = csv.DictReader(src)
        fieldnames = list(reader.fieldnames or ["GROUP", "ATTRIBUTE", "ACCOUNT", "SUM"])
        rows = [{key: row.get(key, "") for key in fieldnames} for row in reader]

    has_qmd_rows = any(
        QMD_ACCOUNT_PATTERN.match(str(row.get("ATTRIBUTE", ""))) is not None
        for row in rows
    )
    has_height_rows = any(
        HEIGHT_ACCOUNT_PATTERN.match(str(row.get("ATTRIBUTE", ""))) is not None
        for row in rows
    )
    has_stems_per_ha_rows = any(
        STEMS_PER_HA_ACCOUNT_PATTERN.match(str(row.get("ATTRIBUTE", ""))) is not None
        for row in rows
    )
    has_stand_structure_basic_rows = any(
        STAND_STRUCTURE_BASIC_ACCOUNT_PATTERN.match(str(row.get("ATTRIBUTE", "")))
        is not None
        for row in rows
    )
    utilization_by_treatment = harvested_volume_utilization_by_treatment or {}
    qmd_sum_overrides = (
        _resolve_qmd_account_sum_overrides(
            fragments_path=fragments_path,
            forestmodel_xml_path=forestmodel_xml_path,
        )
        if has_qmd_rows
        else {}
    )
    height_sum_overrides = (
        _resolve_height_account_sum_overrides(
            fragments_path=fragments_path,
            forestmodel_xml_path=forestmodel_xml_path,
        )
        if has_height_rows
        else {}
    )
    stems_per_ha_sum_overrides = (
        _resolve_stems_per_ha_account_sum_overrides(
            fragments_path=fragments_path,
            forestmodel_xml_path=forestmodel_xml_path,
        )
        if has_stems_per_ha_rows
        else {}
    )
    stand_structure_basic_sum_overrides = (
        _resolve_stand_structure_basic_account_sum_overrides(
            fragments_path=fragments_path,
            forestmodel_xml_path=forestmodel_xml_path,
        )
        if has_stand_structure_basic_rows
        else {}
    )
    feature_sum_overrides = {
        **qmd_sum_overrides,
        **height_sum_overrides,
        **stems_per_ha_sum_overrides,
        **stand_structure_basic_sum_overrides,
    }
    if not exclude_regex and not feature_sum_overrides and not utilization_by_treatment:
        shutil.copy2(protoaccounts_path, accounts_path)
        return accounts_path, backup_path, protoaccounts_path, 0

    with accounts_path.open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=fieldnames)
        writer.writeheader()
        excluded_count = 0
        for row in rows:
            attribute = str(row.get("ATTRIBUTE", ""))
            account = str(row.get("ACCOUNT", ""))
            if any(
                pattern.search(attribute) or pattern.search(account)
                for pattern in patterns
            ):
                excluded_count += 1
                continue
            if attribute in feature_sum_overrides:
                row["SUM"] = feature_sum_overrides[attribute]
            utilization_multiplier = _resolve_harvested_volume_sum_multiplier(
                attribute=attribute,
                harvested_volume_utilization_by_treatment=utilization_by_treatment,
            )
            if utilization_multiplier is not None:
                base_multiplier = _parse_account_sum_multiplier(str(row.get("SUM", "")))
                row["SUM"] = _format_account_sum_multiplier(
                    base_multiplier * utilization_multiplier
                )
            writer.writerow(row)
    return accounts_path, backup_path, protoaccounts_path, excluded_count


def run_patchworks_command(
    *,
    config: PatchworksRuntimeConfig,
    interactive: bool,
    log_dir: Path,
    run_id: str | None = None,
) -> PatchworksExecutionResult:
    """Execute Patchworks command and capture logs+manifest."""

    preflight = run_patchworks_preflight(config=config, require_matrix_inputs=True)
    if not preflight.ok:
        raise PatchworksConfigError(
            "Patchworks preflight failed prior to execution: "
            + "; ".join(preflight.errors)
        )
    assert preflight.launcher_executable is not None

    effective_run_id = _resolve_run_id(run_id)
    resolved_log_dir = log_dir.expanduser().resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    if not interactive:
        config.matrix_output_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = (
        resolved_log_dir / f"patchworks_matrixbuilder_stdout-{effective_run_id}.log"
    )
    stderr_log = (
        resolved_log_dir / f"patchworks_matrixbuilder_stderr-{effective_run_id}.log"
    )
    manifest_path = (
        resolved_log_dir / f"patchworks_matrixbuilder_manifest-{effective_run_id}.json"
    )

    command_string = (
        build_appchooser_command_string(config)
        if interactive
        else build_matrix_builder_command_string(config)
    )
    command = (
        _build_windows_java_command(
            launcher_executable=preflight.launcher_executable,
            config=config,
            interactive=interactive,
        )
        if preflight.host_mode == "windows"
        else _build_launch_command(
            launcher_executable=preflight.launcher_executable,
            host_mode=preflight.host_mode,
            command_string=command_string,
            use_xvfb=config.use_xvfb,
        )
    )
    if preflight.host_mode == "windows":
        command_string = format_command_for_display(command)

    windows_automation: dict[str, Any] | None = None
    if preflight.host_mode == "windows" and not interactive:
        raw_returncode, windows_automation = (
            _run_windows_matrix_builder_with_auto_close(
                command=command,
                env=_build_base_env(config),
                cwd=config.jar_path.parent,
                stdout_log_path=stdout_log,
                stderr_log_path=stderr_log,
                fragments_path=config.fragments_path,
                matrix_output_dir=config.matrix_output_dir,
                forestmodel_xml_path=config.forestmodel_xml_path,
                auto_close_window_on_success=config.auto_close_window_on_success,
                auto_close_settle_seconds=config.auto_close_settle_seconds,
                auto_close_timeout_seconds=config.auto_close_timeout_seconds,
            )
        )
        stdout_text = stdout_log.read_text(encoding="utf-8")
        stderr_text = stderr_log.read_text(encoding="utf-8")
    else:
        proc = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            env=_build_base_env(config),
            cwd=config.jar_path.parent if preflight.host_mode == "windows" else None,
            check=False,
        )
        raw_returncode = proc.returncode
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
        stdout_log.write_text(stdout_text, encoding="utf-8")
        stderr_log.write_text(stderr_text, encoding="utf-8")

    failures: list[str] = []
    accounts_synced_path: Path | None = None
    accounts_backup_path: Path | None = None
    protoaccounts_path: Path | None = None
    accounts_sync_status = "not_requested"
    accounts_excluded_row_count = 0
    output_for_scan = stderr_text + "\n" + stdout_text
    fatal_stderr_matches = _detect_fatal_output(output_for_scan)
    if fatal_stderr_matches:
        failures.append(
            "fatal stderr signatures detected: " + ", ".join(fatal_stderr_matches)
        )
    if not interactive and not _matrix_output_ready(config.matrix_output_dir):
        failures.append(
            f"matrix output directory missing or empty: {config.matrix_output_dir}"
        )
    if not interactive and not failures:
        (
            accounts_synced_path,
            accounts_backup_path,
            protoaccounts_path,
            accounts_excluded_row_count,
        ) = _promote_protoaccounts_to_accounts(
            matrix_output_dir=config.matrix_output_dir,
            fragments_path=config.fragments_path,
            forestmodel_xml_path=config.forestmodel_xml_path,
            exclude_regex=config.accounts_exclude_regex,
            harvested_volume_utilization_by_treatment=(
                config.harvested_volume_utilization_by_treatment
            ),
        )
        if accounts_synced_path is not None:
            accounts_sync_status = "synced"
        elif protoaccounts_path is not None:
            accounts_sync_status = "skipped_missing_protoaccounts"

    if failures:
        effective_returncode = 1
    elif not interactive and _matrix_output_ready(config.matrix_output_dir):
        # Process.main(...) may dispatch background work and not return a stable process code.
        effective_returncode = 0
    else:
        effective_returncode = raw_returncode

    manifest_payload = {
        "run_id": effective_run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "interactive": interactive,
        "command": list(command),
        "command_string": command_string,
        "raw_returncode": raw_returncode,
        "returncode": effective_returncode,
        "runtime": {
            "launcher_executable": preflight.launcher_executable,
            "host_mode": preflight.host_mode,
            "jar_path": str(config.jar_path),
            "license_env": config.license_env,
            "license_value": config.license_value,
            "spshome": config.spshome,
            "use_xvfb": config.use_xvfb,
            "wine_prefix": str(config.wine_prefix) if config.wine_prefix else None,
            "auto_close_window_on_success": config.auto_close_window_on_success,
            "auto_close_settle_seconds": config.auto_close_settle_seconds,
            "auto_close_timeout_seconds": config.auto_close_timeout_seconds,
        },
        "inputs": {
            "fragments_path": str(config.fragments_path),
            "matrix_output_dir": str(config.matrix_output_dir),
            "forestmodel_xml_path": str(config.forestmodel_xml_path),
        },
        "accounts_sync": {
            "status": accounts_sync_status,
            "protoaccounts_path": (
                str(protoaccounts_path) if protoaccounts_path is not None else None
            ),
            "accounts_path": (
                str(accounts_synced_path) if accounts_synced_path is not None else None
            ),
            "backup_path": (
                str(accounts_backup_path) if accounts_backup_path is not None else None
            ),
            "excluded_patterns": list(config.accounts_exclude_regex),
            "excluded_row_count": accounts_excluded_row_count,
            "harvested_volume_utilization_by_treatment": (
                config.harvested_volume_utilization_by_treatment
            ),
        },
        "logs": {
            "stdout": str(stdout_log),
            "stderr": str(stderr_log),
        },
        "windows_automation": windows_automation,
        "failures": failures,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    return PatchworksExecutionResult(
        run_id=effective_run_id,
        command=command,
        command_string=command_string,
        returncode=effective_returncode,
        stdout_log_path=stdout_log,
        stderr_log_path=stderr_log,
        manifest_path=manifest_path,
        failures=tuple(failures),
    )


def run_patchworks_beanshell_script(
    *,
    config: PatchworksRuntimeConfig,
    script_path: Path,
    script_args: tuple[str, ...],
    log_dir: Path,
    run_id: str | None = None,
) -> PatchworksExecutionResult:
    """Execute a Patchworks BeanShell script via IProperties."""

    preflight = run_patchworks_preflight(config=config, require_matrix_inputs=False)
    if not preflight.ok:
        raise PatchworksConfigError(
            "Patchworks preflight failed prior to execution: "
            + "; ".join(preflight.errors)
        )
    assert preflight.launcher_executable is not None

    resolved_script_path = script_path.expanduser().resolve()
    if not resolved_script_path.exists():
        raise FileNotFoundError(f"BeanShell script not found: {resolved_script_path}")
    if resolved_script_path.is_dir():
        raise PatchworksConfigError(
            f"BeanShell script path is a directory: {resolved_script_path}"
        )

    effective_run_id = _resolve_run_id(run_id)
    resolved_log_dir = log_dir.expanduser().resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    stdout_log = (
        resolved_log_dir / f"patchworks_beanshell_stdout-{effective_run_id}.log"
    )
    stderr_log = (
        resolved_log_dir / f"patchworks_beanshell_stderr-{effective_run_id}.log"
    )
    manifest_path = (
        resolved_log_dir / f"patchworks_beanshell_manifest-{effective_run_id}.json"
    )

    command_string = build_beanshell_command_string(
        config=config,
        script_path=resolved_script_path,
        script_args=script_args,
    )
    command = (
        _build_windows_beanshell_command(
            launcher_executable=preflight.launcher_executable,
            config=config,
            script_path=resolved_script_path,
            script_args=script_args,
        )
        if preflight.host_mode == "windows"
        else _build_launch_command(
            launcher_executable=preflight.launcher_executable,
            host_mode=preflight.host_mode,
            command_string=command_string,
            use_xvfb=config.use_xvfb,
        )
    )
    if preflight.host_mode == "windows":
        command_string = format_command_for_display(command)

    proc = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        env=_build_base_env(config),
        cwd=config.jar_path.parent if preflight.host_mode == "windows" else None,
        check=False,
    )

    stdout_log.write_text(proc.stdout or "", encoding="utf-8")
    stderr_log.write_text(proc.stderr or "", encoding="utf-8")

    failures: list[str] = []
    output_for_scan = (proc.stderr or "") + "\n" + (proc.stdout or "")
    fatal_stderr_matches = _detect_fatal_output(output_for_scan)
    if fatal_stderr_matches:
        failures.append(
            "fatal stderr signatures detected: " + ", ".join(fatal_stderr_matches)
        )
    effective_returncode = 1 if failures else proc.returncode

    manifest_payload = {
        "run_id": effective_run_id,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "interactive": False,
        "mode": "beanshell",
        "command": list(command),
        "command_string": command_string,
        "raw_returncode": proc.returncode,
        "returncode": effective_returncode,
        "runtime": {
            "launcher_executable": preflight.launcher_executable,
            "host_mode": preflight.host_mode,
            "jar_path": str(config.jar_path),
            "license_env": config.license_env,
            "license_value": config.license_value,
            "spshome": config.spshome,
            "use_xvfb": config.use_xvfb,
            "wine_prefix": str(config.wine_prefix) if config.wine_prefix else None,
        },
        "inputs": {
            "script_path": str(resolved_script_path),
            "script_args": list(script_args),
        },
        "logs": {
            "stdout": str(stdout_log),
            "stderr": str(stderr_log),
        },
        "failures": failures,
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    return PatchworksExecutionResult(
        run_id=effective_run_id,
        command=command,
        command_string=command_string,
        returncode=effective_returncode,
        stdout_log_path=stdout_log,
        stderr_log_path=stderr_log,
        manifest_path=manifest_path,
        failures=tuple(failures),
    )


def _import_geopandas() -> Any:
    try:
        return importlib.import_module("geopandas")
    except ModuleNotFoundError as exc:
        raise PatchworksConfigError(
            "geopandas is required for `femic patchworks build-blocks`"
        ) from exc


def _import_pandas() -> Any:
    try:
        return importlib.import_module("pandas")
    except ModuleNotFoundError as exc:
        raise PatchworksConfigError(
            "pandas is required for `femic patchworks build-blocks`"
        ) from exc


def _import_shapely_unary_union() -> Any:
    try:
        ops = importlib.import_module("shapely.ops")
        return ops.unary_union
    except ModuleNotFoundError as exc:
        raise PatchworksConfigError(
            "shapely is required for `femic patchworks build-blocks`"
        ) from exc


def _resolve_fragments_shapefile_path(
    *,
    config: PatchworksRuntimeConfig,
    fragments_shapefile_path: Path | None,
) -> Path:
    if fragments_shapefile_path is not None:
        candidate = fragments_shapefile_path.expanduser().resolve()
    elif config.fragments_path.suffix.lower() == ".dbf":
        candidate = config.fragments_path.with_suffix(".shp")
    else:
        candidate = config.fragments_path
    return candidate.expanduser().resolve()


def _resolve_blocks_model_dir(
    *,
    config: PatchworksRuntimeConfig,
    model_dir: Path | None,
) -> Path:
    if model_dir is not None:
        return model_dir.expanduser().resolve()
    return infer_patchworks_model_dir(config)


def _select_stand_id_field(columns: list[str]) -> str:
    # Prefer the Matrix Builder block key when present so blocks.shp joins align
    # with tracks/blocks.csv.
    for candidate in ("BLOCK", "FEATURE_ID", "FRAGMENT_ID", "FRAGMENT_I", "FRAGS_ID"):
        if candidate in columns:
            return candidate
    raise PatchworksConfigError(
        "No stand identifier field found in fragments. "
        "Expected BLOCK, FEATURE_ID, FRAGMENT_ID, FRAGMENT_I, or FRAGS_ID."
    )


def _select_topology_id_field(columns: list[str]) -> str:
    for candidate in ("FRAGMENT_ID", "FRAGMENT_I", "FEATURE_ID", "BLOCK", "FRAGS_ID"):
        if candidate in columns:
            return candidate
    raise PatchworksConfigError(
        "No topology identifier field found in fragments. "
        "Expected FRAGMENT_ID, FRAGMENT_I, FEATURE_ID, BLOCK, or FRAGS_ID."
    )


def _build_topology_rows(
    *,
    blocks_gdf: Any,
    topology_radius_m: float,
) -> list[tuple[int, int, float, float]]:
    if topology_radius_m < 0:
        raise PatchworksConfigError("topology_radius_m must be >= 0")

    records: list[tuple[int, int, float, float]] = []
    seen_pairs: set[tuple[int, int]] = set()

    geometries = list(blocks_gdf.geometry)
    block_ids = [int(value) for value in blocks_gdf["BLOCK"]]
    sindex = blocks_gdf.sindex

    for left_idx, (left_block, left_geom) in enumerate(zip(block_ids, geometries)):
        if left_geom is None or left_geom.is_empty:
            continue
        candidate_bounds = left_geom.buffer(topology_radius_m).bounds
        for right_idx in sindex.intersection(candidate_bounds):
            if right_idx <= left_idx:
                continue
            right_geom = geometries[right_idx]
            if right_geom is None or right_geom.is_empty:
                continue
            distance = float(left_geom.distance(right_geom))
            if distance > topology_radius_m + 1e-9:
                continue
            right_block = block_ids[right_idx]
            block1 = min(left_block, right_block)
            block2 = max(left_block, right_block)
            pair = (block1, block2)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if distance <= 1e-9:
                edge_length = float(
                    left_geom.boundary.intersection(right_geom.boundary).length
                )
                records.append((block1, block2, 0.0, edge_length))
            else:
                records.append((block1, block2, distance, 0.0))

    unary_union = _import_shapely_unary_union()
    model_boundary = unary_union(geometries).boundary
    for block_id, geom in zip(block_ids, geometries):
        if geom is None or geom.is_empty:
            continue
        perimeter_on_exterior = float(geom.boundary.intersection(model_boundary).length)
        if perimeter_on_exterior > 0:
            records.append((-9999, block_id, 0.0, perimeter_on_exterior))
            continue
        distance_to_exterior = float(geom.distance(model_boundary))
        if distance_to_exterior <= topology_radius_m + 1e-9:
            records.append((-9999, block_id, distance_to_exterior, 0.0))

    records.sort(key=lambda row: (row[0], row[1]))
    return records


def build_patchworks_blocks_dataset(
    *,
    config: PatchworksRuntimeConfig,
    model_dir: Path | None = None,
    fragments_shapefile_path: Path | None = None,
    topology_radius_m: float = 200.0,
    build_topology: bool = True,
    topology_backend: PatchworksTopologyBackend = "python",
) -> PatchworksBlocksBuildResult:
    """Build 1:1 stand:block `blocks.shp` (and optional topology CSV)."""

    gpd = _import_geopandas()
    pd = _import_pandas()

    resolved_model_dir = _resolve_blocks_model_dir(config=config, model_dir=model_dir)
    resolved_fragments_shp = _resolve_fragments_shapefile_path(
        config=config,
        fragments_shapefile_path=fragments_shapefile_path,
    )
    if not resolved_fragments_shp.exists():
        raise FileNotFoundError(
            f"Fragments shapefile not found: {resolved_fragments_shp}"
        )
    if resolved_fragments_shp.suffix.lower() != ".shp":
        raise PatchworksConfigError(
            "fragments_shapefile_path must point to a .shp file"
        )

    fragments_gdf = gpd.read_file(resolved_fragments_shp)
    if fragments_gdf.empty:
        raise PatchworksConfigError(
            f"Fragments shapefile has no records: {resolved_fragments_shp}"
        )
    if "geometry" not in fragments_gdf.columns:
        raise PatchworksConfigError(
            f"Fragments shapefile missing geometry column: {resolved_fragments_shp}"
        )

    stand_id_field = _select_stand_id_field(list(fragments_gdf.columns))
    stand_series = pd.to_numeric(fragments_gdf[stand_id_field], errors="raise")
    if stand_series.isna().any():
        raise PatchworksConfigError(
            f"Stand identifier field contains null values: {stand_id_field}"
        )

    blocks_gdf = fragments_gdf.copy()
    blocks_gdf["BLOCK"] = stand_series.astype("int64")

    blocks_dir = resolved_model_dir / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)
    blocks_shp_path = (blocks_dir / "blocks.shp").resolve()
    blocks_gdf.to_file(blocks_shp_path, index=False)

    topology_path: Path | None = None
    topology_edge_count = 0
    if build_topology:
        rounded_radius = int(round(topology_radius_m))
        topology_path = (
            blocks_dir / f"topology_blocks_{rounded_radius}r.csv"
        ).resolve()
        if topology_backend == "python":
            topology_rows = _build_topology_rows(
                blocks_gdf=blocks_gdf,
                topology_radius_m=topology_radius_m,
            )
            with topology_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(("BLOCK1", "BLOCK2", "DISTANCE", "LENGTH"))
                for block1, block2, distance, length in topology_rows:
                    writer.writerow(
                        (block1, block2, f"{distance:.3f}", f"{length:.3f}")
                    )
            topology_edge_count = len(topology_rows)
        elif topology_backend == "patchworks-raster":
            topology_edge_count = _run_patchworks_raster_topology(
                config=config,
                fragments_shapefile_path=resolved_fragments_shp,
                topology_id_field=_select_topology_id_field(
                    list(fragments_gdf.columns)
                ),
                topology_csv_path=topology_path,
                topology_radius_m=topology_radius_m,
            )
        else:
            raise PatchworksConfigError(
                "Unsupported topology backend: "
                f"{topology_backend}. Expected 'python' or 'patchworks-raster'."
            )

    return PatchworksBlocksBuildResult(
        model_dir=resolved_model_dir,
        fragments_shapefile_path=resolved_fragments_shp,
        blocks_shapefile_path=blocks_shp_path,
        topology_csv_path=topology_path,
        block_count=len(blocks_gdf),
        stand_id_field=stand_id_field,
        topology_edge_count=topology_edge_count,
        topology_radius_m=topology_radius_m,
    )


def format_command_for_display(command: tuple[str, ...]) -> str:
    """Return shell-quoted command for human-readable logs."""

    return " ".join(shlex.quote(part) for part in command)
