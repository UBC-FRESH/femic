"""Process-based hydrology model adapters and scenario manifests.

P114.6 defines how FEMIC drives user-supplied DHSVM, RHESSys, CRHM, SUMMA, and
HEC-HMS runtimes. It does not bundle binaries, licences, or private data.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from femic.hydrology.flood import FloodSample, HydrologyFloodError

HYDROLOGY_PROCESS_SCENARIO_SCHEMA_VERSION = "femic.hydrology.process_scenario.v1"
HYDROLOGY_PROCESS_RESULT_SCHEMA_VERSION = "femic.hydrology.process_result.v1"
PROCESS_MODEL_IDS: tuple[str, ...] = ("dhsvm", "rhessys", "crhm", "summa", "hechms")
PROCESS_MODEL_SCENARIO_KINDS: tuple[str, ...] = (
    "baseline",
    "treatment",
    "ensemble",
)
DEFAULT_PEAK_FLOW_FILENAME = "peak_flows.csv"
DEFAULT_RECEPTOR_METRICS_FILENAME = "receptor_metrics.csv"
DEFAULT_PROCESS_TIME_STEP_HOURS = 24.0
DEFAULT_PROCESS_CRS = "EPSG:3005"


class HydrologyProcessModelError(RuntimeError):
    """Raised when a process-model scenario, adapter, or run is invalid."""


@dataclass(frozen=True)
class ProcessModelSpec:
    """External process-model boundary metadata."""

    model_id: str
    display_name: str
    licence: str
    runtime_kind: str
    default_executable: str
    executable_env_var: str
    config_filename: str
    command_style: str
    required_inputs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the spec as a JSON-serializable mapping."""

        return {
            "model_id": self.model_id,
            "display_name": self.display_name,
            "licence": self.licence,
            "runtime_kind": self.runtime_kind,
            "default_executable": self.default_executable,
            "executable_env_var": self.executable_env_var,
            "config_filename": self.config_filename,
            "command_style": self.command_style,
            "required_inputs": list(self.required_inputs),
            "notes": list(self.notes),
        }


PROCESS_MODEL_SPECS: tuple[ProcessModelSpec, ...] = (
    ProcessModelSpec(
        model_id="dhsvm",
        display_name="Distributed Hydrology Soil Vegetation Model",
        licence="User-supplied DHSVM build and research-model terms.",
        runtime_kind="binary",
        default_executable="dhsvm",
        executable_env_var="FEMIC_DHSVM_EXE",
        config_filename="dhsvm.config",
        command_style="config_path",
        required_inputs=("climate", "land_cover", "roads", "dem"),
        notes=("DHSVM is commonly used for forest/snow watersheds in BC.",),
    ),
    ProcessModelSpec(
        model_id="summa",
        display_name="Structure for Unifying Multiple Modeling Alternatives",
        licence="Open-source SUMMA; user-supplied build and runtime.",
        runtime_kind="binary",
        default_executable="summa.exe",
        executable_env_var="FEMIC_SUMMA_EXE",
        config_filename="fileManager.txt",
        command_style="file_manager",
        required_inputs=("climate", "land_cover", "roads", "dem"),
        notes=("SUMMA uses a file-manager run configuration.",),
    ),
    ProcessModelSpec(
        model_id="rhessys",
        display_name="Regional Hydro-Ecologic Simulation System",
        licence="User-supplied RHESSys build and research-model terms.",
        runtime_kind="binary",
        default_executable="rhessys",
        executable_env_var="FEMIC_RHESSYS_EXE",
        config_filename="worldfile",
        command_style="worldfile",
        required_inputs=("climate", "land_cover", "roads", "dem"),
        notes=("RHESSys couples hydrology and ecosystem processes.",),
    ),
    ProcessModelSpec(
        model_id="crhm",
        display_name="Cold Regions Hydrological Model",
        licence="User-supplied CRHM build and runtime.",
        runtime_kind="binary",
        default_executable="crhm",
        executable_env_var="FEMIC_CRHM_EXE",
        config_filename="crhm_project.obs",
        command_style="project",
        required_inputs=("climate", "land_cover", "roads", "dem"),
        notes=("CRHM is a candidate for snow-dominated basins.",),
    ),
    ProcessModelSpec(
        model_id="hechms",
        display_name="Hydrologic Engineering Center - Hydrologic Modeling System",
        licence="USACE HEC-HMS; user-supplied installation and terms.",
        runtime_kind="external",
        default_executable="hec-hms",
        executable_env_var="FEMIC_HEC_HMS_EXE",
        config_filename="hec_hms_project",
        command_style="project",
        required_inputs=("climate", "land_cover", "roads", "dem"),
        notes=("HEC-HMS is an engineering flood model, not a forest-process model.",),
    ),
)


@dataclass(frozen=True)
class HydrologyScenarioManifest:
    """Scenario inputs for one external hydrology model run."""

    scenario_id: str
    scenario_name: str
    model_id: str
    domain_id: str
    scenario_kind: str
    watershed_ids: tuple[str, ...]
    start_year: int
    end_year: int
    time_step_hours: float
    crs: str
    climate_forcing_path: str
    land_cover_path: str
    road_scenario_path: str
    harvest_scenario_path: str
    model_config_path: str
    output_dir: str
    receptor_ids: tuple[str, ...] = ()
    ledger_id: str | None = None
    provenance: dict[str, object] = field(default_factory=dict)
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_PROCESS_SCENARIO_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the scenario manifest as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "model_id": self.model_id,
            "domain_id": self.domain_id,
            "ledger_id": self.ledger_id,
            "scenario_kind": self.scenario_kind,
            "watershed_ids": list(self.watershed_ids),
            "start_year": self.start_year,
            "end_year": self.end_year,
            "time_step_hours": self.time_step_hours,
            "crs": self.crs,
            "climate_forcing_path": self.climate_forcing_path,
            "land_cover_path": self.land_cover_path,
            "road_scenario_path": self.road_scenario_path,
            "harvest_scenario_path": self.harvest_scenario_path,
            "model_config_path": self.model_config_path,
            "output_dir": self.output_dir,
            "receptor_ids": list(self.receptor_ids),
            "provenance": self.provenance,
            "caveats": list(self.caveats),
        }


@dataclass(frozen=True)
class ProcessModelAvailability:
    """Probe result for a user-supplied process-model runtime."""

    model_id: str
    available: bool
    executable: str | None
    source: str | None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the probe as a JSON-serializable mapping."""

        return {
            "model_id": self.model_id,
            "available": self.available,
            "executable": self.executable,
            "source": self.source,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ProcessModelRunPlan:
    """Command and availability for one planned process-model run."""

    model_id: str
    scenario_id: str
    executable: str | None
    executable_source: str | None
    command: tuple[str, ...]
    available: bool
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return the plan as a JSON-serializable mapping."""

        return {
            "model_id": self.model_id,
            "scenario_id": self.scenario_id,
            "executable": self.executable,
            "executable_source": self.executable_source,
            "command": list(self.command),
            "available": self.available,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ProcessModelResult:
    """Normalized result from one process-model run."""

    model_id: str
    scenario_id: str
    command: tuple[str, ...]
    returncode: int
    peak_series: FloodSample
    receptor_metrics: dict[str, dict[str, float]]
    output_files: tuple[str, ...]
    stdout_path: str
    stderr_path: str
    warnings: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    schema_version: str = HYDROLOGY_PROCESS_RESULT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the result as a JSON-serializable mapping."""

        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "scenario_id": self.scenario_id,
            "command": list(self.command),
            "returncode": self.returncode,
            "peak_series": self.peak_series.to_dict(),
            "receptor_metrics": self.receptor_metrics,
            "output_files": list(self.output_files),
            "stdout_path": self.stdout_path,
            "stderr_path": self.stderr_path,
            "warnings": list(self.warnings),
            "caveats": list(self.caveats),
        }


class ProcessModelAdapter(Protocol):
    """Protocol for a user-supplied process-model adapter."""

    spec: ProcessModelSpec

    def probe(self, executable: Path | None = None) -> ProcessModelAvailability:
        """Return whether the model runtime is available."""

    def build_command(
        self,
        manifest: HydrologyScenarioManifest,
        run_dir: Path,
        executable: str,
    ) -> tuple[str, ...]:
        """Build the model command for one run directory."""

    def parse_outputs(
        self,
        run_dir: Path,
        manifest: HydrologyScenarioManifest,
    ) -> tuple[FloodSample, dict[str, dict[str, float]], tuple[str, ...]]:
        """Parse normalized peak-flow and receptor outputs."""


class _BaseProcessModelAdapter:
    spec: ProcessModelSpec

    def probe(self, executable: Path | None = None) -> ProcessModelAvailability:
        warnings: list[str] = []
        if executable is not None:
            resolved = executable.expanduser().resolve()
            available = resolved.is_file() and os.access(resolved, os.X_OK)
            if not available:
                warnings.append(f"Explicit executable is not runnable: {resolved}")
            return ProcessModelAvailability(
                model_id=self.spec.model_id,
                available=available,
                executable=str(resolved),
                source="explicit",
                warnings=tuple(warnings),
            )
        env_executable = os.environ.get(self.spec.executable_env_var, "").strip()
        if env_executable:
            resolved = Path(env_executable).expanduser().resolve()
            available = resolved.is_file() and os.access(resolved, os.X_OK)
            if not available:
                warnings.append(
                    f"{self.spec.executable_env_var} does not point to a runnable "
                    f"file: {resolved}"
                )
            return ProcessModelAvailability(
                model_id=self.spec.model_id,
                available=available,
                executable=str(resolved),
                source=self.spec.executable_env_var,
                warnings=tuple(warnings),
            )
        found = shutil.which(self.spec.default_executable)
        if found is None:
            warnings.append(
                f"{self.spec.display_name} executable was not found; set "
                f"{self.spec.executable_env_var} or pass executable."
            )
            return ProcessModelAvailability(
                model_id=self.spec.model_id,
                available=False,
                executable=None,
                source="path",
                warnings=tuple(warnings),
            )
        return ProcessModelAvailability(
            model_id=self.spec.model_id,
            available=True,
            executable=found,
            source="path",
            warnings=(),
        )

    def _config_path(
        self,
        manifest: HydrologyScenarioManifest,
        run_dir: Path,
    ) -> Path:
        config = Path(manifest.model_config_path).expanduser()
        return config if config.is_absolute() else run_dir / config

    def parse_outputs(
        self,
        run_dir: Path,
        manifest: HydrologyScenarioManifest,
    ) -> tuple[FloodSample, dict[str, dict[str, float]], tuple[str, ...]]:
        peak_path = run_dir / DEFAULT_PEAK_FLOW_FILENAME
        if not peak_path.is_file():
            raise HydrologyProcessModelError(
                f"Process-model output is missing: {peak_path}"
            )
        peak_series = read_peak_flow_series(
            peak_path,
            station_id=manifest.scenario_id,
            regime=manifest.scenario_kind,
        )
        receptor_path = run_dir / DEFAULT_RECEPTOR_METRICS_FILENAME
        receptor_metrics = (
            read_receptor_metrics(receptor_path) if receptor_path.is_file() else {}
        )
        outputs = tuple(
            str(path) for path in (peak_path, receptor_path) if path.is_file()
        )
        return peak_series, receptor_metrics, outputs


def _spec(model_id: str) -> ProcessModelSpec:
    spec = next(
        (item for item in PROCESS_MODEL_SPECS if item.model_id == model_id),
        None,
    )
    if spec is None:
        raise HydrologyProcessModelError(f"Unknown process model {model_id!r}.")
    return spec


class DhsvmAdapter(_BaseProcessModelAdapter):
    """DHSVM config-path adapter."""

    spec = _spec("dhsvm")

    def build_command(
        self,
        manifest: HydrologyScenarioManifest,
        run_dir: Path,
        executable: str,
    ) -> tuple[str, ...]:
        return (executable, str(self._config_path(manifest, run_dir)))


class SummaAdapter(_BaseProcessModelAdapter):
    """SUMMA file-manager adapter."""

    spec = _spec("summa")

    def build_command(
        self,
        manifest: HydrologyScenarioManifest,
        run_dir: Path,
        executable: str,
    ) -> tuple[str, ...]:
        return (executable, "-m", str(self._config_path(manifest, run_dir)))


def process_model_specs() -> tuple[ProcessModelSpec, ...]:
    """Return the process-model boundary registry."""

    return PROCESS_MODEL_SPECS


def find_process_model_spec(model_id: str) -> ProcessModelSpec | None:
    """Resolve one process-model spec."""

    return next(
        (spec for spec in PROCESS_MODEL_SPECS if spec.model_id == model_id), None
    )


def adapter_for_model(model_id: str) -> ProcessModelAdapter:
    """Return an implemented adapter for a supported process model."""

    if model_id == "dhsvm":
        return DhsvmAdapter()
    if model_id == "summa":
        return SummaAdapter()
    raise HydrologyProcessModelError(
        f"No executable adapter is implemented for {model_id!r}; currently "
        "implemented adapters are `dhsvm` and `summa`."
    )


def build_scenario_manifest(
    *,
    scenario_id: str,
    scenario_name: str,
    model_id: str,
    domain_id: str,
    scenario_kind: str,
    watershed_ids: Sequence[str],
    start_year: int,
    end_year: int,
    time_step_hours: float = DEFAULT_PROCESS_TIME_STEP_HOURS,
    crs: str = DEFAULT_PROCESS_CRS,
    climate_forcing_path: str,
    land_cover_path: str,
    road_scenario_path: str,
    harvest_scenario_path: str,
    model_config_path: str,
    output_dir: str,
    receptor_ids: Sequence[str] = (),
    ledger_id: str | None = None,
    provenance: Mapping[str, object] | None = None,
    caveats: Sequence[str] = (),
) -> HydrologyScenarioManifest:
    """Build and validate one process-model scenario manifest."""

    manifest = HydrologyScenarioManifest(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        model_id=model_id,
        domain_id=domain_id,
        ledger_id=ledger_id,
        scenario_kind=scenario_kind,
        watershed_ids=tuple(watershed_ids),
        start_year=start_year,
        end_year=end_year,
        time_step_hours=time_step_hours,
        crs=crs,
        climate_forcing_path=climate_forcing_path,
        land_cover_path=land_cover_path,
        road_scenario_path=road_scenario_path,
        harvest_scenario_path=harvest_scenario_path,
        model_config_path=model_config_path,
        output_dir=output_dir,
        receptor_ids=tuple(receptor_ids),
        provenance={
            "producer": "femic.hydrology.process_models",
            **dict(provenance or {}),
        },
        caveats=tuple(caveats),
    )
    errors = validate_scenario_manifest(manifest)
    if errors:
        raise HydrologyProcessModelError("; ".join(errors))
    return manifest


def validate_scenario_manifest(
    manifest: HydrologyScenarioManifest,
) -> tuple[str, ...]:
    """Validate a process-model scenario manifest."""

    errors: list[str] = []
    if manifest.schema_version != HYDROLOGY_PROCESS_SCENARIO_SCHEMA_VERSION:
        errors.append(
            f"Unsupported process scenario schema {manifest.schema_version!r}."
        )
    for name, value in (
        ("scenario_id", manifest.scenario_id),
        ("scenario_name", manifest.scenario_name),
        ("domain_id", manifest.domain_id),
        ("crs", manifest.crs),
        ("climate_forcing_path", manifest.climate_forcing_path),
        ("land_cover_path", manifest.land_cover_path),
        ("road_scenario_path", manifest.road_scenario_path),
        ("harvest_scenario_path", manifest.harvest_scenario_path),
        ("model_config_path", manifest.model_config_path),
        ("output_dir", manifest.output_dir),
    ):
        if not value.strip():
            errors.append(f"{name} must be non-empty.")
    if find_process_model_spec(manifest.model_id) is None:
        errors.append(f"Unsupported model_id {manifest.model_id!r}.")
    if manifest.scenario_kind not in PROCESS_MODEL_SCENARIO_KINDS:
        errors.append(f"Unsupported scenario_kind {manifest.scenario_kind!r}.")
    if manifest.start_year > manifest.end_year:
        errors.append("start_year must not exceed end_year.")
    if manifest.time_step_hours <= 0 or not math.isfinite(manifest.time_step_hours):
        errors.append("time_step_hours must be positive and finite.")
    if not manifest.watershed_ids:
        errors.append("At least one watershed_id is required.")
    if any(not watershed.strip() for watershed in manifest.watershed_ids):
        errors.append("watershed_ids cannot contain blanks.")
    if any(not receptor.strip() for receptor in manifest.receptor_ids):
        errors.append("receptor_ids cannot contain blanks.")
    return tuple(errors)


def write_scenario_manifest(
    manifest: HydrologyScenarioManifest,
    path: Path,
) -> Path:
    """Write a scenario manifest as JSON."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return resolved


def load_scenario_manifest(path: Path) -> HydrologyScenarioManifest:
    """Load a scenario manifest from JSON."""

    resolved = path.expanduser().resolve()
    payload = _read_json_object(resolved, context="process scenario manifest")
    schema_version = _required_str(
        payload,
        "schema_version",
        context="process scenario manifest",
    )
    if schema_version != HYDROLOGY_PROCESS_SCENARIO_SCHEMA_VERSION:
        raise HydrologyProcessModelError(
            f"Unsupported process scenario schema {schema_version!r}."
        )
    manifest = HydrologyScenarioManifest(
        scenario_id=_required_str(payload, "scenario_id", context="scenario"),
        scenario_name=_required_str(payload, "scenario_name", context="scenario"),
        model_id=_required_str(payload, "model_id", context="scenario"),
        domain_id=_required_str(payload, "domain_id", context="scenario"),
        ledger_id=_optional_str(payload.get("ledger_id")),
        scenario_kind=_required_str(payload, "scenario_kind", context="scenario"),
        watershed_ids=_required_str_list(
            payload.get("watershed_ids"),
            context="watershed_ids",
        ),
        start_year=_required_int(payload, "start_year", context="scenario"),
        end_year=_required_int(payload, "end_year", context="scenario"),
        time_step_hours=_required_float(
            payload,
            "time_step_hours",
            context="scenario",
        ),
        crs=_required_str(payload, "crs", context="scenario"),
        climate_forcing_path=_required_str(
            payload,
            "climate_forcing_path",
            context="scenario",
        ),
        land_cover_path=_required_str(
            payload,
            "land_cover_path",
            context="scenario",
        ),
        road_scenario_path=_required_str(
            payload,
            "road_scenario_path",
            context="scenario",
        ),
        harvest_scenario_path=_required_str(
            payload,
            "harvest_scenario_path",
            context="scenario",
        ),
        model_config_path=_required_str(
            payload,
            "model_config_path",
            context="scenario",
        ),
        output_dir=_required_str(payload, "output_dir", context="scenario"),
        receptor_ids=_optional_str_list(
            payload.get("receptor_ids"),
            context="receptor_ids",
        ),
        provenance=_optional_mapping(payload.get("provenance"), context="provenance"),
        caveats=_optional_str_list(payload.get("caveats"), context="caveats"),
        schema_version=schema_version,
    )
    errors = validate_scenario_manifest(manifest)
    if errors:
        raise HydrologyProcessModelError("; ".join(errors))
    return manifest


def plan_process_model_run(
    adapter: ProcessModelAdapter,
    manifest: HydrologyScenarioManifest,
    run_dir: Path,
    *,
    executable: Path | None = None,
) -> ProcessModelRunPlan:
    """Plan a process-model run without executing it."""

    errors = validate_scenario_manifest(manifest)
    if errors:
        raise HydrologyProcessModelError("; ".join(errors))
    availability = adapter.probe(executable)
    if not availability.available or availability.executable is None:
        return ProcessModelRunPlan(
            model_id=adapter.spec.model_id,
            scenario_id=manifest.scenario_id,
            executable=None,
            executable_source=availability.source,
            command=(),
            available=False,
            warnings=availability.warnings,
        )
    command = adapter.build_command(manifest, run_dir, availability.executable)
    warnings = list(availability.warnings)
    config_path = Path(manifest.model_config_path).expanduser()
    if not config_path.is_absolute():
        config_path = run_dir / config_path
    if not config_path.is_file():
        warnings.append(f"Model config does not exist yet: {config_path}")
    return ProcessModelRunPlan(
        model_id=adapter.spec.model_id,
        scenario_id=manifest.scenario_id,
        executable=availability.executable,
        executable_source=availability.source,
        command=command,
        available=True,
        warnings=tuple(warnings),
    )


def run_process_model(
    adapter: ProcessModelAdapter,
    manifest: HydrologyScenarioManifest,
    run_dir: Path,
    *,
    executable: Path | None = None,
    timeout_sec: float = 600.0,
) -> ProcessModelResult:
    """Execute a user-supplied process model and parse normalized outputs."""

    if timeout_sec <= 0:
        raise HydrologyProcessModelError("timeout_sec must be positive.")
    resolved_run_dir = run_dir.expanduser().resolve()
    plan = plan_process_model_run(
        adapter,
        manifest,
        resolved_run_dir,
        executable=executable,
    )
    if not plan.available or plan.executable is None:
        raise HydrologyProcessModelError(
            "Process model is unavailable: " + "; ".join(plan.warnings)
        )
    resolved_run_dir.mkdir(parents=True, exist_ok=True)
    write_scenario_manifest(
        manifest,
        resolved_run_dir / "scenario_manifest.json",
    )
    try:
        completed = subprocess.run(
            list(plan.command),
            cwd=resolved_run_dir,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HydrologyProcessModelError(
            f"Process-model execution failed: {exc}"
        ) from exc
    stdout_path = resolved_run_dir / "model.stdout.log"
    stderr_path = resolved_run_dir / "model.stderr.log"
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode != 0:
        raise HydrologyProcessModelError(
            f"Process model exited with {completed.returncode}: "
            f"{(completed.stderr or completed.stdout or '').strip()[:500]}"
        )
    peak_series, receptor_metrics, output_files = adapter.parse_outputs(
        resolved_run_dir,
        manifest,
    )
    return ProcessModelResult(
        model_id=adapter.spec.model_id,
        scenario_id=manifest.scenario_id,
        command=plan.command,
        returncode=completed.returncode,
        peak_series=peak_series,
        receptor_metrics=receptor_metrics,
        output_files=output_files,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
        warnings=plan.warnings,
        caveats=(
            "External process-model binaries and licences are user-supplied.",
            "Model output validity depends on the supplied scenario and calibration.",
            "FEMIC stores only normalized peak-flow and receptor outputs.",
        ),
    )


def read_peak_flow_series(
    path: Path,
    *,
    station_id: str,
    regime: str = "unknown",
) -> FloodSample:
    """Read a normalized ``year,peak_flow_m3s`` peak-flow CSV."""

    resolved = path.expanduser().resolve()
    rows = _read_csv_rows(resolved)
    years: list[int] = []
    values: list[float] = []
    for row in rows:
        years.append(_required_int(row, "year", context="peak-flow CSV"))
        values.append(_required_float(row, "peak_flow_m3s", context="peak-flow CSV"))
    try:
        return FloodSample(
            station_id=station_id,
            years=tuple(years),
            values=tuple(values),
            regime=regime,
        )
    except (HydrologyFloodError, ValueError) as exc:
        raise HydrologyProcessModelError(str(exc)) from exc


def read_receptor_metrics(path: Path) -> dict[str, dict[str, float]]:
    """Read a normalized ``receptor_id,metric,value`` CSV."""

    resolved = path.expanduser().resolve()
    metrics: dict[str, dict[str, float]] = {}
    for row in _read_csv_rows(resolved):
        receptor_id = _required_str(row, "receptor_id", context="receptor CSV")
        metric = _required_str(row, "metric", context="receptor CSV")
        value = _required_float(row, "value", context="receptor CSV")
        metrics.setdefault(receptor_id, {})[metric] = value
    return metrics


def write_peak_flow_series(sample: FloodSample, path: Path) -> Path:
    """Write a normalized peak-flow CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["year", "peak_flow_m3s"])
        for year, value in zip(sample.years, sample.values, strict=False):
            writer.writerow([year, value])
    return resolved


def write_receptor_metrics(
    metrics: Mapping[str, Mapping[str, float]],
    path: Path,
) -> Path:
    """Write a normalized receptor-metrics CSV."""

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["receptor_id", "metric", "value"])
        for receptor_id, values in sorted(metrics.items()):
            for metric, value in sorted(values.items()):
                writer.writerow([receptor_id, metric, value])
    return resolved


def _read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    try:
        with path.expanduser().resolve().open(newline="", encoding="utf-8") as handle:
            return tuple(dict(row) for row in csv.DictReader(handle))
    except OSError as exc:
        raise HydrologyProcessModelError(f"Unable to read CSV {path}: {exc}") from exc


def _read_json_object(path: Path, *, context: str) -> dict[str, object]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise HydrologyProcessModelError(
            f"Unable to read {context}: {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise HydrologyProcessModelError(
            f"Invalid JSON in {context}: {path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise HydrologyProcessModelError(f"{context} must be a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _mapping_from_object(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise HydrologyProcessModelError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}


def _required_str(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise HydrologyProcessModelError(
            f"{context} field {key!r} must be a non-empty string."
        )
    return value.strip()


def _required_float(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> float:
    value = mapping.get(key)
    if isinstance(value, bool):
        raise HydrologyProcessModelError(f"{context} field {key!r} must be numeric.")
    try:
        parsed = float(str(value))
    except (TypeError, ValueError) as exc:
        raise HydrologyProcessModelError(
            f"{context} field {key!r} must be numeric."
        ) from exc
    if not math.isfinite(parsed):
        raise HydrologyProcessModelError(f"{context} field {key!r} must be finite.")
    return parsed


def _required_int(
    mapping: Mapping[str, object],
    key: str,
    *,
    context: str,
) -> int:
    value = mapping.get(key)
    if isinstance(value, bool):
        raise HydrologyProcessModelError(f"{context} field {key!r} must be an integer.")
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise HydrologyProcessModelError(
            f"{context} field {key!r} must be an integer."
        ) from exc


def _required_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise HydrologyProcessModelError(f"{context} must be a list.")
    items = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if len(items) != len(value) or not items:
        raise HydrologyProcessModelError(f"{context} must contain non-empty strings.")
    return tuple(items)


def _optional_str_list(value: object, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise HydrologyProcessModelError(f"{context} must be a list.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise HydrologyProcessModelError(f"{context} entries must be strings.")
        text = item.strip()
        if text:
            items.append(text)
    return tuple(items)


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_mapping(value: object, *, context: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise HydrologyProcessModelError(f"{context} must be an object.")
    return {str(key): item for key, item in value.items()}
