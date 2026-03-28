"""Reusable TIPSY parameter helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Mapping, Sequence
import warnings

import numpy as np

from femic.pipeline.diagnostics import build_timestamped_event


_BTC_REPORT_COLUMNS_COMMENT = (
    "'enum_db_column\tWidth\tHeader1Override\tHeader2Override\tUnitsOverride"
)
DEFAULT_BTC_REPORT_HEADER_FLAGS: dict[str, str] = {
    "ModelVersion": "1",
    "TU_InitDensity": "1",
    "TU_RegenType": "1",
    "TU_RegenDelay": "1",
    "TU_Treatments": "1",
    "TU_Area": "1",
    "Species_SiteCurve": "0",
    "Species_TopHeight": "0",
    "Species_InitDensity": "0",
    "Species_StockHeight": "1",
    "Species_GenWorth": "1",
    "Species_Fertilization": "1",
}
_BTC_REPORT_PRESET_NAMES = (
    "timber-supply-sql",
    "tsr-unattended-default",
)
DEFAULT_BTC_MSYT_COLUMNS = (
    "feature_id",
    "bec_zone",
    "bec_subzone",
    "planted_species1",
    "planted_species2",
    "planted_species3",
    "planted_species4",
    "planted_species5",
    "planted_density1",
    "planted_density2",
    "planted_density3",
    "planted_density4",
    "planted_density5",
    "genetic_worth1",
    "genetic_worth2",
    "genetic_worth3",
    "genetic_worth4",
    "genetic_worth5",
    "planting_delay",
    "planted_percent",
    "natural_species1",
    "natural_species2",
    "natural_species3",
    "natural_species4",
    "natural_species5",
    "natural_density1",
    "natural_density2",
    "natural_density3",
    "natural_density4",
    "natural_density5",
    "oaf1",
    "oaf2",
    "opening_id",
    "vri_ref_age",
    "vri_ref_sph",
    "at_si",
    "ba_si",
    "bg_si",
    "bl_si",
    "cw_si",
    "dr_si",
    "ep_si",
    "fd_si",
    "hm_si",
    "hw_si",
    "lt_si",
    "lw_si",
    "pa_si",
    "pl_si",
    "pw_si",
    "py_si",
    "sb_si",
    "se_si",
    "ss_si",
    "sw_si",
    "sx_si",
    "yc_si",
)
_BTC_MSYT_SITE_INDEX_COLUMNS = tuple(
    column for column in DEFAULT_BTC_MSYT_COLUMNS if column.endswith("_si")
)
DEFAULT_BATCHTIPSY_EXE_ENV = "FEMIC_BATCHTIPSY_EXE"
DEFAULT_BATCHTIPSY_WINDOWS_EXE = Path(r"C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe")
_BTC_SUPPORTED_MODES = {"TSR", "FLP"}
_BTC_REPORT_FILENAME_BY_MODE = {
    "TSR": "TimberSupply.rpt",
    "FLP": "ForestLandscapePlan.rpt",
}


@dataclass(frozen=True)
class BTCRuntimeDiscovery:
    """Resolved BTC executable discovery result."""

    executable_path: Path
    source: str


@dataclass(frozen=True)
class BTCRuntimePreparation:
    """Prepared BTC runtime layout for one supervised CLI run."""

    executable_path: Path
    install_root: Path
    working_dir: Path
    staged_input_csv: Path
    copied_install: bool
    report_template_path: Path | None


@dataclass(frozen=True)
class BTCRunResult:
    """Result payload for one supervised BTC CLI run."""

    run_id: str
    mode: str
    command: tuple[str, ...]
    manifest_path: Path
    stdout_log_path: Path
    stderr_log_path: Path
    output_csv_path: Path
    error_csv_path: Path
    executable_path: Path
    install_root: Path
    working_dir: Path
    copied_install: bool
    exit_code: int
    duration_sec: float
    report_template_path: Path | None


@dataclass(frozen=True)
class BTCCustomReportColumn:
    """One column entry in a BTC custom report template."""

    token: str
    width: int = 0
    header1_override: str = ""
    header2_override: str = ""
    units_override: str = ""

    def render(self) -> str:
        return "\t".join(
            [
                self.token,
                str(int(self.width)),
                self.header1_override,
                self.header2_override,
                self.units_override,
            ]
        ).rstrip()


@dataclass(frozen=True)
class BTCCustomReportTemplate:
    """Structured BTC custom report template."""

    name: str
    icon_id: int = 13
    identifier: str = "FirstIDcolumn"
    identifier_integer: bool = True
    report_type: str = "databaseByStand"
    output_format: str = "TAB"
    border: int = 500
    header_height: int = 250
    footer_height: int = 250
    header_flags: Mapping[str, str] | None = None
    columns: Sequence[BTCCustomReportColumn] = ()

    def render(self) -> str:
        header_flags = dict(self.header_flags or DEFAULT_BTC_REPORT_HEADER_FLAGS)
        lines = [
            "[CustomReport]",
            f"Name={self.name}",
            f"IconID={int(self.icon_id)}",
            f"Identifier={self.identifier}",
            f"IdentifierInteger={1 if self.identifier_integer else 0}",
            f"Type={self.report_type}",
            f"OutputFormat={self.output_format}",
            f"Border={int(self.border)}",
            f"HeaderHeight={int(self.header_height)}",
            f"FooterHeight={int(self.footer_height)}",
            "",
            "[CustomReportHeader]",
        ]
        lines.extend(f"{key}={value}" for key, value in header_flags.items())
        lines.extend(["", "[CustomReportColumns]", _BTC_REPORT_COLUMNS_COMMENT])
        lines.extend(column.render() for column in self.columns)
        return "\n".join(lines) + "\n"


def _parse_btc_column_line(raw_line: str) -> BTCCustomReportColumn:
    parts = [
        part.strip()
        for part in re.split(r"\t+|\s{2,}", raw_line.rstrip())
        if part.strip() != ""
    ]
    if not parts:
        raise ValueError("BTC custom report column line is empty")
    token = parts[0]
    width = 0
    header1_override = ""
    header2_override = ""
    units_override = ""
    if len(parts) >= 2:
        try:
            width = int(parts[1])
            if len(parts) >= 3:
                header1_override = parts[2]
            if len(parts) >= 4:
                header2_override = parts[3]
            if len(parts) >= 5:
                units_override = parts[4]
        except ValueError:
            header1_override = parts[1]
            if len(parts) >= 3:
                header2_override = parts[2]
            if len(parts) >= 4:
                units_override = parts[3]
    return BTCCustomReportColumn(
        token=token,
        width=width,
        header1_override=header1_override,
        header2_override=header2_override,
        units_override=units_override,
    )


def parse_btc_custom_report_template(template_path: str | Path) -> BTCCustomReportTemplate:
    """Parse a BTC ``.rpt`` custom report file into a structured template."""
    path = Path(template_path)
    text = path.read_text(encoding="utf-8")
    current_section: str | None = None
    report_values: dict[str, str] = {}
    header_values: dict[str, str] = {}
    columns: list[BTCCustomReportColumn] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            continue
        if current_section == "CustomReport":
            if "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            report_values[key.strip()] = value.strip()
            continue
        if current_section == "CustomReportHeader":
            if "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            header_values[key.strip()] = value.strip()
            continue
        if current_section == "CustomReportColumns":
            if line.startswith("'"):
                continue
            columns.append(_parse_btc_column_line(raw_line))
    if "Name" not in report_values:
        raise ValueError(f"BTC report template missing Name in {path}")
    return BTCCustomReportTemplate(
        name=report_values["Name"],
        icon_id=int(report_values.get("IconID", 13)),
        identifier=report_values.get("Identifier", "FirstIDcolumn"),
        identifier_integer=report_values.get("IdentifierInteger", "1") not in {"0", "false"},
        report_type=report_values.get("Type", "databaseByStand"),
        output_format=report_values.get("OutputFormat", "TAB"),
        border=int(report_values.get("Border", 500)),
        header_height=int(report_values.get("HeaderHeight", 250)),
        footer_height=int(report_values.get("FooterHeight", 250)),
        header_flags=header_values,
        columns=columns,
    )


def build_btc_custom_report_template(
    *,
    name: str,
    source_template: BTCCustomReportTemplate | None = None,
    columns: Sequence[BTCCustomReportColumn] | None = None,
    header_flags: Mapping[str, str] | None = None,
    icon_id: int | None = None,
    identifier: str | None = None,
    identifier_integer: bool | None = None,
    report_type: str | None = None,
    output_format: str | None = None,
    border: int | None = None,
    header_height: int | None = None,
    footer_height: int | None = None,
) -> BTCCustomReportTemplate:
    """Build a BTC custom report template from a preset or existing template."""
    base = source_template or BTCCustomReportTemplate(name=name)
    merged_header_flags = dict(base.header_flags or DEFAULT_BTC_REPORT_HEADER_FLAGS)
    if header_flags:
        merged_header_flags.update(header_flags)
    return BTCCustomReportTemplate(
        name=name,
        icon_id=icon_id if icon_id is not None else base.icon_id,
        identifier=identifier or base.identifier,
        identifier_integer=(
            identifier_integer
            if identifier_integer is not None
            else base.identifier_integer
        ),
        report_type=report_type or base.report_type,
        output_format=output_format or base.output_format,
        border=border if border is not None else base.border,
        header_height=header_height if header_height is not None else base.header_height,
        footer_height=footer_height if footer_height is not None else base.footer_height,
        header_flags=merged_header_flags,
        columns=list(columns if columns is not None else base.columns),
    )


def btc_report_template_preset(name: str) -> BTCCustomReportTemplate:
    """Return a vetted built-in BTC custom report template preset."""
    normalized = name.strip().lower().replace("_", "-")
    if normalized == "timber-supply-sql":
        return BTCCustomReportTemplate(
            name="Timber Supply SQL",
            icon_id=13,
            identifier="FirstIDcolumn",
            identifier_integer=True,
            report_type="databaseByStand",
            output_format="TAB",
            border=500,
            header_height=250,
            footer_height=250,
            header_flags=DEFAULT_BTC_REPORT_HEADER_FLAGS,
            columns=[
                BTCCustomReportColumn("Year", 0, "Year"),
                BTCCustomReportColumn("Volume:Auto:Con", 0, "VolumeCon"),
                BTCCustomReportColumn("Volume:Auto:Dec", 0, "VolumeDec"),
                BTCCustomReportColumn("Height:Auto:Con", 0, "HeightCon"),
                BTCCustomReportColumn("Height:Auto:Dec", 0, "HeightDec"),
            ],
        )
    if normalized == "tsr-unattended-default":
        return BTCCustomReportTemplate(
            name="TSR Unattended Default",
            icon_id=7,
            identifier="FirstIDcolumn",
            identifier_integer=False,
            report_type="transposed",
            output_format="CSV",
            border=500,
            header_height=250,
            footer_height=250,
            header_flags={},
            columns=[
                BTCCustomReportColumn("Volume:Auto:Con", 0, "MVcon", "{yr}"),
                BTCCustomReportColumn("Volume:Auto:Dec", 0, "MVdec", "{yr}"),
                BTCCustomReportColumn("Height:Con", 0, "HTcon", "{yr}"),
                BTCCustomReportColumn("Height:Dec", 0, "HTdec", "{yr}"),
                BTCCustomReportColumn("VolumeGross", 0, "gVol", "{yr}"),
                BTCCustomReportColumn("CC", 0, "CC", "{yr}"),
            ],
        )
    supported = ", ".join(_BTC_REPORT_PRESET_NAMES)
    raise ValueError(
        f"Unsupported BTC report template preset {name!r}. Supported presets: {supported}"
    )


def write_btc_custom_report_template(
    *,
    output_path: str | Path,
    template: BTCCustomReportTemplate,
) -> Path:
    """Write a BTC custom report template to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template.render(), encoding="utf-8")
    return path


def _write_tsr_unattended_runtime_template_from_stock(*, install_root: Path) -> Path:
    """Patch stock `TimberSupply.rpt` in place with the proven safe mashup columns."""
    template_path = install_root / _BTC_REPORT_FILENAME_BY_MODE["TSR"]
    text = template_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    additions = [
        "VolumeGross\t\tgVol\t{yr}",
        "CC\t\tCC\t{yr}",
    ]
    for addition in additions:
        token = addition.split("\t", 1)[0]
        if any(line.startswith(token) for line in lines):
            continue
        lines.append(addition)
    template_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return template_path


def resolve_btc_executable(
    *,
    executable_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> BTCRuntimeDiscovery:
    """Resolve the BatchTIPSY BTC executable path on Windows-first hosts."""
    candidates: list[tuple[Path | None, str]] = [
        (Path(executable_path) if executable_path is not None else None, "explicit"),
        (
            Path((env or os.environ)[DEFAULT_BATCHTIPSY_EXE_ENV])
            if (env or os.environ).get(DEFAULT_BATCHTIPSY_EXE_ENV)
            else None,
            f"env:{DEFAULT_BATCHTIPSY_EXE_ENV}",
        ),
        (DEFAULT_BATCHTIPSY_WINDOWS_EXE, "default"),
    ]
    for candidate, source in candidates:
        if candidate is None:
            continue
        resolved = candidate.expanduser()
        if resolved.exists():
            return BTCRuntimeDiscovery(
                executable_path=resolved.resolve(),
                source=source,
            )
    searched = ", ".join(str(path) for path, _source in candidates if path is not None)
    raise FileNotFoundError(
        "Could not resolve BatchTIPSY BTC executable. Checked: "
        f"{searched}. Set {DEFAULT_BATCHTIPSY_EXE_ENV} or pass an explicit path."
    )


def build_btc_cli_command(
    *,
    executable_path: str | Path,
    mode: str,
    input_csv: str | Path,
    output_csv: str | Path,
    error_csv: str | Path,
    extra_executable_args: Sequence[str | Path] = (),
) -> list[str]:
    """Build the concrete BTC CLI command for `/TSR` or `/FLP` execution."""
    normalized_mode = str(mode).strip().upper()
    if normalized_mode not in _BTC_SUPPORTED_MODES:
        supported = ", ".join(sorted(_BTC_SUPPORTED_MODES))
        raise ValueError(f"Unsupported BTC mode {mode!r}. Supported modes: {supported}")
    command = [str(Path(executable_path))]
    command.extend(str(arg) for arg in extra_executable_args)
    command.extend(
        [
            f"/{normalized_mode}",
            str(input_csv),
            str(output_csv),
            str(error_csv),
        ]
    )
    return command


def _write_btc_manifest(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_btc_runtime(
    *,
    executable_path: str | Path,
    input_csv: str | Path,
    scratch_root: str | Path,
    mode: str,
    report_template: BTCCustomReportTemplate | str | Path | None = None,
    report_preset_name: str | None = None,
    copy_install: bool = False,
) -> BTCRuntimePreparation:
    """Stage a writable BTC runtime root and input CSV for one run."""
    resolved_exe = Path(executable_path).expanduser().resolve()
    install_root = resolved_exe.parent
    resolved_scratch_root = Path(scratch_root).expanduser().resolve()
    resolved_scratch_root.mkdir(parents=True, exist_ok=True)
    effective_install_root = install_root
    effective_executable = resolved_exe
    copied = False
    report_target_path: Path | None = None
    if copy_install or report_template is not None:
        effective_install_root = resolved_scratch_root / "btc_install"
        if effective_install_root.exists():
            shutil.rmtree(effective_install_root)
        shutil.copytree(install_root, effective_install_root)
        effective_executable = effective_install_root / resolved_exe.name
        copied = True
    normalized_mode = str(mode).upper()
    if report_preset_name == "tsr-unattended-default":
        if normalized_mode != "TSR":
            raise ValueError(
                "The tsr-unattended-default runtime preset only supports mode=TSR."
            )
        report_target_path = _write_tsr_unattended_runtime_template_from_stock(
            install_root=effective_install_root
        )
    elif report_template is not None:
        report_target_path = effective_install_root / _BTC_REPORT_FILENAME_BY_MODE[normalized_mode]
        if isinstance(report_template, BTCCustomReportTemplate):
            write_btc_custom_report_template(
                output_path=report_target_path,
                template=report_template,
            )
        else:
            source_text = Path(report_template).read_text(encoding="utf-8")
            report_target_path.write_text(source_text, encoding="utf-8")
    working_dir = resolved_scratch_root / "work"
    working_dir.mkdir(parents=True, exist_ok=True)
    staged_input = working_dir / Path(input_csv).name
    shutil.copy2(Path(input_csv), staged_input)
    return BTCRuntimePreparation(
        executable_path=effective_executable,
        install_root=effective_install_root,
        working_dir=working_dir,
        staged_input_csv=staged_input,
        copied_install=copied,
        report_template_path=report_target_path,
    )


def run_btc_cli(
    *,
    input_csv: str | Path,
    mode: str = "TSR",
    output_csv: str | Path | None = None,
    error_csv: str | Path | None = None,
    executable_path: str | Path | None = None,
    report_template: BTCCustomReportTemplate | str | Path | None = None,
    report_preset_name: str | None = None,
    copy_install: bool | None = None,
    scratch_root: str | Path | None = None,
    log_dir: str | Path = Path("vdyp_io/logs"),
    run_id: str | None = None,
    env: Mapping[str, str] | None = None,
    extra_executable_args: Sequence[str | Path] = (),
) -> BTCRunResult:
    """Run BTC `/TSR` or `/FLP` in a supervised writable scratch environment."""
    discovery = resolve_btc_executable(executable_path=executable_path, env=env)
    normalized_mode = str(mode).strip().upper()
    if normalized_mode not in _BTC_SUPPORTED_MODES:
        supported = ", ".join(sorted(_BTC_SUPPORTED_MODES))
        raise ValueError(f"Unsupported BTC mode {mode!r}. Supported modes: {supported}")
    resolved_log_dir = Path(log_dir).expanduser().resolve()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    effective_run_id = run_id or datetime.now(UTC).strftime("btc_%Y%m%dT%H%M%SZ")
    resolved_scratch_root = (
        Path(scratch_root).expanduser().resolve()
        if scratch_root is not None
        else (resolved_log_dir / f"btc_scratch-{effective_run_id}").resolve()
    )
    should_copy_install = bool(copy_install) if copy_install is not None else (
        report_template is not None or report_preset_name is not None
    )
    prep = prepare_btc_runtime(
        executable_path=discovery.executable_path,
        input_csv=input_csv,
        scratch_root=resolved_scratch_root,
        mode=normalized_mode,
        report_template=report_template,
        report_preset_name=report_preset_name,
        copy_install=should_copy_install,
    )
    input_path = Path(input_csv).expanduser().resolve()
    if output_csv is not None:
        requested_output = Path(output_csv).expanduser().resolve()
        staged_output = prep.working_dir / requested_output.name
    else:
        staged_output = prep.working_dir / f"{input_path.stem}_output.csv"
        requested_output = staged_output
    if error_csv is not None:
        requested_error = Path(error_csv).expanduser().resolve()
        staged_error = prep.working_dir / requested_error.name
    else:
        staged_error = prep.working_dir / f"{input_path.stem}_error.csv"
        requested_error = staged_error
    command = build_btc_cli_command(
        executable_path=prep.executable_path,
        mode=normalized_mode,
        input_csv=prep.staged_input_csv.name,
        output_csv=staged_output.name,
        error_csv=staged_error.name,
        extra_executable_args=extra_executable_args,
    )
    stdout_log_path = resolved_log_dir / f"btc_stdout-{effective_run_id}.log"
    stderr_log_path = resolved_log_dir / f"btc_stderr-{effective_run_id}.log"
    manifest_path = resolved_log_dir / f"btc_manifest-{effective_run_id}.json"
    started_at = datetime.now(UTC)
    manifest_started = {
        "run_id": effective_run_id,
        "status": "started",
        "mode": normalized_mode,
        "started_at_utc": started_at.isoformat(),
        "command": command,
        "log_dir": str(resolved_log_dir),
        "input_csv": str(Path(input_csv).expanduser().resolve()),
        "staged_input_csv": str(prep.staged_input_csv),
        "output_csv": str(requested_output),
        "error_csv": str(requested_error),
        "staged_output_csv": str(staged_output),
        "staged_error_csv": str(staged_error),
        "executable_path": str(prep.executable_path),
        "install_root": str(prep.install_root),
        "copied_install": prep.copied_install,
        "report_template_path": (
            str(prep.report_template_path) if prep.report_template_path else None
        ),
        "discovery_source": discovery.source,
    }
    _write_btc_manifest(manifest_path, manifest_started)
    started_monotonic = time.monotonic()
    merged_env = dict(os.environ)
    merged_env.update(env or {})
    completed = subprocess.run(
        command,
        cwd=prep.working_dir,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_sec = round(time.monotonic() - started_monotonic, 3)
    stdout_log_path.write_text(completed.stdout, encoding="utf-8")
    stderr_log_path.write_text(completed.stderr, encoding="utf-8")
    finished_at = datetime.now(UTC)
    error_message = None
    try:
        if not staged_output.exists():
            raise RuntimeError(
                f"BTC did not create expected output file: {staged_output} "
                f"(exit_code={completed.returncode})"
            )
        if not staged_error.exists():
            raise RuntimeError(
                f"BTC did not create expected error file: {staged_error} "
                f"(exit_code={completed.returncode})"
            )
        if requested_output != staged_output:
            requested_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_output, requested_output)
        if requested_error != staged_error:
            requested_error.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_error, requested_error)
    except Exception as exc:
        error_message = str(exc)
        from femic.pipeline.manifest import collect_runtime_versions

        _write_btc_manifest(
            manifest_path,
            {
                **manifest_started,
                "status": "failed",
                "finished_at_utc": finished_at.isoformat(),
                "duration_sec": duration_sec,
                "exit_code": completed.returncode,
                "error_message": error_message,
                "stdout_log_path": str(stdout_log_path),
                "stderr_log_path": str(stderr_log_path),
                "runtime_versions": collect_runtime_versions(),
                "artifacts": {
                    "output_csv": {
                        "path": str(requested_output),
                        "exists": requested_output.exists(),
                    },
                    "error_csv": {
                        "path": str(requested_error),
                        "exists": requested_error.exists(),
                    },
                    "stdout_log": {
                        "path": str(stdout_log_path),
                        "exists": stdout_log_path.exists(),
                    },
                    "stderr_log": {
                        "path": str(stderr_log_path),
                        "exists": stderr_log_path.exists(),
                    },
                },
            },
        )
        raise
    from femic.pipeline.manifest import collect_runtime_versions

    manifest_finished = {
        **manifest_started,
        "status": "ok" if completed.returncode == 0 else "failed",
        "finished_at_utc": finished_at.isoformat(),
        "duration_sec": duration_sec,
        "exit_code": completed.returncode,
        "error_message": error_message,
        "stdout_log_path": str(stdout_log_path),
        "stderr_log_path": str(stderr_log_path),
        "runtime_versions": collect_runtime_versions(),
        "artifacts": {
            "output_csv": {
                "path": str(requested_output),
                "exists": requested_output.exists(),
            },
            "error_csv": {
                "path": str(requested_error),
                "exists": requested_error.exists(),
            },
            "stdout_log": {
                "path": str(stdout_log_path),
                "exists": stdout_log_path.exists(),
            },
            "stderr_log": {
                "path": str(stderr_log_path),
                "exists": stderr_log_path.exists(),
            },
        },
    }
    _write_btc_manifest(manifest_path, manifest_finished)
    return BTCRunResult(
        run_id=effective_run_id,
        mode=normalized_mode,
        command=tuple(command),
        manifest_path=manifest_path,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
        output_csv_path=requested_output,
        error_csv_path=requested_error,
        executable_path=prep.executable_path,
        install_root=prep.install_root,
        working_dir=prep.working_dir,
        copied_install=prep.copied_install,
        exit_code=completed.returncode,
        duration_sec=duration_sec,
        report_template_path=prep.report_template_path,
    )


DEFAULT_TIPSY_BATCH_COLUMNS_1BASED: dict[str, tuple[int, int]] = {
    # Canonical BatchTIPSY GUI ranges from user screenshots.
    "AU": (1, 6),
    "TBLno": (7, 12),
    "BEC": (14, 17),
    # Keep proportion in a wider field so values like 0.3/0.85 fit while
    # preserving the downstream BatchTIPSY column anchors in user runbooks.
    "Proportion": (31, 39),
    "Regen_Delay": (40, 42),
    "Density": (47, 51),
    "PCT_1": (61, 63),
    "Regen_Method": (64, 64),
    "Util_DBH_cm": (74, 77),
    "OAF1": (80, 83),
    "OAF2": (86, 89),
    "FIZ": (93, 93),
    "SPP_1": (97, 99),
    "SI": (108, 111),
    "GW_1": (113, 116),
    "GW_age_1": (123, 125),
    "SPP_2": (129, 131),
    "PCT_2": (136, 137),
    "GW_2": (139, 142),
    "GW_age_2": (149, 151),
    "SPP_3": (155, 157),
    "PCT_3": (162, 163),
    "GW_3": (165, 168),
    "GW_age_3": (175, 177),
    "SPP_4": (181, 183),
    "PCT_4": (188, 189),
    "GW_4": (191, 194),
    "GW_age_4": (201, 203),
    "SPP_5": (207, 209),
    "PCT_5": (214, 215),
    "GW_5": (217, 220),
    "GW_age_5": (229, 231),
}
DEFAULT_TIPSY_DAT_ROW_STARTS: dict[str, int] = {
    col: start - 1 for col, (start, _end) in DEFAULT_TIPSY_BATCH_COLUMNS_1BASED.items()
}
DEFAULT_TIPSY_DAT_ROW_WIDTHS: dict[str, int] = {
    col: (end - start + 1)
    for col, (start, end) in DEFAULT_TIPSY_BATCH_COLUMNS_1BASED.items()
}
DEFAULT_TIPSY_DAT_HEADER_STARTS: dict[str, int] = {
    **DEFAULT_TIPSY_DAT_ROW_STARTS,
    "AU": 3,
}
_TIPSY_TEXT_COLUMNS = {
    "BEC",
    "Regen_Method",
    "FIZ",
    "SPP_1",
    "SPP_2",
    "SPP_3",
    "SPP_4",
    "SPP_5",
}


def _tipsy_dat_widths_from_starts(starts: Mapping[str, int]) -> dict[str, int]:
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    widths: dict[str, int] = {}
    for idx, (key, start) in enumerate(ordered):
        next_start = ordered[idx + 1][1] if idx + 1 < len(ordered) else 231
        widths[key] = int(next_start - start)
    return widths


DEFAULT_TIPSY_DAT_COL_WIDTHS = DEFAULT_TIPSY_DAT_ROW_WIDTHS.copy()
DEFAULT_TIPSY_DAT_LINE_LENGTH = 231


def _format_tipsy_dat_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(float(value)):
            return ""
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _render_tipsy_dat_line(
    *,
    values: Mapping[str, Any],
    starts: Mapping[str, int],
    widths: Mapping[str, int],
    left_align_all: bool = False,
) -> str:
    line_len = max(starts[col] + widths[col] for col in starts)
    chars = [" "] * int(line_len)
    for col, start in starts.items():
        width = int(widths[col])
        text = _format_tipsy_dat_value(values.get(col, ""))[:width]
        if left_align_all or col in _TIPSY_TEXT_COLUMNS or col in {"AU", "TBLno"}:
            field = text.ljust(width)
        else:
            field = text.rjust(width)
        chars[start : start + width] = list(field)
    return "".join(chars)


def _validate_tipsy_dat_row(
    *,
    line: str,
    values: Mapping[str, Any],
    starts: Mapping[str, int],
    widths: Mapping[str, int],
) -> None:
    if len(line) != DEFAULT_TIPSY_DAT_LINE_LENGTH:
        raise ValueError(
            f"TIPSY DAT row length {len(line)} != expected {DEFAULT_TIPSY_DAT_LINE_LENGTH}"
        )
    for col in starts:
        expected = _format_tipsy_dat_value(values.get(col, ""))
        width = int(widths[col])
        if len(expected) > width:
            raise ValueError(
                f"TIPSY DAT value overflow for {col}: {expected!r} exceeds width {width}"
            )
        start = int(starts[col])
        actual = line[start : start + width].strip()
        if expected != actual:
            raise ValueError(
                f"TIPSY DAT slice mismatch for {col}: expected={expected!r}, actual={actual!r}"
            )


@dataclass(frozen=True)
class TIPSYCandidateEvaluation:
    """Eligibility outcome and derived metrics for one stratum+SI candidate."""

    eligible: bool
    reason: str | None
    species_map: Mapping[str, Any]
    leading_species: str | None
    bec: str
    max_vol: float
    min_vol: float
    operable_years: float
    si_vri_iqrlo: float
    si_spr_iqrlo: float
    si_vri_med: float
    si_spr_med: float
    min_si: float | None


def _tipsy_candidate_exception_types() -> tuple[type[Exception], ...]:
    """Candidate-evaluation failures that preserve legacy debug+re-raise behavior."""
    return (ValueError, KeyError, TypeError, AttributeError, RuntimeError, IndexError)


def compute_vdyp_site_index(
    vdyp_out: Mapping[Any, Any],
    *,
    ndigits: int = 1,
) -> float:
    """Compute mean SI across VDYP output tables, rounded for TIPSY input."""
    values: list[float] = []
    for table in vdyp_out.values():
        try:
            value = float(table["SI"].mean())
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            continue
        if np.isfinite(value):
            values.append(value)
    if not values:
        return float("nan")
    return round(float(np.mean(values)), ndigits)


def compute_vdyp_oaf1(vdyp_out: Mapping[Any, Any]) -> float:
    """Compute OAF1 from mean VDYP `% Stk` values, handling malformed tables."""
    stockability: list[float] = []
    for table in vdyp_out.values():
        try:
            value = float(table["% Stk"].iloc[0])
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            continue
        if np.isfinite(value):
            stockability.append(value)
    if not stockability:
        return float("nan")
    return round(float(np.mean(stockability)) * 0.01, 2)


def build_tipsy_warning_event(
    *,
    tsa: str,
    stratumi: int,
    sc: str,
    si_level: str | None,
    au: int | None,
    reason: str,
) -> dict[str, Any]:
    """Build standardized warning payload for TIPSY-input stage issues."""
    return build_timestamped_event(
        event="vdyp_curve_fit",
        status="warning",
        stage="tipsy_input",
        reason=reason,
        context={
            "tsa": tsa,
            "stratum_index": int(stratumi),
            "stratum_code": sc,
            "si_level": si_level,
            "au": (int(au) if au is not None else None),
        },
    )


def build_tipsy_input_table(
    *,
    tipsy_params_for_tsa: Mapping[int, Mapping[str, Mapping[str, Any]]],
    tipsy_params_columns: Sequence[str],
    pd_module: Any,
    table_key: str = "f",
) -> Any:
    """Build TIPSY input table rows from per-AU parameter payloads."""
    rows: list[Any] = []
    for au in tipsy_params_for_tsa:
        table_map = tipsy_params_for_tsa[au].get(table_key)
        if table_map is None:
            continue
        if "TBLno" not in table_map:
            raise KeyError(f"missing TBLno in tipsy_params[{au!r}][{table_key!r}]")
        rows.append(pd_module.DataFrame(table_map, index=[table_map["TBLno"]]))
    if not rows:
        raise RuntimeError("No TIPSY parameter tables generated.")
    return pd_module.concat(rows)[list(tipsy_params_columns)]


def _btc_msyt_bec_fields(value: Any) -> tuple[str, str]:
    text = "" if value is None else str(value).strip()
    if not text:
        return "", ""
    match = re.match(r"^([A-Z]+)([a-z]+)", text)
    if match:
        return match.group(1), match.group(2)
    return text, ""


def _btc_species_code(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    lowered = text.lower()
    return lowered[:1].upper() + lowered[1:]


def _btc_site_index_column_for_species(species_code: str) -> str | None:
    normalized = species_code.strip().lower()
    if not normalized:
        return None
    key = f"{normalized[:2]}_si"
    if key in _BTC_MSYT_SITE_INDEX_COLUMNS:
        return key
    return None


def _btc_numeric_or_blank(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        return stripped
    try:
        if value != value:  # NaN
            return ""
    except Exception:
        return value
    return value


def _btc_density_from_percent(*, total_density: Any, percent: Any) -> Any:
    total = _btc_numeric_or_blank(total_density)
    pct = _btc_numeric_or_blank(percent)
    if total == "" or pct == "":
        return ""
    total_float = float(total)
    pct_float = float(pct)
    return int(round(total_float * (pct_float / 100.0)))


def build_btc_msyt_input_table(
    *,
    tipsy_table: Any,
    pd_module: Any,
) -> Any:
    """Build BTC `MSYT.csv` input rows from the current TIPSY `f`-table payload."""
    table = tipsy_table.copy()
    unnamed_cols = [col for col in table.columns if str(col).startswith("Unnamed:")]
    if unnamed_cols:
        table = table.drop(columns=unnamed_cols)

    rows: list[dict[str, Any]] = []
    for record in table.to_dict(orient="records"):
        bec_zone, bec_subzone = _btc_msyt_bec_fields(record.get("BEC"))
        row: dict[str, Any] = {column: "" for column in DEFAULT_BTC_MSYT_COLUMNS}
        for si_column in _BTC_MSYT_SITE_INDEX_COLUMNS:
            row[si_column] = 0

        au = record.get("AU")
        feature_id = int(au) if _btc_numeric_or_blank(au) != "" else ""
        row["feature_id"] = feature_id
        row["bec_zone"] = bec_zone
        row["bec_subzone"] = bec_subzone
        row["planting_delay"] = _btc_numeric_or_blank(record.get("Regen_Delay"))
        proportion = _btc_numeric_or_blank(record.get("Proportion"))
        row["planted_percent"] = (
            int(round(float(proportion) * 100.0)) if proportion != "" else ""
        )
        row["oaf1"] = _btc_numeric_or_blank(record.get("OAF1"))
        row["oaf2"] = _btc_numeric_or_blank(record.get("OAF2"))
        row["opening_id"] = feature_id
        row["vri_ref_age"] = 0
        row["vri_ref_sph"] = 0

        for i in range(1, 6):
            species_key = f"SPP_{i}"
            percent_key = f"PCT_{i}"
            gw_key = f"GW_{i}"
            btc_species = _btc_species_code(record.get(species_key))
            if not btc_species:
                continue
            planted_species_col = f"planted_species{i}"
            planted_density_col = f"planted_density{i}"
            genetic_worth_col = f"genetic_worth{i}"
            row[planted_species_col] = btc_species
            row[planted_density_col] = _btc_density_from_percent(
                total_density=record.get("Density"),
                percent=record.get(percent_key),
            )
            row[genetic_worth_col] = _btc_numeric_or_blank(record.get(gw_key))
            site_column: str | None = _btc_site_index_column_for_species(btc_species)
            if site_column is not None:
                row[site_column] = _btc_numeric_or_blank(record.get("SI")) or 0

        rows.append(row)

    if not rows:
        raise RuntimeError("No BTC MSYT input rows generated.")
    return pd_module.DataFrame(rows)[list(DEFAULT_BTC_MSYT_COLUMNS)]


def write_btc_msyt_input_csv(
    *,
    btc_msyt_table: Any,
    tsa: str,
    output_root: str | Path = "data",
    filename_template: str = "03_input-tsa{tsa}.csv",
) -> Path:
    """Write the BTC canonical `MSYT.csv` handoff for one TSA."""
    output_path = Path(output_root) / filename_template.format(tsa=tsa)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    btc_msyt_table.to_csv(output_path, index=False)
    return output_path


def write_tipsy_input_exports(
    *,
    tipsy_table: Any,
    tsa: str,
    tipsy_params_path_prefix: str,
    dat_path_template: str = "./data/02_input-tsa{tsa}.dat",
) -> tuple[str, str]:
    """Write TIPSY input exports to XLSX and DAT outputs for one TSA."""
    table = tipsy_table.copy()
    unnamed_cols = [col for col in table.columns if str(col).startswith("Unnamed:")]
    if unnamed_cols:
        table = table.drop(columns=unnamed_cols)

    tipsy_excel_path = f"{tipsy_params_path_prefix}{tsa}.xlsx"
    tipsy_dat_path = dat_path_template.format(tsa=tsa)
    ordered_cols = list(DEFAULT_TIPSY_DAT_ROW_STARTS.keys())
    for col in ordered_cols:
        if col not in table.columns:
            table[col] = ""
    row_starts = {col: DEFAULT_TIPSY_DAT_ROW_STARTS[col] for col in ordered_cols}
    row_widths = {col: DEFAULT_TIPSY_DAT_ROW_WIDTHS[col] for col in ordered_cols}
    header_starts = {col: DEFAULT_TIPSY_DAT_HEADER_STARTS[col] for col in ordered_cols}
    header_widths = _tipsy_dat_widths_from_starts(header_starts)
    lines = [
        _render_tipsy_dat_line(
            values={col: col for col in ordered_cols},
            starts=header_starts,
            widths=header_widths,
            left_align_all=True,
        )
    ]
    for row in table[ordered_cols].itertuples(index=False):
        row_map = {col: val for col, val in zip(ordered_cols, row)}
        row_line = _render_tipsy_dat_line(
            values=row_map,
            starts=row_starts,
            widths=row_widths,
        )
        _validate_tipsy_dat_row(
            line=row_line,
            values=row_map,
            starts=row_starts,
            widths=row_widths,
        )
        lines.append(row_line)
    Path(tipsy_dat_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        table.to_excel(
            tipsy_excel_path,
            index=False,
            sheet_name="TIPSY_inputTBL",
        )
    except PermissionError:
        fallback_path = str(
            Path(tipsy_excel_path).with_name(
                f"{Path(tipsy_excel_path).stem}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
        )
        table.to_excel(
            fallback_path,
            index=False,
            sheet_name="TIPSY_inputTBL",
        )
        tipsy_excel_path = fallback_path
    return tipsy_excel_path, tipsy_dat_path


def tipsy_params_excel_path(
    *,
    tsa: str,
    tipsy_params_path_prefix: str | Path,
) -> Path:
    """Build legacy per-TSA TIPSY parameter workbook path."""
    return Path(f"{tipsy_params_path_prefix}{tsa}.xlsx")


def tipsy_input_dat_path(
    *,
    tsa: str,
    input_root: str | Path = "data",
    filename_template: str = "02_input-tsa{tsa}.dat",
) -> Path:
    """Build legacy per-TSA BatchTIPSY DAT handoff path."""
    return Path(input_root) / filename_template.format(tsa=tsa)


def btc_msyt_input_csv_path(
    *,
    tsa: str,
    input_root: str | Path = "data",
    filename_template: str = "03_input-tsa{tsa}.csv",
) -> Path:
    """Build canonical per-TSA BTC `MSYT.csv` handoff path."""
    return Path(input_root) / filename_template.format(tsa=tsa)


def tipsy_stage_output_paths(
    *,
    tsa: str,
    output_root: str | Path = "data",
) -> tuple[Path, Path]:
    """Build legacy 01b per-TSA output CSV paths."""
    root = Path(output_root)
    return (
        root / f"tipsy_curves_tsa{tsa}.csv",
        root / f"tipsy_sppcomp_tsa{tsa}.csv",
    )


def validate_tipsy_output_is_fresh(
    *,
    tipsy_input_excel_path: str | Path,
    tipsy_input_dat_path: str | Path | None = None,
    tipsy_output_path: str | Path,
    allow_stale: bool = False,
    strict_timestamp_mismatch: bool = False,
) -> None:
    """Fail fast when BatchTIPSY output is stale against canonical input DAT.

    Canonical operator contract uses ``02_input-tsaXX.dat`` as the real
    BatchTIPSY input; ``tipsy_params_tsaXX.xlsx`` is a human-readable mirror.
    This catches stale-output scenarios that would silently yield mismatched
    treated-curve overlays and downstream artifacts, while allowing repeated
    FEMIC reruns to reuse existing BatchTIPSY output when DAT content is
    unchanged.
    """
    if allow_stale:
        return
    excel_path = Path(tipsy_input_excel_path)
    dat_path = Path(tipsy_input_dat_path) if tipsy_input_dat_path else None
    output_path = Path(tipsy_output_path)
    if not output_path.is_file():
        return
    if dat_path is not None and not dat_path.is_file():
        raise RuntimeError(
            "Missing canonical BatchTIPSY input DAT file: "
            f"{dat_path}. Generate 02_input-tsaXX.dat in Stage 01a before "
            "running Stage 01b/post-TIPSY."
        )

    if dat_path is not None:
        dat_sha256 = compute_file_sha256(dat_path)
        fingerprint_path = tipsy_output_input_fingerprint_path(
            tipsy_output_path=output_path
        )
        known_sha = (
            fingerprint_path.read_text(encoding="utf-8").strip()
            if fingerprint_path.is_file()
            else None
        )
        if known_sha:
            if known_sha != dat_sha256:
                raise RuntimeError(
                    "Stale BatchTIPSY output detected: "
                    f"{output_path} was recorded against a different "
                    f"02_input-tsaXX.dat fingerprint ({known_sha} != {dat_sha256}). "
                    "Regenerate 04_output-tsaXX.out from the current "
                    "02_input-tsaXX.dat handoff, then rerun FEMIC stage "
                    "01b/post-TIPSY."
                )
            return
        input_mtime = dat_path.stat().st_mtime
    elif excel_path.is_file():
        input_mtime = excel_path.stat().st_mtime
    else:
        return

    output_mtime = output_path.stat().st_mtime
    if output_mtime < input_mtime:
        coherence = assess_tipsy_input_output_coherence(
            tipsy_input_excel_path=excel_path,
            tipsy_output_path=output_path,
        )
        if coherence.coherent:
            detail = (
                "Timestamp mismatch detected but TIPSY input/output appear coherent: "
                f"{coherence.summary}"
            )
            if strict_timestamp_mismatch:
                raise RuntimeError(
                    "Strict BatchTIPSY freshness is enabled and "
                    f"{output_path} is older than {dat_path or excel_path}. "
                    f"{detail} Regenerate 04_output-tsaXX.out from current "
                    "02_input-tsaXX.dat before rerunning."
                )
            warnings.warn(
                detail
                + " Continuing with existing 04_output-tsaXX.out (default behavior). "
                "Set FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH=1 to escalate this to an error.",
                RuntimeWarning,
                stacklevel=2,
            )
            return
        raise RuntimeError(
            "Stale BatchTIPSY output detected: "
            f"{output_path} is older than {dat_path or excel_path}. "
            f"Coherence check did not pass ({coherence.summary}). "
            "Regenerate 04_output-tsaXX.out from the current "
            "02_input-tsaXX.dat handoff (and matching workbook), then rerun "
            "FEMIC stage 01b/post-TIPSY. Future reruns can avoid repeated "
            "manual prompts when DAT content is unchanged once a fingerprint "
            "is recorded."
        )


@dataclass(frozen=True)
class TipsyInputOutputCoherence:
    coherent: bool
    summary: str
    expected_au_count: int
    expected_table_count: int
    observed_table_count: int


def assess_tipsy_input_output_coherence(
    *,
    tipsy_input_excel_path: str | Path,
    tipsy_output_path: str | Path,
) -> TipsyInputOutputCoherence:
    """Assess whether TIPSY input and output look structurally coherent."""
    excel_path = Path(tipsy_input_excel_path)
    output_path = Path(tipsy_output_path)
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return TipsyInputOutputCoherence(
            coherent=False,
            summary="pandas is unavailable for coherence parsing",
            expected_au_count=0,
            expected_table_count=0,
            observed_table_count=0,
        )

    try:
        input_df = pd.read_excel(
            excel_path,
            sheet_name="TIPSY_inputTBL",
            usecols=["AU", "TBLno", "SI"],
        )
    except Exception as exc:  # pragma: no cover - defensive parse boundary
        return TipsyInputOutputCoherence(
            coherent=False,
            summary=f"could not parse input workbook: {exc}",
            expected_au_count=0,
            expected_table_count=0,
            observed_table_count=0,
        )
    if input_df.empty:
        return TipsyInputOutputCoherence(
            coherent=False,
            summary="input workbook has no rows",
            expected_au_count=0,
            expected_table_count=0,
            observed_table_count=0,
        )
    if "SI" in input_df.columns:
        input_df = input_df[pd.to_numeric(input_df["SI"], errors="coerce") > 0]
    input_df = input_df.dropna(subset=["AU", "TBLno"])
    if input_df.empty:
        return TipsyInputOutputCoherence(
            coherent=False,
            summary="input workbook has no valid AU/TBLno rows",
            expected_au_count=0,
            expected_table_count=0,
            observed_table_count=0,
        )

    input_df["AU"] = pd.to_numeric(input_df["AU"], errors="coerce")
    input_df["TBLno"] = pd.to_numeric(input_df["TBLno"], errors="coerce")
    input_df = input_df.dropna(subset=["AU", "TBLno"])
    input_df["AU"] = input_df["AU"].astype(int)
    input_df["TBLno"] = input_df["TBLno"].astype(int)
    expected_tables = set(input_df["TBLno"].tolist())
    expected_aus = set(input_df["AU"].tolist())

    try:
        output_df = pd.read_csv(
            output_path,
            low_memory=False,
            header=None,
            skiprows=4,
            sep=r"\s+",
            usecols=[0],
        )
    except Exception as exc:  # pragma: no cover - defensive parse boundary
        return TipsyInputOutputCoherence(
            coherent=False,
            summary=f"could not parse output tables: {exc}",
            expected_au_count=len(expected_aus),
            expected_table_count=len(expected_tables),
            observed_table_count=0,
        )
    if output_df.empty:
        return TipsyInputOutputCoherence(
            coherent=False,
            summary="output table list is empty",
            expected_au_count=len(expected_aus),
            expected_table_count=len(expected_tables),
            observed_table_count=0,
        )

    observed_tables = set(
        pd.to_numeric(output_df.iloc[:, 0], errors="coerce")
        .dropna()
        .astype(int)
        .tolist()
    )
    missing_tables = sorted(expected_tables - observed_tables)
    covered_aus = set(input_df[input_df["TBLno"].isin(observed_tables)]["AU"].tolist())
    missing_aus = sorted(expected_aus - covered_aus)
    coherent = (not missing_tables) and (not missing_aus)
    summary = (
        f"expected_aus={len(expected_aus)} expected_tables={len(expected_tables)} "
        f"observed_tables={len(observed_tables)} missing_tables={len(missing_tables)} "
        f"missing_aus={len(missing_aus)}"
    )
    if missing_tables:
        summary += f" missing_table_ids={missing_tables[:8]}"
    if missing_aus:
        summary += f" missing_au_ids={missing_aus[:8]}"
    return TipsyInputOutputCoherence(
        coherent=coherent,
        summary=summary,
        expected_au_count=len(expected_aus),
        expected_table_count=len(expected_tables),
        observed_table_count=len(observed_tables),
    )


def tipsy_output_input_fingerprint_path(*, tipsy_output_path: str | Path) -> Path:
    """Return sidecar path storing the DAT fingerprint paired with TIPSY output."""
    output_path = Path(tipsy_output_path)
    return output_path.with_name(f"{output_path.name}.input_sha256")


def compute_file_sha256(path: str | Path) -> str:
    """Compute deterministic SHA256 digest for file content."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_tipsy_output_input_fingerprint(
    *,
    tipsy_input_dat_path: str | Path | None,
    tipsy_output_path: str | Path,
) -> Path | None:
    """Persist DAT SHA256 used for the accepted BatchTIPSY output."""
    if tipsy_input_dat_path is None:
        return None
    dat_path = Path(tipsy_input_dat_path)
    output_path = Path(tipsy_output_path)
    if not dat_path.is_file() or not output_path.is_file():
        return None
    digest = compute_file_sha256(dat_path)
    fingerprint_path = tipsy_output_input_fingerprint_path(
        tipsy_output_path=output_path
    )
    fingerprint_path.write_text(f"{digest}\n", encoding="utf-8")
    return fingerprint_path


def evaluate_tipsy_candidate(
    *,
    sc: str,
    vdyp_curve_df: Any,
    result_si: Mapping[str, Any],
    exclusion: Mapping[str, Any],
    min_operable_years: float,
    si_iqrlo_quantile: float,
    siteprod_si_fallback_by_species: Mapping[str, float] | None = None,
) -> TIPSYCandidateEvaluation:
    """Evaluate whether a stratum+SI candidate is usable for TIPSY parameter generation."""
    sc_tokens = sc.split("_")
    if len(sc_tokens) < 2 or not sc_tokens[1]:
        raise ValueError(f"invalid stratum code format: {sc!r}")
    bec = sc_tokens[0]
    min_vol = float(exclusion["min_vol"](sc_tokens[1][0]))
    max_vol = float(vdyp_curve_df.volume.max())
    if max_vol < min_vol:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="max_vol_too_low",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=float("nan"),
            si_vri_iqrlo=float("nan"),
            si_spr_iqrlo=float("nan"),
            si_vri_med=float("nan"),
            si_spr_med=float("nan"),
            min_si=None,
        )
    operable_ages = vdyp_curve_df[vdyp_curve_df.volume >= min_vol].age
    operable_years = float(operable_ages.max() - operable_ages.min())
    if operable_years < min_operable_years:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="operability_window_too_narrow",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=float("nan"),
            si_spr_iqrlo=float("nan"),
            si_vri_med=float("nan"),
            si_spr_med=float("nan"),
            min_si=None,
        )
    ss = result_si["ss"]
    si_vri_iqrlo = float(ss.SITE_INDEX.quantile(si_iqrlo_quantile))
    si_vri_med = float(ss.SITE_INDEX.median())
    siteprod_series = ss.get("siteprod")
    if siteprod_series is None:
        si_spr_iqrlo = si_vri_iqrlo
        si_spr_med = si_vri_med
    else:
        siteprod_series = siteprod_series.dropna()
        siteprod_series = siteprod_series[siteprod_series > 0]
        if siteprod_series.empty:
            si_spr_iqrlo = si_vri_iqrlo
            si_spr_med = si_vri_med
        else:
            si_spr_iqrlo = float(siteprod_series.quantile(si_iqrlo_quantile))
            si_spr_med = float(siteprod_series.median())
    species_map: Mapping[str, Any] = result_si.get("species", {})
    if not species_map:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="no_species_candidates",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=None,
        )
    leading_species = list(species_map.keys())[0]
    if (siteprod_series is None) or siteprod_series.empty:
        fallback_si = None
        if siteprod_si_fallback_by_species:
            fallback_si = siteprod_si_fallback_by_species.get(
                str(leading_species).upper()
            )
        if fallback_si is not None and np.isfinite(float(fallback_si)):
            si_spr_iqrlo = float(fallback_si)
            si_spr_med = float(fallback_si)
    min_si = float(exclusion["min_si"](leading_species))
    if min(si_vri_iqrlo, si_spr_iqrlo) < min_si:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="si_too_low",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    if leading_species in exclusion["excl_leading_species"]:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="excluded_leading_species",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    if bec in exclusion["excl_bec"]:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="excluded_bec",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    return TIPSYCandidateEvaluation(
        eligible=True,
        reason=None,
        species_map=species_map,
        leading_species=leading_species,
        bec=bec,
        max_vol=max_vol,
        min_vol=min_vol,
        operable_years=operable_years,
        si_vri_iqrlo=si_vri_iqrlo,
        si_spr_iqrlo=si_spr_iqrlo,
        si_vri_med=si_vri_med,
        si_spr_med=si_spr_med,
        min_si=min_si,
    )


def build_tipsy_params_for_tsa(
    *,
    tsa: str,
    results_for_tsa: Sequence[tuple[int, str, Mapping[str, Any]]],
    si_levels: Sequence[str],
    vdyp_curves_smooth_tsa: Any,
    vdyp_results_for_tsa: Mapping[int, Mapping[str, Any]],
    exclusion: Mapping[str, Any],
    tipsy_param_builder: Any,
    vdyp_curve_events_path: Any = None,
    append_jsonl_fn: Any = None,
    min_operable_years: float = 50.0,
    si_iqrlo_quantile: float = 0.50,
    si_merge_enabled: bool = True,
    si_merge_max_relative_gap: float = 0.08,
    si_merge_max_window_nrmse: float = 0.12,
    si_merge_min_common_ages: int = 5,
    si_merge_age_min: int = 30,
    si_merge_age_max: int = 250,
    verbose: bool = True,
    message_fn: Any = print,
) -> tuple[
    dict[tuple[str, str], int],
    dict[int, tuple[str, str]],
    dict[int, dict[str, dict[str, Any]]],
]:
    """Select eligible strata+SI combos and build TIPSY params for one TSA."""
    scsi_au_tsa: dict[tuple[str, str], int] = {}
    au_scsi_tsa: dict[int, tuple[str, str]] = {}
    tipsy_params_tsa: dict[int, dict[str, dict[str, Any]]] = {}

    vdyp_indexed = vdyp_curves_smooth_tsa.set_index(["stratum_code", "si_level"])
    vdyp_strata = set(vdyp_indexed.index.get_level_values("stratum_code"))
    siteprod_si_fallback_by_species = getattr(
        tipsy_param_builder,
        "siteprod_si_fallback_by_species",
        None,
    )
    if not isinstance(siteprod_si_fallback_by_species, Mapping):
        siteprod_si_fallback_by_species = None

    excluded_stratum_codes = getattr(
        tipsy_param_builder,
        "excluded_stratum_codes",
        None,
    )
    if not isinstance(excluded_stratum_codes, (set, list, tuple)):
        excluded_stratum_codes = set()
    else:
        excluded_stratum_codes = {
            str(value).strip() for value in excluded_stratum_codes if str(value).strip()
        }

    def _curve_df(sc_code: str, si_level: str) -> Any | None:
        try:
            df_ = vdyp_indexed.loc[sc_code, si_level]
        except KeyError:
            return None
        if not hasattr(df_, "columns") and hasattr(df_, "to_frame"):
            df_ = df_.to_frame().T
        return df_

    def _curve_merge_metrics(df_a: Any, df_b: Any) -> tuple[float, float, float]:
        series_a = (
            df_a[(df_a["age"] >= si_merge_age_min) & (df_a["age"] <= si_merge_age_max)]
            .groupby("age")["volume"]
            .mean()
        )
        series_b = (
            df_b[(df_b["age"] >= si_merge_age_min) & (df_b["age"] <= si_merge_age_max)]
            .groupby("age")["volume"]
            .mean()
        )
        common_ages = sorted(set(series_a.index).intersection(series_b.index))
        if len(common_ages) < int(si_merge_min_common_ages):
            return float("inf"), float("inf"), float("inf")
        a_vals = series_a.loc[common_ages].values.astype(float)
        b_vals = series_b.loc[common_ages].values.astype(float)
        denom = np.maximum(np.maximum(np.abs(a_vals), np.abs(b_vals)), 1e-9)
        rel_gap = np.abs(a_vals - b_vals) / denom
        if rel_gap.size == 0:
            return float("inf"), float("inf"), float("inf")
        diff = a_vals - b_vals
        rmse = float(np.sqrt(np.mean(np.square(diff))))
        scale = float(np.maximum(np.nanmean(np.maximum(a_vals, b_vals)), 1e-9))
        nrmse = float(rmse / scale)
        return float(np.nanmax(rel_gap)), rmse, nrmse

    for stratumi, sc, result in results_for_tsa:
        message_fn(sc)
        if sc in excluded_stratum_codes:
            if verbose:
                message_fn("  excluded from TIPSY handoff", sc)
            if append_jsonl_fn is not None and vdyp_curve_events_path is not None:
                append_jsonl_fn(
                    vdyp_curve_events_path,
                    build_tipsy_warning_event(
                        tsa=tsa,
                        stratumi=int(stratumi),
                        sc=sc,
                        si_level=None,
                        au=None,
                        reason="excluded_stratum_code",
                    ),
                )
            continue
        if sc not in vdyp_strata:
            if verbose:
                message_fn("  missing vdyp curves for stratum", sc)
            continue

        present_levels = [
            si_level
            for si_level in si_levels
            if _curve_df(sc, si_level) is not None
            and isinstance(result.get(si_level), Mapping)
        ]
        merge_groups: list[list[str]] = []
        if si_merge_enabled and present_levels:
            for level in present_levels:
                if not merge_groups:
                    merge_groups.append([level])
                    continue
                prev_level = merge_groups[-1][-1]
                prev_df = _curve_df(sc, prev_level)
                cur_df = _curve_df(sc, level)
                if prev_df is None or cur_df is None:
                    merge_groups.append([level])
                    continue
                gap, rmse, nrmse = _curve_merge_metrics(prev_df, cur_df)
                if (gap <= float(si_merge_max_relative_gap)) and (
                    nrmse <= float(si_merge_max_window_nrmse)
                ):
                    merge_groups[-1].append(level)
                    if verbose:
                        message_fn(
                            "    merge metrics",
                            f"{prev_level}+{level}",
                            f"gap={gap:0.3f}",
                            f"rmse={rmse:0.1f}",
                            f"nrmse={nrmse:0.3f}",
                        )
                else:
                    merge_groups.append([level])
        elif present_levels:
            merge_groups = [[level] for level in present_levels]

        if merge_groups:
            message_fn(
                "  si-groups",
                ", ".join("[" + "+".join(group) + "]" for group in merge_groups),
            )

        # Map all SI levels (including non-representatives) to their group representative.
        representative_for_level: dict[str, str] = {}
        group_by_representative: dict[str, list[str]] = {}
        for group in merge_groups:
            rep = group[len(group) // 2]
            group_by_representative[rep] = group
            for level in group:
                representative_for_level[level] = rep

        for i, si_level in enumerate(si_levels, start=1):
            if si_level not in representative_for_level:
                if verbose:
                    message_fn("  missing fit result for", sc, si_level)
                continue
            rep_level = representative_for_level[si_level]
            if si_level != rep_level:
                continue
            au = 1000 * i + stratumi
            group_levels = group_by_representative.get(rep_level, [rep_level])
            result_si = result.get(rep_level)
            if not isinstance(result_si, Mapping):
                if verbose:
                    message_fn("  missing fit result for", sc, rep_level)
                continue
            df = _curve_df(sc, rep_level)
            if df is None:
                if verbose:
                    message_fn("  missing vdyp curves for", sc, rep_level)
                continue
            try:
                candidate = evaluate_tipsy_candidate(
                    sc=sc,
                    vdyp_curve_df=df,
                    result_si=result_si,
                    exclusion=exclusion,
                    min_operable_years=min_operable_years,
                    si_iqrlo_quantile=si_iqrlo_quantile,
                    siteprod_si_fallback_by_species=siteprod_si_fallback_by_species,
                )
            except _tipsy_candidate_exception_types():
                message_fn(sc, si_level)
                message_fn(result[si_level]["ss"])
                raise
            if not candidate.eligible:
                if verbose and candidate.reason == "max_vol_too_low":
                    message_fn(
                        "  ",
                        si_level,
                        "max_vol too low",
                        candidate.max_vol,
                        candidate.min_vol,
                    )
                elif verbose and candidate.reason == "operability_window_too_narrow":
                    message_fn(
                        "  ",
                        si_level,
                        "operability window too narrow",
                        candidate.operable_years,
                        min_operable_years,
                    )
                elif verbose and candidate.reason == "si_too_low":
                    message_fn(
                        "  ",
                        si_level,
                        "SI too low (using %0.2f quantile)" % si_iqrlo_quantile,
                        "%2.1f" % candidate.si_vri_iqrlo,
                        "%2.1f" % candidate.si_spr_iqrlo,
                        candidate.min_si,
                    )
                elif verbose and candidate.reason == "excluded_leading_species":
                    message_fn(
                        "  ",
                        si_level,
                        "bad leading species",
                        candidate.leading_species,
                    )
                elif verbose and candidate.reason == "excluded_bec":
                    message_fn("  ", si_level, "bad bec", candidate.bec)
                elif verbose and candidate.reason == "no_species_candidates":
                    message_fn("  ", si_level, "no species candidates after filtering")
                if append_jsonl_fn is not None and vdyp_curve_events_path is not None:
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_tipsy_warning_event(
                            tsa=tsa,
                            stratumi=int(stratumi),
                            sc=sc,
                            si_level=rep_level,
                            au=int(au),
                            reason="no_species_candidates",
                        ),
                    )
                continue

            message_fn("  ", rep_level, au)
            if len(group_levels) > 1:
                message_fn("    merged si levels", "+".join(group_levels))
            message_fn(
                "    median SI (VRI)               ",
                ("%2.1f" % candidate.si_vri_med).rjust(4),
            )
            message_fn(
                "    median SI (siteprod)          ",
                ("%2.1f" % candidate.si_spr_med).rjust(4),
            )
            message_fn(
                "    median SI ratio (VRI/siteprod) ",
                "%0.2f" % (candidate.si_vri_med / candidate.si_spr_med),
            )
            for species, v in candidate.species_map.items():
                message_fn("    species", species.ljust(3), "%3.0f" % v["pct"])
            vdyp_result = vdyp_results_for_tsa.get(stratumi, {}).get(rep_level)
            if not isinstance(vdyp_result, dict):
                if verbose:
                    message_fn("    missing vdyp result table for", sc, rep_level)
                if append_jsonl_fn is not None and vdyp_curve_events_path is not None:
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_tipsy_warning_event(
                            tsa=tsa,
                            stratumi=int(stratumi),
                            sc=sc,
                            si_level=rep_level,
                            au=int(au),
                            reason="missing_vdyp_output",
                        ),
                    )
                continue
            for level in group_levels:
                scsi_au_tsa[(sc, level)] = au
            au_scsi_tsa[au] = (sc, rep_level)
            builder_au_data = dict(result_si)
            builder_au_data.setdefault("stratum_code", sc)
            tipsy_params_tsa[au] = tipsy_param_builder(au, builder_au_data, vdyp_result)
            message_fn()
    return scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa
