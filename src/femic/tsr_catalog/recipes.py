"""Instance-local TSR recipe scaffold helpers."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
import hashlib
from importlib import resources as importlib_resources
import json
import math
import shutil
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Sequence

import geopandas as gpd  # type: ignore[import-untyped]
import nbformat
import pandas as pd
from shapely.geometry import box  # type: ignore[import-untyped]
import yaml
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from femic.bcdc_catalog import (
    INDIRECT_CUSTOM_DOWNLOAD,
    SERVICE,
    SUPPORTING_DOCUMENT,
    download_direct_bcdc_resources,
    resolve_bcdc_candidates,
)
from femic.bcdc_dwds import BcdcDwdsError, submit_bcdc_dwds_order
from femic.bcdc_fetch import (
    BC_ALBERS_EPSG,
    BcdcFetchError,
    GeomarkBBox,
    fetch_bcdc_wfs_data,
)
from femic.pipeline.tipsy_config import BROADLEAF_SPECIES_CODES
from femic.pipeline.vri import initialize_aflb_land_base_records

from .overlay import TsrOverlayTsaRecord
from .report import TsrFactReviewRow, report_tsr_candidate_facts
from .source_overrides import (
    TsrSourceLayerOverrideEntry,
    load_tsr_source_layer_overrides,
)


class TsrRecipeError(RuntimeError):
    """Raised when TSR recipe initialization or loading fails."""


_TSR_RECIPE_RESOURCE_PACKAGE = "femic.resources.tsr_recipes"
_SOURCE_LAYERS_RECIPE_RESOURCE = "source_layers.recipe.yaml"
_THLB_NETDOWN_RECIPE_RESOURCE = "thlb_netdown.recipe.yaml"
TSR_THLB_EXECUTION_MODE_HYBRID = "hybrid"
TSR_THLB_EXECUTION_MODE_RECONSTRUCTED = "reconstructed"
_TSR_THLB_EXECUTION_MODES = {
    TSR_THLB_EXECUTION_MODE_HYBRID,
    TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
}
_RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD = 10000
_RECONSTRUCTED_STAND_BINARY_EXCLUDE_THRESHOLD = 0.5
_THLB_STAGE_ORDER = (
    "glb_to_aflb",
    "aflb_to_lhlb",
    "lhlb_to_thlb",
    "reference_target",
    "context",
)
_THLB_STAGE_LABELS = {
    "glb_to_aflb": "GLB -> AFLB",
    "aflb_to_lhlb": "AFLB -> LHLB",
    "lhlb_to_thlb": "LHLB -> THLB",
    "reference_target": "Reference targets",
    "context": "Context / interpretation",
}
_THLB_JUNK_FRAGMENTS = {
    "stands",
    "forest stands",
    "forest lands",
    "lands that are",
    "lands",
    "areas",
    "areas where",
    "forested areas",
    "non-forested areas",
    "non contributing areas",
}
_THLB_ADDITIONAL_SUPPORTING_PROVENANCE_IDS: dict[str, tuple[str, ...]] = {
    "areas considered inoperable": ("reference/res_xSteepSlopeLogging.pdf#page=1",),
}
_THLB_NOTEBOOK_RUNNABLE_PARENT_LABELS = {
    "land not administered by the province",
    "non-forest",
    "roads and landings",
    "parks, protected areas, area-base tenures",
    "old growth management areas",
    "wildlife habitat areas",
    "critical habitat for fish",
    "lakeshore management",
    "community areas of special concern",
    "areas considered inoperable",
    "sites with low growing timber potential",
    "non-merchantable timber profiles",
    "recreation features",
    "growth and yield permanent sample plots",
    "riparian areas",
    "buffered trails",
    "wildlife tree retention areas",
    "cultural heritage and archaeological resources",
    "future roads",
}

_RIPARIAN_STREAM_WIDTHS_M = {
    1: 60.0,
    2: 34.0,
    3: 24.0,
    4: 10.0,
    5: 10.0,
    6: 6.0,
}

_RIPARIAN_WETLAND_WIDTHS_M = {
    "w1": 18.0,
    "w2": 14.0,
    "w3": 6.0,
    "w4": 6.0,
    "w5": 18.0,
}
_STEP13_ATTRIBUTE_CHECKPOINT_RELATIVE_PATH = Path(
    "data/tsr/ria_vri_vclr1p_checkpoint7.step13_attrs.feather"
)
_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA = 67.1
TSR_EFFECTIVE_AREA_SQM_COLUMN = "FEMIC_EFFECTIVE_AREA_SQM"
TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL = "serial"
TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL = "lu_parallel"
_TSR_THLB_PARENT_STEP_EXECUTION_MODES = {
    TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
    TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL,
}
_CURVE_VOLUME_METRIC_AUTO = "treated_cmai_untreated_culmination"
_CURVE_VOLUME_METRIC_AGE = "volume_at_age"


@dataclass(frozen=True)
class TsrRecipeCanonicalInputs:
    """Canonical shared inputs referenced by TSR recipes."""

    registry_path: str
    documents_path: str
    candidate_facts_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "registry_path": self.registry_path,
            "documents_path": self.documents_path,
            "candidate_facts_path": self.candidate_facts_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeInstanceInputs:
    """Instance-local inputs referenced by the source-layer recipe."""

    overlay_path: str
    source_layer_overrides_path: str
    download_root: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
            "download_root": self.download_root,
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeInstanceInputs:
    """Instance-local inputs referenced by the THLB netdown recipe."""

    overlay_path: str
    source_layer_recipe_path: str
    source_layer_overrides_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "overlay_path": self.overlay_path,
            "source_layer_recipe_path": self.source_layer_recipe_path,
            "source_layer_overrides_path": self.source_layer_overrides_path,
        }


@dataclass(frozen=True)
class TsrSourceLayersRecipeRecord:
    """One instance-local source-layer recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrSourceLayersRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    entries: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "entries": [dict(entry) for entry in self.entries],
        }


@dataclass(frozen=True)
class TsrThlbNetdownRecipeRecord:
    """One instance-local THLB netdown recipe scaffold."""

    schema_version: int
    recipe_kind: str
    tsa: TsrOverlayTsaRecord
    canonical_inputs: TsrRecipeCanonicalInputs
    instance_inputs: TsrThlbNetdownRecipeInstanceInputs
    recipe_contract: dict[str, Any]
    parent_steps: tuple[dict[str, Any], ...]
    steps: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "recipe_kind": self.recipe_kind,
            "tsa": self.tsa.to_dict(),
            "canonical_inputs": self.canonical_inputs.to_dict(),
            "instance_inputs": self.instance_inputs.to_dict(),
            "recipe_contract": dict(self.recipe_contract),
            "parent_steps": [dict(step) for step in self.parent_steps],
            "steps": [dict(step) for step in self.steps],
        }


@dataclass(frozen=True)
class TsrRecipeInitResult:
    """Result payload for recipe scaffold initialization."""

    tsa: TsrOverlayTsaRecord
    source_layers_recipe_path: Path
    thlb_netdown_recipe_path: Path
    created_source_layers_recipe: bool
    created_thlb_netdown_recipe: bool


@dataclass(frozen=True)
class TsrSourceLayersRecipeBuildResult:
    """Summary of one source-layer recipe build pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    entry_count: int
    status_counts: dict[str, int]


@dataclass(frozen=True)
class TsrSourceLayersRecipeRunResult:
    """Summary of one source-layer recipe execution pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    entry_count: int
    outcome_counts: dict[str, int]


@dataclass(frozen=True)
class TsrThlbNetdownRecipeBuildResult:
    """Summary of one THLB netdown recipe build pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    step_count: int
    step_kind_counts: dict[str, int]
    status_counts: dict[str, int]
    selected_document_paths: tuple[str, ...]


@dataclass(frozen=True)
class TsrThlbNetdownRecipeRunResult:
    """Summary of one THLB netdown recipe execution pass."""

    recipe_path: Path
    tsa: TsrOverlayTsaRecord
    checkpoint_path: Path
    output_path: Path
    audit_path: Path
    status_report_path: Path
    runtime_status_report_path: Path
    execution_mode: str
    baseline_signal: str
    selected_map_ids: tuple[str, ...]
    step_count: int
    outcome_counts: dict[str, int]
    input_area_ha: float
    baseline_managed_area_ha: float
    final_managed_area_ha: float
    legacy_reference_managed_area_ha: float | None
    tsr_reported_aflb_area_ha: float | None
    tsr_reported_thlb_area_ha: float | None


@dataclass(frozen=True)
class TsrThlbWorkbenchBuildResult:
    """Summary of one THLB workbench notebook build pass."""

    recipe_path: Path
    notebook_path: Path
    tsa: TsrOverlayTsaRecord
    parent_step_count: int
    compiled_logic_count: int
    stage_counts: dict[str, int]


@dataclass(frozen=True)
class TsrThlbWorkbenchLockResult:
    """Summary of one THLB workbench lock/export pass."""

    recipe_path: Path
    notebook_path: Path
    locked_script_path: Path
    locked_recipe_path: Path
    frozen_status_report_path: Path
    frozen_audit_path: Path | None
    tsa: TsrOverlayTsaRecord
    lock_scope: str


@dataclass(frozen=True)
class TsrThlbParentStepRunResult:
    """Summary of one notebook-safe THLB parent-step execution pass."""

    recipe_path: Path
    parent_step_id: str
    parent_label: str
    tsa: TsrOverlayTsaRecord
    checkpoint_path: Path
    selected_map_ids: tuple[str, ...]
    selected_landscape_units: tuple[str, ...]
    output_path: Path
    result_json_path: Path
    status: str
    executed_parent_step_ids: tuple[str, ...]
    input_area_ha: float
    removed_area_ha: float
    remaining_area_ha: float
    benchmark_marginal_area_ha: float | None
    benchmark_cumulative_area_ha: float | None
    benchmark_marginal_delta_ha: float | None
    benchmark_cumulative_delta_ha: float | None
    smoke_benchmark_scale_factor: float | None
    scaled_benchmark_marginal_area_ha: float | None
    scaled_benchmark_cumulative_area_ha: float | None
    scaled_benchmark_marginal_delta_ha: float | None
    scaled_benchmark_cumulative_delta_ha: float | None
    notes: tuple[str, ...]
    execution_mode: str = TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL
    worker_count: int | None = None
    lu_chunk_count: int | None = None
    lu_bundle_count: int | None = None
    progress_root: Path | None = None
    profiling: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "recipe_path": str(self.recipe_path),
            "parent_step_id": self.parent_step_id,
            "parent_label": self.parent_label,
            "tsa": self.tsa.to_dict(),
            "checkpoint_path": str(self.checkpoint_path),
            "selected_map_ids": list(self.selected_map_ids),
            "selected_landscape_units": list(self.selected_landscape_units),
            "output_path": str(self.output_path),
            "result_json_path": str(self.result_json_path),
            "status": self.status,
            "executed_parent_step_ids": list(self.executed_parent_step_ids),
            "input_area_ha": self.input_area_ha,
            "removed_area_ha": self.removed_area_ha,
            "remaining_area_ha": self.remaining_area_ha,
            "benchmark_marginal_area_ha": self.benchmark_marginal_area_ha,
            "benchmark_cumulative_area_ha": self.benchmark_cumulative_area_ha,
            "benchmark_marginal_delta_ha": self.benchmark_marginal_delta_ha,
            "benchmark_cumulative_delta_ha": self.benchmark_cumulative_delta_ha,
            "smoke_benchmark_scale_factor": self.smoke_benchmark_scale_factor,
            "scaled_benchmark_marginal_area_ha": self.scaled_benchmark_marginal_area_ha,
            "scaled_benchmark_cumulative_area_ha": self.scaled_benchmark_cumulative_area_ha,
            "scaled_benchmark_marginal_delta_ha": self.scaled_benchmark_marginal_delta_ha,
            "scaled_benchmark_cumulative_delta_ha": self.scaled_benchmark_cumulative_delta_ha,
            "notes": list(self.notes),
            "execution_mode": self.execution_mode,
            "worker_count": self.worker_count,
            "lu_chunk_count": self.lu_chunk_count,
            "lu_bundle_count": self.lu_bundle_count,
            "progress_root": str(self.progress_root)
            if self.progress_root is not None
            else None,
            "profiling": self.profiling,
        }


@dataclass(frozen=True)
class TsrThlbParallelBenchmarkRunResult:
    """One serial or LU-parallel benchmark record for a THLB parent step."""

    parent_step_id: str
    parent_label: str
    execution_mode: str
    worker_count: int
    lu_count: int
    wall_time_seconds: float
    peak_memory_mb: float | None
    status: str
    input_area_ha: float
    removed_area_ha: float
    remaining_area_ha: float
    output_row_count: int
    result_json_path: Path
    output_path: Path
    parity_with_serial: bool | None
    parity_removed_area_delta_ha: float | None
    parity_remaining_area_delta_ha: float | None
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "parent_step_id": self.parent_step_id,
            "parent_label": self.parent_label,
            "execution_mode": self.execution_mode,
            "worker_count": self.worker_count,
            "lu_count": self.lu_count,
            "wall_time_seconds": self.wall_time_seconds,
            "peak_memory_mb": self.peak_memory_mb,
            "status": self.status,
            "input_area_ha": self.input_area_ha,
            "removed_area_ha": self.removed_area_ha,
            "remaining_area_ha": self.remaining_area_ha,
            "output_row_count": self.output_row_count,
            "result_json_path": str(self.result_json_path),
            "output_path": str(self.output_path),
            "parity_with_serial": self.parity_with_serial,
            "parity_removed_area_delta_ha": self.parity_removed_area_delta_ha,
            "parity_remaining_area_delta_ha": self.parity_remaining_area_delta_ha,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class TsrThlbParallelBenchmarkResult:
    """Aggregate benchmark summary for one or more THLB parent steps."""

    summary_path: Path
    run_results: tuple[TsrThlbParallelBenchmarkRunResult, ...]
    parent_step_ids: tuple[str, ...]
    landscape_units: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary_path": str(self.summary_path),
            "parent_step_ids": list(self.parent_step_ids),
            "landscape_units": list(self.landscape_units),
            "run_results": [item.to_dict() for item in self.run_results],
        }


def _read_json_object(path: Path, *, description: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"{description} not found: {resolved}")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid {description.lower()} payload: {resolved}")
    return payload


def _normalize_tsa_token(value: str) -> str:
    return value.strip().replace("_", " ").casefold()


def _resolve_tsa_record(*, tsa: str, registry_path: Path) -> TsrOverlayTsaRecord:
    payload = _read_json_object(registry_path, description="TSR registry JSON")
    records = payload.get("tsas")
    if not isinstance(records, list):
        raise TsrRecipeError("TSR registry JSON is missing a valid `tsas` list.")
    normalized = _normalize_tsa_token(tsa)
    matches: list[TsrOverlayTsaRecord] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        record = TsrOverlayTsaRecord(
            tsa_id=str(item.get("tsa_id", "")),
            tsa_code=str(item.get("tsa_code", "")),
            tsa_name=str(item.get("tsa_name", "")),
        )
        if normalized in {
            _normalize_tsa_token(record.tsa_id),
            _normalize_tsa_token(record.tsa_code),
            _normalize_tsa_token(record.tsa_code.lstrip("0") or record.tsa_code),
            _normalize_tsa_token(record.tsa_name),
        }:
            matches.append(record)
    if not matches:
        raise TsrRecipeError(f"No canonical TSR TSA match found for `{tsa}`.")
    if len(matches) > 1:
        labels = ", ".join(f"{record.tsa_code}:{record.tsa_name}" for record in matches)
        raise TsrRecipeError(f"Ambiguous TSR TSA match for `{tsa}`: {labels}")
    return matches[0]


def _load_resource_yaml(resource_name: str) -> dict[str, Any]:
    resource = importlib_resources.files(_TSR_RECIPE_RESOURCE_PACKAGE).joinpath(
        resource_name
    )
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid packaged TSR recipe template: {resource_name}")
    return payload


def _repo_relative(path: Path, *, source_root: Path) -> str:
    return path.expanduser().resolve().relative_to(source_root.resolve()).as_posix()


def default_tsr_source_layers_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance source-layer recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml"
    )


def default_tsr_thlb_netdown_recipe_path(*, instance_root: Path) -> Path:
    """Return the default per-instance THLB netdown recipe path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml"
    )


def default_tsr_thlb_netdown_output_path(*, instance_root: Path) -> Path:
    """Return the default stand-level THLB checkpoint output path."""

    return (
        instance_root.expanduser().resolve()
        / "data"
        / "tsr"
        / "thlb_netdown_checkpoint.feather"
    )


def default_tsr_thlb_netdown_audit_path(*, instance_root: Path) -> Path:
    """Return the default THLB netdown audit JSON path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.audit.json"
    )


def default_tsr_thlb_reconstructed_output_path(*, instance_root: Path) -> Path:
    """Return the default reconstructed fragment/resultant THLB checkpoint path."""

    return (
        instance_root.expanduser().resolve()
        / "data"
        / "tsr"
        / "thlb_reconstructed_checkpoint.feather"
    )


def default_tsr_thlb_reconstructed_audit_path(*, instance_root: Path) -> Path:
    """Return the default reconstructed THLB audit JSON path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_reconstructed.audit.json"
    )


def default_tsr_thlb_netdown_status_report_path(*, instance_root: Path) -> Path:
    """Return the default human-readable hybrid THLB status report path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_netdown.status.md"
    )


def default_tsr_thlb_reconstructed_status_report_path(*, instance_root: Path) -> Path:
    """Return the default human-readable reconstructed THLB status report path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_reconstructed.status.md"
    )


def default_tsr_thlb_workbench_notebook_path(*, instance_root: Path) -> Path:
    """Return the default generated THLB workbench notebook path."""

    return (
        instance_root.expanduser().resolve()
        / "workbench"
        / "tsr"
        / "thlb_netdown.workbench.ipynb"
    )


def default_tsr_thlb_workbench_locked_script_path(*, instance_root: Path) -> Path:
    """Return the default locked THLB workbench script path."""

    return (
        instance_root.expanduser().resolve()
        / "workbench"
        / "tsr"
        / "thlb_netdown.locked.py"
    )


def default_tsr_thlb_workbench_locked_recipe_path(*, instance_root: Path) -> Path:
    """Return the default frozen THLB recipe copy path."""

    return (
        instance_root.expanduser().resolve()
        / "workbench"
        / "tsr"
        / "thlb_netdown.locked.recipe.yaml"
    )


def default_tsr_thlb_notebook_runs_root(*, instance_root: Path) -> Path:
    """Return the default runtime root for notebook-driven THLB step runs."""

    return (
        instance_root.expanduser().resolve()
        / "runtime"
        / "logs"
        / "tsr"
        / "notebook_runs"
    )


def default_tsr_thlb_parallel_benchmark_root(*, instance_root: Path) -> Path:
    """Return the default runtime root for LU-parallel THLB benchmark artifacts."""

    return (
        instance_root.expanduser().resolve()
        / "runtime"
        / "logs"
        / "tsr"
        / "parallel_benchmarks"
    )


def default_tsr_thlb_lu_partition_root(*, instance_root: Path) -> Path:
    """Return the default runtime root for cached LU-clipped THLB partitions."""

    return (
        instance_root.expanduser().resolve()
        / "runtime"
        / "logs"
        / "tsr"
        / "lu_partitions"
    )


def resolve_tsr_workbench_instance_root(*, start: Path | None = None) -> Path:
    """Resolve the enclosing instance root for a generated THLB workbench."""

    origin = (start or Path.cwd()).expanduser().resolve()
    for candidate in (origin, *origin.parents):
        if (candidate / "config" / "tsr" / "thlb_netdown.recipe.yaml").exists():
            return candidate
    raise TsrRecipeError(
        "Could not resolve the instance root from the current notebook working directory. "
        "Start the notebook from inside a FEMIC instance or set INSTANCE_ROOT manually."
    )


def _write_recipe_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def init_tsr_recipe_scaffolds(
    *,
    instance_root: Path,
    tsa: str,
    registry_path: Path,
    documents_path: Path,
    candidate_facts_path: Path,
    source_root: Path,
    overlay_path: Path,
    overrides_path: Path,
    source_layers_recipe_path: Path,
    thlb_netdown_recipe_path: Path,
    overwrite: bool = False,
) -> TsrRecipeInitResult:
    """Initialize per-instance TSR recipe scaffold YAML files."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_registry_path = registry_path.expanduser().resolve()
    resolved_documents_path = documents_path.expanduser().resolve()
    resolved_candidate_facts_path = candidate_facts_path.expanduser().resolve()
    resolved_overlay_path = overlay_path.expanduser().resolve()
    resolved_overrides_path = overrides_path.expanduser().resolve()
    resolved_source_layers_recipe_path = (
        source_layers_recipe_path.expanduser().resolve()
    )
    resolved_thlb_netdown_recipe_path = thlb_netdown_recipe_path.expanduser().resolve()

    for candidate_path in (
        resolved_overlay_path,
        resolved_overrides_path,
        resolved_source_layers_recipe_path,
        resolved_thlb_netdown_recipe_path,
    ):
        try:
            candidate_path.relative_to(resolved_instance_root)
        except ValueError as exc:
            raise TsrRecipeError(
                "TSR recipe paths must live under the instance root."
            ) from exc

    if not overwrite:
        existing = [
            path
            for path in (
                resolved_source_layers_recipe_path,
                resolved_thlb_netdown_recipe_path,
            )
            if path.exists()
        ]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            raise TsrRecipeError(
                "TSR recipe scaffold(s) already exist: "
                f"{joined}. Use `--overwrite` to replace them."
            )

    tsa_record = _resolve_tsa_record(tsa=tsa, registry_path=resolved_registry_path)
    canonical_inputs = TsrRecipeCanonicalInputs(
        registry_path=_repo_relative(resolved_registry_path, source_root=source_root),
        documents_path=_repo_relative(resolved_documents_path, source_root=source_root),
        candidate_facts_path=_repo_relative(
            resolved_candidate_facts_path, source_root=source_root
        ),
    )
    source_layers_instance_inputs = TsrSourceLayersRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
        download_root="data/downloads/bcdc",
    )
    thlb_instance_inputs = TsrThlbNetdownRecipeInstanceInputs(
        overlay_path=str(
            resolved_overlay_path.relative_to(resolved_instance_root).as_posix()
        ),
        source_layer_recipe_path=str(
            resolved_source_layers_recipe_path.relative_to(
                resolved_instance_root
            ).as_posix()
        ),
        source_layer_overrides_path=str(
            resolved_overrides_path.relative_to(resolved_instance_root).as_posix()
        ),
    )

    source_layers_template = _load_resource_yaml(_SOURCE_LAYERS_RECIPE_RESOURCE)
    thlb_template = _load_resource_yaml(_THLB_NETDOWN_RECIPE_RESOURCE)

    source_layers_record = TsrSourceLayersRecipeRecord(
        schema_version=int(source_layers_template.get("schema_version", 1)),
        recipe_kind=str(source_layers_template.get("recipe_kind", "source_layers")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=source_layers_instance_inputs,
        recipe_contract=dict(source_layers_template.get("recipe_contract", {})),
        entries=(),
    )
    thlb_record = TsrThlbNetdownRecipeRecord(
        schema_version=int(thlb_template.get("schema_version", 1)),
        recipe_kind=str(thlb_template.get("recipe_kind", "thlb_netdown")),
        tsa=tsa_record,
        canonical_inputs=canonical_inputs,
        instance_inputs=thlb_instance_inputs,
        recipe_contract=dict(thlb_template.get("recipe_contract", {})),
        parent_steps=(),
        steps=(),
    )

    _write_recipe_yaml(
        resolved_source_layers_recipe_path,
        source_layers_record.to_dict(),
    )
    _write_recipe_yaml(
        resolved_thlb_netdown_recipe_path,
        thlb_record.to_dict(),
    )
    return TsrRecipeInitResult(
        tsa=tsa_record,
        source_layers_recipe_path=resolved_source_layers_recipe_path,
        thlb_netdown_recipe_path=resolved_thlb_netdown_recipe_path,
        created_source_layers_recipe=True,
        created_thlb_netdown_recipe=True,
    )


def load_tsr_source_layers_recipe(path: Path) -> TsrSourceLayersRecipeRecord:
    """Load one per-instance source-layer recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR source-layer recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "source_layers":
        raise TsrRecipeError(f"Invalid TSR source-layer recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR source-layer recipe structure: {resolved}")
    return TsrSourceLayersRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="source_layers",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrSourceLayersRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
            download_root=str(instance_payload.get("download_root", "")),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        entries=tuple(
            item for item in payload.get("entries", []) if isinstance(item, dict)
        ),
    )


def load_tsr_thlb_netdown_recipe(path: Path) -> TsrThlbNetdownRecipeRecord:
    """Load one per-instance THLB netdown recipe scaffold YAML file."""

    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TsrRecipeError(f"TSR THLB netdown recipe not found: {resolved}")
    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe payload: {resolved}")
    if str(payload.get("recipe_kind", "")) != "thlb_netdown":
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe kind: {resolved}")
    tsa_payload = payload.get("tsa")
    canonical_payload = payload.get("canonical_inputs")
    instance_payload = payload.get("instance_inputs")
    if (
        not isinstance(tsa_payload, dict)
        or not isinstance(canonical_payload, dict)
        or not isinstance(instance_payload, dict)
    ):
        raise TsrRecipeError(f"Invalid TSR THLB netdown recipe structure: {resolved}")
    return TsrThlbNetdownRecipeRecord(
        schema_version=int(payload.get("schema_version", 1)),
        recipe_kind="thlb_netdown",
        tsa=TsrOverlayTsaRecord(
            tsa_id=str(tsa_payload.get("tsa_id", "")),
            tsa_code=str(tsa_payload.get("tsa_code", "")),
            tsa_name=str(tsa_payload.get("tsa_name", "")),
        ),
        canonical_inputs=TsrRecipeCanonicalInputs(
            registry_path=str(canonical_payload.get("registry_path", "")),
            documents_path=str(canonical_payload.get("documents_path", "")),
            candidate_facts_path=str(canonical_payload.get("candidate_facts_path", "")),
        ),
        instance_inputs=TsrThlbNetdownRecipeInstanceInputs(
            overlay_path=str(instance_payload.get("overlay_path", "")),
            source_layer_recipe_path=str(
                instance_payload.get("source_layer_recipe_path", "")
            ),
            source_layer_overrides_path=str(
                instance_payload.get("source_layer_overrides_path", "")
            ),
        ),
        recipe_contract=dict(payload.get("recipe_contract", {})),
        parent_steps=tuple(
            item for item in payload.get("parent_steps", []) if isinstance(item, dict)
        ),
        steps=tuple(
            item for item in payload.get("steps", []) if isinstance(item, dict)
        ),
    )


_RECIPE_ENTRY_ID_RE = re.compile(r"[^a-z0-9]+")


def _recipe_entry_id(query: str) -> str:
    slug = _RECIPE_ENTRY_ID_RE.sub("_", query.strip().casefold()).strip("_")
    return slug or "entry"


def _recipe_status_from_resolve(result: Any) -> str:
    top_match = result.top_match
    if top_match is None:
        return "no_hit"
    if any("alias/query variant" in note for note in result.notes):
        return "alias_hit"
    matched_by = top_match.matched_by
    if (
        matched_by.startswith("object_name:")
        or matched_by.startswith("object_short_name:")
        or matched_by.startswith("object_name_suffix:")
        or matched_by.startswith("object_name_stem:")
    ):
        return "exact_hit"
    return "weak_text_hit"


def _used_alias_from_notes(notes: tuple[str, ...]) -> str:
    return next(
        (
            note.split("`")[1]
            for note in notes
            if "alias/query variant" in note and "`" in note
        ),
        "",
    )


def _resource_object_names(resources: tuple[Any, ...]) -> tuple[str, ...]:
    names: list[str] = []
    for resource in resources:
        object_name = str(getattr(resource, "object_name", "") or "").strip()
        if object_name and object_name not in names:
            names.append(object_name)
    return tuple(names)


def _resolve_path_from_recipe(source_root: Path, relative_path: str) -> Path:
    return (source_root / Path(relative_path)).expanduser().resolve()


def _resolve_instance_path(instance_root: Path, relative_path: str) -> Path:
    return (instance_root / Path(relative_path)).expanduser().resolve()


def _load_override_map(
    overrides_path: Path,
) -> dict[str, TsrSourceLayerOverrideEntry]:
    if not overrides_path.exists():
        return {}
    record = load_tsr_source_layer_overrides(overrides_path)
    return {entry.query.casefold(): entry for entry in record.entries}


def _load_overlay_attempt_map(
    overlay_path: Path,
) -> dict[str, dict[str, Any]]:
    if not overlay_path.exists():
        return {}
    payload = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    review_payload = payload.get("bcdc_acquisition_review")
    if not isinstance(review_payload, dict):
        return {}
    attempts = review_payload.get("attempts", [])
    if not isinstance(attempts, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        query = str(attempt.get("query", "")).strip()
        if not query:
            continue
        result[query.casefold()] = attempt
    return result


def _review_rows_for_recipe(
    candidate_facts_path: Path,
    *,
    tsa_code: str,
) -> tuple[TsrFactReviewRow, ...]:
    report = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa=tsa_code,
        fact_families=("source_layer_candidate",),
    )
    rows = [
        row
        for row in report.rows
        if row.recommended_query and row.quality != "likely_noise"
    ]
    deduped: dict[str, TsrFactReviewRow] = {}
    grouped: dict[str, list[TsrFactReviewRow]] = {}
    quality_rank = {"likely_useful": 0, "needs_review": 1, "likely_noise": 2}
    for row in rows:
        key = row.recommended_query.casefold()
        grouped.setdefault(key, []).append(row)
        current = deduped.get(key)
        if current is None or quality_rank[row.quality] < quality_rank[current.quality]:
            deduped[key] = row
    ordered = sorted(
        deduped.values(),
        key=lambda row: (
            quality_rank[row.quality],
            row.recommended_query,
            row.page_number if row.page_number is not None else 10**9,
        ),
    )
    output_rows: list[TsrFactReviewRow] = []
    for row in ordered:
        row_group = grouped[row.recommended_query.casefold()]
        output_rows.append(
            TsrFactReviewRow(
                tsa_id=row.tsa_id,
                tsa_code=row.tsa_code,
                tsa_name=row.tsa_name,
                fact_family=row.fact_family,
                extracted_value=row.extracted_value,
                recommended_query=row.recommended_query,
                quality=row.quality,
                quality_reason=row.quality_reason,
                snippet=row.snippet,
                page_number=row.page_number,
                title=row.title,
                cycle_label=row.cycle_label,
                cycle_year=row.cycle_year,
                provenance_id=" | ".join(
                    item.provenance_id for item in row_group if item.provenance_id
                ),
                source_url=row.source_url,
            )
        )
    return tuple(output_rows)


def _replacement_family_dicts(
    entry: TsrSourceLayerOverrideEntry | None,
) -> list[dict[str, object]]:
    if entry is None:
        return []
    return [candidate.to_dict() for candidate in entry.replacement_family_candidates]


def _build_source_recipe_entry(
    row: TsrFactReviewRow,
    *,
    resolve_result: Any,
    override_entry: TsrSourceLayerOverrideEntry | None,
    overlay_attempt: dict[str, Any] | None,
    instance_root: Path,
) -> dict[str, Any]:
    top_match = resolve_result.top_match
    resources = top_match.resources if top_match is not None else ()
    resource_object_names = _resource_object_names(resources)
    current_public_status = _recipe_status_from_resolve(resolve_result)
    suggested_fetch_strategy = (
        top_match.suggested_fetch_strategy if top_match is not None else None
    )
    direct_download_candidates = (
        len(top_match.direct_download_resources) if top_match is not None else 0
    )
    has_service = any(resource.classification == SERVICE for resource in resources)
    has_wfs_queryable_service = any(resource.wfs_queryable for resource in resources)
    has_indirect_custom_download = any(
        resource.classification == INDIRECT_CUSTOM_DOWNLOAD for resource in resources
    )
    has_supporting_document = any(
        resource.classification == SUPPORTING_DOCUMENT for resource in resources
    )

    if override_entry is not None and override_entry.override_kind:
        acquisition_strategy = "override"
    elif current_public_status == "no_hit":
        acquisition_strategy = "override_required"
    elif current_public_status == "weak_text_hit":
        acquisition_strategy = "manual_review_required"
    elif suggested_fetch_strategy:
        acquisition_strategy = "wfs_fetch"
    elif direct_download_candidates:
        acquisition_strategy = "direct_download"
    elif has_indirect_custom_download:
        acquisition_strategy = "dwds_order"
    else:
        acquisition_strategy = "manual_review_required"

    notes = list(resolve_result.notes)
    if top_match is not None:
        notes.extend(list(top_match.manual_follow_up))

    used_alias = _used_alias_from_notes(resolve_result.notes)
    acquisition_query = used_alias or (
        resource_object_names[0] if resource_object_names else row.recommended_query
    )

    artifact_path = ""
    prior_run_status = "pending"
    if overlay_attempt is not None:
        raw_artifact_path = str(overlay_attempt.get("saved_path", "")).replace(
            "\\", "/"
        )
        if raw_artifact_path:
            artifact_candidate = Path(raw_artifact_path)
            if artifact_candidate.is_absolute():
                try:
                    artifact_path = str(
                        artifact_candidate.resolve()
                        .relative_to(instance_root)
                        .as_posix()
                    )
                except ValueError:
                    artifact_path = raw_artifact_path
            elif raw_artifact_path.startswith(f"external/{instance_root.name}/"):
                artifact_path = raw_artifact_path.split(
                    f"external/{instance_root.name}/", 1
                )[1]
            else:
                artifact_path = raw_artifact_path
        prior_run_status = str(overlay_attempt.get("acquisition_outcome", "pending"))
        prior_notes = str(overlay_attempt.get("notes", "")).strip()
        if prior_notes:
            notes.extend(
                part.strip() for part in prior_notes.split(" | ") if part.strip()
            )

    return {
        "entry_id": _recipe_entry_id(row.recommended_query),
        "label": row.recommended_query,
        "recommended_query": row.recommended_query,
        "acquisition_query": acquisition_query,
        "extracted_value": row.extracted_value,
        "quality": row.quality,
        "quality_reason": row.quality_reason,
        "snippet": row.snippet,
        "page_number": row.page_number,
        "document_title": row.title,
        "cycle_label": row.cycle_label,
        "cycle_year": row.cycle_year,
        "provenance_id": row.provenance_id,
        "source_url": row.source_url,
        "current_public_status": current_public_status,
        "matched_by": top_match.matched_by if top_match is not None else "",
        "used_alias": used_alias,
        "top_match_title": top_match.title if top_match is not None else "",
        "dataset_page_url": top_match.dataset_page_url if top_match is not None else "",
        "suggested_fetch_strategy": suggested_fetch_strategy or "",
        "direct_download_candidates": direct_download_candidates,
        "has_service": has_service,
        "has_wfs_queryable_service": has_wfs_queryable_service,
        "has_indirect_custom_download": has_indirect_custom_download,
        "has_supporting_document": has_supporting_document,
        "acquisition_strategy": acquisition_strategy,
        "run_status": prior_run_status,
        "artifact_path": artifact_path
        or (
            override_entry.override_value
            if override_entry is not None
            and override_entry.override_kind in {"local_path", "datalad_path"}
            else ""
        ),
        "override_kind": override_entry.override_kind
        if override_entry is not None
        else "",
        "override_value": override_entry.override_value
        if override_entry is not None
        else "",
        "replacement_family_candidates": _replacement_family_dicts(override_entry),
        "feature_count": overlay_attempt.get("feature_count", "")
        if overlay_attempt is not None
        else "",
        "order_id": overlay_attempt.get("order_id", "")
        if overlay_attempt is not None
        else "",
        "submission_status": overlay_attempt.get("submission_status", "")
        if overlay_attempt is not None
        else "",
        "failure_message": overlay_attempt.get("failure_message", "")
        if overlay_attempt is not None
        else "",
        "notes": notes,
    }


def _overlay_attempt_for_row(
    row: TsrFactReviewRow,
    *,
    resolve_result: Any,
    overlay_attempt_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    top_match = resolve_result.top_match
    resources = top_match.resources if top_match is not None else ()
    candidate_keys = [
        row.recommended_query.casefold(),
        _used_alias_from_notes(resolve_result.notes).casefold(),
    ]
    candidate_keys.extend(name.casefold() for name in _resource_object_names(resources))
    for key in candidate_keys:
        if key and key in overlay_attempt_map:
            return overlay_attempt_map[key]
    return None


def _load_tsa_documents_for_recipe(
    documents_path: Path, *, tsa_id: str
) -> tuple[dict[str, dict[str, Any]], tuple[dict[str, Any], ...]]:
    payload = _read_json_object(documents_path, description="TSR documents JSON")
    documents = payload.get("documents")
    if not isinstance(documents, list):
        raise TsrRecipeError("TSR documents JSON is missing a valid `documents` list.")

    records: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for item in documents:
        if not isinstance(item, dict):
            continue
        if str(item.get("tsa_id", "")) != tsa_id:
            continue
        record = dict(item)
        relative_path = str(record.get("relative_path", "")).strip()
        if relative_path:
            index[relative_path] = record
        records.append(record)
    return index, tuple(records)


def _provenance_document_path(provenance_id: str) -> str:
    return provenance_id.split("#", 1)[0].strip()


def _coerce_cycle_year(value: object) -> int:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else 0


def _normalize_whitespace(text: str) -> str:
    return " ".join(str(text or "").split())


def _normalize_step_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
    return slug or "step"


def _choose_preferred_thlb_documents(
    rows: tuple[TsrFactReviewRow, ...],
    *,
    documents_index: dict[str, dict[str, Any]],
    documents: tuple[dict[str, Any], ...],
) -> tuple[tuple[TsrFactReviewRow, ...], tuple[str, ...]]:
    available_paths = {
        _provenance_document_path(row.provenance_id)
        for row in rows
        if row.provenance_id.strip()
    }
    if not available_paths:
        return rows, ()

    latest_year = max(
        (_coerce_cycle_year(doc.get("cycle_year")) for doc in documents),
        default=0,
    )
    preferred_paths = tuple(
        path
        for path, doc in documents_index.items()
        if path in available_paths
        and _coerce_cycle_year(doc.get("cycle_year")) == latest_year
        and str(doc.get("document_type", "")).casefold() == "data_package"
    )
    if not preferred_paths:
        preferred_paths = tuple(
            path
            for path, doc in documents_index.items()
            if path in available_paths
            and _coerce_cycle_year(doc.get("cycle_year")) == latest_year
        )
    if not preferred_paths:
        return rows, tuple(sorted(available_paths))

    selected = tuple(
        row
        for row in rows
        if _provenance_document_path(row.provenance_id) in preferred_paths
    )
    return (selected or rows), tuple(sorted(preferred_paths))


def _load_selected_tsr_pdf_pages(
    *,
    tsa_id: str,
    selected_document_paths: Sequence[str],
) -> tuple[tuple[dict[str, Any], ...], str | None]:
    if not selected_document_paths:
        return (), None
    try:
        from pypdf import PdfReader
    except Exception:  # pragma: no cover - dependency seam
        return (), None
    from femic.user_config import default_femic_tsr_corpus_root

    relative_path = str(selected_document_paths[0]).strip()
    if not relative_path:
        return (), None
    pdf_path = default_femic_tsr_corpus_root() / "tsa" / tsa_id / Path(relative_path)
    if not pdf_path.exists():
        return (), None
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:  # pragma: no cover - runtime seam
        return (), None

    pages: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # pragma: no cover - runtime seam
            text = ""
        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "relative_path": relative_path,
            }
        )
    return tuple(pages), relative_path


def _clean_tsr_page_lines(text: str) -> list[str]:
    cleaned: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = _normalize_whitespace(raw_line)
        lower = line.casefold()
        if not line:
            continue
        if "timber supply review data package" in lower:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        cleaned.append(line)
    return cleaned


def _parse_land_base_summary_row(line: str) -> dict[str, Any] | None:
    normalized = _normalize_whitespace(line)
    if not normalized:
        return None
    if normalized.casefold().startswith("table 3."):
        return None
    first_numeric = re.search(r"\d[\d,]*(?:\.\d+)?", normalized)
    if first_numeric is None:
        return None
    label = _normalize_whitespace(normalized[: first_numeric.start()])
    if not label:
        return None
    if label.casefold() in {
        "area net of overlaps with prior items",
        "land classification",
        "total area",
        "forested area",
        "net area removed",
        "percent",
    }:
        return None
    numeric_tokens = re.findall(
        r"\d[\d,]*(?:\.\d+)?", normalized[first_numeric.start() :]
    )
    if not numeric_tokens:
        return None
    numbers = [float(token.replace(",", "")) for token in numeric_tokens]
    return {
        "parent_label": label,
        "numeric_tokens": tuple(numbers),
    }


def _extract_land_base_summary_rows(
    pages: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    in_table = False
    started_rows = False
    pending_parts: list[str] = []
    for page in pages:
        lines = _clean_tsr_page_lines(str(page.get("text", "")))
        for line in lines:
            lower = line.casefold()
            if (
                "preliminary land base classification summary" in lower
                and not _is_toc_like_text(line)
            ):
                in_table = True
                pending_parts = []
                continue
            if not in_table:
                continue
            if re.match(r"^6\.[234](?:\.\d+)?\s", line):
                in_table = False
                break
            if not started_rows:
                if not line.startswith("Total TSA area"):
                    continue
                started_rows = True
            if (
                "area net of overlaps with prior items" in lower
                or lower.startswith("land classification ")
                or lower.startswith("total area ")
                or lower.startswith("forested area ")
                or lower.startswith("net area removed ")
                or lower.startswith("percent (%)")
            ):
                continue
            if not any(char.isdigit() for char in line):
                pending_parts.append(line)
                continue
            combined = _normalize_whitespace(" ".join([*pending_parts, line]))
            pending_parts = []
            parsed = _parse_land_base_summary_row(combined)
            if parsed is None:
                continue
            parsed["page_number"] = int(page.get("page_number", 0))
            parsed["table_provenance"] = (
                f"{page.get('relative_path', '')}#page={int(page.get('page_number', 0))}"
            )
            rows.append(parsed)
    return tuple(rows)


def _stage_from_section_number(section_number: str) -> str:
    if section_number.startswith("6.2."):
        return "glb_to_aflb"
    if section_number.startswith("6.3."):
        return "aflb_to_lhlb"
    if section_number.startswith("6.4."):
        return "lhlb_to_thlb"
    return "context"


def _extract_land_base_subsections(
    pages: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    subsections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    stop = False
    heading_re = re.compile(r"^(?P<section>6\.[234]\.\d+)\s+(?P<title>.+)$")
    for page in pages:
        lines = _clean_tsr_page_lines(str(page.get("text", "")))
        for line in lines:
            if re.match(r"^7\.\s", line) and not _is_toc_like_text(line):
                if current is not None:
                    subsections.append(current)
                    current = None
                stop = True
                break
            heading_match = heading_re.match(line)
            if heading_match:
                if _is_toc_like_text(line):
                    continue
                if current is not None:
                    subsections.append(current)
                section_number = heading_match.group("section")
                title = _normalize_whitespace(heading_match.group("title"))
                current = {
                    "section_number": section_number,
                    "title": title,
                    "page_number": int(page.get("page_number", 0)),
                    "provenance_id": (
                        f"{page.get('relative_path', '')}#page={int(page.get('page_number', 0))}"
                    ),
                    "land_base_stage": _stage_from_section_number(section_number),
                    "lines": [],
                }
                continue
            if re.match(r"^6\.[234]\s+", line) and not _is_toc_like_text(line):
                continue
            if current is not None:
                current["lines"].append(line)
        if stop:
            break
    if current is not None:
        subsections.append(current)
    for subsection in subsections:
        subsection["body"] = _normalize_whitespace(
            " ".join(subsection.pop("lines", []))
        )
    return tuple(subsections)


def _infer_parent_row_stage(
    *,
    label: str,
    linked_subsection: dict[str, Any] | None,
    seen_aflb_row: bool,
    seen_thlb_row: bool,
) -> tuple[str, str]:
    lower = label.casefold()
    # Table 3 is the canonical roadmap for the Williams Lake TSA netdown
    # ladder. A few rows need explicit overrides so subsection numbering does
    # not drag them into the wrong stage group in the generated recipe/report.
    explicit_stage_overrides: dict[str, tuple[str, str]] = {
        "future roads": ("glb_to_aflb", "drop_from_universe"),
        "proven aboriginal rights areas": ("aflb_to_lhlb", "legal_harvest_exclusion"),
        "buffered trails": ("lhlb_to_thlb", "projected_harvest_exclusion"),
    }
    override = explicit_stage_overrides.get(lower)
    if override is not None:
        return override
    if lower == "total tsa area":
        return "reference_target", "reference_only"
    if "analysis forest land base" in lower:
        return "glb_to_aflb", "reference_only"
    if "legally harvestable land base" in lower:
        return "aflb_to_lhlb", "reference_only"
    if "timber harvesting land base" in lower:
        return "lhlb_to_thlb", "reference_only"
    if "long-term thlb" in lower:
        return "reference_target", "reference_only"
    if linked_subsection is not None:
        stage = str(linked_subsection.get("land_base_stage", "context"))
    elif not seen_aflb_row:
        stage = "glb_to_aflb"
    elif seen_thlb_row:
        stage = "reference_target"
    else:
        stage = "context"
    execution_class = _infer_execution_class(
        stage=stage,
        action="exclude" if stage != "context" else "section_heading",
        step_kind="netdown_rule" if stage != "context" else "context",
    )
    return stage, execution_class


def _build_land_base_parent_step_id(row_order: int, label: str) -> str:
    return f"thlb_parent_{row_order:03d}_{_normalize_step_slug(label)}"


def _parent_kind_for_execution_class(execution_class: str) -> str:
    if execution_class == "reference_only":
        return "milestone"
    return "transformation"


def _normalize_source_query_key(value: str) -> str:
    return _normalize_whitespace(value).casefold()


def _extract_layer_like_tokens(text: str) -> tuple[str, ...]:
    if not text:
        return ()
    matches = re.findall(r"\b[A-Z][A-Z0-9_]{2,}(?:\.[A-Z0-9_]+)?\b", text)
    unique: list[str] = []
    seen: set[str] = set()
    for match in matches:
        if match in seen:
            continue
        seen.add(match)
        unique.append(match)
    return tuple(unique)


def _extract_data_source_comment_tokens(text: str) -> tuple[str, ...]:
    normalized = _normalize_whitespace(text)
    if not normalized or "Data source and comments:" not in normalized:
        return ()
    suffix = normalized.split("Data source and comments:", 1)[1]
    if "Table " in suffix:
        suffix = suffix.split("Table ", 1)[0]
    return _extract_layer_like_tokens(suffix)


def _strip_trailing_table_and_comment_blocks(text: str) -> str:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return ""
    cut_points: list[int] = []
    table_match = re.search(r"\bTable\s+\d+\.\s", normalized)
    if table_match:
        cut_points.append(table_match.start())
    comments_match = re.search(r"\bData source and comments:\b", normalized)
    if comments_match:
        cut_points.append(comments_match.start())
    if cut_points:
        normalized = normalized[: min(cut_points)].rstrip()
    return normalized


def _split_subsection_into_draft_subrules(text: str) -> tuple[str, ...]:
    normalized = _strip_trailing_table_and_comment_blocks(text)
    if not normalized:
        return ()

    def is_tableish_sentence(sentence: str) -> bool:
        stripped = sentence.strip()
        lower = stripped.casefold()
        if stripped.startswith("Table "):
            return True
        if "Data source and comments:" in stripped:
            return True
        if "table " in lower:
            return True
        table_markers = (
            "land ownership types",
            "area excluded",
            "attributes description",
            "logging history",
            "designations total",
            "road class width",
            "width and area of existing road",
            "total area (hectares)",
        )
        if any(marker in lower for marker in table_markers):
            return True
        if len(re.findall(r"\d[\d,]*", stripped)) >= 5:
            return True
        return False

    raw_sentences = [
        _normalize_whitespace(part)
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized)
        if _normalize_whitespace(part)
    ]
    sentences: list[str] = []
    for sentence in raw_sentences:
        if sentences and sentences[-1].endswith(" v."):
            sentences[-1] = _normalize_whitespace(f"{sentences[-1]} {sentence}")
            continue
        sentences.append(sentence)
    return tuple(
        sentence
        for sentence in sentences
        if len(sentence) >= 25 and not is_tableish_sentence(sentence)
    )


def _is_rationale_only_draft_sentence(sentence: str) -> bool:
    lower = sentence.casefold()
    rationale_markers = (
        "the purpose of this section is to identify",
        "these areas do not contribute to forest management objectives",
        "the implications of these additional transfers",
        "separate estimates are made to reflect",
        "were reviewed by district staff",
        "was signed on",
        "are in stage 5 negotiations",
        "on june 26, 2014",
        "in that decision the scc outlined",
        "a spatial data set of land ownership was developed using",
    )
    return any(marker in lower for marker in rationale_markers)


def _infer_semantic_candidate_layers(
    sentence: str,
    *,
    subsection_source_hints: Sequence[str],
) -> tuple[str, ...]:
    lower = sentence.casefold()
    layers: list[str] = []
    if (
        "forest management land base" in lower
        or "fmlb" in lower
        or "vri" in lower
        or "crown closure" in lower
        or "site index" in lower
        or "species composition" in lower
        or "leading species" in lower
        or "broadleaf" in lower
        or "deciduous" in lower
    ):
        layers.append("vri")
    if (
        "freshwater atlas" in lower
        or "fwa" in lower
        or "lakes" in lower
        or "rivers" in lower
        or "wetlands" in lower
    ):
        layers.append("freshwater_atlas")
    if (
        "riparian" in lower
        or "rrz" in lower
        or "rmz" in lower
        or "stream class" in lower
        or "stream classification" in lower
        or "wetland class" in lower
        or "swamp class" in lower
        or "lake class" in lower
    ):
        layers.extend(
            [
                "reg_land_and_natural_resource_stream_classification_car_line",
                "reg_land_and_natural_resource_wetland_class_car_poly",
                "whse_basemapping_fwa_lakes_poly",
            ]
        )
    if (
        "harvest history" in lower
        or "harvested in the past" in lower
        or "consolidated harvest depletion" in lower
        or "faib" in lower
        or "past harvest" in lower
    ):
        layers.append("consolidated_harvest_depletion")
    if (
        "terrain stability" in lower
        or "unstable slope" in lower
        or "unstable slopes" in lower
        or "steep slope" in lower
        or "steep slopes" in lower
        or "cable logging" in lower
        or "inoperable" in lower
        or "highway 97" in lower
    ):
        layers.append("terrain_stability")
    if "road" in lower or "roads" in lower or "landing" in lower or "landings" in lower:
        layers.append("road_network")
    if (
        "wildlife habitat" in lower
        or "wildlife habitat areas" in lower
        or "general wildlife measures" in lower
        or "gwm" in lower
        or "ungulate winter range" in lower
        or "uwr" in lower
        or "conditional harvest zone" in lower
        or "no harvest zone" in lower
    ):
        layers.append("wildlife_habitat")
    if (
        "ownership code" in lower
        or "private" in lower
        or "federal" in lower
        or "first nations reserves" in lower
        or "community forest agreement" in lower
        or "community forest agreements" in lower
        or "fnwl" in lower
        or "woodlots" in lower
        or "tsilhqot" in lower
        or "nstq" in lower
        or "crown leases" in lower
        or any(token.endswith("F_OWN") for token in subsection_source_hints)
    ):
        layers.append("whse_forest_vegetation_f_own")
    unique: list[str] = []
    seen: set[str] = set()
    for layer in layers:
        if layer in seen:
            continue
        seen.add(layer)
        unique.append(layer)
    return tuple(unique)


def _infer_candidate_fields_and_values(
    sentence: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    lower = sentence.casefold()
    fields: list[str] = []
    values: list[str] = []
    notes: list[str] = []
    if "forest management land base" in lower or "fmlb" in lower:
        fields.append("FOR_MGMT_LAND_BASE_IND")
        notes.append(
            "TSR prose refers to the VRI FMLB/Forest Management Land Base attribute; "
            "validate its mapping to the current FEMIC/VRI field before locking logic."
        )
    if "crown closure" in lower:
        fields.append("CROWN_CLOSURE")
        if "10%" in sentence or "10 %" in sentence:
            values.append("< 10")
    if "leading species" in lower or "broadleaf" in lower or "deciduous" in lower:
        if "SPECIES_CD_1" not in fields:
            fields.append("SPECIES_CD_1")
        if "broadleaf" in lower or "deciduous" in lower:
            values.append("BROADLEAF_SPECIES_CODES")
    if (
        "timber_harvest_code" in lower
        or "conditional harvest zone" in lower
        or "no harvest zone" in lower
    ):
        if "TIMBER_HARVEST_CODE" not in fields:
            fields.append("TIMBER_HARVEST_CODE")
        if "no harvest zone" in lower:
            values.append("NO HARVEST ZONE")
        if "conditional harvest zone" in lower:
            values.append("CONDITIONAL HARVEST ZONE")
    if "ownership code 62" in lower:
        fields.append("OWNERSHIP_CODE")
        values.append("62")
    if "ownership code 69" in lower:
        if "OWNERSHIP_CODE" not in fields:
            fields.append("OWNERSHIP_CODE")
        values.append("69")
    if "ownership code 99" in lower or "crown leases" in lower:
        if "OWNERSHIP_CODE" not in fields:
            fields.append("OWNERSHIP_CODE")
        values.append("99")
    ownership_code_hits = re.findall(r"ownership code[s]?\s+(\d+)", lower)
    ownership_code_hits.extend(re.findall(r"\bcode[s]?\s+(\d+)\s+\(", lower))
    if ownership_code_hits:
        if "OWNERSHIP_CODE" not in fields:
            fields.append("OWNERSHIP_CODE")
        for hit in ownership_code_hits:
            if hit not in values:
                values.append(hit)
    if "ownership codes 62" in lower and "69" in lower:
        if "OWNERSHIP_CODE" not in fields:
            fields.append("OWNERSHIP_CODE")
        for hit in ("62", "69"):
            if hit not in values:
                values.append(hit)
    if (
        "private" in lower
        or "federal" in lower
        or "first nations reserves" in lower
        or "community forest agreement" in lower
        or "community forest agreements" in lower
        or "fnwl" in lower
        or "woodlots" in lower
        or "municipal" in lower
        or "leases" in lower
    ):
        if "OWNERSHIP_CLASS" not in fields:
            fields.append("OWNERSHIP_CLASS")
        ownership_value_map = {
            "private": "private",
            "federal": "federal",
            "first nations reserves": "first_nations_reserve",
            "community forest agreement": "community_forest_agreement",
            "community forest agreements": "community_forest_agreement",
            "fnwl": "fnwl",
            "woodlots": "woodlot",
            "municipal": "municipal",
            "leases": "lease",
        }
        for token, mapped_value in ownership_value_map.items():
            if token in lower and mapped_value not in values:
                values.append(mapped_value)
    return tuple(fields), tuple(values), tuple(notes)


def _infer_draft_subrule_operation_type(
    sentence: str,
    *,
    default_operation_type: str,
) -> str:
    lower = sentence.casefold()
    if "sensitivity analysis" in lower:
        return "reference_only"
    if (
        "remain in the aflb" in lower
        or "included in the aflb" in lower
        or "considered as contributing" in lower
    ):
        return "no_deduction"
    if "removed when defining the lhlb" in lower:
        return "defer_to_lhlb"
    return default_operation_type


def _build_draft_subrules_for_parent_step(
    *,
    parent_step_id: str,
    linked_subsection: dict[str, Any] | None,
    source_index: tuple[dict[str, Any], ...],
    execution_class: str,
) -> tuple[dict[str, Any], ...]:
    if linked_subsection is None:
        return ()
    subsection_title = str(linked_subsection.get("title", "")).strip()
    subsection_body = str(linked_subsection.get("body", "")).strip()
    if parent_step_id == "thlb_parent_023_future_roads":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Apply the TSR's future-RTL factor as an aspatial area reduction "
                    "across the current AFLB working land base."
                ),
                "rationale": (
                    "TSA29 section 6.2.3 says future roads, trails, and landings are "
                    "estimated from current performance and RESULTS data rather than "
                    "mapped as a present-day spatial road network."
                ),
                "candidate_layers": [],
                "candidate_fields": [],
                "candidate_values": [
                    "2.28% future RTL factor",
                    "22,754 ha total TSR benchmark",
                ],
                "candidate_operation_type": "aspatial_area_reduction",
                "field_mapping_notes": [
                    "Do not reuse the existing-roads spatial overlay logic for this parent step.",
                    "Do not model this step through THLB retention; reduce the stand-area fields that flow downstream into fragments instead.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if (
        subsection_title.casefold().strip()
        == "cultural heritage and archaeological resources."
    ):
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Treat HCA-protected archaeological sites as legally protected "
                    "features that are not auto-mapped into a public exclusion layer here."
                ),
                "rationale": (
                    "TSA29 section 6.4.9 says archaeological sites are protected under the "
                    "Heritage Conservation Act and cultural heritage resources are managed "
                    "through permit/FSP practice, not by citing a single downloadable "
                    "public exclusion layer."
                ),
                "candidate_layers": [],
                "candidate_fields": [],
                "candidate_values": [],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "Do not infer road, burn-severity, or other generic spatial layers from this prose.",
                    "Use reviewed permit/FSP practice and adopted overrides if a trusted spatial source is later identified.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Represent licensee/Tsilhqot'in cultural-heritage exclusions as an "
                    "aspatial THLB reduction rather than a guessed spatial overlay."
                ),
                "rationale": (
                    "The TSR says current practice expands exclusions and reserves through "
                    "boundary amendments, wildlife tree retention, and cultural resource "
                    "management zones, based on discussions with licensees and the "
                    "Tsilhqot'in National Government."
                ),
                "candidate_layers": [],
                "candidate_fields": [],
                "candidate_values": [
                    "2% of cutblock area",
                    "34,205 ha total TSR benchmark",
                ],
                "candidate_operation_type": "aspatial_reduction",
                "field_mapping_notes": [
                    "This is a benchmark-anchored aspatial reduction step, not a direct public-GIS query.",
                    "Reference practice inputs: TNG, Tolko FSP #780, West Fraser FSP #755, BCTS FSP #828.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if subsection_title.casefold().strip() == "riparian areas":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Buffer Cariboo stream-classification lines by the Table 15 "
                    "effective riparian widths for S1-S6 streams."
                ),
                "rationale": (
                    "Use the Cariboo stream-classification line layer with Table 15 "
                    "effective riparian widths (reserve width plus retained RMZ share) "
                    "to set THLB to 0 on riparian stream buffers."
                ),
                "candidate_layers": [
                    "reg_land_and_natural_resource_stream_classification_car_line"
                ],
                "candidate_fields": ["STREAM_CLASS"],
                "candidate_values": [
                    f"S{value}" for value in _RIPARIAN_STREAM_WIDTHS_M
                ],
                "candidate_operation_type": "exclude",
                "field_mapping_notes": [
                    "STREAM_CLASS uses numeric values 1-6 in the downloaded Cariboo stream-classification layer."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Buffer Cariboo wetland-class polygons by the Table 15 effective "
                    "riparian widths for W1-W5 wetlands."
                ),
                "rationale": (
                    "Use the Cariboo wetland-class polygon layer with Table 15 "
                    "effective riparian widths to set THLB to 0 on riparian wetland buffers."
                ),
                "candidate_layers": [
                    "reg_land_and_natural_resource_wetland_class_car_poly"
                ],
                "candidate_fields": ["SWAMP_CLASS"],
                "candidate_values": sorted(_RIPARIAN_WETLAND_WIDTHS_M),
                "candidate_operation_type": "exclude",
                "field_mapping_notes": [
                    "SWAMP_CLASS uses lowercase values such as w1-w5 in the downloaded Cariboo wetland-class layer."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_03",
                "human_summary": (
                    "Lake riparian classes L1-L4 remain a reviewed gap until a clean "
                    "Cariboo lake-class spatial source is adopted."
                ),
                "rationale": (
                    "Table 15 includes L1-L4 lake classes, but the current TSA29 instance "
                    "does not yet have a trustworthy lake-class vector artifact wired into "
                    "the notebook bridge."
                ),
                "candidate_layers": ["whse_basemapping_fwa_lakes_poly"],
                "candidate_fields": [],
                "candidate_values": [],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "FWA lakes polygons are present, but the lake classification surface still needs adoption."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_04",
                "human_summary": (
                    "Apply the special S4=30 m riparian width in Niut SRDZ and South "
                    "Chilcotin SRDZ as a later reviewed refinement."
                ),
                "rationale": (
                    "TSA29 section 6.4.2 increases the S4 riparian area width to 30 metres "
                    "in the Niut and South Chilcotin SRDZs to protect dolly varden trout habitat."
                ),
                "candidate_layers": [
                    "reg_land_and_natural_resource_stream_classification_car_line",
                    "rmp_landscape_unit_svw",
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                ],
                "candidate_fields": ["STREAM_CLASS", "LANDSCAPE_UNIT_NAME"],
                "candidate_values": ["S4", "Niut", "South Chilcotin"],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "Special-case LU/SRDZ overlays are not auto-executed in the first runnable bridge pass."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if subsection_title.casefold().strip() == "critical habitat for fish":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Use the legal CCLUP critical-fish-habitat polygons from the "
                    "Section 93.4 LAO / Map 4 source, not wildlife proxy layers."
                ),
                "rationale": (
                    "TSA29 section 6.3.4 says critical fish habitat boundaries come "
                    "from the Section 93.4 LAO establishing objectives for the CCLUP, "
                    "Map 4."
                ),
                "candidate_layers": ["whse_land_use_planning_rmp_plan_legal_poly_svw"],
                "candidate_fields": [
                    "STRGC_LAND_RSRCE_PLAN_NAME",
                    "LEGAL_FEAT_OBJECTIVE",
                    "LEGAL_FEAT_ATRB_1_VALUE",
                ],
                "candidate_values": [
                    "Cariboo Chilcotin Land Use Plan",
                    "Critical Habitat for Fish",
                    "CRITFISH",
                ],
                "candidate_operation_type": "exclude",
                "field_mapping_notes": [
                    "Keep the executable query inside the legal-planning fish-objective layer.",
                    "Do not revert to wildlife-habitat proxy layers for this parent step.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Treat the mapped critical-fish-habitat polygons as no-harvest "
                    "areas within the LHLB."
                ),
                "rationale": (
                    "The TSR says the LAO specifies these critical fish habitat "
                    "areas are to be maintained as no-harvest areas and excluded "
                    "from the LHLB."
                ),
                "candidate_layers": ["whse_land_use_planning_rmp_plan_legal_poly_svw"],
                "candidate_fields": [],
                "candidate_values": [
                    "no harvest",
                    "Section 93.4 LAO",
                ],
                "candidate_operation_type": "exclude",
                "field_mapping_notes": [
                    "If later refinement is needed, narrow the legal fish-objective attributes rather than swapping data sources."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if subsection_title.casefold().strip() == "lakeshore management":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Only the no-harvest overlap between Class A lake management "
                    "areas and VQO preservation should be excluded here."
                ),
                "rationale": (
                    "TSA29 section 6.3.5 says only Class A lakes with legal buffer "
                    "areas overlapping visual quality objective class "
                    "'preservation' are excluded from the LHLB."
                ),
                "candidate_layers": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                    "whse_forest_vegetation_rec_visual_landscape",
                ],
                "candidate_fields": [
                    "LEGAL_FEAT_OBJECTIVE",
                    "LEGAL_FEAT_ATRB_2_VALUE",
                    "REC_EVQO_CODE",
                ],
                "candidate_values": [
                    "Scenic Areas / Scenic Corridors",
                    "PR",
                    "Class A lake subset still required",
                ],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "The currently adopted public layers do not yet expose a trusted Class A lake discriminator for TSA29.",
                    "Do not use the whole scenic-PR legal surface as a surrogate; it overcuts badly.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Class B-E lakes are not excluded here; they are handled later "
                    "through Section 7.2.6 disturbance assumptions."
                ),
                "rationale": (
                    "The TSR explicitly defers management of Class B to E lakes to "
                    "Section 7.2.6 rather than excluding them in this step."
                ),
                "candidate_layers": [],
                "candidate_fields": [],
                "candidate_values": ["Section 7.2.6 later assumptions"],
                "candidate_operation_type": "reference_only",
                "field_mapping_notes": [
                    "This step is tiny in the TSR benchmark and is being skipped for detailed TSA29 validation."
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if (
        subsection_title.casefold().strip()
        == "community areas of special concern (casc)"
    ):
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Exclude the legal LUO / CCLUP Map 5 community areas of special "
                    "concern polygons from the harvestable land base."
                ),
                "rationale": (
                    "TSA29 section 6.3.7 says CASC areas are no-harvest polygons "
                    "designated in the LUO to address CCLUP objectives."
                ),
                "candidate_layers": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                ],
                "candidate_fields": [
                    "STRGC_LAND_RSRCE_PLAN_NAME",
                    "LEGAL_FEAT_OBJECTIVE",
                ],
                "candidate_values": [
                    "Cariboo Chilcotin Land Use Plan",
                    "Community Areas of Special Concern",
                ],
                "candidate_operation_type": "exclude",
                "field_mapping_notes": [
                    "Use the legal planning polygons for the CCLUP / LUO Map 5 boundaries.",
                    "Do not substitute broad designated-area overlays or unrelated disturbance layers.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    if subsection_title.casefold().strip() == "proven aboriginal rights area":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Exclude the Proven Aboriginal Rights area from the THLB to "
                    "reflect the current lack of commercial forestry activity and "
                    "the unique consultation / authorization regime."
                ),
                "rationale": (
                    "TSA29 section 6.4.1 says the PRA will be excluded from the THLB "
                    "because deep consultation is required and very few provincial "
                    "authorizations have been made there since 2014."
                ),
                "candidate_layers": [
                    "whse_admin_boundaries_pip_consultation",
                ],
                "candidate_fields": [
                    "boundary source still required",
                ],
                "candidate_values": [
                    "Proven Aboriginal Rights area boundary",
                ],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "The PRA is not the same thing as the proven Aboriginal title area and extends beyond the court case area.",
                    "Do not substitute the title area, caretaker area, TSA boundary, or broad ownership layers for the PRA boundary.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Keep the logic manual until a reviewed PRA boundary source is "
                    "adopted into the instance."
                ),
                "rationale": (
                    "The 2024 data package explains why the PRA is excluded but does "
                    "not cite a clean downloadable vector source for the boundary."
                ),
                "candidate_layers": [
                    "whse_admin_boundaries_pip_consultation",
                ],
                "candidate_fields": [],
                "candidate_values": [
                    "reviewed PRA boundary override required",
                ],
                "candidate_operation_type": "manual_review_required",
                "field_mapping_notes": [
                    "Older-cycle TSR material clarifies the distinction between title, caretaker-area, and PRA concepts, but still does not provide a stable public PRA vector source for automation.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
    subsection_source_hints = _extract_data_source_comment_tokens(subsection_body)
    candidate_operation_type = {
        "drop_from_universe": "exclude",
        "legal_harvest_exclusion": "exclude",
        "projected_harvest_exclusion": "exclude",
        "no_deduction": "no_deduction",
        "aspatial_fallback_candidate": "aspatial_reduction",
        "reference_only": "reference_only",
        "context_only": "context_only",
    }.get(execution_class, "review")
    subrules: list[dict[str, Any]] = []
    for index, sentence in enumerate(
        _split_subsection_into_draft_subrules(subsection_body),
        start=1,
    ):
        if _is_rationale_only_draft_sentence(sentence):
            continue
        candidate_operation = _infer_draft_subrule_operation_type(
            sentence,
            default_operation_type=candidate_operation_type,
        )
        semantic_layers = _infer_semantic_candidate_layers(
            sentence,
            subsection_source_hints=subsection_source_hints,
        )
        if semantic_layers:
            candidate_layers = semantic_layers
        else:
            candidate_layers = _link_thlb_step_to_sources(
                f"{subsection_title} {sentence}",
                source_index=source_index,
                explicit_query_tokens=subsection_source_hints,
            )
        candidate_fields, candidate_values, mapping_notes = (
            _infer_candidate_fields_and_values(sentence)
        )
        field_mapping_notes = list(mapping_notes)
        subrules.append(
            {
                "subrule_id": f"{parent_step_id}_draft_{index:02d}",
                "human_summary": sentence[:180],
                "rationale": sentence,
                "candidate_layers": list(candidate_layers),
                "candidate_fields": list(candidate_fields),
                "candidate_values": list(candidate_values),
                "candidate_operation_type": candidate_operation,
                "field_mapping_notes": field_mapping_notes,
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": str(linked_subsection.get("provenance_id", "")),
                "hint_provenance_ids": [],
            }
        )
    return tuple(subrules)


def _specialized_compiled_logic_for_parent_step(
    *,
    parent_step_id: str,
    parent_label: str,
    land_base_stage: str,
    stage_label: str,
    execution_class: str,
    benchmark_marginal_area_ha: float | None,
    benchmark_cumulative_area_ha: float | None,
    table_provenance: str,
    row_order: int,
    linked_subsection: dict[str, Any] | None,
) -> tuple[dict[str, Any], ...] | None:
    lower = parent_label.casefold().strip()
    provenance_id = (
        str(linked_subsection.get("provenance_id", ""))
        if linked_subsection
        else table_provenance
    )
    page_number = (
        int(linked_subsection.get("page_number", 0)) if linked_subsection else None
    )

    def _base_item(step_suffix: str, label: str, operation_type: str) -> dict[str, Any]:
        return {
            "step_id": f"{parent_step_id}_{step_suffix}",
            "parent_step_id": parent_step_id,
            "parent_label": parent_label,
            "order_index": row_order,
            "step_kind": "netdown_rule",
            "label": label,
            "raw_value": label,
            "raw_text": str(linked_subsection.get("body", "")).strip()
            if linked_subsection
            else parent_label,
            "land_base_stage": land_base_stage,
            "stage_label": stage_label,
            "execution_class": execution_class,
            "compiled_operation_type": operation_type,
            "step_status": "ready",
            "required": True,
            "page_number": page_number,
            "document_title": "",
            "document_type": "data_package",
            "cycle_label": "",
            "cycle_year": 0,
            "provenance_id": provenance_id,
            "source_url": "",
            "notes": [],
            "row_source_kind": "table_summary_row",
            "benchmark_marginal_area_ha": benchmark_marginal_area_ha,
            "benchmark_cumulative_area_ha": benchmark_cumulative_area_ha,
            "table_provenance": table_provenance,
        }

    if lower == "land not administered by the province":
        excluded_descriptions = [
            "Private",
            "Private - Parcel has a title registered to a First Nations group.",
            "Federal - Dominion government Block/Federal Parcels",
            "Federal - Indian Reserve",
            "Federal - Military Reserve",
            "Crown Tenure - Community Forest Agreement, Schedule A",
            "Crown Tenure - Community Forest Agreement, Schedule B",
            "Crown Tenure - First Nations Woodland Licence",
            "Crown Tenure - Tree Farm Licence, Schedule A",
            "Crown Tenure - Tree Farm Licence, Schedule B",
            "Crown - Municipal Parcels",
            "Crown Lease - Misc. lease",
        ]
        ownership_item = _base_item(
            "compiled_01",
            "Ownership classes not administered for TSA timber supply",
            "select_spatial_intersect",
        )
        ownership_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Ownership classes not administered for TSA timber supply",
                "normalized_predicate": (
                    "exclude private, federal, Indian reserve, area-based tenure, "
                    "municipal, and lease polygons from the working land base"
                ),
                "linked_source_entry_ids": ["whse_forest_vegetation_f_own"],
                "source_attribute_filters": [
                    {
                        "field": "OWNERSHIP_DESCRIPTION",
                        "operator": "in",
                        "value": excluded_descriptions,
                    },
                ],
                "execution_notes": [
                    "Notebook execution now uses F_OWN ownership descriptions for the first-pass 6.2.1 exclusion buckets instead of the older OWN != {62,69} shortcut.",
                    "Woodlots and parks/protected areas stay in AFLB here and are handled later or retained, consistent with the TSA29 prose.",
                ],
            }
        )
        treaty_item = _base_item(
            "compiled_02",
            "Treaty and title transfers requiring reviewed overlays",
            "manual_review_required",
        )
        treaty_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Treaty and title transfers requiring reviewed overlays",
                "normalized_predicate": (
                    "review NStQ interim treaty parcels and Tsilhqot'in title lands "
                    "with dedicated reviewed overlays before lock"
                ),
                "linked_source_entry_ids": ["whse_forest_vegetation_f_own"],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "The TSA29 prose cites dedicated NStQ and Tsilhqot'in title exclusions that are not yet separated cleanly from the generic F_OWN ownership classes in the notebook bridge."
                ],
            }
        )
        return (ownership_item, treaty_item)

    if lower == "non-forest":
        attribute_item = _base_item("compiled_01", parent_label, "select_attribute")
        attribute_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": parent_label,
                "normalized_predicate": "exclude non-forest and non-productive VRI polygons from the working land base",
                "linked_source_entry_ids": [],
                "checkpoint_attribute_mode": "any",
                "checkpoint_attribute_filters": [
                    {"field": "BCLCS_LEVEL_2", "operator": "ne", "value": "T"},
                    {"field": "FOR_MGMT_LAND_BASE_IND", "operator": "ne", "value": "Y"},
                    {
                        "field": "NON_PRODUCTIVE_CD",
                        "operator": "not_blank",
                        "value": None,
                    },
                    {"field": "CROWN_CLOSURE", "operator": "lt", "value": 10},
                ],
                "execution_notes": [
                    "Current notebook execution uses checkpoint attributes as the first-pass FMLB proxy.",
                    "Harvest-history, MPB, and fire exceptions remain review-sensitive and are not yet auto-restored here.",
                ],
            }
        )
        fwa_item = _base_item(
            "compiled_02",
            "Freshwater Atlas final water check",
            "select_spatial_intersect",
        )
        fwa_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Freshwater Atlas final water check",
                "normalized_predicate": "exclude mapped lakes, rivers, and wetlands from the working land base",
                "linked_source_entry_ids": [
                    "whse_basemapping_fwa_lakes_poly",
                    "whse_basemapping_fwa_rivers_poly",
                    "whse_basemapping_fwa_wetlands_poly",
                ],
                "step_status": "ready",
                "required": True,
                "notes": [
                    "Riparian reserve and riparian management zone buffers are handled in the later riparian parent step, not here.",
                    "This subrule only performs the direct Freshwater Atlas lakes/rivers/wetlands exclusion described in the non-forest step.",
                ],
            }
        )
        return (attribute_item, fwa_item)

    if lower == "roads and landings":
        road_atlas = _base_item(
            "compiled_01", "Existing public and resource roads", "buffer_then_intersect"
        )
        road_atlas.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Existing public and resource roads",
                "normalized_predicate": "buffer road-atlas lines by maintained clearing width and exclude the overlap",
                "linked_source_entry_ids": [
                    "whse_basemapping_dra_dgtl_road_atlas_mpar_sp"
                ],
                "buffer_distance_m": 12.5,
                "execution_notes": [
                    "Notebook execution applies the 12.5 m half-width from the TSR prose for public and forest service road centerlines."
                ],
            }
        )
        road_section = _base_item(
            "compiled_02",
            "Active or retired road permit roads",
            "buffer_then_intersect",
        )
        road_section.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Active or retired road permit roads",
                "normalized_predicate": "buffer road-permit lines by maintained clearing width and exclude the overlap",
                "linked_source_entry_ids": [
                    "whse_forest_tenure_ften_road_section_lines_svw"
                ],
                "buffer_distance_m": 7.5,
                "execution_notes": [
                    "Notebook execution applies the 7.5 m half-width from the TSR prose for active/retired road permit centerlines."
                ],
            }
        )
        landing_item = _base_item(
            "compiled_03", "Landings and temporary roads", "manual_review_required"
        )
        landing_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Landings and temporary roads",
                "normalized_predicate": "requires non-spatial or additional harvested-area treatment logic",
                "linked_source_entry_ids": [
                    "whse_forest_vegetation_veg_consolidated_cut_blocks_sp"
                ],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "Temporary roads and landings remain a review item in the notebook bridge until the non-spatial deduction path is formalized."
                ],
            }
        )
        return (road_atlas, road_section, landing_item)

    if lower == "parks, protected areas, area-base tenures":
        parks_item = _base_item(
            "compiled_01", "Parks and protected areas", "select_spatial_intersect"
        )
        parks_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Parks and protected areas",
                "normalized_predicate": "exclude legally protected polygons from the working harvestable land base",
                "linked_source_entry_ids": ["whse_tantalis_ta_park_ecores_pa_svw"],
            }
        )
        excluded_tenure_descriptions = [
            "Crown Lease - Misc. lease",
            "Crown Tenure - Woodlot Licence, Schedule A",
            "Crown Tenure - Woodlot Licence, Schedule B",
        ]
        tenure_item = _base_item(
            "compiled_02",
            "Area-based tenures and woodlots",
            "select_spatial_intersect",
        )
        tenure_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Area-based tenures and woodlots",
                "normalized_predicate": (
                    "exclude mapped area-based tenure and woodlot polygons from the "
                    "working harvestable land base"
                ),
                "linked_source_entry_ids": ["whse_forest_vegetation_f_own"],
                "source_attribute_filters": [
                    {
                        "field": "OWNERSHIP_DESCRIPTION",
                        "operator": "in",
                        "value": excluded_tenure_descriptions,
                    }
                ],
                "step_status": "ready",
                "required": True,
                "notes": [
                    "TSA29 section 6.2.1 keeps woodlots in AFLB but removes them when defining the LHLB, so woodlot schedules A/B are included here.",
                    "This first runnable pass uses the explicit F_OWN ownership descriptions for woodlots and the small miscellaneous crown-lease class cited in TSA29 Table 7.",
                    "Community forest agreements and first nations woodland licences were already netted out upstream in TSA29 step 2 and are therefore intentionally excluded from this step-6 executable filter.",
                    "FTEN managed-licence and TANTALIS crown-tenure layers remain supporting metadata/reference surfaces, but F_OWN is the executable ownership overlay in the TSA29 bridge.",
                ],
            }
        )
        return (parks_item, tenure_item)

    if lower == "old growth management areas":
        ogma_item = _base_item(
            "compiled_01",
            "Old growth management areas",
            "select_spatial_intersect",
        )
        ogma_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Old growth management areas",
                "normalized_predicate": (
                    "exclude only permanent and rotating legal OGMA polygons "
                    "from the working harvestable land base"
                ),
                "linked_source_entry_ids": ["rmp_ogma_legal"],
                "source_attribute_filters": [
                    {
                        "field": "OGMA_TYPE",
                        "operator": "in",
                        "value": ["PERM", "ROT"],
                    }
                ],
                "notes": [
                    "Current notebook execution treats only permanent and rotating legal OGMAs as the direct no-harvest exclusion surface.",
                    "Transition OGMAs remain contextual/temporal logic and are not hard-excluded in this base-case executable mask.",
                    "Harvest exceptions, overlap replacement, and transition restoration timing remain later review/calibration work.",
                ],
            }
        )
        return (ogma_item,)

    if lower == "wildlife habitat areas":
        no_harvest_uwr = _base_item(
            "compiled_01",
            "Ungulate winter range no-harvest polygons",
            "select_spatial_intersect",
        )
        no_harvest_uwr.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Ungulate winter range no-harvest polygons",
                "normalized_predicate": (
                    "exclude only wildlife polygons where TIMBER_HARVEST_CODE = NO HARVEST ZONE"
                ),
                "linked_source_entry_ids": [
                    "whse_wildlife_management_wcp_ungulate",
                    "wcp_ungulate_winter_range",
                ],
                "source_attribute_filters": [
                    {
                        "field": "TIMBER_HARVEST_CODE",
                        "operator": "eq",
                        "value": "NO HARVEST ZONE",
                    }
                ],
                "notes": [
                    "TSA29 section 6.3.3 states that only no-harvest wildlife areas are excluded at this stage.",
                    "Conditional harvest zones are deferred to later forest-management assumptions and silviculture logic.",
                ],
            }
        )
        no_harvest_wha = _base_item(
            "compiled_02",
            "Wildlife habitat area no-harvest polygons",
            "select_spatial_intersect",
        )
        no_harvest_wha.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Wildlife habitat area no-harvest polygons",
                "normalized_predicate": (
                    "exclude only wildlife polygons where TIMBER_HARVEST_CODE = NO HARVEST ZONE"
                ),
                "linked_source_entry_ids": ["whse_wildlife_management_wcp_wildlife"],
                "source_attribute_filters": [
                    {
                        "field": "TIMBER_HARVEST_CODE",
                        "operator": "eq",
                        "value": "NO HARVEST ZONE",
                    }
                ],
                "notes": [
                    "General Wildlife Measures with no-harvest direction are excluded here; modified/conditional zones are not."
                ],
            }
        )
        conditional_zone = _base_item(
            "compiled_03",
            "Conditional harvest wildlife zones",
            "manual_review_required",
        )
        conditional_zone.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Conditional harvest wildlife zones",
                "normalized_predicate": (
                    "defer conditional harvest zone treatment to later silviculture and assumptions logic"
                ),
                "linked_source_entry_ids": [
                    "whse_wildlife_management_wcp_ungulate",
                    "whse_wildlife_management_wcp_wildlife",
                    "wcp_ungulate_winter_range",
                ],
                "source_attribute_filters": [
                    {
                        "field": "TIMBER_HARVEST_CODE",
                        "operator": "eq",
                        "value": "CONDITIONAL HARVEST ZONE",
                    }
                ],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "Section 6.3.3 / later Section 7 wording defers conditional harvest zones instead of excluding them at this stage."
                ],
            }
        )
        return (no_harvest_uwr, no_harvest_wha, conditional_zone)

    if lower == "community areas of special concern":
        casc_item = _base_item(
            "compiled_01",
            "Community areas of special concern",
            "select_spatial_intersect",
        )
        casc_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Community areas of special concern",
                "normalized_predicate": (
                    "exclude only LUO/CARC CCLUP legal-planning polygons where "
                    "LEGAL_FEAT_OBJECTIVE = Community Areas of Special Concern"
                ),
                "linked_source_entry_ids": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                ],
                "source_attribute_filters": [
                    {
                        "field": "STRGC_LAND_RSRCE_PLAN_NAME",
                        "operator": "eq",
                        "value": "Cariboo Chilcotin Land Use Plan",
                    },
                    {
                        "field": "LEGAL_FEAT_OBJECTIVE",
                        "operator": "eq",
                        "value": "Community Areas of Special Concern",
                    },
                ],
                "notes": [
                    "TSA29 section 6.3.7 points to LUO / CCLUP Map 5 boundaries, so notebook execution uses the legal CCLUP planning polygons instead of broad designated-area overlays."
                ],
            }
        )
        return (casc_item,)

    if lower == "critical habitat for fish":
        fish_item = _base_item(
            "compiled_01",
            "Critical fish habitat",
            "select_spatial_intersect",
        )
        fish_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Critical fish habitat",
                "normalized_predicate": (
                    "exclude only the CCLUP legal-planning polygons for critical "
                    "fish habitat from the working harvestable land base"
                ),
                "linked_source_entry_ids": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw"
                ],
                "source_attribute_filters": [
                    {
                        "field": "STRGC_LAND_RSRCE_PLAN_NAME",
                        "operator": "eq",
                        "value": "Cariboo Chilcotin Land Use Plan",
                    },
                    {
                        "field": "LEGAL_FEAT_OBJECTIVE",
                        "operator": "eq",
                        "value": "Critical Habitat for Fish",
                    },
                    {
                        "field": "LEGAL_FEAT_ATRB_1_VALUE",
                        "operator": "eq",
                        "value": "CRITFISH",
                    },
                ],
                "notes": [
                    "TSA29 section 6.3.4 cites the Section 93.4 LAO establishing objectives for the CCLUP, Map 4, as the critical-fish-habitat source.",
                    "Notebook execution therefore uses the legal-planning fish objective polygons instead of wildlife-habitat proxy layers.",
                    "If the full-TSA result still runs materially high, the next refinement seam is inside the legal fish objective attributes themselves, not a return to wildlife proxy sources.",
                ],
            }
        )
        return (fish_item,)

    if lower == "lakeshore management":
        lakeshore_item = _base_item(
            "compiled_01",
            "Class A lakes with preservation VQO overlap",
            "manual_review_required",
        )
        lakeshore_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Class A lakes with preservation VQO overlap",
                "normalized_predicate": (
                    "exclude only the Class A lake legal buffer areas that overlap "
                    "VQO preservation once a trusted Class A lake source is adopted"
                ),
                "linked_source_entry_ids": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                    "whse_forest_vegetation_rec_visual_landscape",
                ],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "TSA29 section 6.3.5 is a very small benchmark step and only applies to Class A lakes overlapping preservation VQO.",
                    "The currently adopted public layers do not yet expose a trusted Class A lake discriminator for TSA29.",
                    "Do not substitute the whole scenic-PR legal surface; it materially overcuts.",
                    "Class B-E lakes are deferred to Section 7.2.6 assumptions logic, not excluded here.",
                ],
            }
        )
        return (lakeshore_item,)

    if lower == "areas considered inoperable":
        terrain_item = _base_item(
            "compiled_01",
            "Unstable terrain and terrain class 5",
            "select_spatial_intersect",
        )
        terrain_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Unstable terrain and terrain class 5",
                "normalized_predicate": (
                    "set THLB to 0 where terrain-stability mapping identifies unstable "
                    "terrain or terrain class 5 polygons"
                ),
                "linked_source_entry_ids": [
                    "reg_land_and_natural_resource_terrain_stability"
                ],
                "source_attribute_filters": [
                    {
                        "field": "SLOPE_STABILITY_CLASS_W_ROADS",
                        "operator": "in",
                        "value": ["U", "V"],
                    },
                ],
                "notes": [
                    "The terrain-stability branch remains the current public-data executable proxy for the TSR's Unstable (U) / Terrain Class 5 clause.",
                    "The v1 terrain filter uses terrain-stability classes U (Unstable) and V (Terrain Class 5 proxy) as the current executable subset.",
                ],
            }
        )
        steep_item = _base_item(
            "compiled_02",
            "Steep slope thresholds east and west of Highway 97",
            "select_attribute",
        )
        steep_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Steep slope thresholds east and west of Highway 97",
                "normalized_predicate": (
                    "set THLB to 0 where checkpoint-derived stand attributes identify "
                    "slope > 70% east of Highway 97 or slope > 40% west of Highway 97"
                ),
                "checkpoint_attribute_mode": "any",
                "checkpoint_attribute_filters": [
                    {
                        "field": "femic_step13_steep_slope_flag",
                        "operator": "eq",
                        "value": True,
                    }
                ],
                "linked_source_entry_ids": [
                    "reg_land_and_natural_resource_terrain_stability",
                    "whse_imagery_and_base_maps_mot_highway_profiles_sp",
                ],
                "notes": [
                    "TSA29 section 6.4.3 splits steep-slope exclusions east and west of Highway 97.",
                    "Checkpoint execution expects `femic_slope_pct_median`, `femic_hwy97_side`, and `femic_step13_steep_slope_flag` to be precompiled onto the curve-ready checkpoint.",
                ],
            }
        )
        return (terrain_item, steep_item)

    if lower == "sites with low growing timber potential":
        non_steep_item = _base_item(
            "compiled_01",
            f"Non-steep {_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA:g} m3/ha threshold",
            "curve_volume_threshold_exclusion",
        )
        non_steep_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": (
                    f"Non-steep {_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA:g} m3/ha threshold"
                ),
                "normalized_predicate": (
                    "set THLB to 0 on non-steep stands where assigned curve volume "
                    f"at age 160 falls below the calibrated "
                    f"{_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA:g} m3/ha bridge threshold"
                ),
                "linked_source_entry_ids": [],
                "curve_id_column": "curve1",
                "minimum_volume_m3_per_ha": (
                    _STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA
                ),
                "curve_volume_metric": _CURVE_VOLUME_METRIC_AGE,
                "curve_volume_age_years": 160.0,
                "checkpoint_attribute_mode": "any",
                "checkpoint_attribute_filters": [
                    {
                        "field": "femic_step13_steep_slope_flag",
                        "operator": "eq",
                        "value": False,
                    }
                ],
                "notes": [
                    "Step 14 runs late in the pipeline on the curve-ready checkpoint rather than on checkpoint1.",
                    "Notebook execution uses the current assigned bundle curves and evaluates volume at age 160, matching the TSR wording for low-productivity stands.",
                    f"This branch reuses the accepted step-13 steep-slope flag and applies the calibrated non-steep {_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA:g} m3/ha bridge threshold only where `femic_step13_steep_slope_flag == False`.",
                    "The threshold is calibrated to approximate the TSR step-14 benchmark with the current public-input curve family rather than claiming exact parity with the Chief Forester's yield tables.",
                ],
            }
        )
        steep_item = _base_item(
            "compiled_02",
            "Steep-slope 250 m3/ha threshold",
            "curve_volume_threshold_exclusion",
        )
        steep_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Steep-slope 250 m3/ha threshold",
                "normalized_predicate": (
                    "set THLB to 0 on steep stands where assigned curve volume at "
                    "age 160 falls below 250 m3/ha"
                ),
                "linked_source_entry_ids": [],
                "curve_id_column": "curve1",
                "minimum_volume_m3_per_ha": 250.0,
                "curve_volume_metric": _CURVE_VOLUME_METRIC_AGE,
                "curve_volume_age_years": 160.0,
                "checkpoint_attribute_mode": "any",
                "checkpoint_attribute_filters": [
                    {
                        "field": "femic_step13_steep_slope_flag",
                        "operator": "eq",
                        "value": True,
                    }
                ],
                "notes": [
                    "TSA29 section 6.4.4 raises the threshold to 250 m3/ha on steep slopes.",
                    "Notebook execution uses the current assigned bundle curves and evaluates volume at age 160, matching the TSR wording for low-productivity stands.",
                    "This branch reuses the accepted step-13 steep-slope flag and applies the 250 m3/ha threshold only where `femic_step13_steep_slope_flag == True`.",
                    f"Together with the calibrated non-steep {_STEP14_CALIBRATED_NON_STEEP_THRESHOLD_M3_PER_HA:g} m3/ha branch, this keeps the step-14 partition mutually exclusive and avoids applying the lower threshold to steep stands.",
                ],
            }
        )
        return (non_steep_item, steep_item)

    if lower == "non-merchantable timber profiles":
        broadleaf_item = _base_item(
            "compiled_01",
            "Broadleaf-leading stands",
            "select_attribute",
        )
        broadleaf_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Broadleaf-leading stands",
                "normalized_predicate": (
                    "set THLB to 0 where the leading species code is broadleaf; "
                    "defer broadleaf components in conifer-leading stands to the later broadleaf volume-exclusion assumption"
                ),
                "linked_source_entry_ids": [],
                "checkpoint_attribute_mode": "any",
                "checkpoint_attribute_filters": [
                    {
                        "field": "SPECIES_CD_1",
                        "operator": "in",
                        "value": sorted(BROADLEAF_SPECIES_CODES),
                    }
                ],
                "notes": [
                    "TSA29 section 6.4.5 excludes broadleaf-leading stands from THLB.",
                    "Notebook execution uses the leading VRI species code on the late-stage curve-ready checkpoint surface.",
                    "The deciduous component of conifer-leading stands is explicitly deferred to the later broadleaf volume-exclusion assumption.",
                ],
            }
        )
        return (broadleaf_item,)

    if lower == "recreation features":
        recreation_item = _base_item(
            "compiled_01",
            "Active recreation polygons",
            "select_spatial_intersect",
        )
        recreation_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Active recreation polygons",
                "normalized_predicate": (
                    "set THLB to 0 where active legally established recreation "
                    "site and reserve polygons intersect the working land base"
                ),
                "linked_source_entry_ids": ["whse_forest_tenure_ften_recreation"],
                "source_attribute_filters": [
                    {
                        "field": "LIFE_CYCLE_STATUS_CODE",
                        "operator": "eq",
                        "value": "ACTIVE",
                    }
                ],
                "notes": [
                    "TSA29 section 6.4.6 excludes identified recreation areas and features from THLB.",
                    "Notebook execution currently auto-runs the active FTEN recreation polygon subset only.",
                    "Recreation trails and FSP consultation/procedure language remain out of scope for this first runnable bridge pass.",
                ],
            }
        )
        return (recreation_item,)

    if lower == "riparian areas":
        items: list[dict[str, Any]] = []
        for stream_class, width_m in _RIPARIAN_STREAM_WIDTHS_M.items():
            item = _base_item(
                f"compiled_stream_s{stream_class}",
                f"Stream class S{stream_class} effective riparian buffer",
                "buffer_then_intersect",
            )
            item.update(
                {
                    "normalized_action": "exclude",
                    "normalized_subject": f"Stream class S{stream_class} riparian area",
                    "normalized_predicate": (
                        "set THLB to 0 on stream-buffer fragments using the Table 15 "
                        f"effective riparian width for S{stream_class} streams"
                    ),
                    "linked_source_entry_ids": [
                        "reg_land_and_natural_resource_stream_classification_car_line"
                    ],
                    "source_attribute_filters": [
                        {
                            "field": "STREAM_CLASS",
                            "operator": "eq",
                            "value": stream_class,
                        }
                    ],
                    "buffer_distance_m": width_m,
                    "notes": [
                        "Step 3 already removed the direct non-forest waterbody area; "
                        "this later THLB step models the additional riparian buffer.",
                        "The Table 15 riparian width already folds RRZ plus retained RMZ "
                        "share into an equivalent full-exclusion width.",
                    ],
                }
            )
            items.append(item)
        for swamp_class, width_m in _RIPARIAN_WETLAND_WIDTHS_M.items():
            item = _base_item(
                f"compiled_wetland_{swamp_class}",
                f"Wetland class {swamp_class.upper()} effective riparian buffer",
                "buffer_then_intersect",
            )
            item.update(
                {
                    "normalized_action": "exclude",
                    "normalized_subject": (
                        f"Wetland class {swamp_class.upper()} riparian area"
                    ),
                    "normalized_predicate": (
                        "set THLB to 0 on wetland-buffer fragments using the Table 15 "
                        f"effective riparian width for {swamp_class.upper()} wetlands"
                    ),
                    "linked_source_entry_ids": [
                        "reg_land_and_natural_resource_wetland_class_car_poly"
                    ],
                    "source_attribute_filters": [
                        {
                            "field": "SWAMP_CLASS",
                            "operator": "eq",
                            "value": swamp_class,
                        }
                    ],
                    "buffer_distance_m": width_m,
                    "notes": [
                        "Step 3 already removed the direct wetland polygon area; this "
                        "later THLB step models the additional riparian buffer.",
                        "The Table 15 riparian width already folds RRZ plus retained RMZ "
                        "share into an equivalent full-exclusion width.",
                    ],
                }
            )
            items.append(item)
        lake_item = _base_item(
            "compiled_lakes_review",
            "Lake riparian classes",
            "manual_review_required",
        )
        lake_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Lake riparian classes",
                "normalized_predicate": (
                    "requires a reviewed Cariboo lake-class surface before automated "
                    "L1/L2/L3/L4 riparian buffering can run"
                ),
                "linked_source_entry_ids": ["whse_basemapping_fwa_lakes_poly"],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "Table 15 includes lake classes L1-B, L2, and L3/L4, but the "
                    "current TSA29 instance does not yet have a trustworthy lake-class "
                    "artifact wired into the notebook bridge."
                ],
            }
        )
        s4_special_item = _base_item(
            "compiled_s4_special_review",
            "Niut and South Chilcotin S4 special width",
            "manual_review_required",
        )
        s4_special_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Niut and South Chilcotin S4 special width",
                "normalized_predicate": (
                    "requires a reviewed LU/SRDZ overlay to increase S4 riparian width "
                    "to 30 metres in the Niut and South Chilcotin areas"
                ),
                "linked_source_entry_ids": [
                    "reg_land_and_natural_resource_stream_classification_car_line",
                    "rmp_landscape_unit_svw",
                    "whse_land_use_planning_rmp_plan_legal_poly_svw",
                ],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "TSA29 section 6.4.2 increases the S4 riparian area width in the "
                    "Niut SRDZ and South Chilcotin SRDZ to protect dolly varden trout "
                    "habitat. This first runnable pass leaves that special-case refinement "
                    "as reviewed/manual logic."
                ],
            }
        )
        items.extend((lake_item, s4_special_item))
        return tuple(items)

    if lower == "buffered trails":
        trail_item = _base_item(
            "compiled_01",
            "Buffered trail areas",
            "buffer_then_intersect",
        )
        trail_item.update(
            {
                "normalized_action": "exclude",
                "normalized_subject": "Buffered trail areas",
                "normalized_predicate": (
                    "shrink the legal 100-metre buffered-trail polygons by 7.5 metres "
                    "and set THLB to 0 on the resulting 85-metre equivalent corridor"
                ),
                "linked_source_entry_ids": [
                    "whse_land_use_planning_rmp_plan_legal_poly_svw"
                ],
                "source_attribute_filters": [
                    {
                        "field": "LEGAL_FEAT_OBJECTIVE",
                        "operator": "eq",
                        "value": "Buffered Trail Areas",
                    }
                ],
                "buffer_distance_m": -7.5,
                "notes": [
                    "TSA29 section 6.3.6 says at least 85% of the area within the 100-metre trail corridor will not be available for harvest.",
                    "Notebook execution models that rule by shrinking the legal 100-metre buffered-trail polygons inward by 7.5 metres on each side, yielding an 85-metre equivalent full-exclusion corridor.",
                ],
            }
        )
        return (trail_item,)

    if lower == "wildlife tree retention areas":
        wtra_item = _base_item(
            "compiled_01",
            "Future wildlife tree retention area reduction",
            "aspatial_reduction",
        )
        wtra_item.update(
            {
                "normalized_action": "aspatial_reduction",
                "normalized_subject": "Future wildlife tree retention area reduction",
                "normalized_predicate": (
                    "apply the TSR-cited future WTRA exclusion as an aspatial THLB reduction "
                    "factor after the spatially executable steps"
                ),
                "linked_source_entry_ids": [],
                "notes": [
                    "TSA29 section 6.4.8 says existing mapped WTRA remain in THLB and are deferred from harvest for 80 years.",
                    "Notebook execution models only the future WTRA requirement here as an aspatial THLB reduction factor.",
                    "The deduction magnitude is anchored to the TSR benchmark area and scaled to the current smoke subset.",
                ],
            }
        )
        return (wtra_item,)

    if lower == "future roads":
        future_roads_item = _base_item(
            "compiled_01",
            "Future roads, trails, and landings area reduction",
            "aspatial_area_reduction",
        )
        future_roads_item.update(
            {
                "benchmark_marginal_area_ha": (
                    benchmark_marginal_area_ha
                    if benchmark_marginal_area_ha is not None
                    else 22754.0
                ),
                "normalized_action": "aspatial_area_reduction",
                "normalized_subject": "Future roads, trails, and landings area reduction",
                "normalized_predicate": (
                    "apply the TSR-cited future RTL deduction as an aspatial stand-area "
                    "reduction across the AFLB working land base"
                ),
                "linked_source_entry_ids": [],
                "notes": [
                    "TSA29 section 6.2.3 says future roads are estimated from current performance and RESULTS data rather than a mapped future-road layer.",
                    "Notebook execution treats this as an early-stage AFLB area reduction and scales stand-area fields directly.",
                    "Do not reuse the existing present-day roads spatial overlay for this parent step.",
                    "Do not use THLB retention for this step because the deducted area is non-forested road footprint.",
                ],
            }
        )
        return (future_roads_item,)

    if lower == "cultural heritage and archaeological resources":
        heritage_item = _base_item(
            "compiled_01",
            "Cultural heritage and archaeological resources reduction",
            "aspatial_reduction",
        )
        heritage_item.update(
            {
                "normalized_action": "aspatial_reduction",
                "normalized_subject": "Cultural heritage and archaeological resources reduction",
                "normalized_predicate": (
                    "apply the TSR-cited cultural-heritage THLB reduction as an "
                    "aspatial factor anchored to current licensee and Tsilhqot'in practice"
                ),
                "linked_source_entry_ids": [],
                "notes": [
                    "TSA29 section 6.4.9 models this as an aspatial THLB reduction rather than a single public spatial layer.",
                    "The deduction is anchored to the TSR benchmark area and informed by TNG plus FSP practice (Tolko #780, West Fraser #755, BCTS #828).",
                    "Do not infer road or other generic spatial layers from the permit/FSP discussion in this subsection.",
                ],
            }
        )
        return (heritage_item,)

    if lower == "proven aboriginal rights areas":
        pra_item = _base_item(
            "compiled_01",
            "Proven Aboriginal Rights area boundary",
            "manual_review_required",
        )
        pra_item.update(
            {
                "normalized_action": "review",
                "normalized_subject": "Proven Aboriginal Rights area boundary",
                "normalized_predicate": (
                    "requires a reviewed PRA boundary overlay before automation; "
                    "do not auto-exclude with broad TSA or designated-area polygons"
                ),
                "linked_source_entry_ids": [
                    "whse_admin_boundaries_pip_consultation",
                    "whse_land_use_planning_fadm_designated",
                ],
                "step_status": "manual_review_required",
                "required": False,
                "notes": [
                    "TSA29 section 6.4.1 defines the Proven Aboriginal Rights area conceptually but does not cite a clean public vector source in the data-package text.",
                    "Current public lead is the PIP Consultation Areas public map service; treat this step as review/manual until a trustworthy boundary source or override is adopted.",
                ],
            }
        )
        return (pra_item,)

    return None


def _build_compiled_logic_for_parent_step(
    *,
    parent_step_id: str,
    parent_label: str,
    land_base_stage: str,
    stage_label: str,
    execution_class: str,
    benchmark_marginal_area_ha: float | None,
    benchmark_cumulative_area_ha: float | None,
    table_provenance: str,
    row_order: int,
    linked_subsection: dict[str, Any] | None,
    source_index: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    specialized = _specialized_compiled_logic_for_parent_step(
        parent_step_id=parent_step_id,
        parent_label=parent_label,
        land_base_stage=land_base_stage,
        stage_label=stage_label,
        execution_class=execution_class,
        benchmark_marginal_area_ha=benchmark_marginal_area_ha,
        benchmark_cumulative_area_ha=benchmark_cumulative_area_ha,
        table_provenance=table_provenance,
        row_order=row_order,
        linked_subsection=linked_subsection,
    )
    if specialized is not None:
        return specialized

    raw_text = (
        _strip_trailing_table_and_comment_blocks(
            str(linked_subsection.get("body", ""))
        ).strip()
        if linked_subsection
        else parent_label
    )
    subsection_title = (
        str(linked_subsection.get("title", "")).strip()
        if linked_subsection
        else parent_label
    )
    subsection_source_hints = (
        _extract_data_source_comment_tokens(str(linked_subsection.get("body", "")))
        if linked_subsection
        else ()
    )
    action, subject, predicate = _match_thlb_action(raw_text)
    if execution_class == "reference_only":
        action = "reference_target"
        step_kind = "reference_target"
        step_status = "ready"
        required = True
    elif execution_class == "context_only":
        action = action or "section_heading"
        step_kind = "context"
        step_status = "needs_review"
        required = False
    else:
        if not action:
            if execution_class == "no_deduction":
                action = "no_deduction"
            elif execution_class == "aspatial_fallback_candidate":
                action = "aspatial_reduction"
            else:
                action = "exclude"
        step_kind = "netdown_rule"
        required = True
        step_status = "ready"
    linked_source_entry_ids = _link_thlb_step_to_sources(
        f"{parent_label} {subsection_title} {raw_text}",
        source_index=source_index,
        explicit_query_tokens=subsection_source_hints,
    )
    if (
        step_kind == "netdown_rule"
        and not linked_source_entry_ids
        and action
        not in {
            "use_land_base",
            "no_deduction",
            "aspatial_reduction",
            "aspatial_area_reduction",
            "restore",
        }
    ):
        step_status = "blocked_missing_source"
    notes: list[str] = []
    if step_status == "blocked_missing_source":
        notes.append(
            "No source-layer recipe entry linked automatically; review or add an override."
        )
    return (
        {
            "step_id": f"{parent_step_id}_compiled_01",
            "parent_step_id": parent_step_id,
            "parent_label": parent_label,
            "order_index": row_order,
            "step_kind": step_kind,
            "label": parent_label,
            "raw_value": subsection_title or parent_label,
            "raw_text": raw_text or parent_label,
            "land_base_stage": land_base_stage,
            "stage_label": stage_label,
            "execution_class": execution_class,
            "normalized_action": action,
            "normalized_subject": subject,
            "normalized_predicate": predicate,
            "linked_source_entry_ids": list(linked_source_entry_ids),
            "step_status": step_status,
            "required": required,
            "page_number": int(linked_subsection.get("page_number", 0))
            if linked_subsection
            else None,
            "document_title": "",
            "document_type": "data_package",
            "cycle_label": "",
            "cycle_year": 0,
            "provenance_id": (
                str(linked_subsection.get("provenance_id", ""))
                if linked_subsection
                else table_provenance
            ),
            "source_url": "",
            "notes": notes,
            "row_source_kind": "table_summary_row",
            "benchmark_marginal_area_ha": benchmark_marginal_area_ha,
            "benchmark_cumulative_area_ha": benchmark_cumulative_area_ha,
            "table_provenance": table_provenance,
        },
    )


def _best_matching_subsection(
    *,
    parent_label: str,
    subsections: Sequence[dict[str, Any]],
    preferred_stages: Sequence[str] | None,
) -> dict[str, Any] | None:
    normalized_parent = _normalize_whitespace(parent_label).casefold()
    parent_tokens = _meaningful_tokens(parent_label)
    if not normalized_parent or not parent_tokens:
        return None
    scored: list[tuple[int, int, int, int, dict[str, Any]]] = []
    for subsection in subsections:
        subsection_stage = str(subsection.get("land_base_stage", "context"))
        if preferred_stages and subsection_stage not in preferred_stages:
            continue
        title = str(subsection.get("title", ""))
        body = str(subsection.get("body", ""))
        normalized_title = _normalize_whitespace(title).casefold()
        title_tokens = _meaningful_tokens(title)
        body_tokens = _meaningful_tokens(body)
        overlap = parent_tokens & (title_tokens | body_tokens)
        if not overlap:
            continue
        title_overlap = len(parent_tokens & title_tokens)
        body_overlap = len(parent_tokens & body_tokens)
        exact_title = int(normalized_parent == normalized_title)
        parent_in_title = int(normalized_parent in normalized_title)
        title_in_parent = int(normalized_title in normalized_parent)
        score = (
            exact_title * 1000
            + (parent_in_title + title_in_parent) * 500
            + title_overlap * 50
            + body_overlap * 5
        )
        scored.append((score, title_overlap, body_overlap, len(title), subsection))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], -item[3]))
    return scored[0][4]


def _build_parent_steps_from_land_base_summary(
    *,
    summary_rows: Sequence[dict[str, Any]],
    subsections: Sequence[dict[str, Any]],
    source_index: tuple[dict[str, Any], ...],
) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    parent_steps: list[dict[str, Any]] = []
    compiled_steps: list[dict[str, Any]] = []
    glb_area_ha: float | None = None
    current_cumulative_area_ha: float | None = None
    seen_aflb_row = False
    seen_thlb_row = False
    for row_order, row in enumerate(summary_rows, start=1):
        label = str(row.get("parent_label", "")).strip()
        numeric_tokens = tuple(float(value) for value in row.get("numeric_tokens", ()))
        if not label or not numeric_tokens:
            continue
        lower = label.casefold()
        if lower == "total tsa area":
            glb_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = glb_area_ha
            linked_subsection = None
        else:
            if not seen_aflb_row:
                preferred_stages: tuple[str, ...] | None = ("glb_to_aflb",)
            elif seen_thlb_row:
                preferred_stages = ("reference_target",)
            else:
                preferred_stages = ("aflb_to_lhlb", "lhlb_to_thlb")
            linked_subsection = _best_matching_subsection(
                parent_label=label,
                subsections=subsections,
                preferred_stages=preferred_stages,
            )
            if linked_subsection is None:
                linked_subsection = _best_matching_subsection(
                    parent_label=label,
                    subsections=subsections,
                    preferred_stages=None,
                )
        land_base_stage, execution_class = _infer_parent_row_stage(
            label=label,
            linked_subsection=linked_subsection,
            seen_aflb_row=seen_aflb_row,
            seen_thlb_row=seen_thlb_row,
        )
        stage_label = _THLB_STAGE_LABELS[land_base_stage]
        benchmark_marginal_area_ha: float | None = None
        benchmark_cumulative_area_ha: float | None = None
        if lower == "analysis forest land base":
            benchmark_cumulative_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = benchmark_cumulative_area_ha
            seen_aflb_row = True
        elif lower == "timber harvesting land base":
            benchmark_cumulative_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = benchmark_cumulative_area_ha
            seen_thlb_row = True
        elif lower == "long-term thlb":
            benchmark_cumulative_area_ha = numeric_tokens[0]
        else:
            if len(numeric_tokens) >= 3:
                benchmark_marginal_area_ha = numeric_tokens[-3]
            elif len(numeric_tokens) >= 2:
                benchmark_marginal_area_ha = numeric_tokens[-2]
            if (
                current_cumulative_area_ha is not None
                and benchmark_marginal_area_ha is not None
            ):
                current_cumulative_area_ha = max(
                    0.0,
                    current_cumulative_area_ha - benchmark_marginal_area_ha,
                )
                benchmark_cumulative_area_ha = current_cumulative_area_ha
        parent_step_id = _build_land_base_parent_step_id(row_order, label)
        draft_subrules = _build_draft_subrules_for_parent_step(
            parent_step_id=parent_step_id,
            linked_subsection=linked_subsection,
            source_index=source_index,
            execution_class=execution_class,
        )
        compiled_logic = _build_compiled_logic_for_parent_step(
            parent_step_id=parent_step_id,
            parent_label=label,
            land_base_stage=land_base_stage,
            stage_label=stage_label,
            execution_class=execution_class,
            benchmark_marginal_area_ha=benchmark_marginal_area_ha,
            benchmark_cumulative_area_ha=benchmark_cumulative_area_ha,
            table_provenance=str(row.get("table_provenance", "")),
            row_order=row_order,
            linked_subsection=linked_subsection,
            source_index=source_index,
        )
        if benchmark_marginal_area_ha is None:
            compiled_marginals: list[float] = []
            for item in compiled_logic:
                marginal_value = item.get("benchmark_marginal_area_ha")
                if marginal_value is None:
                    continue
                compiled_marginals.append(float(marginal_value))
            if compiled_marginals:
                benchmark_marginal_area_ha = compiled_marginals[0]
        if benchmark_cumulative_area_ha is None:
            compiled_cumulatives: list[float] = []
            for item in compiled_logic:
                cumulative_value = item.get("benchmark_cumulative_area_ha")
                if cumulative_value is None:
                    continue
                compiled_cumulatives.append(float(cumulative_value))
            if compiled_cumulatives:
                benchmark_cumulative_area_ha = compiled_cumulatives[0]
        supporting_provenance_ids: list[str] = []
        if linked_subsection:
            provenance_id = str(linked_subsection.get("provenance_id", "")).strip()
            if provenance_id:
                supporting_provenance_ids.append(provenance_id)
        supporting_provenance_ids.extend(
            _additional_supporting_provenance_ids(parent_label=label)
        )
        parent_steps.append(
            {
                "parent_step_id": parent_step_id,
                "parent_label": label,
                "parent_kind": _parent_kind_for_execution_class(execution_class),
                "row_order": row_order,
                "row_source_kind": "table_summary_row",
                "table_role": "land_base_summary",
                "land_base_stage": land_base_stage,
                "stage_label": stage_label,
                "execution_class": execution_class,
                "benchmark_marginal_area_ha": benchmark_marginal_area_ha,
                "benchmark_cumulative_area_ha": benchmark_cumulative_area_ha,
                "table_provenance": str(row.get("table_provenance", "")),
                "subsection_title": str(linked_subsection.get("title", ""))
                if linked_subsection
                else "",
                "subsection_number": str(linked_subsection.get("section_number", ""))
                if linked_subsection
                else "",
                "supporting_provenance_ids": supporting_provenance_ids,
                "draft_subrules": [dict(item) for item in draft_subrules],
                "compiled_logic": [dict(item) for item in compiled_logic],
            }
        )
        compiled_steps.extend(dict(item) for item in compiled_logic)
    return tuple(parent_steps), tuple(compiled_steps)


_THLB_GENERIC_TOKENS = {
    "the",
    "and",
    "for",
    "from",
    "with",
    "that",
    "this",
    "will",
    "into",
    "have",
    "used",
    "use",
    "land",
    "base",
    "timber",
    "harvesting",
    "thlb",
    "whse",
    "reg",
    "resource",
    "resources",
    "planning",
    "management",
    "current",
    "poly",
    "line",
    "lines",
    "svw",
    "sp",
    "tsa",
    "bcgw",
    "data",
    "layer",
    "forest",
    "natural",
}


def _meaningful_tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[A-Za-z0-9]+", str(text).casefold())
        if len(token) >= 3 and token not in _THLB_GENERIC_TOKENS
    }
    return tokens


def _extract_token_years(text: str) -> tuple[int, ...]:
    years: list[int] = []
    seen: set[int] = set()
    for match in re.findall(r"\b(19\d{2}|20\d{2})\b", str(text)):
        year = int(match)
        if year in seen:
            continue
        seen.add(year)
        years.append(year)
    return tuple(years)


def _build_source_recipe_index(
    source_recipe: TsrSourceLayersRecipeRecord,
) -> tuple[dict[str, Any], ...]:
    latest_cycle_year = max(
        (
            int(str(cycle_year))
            for entry in source_recipe.entries
            if (cycle_year := entry.get("cycle_year")) not in (None, "")
        ),
        default=0,
    )
    indexed = []
    for entry in source_recipe.entries:
        entry_id = str(entry.get("entry_id", "")).strip()
        if not entry_id:
            continue
        label = str(entry.get("label", "")).strip()
        recommended_query = str(entry.get("recommended_query", "")).strip()
        top_match_title = str(entry.get("top_match_title", "")).strip()
        snippet = str(entry.get("snippet", "")).strip()
        cycle_year = int(entry.get("cycle_year", 0) or 0)
        query_years = _extract_token_years(
            " ".join(
                part
                for part in (label, recommended_query, top_match_title, snippet)
                if part
            )
        )
        is_stale_year_stamped = (
            bool(query_years)
            and cycle_year > 0
            and latest_cycle_year > 0
            and cycle_year < latest_cycle_year
        )
        exact_query_keys = {
            _normalize_source_query_key(value)
            for value in (entry_id, label, recommended_query)
            if _normalize_source_query_key(value)
        }
        tokens = (
            _meaningful_tokens(label)
            | _meaningful_tokens(recommended_query)
            | _meaningful_tokens(top_match_title)
            | _meaningful_tokens(snippet)
        )
        indexed.append(
            {
                "entry_id": entry_id,
                "label": label,
                "recommended_query": recommended_query,
                "exact_query_keys": exact_query_keys,
                "tokens": tokens,
                "cycle_year": cycle_year,
                "query_years": query_years,
                "is_stale_year_stamped": is_stale_year_stamped,
            }
        )
    return tuple(indexed)


def _link_thlb_step_to_sources(
    text: str,
    *,
    source_index: tuple[dict[str, Any], ...],
    explicit_query_tokens: Sequence[str] = (),
) -> tuple[str, ...]:
    if explicit_query_tokens:
        direct_matches: list[str] = []
        seen: set[str] = set()
        normalized_tokens = {
            _normalize_source_query_key(token)
            for token in explicit_query_tokens
            if _normalize_source_query_key(token)
        }
        for entry in source_index:
            if normalized_tokens & set(entry.get("exact_query_keys", set())):
                entry_id = str(entry["entry_id"])
                if entry_id not in seen:
                    seen.add(entry_id)
                    direct_matches.append(entry_id)
        if direct_matches:
            return tuple(direct_matches)

    subject_tokens = _meaningful_tokens(text)
    text_years = set(_extract_token_years(text))
    if not subject_tokens:
        return ()

    scored: list[tuple[int, int, int, str]] = []
    for entry in source_index:
        overlap = subject_tokens & set(entry["tokens"])
        score = len(overlap)
        if (
            score > 0
            and bool(entry.get("is_stale_year_stamped"))
            and not (text_years & set(entry.get("query_years", ())))
        ):
            score -= 1
        if score > 0:
            scored.append(
                (
                    score,
                    1 if bool(entry.get("is_stale_year_stamped")) else 0,
                    int(entry.get("cycle_year", 0) or 0),
                    str(entry["entry_id"]),
                )
            )
    scored.sort(key=lambda item: (-item[0], item[1], -item[2], item[3]))
    if not scored:
        return ()

    top_score = scored[0][0]
    linked = [entry_id for score, _, _, entry_id in scored if score == top_score]
    if top_score == 1:
        return tuple(linked[:1])
    return tuple(linked[:3])


def _match_thlb_action(text: str) -> tuple[str, str, str]:
    normalized = _normalize_whitespace(text)
    lower = normalized.casefold()

    patterns = (
        (
            "use_land_base",
            re.compile(
                r"^(?P<subject>.+?)\s+use\s+(?P<predicate>[A-Z]{3,5})$", re.IGNORECASE
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+exclude(?:d)?\s+(?P<predicate>.+?)\s+from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "exclude",
            re.compile(r"^(?P<subject>.+?)\s+exclude from the thlb$", re.IGNORECASE),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+remove(?:d)?\s+(?P<predicate>.+?)\s+from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+(?:are|is)\s+removed from the thlb", re.IGNORECASE
            ),
        ),
        (
            "exclude",
            re.compile(
                r"^(?P<subject>.+?)\s+(?:are|is)\s+excluded from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "defer",
            re.compile(
                r"^(?P<subject>.+?)\s+included in the thlb but will be deferred from harvest for (?P<predicate>\d+\s+years?)",
                re.IGNORECASE,
            ),
        ),
        (
            "aspatial_reduction",
            re.compile(
                r"^(?P<subject>.+?)\s+will be modelled as an aspatial(?: thlb)? reduction(?: factor)?",
                re.IGNORECASE,
            ),
        ),
        (
            "no_deduction",
            re.compile(
                r"^(?P<subject>.+?)\s+will have no deduction from the thlb",
                re.IGNORECASE,
            ),
        ),
        (
            "restore",
            re.compile(
                r"^(?P<subject>.+?)\s+.*fully restored to the thlb",
                re.IGNORECASE,
            ),
        ),
    )
    for action, pattern in patterns:
        match = pattern.search(normalized)
        if match:
            subject = _normalize_whitespace(match.groupdict().get("subject", ""))
            predicate = _normalize_whitespace(match.groupdict().get("predicate", ""))
            return action, subject, predicate

    if "long-term thlb" in lower:
        return "reference_target", "long-term thlb", _normalize_whitespace(normalized)
    if "the thlb is the portion" in lower:
        return "definition", "thlb definition", ""
    if "the thlb may increase in size" in lower:
        return "increase_conditions", "thlb increase conditions", ""
    if "the thlb may also decrease in size" in lower:
        return "decrease_conditions", "thlb decrease conditions", ""
    return "", "", ""


def _is_heading_like(text: str) -> bool:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return False
    return bool(
        re.match(r"^\d+(\.\d+)*\s", normalized)
        or "timber harvesting land base definition" in normalized.casefold()
        or "identification of the timber harvesting land base" in normalized.casefold()
    )


def _is_toc_like_text(text: str) -> bool:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return False
    return bool(
        re.search(r"\.{2,}\s*\d+\s*$", normalized)
        or (
            re.match(r"^(table|figure)\s+\d+[\.:]?", normalized, flags=re.IGNORECASE)
            and re.search(r"\d+\s*$", normalized)
        )
    )


def _is_orphan_thlb_noise(text: str) -> bool:
    normalized = _normalize_whitespace(text).casefold()
    if not normalized:
        return False
    if normalized in _THLB_JUNK_FRAGMENTS:
        return True
    words = normalized.split()
    return len(words) <= 3 and normalized.endswith((" are", " is", " to", " of"))


def _is_low_signal_thlb_subject(text: str) -> bool:
    normalized = _normalize_whitespace(text).casefold()
    if not normalized:
        return True
    if normalized in _THLB_JUNK_FRAGMENTS:
        return True
    return len(normalized.split()) <= 2 and normalized in {
        "stands",
        "lands",
        "areas",
        "mortality",
    }


def _preferred_thlb_primary_text(*, value: str, snippet: str) -> str:
    normalized_value = _normalize_whitespace(value)
    normalized_snippet = _normalize_whitespace(snippet)
    if not normalized_snippet:
        return normalized_value
    if not normalized_value:
        return normalized_snippet
    if re.fullmatch(r"\d+(?:\.\d+)*", normalized_value):
        return normalized_snippet
    if len(normalized_value) <= 8 and len(normalized_snippet) > len(normalized_value):
        return normalized_snippet
    if _is_toc_like_text(normalized_snippet):
        return normalized_snippet
    return normalized_value


def _find_land_base_anchor_page(rows: Sequence[TsrFactReviewRow]) -> int | None:
    anchor_patterns = (
        "gross land base",
        "analysis forest land base",
        "aflb",
        "legally harvestable land base",
        "lhlb",
        "timber harvesting land base",
        "thlb",
    )
    pages = [
        int(row.page_number)
        for row in rows
        if row.page_number
        and not _is_toc_like_text(
            _preferred_thlb_primary_text(
                value=row.extracted_value,
                snippet=row.snippet,
            )
        )
        and not _is_orphan_thlb_noise(
            _preferred_thlb_primary_text(
                value=row.extracted_value,
                snippet=row.snippet,
            )
        )
        and any(
            pattern
            in _preferred_thlb_primary_text(
                value=row.extracted_value,
                snippet=row.snippet,
            ).casefold()
            for pattern in anchor_patterns
        )
    ]
    if not pages:
        return None
    return min(pages)


def _infer_land_base_stage(*, action: str, snippet: str, value: str) -> str:
    # Prototype-fin guardrail: stage anchors help the extractor recognize a
    # plausible THLB step instead of bringing back locally plausible junk.
    normalized = _normalize_whitespace(
        " ".join(part for part in (value, snippet) if part)
    )
    lower = normalized.casefold()
    if action == "reference_target":
        return "reference_target"
    if action in {
        "definition",
        "increase_conditions",
        "decrease_conditions",
        "section_heading",
    }:
        if "thlb" in lower and "lhlb" in lower:
            return "lhlb_to_thlb"
        if "gross land base" in lower or "analysis forest land base" in lower:
            return "glb_to_aflb"
        if "legally harvestable land base" in lower or "lhlb" in lower:
            return "aflb_to_lhlb"
        if "timber harvesting land base" in lower or "thlb" in lower:
            return "lhlb_to_thlb"
        return "context"
    if any(
        token in lower
        for token in (
            "gross land base",
            "analysis forest land base",
            "aflb",
            "non-forested",
            "non contributing",
            "aac is determined separately",
        )
    ):
        return "glb_to_aflb"
    if any(
        token in lower
        for token in (
            "legally harvestable land base",
            "lhlb",
            "legally unavailable",
            "harvesting prohibited",
            "legal harvest",
            "no harvest",
            "park",
            "ecological reserve",
            "protected area",
        )
    ):
        return "aflb_to_lhlb"
    if any(
        token in lower
        for token in (
            "timber harvesting land base",
            "thlb",
            "ogma",
            "mule deer",
            "winter range",
            "wildlife tree",
            "wtra",
            "riparian",
            "road",
            "roads",
            "unstable slope",
            "terrain stability",
            "viewscape",
            "projected to occur",
            "deferred from harvest",
        )
    ):
        return "lhlb_to_thlb"
    return "context"


def _infer_execution_class(*, stage: str, action: str, step_kind: str) -> str:
    if stage == "reference_target" or step_kind == "reference_target":
        return "reference_only"
    if stage == "context" or step_kind == "context":
        return "context_only"
    if action == "aspatial_reduction":
        return "aspatial_fallback_candidate"
    if action in {"use_land_base", "no_deduction", "restore"}:
        return "no_deduction"
    if stage == "glb_to_aflb":
        return "drop_from_universe"
    if stage == "aflb_to_lhlb":
        return "legal_harvest_exclusion"
    return "projected_harvest_exclusion"


def _classify_thlb_recipe_step(
    row: TsrFactReviewRow,
    *,
    documents_index: dict[str, dict[str, Any]],
    source_index: tuple[dict[str, Any], ...],
    anchor_page: int | None,
) -> dict[str, Any] | None:
    snippet = _normalize_whitespace(row.snippet)
    value = _normalize_whitespace(row.extracted_value)
    if not snippet:
        return None
    primary_text = _preferred_thlb_primary_text(value=value, snippet=snippet)
    if _is_toc_like_text(primary_text):
        return None
    if _is_orphan_thlb_noise(primary_text):
        return None
    if (
        anchor_page is not None
        and int(row.page_number or 0) < anchor_page
        and (_is_heading_like(snippet) or _is_toc_like_text(snippet))
    ):
        return None

    action, subject, predicate = _match_thlb_action(primary_text)
    document_path = _provenance_document_path(row.provenance_id)
    document_record = documents_index.get(document_path, {})
    document_title = row.title or str(document_record.get("title", ""))
    document_type = str(document_record.get("document_type", "")).strip()

    if action == "reference_target":
        step_kind = "reference_target"
        label = "Long-term THLB reference"
    elif action in {"definition", "increase_conditions", "decrease_conditions"}:
        step_kind = "context"
        label = {
            "definition": "THLB definition",
            "increase_conditions": "THLB increase conditions",
            "decrease_conditions": "THLB decrease conditions",
        }[action]
    elif action:
        step_kind = "netdown_rule"
        label = primary_text[:120] if _is_low_signal_thlb_subject(subject) else subject
    elif _is_heading_like(snippet):
        step_kind = "context"
        label = snippet[:80]
        action = "section_heading"
    else:
        return None

    land_base_stage = _infer_land_base_stage(
        action=action,
        snippet=snippet,
        value=value,
    )
    stage_label = _THLB_STAGE_LABELS[land_base_stage]
    execution_class = _infer_execution_class(
        stage=land_base_stage,
        action=action,
        step_kind=step_kind,
    )

    linked_source_entry_ids = _link_thlb_step_to_sources(
        " ".join(part for part in (label, snippet, subject, predicate) if part),
        source_index=source_index,
    )
    if step_kind == "context":
        step_status = "needs_review"
        required = False
    elif step_kind == "reference_target":
        step_status = "ready"
        required = True
    elif linked_source_entry_ids or action in {
        "use_land_base",
        "aspatial_reduction",
        "no_deduction",
        "restore",
    }:
        step_status = "ready"
        required = True
    else:
        step_status = "blocked_missing_source"
        required = True

    notes = []
    if not linked_source_entry_ids and step_kind == "netdown_rule":
        notes.append(
            "No source-layer recipe entry linked automatically; review or add an override."
        )

    return {
        "step_kind": step_kind,
        "label": _normalize_whitespace(label),
        "raw_value": value,
        "raw_text": snippet,
        "land_base_stage": land_base_stage,
        "stage_label": stage_label,
        "execution_class": execution_class,
        "normalized_action": action,
        "normalized_subject": subject,
        "normalized_predicate": predicate,
        "linked_source_entry_ids": list(linked_source_entry_ids),
        "step_status": step_status,
        "required": required,
        "page_number": row.page_number,
        "document_title": document_title,
        "document_type": document_type,
        "cycle_label": row.cycle_label,
        "cycle_year": row.cycle_year,
        "provenance_id": row.provenance_id,
        "source_url": row.source_url,
        "notes": notes,
    }


def build_tsr_source_layers_recipe(
    *,
    recipe_path: Path,
    source_root: Path,
    limit: int = 5,
) -> TsrSourceLayersRecipeBuildResult:
    """Populate the source-layer recipe from TSR facts and current BCDC knowledge."""

    recipe = load_tsr_source_layers_recipe(recipe_path)
    source_root_resolved = source_root.expanduser().resolve()
    candidate_facts_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.candidate_facts_path
    )
    instance_root = recipe_path.expanduser().resolve().parents[2]
    overrides_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_overrides_path
    )
    overlay_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.overlay_path
    )
    override_map = _load_override_map(overrides_path)
    overlay_attempt_map = _load_overlay_attempt_map(overlay_path)

    entries = []
    status_counts: Counter[str] = Counter()
    for row in _review_rows_for_recipe(
        candidate_facts_path,
        tsa_code=recipe.tsa.tsa_code,
    ):
        resolve_result = resolve_bcdc_candidates(row.recommended_query, limit=limit)
        entry = _build_source_recipe_entry(
            row,
            resolve_result=resolve_result,
            override_entry=override_map.get(row.recommended_query.casefold()),
            overlay_attempt=_overlay_attempt_for_row(
                row,
                resolve_result=resolve_result,
                overlay_attempt_map=overlay_attempt_map,
            ),
            instance_root=instance_root,
        )
        entries.append(entry)
        status_counts.update([entry["current_public_status"]])

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "built"
    recipe_contract["last_built_utc"] = datetime.now(UTC).isoformat()
    payload["recipe_contract"] = recipe_contract
    payload["entries"] = entries
    _write_recipe_yaml(recipe_path.expanduser().resolve(), payload)
    return TsrSourceLayersRecipeBuildResult(
        recipe_path=recipe_path.expanduser().resolve(),
        tsa=recipe.tsa,
        entry_count=len(entries),
        status_counts=dict(sorted(status_counts.items())),
    )


def build_tsr_thlb_netdown_recipe(
    *,
    recipe_path: Path,
    source_root: Path,
) -> TsrThlbNetdownRecipeBuildResult:
    """Populate the THLB netdown recipe from TSR facts and source-layer recipe state."""

    recipe = load_tsr_thlb_netdown_recipe(recipe_path)
    source_root_resolved = source_root.expanduser().resolve()
    candidate_facts_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.candidate_facts_path
    )
    documents_path = _resolve_path_from_recipe(
        source_root_resolved, recipe.canonical_inputs.documents_path
    )
    instance_root = recipe_path.expanduser().resolve().parents[2]
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    source_index = _build_source_recipe_index(source_recipe)
    overrides_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_overrides_path
    )
    override_entries = _load_override_map(overrides_path)

    report_result = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa=recipe.tsa.tsa_code,
        fact_families=("thlb_reference",),
        limit=None,
    )
    documents_index, documents = _load_tsa_documents_for_recipe(
        documents_path,
        tsa_id=recipe.tsa.tsa_id,
    )
    selected_rows, selected_document_paths = _choose_preferred_thlb_documents(
        report_result.rows,
        documents_index=documents_index,
        documents=documents,
    )
    parent_steps: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    step_kind_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    pdf_pages, _selected_pdf_relative_path = _load_selected_tsr_pdf_pages(
        tsa_id=recipe.tsa.tsa_id,
        selected_document_paths=selected_document_paths,
    )
    summary_rows = _extract_land_base_summary_rows(pdf_pages)
    subsections = _extract_land_base_subsections(pdf_pages)
    if summary_rows:
        built_parent_steps, built_compiled_steps = (
            _build_parent_steps_from_land_base_summary(
                summary_rows=summary_rows,
                subsections=subsections,
                source_index=source_index,
            )
        )
        parent_steps = _merge_preserved_thlb_parent_step_metadata(
            existing_parent_steps=recipe.parent_steps,
            built_parent_steps=built_parent_steps,
        )
        steps = [dict(item) for item in built_compiled_steps]
        for step in steps:
            step_kind_counts.update([str(step.get("step_kind", ""))])
            status_counts.update([str(step.get("step_status", ""))])
    else:
        anchor_page = _find_land_base_anchor_page(selected_rows)
        seen_signatures: set[tuple[int, str, str]] = set()
        for order_index, row in enumerate(
            sorted(
                selected_rows,
                key=lambda item: (
                    int(item.page_number or 0),
                    str(item.provenance_id),
                    str(item.extracted_value),
                ),
            ),
            start=1,
        ):
            classified = _classify_thlb_recipe_step(
                row,
                documents_index=documents_index,
                source_index=source_index,
                anchor_page=anchor_page,
            )
            if classified is None:
                continue
            signature = (
                int(classified.get("page_number") or 0),
                str(classified["step_kind"]),
                str(classified["raw_text"]),
            )
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            slug = _normalize_step_slug(
                str(classified["label"] or classified["normalized_action"])
            )
            step_id = f"thlb_step_{order_index:03d}_{slug}"
            classified["step_id"] = step_id
            classified["order_index"] = order_index
            steps.append(classified)
            step_kind_counts.update([str(classified["step_kind"])])
            status_counts.update([str(classified["step_status"])])

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "built"
    recipe_contract["last_built_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["selected_document_paths"] = list(selected_document_paths)
    payload["recipe_contract"] = recipe_contract
    payload["parent_steps"] = parent_steps
    payload["steps"] = steps
    resolved_recipe_path = recipe_path.expanduser().resolve()
    _write_recipe_yaml(resolved_recipe_path, payload)

    build_status_report_path = default_tsr_thlb_netdown_status_report_path(
        instance_root=instance_root
    )
    build_report_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runtime_build_status_report_path = (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / f"thlb_recipe_build_status_report-{build_report_timestamp}.md"
    )
    build_generated_utc = datetime.now(UTC).isoformat()
    build_status_report_markdown = _build_tsr_thlb_recipe_build_report_markdown(
        recipe=load_tsr_thlb_netdown_recipe(resolved_recipe_path),
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        source_layer_recipe_relative_path=str(
            source_layer_recipe_path.relative_to(instance_root).as_posix()
        ),
        generated_utc=build_generated_utc,
        runtime_report_relative_path=str(
            runtime_build_status_report_path.relative_to(instance_root).as_posix()
        ),
        source_entry_map=_load_source_recipe_entry_map(source_recipe),
        override_entries=override_entries,
    )
    build_status_report_path.parent.mkdir(parents=True, exist_ok=True)
    build_status_report_path.write_text(build_status_report_markdown, encoding="utf-8")
    runtime_build_status_report_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_build_status_report_path.write_text(
        build_status_report_markdown, encoding="utf-8"
    )
    recipe_contract["recipe_build_status_report_path"] = str(
        build_status_report_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["recipe_build_runtime_status_report_path"] = str(
        runtime_build_status_report_path.relative_to(instance_root).as_posix()
    )
    payload["recipe_contract"] = recipe_contract
    _write_recipe_yaml(resolved_recipe_path, payload)
    return TsrThlbNetdownRecipeBuildResult(
        recipe_path=resolved_recipe_path,
        tsa=recipe.tsa,
        step_count=len(steps),
        step_kind_counts=dict(sorted(step_kind_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
        selected_document_paths=selected_document_paths,
    )


def _path_exists_under_instance(instance_root: Path, value: str) -> bool:
    if not value:
        return False
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = instance_root / candidate
    return candidate.expanduser().resolve().exists()


def run_tsr_source_layers_recipe(
    *,
    recipe_path: Path,
    bbox_epsg3005: tuple[float, float, float, float] | None = None,
    geomark: GeomarkBBox | None = None,
    limit: int = 5,
    allow_order: bool = False,
) -> TsrSourceLayersRecipeRunResult:
    """Execute safe source-layer acquisition steps from one recipe."""

    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_source_layers_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    download_root = _resolve_instance_path(
        instance_root, recipe.instance_inputs.download_root
    )
    outcome_counts: Counter[str] = Counter()
    payload = recipe.to_dict()
    updated_entries: list[dict[str, Any]] = []

    needs_aoi = any(
        entry.get("acquisition_strategy") in {"wfs_fetch", "dwds_order"}
        for entry in recipe.entries
    )
    if needs_aoi and bbox_epsg3005 is None:
        raise TsrRecipeError(
            "Source-layer recipe execution needs an AOI for WFS/DWDS entries. "
            "Supply `--bbox` or `--geomark`."
        )

    for entry in recipe.entries:
        updated = dict(entry)
        strategy = str(entry.get("acquisition_strategy", ""))
        artifact_path = str(entry.get("artifact_path", ""))
        query = str(
            entry.get("acquisition_query") or entry.get("recommended_query", "")
        )
        override_kind = str(entry.get("override_kind", ""))

        if strategy == "override":
            if override_kind in {"local_path", "datalad_path", "replacement_layer"}:
                updated["run_status"] = "override_resolved"
            elif override_kind in {"dataset_url", "private", "unavailable"}:
                updated["run_status"] = "override_requires_manual_materialization"
            else:
                updated["run_status"] = "override_pending"
            outcome_counts.update([updated["run_status"]])
            updated_entries.append(updated)
            continue

        if artifact_path and _path_exists_under_instance(instance_root, artifact_path):
            updated["run_status"] = "reused"
            outcome_counts.update(["reused"])
            updated_entries.append(updated)
            continue

        if strategy == "manual_review_required":
            updated["run_status"] = "manual_review_required"
        elif strategy == "override_required":
            updated["run_status"] = "override_required"
        elif strategy == "wfs_fetch":
            assert bbox_epsg3005 is not None
            try:
                fetch_result = fetch_bcdc_wfs_data(
                    query,
                    destination_root=download_root,
                    bbox_epsg3005=bbox_epsg3005,
                    limit=limit,
                    geomark=geomark,
                    query_slug=str(
                        entry.get("recommended_query") or entry.get("entry_id") or query
                    ),
                )
                updated["artifact_path"] = str(
                    fetch_result.saved_path.relative_to(instance_root).as_posix()
                )
                updated["feature_count"] = fetch_result.feature_count
                updated["run_status"] = "fetched"
            except BcdcFetchError as exc:
                updated["run_status"] = "failed"
                updated["failure_message"] = str(exc)
        elif strategy == "direct_download":
            try:
                resolve_result = resolve_bcdc_candidates(query, limit=limit)
                download_result = download_direct_bcdc_resources(
                    resolve_result,
                    destination_root=download_root,
                    query_slug=str(
                        entry.get("recommended_query") or entry.get("entry_id") or query
                    ),
                )
                downloaded = download_result.downloaded
                if downloaded:
                    saved_path = downloaded[0].saved_path
                    updated["artifact_path"] = str(
                        saved_path.relative_to(instance_root).as_posix()
                    )
                    updated["run_status"] = "downloaded"
                else:
                    updated["run_status"] = "failed"
                    updated["failure_message"] = (
                        "Direct download returned no saved resources."
                    )
            except Exception as exc:  # pragma: no cover - network/runtime seam
                updated["run_status"] = "failed"
                updated["failure_message"] = str(exc)
        elif strategy == "dwds_order":
            if not allow_order:
                updated["run_status"] = "dwds_order_skipped"
            else:
                assert bbox_epsg3005 is not None
                try:
                    order_result = submit_bcdc_dwds_order(
                        query,
                        bbox_epsg3005=bbox_epsg3005,
                        limit=limit,
                        geomark=geomark,
                    )
                    updated["run_status"] = "ordered"
                    updated["order_id"] = order_result.order_id
                    updated["submission_status"] = order_result.submission_status
                except BcdcDwdsError as exc:
                    updated["run_status"] = "failed"
                    updated["failure_message"] = str(exc)
        else:
            updated["run_status"] = "blocked"

        outcome_counts.update([str(updated.get("run_status", "blocked"))])
        updated_entries.append(updated)

    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["last_run_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["status"] = "run"
    payload["recipe_contract"] = recipe_contract
    payload["entries"] = updated_entries
    _write_recipe_yaml(resolved_recipe_path, payload)
    return TsrSourceLayersRecipeRunResult(
        recipe_path=resolved_recipe_path,
        tsa=recipe.tsa,
        entry_count=len(updated_entries),
        outcome_counts=dict(sorted(outcome_counts.items())),
    )


def _find_tsr_checkpoint_path(*, instance_root: Path, mode: str) -> Path:
    candidates = sorted(
        instance_root.expanduser()
        .resolve()
        .glob("data/ria_vri_vclr1p_checkpoint*.feather")
    )
    if not candidates:
        raise TsrRecipeError(
            "No stand checkpoint feather found under the instance data directory."
        )

    def _checkpoint_order(path: Path) -> int:
        match = re.search(r"checkpoint(\d+)", path.stem, flags=re.IGNORECASE)
        if match is None:
            return -1
        return int(match.group(1))

    if mode == "latest":
        return max(candidates, key=_checkpoint_order)
    if mode == "earliest":
        return min(candidates, key=_checkpoint_order)
    raise TsrRecipeError(f"Unsupported checkpoint lookup mode: {mode}")


def _feather_has_column(path: Path, column: str) -> bool:
    try:
        frame = pd.read_feather(path, columns=[column])
    except Exception:
        return False
    return column in frame.columns


def _find_curve_ready_thlb_checkpoint_path(*, instance_root: Path) -> Path:
    candidates = sorted(
        instance_root.expanduser()
        .resolve()
        .glob("data/ria_vri_vclr1p_checkpoint*.feather")
    )
    if not candidates:
        raise TsrRecipeError(
            "No stand checkpoint feather found under the instance data directory."
        )

    def _checkpoint_order(path: Path) -> int:
        match = re.search(r"checkpoint(\d+)", path.stem, flags=re.IGNORECASE)
        if match is None:
            return -1
        return int(match.group(1))

    curve_ready = [path for path in candidates if _feather_has_column(path, "curve1")]
    if not curve_ready:
        return _find_tsr_checkpoint_path(instance_root=instance_root, mode="latest")
    pre_legacy_flag = [
        path
        for path in curve_ready
        if not _feather_has_column(path, "thlb_area")
        and not _feather_has_column(path, "thlb")
    ]
    if pre_legacy_flag:
        return max(pre_legacy_flag, key=_checkpoint_order)
    return max(curve_ready, key=_checkpoint_order)


def _default_workbench_checkpoint_path(
    *, instance_root: Path, target_parent: dict[str, Any]
) -> Path:
    stage = str(target_parent.get("land_base_stage", "")).strip()
    if stage == "lhlb_to_thlb":
        enriched_path = (
            instance_root.expanduser().resolve()
            / _STEP13_ATTRIBUTE_CHECKPOINT_RELATIVE_PATH
        )
        if enriched_path.exists():
            return enriched_path
    if stage == "glb_to_aflb":
        return _find_tsr_checkpoint_path(instance_root=instance_root, mode="earliest")
    return _find_curve_ready_thlb_checkpoint_path(instance_root=instance_root)


def _additional_supporting_provenance_ids(*, parent_label: str) -> tuple[str, ...]:
    return _THLB_ADDITIONAL_SUPPORTING_PROVENANCE_IDS.get(
        parent_label.strip().casefold(),
        (),
    )


def _workbench_stage_window_for_target(
    target_parent: dict[str, Any],
) -> tuple[str, ...]:
    stage = str(target_parent.get("land_base_stage", "")).strip()
    if stage == "glb_to_aflb":
        return ("glb_to_aflb",)
    if stage in {"aflb_to_lhlb", "lhlb_to_thlb"}:
        return ("aflb_to_lhlb", "lhlb_to_thlb")
    return (stage,) if stage else ()


def _load_checkpoint_geodataframe(path: Path) -> gpd.GeoDataFrame:
    try:
        checkpoint = gpd.read_feather(path)
    except Exception as exc:  # pragma: no cover - filesystem/runtime seam
        raise TsrRecipeError(f"Unable to read THLB checkpoint feather: {path}") from exc
    if "geometry" not in checkpoint.columns:
        raise TsrRecipeError(f"THLB checkpoint is missing a geometry column: {path}")
    checkpoint = checkpoint.copy()
    if checkpoint.crs is None:
        checkpoint = checkpoint.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint = checkpoint.to_crs(BC_ALBERS_EPSG)
    return checkpoint


def _normalize_map_id_token(value: Any) -> str:
    text = str(value).strip().upper()
    return text


def _filter_checkpoint_by_map_ids(
    checkpoint: gpd.GeoDataFrame,
    *,
    map_ids: tuple[str, ...],
) -> gpd.GeoDataFrame:
    if not map_ids:
        return checkpoint
    if "MAP_ID" not in checkpoint.columns:
        raise TsrRecipeError(
            "Checkpoint does not carry `MAP_ID`, so MAP_ID-based THLB smoke subsetting "
            "cannot be applied."
        )
    normalized = tuple(
        _normalize_map_id_token(value) for value in map_ids if str(value).strip()
    )
    if not normalized:
        return checkpoint
    subset = checkpoint.loc[
        checkpoint["MAP_ID"].fillna("").astype(str).str.upper().isin(normalized)
    ].copy()
    if subset.empty:
        raise TsrRecipeError(
            "MAP_ID subset did not match any checkpoint rows: " + ", ".join(normalized)
        )
    return subset


def _auto_select_smoke_map_ids(
    checkpoint: gpd.GeoDataFrame,
    *,
    max_area_ha: float = 100000.0,
) -> tuple[str, ...]:
    if "MAP_ID" not in checkpoint.columns:
        raise TsrRecipeError(
            "Checkpoint does not carry `MAP_ID`, so automatic smoke subset selection "
            "cannot be applied."
        )
    working = checkpoint.loc[
        checkpoint["MAP_ID"].notna() & checkpoint.geometry.notna()
    ].copy()
    if working.empty:
        raise TsrRecipeError("Checkpoint does not contain any usable `MAP_ID` rows.")
    working["_area_ha"] = working.geometry.area.astype(float) / 10000.0
    summary = (
        working.groupby("MAP_ID", dropna=False)
        .agg(rows=("MAP_ID", "size"), area_ha=("_area_ha", "sum"))
        .sort_values(["area_ha", "rows"], ascending=[False, False])
    )
    under_cap = summary.loc[summary["area_ha"] <= max_area_ha]
    chosen = under_cap.index[0] if not under_cap.empty else summary.index[0]
    return (_normalize_map_id_token(chosen),)


def _find_landscape_unit_layer_path(instance_root: Path) -> Path | None:
    candidates = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW"
        / "WHSE_LAND_USE_PLANNING_RMP_LANDSCAPE_UNIT_SVW.gpkg",
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "RMP_LANDSCAPE_UNIT_SVW_NO_MULTIPLES"
        / "RMP_LANDSCAPE_UNIT_SVW_NO_MULTIPLES.gpkg",
    )
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.exists():
            return resolved
    return None


def _load_landscape_unit_layer(instance_root: Path) -> gpd.GeoDataFrame:
    layer_path = _find_landscape_unit_layer_path(instance_root)
    if layer_path is None:
        raise TsrRecipeError(
            "Landscape unit layer was not found under the instance BCDC downloads."
        )
    lu_layer = gpd.read_file(layer_path, engine="pyogrio")
    if lu_layer.empty or "geometry" not in lu_layer.columns:
        raise TsrRecipeError(
            f"Landscape unit layer is empty or unreadable: {layer_path}"
        )
    if lu_layer.crs is None:
        lu_layer = lu_layer.set_crs(BC_ALBERS_EPSG)
    else:
        lu_layer = lu_layer.to_crs(BC_ALBERS_EPSG)
    return lu_layer


def _select_landscape_unit_rows(
    lu_layer: gpd.GeoDataFrame,
    *,
    landscape_units: Sequence[str],
) -> tuple[gpd.GeoDataFrame, tuple[str, ...]]:
    tokens = tuple(
        str(value).strip() for value in landscape_units if str(value).strip()
    )
    if not tokens:
        return lu_layer.iloc[0:0].copy(), ()
    normalized = {token.casefold() for token in tokens}
    selected_rows = pd.Series(False, index=lu_layer.index)
    for column in ("LANDSCAPE_UNIT_ID", "LANDSCAPE_UNIT_NAME", "LANDSCAPE_UNIT_NUMBER"):
        if column not in lu_layer.columns:
            continue
        values = lu_layer[column].fillna("").astype(str).str.strip()
        selected_rows = selected_rows | values.str.casefold().isin(normalized)
    selected = lu_layer.loc[selected_rows].copy()
    selected_names = tuple(
        str(value).strip()
        for value in selected.get("LANDSCAPE_UNIT_NAME", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .tolist()
        if str(value).strip()
    )
    return selected, selected_names


def _filter_checkpoint_by_landscape_units(
    checkpoint: gpd.GeoDataFrame,
    *,
    instance_root: Path,
    landscape_units: Sequence[str],
) -> tuple[gpd.GeoDataFrame, tuple[str, ...]]:
    tokens = tuple(
        str(value).strip() for value in landscape_units if str(value).strip()
    )
    if not tokens:
        return checkpoint, ()
    lu_layer = _load_landscape_unit_layer(instance_root)
    selected, selected_names = _select_landscape_unit_rows(
        lu_layer, landscape_units=landscape_units
    )
    if selected.empty:
        raise TsrRecipeError(
            "Landscape unit subset did not match any LU rows: "
            + ", ".join(
                str(value).strip() for value in landscape_units if str(value).strip()
            )
        )
    union = selected.geometry.union_all()
    checkpoint_bc = checkpoint.copy()
    if checkpoint_bc.crs is None:
        checkpoint_bc = checkpoint_bc.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint_bc = checkpoint_bc.to_crs(BC_ALBERS_EPSG)
    subset = checkpoint_bc.loc[checkpoint_bc.geometry.intersects(union)].copy()
    if subset.empty:
        raise TsrRecipeError(
            "Landscape unit subset matched no checkpoint rows: " + ", ".join(tokens)
        )
    return subset, selected_names


def _select_intersecting_landscape_units_for_checkpoint(
    checkpoint: gpd.GeoDataFrame,
    *,
    instance_root: Path,
) -> tuple[gpd.GeoDataFrame, tuple[str, ...], dict[str, float]]:
    profiling: dict[str, float] = {
        "lu_layer_load_seconds": 0.0,
        "lu_bbox_filter_seconds": 0.0,
        "lu_union_seconds": 0.0,
        "lu_intersect_seconds": 0.0,
    }
    lu_load_started = perf_counter()
    lu_layer = _load_landscape_unit_layer(instance_root)
    profiling["lu_layer_load_seconds"] = perf_counter() - lu_load_started
    checkpoint_bc = checkpoint.copy()
    if checkpoint_bc.crs is None:
        checkpoint_bc = checkpoint_bc.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint_bc = checkpoint_bc.to_crs(BC_ALBERS_EPSG)
    bbox = tuple(map(float, checkpoint_bc.total_bounds))
    bbox_started = perf_counter()
    candidate = lu_layer.loc[lu_layer.geometry.intersects(box(*bbox))].copy()
    profiling["lu_bbox_filter_seconds"] = perf_counter() - bbox_started
    if candidate.empty:
        raise TsrRecipeError(
            "No landscape units intersect the current checkpoint extent."
        )
    union_started = perf_counter()
    union = checkpoint_bc.geometry.union_all()
    profiling["lu_union_seconds"] = perf_counter() - union_started
    intersect_started = perf_counter()
    selected = candidate.loc[candidate.geometry.intersects(union)].copy()
    profiling["lu_intersect_seconds"] = perf_counter() - intersect_started
    if selected.empty:
        raise TsrRecipeError(
            "No landscape units intersect the current checkpoint geometry."
        )
    selected_names = tuple(
        str(value).strip()
        for value in selected.get("LANDSCAPE_UNIT_NAME", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .tolist()
        if str(value).strip()
    )
    return selected, selected_names, profiling


def _load_cached_landscape_unit_partition_selection(
    *,
    checkpoint_path: Path,
    instance_root: Path,
) -> tuple[tuple[str, ...], Path] | None:
    partition_root = default_tsr_thlb_lu_partition_root(instance_root=instance_root)
    if not partition_root.exists():
        return None
    resolved_checkpoint = str(checkpoint_path.expanduser().resolve())
    for metadata_path in sorted(partition_root.glob("*/partition_metadata.json")):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(payload.get("checkpoint_path", "")).strip() != resolved_checkpoint:
            continue
        selected_raw = payload.get("selected_landscape_units", [])
        if not isinstance(selected_raw, list):
            continue
        selected_names = tuple(
            str(value).strip() for value in selected_raw if str(value).strip()
        )
        if not selected_names:
            continue
        return selected_names, metadata_path.parent
    return None


def _load_cached_landscape_unit_partition_records(
    *,
    checkpoint_path: Path,
    instance_root: Path,
) -> tuple[tuple[str, ...], list[dict[str, Any]]] | None:
    partition_root = default_tsr_thlb_lu_partition_root(instance_root=instance_root)
    if not partition_root.exists():
        return None
    resolved_checkpoint = str(checkpoint_path.expanduser().resolve())
    for metadata_path in sorted(partition_root.glob("*/partition_metadata.json")):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(payload.get("checkpoint_path", "")).strip() != resolved_checkpoint:
            continue
        selected_raw = payload.get("selected_landscape_units", [])
        records_raw = payload.get("chunk_records", [])
        if not isinstance(selected_raw, list) or not isinstance(records_raw, list):
            continue
        selected_names = tuple(
            str(value).strip() for value in selected_raw if str(value).strip()
        )
        cached_records: list[dict[str, Any]] = []
        partition_dir = metadata_path.parent
        for item in records_raw:
            if not isinstance(item, dict):
                continue
            path_value = str(item.get("chunk_path", "")).strip()
            if not path_value:
                continue
            chunk_path = partition_dir / path_value
            if not chunk_path.exists():
                cached_records = []
                break
            cached_records.append(
                {
                    "lu_name": str(item.get("lu_name", "")).strip(),
                    "chunk_path": chunk_path,
                    "area_ha": float(item.get("area_ha", 0.0) or 0.0),
                }
            )
        if cached_records:
            cached_records.sort(key=lambda item: str(item.get("lu_name", "")).strip())
            return selected_names, cached_records
    return None


def _scale_area_series_for_clip(
    values: pd.Series,
    *,
    ratio: pd.Series,
    unit: str,
) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    scaled = numeric * ratio
    if unit == "ha":
        return scaled.clip(lower=0.0)
    return scaled.clip(lower=0.0)


def _clip_checkpoint_to_landscape_unit_chunks(
    checkpoint: gpd.GeoDataFrame,
    *,
    lu_frame: gpd.GeoDataFrame,
) -> list[tuple[str, gpd.GeoDataFrame]]:
    if checkpoint.empty:
        return []
    checkpoint_bc = checkpoint.copy()
    if checkpoint_bc.crs is None:
        checkpoint_bc = checkpoint_bc.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint_bc = checkpoint_bc.to_crs(BC_ALBERS_EPSG)
    checkpoint_bc = checkpoint_bc.copy()
    checkpoint_bc["_orig_geom_area_sqm"] = checkpoint_bc.geometry.area.astype(float)
    lu_bc = lu_frame.copy()
    if lu_bc.crs is None:
        lu_bc = lu_bc.set_crs(BC_ALBERS_EPSG)
    else:
        lu_bc = lu_bc.to_crs(BC_ALBERS_EPSG)
    lu_bc = lu_bc.copy()
    lu_bc["_lu_name"] = (
        lu_bc.get("LANDSCAPE_UNIT_NAME", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    overlay = gpd.overlay(
        checkpoint_bc,
        lu_bc[["_lu_name", "geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if overlay.empty:
        return []
    overlay = overlay.loc[~overlay.geometry.is_empty].copy()
    clipped_area_sqm = overlay.geometry.area.astype(float)
    original_area_sqm = pd.to_numeric(
        overlay.get("_orig_geom_area_sqm", pd.Series(0.0, index=overlay.index)),
        errors="coerce",
    ).fillna(0.0)
    ratio = clipped_area_sqm / original_area_sqm.where(
        original_area_sqm > 0.0, other=1.0
    )
    ratio = ratio.where(original_area_sqm > 0.0, other=0.0).fillna(0.0).clip(lower=0.0)
    if "FEATURE_AREA_SQM" in overlay.columns:
        overlay["FEATURE_AREA_SQM"] = _scale_area_series_for_clip(
            overlay["FEATURE_AREA_SQM"], ratio=ratio, unit="sqm"
        )
    if "Shape_Area" in overlay.columns:
        overlay["Shape_Area"] = _scale_area_series_for_clip(
            overlay["Shape_Area"], ratio=ratio, unit="sqm"
        )
    if "POLYGON_AREA" in overlay.columns:
        overlay["POLYGON_AREA"] = _scale_area_series_for_clip(
            overlay["POLYGON_AREA"], ratio=ratio, unit="ha"
        )
    if "GEOMETRY_AREA" in overlay.columns:
        overlay["GEOMETRY_AREA"] = _scale_area_series_for_clip(
            overlay["GEOMETRY_AREA"], ratio=ratio, unit="ha"
        )
    if "AREA_HA" in overlay.columns:
        overlay["AREA_HA"] = _scale_area_series_for_clip(
            overlay["AREA_HA"], ratio=ratio, unit="ha"
        )
    if TSR_EFFECTIVE_AREA_SQM_COLUMN in overlay.columns:
        overlay[TSR_EFFECTIVE_AREA_SQM_COLUMN] = _scale_area_series_for_clip(
            overlay[TSR_EFFECTIVE_AREA_SQM_COLUMN], ratio=ratio, unit="sqm"
        )
    if "_stand_area_sqm" in overlay.columns:
        overlay["_stand_area_sqm"] = _scale_area_series_for_clip(
            overlay["_stand_area_sqm"], ratio=ratio, unit="sqm"
        )
    else:
        overlay["_stand_area_sqm"] = clipped_area_sqm
    overlay = _update_geometry_measure_columns(overlay)

    chunks: list[tuple[str, gpd.GeoDataFrame]] = []
    for lu_name, group in overlay.groupby("_lu_name", dropna=False):
        label = str(lu_name).strip() or "unnamed_lu"
        chunk = gpd.GeoDataFrame(
            group.drop(columns=["_lu_name"], errors="ignore").copy(),
            crs=BC_ALBERS_EPSG,
        )
        chunks.append((label, chunk))
    chunks.sort(key=lambda item: item[0])
    return chunks


def _group_landscape_unit_chunks(
    chunks: Sequence[tuple[str, gpd.GeoDataFrame]],
    *,
    bundle_count: int,
) -> list[dict[str, Any]]:
    if not chunks:
        return []
    resolved_bundle_count = max(1, min(int(bundle_count), len(chunks)))
    bundles: list[dict[str, Any]] = [
        {
            "bundle_index": index + 1,
            "bundle_label": f"worker_{index + 1:02d}",
            "total_area_ha": 0.0,
            "chunks": [],
        }
        for index in range(resolved_bundle_count)
    ]
    sorted_chunks = sorted(
        chunks,
        key=lambda item: float(_managed_area_ha(item[1])),
        reverse=True,
    )
    for lu_name, chunk in sorted_chunks:
        target = min(bundles, key=lambda item: float(item["total_area_ha"]))
        target["chunks"].append((lu_name, chunk))
        target["total_area_ha"] = float(target["total_area_ha"]) + float(
            _managed_area_ha(chunk)
        )
    return bundles


def _group_landscape_unit_chunk_records(
    chunk_records: Sequence[dict[str, Any]],
    *,
    bundle_count: int,
) -> list[dict[str, Any]]:
    if not chunk_records:
        return []
    resolved_bundle_count = max(1, min(int(bundle_count), len(chunk_records)))
    bundles: list[dict[str, Any]] = [
        {
            "bundle_index": index + 1,
            "bundle_label": f"worker_{index + 1:02d}",
            "total_area_ha": 0.0,
            "chunk_records": [],
        }
        for index in range(resolved_bundle_count)
    ]
    sorted_records = sorted(
        chunk_records,
        key=lambda item: float(item.get("area_ha", 0.0) or 0.0),
        reverse=True,
    )
    for record in sorted_records:
        target = min(bundles, key=lambda item: float(item["total_area_ha"]))
        target["chunk_records"].append(dict(record))
        target["total_area_ha"] = float(target["total_area_ha"]) + float(
            record.get("area_ha", 0.0) or 0.0
        )
    return bundles


def _materialize_checkpoint_landscape_unit_partitions(
    checkpoint: gpd.GeoDataFrame,
    *,
    checkpoint_path: Path,
    lu_frame: gpd.GeoDataFrame,
    selected_landscape_units: Sequence[str],
    instance_root: Path,
) -> list[dict[str, Any]]:
    partition_root = default_tsr_thlb_lu_partition_root(instance_root=instance_root)
    partition_root.mkdir(parents=True, exist_ok=True)
    lu_key = "|".join(
        str(value).strip() for value in selected_landscape_units if str(value).strip()
    )
    digest = hashlib.sha1(
        (f"{checkpoint_path.expanduser().resolve()}||{lu_key or 'all_lus'}").encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    partition_dir = partition_root / f"{checkpoint_path.stem}.{digest}"
    metadata_path = partition_dir / "partition_metadata.json"
    if metadata_path.exists():
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        records_raw = payload.get("chunk_records", [])
        if isinstance(records_raw, list):
            cached_records: list[dict[str, Any]] = []
            for item in records_raw:
                if not isinstance(item, dict):
                    continue
                path_value = str(item.get("chunk_path", "")).strip()
                if not path_value:
                    continue
                chunk_path = partition_dir / path_value
                if not chunk_path.exists():
                    continue
                cached_records.append(
                    {
                        "lu_name": str(item.get("lu_name", "")).strip(),
                        "chunk_path": chunk_path,
                        "area_ha": float(item.get("area_ha", 0.0) or 0.0),
                    }
                )
            if cached_records:
                cached_records.sort(
                    key=lambda item: str(item.get("lu_name", "")).strip()
                )
                return cached_records

    partition_dir.mkdir(parents=True, exist_ok=True)
    chunks = _clip_checkpoint_to_landscape_unit_chunks(checkpoint, lu_frame=lu_frame)
    records: list[dict[str, Any]] = []
    for index, (lu_name, chunk) in enumerate(chunks, start=1):
        slug = (
            re.sub(r"[^A-Za-z0-9]+", "_", lu_name).strip("_").lower()
            or f"lu_{index:03d}"
        )
        chunk_filename = f"{index:03d}_{slug}.feather"
        chunk_path = partition_dir / chunk_filename
        chunk.drop(columns=["_orig_geom_area_sqm"], errors="ignore").to_feather(
            chunk_path
        )
        area_ha = float(chunk.geometry.area.astype(float).sum() / 10000.0)
        records.append(
            {
                "lu_name": lu_name,
                "chunk_path": chunk_path,
                "area_ha": area_ha,
            }
        )
    metadata_payload = {
        "checkpoint_path": str(checkpoint_path.expanduser().resolve()),
        "selected_landscape_units": list(selected_landscape_units),
        "chunk_records": [
            {
                "lu_name": str(item["lu_name"]),
                "chunk_path": Path(str(item["chunk_path"])).name,
                "area_ha": float(item["area_ha"] or 0.0),
            }
            for item in records
        ],
    }
    metadata_path.write_text(
        json.dumps(metadata_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    records.sort(key=lambda item: str(item.get("lu_name", "")).strip())
    return records


def _write_tsr_thlb_parallel_progress(
    progress_path: Path,
    *,
    bundle_index: int,
    bundle_label: str,
    lu_names: Sequence[str],
    completed_lus: int,
    total_lus: int,
    current_lu: str | None,
    status: str,
    notes: Sequence[str] = (),
) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle_index": bundle_index,
        "bundle_label": bundle_label,
        "lu_names": list(lu_names),
        "completed_lus": int(completed_lus),
        "total_lus": int(total_lus),
        "fraction_complete": (
            float(completed_lus) / float(total_lus) if total_lus > 0 else 1.0
        ),
        "current_lu": current_lu,
        "status": status,
        "notes": [str(value).strip() for value in notes if str(value).strip()],
        "updated_utc": datetime.now(UTC).isoformat(),
    }
    progress_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )


def _auto_select_smoke_map_ids_for_parent_step(
    *,
    checkpoint: gpd.GeoDataFrame,
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    instance_root: Path,
    source_entry_map: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    max_candidate_tiles = 40
    linked_source_entry_ids = tuple(
        sorted(
            {
                str(value).strip()
                for item in compiled_steps
                for value in item.get("linked_source_entry_ids", ())
                if str(value).strip()
            }
        )
    )
    if not linked_source_entry_ids:
        linked_source_entry_ids = tuple(
            sorted(
                {
                    str(value).strip()
                    for value in parent_step.get("linked_source_entry_ids", ())
                    if str(value).strip()
                }
            )
        )
    if not linked_source_entry_ids:
        return _auto_select_smoke_map_ids(checkpoint)

    working = checkpoint.loc[
        checkpoint["MAP_ID"].notna() & checkpoint.geometry.notna()
    ].copy()
    if working.empty:
        return _auto_select_smoke_map_ids(checkpoint)
    working["_area_ha"] = working.geometry.area.astype(float) / 10000.0
    map_polys = (
        working[["MAP_ID", "geometry", "_area_ha"]]
        .dissolve(by="MAP_ID", aggfunc={"_area_ha": "sum"})
        .reset_index()
    )
    if map_polys.empty:
        return _auto_select_smoke_map_ids(checkpoint)

    source_artifact_paths = []
    for entry_id in linked_source_entry_ids:
        source_entry = source_entry_map.get(entry_id)
        if source_entry is None:
            continue
        artifact_path = _resolve_source_artifact_path(
            instance_root=instance_root,
            source_entry=source_entry,
        )
        if artifact_path is not None:
            source_artifact_paths.append(artifact_path)
    if not source_artifact_paths:
        return _auto_select_smoke_map_ids(checkpoint)

    scored: list[tuple[float, str, tuple[float, float, float, float]]] = []
    candidate_rows = map_polys.sort_values("_area_ha", ascending=False).head(
        max_candidate_tiles
    )
    for _idx, row in candidate_rows.iterrows():
        map_id = _normalize_map_id_token(row["MAP_ID"])
        if not map_id:
            continue
        minx, miny, maxx, maxy = map(float, row.geometry.bounds)
        bbox = (minx, miny, maxx, maxy)
        scored.append((float(row["_area_ha"]), map_id, bbox))
    scored.sort(key=lambda item: (-item[0], item[1]))

    for _area_ha, map_id, bbox in scored:
        hit_count = 0
        for artifact_path in source_artifact_paths:
            try:
                layer = gpd.read_file(artifact_path, engine="pyogrio", bbox=bbox)
            except Exception:
                continue
            if not layer.empty:
                hit_count += len(layer)
        if hit_count > 0:
            return (map_id,)
    return _auto_select_smoke_map_ids(checkpoint)


def _normalize_checkpoint_thlb_fact(
    checkpoint: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, str]:
    normalized = checkpoint.copy()
    stand_area_sqm = _resolve_effective_stand_area_sqm(normalized)
    normalized["_stand_area_sqm"] = stand_area_sqm
    signal_source = "default_one"

    if "thlb_fact" in normalized.columns:
        thlb_fact = normalized["thlb_fact"].fillna(0).astype(float)
        signal_source = "thlb_fact"
    elif "thlb_raw" in normalized.columns:
        thlb_fact = normalized["thlb_raw"].fillna(0).astype(float)
        if float(thlb_fact.max()) > 1.0:
            thlb_fact = thlb_fact / 100.0
        signal_source = "thlb_raw"
    elif "thlb_area" in normalized.columns:
        area_ha = stand_area_sqm / 10000.0
        with_area = area_ha.where(area_ha > 0, other=1.0)
        thlb_fact = normalized["thlb_area"].fillna(0).astype(float) / with_area
        signal_source = "thlb_area"
    elif "thlb" in normalized.columns:
        thlb_fact = normalized["thlb"].fillna(0).astype(float)
        signal_source = "thlb"
    else:
        thlb_fact = stand_area_sqm.map(lambda _value: 1.0)

    normalized["thlb_fact"] = thlb_fact.clip(lower=0.0, upper=1.0)
    return normalized, signal_source


def _resolve_union_geometry(exclusion_geometries: gpd.GeoDataFrame) -> Any | None:
    if exclusion_geometries.empty:
        return None
    series = exclusion_geometries.geometry
    if hasattr(series, "union_all"):
        return series.union_all()
    return series.unary_union


def _update_geometry_measure_columns(checkpoint: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    updated = checkpoint.copy()
    area_sqm = updated.geometry.area.astype(float)
    length_m = updated.geometry.length.astype(float)
    if "FEATURE_AREA_SQM" in updated.columns:
        updated["FEATURE_AREA_SQM"] = area_sqm
    if "POLYGON_AREA" in updated.columns:
        updated["POLYGON_AREA"] = area_sqm / 10000.0
    if "GEOMETRY_AREA" in updated.columns:
        updated["GEOMETRY_AREA"] = area_sqm / 10000.0
    if "Shape_Area" in updated.columns:
        updated["Shape_Area"] = area_sqm
    if "FEATURE_LENGTH_M" in updated.columns:
        updated["FEATURE_LENGTH_M"] = length_m
    if "Shape_Length" in updated.columns:
        updated["Shape_Length"] = length_m
    return updated


def _resolve_effective_stand_area_sqm(checkpoint: gpd.GeoDataFrame) -> pd.Series:
    if TSR_EFFECTIVE_AREA_SQM_COLUMN in checkpoint.columns:
        effective = pd.to_numeric(
            checkpoint[TSR_EFFECTIVE_AREA_SQM_COLUMN], errors="coerce"
        ).fillna(0.0)
        return effective.clip(lower=0.0)
    return _resolve_canonical_stand_area_sqm(checkpoint)


def _resolve_canonical_stand_area_sqm(checkpoint: gpd.GeoDataFrame) -> pd.Series:
    if "FEATURE_AREA_SQM" in checkpoint.columns:
        feature_area = pd.to_numeric(
            checkpoint["FEATURE_AREA_SQM"], errors="coerce"
        ).fillna(0.0)
        return feature_area.clip(lower=0.0)
    if "POLYGON_AREA" in checkpoint.columns:
        polygon_area = pd.to_numeric(
            checkpoint["POLYGON_AREA"], errors="coerce"
        ).fillna(0.0)
        if float(polygon_area.max()) <= 1000.0:
            polygon_area = polygon_area * 10000.0
        return polygon_area.clip(lower=0.0)
    return checkpoint.geometry.area.astype(float)


def _initialize_reconstructed_land_base(
    checkpoint: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, str]:
    if "FOR_MGMT_LAND_BASE_IND" in checkpoint.columns:
        reconstructed = initialize_aflb_land_base_records(
            f_table=checkpoint,
            required_bclcs_level_2="T",
            required_for_mgmt_land_base="Y",
            excluded_bec_zones=(),
        )
        thlb_binary = reconstructed.geometry.map(lambda _value: 1.0).astype(float)
        signal_source = "checkpoint1_aflb_initialization"
    else:
        reconstructed = checkpoint.copy()
        thlb_binary = reconstructed.geometry.map(lambda _value: 1.0).astype(float)
        signal_source = "default_one"
    if (
        "FEATURE_ID" in reconstructed.columns
        and "SOURCE_FEATURE_ID" not in reconstructed.columns
    ):
        reconstructed["SOURCE_FEATURE_ID"] = reconstructed["FEATURE_ID"]
    reconstructed["thlb_fact"] = thlb_binary
    reconstructed["thlb"] = thlb_binary.astype(int)
    reconstructed = _update_geometry_measure_columns(reconstructed)
    reconstructed["_row_id"] = range(len(reconstructed))
    reconstructed["_stand_area_sqm"] = _resolve_effective_stand_area_sqm(reconstructed)
    return reconstructed, signal_source


def _assign_fragment_feature_ids(checkpoint: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    updated = checkpoint.copy().reset_index(drop=True)
    updated["_row_id"] = range(len(updated))
    if "FEATURE_ID" in updated.columns:
        updated["FEATURE_ID"] = updated.index + 1
    updated = _update_geometry_measure_columns(updated)
    updated["_stand_area_sqm"] = _resolve_effective_stand_area_sqm(updated)
    return updated


def _fragment_binary_exclusion_step(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
    update_aflb_flag_on_exclusion: bool = True,
) -> tuple[gpd.GeoDataFrame, int, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return checkpoint, 0, 0.0
    active = checkpoint.loc[checkpoint["thlb_fact"] > 0].copy()
    if active.empty:
        return checkpoint, 0, 0.0
    candidate_indices = active.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return checkpoint, 0, 0.0
    candidate = active.iloc[unique_indices].copy()
    mask_geometry = _resolve_union_geometry(exclusion_geometries)
    if mask_geometry is None or getattr(mask_geometry, "is_empty", False):
        return checkpoint, 0, 0.0

    untouched = checkpoint.drop(candidate.index).copy()
    mask_frame = gpd.GeoDataFrame(geometry=[mask_geometry], crs=BC_ALBERS_EPSG)
    intersections = gpd.overlay(
        candidate,
        mask_frame,
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return checkpoint, 0, 0.0
    differences = gpd.overlay(
        candidate,
        mask_frame,
        how="difference",
        keep_geom_type=False,
    )

    intersections = intersections.copy()
    intersections["thlb_fact"] = 0.0
    intersections["thlb"] = 0
    if (
        update_aflb_flag_on_exclusion
        and "FOR_MGMT_LAND_BASE_IND" in intersections.columns
    ):
        intersections["FOR_MGMT_LAND_BASE_IND"] = "N"

    if not differences.empty:
        differences = differences.copy()
        differences["thlb_fact"] = 1.0
        differences["thlb"] = 1

    affected_area_ha = float(intersections.geometry.area.sum() / 10000.0)
    affected_fragment_count = int(len(intersections))
    rebuilt = gpd.GeoDataFrame(
        pd.concat([untouched, differences, intersections], ignore_index=True),
        crs=BC_ALBERS_EPSG,
    )
    rebuilt = rebuilt.loc[~rebuilt.geometry.is_empty].copy()
    rebuilt = _assign_fragment_feature_ids(rebuilt)
    return rebuilt, affected_fragment_count, affected_area_ha


def _apply_binary_stand_exclusion(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, int, float, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return checkpoint, 0, 0.0, 0.0
    active = checkpoint.loc[checkpoint["thlb_fact"] > 0].copy()
    if active.empty:
        return checkpoint, 0, 0.0, 0.0
    candidate_indices = active.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return checkpoint, 0, 0.0, 0.0
    candidate = active.iloc[unique_indices].copy()
    mask_geometry = _resolve_union_geometry(exclusion_geometries)
    if mask_geometry is None or getattr(mask_geometry, "is_empty", False):
        return checkpoint, 0, 0.0, 0.0
    representative = candidate.geometry.representative_point()
    selected_row_ids = candidate.loc[
        representative.intersects(mask_geometry), "_row_id"
    ]
    if selected_row_ids.empty:
        return checkpoint, 0, 0.0, 0.0
    exclude_mask = checkpoint["_row_id"].isin(selected_row_ids.tolist())
    updated = checkpoint.copy()
    updated.loc[exclude_mask, "thlb_fact"] = 0.0
    updated.loc[exclude_mask, "thlb"] = 0
    affected_area_ha = float(
        updated.loc[exclude_mask, "_stand_area_sqm"].sum() / 10000.0
    )
    overlap_area_ha = affected_area_ha
    return updated, int(exclude_mask.sum()), affected_area_ha, overlap_area_ha


def _compute_legacy_reference_managed_area_ha(
    *,
    instance_root: Path,
    checkpoint_path: Path,
) -> float | None:
    latest_checkpoint = _find_tsr_checkpoint_path(
        instance_root=instance_root, mode="latest"
    )
    if latest_checkpoint == checkpoint_path:
        return None
    comparison = _load_checkpoint_geodataframe(latest_checkpoint)
    if not {"thlb_fact", "thlb_raw", "thlb_area", "thlb"}.intersection(
        comparison.columns
    ):
        return None
    comparison["_row_id"] = range(len(comparison))
    comparison, _signal_source = _normalize_checkpoint_thlb_fact(comparison)
    return _managed_area_ha(comparison)


def _extract_tsr_reported_thlb_area_ha(
    *,
    instance_root: Path,
    recipe: TsrThlbNetdownRecipeRecord,
) -> float | None:
    return _extract_tsr_reported_land_base_benchmarks(
        instance_root=instance_root,
        recipe=recipe,
    ).get("thlb_area_ha")


def _extract_tsr_reported_land_base_benchmarks(
    *,
    instance_root: Path,
    recipe: TsrThlbNetdownRecipeRecord,
) -> dict[str, float]:
    selected_paths = tuple(
        str(path).strip()
        for path in recipe.recipe_contract.get("selected_document_paths", ())
        if str(path).strip()
    )
    if not selected_paths:
        return {}
    try:
        from pypdf import PdfReader
    except Exception:  # pragma: no cover - dependency seam
        return {}
    from femic.user_config import default_femic_tsr_corpus_root

    corpus_root = default_femic_tsr_corpus_root()
    target_document = corpus_root / "tsa" / recipe.tsa.tsa_id / Path(selected_paths[0])
    if not target_document.exists():
        return {}
    try:
        reader = PdfReader(str(target_document))
    except Exception:  # pragma: no cover - runtime seam
        return {}

    patterns = {
        "aflb_area_ha": re.compile(
            r"(?:Analysis forest land base|AFLB)\s+([\d,]+)",
            flags=re.IGNORECASE,
        ),
        "thlb_area_ha": re.compile(
            r"(?:Timber harvesting land\s+base|THLB)\s+([\d,]+)",
            flags=re.IGNORECASE,
        ),
        "long_term_thlb_area_ha": re.compile(
            r"Long-term THLB\s+([\d,]+)",
            flags=re.IGNORECASE,
        ),
    }
    benchmarks: dict[str, float] = {}
    for page in reader.pages:
        text = page.extract_text() or ""
        for key, pattern in patterns.items():
            for match in pattern.finditer(text):
                value = match.group(1)
                if value:
                    benchmarks[key] = float(value.replace(",", ""))
    if "long_term_thlb_area_ha" in benchmarks:
        benchmarks["thlb_area_ha"] = benchmarks["long_term_thlb_area_ha"]
    return benchmarks


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f} ({value * 100.0:.2f}%)"


def _lookup_override_for_source_entry(
    *,
    source_entry: dict[str, Any],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> TsrSourceLayerOverrideEntry | None:
    recommended_query = (
        str(source_entry.get("recommended_query", "")).strip().casefold()
    )
    if not recommended_query:
        return None
    return override_entries.get(recommended_query)


def _describe_thlb_step_logic(step: dict[str, Any]) -> str:
    normalized_action = str(step.get("normalized_action", "")).strip()
    spatial_mode = str(step.get("spatial_application_mode", "")).strip()
    normalized_subject = str(step.get("normalized_subject", "")).strip()
    normalized_predicate = str(step.get("normalized_predicate", "")).strip()
    if normalized_action == "use_land_base":
        return "Use the AFLB-style initialized land base as the THLB starting universe."
    if normalized_action == "no_deduction":
        return "Apply no THLB deduction for this rule."
    if normalized_action == "exclude":
        if spatial_mode == "fragment_overlay":
            return (
                "Overlay the linked polygon layers onto the working land base, fragment intersected "
                "geometry, and assign binary THLB {0,1} so excluded fragments are 0 and retained "
                "fragments remain 1."
            )
        if spatial_mode == "stand_binary_majority":
            return (
                "Apply the current coarse stand-binary fallback: whole stands are netted down when "
                "the exclusion mask trips the explicit stand-binary approximation."
            )
        return (
            "Exclude the linked polygons from THLB where they intersect the working land base; "
            "the exact execution mode depends on available data and current implementation support."
        )
    if normalized_action == "aspatial_reduction":
        return (
            "Apply a final aspatial THLB reduction of the TSR-cited magnitude after the spatially "
            "executable steps have completed."
        )
    if normalized_action in {
        "section_heading",
        "definition",
        "increase_conditions",
        "decrease_conditions",
    }:
        return "Context/interpretation row only; no executable THLB logic is applied automatically."
    logic_parts = [part for part in (normalized_subject, normalized_predicate) if part]
    if logic_parts:
        return " ".join(logic_parts)
    return "No executable logic has been normalized for this row yet."


def _format_thlb_step_markdown(
    *,
    step: dict[str, Any],
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
    heading_level: str = "###",
    heading_index_label: str | None = None,
) -> list[str]:
    label = str(step.get("label", "")).strip() or str(step.get("step_id", "")).strip()
    logic_mode = "femic_core"
    heading_prefix = (
        heading_index_label
        if heading_index_label is not None
        else str(int(step.get("order_index", 0)))
    )
    lines = [
        f"{heading_level} {heading_prefix}. {label}",
        "",
        f"- Step id: `{step.get('step_id', '')}`",
        f"- Kind: `{step.get('step_kind', '')}`",
        f"- Stage: `{step.get('stage_label', step.get('land_base_stage', ''))}`",
        f"- Execution class: `{step.get('execution_class', '')}`",
        f"- Run status: `{step.get('run_status', step.get('step_status', 'unknown'))}`",
        f"- TSR provenance: `{step.get('provenance_id', '')}`",
    ]
    page_number = step.get("page_number")
    if page_number:
        lines.append(f"- TSR page: `{page_number}`")
    raw_text = str(step.get("raw_text", "")).strip()
    if raw_text:
        lines.append(f"- TSR text: `{raw_text}`")
    lines.append(f"- FEMIC proposed logic: {_describe_thlb_step_logic(step)}")

    linked_source_ids = [
        str(value).strip()
        for value in step.get("linked_source_entry_ids", ())
        if str(value).strip()
    ]
    if linked_source_ids:
        lines.append("- Linked source layers:")
        for entry_id in linked_source_ids:
            source_entry = source_entry_map.get(entry_id)
            if source_entry is None:
                lines.append(
                    f"  - `{entry_id}`: missing from `source_layers.recipe.yaml`"
                )
                continue
            lines.append(
                "  - "
                + f"`{entry_id}` | query=`{source_entry.get('recommended_query', '')}` | "
                + f"status=`{source_entry.get('current_public_status', '')}` | "
                + f"strategy=`{source_entry.get('acquisition_strategy', '')}`"
            )
            artifact_path = str(source_entry.get("artifact_path", "")).strip()
            if artifact_path:
                lines.append(f"    - artifact: `{artifact_path}`")
            matched_by = str(source_entry.get("matched_by", "")).strip()
            if matched_by:
                lines.append(f"    - matched by: `{matched_by}`")
            top_match_title = str(source_entry.get("top_match_title", "")).strip()
            if top_match_title:
                lines.append(f"    - top match: `{top_match_title}`")
            override_entry = _lookup_override_for_source_entry(
                source_entry=source_entry,
                override_entries=override_entries,
            )
            if override_entry is not None and override_entry.override_kind:
                logic_mode = "user_overlay"
                lines.append(
                    "    - user-overlay logic mode: "
                    + f"`{override_entry.override_kind}` via `config/tsr/source_layer_overrides.yaml`"
                )
                if override_entry.override_value:
                    lines.append(
                        f"    - override value: `{override_entry.override_value}`"
                    )
                if override_entry.notes:
                    lines.append(f"    - override notes: {override_entry.notes}")

    lines.append(f"- Logic mode: `{logic_mode}`")
    missing_source_ids = [
        str(value).strip()
        for value in step.get("missing_source_entry_ids", ())
        if str(value).strip()
    ]
    if missing_source_ids:
        lines.append("- Missing linked source entries:")
        for entry_id in missing_source_ids:
            lines.append(f"  - `{entry_id}`")

    run_notes = [
        str(note).strip() for note in step.get("run_notes", ()) if str(note).strip()
    ]
    if run_notes:
        lines.append("- Run notes:")
        for note in run_notes:
            lines.append(f"  - {note}")
    lines.append("")
    return lines


def _format_thlb_parent_step_markdown(
    *,
    parent_step: dict[str, Any],
    compiled_step_map: dict[str, list[dict[str, Any]]],
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> list[str]:
    label = (
        str(parent_step.get("parent_label", "")).strip()
        or str(parent_step.get("parent_step_id", "")).strip()
    )
    row_order = int(parent_step.get("row_order", 0))
    lines = [
        f"### {row_order}. {label}",
        "",
        f"- Parent step id: `{parent_step.get('parent_step_id', '')}`",
        f"- Stage: `{parent_step.get('stage_label', parent_step.get('land_base_stage', ''))}`",
        f"- Execution class: `{parent_step.get('execution_class', '')}`",
        f"- Ratchet state: `{_infer_thlb_parent_step_ratchet_state(parent_step)}`",
        f"- Table provenance: `{parent_step.get('table_provenance', '')}`",
    ]
    benchmark_marginal = parent_step.get("benchmark_marginal_area_ha")
    if benchmark_marginal is not None:
        lines.append(
            f"- Benchmark marginal deduction: `{float(benchmark_marginal):.3f} ha`"
        )
    benchmark_cumulative = parent_step.get("benchmark_cumulative_area_ha")
    if benchmark_cumulative is not None:
        lines.append(
            f"- Benchmark cumulative remaining area: `{float(benchmark_cumulative):.3f} ha`"
        )
    if bool(parent_step.get("approved", False)):
        lines.append("- Approval: `soft-approved`")
        approval_scope = str(parent_step.get("approval_scope", "")).strip()
        if approval_scope:
            lines.append(f"- Approval scope: `{approval_scope}`")
        approval_note = str(parent_step.get("approval_note", "")).strip()
        if approval_note:
            lines.append(f"- Approval note: {approval_note}")
        approved_utc = str(parent_step.get("approved_utc", "")).strip()
        if approved_utc:
            lines.append(f"- Approved UTC: `{approved_utc}`")
        approved_by = str(parent_step.get("approved_by", "")).strip()
        if approved_by:
            lines.append(f"- Approved by: `{approved_by}`")
    ratchet_note = str(parent_step.get("ratchet_note", "")).strip()
    if ratchet_note:
        lines.append(f"- Ratchet note: {ratchet_note}")
    subsection_number = str(parent_step.get("subsection_number", "")).strip()
    subsection_title = str(parent_step.get("subsection_title", "")).strip()
    if subsection_number or subsection_title:
        lines.append(
            "- Supporting prose section: "
            + f"`{_normalize_whitespace(' '.join(part for part in (subsection_number, subsection_title) if part))}`"
        )
    supporting_provenance_ids = [
        str(value).strip()
        for value in parent_step.get("supporting_provenance_ids", ())
        if str(value).strip()
    ]
    if supporting_provenance_ids:
        lines.append("- Supporting prose provenance:")
        for provenance_id in supporting_provenance_ids:
            lines.append(f"  - `{provenance_id}`")
    draft_subrules = [
        dict(item)
        for item in parent_step.get("draft_subrules", ())
        if isinstance(item, dict)
    ]
    if draft_subrules:
        lines.append("- Draft subrules:")
        for subrule in draft_subrules:
            lines.append(
                "  - "
                + f"`{subrule.get('subrule_id', '')}` | summary=`{subrule.get('human_summary', '')}` | "
                + f"operation=`{subrule.get('candidate_operation_type', '')}` | "
                + f"review=`{subrule.get('review_status', '')}`"
            )
            candidate_layers = [
                str(value).strip()
                for value in subrule.get("candidate_layers", ())
                if str(value).strip()
            ]
            if candidate_layers:
                lines.append(
                    "    - candidate layers: "
                    + ", ".join(f"`{layer}`" for layer in candidate_layers)
                )
            candidate_fields = [
                str(value).strip()
                for value in subrule.get("candidate_fields", ())
                if str(value).strip()
            ]
            if candidate_fields:
                lines.append(
                    "    - candidate fields: "
                    + ", ".join(f"`{field}`" for field in candidate_fields)
                )
            candidate_values = [
                str(value).strip()
                for value in subrule.get("candidate_values", ())
                if str(value).strip()
            ]
            if candidate_values:
                lines.append(
                    "    - candidate values: "
                    + ", ".join(f"`{value}`" for value in candidate_values)
                )
            field_mapping_notes = [
                str(value).strip()
                for value in subrule.get("field_mapping_notes", ())
                if str(value).strip()
            ]
            if field_mapping_notes:
                lines.append("    - field/value mapping notes:")
                for note in field_mapping_notes:
                    lines.append(f"      - {note}")
    compiled_steps = compiled_step_map.get(
        str(parent_step.get("parent_step_id", "")), []
    )
    if compiled_steps:
        status_counts: dict[str, int] = {}
        for compiled_step in compiled_steps:
            status = (
                str(
                    compiled_step.get(
                        "run_status", compiled_step.get("step_status", "unknown")
                    )
                ).strip()
                or "unknown"
            )
            status_counts[status] = status_counts.get(status, 0) + 1
        lines.append(
            "- Current compiled status summary: "
            + ", ".join(
                f"`{status}`={count}" for status, count in sorted(status_counts.items())
            )
        )
    last_run_status = str(parent_step.get("last_notebook_run_status", "")).strip()
    if last_run_status:
        lines.append(f"- Last notebook run status: `{last_run_status}`")
        last_removed_area_ha = parent_step.get("last_removed_area_ha")
        if last_removed_area_ha is not None:
            lines.append(
                f"- Last notebook removed area: `{float(last_removed_area_ha):.3f} ha`"
            )
        last_remaining_area_ha = parent_step.get("last_remaining_area_ha")
        if last_remaining_area_ha is not None:
            lines.append(
                f"- Last notebook remaining area: `{float(last_remaining_area_ha):.3f} ha`"
            )
        last_result_json_path = str(
            parent_step.get("last_notebook_run_result_json_path", "")
        ).strip()
        if last_result_json_path:
            lines.append(f"- Last notebook result JSON: `{last_result_json_path}`")
    if compiled_steps:
        lines.append("- Compiled logic:")
        lines.append("")
        for compiled_index, compiled_step in enumerate(compiled_steps, start=1):
            lines.extend(
                _format_thlb_step_markdown(
                    step=compiled_step,
                    source_entry_map=source_entry_map,
                    override_entries=override_entries,
                    heading_level="####",
                    heading_index_label=f"{row_order}.{compiled_index}",
                )
            )
    else:
        lines.extend(["- Compiled logic: `not yet compiled`", ""])
    return lines


def _infer_thlb_parent_step_ratchet_state(parent_step: dict[str, Any]) -> str:
    explicit = str(parent_step.get("ratchet_state", "")).strip()
    if explicit:
        return explicit
    if str(parent_step.get("parent_kind", "")).strip() == "milestone":
        return "milestone_node"
    if bool(parent_step.get("approved", False)):
        return "approved"
    last_run_status = str(parent_step.get("last_notebook_run_status", "")).strip()
    if last_run_status in {"applied", "applied_noop", "manual_review_required"}:
        return "benchmarked"
    if last_run_status:
        return "smoke_runnable"
    draft_subrules = [
        item for item in parent_step.get("draft_subrules", ()) if isinstance(item, dict)
    ]
    compiled_logic = [
        item for item in parent_step.get("compiled_logic", ()) if isinstance(item, dict)
    ]
    if compiled_logic:
        return "compiled"
    if draft_subrules:
        return "drafted"
    return "translated"


_THLB_PARENT_STEP_PRESERVED_METADATA_KEYS = (
    "approved",
    "approval_scope",
    "approval_note",
    "approved_utc",
    "approved_by",
    "ratchet_state",
    "ratchet_note",
    "last_notebook_run_status",
    "last_notebook_run_result_json_path",
    "last_notebook_run_output_path",
    "last_selected_map_ids",
    "last_selected_landscape_units",
    "last_input_area_ha",
    "last_removed_area_ha",
    "last_remaining_area_ha",
    "last_benchmark_marginal_delta_ha",
    "last_benchmark_cumulative_delta_ha",
)


def _merge_preserved_thlb_parent_step_metadata(
    *,
    existing_parent_steps: Sequence[dict[str, Any]],
    built_parent_steps: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_by_id = {
        str(item.get("parent_step_id", "")).strip(): dict(item)
        for item in existing_parent_steps
        if isinstance(item, dict) and str(item.get("parent_step_id", "")).strip()
    }
    merged: list[dict[str, Any]] = []
    for parent_step in built_parent_steps:
        updated = dict(parent_step)
        existing = existing_by_id.get(str(updated.get("parent_step_id", "")).strip())
        if existing is not None:
            for key in _THLB_PARENT_STEP_PRESERVED_METADATA_KEYS:
                if key in existing:
                    updated[key] = existing[key]
        updated["ratchet_state"] = _infer_thlb_parent_step_ratchet_state(updated)
        merged.append(updated)
    return merged


def _build_tsr_thlb_status_report_markdown(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    recipe_relative_path: str,
    checkpoint_relative_path: str,
    output_relative_path: str,
    audit_relative_path: str,
    execution_mode: str,
    baseline_signal: str,
    selected_map_ids: tuple[str, ...],
    input_area_ha: float,
    baseline_managed_area_ha: float,
    final_managed_area_ha: float,
    legacy_reference_managed_area_ha: float | None,
    tsr_reported_aflb_area_ha: float | None,
    tsr_reported_thlb_area_ha: float | None,
    outcome_counts: dict[str, int],
    step_count: int,
    generated_utc: str,
    runtime_report_relative_path: str,
    applied_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> str:
    input_to_baseline_ratio = _safe_ratio(baseline_managed_area_ha, input_area_ha)
    baseline_to_final_ratio = _safe_ratio(
        final_managed_area_ha, baseline_managed_area_ha
    )
    input_to_final_ratio = _safe_ratio(final_managed_area_ha, input_area_ha)
    tsr_aflb_to_thlb_ratio = (
        _safe_ratio(tsr_reported_thlb_area_ha, tsr_reported_aflb_area_ha)
        if tsr_reported_aflb_area_ha is not None
        and tsr_reported_thlb_area_ha is not None
        else None
    )
    compiled_step_map: dict[str, list[dict[str, Any]]] = {}
    for step in applied_steps:
        parent_step_id = str(step.get("parent_step_id", "")).strip()
        if parent_step_id:
            compiled_step_map.setdefault(parent_step_id, []).append(step)
    parent_stage_groups: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _THLB_STAGE_ORDER
    }
    milestone_parent_steps: list[dict[str, Any]] = []
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_kind", "")) == "milestone":
            milestone_parent_steps.append(dict(parent_step))
            continue
        stage = str(parent_step.get("land_base_stage", "context"))
        if stage not in parent_stage_groups:
            stage = "context"
        parent_stage_groups[stage].append(dict(parent_step))
    flat_stage_groups: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _THLB_STAGE_ORDER
    }
    for step in applied_steps:
        stage = str(step.get("land_base_stage", "context"))
        if stage not in flat_stage_groups:
            stage = "context"
        flat_stage_groups[stage].append(step)
    lines = [
        f"# THLB Netdown Status Report: TSA {recipe.tsa.tsa_code} ({recipe.tsa.tsa_name})",
        "",
        f"- Generated UTC: `{generated_utc}`",
        f"- Execution mode: `{execution_mode}`",
        f"- Baseline signal: `{baseline_signal}`",
        f"- Recipe path: `{recipe_relative_path}`",
        f"- Checkpoint input: `{checkpoint_relative_path}`",
        f"- Output checkpoint: `{output_relative_path}`",
        f"- Audit JSON: `{audit_relative_path}`",
        f"- Runtime history copy: `{runtime_report_relative_path}`",
        "",
        "## Scope",
        "",
        f"- Selected MAP_ID subset: `{', '.join(selected_map_ids) if selected_map_ids else 'full input'}`",
        f"- Step count: `{step_count}`",
        "",
        "## Backbone Summary",
        "",
        f"- Input checkpoint area: `{input_area_ha:.3f} ha`",
        f"- GLB / current input proxy: `{input_area_ha:.3f} ha`",
        f"- AFLB / baseline managed area: `{baseline_managed_area_ha:.3f} ha`",
        "- LHLB current: `not yet materialized separately in the current runner`",
        f"- THLB / final managed area: `{final_managed_area_ha:.3f} ha`",
    ]
    if legacy_reference_managed_area_ha is not None:
        lines.append(
            f"- Legacy raster THLB reference: `{legacy_reference_managed_area_ha:.3f} ha`"
        )
    if tsr_reported_aflb_area_ha is not None:
        lines.append(
            f"- TSR reported AFLB benchmark: `{tsr_reported_aflb_area_ha:.3f} ha`"
        )
    if tsr_reported_thlb_area_ha is not None:
        lines.append(
            f"- TSR reported THLB benchmark: `{tsr_reported_thlb_area_ha:.3f} ha`"
        )

    lines.extend(
        [
            "",
            "## Ratios",
            "",
            f"- GLB:AFLB current proxy = `{_format_ratio(input_to_baseline_ratio)}`",
            "- AFLB:LHLB current = `n/a yet`",
            f"- AFLB:THLB current = `{_format_ratio(baseline_to_final_ratio)}`",
            f"- GLB:THLB current proxy = `{_format_ratio(input_to_final_ratio)}`",
        ]
    )
    if tsr_aflb_to_thlb_ratio is not None:
        lines.append(f"- TSR AFLB:THLB = `{_format_ratio(tsr_aflb_to_thlb_ratio)}`")

    lines.extend(["", "## Outcomes", ""])
    for outcome, count in outcome_counts.items():
        lines.append(f"- `{outcome}`: `{count}`")

    lines.extend(
        [
            "",
            "## Locking / Convergence",
            "",
            "- AFLB lock state: `unlocked`",
            "- THLB lock state: `unlocked`",
            "- Lock dependency: cutting the AFLB lock automatically invalidates the THLB lock because THLB is downstream from the AFLB universe definition.",
            "- Current note: FEMIC now records benchmark ratios and runtime history for convergence review, but explicit user lock/cut-lock controls are not implemented yet.",
            "",
            "## Interpretation",
            "",
            "- Non-AFLB polygons are excluded from the reconstruction universe before THLB logic applies.",
            "- Non-THLB polygons or fragments remain inside that working universe and are assigned THLB state downstream from AFLB initialization.",
            "- GLB -> AFLB rows define the modeled universe, AFLB -> LHLB rows define legal harvestability, and LHLB -> THLB rows define projected operational harvestability.",
            "- AU/VDYP-oriented filters are not assumed to be valid THLB filters unless the TSR logic says so explicitly.",
            "- Legacy raster THLB values are reference-only in reconstructed mode.",
        ]
    )
    if milestone_parent_steps:
        lines.extend(["", "## Backbone Milestones", ""])
        for parent_step in milestone_parent_steps:
            label = str(parent_step.get("parent_label", "")).strip()
            stage_label = str(
                parent_step.get("stage_label", parent_step.get("land_base_stage", ""))
            ).strip()
            benchmark_cumulative = parent_step.get("benchmark_cumulative_area_ha")
            if benchmark_cumulative is None:
                benchmark_text = "benchmark not parsed"
            else:
                benchmark_text = f"{float(benchmark_cumulative):.3f} ha"
            lines.append(
                f"- `{label}` | stage=`{stage_label}` | benchmark remaining area=`{benchmark_text}`"
            )
    lines.extend(["", "## Stage-by-Stage THLB Steps", ""])
    if recipe.parent_steps:
        for stage in _THLB_STAGE_ORDER:
            parent_steps_for_stage = parent_stage_groups.get(stage, [])
            if not parent_steps_for_stage:
                continue
            lines.append(f"### {_THLB_STAGE_LABELS[stage]}")
            lines.append("")
            for parent_step in parent_steps_for_stage:
                lines.extend(
                    _format_thlb_parent_step_markdown(
                        parent_step=parent_step,
                        compiled_step_map=compiled_step_map,
                        source_entry_map=source_entry_map,
                        override_entries=override_entries,
                    )
                )
    else:
        for stage in _THLB_STAGE_ORDER:
            steps_for_stage = flat_stage_groups.get(stage, [])
            if not steps_for_stage:
                continue
            lines.append(f"### {_THLB_STAGE_LABELS[stage]}")
            lines.append("")
            for step in steps_for_stage:
                lines.extend(
                    _format_thlb_step_markdown(
                        step=step,
                        source_entry_map=source_entry_map,
                        override_entries=override_entries,
                    )
                )
    return "\n".join(lines) + "\n"


def _build_tsr_thlb_recipe_build_report_markdown(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    recipe_relative_path: str,
    source_layer_recipe_relative_path: str,
    generated_utc: str,
    runtime_report_relative_path: str,
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> str:
    compiled_step_map: dict[str, list[dict[str, Any]]] = {}
    for step in recipe.steps:
        parent_step_id = str(step.get("parent_step_id", "")).strip()
        if parent_step_id:
            compiled_step_map.setdefault(parent_step_id, []).append(dict(step))
    parent_stage_groups: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _THLB_STAGE_ORDER
    }
    milestone_parent_steps: list[dict[str, Any]] = []
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_kind", "")) == "milestone":
            milestone_parent_steps.append(dict(parent_step))
            continue
        stage = str(parent_step.get("land_base_stage", "context"))
        if stage not in parent_stage_groups:
            stage = "context"
        parent_stage_groups[stage].append(dict(parent_step))
    lines = [
        f"# THLB Recipe Build Report: TSA {recipe.tsa.tsa_code} ({recipe.tsa.tsa_name})",
        "",
        f"- Generated UTC: `{generated_utc}`",
        "- Report mode: `recipe_build`",
        f"- THLB recipe path: `{recipe_relative_path}`",
        f"- Source-layer recipe path: `{source_layer_recipe_relative_path}`",
        f"- Runtime history copy: `{runtime_report_relative_path}`",
        "",
        "## Scope",
        "",
        f"- Parent step count: `{len(recipe.parent_steps)}`",
        f"- Compiled step count: `{len(recipe.steps)}`",
    ]
    selected_document_paths = [
        str(value).strip()
        for value in recipe.recipe_contract.get("selected_document_paths", ())
        if str(value).strip()
    ]
    if selected_document_paths:
        lines.append("- Selected TSR documents:")
        for relative_path in selected_document_paths:
            lines.append(f"  - `{relative_path}`")
    stage_counts = Counter(
        str(parent_step.get("land_base_stage", "context"))
        for parent_step in recipe.parent_steps
    )
    lines.extend(
        [
            "",
            "## Stage Counts",
            "",
            f"- `GLB -> AFLB`: `{stage_counts.get('glb_to_aflb', 0)}`",
            f"- `AFLB -> LHLB`: `{stage_counts.get('aflb_to_lhlb', 0)}`",
            f"- `LHLB -> THLB`: `{stage_counts.get('lhlb_to_thlb', 0)}`",
            f"- `Reference targets`: `{stage_counts.get('reference_target', 0)}`",
            f"- `Context`: `{stage_counts.get('context', 0)}`",
            "",
            "## Backbone Milestones",
            "",
        ]
    )
    if milestone_parent_steps:
        for parent_step in milestone_parent_steps:
            label = str(parent_step.get("parent_label", "")).strip()
            stage_label = str(
                parent_step.get("stage_label", parent_step.get("land_base_stage", ""))
            ).strip()
            benchmark_cumulative = parent_step.get("benchmark_cumulative_area_ha")
            if benchmark_cumulative is None:
                benchmark_text = "benchmark not parsed"
            else:
                benchmark_text = f"{float(benchmark_cumulative):.3f} ha"
            lines.append(
                f"- `{label}` | stage=`{stage_label}` | benchmark remaining area=`{benchmark_text}`"
            )
    else:
        lines.append("- No milestone rows parsed.")
    lines.extend(
        [
            "",
            "## Stage-by-Stage THLB Steps",
            "",
        ]
    )
    for stage in _THLB_STAGE_ORDER:
        parent_steps_for_stage = parent_stage_groups.get(stage, [])
        if not parent_steps_for_stage:
            continue
        lines.append(f"### {_THLB_STAGE_LABELS[stage]}")
        lines.append("")
        for parent_step in parent_steps_for_stage:
            lines.extend(
                _format_thlb_parent_step_markdown(
                    parent_step=parent_step,
                    compiled_step_map=compiled_step_map,
                    source_entry_map=source_entry_map,
                    override_entries=override_entries,
                )
            )
    return "\n".join(lines) + "\n"


def _load_source_recipe_entry_map(
    source_recipe: TsrSourceLayersRecipeRecord,
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in source_recipe.entries:
        entry_id = str(entry.get("entry_id", "")).strip()
        if entry_id:
            index[entry_id] = dict(entry)
    return index


def _load_tsr_thlb_recipe_context(
    recipe_path: Path,
) -> tuple[
    TsrThlbNetdownRecipeRecord,
    Path,
    TsrSourceLayersRecipeRecord,
    dict[str, dict[str, Any]],
    dict[str, TsrSourceLayerOverrideEntry],
]:
    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_thlb_netdown_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    overrides_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_overrides_path
    )
    return (
        recipe,
        instance_root,
        source_recipe,
        _load_source_recipe_entry_map(source_recipe),
        _load_override_map(overrides_path),
    )


def _current_thlb_lock_state(
    recipe_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    current = recipe_contract.get("lock_state")
    if not isinstance(current, dict):
        current = {}
    normalized: dict[str, dict[str, Any]] = {}
    for scope in ("aflb", "thlb"):
        payload = current.get(scope)
        if not isinstance(payload, dict):
            payload = {}
        normalized[scope] = {
            "locked": bool(payload.get("locked", False)),
            "locked_utc": str(payload.get("locked_utc", "")).strip() or None,
            "locked_by": str(payload.get("locked_by", "")).strip() or None,
            "locked_script_path": str(payload.get("locked_script_path", "")).strip()
            or None,
            "frozen_status_report_path": str(
                payload.get("frozen_status_report_path", "")
            ).strip()
            or None,
            "frozen_audit_path": str(payload.get("frozen_audit_path", "")).strip()
            or None,
            "note": str(payload.get("note", "")).strip() or None,
        }
    if not normalized["aflb"]["locked"] and normalized["thlb"]["locked"]:
        normalized["thlb"] = {
            "locked": False,
            "locked_utc": None,
            "locked_by": None,
            "locked_script_path": None,
            "frozen_status_report_path": None,
            "frozen_audit_path": None,
            "note": "invalidated because AFLB lock is not active",
        }
    return normalized


def _detect_current_thlb_status_report_path(
    *, instance_root: Path, recipe_contract: dict[str, Any]
) -> Path:
    candidate_keys = (
        "status_report_path",
        "recipe_build_status_report_path",
    )
    for key in candidate_keys:
        value = str(recipe_contract.get(key, "")).strip()
        if not value:
            continue
        candidate = _resolve_instance_path(instance_root, value)
        if candidate.exists():
            return candidate
    raise TsrRecipeError(
        "No THLB status report is available to freeze yet. Run "
        "`femic tsr thlb-netdown-build` or `femic tsr thlb-netdown-run` first."
    )


def _detect_current_thlb_audit_path(*, instance_root: Path) -> Path | None:
    candidates = (
        default_tsr_thlb_reconstructed_audit_path(instance_root=instance_root),
        default_tsr_thlb_netdown_audit_path(instance_root=instance_root),
    )
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _parent_steps_grouped_by_stage(
    recipe: TsrThlbNetdownRecipeRecord,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    milestones: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {stage: [] for stage in _THLB_STAGE_ORDER}
    for parent_step in recipe.parent_steps:
        item = dict(parent_step)
        if str(item.get("parent_kind", "")) == "milestone":
            milestones.append(item)
            continue
        stage = str(item.get("land_base_stage", "context"))
        if stage not in groups:
            stage = "context"
        groups[stage].append(item)
    return milestones, groups


def _stage_header_text(stage: str) -> str:
    return _THLB_STAGE_LABELS.get(stage, stage)


def _resolve_tsr_thlb_parent_step(
    recipe: TsrThlbNetdownRecipeRecord, *, parent_step_id: str
) -> dict[str, Any]:
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_step_id", "")).strip() == parent_step_id:
            return dict(parent_step)
    raise TsrRecipeError(f"No THLB parent step found for `{parent_step_id}`.")


def _resolve_tsr_total_area_benchmark(
    recipe: TsrThlbNetdownRecipeRecord,
) -> float | None:
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_kind", "")).strip() != "milestone":
            continue
        label = str(parent_step.get("parent_label", "")).strip().casefold()
        if "total tsa area" not in label and "gross land base" not in label:
            continue
        value = parent_step.get("benchmark_cumulative_area_ha")
        if value is None:
            continue
        return float(value)
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_kind", "")).strip() == "milestone":
            continue
        stage = str(parent_step.get("land_base_stage", "")).strip()
        if stage != "glb_to_aflb":
            continue
        marginal = parent_step.get("benchmark_marginal_area_ha")
        cumulative = parent_step.get("benchmark_cumulative_area_ha")
        if marginal is None or cumulative is None:
            continue
        return float(marginal) + float(cumulative)
    return None


def _evaluate_attribute_filter(
    series: pd.Series,
    *,
    operator: str,
    value: Any,
) -> pd.Series:
    if operator == "eq":
        return series == value
    if operator == "ne":
        return series != value
    if operator == "lt":
        return pd.to_numeric(series, errors="coerce") < float(value)
    if operator == "le":
        return pd.to_numeric(series, errors="coerce") <= float(value)
    if operator == "gt":
        return pd.to_numeric(series, errors="coerce") > float(value)
    if operator == "ge":
        return pd.to_numeric(series, errors="coerce") >= float(value)
    if operator == "in":
        return series.isin(list(value))
    if operator == "not_in":
        return ~series.isin(list(value))
    if operator == "is_null":
        return series.isna()
    if operator == "not_blank":
        return series.notna() & (series.astype(str).str.strip() != "")
    raise TsrRecipeError(f"Unsupported attribute filter operator: {operator}")


def _apply_checkpoint_attribute_filters(
    checkpoint: gpd.GeoDataFrame,
    *,
    filters: Sequence[dict[str, Any]],
    mode: str,
    preserve_geometry: bool = False,
) -> tuple[gpd.GeoDataFrame, float]:
    if not filters:
        return checkpoint, 0.0
    exclude_mask = _build_checkpoint_attribute_mask(
        checkpoint,
        filters=filters,
        mode=mode,
    )
    if exclude_mask is None:
        return checkpoint, 0.0
    active_mask = (
        checkpoint["thlb_fact"] > 0 if "thlb_fact" in checkpoint.columns else True
    )
    effective_exclude_mask = exclude_mask & active_mask
    removed_area_ha = float(
        checkpoint.loc[effective_exclude_mask, "_stand_area_sqm"].sum() / 10000.0
    )
    if preserve_geometry:
        updated = checkpoint.copy()
        updated.loc[effective_exclude_mask, "thlb_fact"] = 0.0
        updated.loc[effective_exclude_mask, "thlb"] = 0
        updated = _assign_fragment_feature_ids(updated)
        return updated, removed_area_ha
    remaining = checkpoint.loc[~effective_exclude_mask].copy()
    remaining = _assign_fragment_feature_ids(remaining)
    remaining["thlb_fact"] = 1.0
    remaining["thlb"] = 1
    return remaining, removed_area_ha


def _build_checkpoint_attribute_mask(
    checkpoint: gpd.GeoDataFrame,
    *,
    filters: Sequence[dict[str, Any]],
    mode: str,
) -> pd.Series | None:
    if not filters:
        return None
    masks: list[pd.Series] = []
    for item in filters:
        field = str(item.get("field", "")).strip()
        operator = str(item.get("operator", "")).strip()
        value = item.get("value")
        if field not in checkpoint.columns:
            continue
        masks.append(
            _evaluate_attribute_filter(
                checkpoint[field], operator=operator, value=value
            )
        )
    if not masks:
        return None
    exclude_mask = masks[0].copy()
    for mask in masks[1:]:
        if mode == "all":
            exclude_mask = exclude_mask & mask
        else:
            exclude_mask = exclude_mask | mask
    return exclude_mask


def _apply_source_attribute_filters(
    layer: gpd.GeoDataFrame,
    *,
    filters: Sequence[dict[str, Any]],
) -> gpd.GeoDataFrame:
    if not filters:
        return layer
    filtered = layer.copy()
    for item in filters:
        field = str(item.get("field", "")).strip()
        operator = str(item.get("operator", "")).strip()
        value = item.get("value")
        if field not in filtered.columns:
            continue
        mask = _evaluate_attribute_filter(
            filtered[field], operator=operator, value=value
        )
        filtered = filtered.loc[mask].copy()
    return filtered


@lru_cache(maxsize=8)
def _load_curve_metric_lookup(bundle_root_str: str) -> dict[int, dict[str, Any]]:
    bundle_root = Path(bundle_root_str)
    curve_table_path = bundle_root / "curve_table.csv"
    curve_points_path = bundle_root / "curve_points_table.csv"
    if not curve_table_path.exists() or not curve_points_path.exists():
        raise TsrRecipeError(
            "Curve-driven THLB step requires `data/model_input_bundle/curve_table.csv` "
            "and `curve_points_table.csv`."
        )
    curve_table = pd.read_csv(curve_table_path, usecols=["curve_id", "curve_type"])
    curve_points = pd.read_csv(curve_points_path, usecols=["curve_id", "x", "y"])
    curve_points["x"] = pd.to_numeric(curve_points["x"], errors="coerce")
    curve_points["y"] = pd.to_numeric(curve_points["y"], errors="coerce")
    curve_points = curve_points.loc[
        curve_points["curve_id"].notna()
        & curve_points["x"].notna()
        & curve_points["y"].notna()
        & (curve_points["x"] > 0)
    ].copy()
    if curve_points.empty:
        raise TsrRecipeError(
            "Curve-driven THLB step could not find any usable curve points in "
            f"{curve_points_path}."
        )
    curve_points["mai"] = curve_points["y"] / curve_points["x"]
    curve_point_series: dict[int, tuple[tuple[float, float], ...]] = {}
    for curve_id, group in curve_points.groupby("curve_id", sort=False):
        try:
            curve_id_int = int(float(str(curve_id)))
        except (TypeError, ValueError) as exc:
            raise TsrRecipeError(
                "Curve-driven THLB step encountered a non-numeric curve_id while "
                "building metric lookup data."
            ) from exc
        ordered = group.sort_values("x")[["x", "y"]]
        curve_point_series[curve_id_int] = tuple(
            (float(x), float(y)) for x, y in ordered.itertuples(index=False, name=None)
        )
    cmai_rows = curve_points.loc[
        curve_points.groupby("curve_id", sort=False)["mai"].idxmax()
    ][["curve_id", "x", "y"]].rename(columns={"x": "cmai_age", "y": "cmai_volume"})
    culmination_rows = curve_points.groupby("curve_id", as_index=False).agg(
        culmination_volume=("y", "max")
    )
    merged = curve_table.merge(cmai_rows, on="curve_id", how="left").merge(
        culmination_rows, on="curve_id", how="left"
    )
    lookup: dict[int, dict[str, Any]] = {}
    for row in merged.to_dict(orient="records"):
        curve_id = int(row["curve_id"])
        lookup[curve_id] = {
            "curve_type": str(row.get("curve_type", "")).strip(),
            "cmai_age": (
                float(row["cmai_age"]) if pd.notna(row.get("cmai_age")) else None
            ),
            "cmai_volume": (
                float(row["cmai_volume"]) if pd.notna(row.get("cmai_volume")) else None
            ),
            "culmination_volume": (
                float(row["culmination_volume"])
                if pd.notna(row.get("culmination_volume"))
                else None
            ),
            "curve_points": curve_point_series.get(curve_id, ()),
        }
    return lookup


def _interpolate_curve_volume_at_age(
    curve_points: Sequence[tuple[float, float]],
    *,
    age_years: float,
) -> float | None:
    if not curve_points:
        return None
    if math.isnan(age_years) or age_years <= 0.0:
        return None
    if len(curve_points) == 1:
        only_age, only_volume = curve_points[0]
        return only_volume if only_age == age_years else None
    lower_point: tuple[float, float] | None = None
    upper_point: tuple[float, float] | None = None
    for current_age, current_volume in curve_points:
        if current_age == age_years:
            return current_volume
        if current_age < age_years:
            lower_point = (current_age, current_volume)
            continue
        upper_point = (current_age, current_volume)
        break
    if lower_point is None or upper_point is None:
        return None
    lower_age, lower_volume = lower_point
    upper_age, upper_volume = upper_point
    if upper_age <= lower_age:
        return None
    age_fraction = (age_years - lower_age) / (upper_age - lower_age)
    return lower_volume + ((upper_volume - lower_volume) * age_fraction)


def _resolve_curve_metric_series(
    metric_frame: pd.DataFrame,
    *,
    compiled_item: dict[str, Any],
) -> tuple[pd.Series, str]:
    metric_mode = (
        str(compiled_item.get("curve_volume_metric", _CURVE_VOLUME_METRIC_AUTO)).strip()
        or _CURVE_VOLUME_METRIC_AUTO
    )
    if metric_mode == _CURVE_VOLUME_METRIC_AUTO:
        treated_mask = (
            metric_frame["curve_type"]
            .fillna("")
            .str.casefold()
            .str.startswith("treated")
        )
        metric_series = metric_frame["culmination_volume"].copy()
        metric_series.loc[treated_mask] = metric_frame.loc[treated_mask, "cmai_volume"]
        return (
            metric_series,
            "treated curves use volume at CMAI; untreated curves use culmination volume",
        )
    if metric_mode == _CURVE_VOLUME_METRIC_AGE:
        raw_age = compiled_item.get("curve_volume_age_years")
        if raw_age is None:
            raise TsrRecipeError(
                "Curve-driven THLB step with `volume_at_age` metric requires a "
                "numeric `curve_volume_age_years`."
            )
        try:
            age_years = float(raw_age)
        except (TypeError, ValueError) as exc:
            raise TsrRecipeError(
                "Curve-driven THLB step with `volume_at_age` metric requires a "
                "numeric `curve_volume_age_years`."
            ) from exc
        metric_series = metric_frame["curve_points"].map(
            lambda value: _interpolate_curve_volume_at_age(
                value if isinstance(value, tuple) else (),
                age_years=age_years,
            )
        )
        return (metric_series, f"assigned curve volume at age {age_years:g}")
    raise TsrRecipeError(f"Unsupported curve volume metric mode: {metric_mode}")


def _describe_curve_metric(compiled_item: dict[str, Any]) -> str:
    metric_mode = (
        str(compiled_item.get("curve_volume_metric", _CURVE_VOLUME_METRIC_AUTO)).strip()
        or _CURVE_VOLUME_METRIC_AUTO
    )
    if metric_mode == _CURVE_VOLUME_METRIC_AUTO:
        return (
            "treated curves use volume at CMAI; untreated curves use culmination volume"
        )
    if metric_mode == _CURVE_VOLUME_METRIC_AGE:
        raw_age = compiled_item.get("curve_volume_age_years")
        if raw_age is None:
            raise TsrRecipeError(
                "Curve-driven THLB step with `volume_at_age` metric requires a "
                "numeric `curve_volume_age_years`."
            )
        try:
            age_years = float(raw_age)
        except (TypeError, ValueError) as exc:
            raise TsrRecipeError(
                "Curve-driven THLB step with `volume_at_age` metric requires a "
                "numeric `curve_volume_age_years`."
            ) from exc
        return f"assigned curve volume at age {age_years:g}"
    raise TsrRecipeError(f"Unsupported curve volume metric mode: {metric_mode}")


def _apply_curve_volume_threshold_exclusion(
    checkpoint: gpd.GeoDataFrame,
    *,
    instance_root: Path,
    compiled_item: dict[str, Any],
    preserve_geometry: bool,
) -> tuple[gpd.GeoDataFrame, float, int, int, int, int]:
    curve_id_column = (
        str(compiled_item.get("curve_id_column", "curve1")).strip() or "curve1"
    )
    if curve_id_column not in checkpoint.columns:
        raise TsrRecipeError(
            f"Curve-driven THLB step requires checkpoint column `{curve_id_column}`."
        )
    minimum_volume = float(compiled_item.get("minimum_volume_m3_per_ha", 0.0) or 0.0)
    if minimum_volume <= 0.0:
        raise TsrRecipeError(
            "Curve-driven THLB step requires a positive minimum volume cutoff."
        )
    metrics_lookup = _load_curve_metric_lookup(
        str((instance_root / "data" / "model_input_bundle").expanduser().resolve())
    )
    curve_ids = pd.to_numeric(checkpoint[curve_id_column], errors="coerce")
    metric_frame = pd.DataFrame(
        {
            "curve_id": curve_ids,
            "curve_type": curve_ids.map(
                lambda value: (
                    metrics_lookup.get(int(value), {}).get("curve_type")
                    if pd.notna(value)
                    else None
                )
            ),
            "cmai_volume": curve_ids.map(
                lambda value: (
                    metrics_lookup.get(int(value), {}).get("cmai_volume")
                    if pd.notna(value)
                    else None
                )
            ),
            "culmination_volume": curve_ids.map(
                lambda value: (
                    metrics_lookup.get(int(value), {}).get("culmination_volume")
                    if pd.notna(value)
                    else None
                )
            ),
            "curve_points": curve_ids.map(
                lambda value: (
                    metrics_lookup.get(int(value), {}).get("curve_points")
                    if pd.notna(value)
                    else None
                )
            ),
        },
        index=checkpoint.index,
    )
    metric_series, _ = _resolve_curve_metric_series(
        metric_frame,
        compiled_item=compiled_item,
    )
    filters = [
        dict(item)
        for item in compiled_item.get("checkpoint_attribute_filters", ())
        if isinstance(item, dict)
    ]
    mode = str(compiled_item.get("checkpoint_attribute_mode", "any")).strip() or "any"
    subset_mask = _build_checkpoint_attribute_mask(
        checkpoint,
        filters=filters,
        mode=mode,
    )
    if subset_mask is None:
        subset_mask = pd.Series(True, index=checkpoint.index, dtype=bool)
    active_mask = (
        checkpoint["thlb_fact"] > 0 if "thlb_fact" in checkpoint.columns else True
    )
    scoped_active_mask = active_mask & subset_mask
    metric_available = metric_series.notna()
    exclude_mask = (
        scoped_active_mask & metric_available & (metric_series < minimum_volume)
    )
    removed_area_ha = float(
        checkpoint.loc[exclude_mask, "_stand_area_sqm"].sum() / 10000.0
    )
    missing_metric_count = int((scoped_active_mask & ~metric_available).sum())
    scoped_row_count = int(subset_mask.sum())
    scoped_active_row_count = int(scoped_active_mask.sum())
    if preserve_geometry:
        updated = checkpoint.copy()
        updated.loc[exclude_mask, "thlb_fact"] = 0.0
        updated.loc[exclude_mask, "thlb"] = 0
        updated = _assign_fragment_feature_ids(updated)
        return (
            updated,
            removed_area_ha,
            missing_metric_count,
            int(exclude_mask.sum()),
            scoped_row_count,
            scoped_active_row_count,
        )
    remaining = checkpoint.loc[~exclude_mask].copy()
    remaining = _assign_fragment_feature_ids(remaining)
    remaining["thlb_fact"] = 1.0
    remaining["thlb"] = 1
    return (
        remaining,
        removed_area_ha,
        missing_metric_count,
        int(exclude_mask.sum()),
        scoped_row_count,
        scoped_active_row_count,
    )


def _load_compiled_logic_geometries(
    *,
    instance_root: Path,
    compiled_item: dict[str, Any],
    source_entry_map: dict[str, dict[str, Any]],
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[gpd.GeoDataFrame | None, list[str], bool]:
    filters = [
        dict(item)
        for item in compiled_item.get("source_attribute_filters", ())
        if isinstance(item, dict)
    ]
    linked_source_entry_ids = tuple(
        str(value).strip()
        for value in compiled_item.get("linked_source_entry_ids", ())
        if str(value).strip()
    )
    operation_type = _resolve_compiled_operation_type(compiled_item)
    allowed_geom_types = (
        ("Polygon", "MultiPolygon", "LineString", "MultiLineString")
        if operation_type == "buffer_then_intersect"
        else ("Polygon", "MultiPolygon")
    )
    geometries, missing_sources = _load_exclusion_geometries(
        instance_root=instance_root,
        linked_source_entry_ids=linked_source_entry_ids,
        source_entry_map=source_entry_map,
        preserve_attributes=bool(filters),
        allowed_geom_types=allowed_geom_types,
        bbox=bbox,
    )
    if geometries is None:
        return None, missing_sources, False
    if geometries.empty:
        return geometries, missing_sources, True
    if filters:
        geometries = _apply_source_attribute_filters(geometries, filters=filters)
        if geometries.empty:
            return geometries, missing_sources, True
    return geometries, missing_sources, False


def _execute_workbench_compiled_item(
    *,
    checkpoint: gpd.GeoDataFrame,
    compiled_item: dict[str, Any],
    instance_root: Path,
    source_entry_map: dict[str, dict[str, Any]],
    total_area_benchmark_ha: float | None = None,
) -> tuple[gpd.GeoDataFrame, dict[str, Any]]:
    operation_type = _resolve_compiled_operation_type(compiled_item)
    land_base_stage = str(compiled_item.get("land_base_stage", "")).strip()
    preserve_geometry = land_base_stage in {"aflb_to_lhlb", "lhlb_to_thlb"}
    runtime_item = dict(compiled_item)
    runtime_item["execution_status"] = "ready"
    runtime_item["removed_area_ha"] = 0.0
    runtime_item["remaining_area_ha"] = _managed_area_ha(checkpoint)
    runtime_notes: list[str] = list(runtime_item.get("notes", []))

    if operation_type in {"reference_only", "manual_review_required"}:
        runtime_item["execution_status"] = operation_type
        runtime_item["runtime_notes"] = runtime_notes
        return checkpoint, runtime_item

    if operation_type == "select_attribute":
        filters = [
            dict(item)
            for item in compiled_item.get("checkpoint_attribute_filters", ())
            if isinstance(item, dict)
        ]
        mode = (
            str(compiled_item.get("checkpoint_attribute_mode", "any")).strip() or "any"
        )
        updated, removed_area_ha = _apply_checkpoint_attribute_filters(
            checkpoint,
            filters=filters,
            mode=mode,
            preserve_geometry=preserve_geometry,
        )
        runtime_item["removed_area_ha"] = removed_area_ha
        runtime_item["remaining_area_ha"] = _managed_area_ha(updated)
        runtime_item["execution_status"] = (
            "applied" if removed_area_ha > 0 else "applied_noop"
        )
        if preserve_geometry:
            runtime_notes.append(
                "Later-stage exclusion preserved geometry and set THLB state to 0 on matched rows."
            )
        runtime_item["runtime_notes"] = runtime_notes
        return updated, runtime_item

    if operation_type == "curve_volume_threshold_exclusion":
        try:
            (
                updated,
                removed_area_ha,
                missing_metric_count,
                affected_row_count,
                scoped_row_count,
                scoped_active_row_count,
            ) = _apply_curve_volume_threshold_exclusion(
                checkpoint,
                instance_root=instance_root,
                compiled_item=compiled_item,
                preserve_geometry=preserve_geometry,
            )
        except TsrRecipeError as exc:
            runtime_item["execution_status"] = "unsupported"
            runtime_notes.append(str(exc))
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        runtime_item["removed_area_ha"] = removed_area_ha
        runtime_item["remaining_area_ha"] = _managed_area_ha(updated)
        runtime_item["affected_fragment_count"] = affected_row_count
        runtime_item["missing_curve_metric_row_count"] = missing_metric_count
        runtime_item["checkpoint_filter_row_count"] = scoped_row_count
        runtime_item["active_checkpoint_filter_row_count"] = scoped_active_row_count
        runtime_item["execution_status"] = (
            "applied" if removed_area_ha > 0 else "applied_noop"
        )
        runtime_item["curve_metric_description"] = _describe_curve_metric(compiled_item)
        runtime_notes.append(
            f"Curve threshold evaluated using {runtime_item['curve_metric_description']}."
        )
        if missing_metric_count:
            runtime_notes.append(
                f"{missing_metric_count} active scoped rows had no usable curve metric and were retained."
            )
        if preserve_geometry:
            runtime_notes.append(
                "Later-stage exclusion preserved geometry/fragments and set THLB state to 0 on excluded areas."
            )
        runtime_item["runtime_notes"] = runtime_notes
        return updated, runtime_item

    if operation_type == "aspatial_reduction":
        benchmark_marginal_area_ha = compiled_item.get("benchmark_marginal_area_ha")
        current_managed_area_ha = _managed_area_ha(checkpoint)
        if (
            benchmark_marginal_area_ha is None
            or total_area_benchmark_ha is None
            or total_area_benchmark_ha <= 0.0
        ):
            runtime_item["execution_status"] = "unsupported"
            runtime_notes.append(
                "Aspatial reduction requires both the TSR benchmark marginal area and total TSA area benchmark."
            )
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        target_removed_area_ha = (
            float(benchmark_marginal_area_ha)
            * current_managed_area_ha
            / total_area_benchmark_ha
        )
        updated, removed_area_ha, affected_row_count = _apply_aspatial_thlb_reduction(
            checkpoint,
            target_removed_area_ha=target_removed_area_ha,
        )
        runtime_item["removed_area_ha"] = removed_area_ha
        runtime_item["remaining_area_ha"] = _managed_area_ha(updated)
        runtime_item["affected_fragment_count"] = affected_row_count
        runtime_item["execution_status"] = (
            "applied" if removed_area_ha > 0 else "applied_noop"
        )
        runtime_notes.append(
            "Later-stage aspatial reduction preserved geometry and reduced THLB state proportionally across the active subset."
        )
        runtime_notes.append(
            "Notebook execution scales the TSR benchmark marginal area to the current smoke subset before applying the reduction."
        )
        runtime_item["runtime_notes"] = runtime_notes
        return updated, runtime_item

    if operation_type == "aspatial_area_reduction":
        benchmark_marginal_area_ha = compiled_item.get("benchmark_marginal_area_ha")
        current_area_ha = float(
            _resolve_canonical_stand_area_sqm(checkpoint).sum() / 10000.0
        )
        if (
            benchmark_marginal_area_ha is None
            or total_area_benchmark_ha is None
            or total_area_benchmark_ha <= 0.0
        ):
            runtime_item["execution_status"] = "unsupported"
            runtime_notes.append(
                "Aspatial area reduction requires both the TSR benchmark marginal area and total TSA area benchmark."
            )
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        target_removed_area_ha = (
            float(benchmark_marginal_area_ha)
            * current_area_ha
            / total_area_benchmark_ha
        )
        updated, removed_area_ha, affected_row_count = _apply_aspatial_area_reduction(
            checkpoint,
            target_removed_area_ha=target_removed_area_ha,
        )
        runtime_item["removed_area_ha"] = removed_area_ha
        runtime_item["remaining_area_ha"] = _managed_area_ha(updated)
        runtime_item["affected_fragment_count"] = affected_row_count
        runtime_item["execution_status"] = (
            "applied" if removed_area_ha > 0 else "applied_noop"
        )
        runtime_notes.append(
            "Early-stage aspatial area reduction preserved geometry and reduced stand-area fields across the active AFLB subset."
        )
        runtime_notes.append(
            "Notebook execution scales the TSR benchmark marginal area to the current smoke subset before shrinking stand-area attributes."
        )
        runtime_item["runtime_notes"] = runtime_notes
        return updated, runtime_item

    if operation_type in {"select_spatial_intersect", "buffer_then_intersect"}:
        exclusion_geometries, missing_sources, no_matching_features = (
            _load_compiled_logic_geometries(
                instance_root=instance_root,
                compiled_item=compiled_item,
                source_entry_map=source_entry_map,
                bbox=(
                    float(checkpoint.total_bounds[0]),
                    float(checkpoint.total_bounds[1]),
                    float(checkpoint.total_bounds[2]),
                    float(checkpoint.total_bounds[3]),
                ),
            )
        )
        if exclusion_geometries is None:
            runtime_item["execution_status"] = "blocked_missing_source"
            runtime_item["missing_source_entry_ids"] = missing_sources
            runtime_notes.append(
                "No fetched spatial artifact was available for the linked source entries."
            )
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        if no_matching_features:
            runtime_item["execution_status"] = "applied_noop"
            runtime_notes.append(
                "Fetched spatial artifacts were available, but no features matched the current "
                "attribute filters within the smoke subset."
            )
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        if operation_type == "buffer_then_intersect":
            buffer_distance_m = float(
                compiled_item.get("buffer_distance_m", 0.0) or 0.0
            )
            exclusion_geometries = exclusion_geometries.copy()
            exclusion_geometries["geometry"] = exclusion_geometries.geometry.buffer(
                buffer_distance_m
            )
            exclusion_geometries = exclusion_geometries.loc[
                ~exclusion_geometries.geometry.is_empty
            ].copy()
        updated, affected_fragment_count, affected_area_ha = (
            _fragment_binary_exclusion_step(
                checkpoint=checkpoint,
                exclusion_geometries=exclusion_geometries,
                update_aflb_flag_on_exclusion=not preserve_geometry,
            )
        )
        if not preserve_geometry:
            updated = updated.loc[updated["thlb_fact"] > 0].copy()
            updated = _assign_fragment_feature_ids(updated)
            updated["thlb_fact"] = 1.0
            updated["thlb"] = 1
        else:
            runtime_notes.append(
                "Later-stage exclusion preserved geometry/fragments and set THLB state to 0 on excluded areas."
            )
        runtime_item["removed_area_ha"] = affected_area_ha
        runtime_item["remaining_area_ha"] = _managed_area_ha(updated)
        runtime_item["affected_fragment_count"] = affected_fragment_count
        runtime_item["execution_status"] = (
            "applied" if affected_area_ha > 0 else "applied_noop"
        )
        runtime_item["runtime_notes"] = runtime_notes
        return updated, runtime_item

    runtime_item["execution_status"] = "unsupported"
    runtime_notes.append(
        f"Unsupported notebook compiled operation type: {operation_type}"
    )
    runtime_item["runtime_notes"] = runtime_notes
    return checkpoint, runtime_item


def _resolve_compiled_operation_type(compiled_item: dict[str, Any]) -> str:
    operation_type = (
        str(compiled_item.get("compiled_operation_type", "")).strip()
        or str(compiled_item.get("operation_type", "")).strip()
    )
    if operation_type:
        return operation_type
    step_status = str(compiled_item.get("step_status", "")).strip()
    normalized_action = str(compiled_item.get("normalized_action", "")).strip()
    linked_source_entry_ids = tuple(
        str(value).strip()
        for value in compiled_item.get("linked_source_entry_ids", ())
        if str(value).strip()
    )
    if step_status == "manual_review_required":
        return "manual_review_required"
    if normalized_action == "review":
        return "manual_review_required"
    if normalized_action == "exclude" and linked_source_entry_ids:
        return "select_spatial_intersect"
    if normalized_action == "aspatial_reduction":
        return "aspatial_reduction"
    if normalized_action == "aspatial_area_reduction":
        return "aspatial_area_reduction"
    if normalized_action == "reference_only":
        return "reference_only"
    return ""


def _combine_parent_step_statuses(statuses: set[str]) -> str:
    applied_statuses = {"applied", "applied_noop"}
    if "blocked_missing_source" in statuses:
        return (
            "applied_with_blockers"
            if statuses & applied_statuses
            else "blocked_missing_source"
        )
    if "unsupported" in statuses:
        return (
            "applied_with_unsupported" if statuses & applied_statuses else "unsupported"
        )
    if "manual_review_required" in statuses and len(statuses) == 1:
        return "manual_review_required"
    return "applied"


def _build_parent_step_execution_plan(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    target_parent: dict[str, Any],
) -> list[dict[str, Any]]:
    target_stage_window = _workbench_stage_window_for_target(target_parent)
    plan: list[dict[str, Any]] = []
    for parent_step in recipe.parent_steps:
        if str(parent_step.get("parent_kind", "")).strip() == "milestone":
            continue
        current_stage = str(parent_step.get("land_base_stage", "")).strip()
        current_label = str(parent_step.get("parent_label", "")).strip()
        if target_stage_window and current_stage not in target_stage_window:
            continue
        if current_label.casefold() not in _THLB_NOTEBOOK_RUNNABLE_PARENT_LABELS:
            continue
        compiled_logic = [
            dict(item)
            for item in parent_step.get("compiled_logic", ())
            if isinstance(item, dict)
        ]
        plan.append(
            {
                "parent_step_id": str(parent_step.get("parent_step_id", "")).strip(),
                "parent_label": current_label,
                "compiled_logic": compiled_logic,
            }
        )
        if (
            str(parent_step.get("parent_step_id", "")).strip()
            == str(target_parent.get("parent_step_id", "")).strip()
        ):
            break
    return plan


def _execute_tsr_thlb_parent_step_plan(
    *,
    checkpoint: gpd.GeoDataFrame,
    execution_plan: Sequence[dict[str, Any]],
    target_parent_id: str,
    instance_root: Path,
    source_entry_map: dict[str, dict[str, Any]],
    total_area_benchmark_ha: float | None,
) -> tuple[
    gpd.GeoDataFrame,
    tuple[str, ...],
    list[dict[str, Any]],
    float,
    float,
    str,
    tuple[str, ...],
]:
    executed_parent_step_ids: list[str] = []
    executed_items: list[dict[str, Any]] = []
    target_removed_area_ha = 0.0
    target_remaining_area_ha = _managed_area_ha(checkpoint)
    target_notes: list[str] = []
    final_status = "ready"

    working = checkpoint
    for parent_step in execution_plan:
        current_parent_id = str(parent_step.get("parent_step_id", "")).strip()
        removed_area_this_parent = 0.0
        parent_runtime_items: list[dict[str, Any]] = []
        for compiled_item in parent_step.get("compiled_logic", ()):
            if not isinstance(compiled_item, dict):
                continue
            working, runtime_item = _execute_workbench_compiled_item(
                checkpoint=working,
                compiled_item=dict(compiled_item),
                instance_root=instance_root,
                source_entry_map=source_entry_map,
                total_area_benchmark_ha=total_area_benchmark_ha,
            )
            removed_area_this_parent += float(
                runtime_item.get("removed_area_ha", 0.0) or 0.0
            )
            parent_runtime_items.append(runtime_item)
            executed_items.append(runtime_item)
        executed_parent_step_ids.append(current_parent_id)
        if current_parent_id != target_parent_id:
            continue
        target_removed_area_ha = removed_area_this_parent
        target_remaining_area_ha = _managed_area_ha(working)
        statuses = {
            str(item.get("execution_status", "")).strip()
            for item in parent_runtime_items
            if str(item.get("execution_status", "")).strip()
        }
        final_status = _combine_parent_step_statuses(statuses)
        for item in parent_runtime_items:
            for note in item.get("runtime_notes", ()):
                note_text = str(note).strip()
                if note_text and note_text not in target_notes:
                    target_notes.append(note_text)
        break

    return (
        working,
        tuple(executed_parent_step_ids),
        executed_items,
        target_removed_area_ha,
        target_remaining_area_ha,
        final_status,
        tuple(target_notes),
    )


def _run_tsr_thlb_parent_step_chunk_worker(
    *,
    chunk_path: str,
    output_path: str,
    execution_plan: Sequence[dict[str, Any]],
    target_parent_id: str,
    instance_root: str,
    source_entry_map: dict[str, dict[str, Any]],
    total_area_benchmark_ha: float | None,
) -> dict[str, Any]:
    checkpoint = gpd.read_feather(chunk_path)
    checkpoint = gpd.GeoDataFrame(checkpoint, geometry="geometry", crs=BC_ALBERS_EPSG)
    (
        updated,
        executed_parent_step_ids,
        executed_items,
        target_removed_area_ha,
        target_remaining_area_ha,
        final_status,
        target_notes,
    ) = _execute_tsr_thlb_parent_step_plan(
        checkpoint=checkpoint,
        execution_plan=execution_plan,
        target_parent_id=target_parent_id,
        instance_root=Path(instance_root),
        source_entry_map=source_entry_map,
        total_area_benchmark_ha=total_area_benchmark_ha,
    )
    updated.drop(columns=["_row_id", "_stand_area_sqm"], errors="ignore").to_feather(
        output_path
    )
    return {
        "output_path": output_path,
        "executed_parent_step_ids": list(executed_parent_step_ids),
        "executed_items": executed_items,
        "removed_area_ha": target_removed_area_ha,
        "remaining_area_ha": target_remaining_area_ha,
        "status": final_status,
        "notes": list(target_notes),
    }


def _run_tsr_thlb_parent_step_bundle_worker(
    *,
    bundle_index: int,
    bundle_label: str,
    bundle_items: Sequence[tuple[str, str]],
    output_path: str,
    execution_plan: Sequence[dict[str, Any]],
    target_parent_id: str,
    instance_root: str,
    source_entry_map: dict[str, dict[str, Any]],
    total_area_benchmark_ha: float | None,
    progress_path: str | None = None,
) -> dict[str, Any]:
    bundle_started = perf_counter()
    progress_target = Path(progress_path) if progress_path else None
    lu_names = [str(lu_name).strip() for lu_name, _chunk_path in bundle_items]
    if progress_target is not None:
        _write_tsr_thlb_parallel_progress(
            progress_target,
            bundle_index=bundle_index,
            bundle_label=bundle_label,
            lu_names=lu_names,
            completed_lus=0,
            total_lus=len(bundle_items),
            current_lu=None,
            status="running",
        )

    merged_frames: list[gpd.GeoDataFrame] = []
    executed_parent_step_ids: tuple[str, ...] = ()
    executed_items: list[dict[str, Any]] = []
    removed_area_ha = 0.0
    notes: list[str] = []
    statuses: set[str] = set()
    completed_lus = 0
    chunk_profile_items: list[dict[str, Any]] = []

    try:
        for lu_name, chunk_path in bundle_items:
            if progress_target is not None:
                _write_tsr_thlb_parallel_progress(
                    progress_target,
                    bundle_index=bundle_index,
                    bundle_label=bundle_label,
                    lu_names=lu_names,
                    completed_lus=completed_lus,
                    total_lus=len(bundle_items),
                    current_lu=lu_name,
                    status="running",
                )
            chunk_started = perf_counter()
            read_started = perf_counter()
            checkpoint = gpd.read_feather(Path(chunk_path))
            checkpoint = gpd.GeoDataFrame(
                checkpoint, geometry="geometry", crs=BC_ALBERS_EPSG
            )
            read_elapsed = perf_counter() - read_started
            execute_started = perf_counter()
            (
                updated,
                current_parent_step_ids,
                current_executed_items,
                current_removed_area_ha,
                _current_remaining_area_ha,
                current_status,
                current_notes,
            ) = _execute_tsr_thlb_parent_step_plan(
                checkpoint=checkpoint,
                execution_plan=execution_plan,
                target_parent_id=target_parent_id,
                instance_root=Path(instance_root),
                source_entry_map=source_entry_map,
                total_area_benchmark_ha=total_area_benchmark_ha,
            )
            execute_elapsed = perf_counter() - execute_started
            merged_frames.append(updated)
            if not executed_parent_step_ids:
                executed_parent_step_ids = tuple(current_parent_step_ids)
            executed_items.extend(current_executed_items)
            removed_area_ha += float(current_removed_area_ha)
            statuses.add(str(current_status).strip())
            notes.extend(
                str(value).strip() for value in current_notes if str(value).strip()
            )
            completed_lus += 1
            chunk_profile_items.append(
                {
                    "lu_name": lu_name,
                    "chunk_path": str(chunk_path),
                    "input_row_count": int(len(checkpoint)),
                    "output_row_count": int(len(updated)),
                    "read_seconds": read_elapsed,
                    "execute_seconds": execute_elapsed,
                    "total_seconds": perf_counter() - chunk_started,
                }
            )
            if progress_target is not None:
                _write_tsr_thlb_parallel_progress(
                    progress_target,
                    bundle_index=bundle_index,
                    bundle_label=bundle_label,
                    lu_names=lu_names,
                    completed_lus=completed_lus,
                    total_lus=len(bundle_items),
                    current_lu=lu_name,
                    status="running",
                    notes=notes[-5:],
                )
    except Exception as exc:
        if progress_target is not None:
            _write_tsr_thlb_parallel_progress(
                progress_target,
                bundle_index=bundle_index,
                bundle_label=bundle_label,
                lu_names=lu_names,
                completed_lus=completed_lus,
                total_lus=len(bundle_items),
                current_lu=None,
                status="failed",
                notes=[*notes[-5:], str(exc)],
            )
        raise

    if merged_frames:
        merge_started = perf_counter()
        updated_frame = gpd.GeoDataFrame(
            pd.concat(merged_frames, ignore_index=True),
            geometry="geometry",
            crs=BC_ALBERS_EPSG,
        )
        concat_elapsed = perf_counter() - merge_started
        write_started = perf_counter()
        updated_frame.drop(
            columns=["_row_id", "_stand_area_sqm"], errors="ignore"
        ).to_feather(output_path)
        write_elapsed = perf_counter() - write_started
        remaining_area_ha = _managed_area_ha(updated_frame)
    else:
        updated_frame = gpd.GeoDataFrame(geometry=[], crs=BC_ALBERS_EPSG)
        concat_elapsed = 0.0
        write_started = perf_counter()
        updated_frame.to_feather(output_path)
        write_elapsed = perf_counter() - write_started
        remaining_area_ha = 0.0
    final_status = _combine_parent_step_statuses(statuses)
    if progress_target is not None:
        _write_tsr_thlb_parallel_progress(
            progress_target,
            bundle_index=bundle_index,
            bundle_label=bundle_label,
            lu_names=lu_names,
            completed_lus=len(bundle_items),
            total_lus=len(bundle_items),
            current_lu=None,
            status="completed",
            notes=notes[-5:],
        )
    return {
        "output_path": output_path,
        "executed_parent_step_ids": list(executed_parent_step_ids),
        "executed_items": executed_items,
        "removed_area_ha": removed_area_ha,
        "remaining_area_ha": remaining_area_ha,
        "status": final_status,
        "notes": list(dict.fromkeys(notes)),
        "bundle_index": bundle_index,
        "bundle_label": bundle_label,
        "lu_names": lu_names,
        "completed_lus": len(bundle_items),
        "profiling": {
            "bundle_total_seconds": perf_counter() - bundle_started,
            "bundle_concat_seconds": concat_elapsed,
            "bundle_write_seconds": write_elapsed,
            "chunk_items": chunk_profile_items,
            "chunk_read_seconds_total": float(
                sum(float(item["read_seconds"]) for item in chunk_profile_items)
            ),
            "chunk_execute_seconds_total": float(
                sum(float(item["execute_seconds"]) for item in chunk_profile_items)
            ),
        },
    }


def _dedupe_runtime_notes(notes: Sequence[str]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for note in notes:
        normalized = str(note).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return tuple(unique)


def _summarize_executed_items(
    executed_items: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    summary_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in executed_items:
        step_id = str(item.get("step_id", "")).strip()
        label = str(item.get("label", "")).strip()
        operation = str(item.get("compiled_operation_type", "")).strip()
        if not step_id:
            continue
        key = (step_id, label, operation)
        summary = summary_map.setdefault(
            key,
            {
                "step_id": step_id,
                "label": label,
                "compiled_operation_type": operation,
                "minimum_volume_m3_per_ha": item.get("minimum_volume_m3_per_ha"),
                "curve_metric_description": item.get("curve_metric_description"),
                "removed_area_ha": 0.0,
                "missing_curve_metric_row_count": 0,
                "affected_fragment_count": 0,
                "checkpoint_filter_row_count": 0,
                "active_checkpoint_filter_row_count": 0,
                "item_count": 0,
            },
        )
        summary["removed_area_ha"] += float(item.get("removed_area_ha", 0.0) or 0.0)
        summary["missing_curve_metric_row_count"] += int(
            item.get("missing_curve_metric_row_count", 0) or 0
        )
        summary["affected_fragment_count"] += int(
            item.get("affected_fragment_count", 0) or 0
        )
        summary["checkpoint_filter_row_count"] += int(
            item.get("checkpoint_filter_row_count", 0) or 0
        )
        summary["active_checkpoint_filter_row_count"] += int(
            item.get("active_checkpoint_filter_row_count", 0) or 0
        )
        summary["item_count"] += 1
    return list(summary_map.values())


def run_tsr_thlb_parent_step(
    *,
    recipe_path: Path,
    parent_step_id: str,
    checkpoint_path: Path | None = None,
    map_ids: Sequence[str] = (),
    landscape_units: Sequence[str] = (),
    auto_map_id_smoke_subset: bool = True,
    execution_mode: str = TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
    max_workers: int | None = None,
    lu_bundle_count: int | None = None,
    progress_root: Path | None = None,
    persist_recipe_update: bool = True,
) -> TsrThlbParentStepRunResult:
    """Execute one THLB parent step cumulatively on the notebook smoke subset."""

    total_started = perf_counter()
    recipe, instance_root, source_recipe, source_entry_map, override_entries = (
        _load_tsr_thlb_recipe_context(recipe_path)
    )
    target_parent = _resolve_tsr_thlb_parent_step(recipe, parent_step_id=parent_step_id)
    target_label = str(target_parent.get("parent_label", "")).strip()
    if target_label.casefold() not in _THLB_NOTEBOOK_RUNNABLE_PARENT_LABELS:
        raise TsrRecipeError(
            "Notebook execution is currently limited to the first TSA29 activation tranche: "
            + ", ".join(sorted(_THLB_NOTEBOOK_RUNNABLE_PARENT_LABELS))
        )
    if execution_mode not in _TSR_THLB_PARENT_STEP_EXECUTION_MODES:
        allowed = ", ".join(sorted(_TSR_THLB_PARENT_STEP_EXECUTION_MODES))
        raise TsrRecipeError(
            f"Unsupported THLB parent-step execution mode `{execution_mode}`. Expected one of: {allowed}"
        )
    resolved_checkpoint_path = (
        checkpoint_path.expanduser().resolve()
        if checkpoint_path is not None
        else _default_workbench_checkpoint_path(
            instance_root=instance_root, target_parent=target_parent
        )
    )
    profiling: dict[str, Any] = {
        "total_seconds": 0.0,
        "checkpoint_load_seconds": 0.0,
        "subset_filter_seconds": 0.0,
        "input_prepare_seconds": 0.0,
        "plan_build_seconds": 0.0,
        "lu_selection_cache_lookup_seconds": 0.0,
        "lu_selection_seconds": 0.0,
        "lu_layer_load_seconds": 0.0,
        "lu_bbox_filter_seconds": 0.0,
        "lu_union_seconds": 0.0,
        "lu_intersect_seconds": 0.0,
        "partition_materialize_seconds": 0.0,
        "bundle_group_seconds": 0.0,
        "worker_pool_seconds": 0.0,
        "merge_read_seconds": 0.0,
        "merge_concat_seconds": 0.0,
        "output_write_seconds": 0.0,
        "result_json_write_seconds": 0.0,
        "recipe_update_seconds": 0.0,
        "report_refresh_seconds": 0.0,
    }
    checkpoint_load_started = perf_counter()
    checkpoint = _load_checkpoint_geodataframe(resolved_checkpoint_path)
    profiling["checkpoint_load_seconds"] = perf_counter() - checkpoint_load_started
    selected_map_ids: tuple[str, ...] = ()
    selected_landscape_units: tuple[str, ...] = ()
    if auto_map_id_smoke_subset and (map_ids or landscape_units):
        raise TsrRecipeError(
            "Choose either explicit subset controls (`map_ids` / `landscape_units`) "
            "or `auto_map_id_smoke_subset`, not both."
        )
    subset_filter_started = perf_counter()
    if auto_map_id_smoke_subset:
        selected_map_ids = _auto_select_smoke_map_ids_for_parent_step(
            checkpoint=checkpoint,
            parent_step=target_parent,
            compiled_steps=[
                dict(item)
                for item in target_parent.get("compiled_logic", ())
                if isinstance(item, dict)
            ],
            instance_root=instance_root,
            source_entry_map=source_entry_map,
        )
        checkpoint = _filter_checkpoint_by_map_ids(checkpoint, map_ids=selected_map_ids)
    elif landscape_units:
        checkpoint, selected_landscape_units = _filter_checkpoint_by_landscape_units(
            checkpoint,
            instance_root=instance_root,
            landscape_units=landscape_units,
        )
        if "MAP_ID" in checkpoint.columns:
            selected_map_ids = tuple(
                sorted(
                    {
                        _normalize_map_id_token(value)
                        for value in checkpoint["MAP_ID"].dropna().astype(str)
                        if _normalize_map_id_token(value)
                    }
                )
            )
    elif map_ids:
        selected_map_ids = tuple(
            _normalize_map_id_token(value) for value in map_ids if str(value).strip()
        )
        checkpoint = _filter_checkpoint_by_map_ids(checkpoint, map_ids=selected_map_ids)
    profiling["subset_filter_seconds"] = perf_counter() - subset_filter_started

    input_prepare_started = perf_counter()
    checkpoint = checkpoint.copy()
    checkpoint["_row_id"] = range(len(checkpoint))
    checkpoint["_stand_area_sqm"] = _resolve_effective_stand_area_sqm(checkpoint)
    checkpoint["thlb_fact"] = 1.0
    checkpoint["thlb"] = 1
    input_area_ha = _managed_area_ha(checkpoint)
    profiling["input_prepare_seconds"] = perf_counter() - input_prepare_started

    runtime_root = default_tsr_thlb_notebook_runs_root(instance_root=instance_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    total_area_benchmark_ha = _resolve_tsr_total_area_benchmark(recipe)
    plan_build_started = perf_counter()
    execution_plan = _build_parent_step_execution_plan(
        recipe=recipe,
        target_parent=target_parent,
    )
    profiling["plan_build_seconds"] = perf_counter() - plan_build_started
    worker_count = 1
    lu_chunk_count: int | None = None
    resolved_progress_root: Path | None = None
    resolved_lu_bundle_count: int | None = None
    if execution_mode == TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL:
        serial_execute_started = perf_counter()
        (
            checkpoint,
            executed_parent_step_ids,
            executed_items,
            target_removed_area_ha,
            target_remaining_area_ha,
            final_status,
            target_notes,
        ) = _execute_tsr_thlb_parent_step_plan(
            checkpoint=checkpoint,
            execution_plan=execution_plan,
            target_parent_id=parent_step_id,
            instance_root=instance_root,
            source_entry_map=source_entry_map,
            total_area_benchmark_ha=total_area_benchmark_ha,
        )
        profiling["worker_pool_seconds"] = perf_counter() - serial_execute_started
    else:
        if auto_map_id_smoke_subset:
            raise TsrRecipeError(
                "LU-parallel THLB execution requires an explicit full/subset scope; "
                "disable `auto_map_id_smoke_subset`."
            )
        if map_ids:
            raise TsrRecipeError(
                "LU-parallel THLB execution does not support explicit `map_ids`; "
                "use the full TSA or an explicit LU subset."
            )
        chunk_records: list[dict[str, Any]] | None = None
        if landscape_units:
            lu_load_started = perf_counter()
            lu_layer = _load_landscape_unit_layer(instance_root)
            profiling["lu_layer_load_seconds"] = perf_counter() - lu_load_started
            lu_select_started = perf_counter()
            lu_frame, selected_landscape_units = _select_landscape_unit_rows(
                lu_layer,
                landscape_units=landscape_units,
            )
            profiling["lu_selection_seconds"] = perf_counter() - lu_select_started
            if lu_frame.empty:
                raise TsrRecipeError(
                    "LU-parallel THLB execution matched no landscape units: "
                    + ", ".join(
                        str(value).strip()
                        for value in landscape_units
                        if str(value).strip()
                    )
                )
        else:
            cache_lookup_started = perf_counter()
            cached_partition = _load_cached_landscape_unit_partition_records(
                checkpoint_path=resolved_checkpoint_path,
                instance_root=instance_root,
            )
            profiling["lu_selection_cache_lookup_seconds"] = (
                perf_counter() - cache_lookup_started
            )
            if cached_partition is not None:
                selected_landscape_units, chunk_records = cached_partition
            else:
                lu_select_started = perf_counter()
                (
                    lu_frame,
                    selected_landscape_units,
                    lu_selection_profile,
                ) = _select_intersecting_landscape_units_for_checkpoint(
                    checkpoint,
                    instance_root=instance_root,
                )
                profiling["lu_selection_seconds"] = perf_counter() - lu_select_started
                for key, value in lu_selection_profile.items():
                    profiling[key] = float(value)
        if chunk_records is None:
            partition_started = perf_counter()
            chunk_records = _materialize_checkpoint_landscape_unit_partitions(
                checkpoint,
                checkpoint_path=resolved_checkpoint_path,
                lu_frame=lu_frame,
                selected_landscape_units=selected_landscape_units,
                instance_root=instance_root,
            )
            profiling["partition_materialize_seconds"] = (
                perf_counter() - partition_started
            )
        if not chunk_records:
            raise TsrRecipeError("LU-parallel THLB execution produced no LU chunks.")
        lu_chunk_count = len(chunk_records)
        resolved_lu_bundle_count = max(
            1,
            min(
                int(lu_bundle_count) if lu_bundle_count is not None else lu_chunk_count,
                lu_chunk_count,
            ),
        )
        worker_count = max(
            1,
            min(max_workers or resolved_lu_bundle_count, resolved_lu_bundle_count),
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        staging_root = runtime_root / f"{parent_step_id}.parallel.{timestamp}"
        staging_root.mkdir(parents=True, exist_ok=True)
        bundle_group_started = perf_counter()
        bundles = _group_landscape_unit_chunk_records(
            chunk_records,
            bundle_count=resolved_lu_bundle_count,
        )
        profiling["bundle_group_seconds"] = perf_counter() - bundle_group_started
        resolved_progress_root = (
            progress_root.expanduser().resolve()
            if progress_root is not None
            else staging_root / "progress"
        )
        resolved_progress_root.mkdir(parents=True, exist_ok=True)
        worker_results: list[dict[str, Any]] = []
        worker_pool_started = perf_counter()
        with ProcessPoolExecutor(max_workers=worker_count) as pool:
            futures = [
                pool.submit(
                    _run_tsr_thlb_parent_step_bundle_worker,
                    bundle_index=int(bundle["bundle_index"]),
                    bundle_label=str(bundle["bundle_label"]),
                    bundle_items=[
                        (str(item["lu_name"]), str(Path(item["chunk_path"])))
                        for item in bundle["chunk_records"]
                    ],
                    output_path=str(
                        staging_root
                        / f"bundle_{int(bundle['bundle_index']):02d}.output.feather"
                    ),
                    execution_plan=execution_plan,
                    target_parent_id=parent_step_id,
                    instance_root=str(instance_root),
                    source_entry_map=source_entry_map,
                    total_area_benchmark_ha=total_area_benchmark_ha,
                    progress_path=str(
                        resolved_progress_root
                        / f"bundle_{int(bundle['bundle_index']):02d}.json"
                    ),
                )
                for bundle in bundles
            ]
            for future in futures:
                worker_results.append(future.result())
        profiling["worker_pool_seconds"] = perf_counter() - worker_pool_started
        merge_read_started = perf_counter()
        merged_frames = [
            gpd.read_feather(Path(result["output_path"])) for result in worker_results
        ]
        profiling["merge_read_seconds"] = perf_counter() - merge_read_started
        merge_concat_started = perf_counter()
        checkpoint = gpd.GeoDataFrame(
            pd.concat(merged_frames, ignore_index=True),
            geometry="geometry",
            crs=BC_ALBERS_EPSG,
        )
        checkpoint = checkpoint.loc[~checkpoint.geometry.is_empty].copy()
        checkpoint = _assign_fragment_feature_ids(checkpoint)
        profiling["merge_concat_seconds"] = perf_counter() - merge_concat_started
        executed_parent_step_ids = tuple(
            worker_results[0].get("executed_parent_step_ids", [])
        )
        executed_items = [
            item
            for result in worker_results
            for item in result.get("executed_items", [])
            if isinstance(item, dict)
        ]
        target_removed_area_ha = float(
            sum(
                float(result.get("removed_area_ha", 0.0) or 0.0)
                for result in worker_results
            )
        )
        target_remaining_area_ha = _managed_area_ha(checkpoint)
        statuses = {
            str(result.get("status", "")).strip()
            for result in worker_results
            if str(result.get("status", "")).strip()
        }
        final_status = _combine_parent_step_statuses(statuses)
        target_notes = tuple(
            dict.fromkeys(
                note_text
                for result in worker_results
                for note in result.get("notes", [])
                for note_text in [str(note).strip()]
                if note_text
            )
        )
        profiling["worker_bundles"] = [
            {
                "bundle_index": int(result.get("bundle_index", 0) or 0),
                "bundle_label": str(result.get("bundle_label", "")).strip(),
                "completed_lus": int(result.get("completed_lus", 0) or 0),
                "lu_names": list(result.get("lu_names", [])),
                "profiling": result.get("profiling", {}),
            }
            for result in worker_results
        ]

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = runtime_root / f"{parent_step_id}.{timestamp}.feather"
    result_json_path = runtime_root / f"{parent_step_id}.{timestamp}.json"
    output_frame = checkpoint.drop(
        columns=["_row_id", "_stand_area_sqm"], errors="ignore"
    )
    output_write_started = perf_counter()
    output_frame.to_feather(output_path)
    profiling["output_write_seconds"] = perf_counter() - output_write_started

    benchmark_marginal_area_ha = target_parent.get("benchmark_marginal_area_ha")
    benchmark_cumulative_area_ha = target_parent.get("benchmark_cumulative_area_ha")
    benchmark_marginal_delta_ha = (
        target_removed_area_ha - float(benchmark_marginal_area_ha)
        if benchmark_marginal_area_ha is not None
        else None
    )
    benchmark_cumulative_delta_ha = (
        target_remaining_area_ha - float(benchmark_cumulative_area_ha)
        if benchmark_cumulative_area_ha is not None
        else None
    )
    smoke_benchmark_scale_factor: float | None = None
    scaled_benchmark_marginal_area_ha: float | None = None
    scaled_benchmark_cumulative_area_ha: float | None = None
    scaled_benchmark_marginal_delta_ha: float | None = None
    scaled_benchmark_cumulative_delta_ha: float | None = None
    if (
        (selected_landscape_units or selected_map_ids)
        and total_area_benchmark_ha is not None
        and total_area_benchmark_ha > 0.0
    ):
        smoke_benchmark_scale_factor = input_area_ha / total_area_benchmark_ha
        if benchmark_marginal_area_ha is not None:
            scaled_benchmark_marginal_area_ha = (
                float(benchmark_marginal_area_ha) * smoke_benchmark_scale_factor
            )
            scaled_benchmark_marginal_delta_ha = (
                target_removed_area_ha - scaled_benchmark_marginal_area_ha
            )
        if benchmark_cumulative_area_ha is not None:
            scaled_benchmark_cumulative_area_ha = (
                float(benchmark_cumulative_area_ha) * smoke_benchmark_scale_factor
            )
            scaled_benchmark_cumulative_delta_ha = (
                target_remaining_area_ha - scaled_benchmark_cumulative_area_ha
            )
    target_notes = _dedupe_runtime_notes(target_notes)
    executed_item_summaries = _summarize_executed_items(executed_items)
    result = TsrThlbParentStepRunResult(
        recipe_path=recipe_path.expanduser().resolve(),
        parent_step_id=parent_step_id,
        parent_label=target_label,
        tsa=recipe.tsa,
        checkpoint_path=resolved_checkpoint_path,
        selected_map_ids=selected_map_ids,
        selected_landscape_units=selected_landscape_units,
        output_path=output_path,
        result_json_path=result_json_path,
        status=final_status,
        executed_parent_step_ids=tuple(executed_parent_step_ids),
        input_area_ha=input_area_ha,
        removed_area_ha=target_removed_area_ha,
        remaining_area_ha=target_remaining_area_ha,
        benchmark_marginal_area_ha=float(benchmark_marginal_area_ha)
        if benchmark_marginal_area_ha is not None
        else None,
        benchmark_cumulative_area_ha=float(benchmark_cumulative_area_ha)
        if benchmark_cumulative_area_ha is not None
        else None,
        benchmark_marginal_delta_ha=benchmark_marginal_delta_ha,
        benchmark_cumulative_delta_ha=benchmark_cumulative_delta_ha,
        smoke_benchmark_scale_factor=smoke_benchmark_scale_factor,
        scaled_benchmark_marginal_area_ha=scaled_benchmark_marginal_area_ha,
        scaled_benchmark_cumulative_area_ha=scaled_benchmark_cumulative_area_ha,
        scaled_benchmark_marginal_delta_ha=scaled_benchmark_marginal_delta_ha,
        scaled_benchmark_cumulative_delta_ha=scaled_benchmark_cumulative_delta_ha,
        notes=tuple(target_notes),
        execution_mode=execution_mode,
        worker_count=worker_count,
        lu_chunk_count=lu_chunk_count,
        lu_bundle_count=resolved_lu_bundle_count,
        progress_root=resolved_progress_root,
        profiling=profiling,
    )
    profiling["total_seconds"] = perf_counter() - total_started
    result_json_write_started = perf_counter()
    result_json_path.write_text(
        json.dumps(
            {
                **result.to_dict(),
                "executed_items": executed_items,
                "executed_item_summaries": executed_item_summaries,
            },
            indent=2,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    profiling["result_json_write_seconds"] = perf_counter() - result_json_write_started
    if not persist_recipe_update:
        profiling["total_seconds"] = perf_counter() - total_started
        return result
    resolved_recipe_path = recipe_path.expanduser().resolve()
    payload = recipe.to_dict()
    payload_parent_steps_raw = payload.get("parent_steps", ())
    payload_parent_steps: list[dict[str, Any]] = []
    if isinstance(payload_parent_steps_raw, (list, tuple)):
        payload_parent_steps = [
            dict(item) for item in payload_parent_steps_raw if isinstance(item, dict)
        ]
    for payload_parent_step in payload_parent_steps:
        if str(payload_parent_step.get("parent_step_id", "")).strip() != parent_step_id:
            continue
        payload_parent_step["last_notebook_run_status"] = final_status
        payload_parent_step["last_notebook_run_result_json_path"] = str(
            result_json_path.relative_to(instance_root).as_posix()
        )
        payload_parent_step["last_notebook_run_output_path"] = str(
            output_path.relative_to(instance_root).as_posix()
        )
        payload_parent_step["last_selected_map_ids"] = list(selected_map_ids)
        payload_parent_step["last_selected_landscape_units"] = list(
            selected_landscape_units
        )
        payload_parent_step["last_input_area_ha"] = input_area_ha
        payload_parent_step["last_removed_area_ha"] = target_removed_area_ha
        payload_parent_step["last_remaining_area_ha"] = target_remaining_area_ha
        payload_parent_step["last_benchmark_marginal_delta_ha"] = (
            benchmark_marginal_delta_ha
        )
        payload_parent_step["last_benchmark_cumulative_delta_ha"] = (
            benchmark_cumulative_delta_ha
        )
        payload_parent_step["ratchet_state"] = _infer_thlb_parent_step_ratchet_state(
            payload_parent_step
        )
        break
    payload["parent_steps"] = payload_parent_steps
    recipe_contract_raw = payload.get("recipe_contract", {})
    recipe_contract = (
        dict(recipe_contract_raw) if isinstance(recipe_contract_raw, dict) else {}
    )
    recipe_contract["last_parent_step_run_utc"] = datetime.now(UTC).isoformat()
    payload["recipe_contract"] = recipe_contract
    recipe_update_started = perf_counter()
    _write_recipe_yaml(resolved_recipe_path, payload)
    updated_recipe = load_tsr_thlb_netdown_recipe(resolved_recipe_path)
    profiling["recipe_update_seconds"] = perf_counter() - recipe_update_started
    recipe_build_status_report_value = str(
        recipe_contract.get("recipe_build_status_report_path", "")
    ).strip()
    if recipe_build_status_report_value:
        report_refresh_started = perf_counter()
        recipe_build_status_report_path = _resolve_instance_path(
            instance_root, recipe_build_status_report_value
        )
        recipe_build_runtime_status_report_value = str(
            recipe_contract.get("recipe_build_runtime_status_report_path", "")
        ).strip()
        runtime_report_relative_path = (
            recipe_build_runtime_status_report_value
            if recipe_build_runtime_status_report_value
            else recipe_build_status_report_value
        )
        refreshed_markdown = _build_tsr_thlb_recipe_build_report_markdown(
            recipe=updated_recipe,
            recipe_relative_path=str(
                resolved_recipe_path.relative_to(instance_root).as_posix()
            ),
            source_layer_recipe_relative_path=updated_recipe.instance_inputs.source_layer_recipe_path,
            generated_utc=datetime.now(UTC).isoformat(),
            runtime_report_relative_path=runtime_report_relative_path,
            source_entry_map=source_entry_map,
            override_entries=override_entries,
        )
        recipe_build_status_report_path.parent.mkdir(parents=True, exist_ok=True)
        recipe_build_status_report_path.write_text(refreshed_markdown, encoding="utf-8")
        profiling["report_refresh_seconds"] = perf_counter() - report_refresh_started
    profiling["total_seconds"] = perf_counter() - total_started
    return result


def _summarize_parallel_benchmark_markdown(
    *,
    recipe_path: Path,
    landscape_units: Sequence[str],
    run_results: Sequence[TsrThlbParallelBenchmarkRunResult],
) -> str:
    lines = [
        "# TSA29 THLB LU-Parallel Benchmark",
        "",
        f"- Recipe: `{recipe_path}`",
        f"- Landscape units: `{', '.join(landscape_units) if landscape_units else 'all intersecting LUs'}`",
        "",
    ]
    if landscape_units:
        lines.extend(
            [
                "- Note: partial-LU benchmark parity assumes the serial reference covers the",
                "  same selected LU union. Any remaining drift is a clipping/merge warning,",
                "  not evidence that LU-parallel is semantically acceptable yet.",
                "",
            ]
        )
    grouped: dict[str, list[TsrThlbParallelBenchmarkRunResult]] = {}
    for item in run_results:
        grouped.setdefault(item.parent_step_id, []).append(item)
    for parent_step_id, group in grouped.items():
        ordered = sorted(
            group,
            key=lambda item: (
                0
                if item.execution_mode == TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL
                else 1,
                item.worker_count,
            ),
        )
        label = ordered[0].parent_label
        lines.append(f"## {label}")
        lines.append("")
        serial = next(
            (
                item
                for item in ordered
                if item.execution_mode == TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL
            ),
            None,
        )
        for item in ordered:
            speedup = (
                serial.wall_time_seconds / item.wall_time_seconds
                if serial is not None and item.wall_time_seconds > 0
                else None
            )
            lines.extend(
                [
                    f"- backend=`{item.execution_mode}` workers=`{item.worker_count}` lu_count=`{item.lu_count}`",
                    f"  - runtime: `{item.wall_time_seconds:.3f} s`",
                    f"  - removed area: `{item.removed_area_ha:.3f} ha`",
                    f"  - remaining area: `{item.remaining_area_ha:.3f} ha`",
                    f"  - output rows: `{item.output_row_count}`",
                    f"  - parity with serial: `{item.parity_with_serial}`",
                ]
            )
            if speedup is not None:
                lines.append(f"  - speedup vs serial: `{speedup:.3f}x`")
            if item.parity_removed_area_delta_ha is not None:
                lines.append(
                    "  - parity deltas: "
                    f"removed=`{item.parity_removed_area_delta_ha:.6f} ha` "
                    f"remaining=`{item.parity_remaining_area_delta_ha:.6f} ha`"
                )
            recommendation = "neutral"
            if item.execution_mode == TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL:
                if item.parity_with_serial is False:
                    recommendation = "not worth adopting"
                elif speedup is not None and speedup > 1.2:
                    recommendation = "promising"
                elif speedup is not None and speedup <= 1.0:
                    recommendation = "not worth adopting"
            lines.append(f"  - recommendation: `{recommendation}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_tsr_thlb_parallel_benchmark(
    *,
    recipe_path: Path,
    parent_step_ids: Sequence[str],
    checkpoint_path: Path | None = None,
    landscape_units: Sequence[str] = (),
    worker_counts: Sequence[int] = (1, 2, 4, 8),
) -> TsrThlbParallelBenchmarkResult:
    """Benchmark serial vs LU-parallel THLB parent-step execution."""

    if not parent_step_ids:
        raise TsrRecipeError(
            "At least one parent step id is required for benchmark runs."
        )
    recipe, instance_root, _source_recipe, _source_entry_map, _override_entries = (
        _load_tsr_thlb_recipe_context(recipe_path)
    )
    runtime_root = default_tsr_thlb_parallel_benchmark_root(instance_root=instance_root)
    runtime_root.mkdir(parents=True, exist_ok=True)
    resolved_checkpoint_path = (
        checkpoint_path.expanduser().resolve() if checkpoint_path is not None else None
    )
    selected_landscape_units: tuple[str, ...] = tuple(
        str(value).strip() for value in landscape_units if str(value).strip()
    )
    run_records: list[TsrThlbParallelBenchmarkRunResult] = []
    for parent_step_id in parent_step_ids:
        serial_started = perf_counter()
        serial_result = run_tsr_thlb_parent_step(
            recipe_path=recipe_path,
            parent_step_id=parent_step_id,
            checkpoint_path=resolved_checkpoint_path,
            landscape_units=selected_landscape_units,
            auto_map_id_smoke_subset=False,
            execution_mode=TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
            persist_recipe_update=False,
        )
        serial_elapsed = perf_counter() - serial_started
        serial_record = TsrThlbParallelBenchmarkRunResult(
            parent_step_id=serial_result.parent_step_id,
            parent_label=serial_result.parent_label,
            execution_mode=TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
            worker_count=1,
            lu_count=max(1, len(serial_result.selected_landscape_units)),
            wall_time_seconds=serial_elapsed,
            peak_memory_mb=None,
            status=serial_result.status,
            input_area_ha=serial_result.input_area_ha,
            removed_area_ha=serial_result.removed_area_ha,
            remaining_area_ha=serial_result.remaining_area_ha,
            output_row_count=len(gpd.read_feather(serial_result.output_path)),
            result_json_path=serial_result.result_json_path,
            output_path=serial_result.output_path,
            parity_with_serial=True,
            parity_removed_area_delta_ha=0.0,
            parity_remaining_area_delta_ha=0.0,
            notes=serial_result.notes,
        )
        run_records.append(serial_record)
        active_lus = (
            serial_result.selected_landscape_units
            if serial_result.selected_landscape_units
            else selected_landscape_units
        )
        for workers in worker_counts:
            if workers <= 0:
                continue
            started = perf_counter()
            parallel_result = run_tsr_thlb_parent_step(
                recipe_path=recipe_path,
                parent_step_id=parent_step_id,
                checkpoint_path=resolved_checkpoint_path,
                landscape_units=active_lus,
                auto_map_id_smoke_subset=False,
                execution_mode=TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL,
                max_workers=workers,
                persist_recipe_update=False,
            )
            elapsed = perf_counter() - started
            removed_delta = (
                parallel_result.removed_area_ha - serial_result.removed_area_ha
            )
            remaining_delta = (
                parallel_result.remaining_area_ha - serial_result.remaining_area_ha
            )
            parity = abs(removed_delta) <= 1e-6 and abs(remaining_delta) <= 1e-6
            run_records.append(
                TsrThlbParallelBenchmarkRunResult(
                    parent_step_id=parallel_result.parent_step_id,
                    parent_label=parallel_result.parent_label,
                    execution_mode=TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL,
                    worker_count=workers,
                    lu_count=parallel_result.lu_chunk_count or len(active_lus),
                    wall_time_seconds=elapsed,
                    peak_memory_mb=None,
                    status=parallel_result.status,
                    input_area_ha=parallel_result.input_area_ha,
                    removed_area_ha=parallel_result.removed_area_ha,
                    remaining_area_ha=parallel_result.remaining_area_ha,
                    output_row_count=len(gpd.read_feather(parallel_result.output_path)),
                    result_json_path=parallel_result.result_json_path,
                    output_path=parallel_result.output_path,
                    parity_with_serial=parity,
                    parity_removed_area_delta_ha=removed_delta,
                    parity_remaining_area_delta_ha=remaining_delta,
                    notes=parallel_result.notes,
                )
            )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    summary_path = runtime_root / f"thlb_parallel_benchmark.{timestamp}.md"
    summary_path.write_text(
        _summarize_parallel_benchmark_markdown(
            recipe_path=recipe_path,
            landscape_units=selected_landscape_units,
            run_results=run_records,
        ),
        encoding="utf-8",
    )
    return TsrThlbParallelBenchmarkResult(
        summary_path=summary_path,
        run_results=tuple(run_records),
        parent_step_ids=tuple(parent_step_ids),
        landscape_units=selected_landscape_units,
    )


def _build_thlb_parent_step_code_cell(
    parent_step: dict[str, Any],
    *,
    tsa_code: str,
) -> str:
    parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
    label = str(parent_step.get("parent_label", "")).strip()
    benchmark_marginal = parent_step.get("benchmark_marginal_area_ha")
    benchmark_cumulative = parent_step.get("benchmark_cumulative_area_ha")
    compiled_logic = [
        dict(item)
        for item in parent_step.get("compiled_logic", ())
        if isinstance(item, dict)
    ]
    compiled_logic_summary = [
        {
            "step_id": str(item.get("step_id", "")).strip(),
            "label": str(item.get("label", "")).strip(),
            "operation_type": (
                str(item.get("compiled_operation_type", "")).strip()
                or str(item.get("operation_type", "")).strip()
            ),
            "linked_source_entry_ids": [
                str(value).strip()
                for value in item.get("linked_source_entry_ids", ())
                if str(value).strip()
            ],
            "step_status": str(item.get("step_status", "")).strip(),
        }
        for item in compiled_logic
    ]
    is_full_tsa_parallel_default = (
        tsa_code == "29"
        and parent_step_id == "thlb_parent_006_parks_protected_areas_area_base_tenures"
    )
    default_landscape_unit_scope = (
        "()"
        if is_full_tsa_parallel_default
        else '("Williams Lake",)'
        if tsa_code == "29"
        else "()"
    )
    default_execution_mode = (
        TSR_THLB_PARENT_STEP_EXECUTION_MODE_LU_PARALLEL
        if is_full_tsa_parallel_default
        else TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL
    )
    default_auto_map_id = "False" if is_full_tsa_parallel_default else "True"
    lines = [
        "# Auto-generated FEMIC THLB workbench cell.",
        "# Teach Baby Groot what the prototype fin looks like:",
        "# keep the parent step anchored on the summary-table row, then",
        "# translate its nested subrules into deterministic compiled logic.",
        "from pathlib import Path",
        "from datetime import UTC, datetime",
        "import json",
        "import threading",
        "import time",
        "try:",
        "    from femic.tsr_catalog import (",
        "        resolve_tsr_workbench_instance_root,",
        "        run_tsr_thlb_parent_step,",
        "    )",
        "except ImportError:",
        "    from femic.tsr_catalog.recipes import (",
        "        resolve_tsr_workbench_instance_root,",
        "        run_tsr_thlb_parent_step,",
        "    )",
        "",
        f'PARENT_STEP_ID = "{parent_step_id}"',
        f'PARENT_LABEL = "{label.replace(chr(34), chr(39))}"',
        f"BENCHMARK_MARGINAL_AREA_HA = {repr(benchmark_marginal)}",
        f"BENCHMARK_CUMULATIVE_AREA_HA = {repr(benchmark_cumulative)}",
        'INSTANCE_ROOT = resolve_tsr_workbench_instance_root(start=Path(".").resolve())',
        'RECIPE_PATH = INSTANCE_ROOT / "config" / "tsr" / "thlb_netdown.recipe.yaml"',
        f"AUTO_MAP_ID_SMOKE_SUBSET = {default_auto_map_id}",
        "MAP_ID_SCOPE: tuple[str, ...] = ()",
        f"LANDSCAPE_UNIT_SCOPE: tuple[str, ...] = {default_landscape_unit_scope}",
        f'EXECUTION_MODE = "{default_execution_mode}"',
        "MAX_WORKERS = 8",
        "LU_BUNDLE_COUNT = 8",
        "PERSIST_RECIPE_UPDATE = False",
        "SHOW_PROGRESS = EXECUTION_MODE == 'lu_parallel'",
        "if LANDSCAPE_UNIT_SCOPE:\n    AUTO_MAP_ID_SMOKE_SUBSET = False",
        'RUN_TIMESTAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")',
        (
            'PROGRESS_ROOT = INSTANCE_ROOT / "runtime" / "logs" / "tsr" / '
            '"notebook_progress" / f"{PARENT_STEP_ID}.{RUN_TIMESTAMP}"'
        ),
        "",
        "# Human reviewers are not expected to read raw machine-oriented list-of-dict",
        "# compiled logic here. Review the Markdown status report for the narrative",
        "# explanation and use this compact summary only as an execution cheat sheet.",
        "compiled_logic_summary = [",
    ]
    for item in compiled_logic_summary:
        lines.append(f"    {repr(item)},")
    lines.extend(
        [
            "]",
            "",
            "try:",
            "    import ipywidgets as widgets",
            "    from IPython.display import display",
            "except ImportError:",
            "    widgets = None",
            "    display = None",
            "",
            "bars = []",
            "status_lines = []",
            "if SHOW_PROGRESS and widgets is not None:",
            "    rows = []",
            "    for worker_index in range(max(1, LU_BUNDLE_COUNT)):",
            "        title = widgets.HTML(f'<b>Worker {worker_index + 1}</b>')",
            "        bar = widgets.FloatProgress(value=0.0, min=0.0, max=1.0)",
            "        status = widgets.HTML('waiting for assignment')",
            "        rows.append(widgets.VBox([title, bar, status]))",
            "        bars.append((bar, status))",
            "    display(widgets.VBox(rows))",
            "elif SHOW_PROGRESS:",
            "    print('ipywidgets not available; falling back to text progress polling.')",
            "",
            "run_state = {}",
            "",
            "def _worker_run():",
            "    try:",
            "        run_state['result'] = run_tsr_thlb_parent_step(",
            "            recipe_path=RECIPE_PATH,",
            "            parent_step_id=PARENT_STEP_ID,",
            "            map_ids=MAP_ID_SCOPE,",
            "            landscape_units=LANDSCAPE_UNIT_SCOPE,",
            "            auto_map_id_smoke_subset=AUTO_MAP_ID_SMOKE_SUBSET,",
            "            execution_mode=EXECUTION_MODE,",
            "            max_workers=MAX_WORKERS,",
            "            lu_bundle_count=LU_BUNDLE_COUNT,",
            "            progress_root=PROGRESS_ROOT,",
            "            persist_recipe_update=PERSIST_RECIPE_UPDATE,",
            "        )",
            "    except Exception as exc:",
            "        run_state['error'] = exc",
            "",
            "worker_thread = threading.Thread(target=_worker_run, daemon=True)",
            "worker_thread.start()",
            "",
            "def _poll_progress():",
            "    progress_files = sorted(PROGRESS_ROOT.glob('*.json')) if PROGRESS_ROOT.exists() else []",
            "    snapshots = []",
            "    for progress_file in progress_files:",
            "        try:",
            "            snapshots.append(json.loads(progress_file.read_text(encoding='utf-8')))",
            "        except Exception:",
            "            continue",
            "    snapshots.sort(key=lambda item: int(item.get('bundle_index', 0) or 0))",
            "    return snapshots",
            "",
            "while worker_thread.is_alive():",
            "    snapshots = _poll_progress()",
            "    if bars:",
            "        for index, (bar, status) in enumerate(bars, start=1):",
            "            if index <= len(snapshots):",
            "                snapshot = snapshots[index - 1]",
            "                bar.value = float(snapshot.get('fraction_complete', 0.0) or 0.0)",
            "                current_lu = snapshot.get('current_lu') or 'idle'",
            "                completed = int(snapshot.get('completed_lus', 0) or 0)",
            "                total = int(snapshot.get('total_lus', 0) or 0)",
            "                state = str(snapshot.get('status', '') or 'running')",
            '                status.value = f"{state}: {completed}/{total} LUs, current={current_lu}"',
            "            else:",
            "                bar.value = 0.0",
            "                status.value = 'waiting for assignment'",
            "    elif SHOW_PROGRESS:",
            "        if snapshots:",
            "            latest = [",
            "                f\"worker {int(item.get('bundle_index', 0) or 0)}: {int(item.get('completed_lus', 0) or 0)}/{int(item.get('total_lus', 0) or 0)}\"",
            "                for item in snapshots",
            "            ]",
            "            latest_line = ' | '.join(latest)",
            "            if not status_lines or latest_line != status_lines[-1]:",
            "                print(latest_line)",
            "                status_lines.append(latest_line)",
            "    time.sleep(0.5)",
            "",
            "worker_thread.join()",
            "snapshots = _poll_progress()",
            "if bars:",
            "    for index, (bar, status) in enumerate(bars, start=1):",
            "        if index <= len(snapshots):",
            "            snapshot = snapshots[index - 1]",
            "            bar.value = float(snapshot.get('fraction_complete', 0.0) or 0.0)",
            "            state = str(snapshot.get('status', '') or 'completed')",
            "            completed = int(snapshot.get('completed_lus', 0) or 0)",
            "            total = int(snapshot.get('total_lus', 0) or 0)",
            '            status.value = f"{state}: {completed}/{total} LUs"',
            "",
            "if 'error' in run_state:",
            "    raise run_state['error']",
            "result = run_state['result']",
            "payload = result.to_dict()",
            "payload['compiled_logic_summary'] = compiled_logic_summary",
            "payload['persist_recipe_update'] = PERSIST_RECIPE_UPDATE",
            "print(json.dumps(payload, indent=2))",
        ]
    )
    return "\n".join(lines)


def _build_tsr_thlb_workbench_notebook(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    recipe_relative_path: str,
    status_report_relative_path: str,
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> nbformat.NotebookNode:
    milestones, parent_stage_groups = _parent_steps_grouped_by_stage(recipe)
    cells: list[nbformat.NotebookNode] = [
        new_markdown_cell(
            "\n".join(
                [
                    f"# THLB Netdown Workbench: TSA {recipe.tsa.tsa_code} ({recipe.tsa.tsa_name})",
                    "",
                    "This notebook is a generated bridge artifact for iterative THLB review.",
                    "",
                    f"- Canonical recipe: `{recipe_relative_path}`",
                    f"- Current status report: `{status_report_relative_path}`",
                    "- Canonicality contract: recipe YAML + script during iteration; "
                    "locked script + frozen report at approval time.",
                ]
            )
        ),
        new_markdown_cell(
            "\n".join(
                [
                    "## Backbone Summary",
                    "",
                    "Use the GLB -> AFLB -> LHLB -> THLB ladder as the governing structure.",
                    "Milestones are nodes. Parent steps are the transformation arcs between them.",
                ]
            )
        ),
    ]
    if milestones:
        milestone_lines = ["## Backbone Milestones", ""]
        for milestone in milestones:
            label = str(milestone.get("parent_label", "")).strip()
            benchmark_cumulative = milestone.get("benchmark_cumulative_area_ha")
            stage_label = _stage_header_text(str(milestone.get("land_base_stage", "")))
            milestone_lines.append(f"- **{label}** (`{stage_label}`)")
            if benchmark_cumulative is not None:
                milestone_lines.append(
                    f"  - benchmark cumulative area: `{float(benchmark_cumulative):.3f} ha`"
                )
        cells.append(new_markdown_cell("\n".join(milestone_lines)))

    for stage in _THLB_STAGE_ORDER:
        parent_steps = parent_stage_groups.get(stage, [])
        if not parent_steps:
            continue
        cells.append(new_markdown_cell(f"## {_stage_header_text(stage)}"))
        for parent_step in parent_steps:
            cells.append(
                new_markdown_cell(
                    "\n".join(
                        _format_thlb_parent_step_markdown(
                            parent_step=parent_step,
                            compiled_step_map={
                                str(parent_step.get("parent_step_id", "")): [
                                    dict(item)
                                    for item in parent_step.get("compiled_logic", ())
                                    if isinstance(item, dict)
                                ]
                            },
                            source_entry_map=source_entry_map,
                            override_entries=override_entries,
                        )
                    )
                )
            )
            cells.append(
                new_code_cell(
                    _build_thlb_parent_step_code_cell(
                        parent_step,
                        tsa_code=recipe.tsa.tsa_code,
                    )
                )
            )
            cells.append(
                new_markdown_cell(
                    "\n".join(
                        [
                            "### Interpretation notes",
                            "",
                            "- Human review notes:",
                            "- LLM draft notes:",
                            "- Benchmark comparison:",
                            "- Decision: good enough to keep going, or iterate again?",
                        ]
                    )
                )
            )
    return new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
            "femic": {
                "artifact_kind": "thlb_workbench",
                "recipe_kind": recipe.recipe_kind,
                "tsa_id": recipe.tsa.tsa_id,
                "tsa_code": recipe.tsa.tsa_code,
            },
        },
    )


def _build_tsr_thlb_locked_script_text(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    locked_recipe_relative_path: str,
    frozen_status_report_relative_path: str,
    frozen_audit_relative_path: str | None,
    notebook_relative_path: str,
    lock_scope: str,
) -> str:
    stage_counts = Counter(
        str(parent.get("land_base_stage", "context"))
        for parent in recipe.parent_steps
        if str(parent.get("parent_kind", "")) != "milestone"
    )
    lines = [
        '"""Locked THLB reproducibility script generated by FEMIC."""',
        "",
        "from __future__ import annotations",
        "",
        "from pathlib import Path",
        "import json",
        "import yaml",
        "",
        f'LOCK_SCOPE = "{lock_scope}"',
        f'TSA_ID = "{recipe.tsa.tsa_id}"',
        f'TSA_CODE = "{recipe.tsa.tsa_code}"',
        f'TSA_NAME = "{recipe.tsa.tsa_name}"',
        f'LOCKED_RECIPE_RELATIVE_PATH = "{locked_recipe_relative_path}"',
        f'FROZEN_STATUS_REPORT_RELATIVE_PATH = "{frozen_status_report_relative_path}"',
        f"FROZEN_AUDIT_RELATIVE_PATH = {repr(frozen_audit_relative_path)}",
        f'WORKBENCH_NOTEBOOK_RELATIVE_PATH = "{notebook_relative_path}"',
        f"STAGE_COUNTS = {dict(sorted(stage_counts.items()))!r}",
        "",
        "",
        "def main() -> None:",
        "    root = Path(__file__).resolve().parents[2]",
        "    recipe_path = root / LOCKED_RECIPE_RELATIVE_PATH",
        "    status_report_path = root / FROZEN_STATUS_REPORT_RELATIVE_PATH",
        "    payload = yaml.safe_load(recipe_path.read_text(encoding='utf-8'))",
        "    print(f'locked_scope: {LOCK_SCOPE}')",
        "    print(f'tsa: {TSA_CODE} {TSA_NAME}')",
        "    print(f'locked_recipe: {recipe_path}')",
        "    print(f'frozen_status_report: {status_report_path}')",
        "    if FROZEN_AUDIT_RELATIVE_PATH:",
        "        print(f'frozen_audit: {root / FROZEN_AUDIT_RELATIVE_PATH}')",
        "    print('stage_counts: ' + json.dumps(STAGE_COUNTS, sort_keys=True))",
        "    print('parent_step_count: ' + str(len(payload.get('parent_steps', []))))",
        "",
        "",
        "if __name__ == '__main__':",
        "    main()",
        "",
    ]
    return "\n".join(lines)


def build_tsr_thlb_workbench(
    *,
    recipe_path: Path,
    notebook_path: Path | None = None,
) -> TsrThlbWorkbenchBuildResult:
    """Generate an instance-local THLB workbench notebook from the recipe."""

    (
        recipe,
        instance_root,
        _source_recipe,
        source_entry_map,
        override_entries,
    ) = _load_tsr_thlb_recipe_context(recipe_path)
    resolved_recipe_path = recipe_path.expanduser().resolve()
    resolved_notebook_path = (
        notebook_path.expanduser().resolve()
        if notebook_path is not None
        else default_tsr_thlb_workbench_notebook_path(instance_root=instance_root)
    )
    status_report_path = _detect_current_thlb_status_report_path(
        instance_root=instance_root,
        recipe_contract=dict(recipe.recipe_contract),
    )
    notebook = _build_tsr_thlb_workbench_notebook(
        recipe=recipe,
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        status_report_relative_path=str(
            status_report_path.relative_to(instance_root).as_posix()
        ),
        source_entry_map=source_entry_map,
        override_entries=override_entries,
    )
    resolved_notebook_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_notebook_path.write_text(nbformat.writes(notebook), encoding="utf-8")

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["workbench_notebook_path"] = str(
        resolved_notebook_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["workbench_last_built_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["lock_state"] = _current_thlb_lock_state(recipe_contract)
    payload["recipe_contract"] = recipe_contract
    _write_recipe_yaml(resolved_recipe_path, payload)

    stage_counts = Counter(
        str(parent.get("land_base_stage", "context"))
        for parent in recipe.parent_steps
        if str(parent.get("parent_kind", "")) != "milestone"
    )
    compiled_logic_count = sum(
        len(
            [
                item
                for item in parent.get("compiled_logic", ())
                if isinstance(item, dict)
            ]
        )
        for parent in recipe.parent_steps
    )
    return TsrThlbWorkbenchBuildResult(
        recipe_path=resolved_recipe_path,
        notebook_path=resolved_notebook_path,
        tsa=recipe.tsa,
        parent_step_count=len(recipe.parent_steps),
        compiled_logic_count=compiled_logic_count,
        stage_counts=dict(sorted(stage_counts.items())),
    )


def lock_tsr_thlb_workbench(
    *,
    recipe_path: Path,
    notebook_path: Path | None = None,
    lock_scope: str = "all",
) -> TsrThlbWorkbenchLockResult:
    """Freeze the current THLB workbench state into a deterministic script bundle."""

    normalized_scope = lock_scope.strip().casefold()
    if normalized_scope not in {"aflb", "thlb", "all"}:
        raise TsrRecipeError(
            "Invalid THLB workbench lock scope. Expected one of: aflb, thlb, all."
        )

    (
        recipe,
        instance_root,
        _source_recipe,
        _source_entry_map,
        _override_entries,
    ) = _load_tsr_thlb_recipe_context(recipe_path)
    resolved_recipe_path = recipe_path.expanduser().resolve()
    resolved_notebook_path = (
        notebook_path.expanduser().resolve()
        if notebook_path is not None
        else default_tsr_thlb_workbench_notebook_path(instance_root=instance_root)
    )
    if not resolved_notebook_path.exists():
        raise TsrRecipeError(
            "THLB workbench notebook is missing. Run "
            "`femic tsr thlb-netdown-workbench-build` first."
        )

    recipe_contract = dict(recipe.recipe_contract)
    lock_state = _current_thlb_lock_state(recipe_contract)
    if normalized_scope == "thlb" and not lock_state["aflb"]["locked"]:
        raise TsrRecipeError(
            "Cannot lock THLB before AFLB is locked. Lock AFLB first or use "
            "`--lock-scope all`."
        )

    status_report_path = _detect_current_thlb_status_report_path(
        instance_root=instance_root,
        recipe_contract=recipe_contract,
    )
    audit_path = _detect_current_thlb_audit_path(instance_root=instance_root)
    locked_script_path = default_tsr_thlb_workbench_locked_script_path(
        instance_root=instance_root
    )
    locked_recipe_path = default_tsr_thlb_workbench_locked_recipe_path(
        instance_root=instance_root
    )
    frozen_root = instance_root / "workbench" / "tsr" / "frozen"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    frozen_status_report_path = (
        frozen_root / f"thlb_netdown.status.locked-{timestamp}.md"
    )
    frozen_audit_path = (
        frozen_root / f"thlb_netdown.audit.locked-{timestamp}.json"
        if audit_path is not None
        else None
    )

    locked_recipe_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(resolved_recipe_path, locked_recipe_path)
    frozen_status_report_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(status_report_path, frozen_status_report_path)
    if audit_path is not None and frozen_audit_path is not None:
        shutil.copyfile(audit_path, frozen_audit_path)

    locked_script_text = _build_tsr_thlb_locked_script_text(
        recipe=recipe,
        locked_recipe_relative_path=str(
            locked_recipe_path.relative_to(instance_root).as_posix()
        ),
        frozen_status_report_relative_path=str(
            frozen_status_report_path.relative_to(instance_root).as_posix()
        ),
        frozen_audit_relative_path=(
            str(frozen_audit_path.relative_to(instance_root).as_posix())
            if frozen_audit_path is not None
            else None
        ),
        notebook_relative_path=str(
            resolved_notebook_path.relative_to(instance_root).as_posix()
        ),
        lock_scope=normalized_scope,
    )
    locked_script_path.parent.mkdir(parents=True, exist_ok=True)
    locked_script_path.write_text(locked_script_text, encoding="utf-8")

    locked_utc = datetime.now(UTC).isoformat()
    if normalized_scope in {"aflb", "all"}:
        lock_state["aflb"] = {
            "locked": True,
            "locked_utc": locked_utc,
            "locked_by": "femic tsr thlb-netdown-workbench-lock",
            "locked_script_path": str(
                locked_script_path.relative_to(instance_root).as_posix()
            ),
            "frozen_status_report_path": str(
                frozen_status_report_path.relative_to(instance_root).as_posix()
            ),
            "frozen_audit_path": (
                str(frozen_audit_path.relative_to(instance_root).as_posix())
                if frozen_audit_path is not None
                else None
            ),
            "note": "AFLB universe definition locked",
        }
        if normalized_scope == "aflb":
            lock_state["thlb"] = {
                "locked": False,
                "locked_utc": None,
                "locked_by": None,
                "locked_script_path": None,
                "frozen_status_report_path": None,
                "frozen_audit_path": None,
                "note": "THLB lock remains inactive until explicitly locked after AFLB",
            }
    if normalized_scope in {"thlb", "all"}:
        lock_state["thlb"] = {
            "locked": True,
            "locked_utc": locked_utc,
            "locked_by": "femic tsr thlb-netdown-workbench-lock",
            "locked_script_path": str(
                locked_script_path.relative_to(instance_root).as_posix()
            ),
            "frozen_status_report_path": str(
                frozen_status_report_path.relative_to(instance_root).as_posix()
            ),
            "frozen_audit_path": (
                str(frozen_audit_path.relative_to(instance_root).as_posix())
                if frozen_audit_path is not None
                else None
            ),
            "note": (
                "THLB lock depends on the AFLB lock; cutting AFLB invalidates THLB."
            ),
        }

    payload = recipe.to_dict()
    recipe_contract["workbench_notebook_path"] = str(
        resolved_notebook_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["locked_script_path"] = str(
        locked_script_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["locked_recipe_path"] = str(
        locked_recipe_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["latest_frozen_status_report_path"] = str(
        frozen_status_report_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["latest_frozen_audit_path"] = (
        str(frozen_audit_path.relative_to(instance_root).as_posix())
        if frozen_audit_path is not None
        else ""
    )
    recipe_contract["lock_state"] = lock_state
    payload["recipe_contract"] = recipe_contract
    _write_recipe_yaml(resolved_recipe_path, payload)

    return TsrThlbWorkbenchLockResult(
        recipe_path=resolved_recipe_path,
        notebook_path=resolved_notebook_path,
        locked_script_path=locked_script_path,
        locked_recipe_path=locked_recipe_path,
        frozen_status_report_path=frozen_status_report_path,
        frozen_audit_path=frozen_audit_path,
        tsa=recipe.tsa,
        lock_scope=normalized_scope,
    )


def _resolve_source_artifact_path(
    *,
    instance_root: Path,
    source_entry: dict[str, Any],
) -> Path | None:
    artifact_path = str(source_entry.get("artifact_path", "")).strip()
    if not artifact_path:
        return None
    candidate = instance_root / artifact_path
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        return None
    return resolved


def _load_exclusion_geometries(
    *,
    instance_root: Path,
    linked_source_entry_ids: tuple[str, ...],
    source_entry_map: dict[str, dict[str, Any]],
    preserve_attributes: bool = False,
    allowed_geom_types: tuple[str, ...] = ("Polygon", "MultiPolygon"),
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[gpd.GeoDataFrame | None, list[str]]:
    frames: list[gpd.GeoDataFrame] = []
    missing_sources: list[str] = []
    found_artifact = False
    for entry_id in linked_source_entry_ids:
        source_entry = source_entry_map.get(entry_id)
        if source_entry is None:
            missing_sources.append(entry_id)
            continue
        artifact_path = _resolve_source_artifact_path(
            instance_root=instance_root,
            source_entry=source_entry,
        )
        if artifact_path is None:
            missing_sources.append(entry_id)
            continue
        found_artifact = True
        try:
            read_kwargs: dict[str, Any] = {}
            if bbox is not None:
                read_kwargs["engine"] = "pyogrio"
                read_kwargs["bbox"] = bbox
            layer = gpd.read_file(artifact_path, **read_kwargs)
        except Exception:  # pragma: no cover - runtime seam
            missing_sources.append(entry_id)
            continue
        if "geometry" not in layer.columns:
            missing_sources.append(entry_id)
            continue
        if layer.empty:
            continue
        layer = layer.copy()
        if layer.crs is None:
            layer = layer.set_crs(BC_ALBERS_EPSG)
        else:
            layer = layer.to_crs(BC_ALBERS_EPSG)
        keep_columns = list(layer.columns) if preserve_attributes else ["geometry"]
        layer = layer[keep_columns].dropna(subset=["geometry"])
        layer = layer.loc[~layer.geometry.is_empty]
        layer = layer.loc[layer.geometry.geom_type.isin(list(allowed_geom_types))]
        if layer.empty:
            continue
        frames.append(layer)
    if not frames:
        if found_artifact and not missing_sources:
            empty_geometry = gpd.GeoDataFrame(
                geometry=gpd.GeoSeries([], crs=BC_ALBERS_EPSG),
                crs=BC_ALBERS_EPSG,
            )
            return empty_geometry, missing_sources
        return None, missing_sources
    if preserve_attributes:
        merged = gpd.GeoDataFrame(
            pd.concat(frames, ignore_index=True),
            geometry="geometry",
            crs=BC_ALBERS_EPSG,
        )
    else:
        merged = gpd.GeoDataFrame(
            geometry=gpd.GeoSeries(
                [geom for frame in frames for geom in frame.geometry],
                crs=BC_ALBERS_EPSG,
            ),
            crs=BC_ALBERS_EPSG,
        )
    return merged, missing_sources


def _compute_exclusion_fraction(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> dict[int, float]:
    if checkpoint.empty or exclusion_geometries.empty:
        return {}
    candidate_indices = checkpoint.sindex.query(
        exclusion_geometries.geometry, predicate="intersects"
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return {}
    candidate = checkpoint.iloc[unique_indices][
        ["_row_id", "_stand_area_sqm", "geometry"]
    ].copy()
    intersections = gpd.overlay(
        candidate[["_row_id", "geometry"]],
        exclusion_geometries[["geometry"]],
        how="intersection",
        keep_geom_type=False,
    )
    if intersections.empty:
        return {}
    intersection_area = intersections.geometry.area.groupby(
        intersections["_row_id"]
    ).sum()
    stand_area = candidate.set_index("_row_id")["_stand_area_sqm"].reindex(
        intersection_area.index
    )
    fraction = (intersection_area / stand_area).clip(lower=0.0, upper=1.0)
    return {int(key): float(value) for key, value in fraction.items()}


def _count_exclusion_candidate_rows(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
) -> int:
    if checkpoint.empty or exclusion_geometries.empty:
        return 0
    candidate_indices = checkpoint.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    return len({int(index) for index in candidate_values.tolist()})


def _managed_area_ha(checkpoint: gpd.GeoDataFrame) -> float:
    return float(
        (checkpoint["_stand_area_sqm"] * checkpoint["thlb_fact"]).sum() / 10000.0
    )


def _apply_aspatial_thlb_reduction(
    checkpoint: gpd.GeoDataFrame,
    *,
    target_removed_area_ha: float,
) -> tuple[gpd.GeoDataFrame, float, int]:
    if checkpoint.empty or target_removed_area_ha <= 0.0:
        return checkpoint, 0.0, 0
    current_managed_area_ha = _managed_area_ha(checkpoint)
    if current_managed_area_ha <= 0.0:
        return checkpoint, 0.0, 0
    removed_area_ha = min(float(target_removed_area_ha), current_managed_area_ha)
    keep_factor = (current_managed_area_ha - removed_area_ha) / current_managed_area_ha
    updated = checkpoint.copy()
    active_mask = updated["thlb_fact"].astype(float) > 0.0
    if not active_mask.any():
        return checkpoint, 0.0, 0
    if "thlb" in updated.columns:
        updated["thlb"] = updated["thlb"].astype(float)
    updated.loc[active_mask, "thlb_fact"] = (
        updated.loc[active_mask, "thlb_fact"].astype(float) * keep_factor
    )
    updated.loc[active_mask, "thlb"] = updated.loc[active_mask, "thlb_fact"].astype(
        float
    )
    return updated, removed_area_ha, int(active_mask.sum())


def _apply_aspatial_area_reduction(
    checkpoint: gpd.GeoDataFrame,
    *,
    target_removed_area_ha: float,
) -> tuple[gpd.GeoDataFrame, float, int]:
    if checkpoint.empty or target_removed_area_ha <= 0.0:
        return checkpoint, 0.0, 0
    canonical_area_sqm = _resolve_canonical_stand_area_sqm(checkpoint)
    current_area_ha = float(canonical_area_sqm.sum() / 10000.0)
    if current_area_ha <= 0.0:
        return checkpoint, 0.0, 0
    removed_area_ha = min(float(target_removed_area_ha), current_area_ha)
    keep_factor = (current_area_ha - removed_area_ha) / current_area_ha
    updated = checkpoint.copy()
    active_mask = canonical_area_sqm.astype(float) > 0.0
    if not active_mask.any():
        return checkpoint, 0.0, 0

    updated[TSR_EFFECTIVE_AREA_SQM_COLUMN] = (
        canonical_area_sqm.astype(float) * keep_factor
    )
    updated.loc[active_mask, "_stand_area_sqm"] = updated.loc[
        active_mask, TSR_EFFECTIVE_AREA_SQM_COLUMN
    ].astype(float)
    return updated, removed_area_ha, int(active_mask.sum())


def run_tsr_thlb_netdown_recipe(
    *,
    recipe_path: Path,
    checkpoint_path: Path | None = None,
    output_path: Path | None = None,
    audit_path: Path | None = None,
    execution_mode: str = TSR_THLB_EXECUTION_MODE_HYBRID,
    map_ids: Sequence[str] = (),
    auto_map_id_smoke_subset: bool = False,
) -> TsrThlbNetdownRecipeRunResult:
    """Execute a THLB netdown recipe into either a hybrid or reconstructed checkpoint."""

    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_thlb_netdown_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    if execution_mode not in _TSR_THLB_EXECUTION_MODES:
        raise TsrRecipeError(
            "Unsupported THLB execution mode: "
            f"{execution_mode}. Expected one of {sorted(_TSR_THLB_EXECUTION_MODES)}."
        )
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    source_entry_map = _load_source_recipe_entry_map(source_recipe)
    overrides_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_overrides_path
    )
    override_entries = _load_override_map(overrides_path)

    resolved_checkpoint_path = (
        checkpoint_path.expanduser().resolve()
        if checkpoint_path is not None
        else _find_tsr_checkpoint_path(
            instance_root=instance_root,
            mode=(
                "earliest"
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
                else "latest"
            ),
        )
    )
    resolved_output_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else (
            default_tsr_thlb_reconstructed_output_path(instance_root=instance_root)
            if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
            else default_tsr_thlb_netdown_output_path(instance_root=instance_root)
        )
    )
    resolved_audit_path = (
        audit_path.expanduser().resolve()
        if audit_path is not None
        else (
            default_tsr_thlb_reconstructed_audit_path(instance_root=instance_root)
            if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
            else default_tsr_thlb_netdown_audit_path(instance_root=instance_root)
        )
    )

    checkpoint = _load_checkpoint_geodataframe(resolved_checkpoint_path)
    selected_map_ids: tuple[str, ...] = ()
    if auto_map_id_smoke_subset and map_ids:
        raise TsrRecipeError(
            "Choose either explicit `map_ids` or `auto_map_id_smoke_subset`, not both."
        )
    if auto_map_id_smoke_subset:
        selected_map_ids = _auto_select_smoke_map_ids(checkpoint)
        checkpoint = _filter_checkpoint_by_map_ids(checkpoint, map_ids=selected_map_ids)
    elif map_ids:
        selected_map_ids = tuple(
            _normalize_map_id_token(value) for value in map_ids if str(value).strip()
        )
        checkpoint = _filter_checkpoint_by_map_ids(checkpoint, map_ids=selected_map_ids)
    input_area_ha = float(checkpoint.geometry.area.sum() / 10000.0)
    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        checkpoint, baseline_signal = _initialize_reconstructed_land_base(checkpoint)
    else:
        checkpoint["_row_id"] = range(len(checkpoint))
        checkpoint, baseline_signal = _normalize_checkpoint_thlb_fact(checkpoint)
    baseline_managed_area_ha = _managed_area_ha(checkpoint)
    legacy_reference_managed_area_ha = _compute_legacy_reference_managed_area_ha(
        instance_root=instance_root,
        checkpoint_path=resolved_checkpoint_path,
    )
    land_base_benchmarks = _extract_tsr_reported_land_base_benchmarks(
        instance_root=instance_root,
        recipe=recipe,
    )
    tsr_reported_aflb_area_ha = land_base_benchmarks.get("aflb_area_ha")
    tsr_reported_thlb_area_ha = land_base_benchmarks.get("thlb_area_ha")
    total_area_benchmark_ha = _resolve_tsr_total_area_benchmark(recipe)

    outcome_counts: Counter[str] = Counter()
    applied_steps: list[dict[str, Any]] = []

    for step in recipe.steps:
        updated_step = dict(step)
        normalized_action = str(step.get("normalized_action", "")).strip()
        linked_source_entry_ids = tuple(
            str(value).strip()
            for value in step.get("linked_source_entry_ids", ())
            if str(value).strip()
        )
        page_number = int(step.get("page_number") or 0)

        if normalized_action in {
            "section_heading",
            "definition",
            "increase_conditions",
            "decrease_conditions",
        }:
            updated_step["run_status"] = "needs_review"
            updated_step["run_notes"] = [
                "Context-only THLB row; no execution attempted."
            ]
        elif normalized_action in {"use_land_base", "no_deduction"}:
            updated_step["run_status"] = "applied_noop"
            updated_step["run_notes"] = ["No spatial deduction applied for this rule."]
        elif normalized_action == "exclude":
            exclusion_geometries, missing_sources = _load_exclusion_geometries(
                instance_root=instance_root,
                linked_source_entry_ids=linked_source_entry_ids,
                source_entry_map=source_entry_map,
            )
            if exclusion_geometries is None:
                updated_step["run_status"] = "blocked_missing_source"
                updated_step["run_notes"] = [
                    "No fetched polygon artifact was available for the linked source entries."
                ]
                if missing_sources:
                    updated_step["missing_source_entry_ids"] = missing_sources
            else:
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                    candidate_count = _count_exclusion_candidate_rows(
                        checkpoint=checkpoint,
                        exclusion_geometries=exclusion_geometries,
                    )
                    if candidate_count == 0:
                        updated_step["run_status"] = "applied_noop"
                        updated_step["run_notes"] = [
                            "No active land-base geometries intersected the exclusion mask."
                        ]
                    elif candidate_count > _RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD:
                        (
                            checkpoint,
                            affected_stand_count,
                            affected_area_ha,
                            overlap_area_ha,
                        ) = _apply_binary_stand_exclusion(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        if affected_stand_count == 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "Candidate rows were found, but none exceeded the stand-binary exclusion threshold."
                            ]
                        else:
                            updated_step["run_status"] = "applied"
                            updated_step["spatial_application_mode"] = (
                                "stand_binary_majority"
                            )
                            updated_step["candidate_row_count"] = candidate_count
                            updated_step["affected_stand_count"] = affected_stand_count
                            updated_step["affected_area_ha"] = affected_area_ha
                            updated_step["overlap_area_ha"] = overlap_area_ha
                            updated_step["run_notes"] = [
                                "Applied reconstructed stand-binary exclusion because the intersecting coarse-polygon workload exceeded the fragment overlay threshold.",
                                "Representative-point containment was used as the coarse-polygon stand-binary approximation.",
                            ]
                    else:
                        (
                            checkpoint,
                            affected_fragment_count,
                            affected_area_ha,
                        ) = _fragment_binary_exclusion_step(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        if affected_fragment_count == 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "No active fragment geometries intersected the exclusion mask."
                            ]
                        else:
                            updated_step["run_status"] = "applied"
                            updated_step["spatial_application_mode"] = (
                                "fragment_overlay"
                            )
                            updated_step["candidate_row_count"] = candidate_count
                            updated_step["affected_fragment_count"] = (
                                affected_fragment_count
                            )
                            updated_step["affected_area_ha"] = affected_area_ha
                            updated_step["run_notes"] = [
                                "Applied fragment/resultant exclusion with binary THLB output in EPSG:3005."
                            ]
                else:
                    exclusion_fraction = _compute_exclusion_fraction(
                        checkpoint=checkpoint,
                        exclusion_geometries=exclusion_geometries,
                    )
                    if not exclusion_fraction:
                        updated_step["run_status"] = "applied_noop"
                        updated_step["run_notes"] = [
                            "No stand geometries intersected the exclusion mask."
                        ]
                    else:
                        ratios = (
                            checkpoint["_row_id"].map(exclusion_fraction).fillna(0.0)
                        )
                        checkpoint["thlb_fact"] = (
                            checkpoint["thlb_fact"] - ratios
                        ).clip(lower=0.0, upper=1.0)
                        updated_step["run_status"] = "applied"
                        updated_step["affected_stand_count"] = int((ratios > 0).sum())
                        updated_step["affected_area_ha"] = float(
                            (
                                checkpoint["_stand_area_sqm"]
                                * ratios.clip(lower=0.0, upper=1.0)
                            ).sum()
                            / 10000.0
                        )
                        updated_step["run_notes"] = [
                            "Applied stand-level exclusion using overlap fractions in EPSG:3005.",
                            "Sequential stand-level subtraction may approximate overlapping exclusion masks.",
                        ]
                if missing_sources:
                    updated_step["missing_source_entry_ids"] = missing_sources
        elif normalized_action == "aspatial_reduction":
            updated_step["run_status"] = "unsupported"
            updated_step["run_notes"] = [
                "Aspatial reduction steps are preserved for review but not executed in v1."
            ]
        elif normalized_action == "aspatial_area_reduction":
            benchmark_marginal_area_ha = updated_step.get("benchmark_marginal_area_ha")
            if benchmark_marginal_area_ha is None or total_area_benchmark_ha is None:
                updated_step["run_status"] = "unsupported"
                updated_step["run_notes"] = [
                    "Aspatial area reduction requires TSR benchmark marginal area and total TSA area benchmark."
                ]
            else:
                current_area_ha = float(
                    _resolve_canonical_stand_area_sqm(checkpoint).sum() / 10000.0
                )
                target_removed_area_ha = (
                    float(benchmark_marginal_area_ha)
                    * current_area_ha
                    / total_area_benchmark_ha
                )
                checkpoint, removed_area_ha, affected_row_count = (
                    _apply_aspatial_area_reduction(
                        checkpoint,
                        target_removed_area_ha=target_removed_area_ha,
                    )
                )
                updated_step["run_status"] = (
                    "applied" if removed_area_ha > 0 else "applied_noop"
                )
                updated_step["affected_stand_count"] = affected_row_count
                updated_step["affected_area_ha"] = removed_area_ha
                updated_step["run_notes"] = [
                    "Applied early-stage aspatial area reduction by shrinking stand-area attributes proportionally across the active AFLB subset.",
                    "This step does not use THLB retention because future road footprint is treated as non-forested area.",
                ]
        else:
            updated_step["run_status"] = "unsupported"
            updated_step["run_notes"] = [
                f"Normalized action `{normalized_action or 'unknown'}` is not executable in v1."
            ]

        updated_step["page_number"] = page_number
        applied_steps.append(updated_step)
        outcome_counts.update([str(updated_step.get("run_status", "unsupported"))])

    final_managed_area_ha = _managed_area_ha(checkpoint)
    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        checkpoint["thlb_fact"] = checkpoint["thlb_fact"].fillna(0.0).clip(0.0, 1.0)
        checkpoint["thlb"] = checkpoint["thlb_fact"].round().astype(int)
        checkpoint["thlb_raw"] = checkpoint["thlb_fact"]
        checkpoint["thlb_area"] = (
            checkpoint["_stand_area_sqm"] * checkpoint["thlb_fact"] / 10000.0
        )
    checkpoint = _update_geometry_measure_columns(checkpoint)

    payload = recipe.to_dict()
    recipe_contract = dict(recipe.recipe_contract)
    recipe_contract["status"] = "run"
    recipe_contract["last_run_utc"] = datetime.now(UTC).isoformat()
    recipe_contract["selected_checkpoint_path"] = str(
        resolved_checkpoint_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["selected_map_ids"] = list(selected_map_ids)
    output_contract_key = (
        "reconstructed_output_checkpoint_path"
        if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        else "output_checkpoint_path"
    )
    audit_contract_key = (
        "reconstructed_audit_path"
        if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        else "audit_path"
    )
    recipe_contract[output_contract_key] = str(
        resolved_output_path.relative_to(instance_root).as_posix()
    )
    recipe_contract[audit_contract_key] = str(
        resolved_audit_path.relative_to(instance_root).as_posix()
    )
    payload["recipe_contract"] = recipe_contract
    payload["steps"] = applied_steps
    _write_recipe_yaml(resolved_recipe_path, payload)

    output_frame = checkpoint.drop(
        columns=["_row_id", "_stand_area_sqm"], errors="ignore"
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_feather(resolved_output_path)

    audit_payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "tsa": recipe.tsa.to_dict(),
        "recipe_path": str(resolved_recipe_path.relative_to(instance_root).as_posix()),
        "checkpoint_path": str(
            resolved_checkpoint_path.relative_to(instance_root).as_posix()
        ),
        "selected_map_ids": list(selected_map_ids),
        "output_path": str(resolved_output_path.relative_to(instance_root).as_posix()),
        "execution_mode": execution_mode,
        "baseline_signal": baseline_signal,
        "input_area_ha": input_area_ha,
        "baseline_managed_area_ha": baseline_managed_area_ha,
        "final_managed_area_ha": final_managed_area_ha,
        "legacy_reference_managed_area_ha": legacy_reference_managed_area_ha,
        "tsr_reported_aflb_area_ha": tsr_reported_aflb_area_ha,
        "tsr_reported_thlb_area_ha": tsr_reported_thlb_area_ha,
        "step_count": len(applied_steps),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "steps": applied_steps,
    }
    resolved_audit_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_audit_path.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    status_report_path = (
        default_tsr_thlb_reconstructed_status_report_path(instance_root=instance_root)
        if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        else default_tsr_thlb_netdown_status_report_path(instance_root=instance_root)
    )
    status_report_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runtime_status_report_path = (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / (
            "thlb_reconstructed_status_report-" + status_report_timestamp + ".md"
            if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
            else "thlb_netdown_status_report-" + status_report_timestamp + ".md"
        )
    )
    generated_utc = datetime.now(UTC).isoformat()
    status_report_markdown = _build_tsr_thlb_status_report_markdown(
        recipe=recipe,
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        checkpoint_relative_path=str(
            resolved_checkpoint_path.relative_to(instance_root).as_posix()
        ),
        output_relative_path=str(
            resolved_output_path.relative_to(instance_root).as_posix()
        ),
        audit_relative_path=str(
            resolved_audit_path.relative_to(instance_root).as_posix()
        ),
        execution_mode=execution_mode,
        baseline_signal=baseline_signal,
        selected_map_ids=selected_map_ids,
        input_area_ha=input_area_ha,
        baseline_managed_area_ha=baseline_managed_area_ha,
        final_managed_area_ha=final_managed_area_ha,
        legacy_reference_managed_area_ha=legacy_reference_managed_area_ha,
        tsr_reported_aflb_area_ha=tsr_reported_aflb_area_ha,
        tsr_reported_thlb_area_ha=tsr_reported_thlb_area_ha,
        outcome_counts=dict(sorted(outcome_counts.items())),
        step_count=len(applied_steps),
        generated_utc=generated_utc,
        runtime_report_relative_path=str(
            runtime_status_report_path.relative_to(instance_root).as_posix()
        ),
        applied_steps=applied_steps,
        source_entry_map=source_entry_map,
        override_entries=override_entries,
    )
    status_report_path.parent.mkdir(parents=True, exist_ok=True)
    status_report_path.write_text(status_report_markdown, encoding="utf-8")
    runtime_status_report_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_status_report_path.write_text(status_report_markdown, encoding="utf-8")

    recipe_contract["status_report_path"] = str(
        status_report_path.relative_to(instance_root).as_posix()
    )
    recipe_contract["runtime_status_report_path"] = str(
        runtime_status_report_path.relative_to(instance_root).as_posix()
    )
    payload["recipe_contract"] = recipe_contract
    _write_recipe_yaml(resolved_recipe_path, payload)

    return TsrThlbNetdownRecipeRunResult(
        recipe_path=resolved_recipe_path,
        tsa=recipe.tsa,
        checkpoint_path=resolved_checkpoint_path,
        output_path=resolved_output_path,
        audit_path=resolved_audit_path,
        status_report_path=status_report_path,
        runtime_status_report_path=runtime_status_report_path,
        execution_mode=execution_mode,
        baseline_signal=baseline_signal,
        selected_map_ids=selected_map_ids,
        step_count=len(applied_steps),
        outcome_counts=dict(sorted(outcome_counts.items())),
        input_area_ha=input_area_ha,
        baseline_managed_area_ha=baseline_managed_area_ha,
        final_managed_area_ha=final_managed_area_ha,
        legacy_reference_managed_area_ha=legacy_reference_managed_area_ha,
        tsr_reported_aflb_area_ha=tsr_reported_aflb_area_ha,
        tsr_reported_thlb_area_ha=tsr_reported_thlb_area_ha,
    )
