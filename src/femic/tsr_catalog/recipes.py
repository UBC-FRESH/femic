"""Instance-local TSR recipe scaffold helpers."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import copy
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
from femic.bcdc_dwds import (
    BcdcDwdsError,
    follow_up_bcdc_dwds_order,
    load_bcdc_dwds_manifest,
    submit_bcdc_dwds_order,
    write_bcdc_dwds_manifest,
)
from femic.bcdc_fetch import (
    BC_ALBERS_EPSG,
    BcdcFetchError,
    GeomarkBBox,
    fetch_bcdc_wfs_data,
)
from femic.pipeline.tipsy_config import BROADLEAF_SPECIES_CODES

from .overlay import TsrOverlayTsaRecord
from .report import TsrFactReviewRow, report_tsr_candidate_facts
from .source_overrides import (
    TsrSourceLayerOverrideEntry,
    load_tsr_source_layer_overrides,
)


class TsrRecipeError(RuntimeError):
    """Raised when TSR recipe initialization or loading fails."""


_TSR_RECIPE_RESOURCE_PACKAGE = "femic.resources.tsr_recipes"
_TSR_WARMSTART_RESOURCE_PACKAGE = "femic.resources.tsr"
_SOURCE_LAYERS_RECIPE_RESOURCE = "source_layers.recipe.yaml"
_THLB_NETDOWN_RECIPE_RESOURCE = "thlb_netdown.recipe.yaml"
_THLB_WARMSTART_PATTERNS_RESOURCE = "thlb_warmstart_patterns.yaml"
TSR_THLB_EXECUTION_MODE_HYBRID = "hybrid"
TSR_THLB_EXECUTION_MODE_RECONSTRUCTED = "reconstructed"
_TSR_THLB_EXECUTION_MODES = {
    TSR_THLB_EXECUTION_MODE_HYBRID,
    TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
}
_RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD = 10000
_RECONSTRUCTED_FRAGMENT_BATCH_SIZE = 5000
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
_THLB_WARMSTART_STATUS_COMPILED_READY = "compiled_ready"
_THLB_WARMSTART_STATUS_REVIEW_PATTERN_MATCH = "review_pattern_match"
_THLB_WARMSTART_STATUS_BLOCKED_MISSING_SOURCE = "blocked_missing_source"
_THLB_WARMSTART_STATUS_MANUAL_OR_ASPATIAL = "manual_or_aspatial"
_THLB_WARMSTART_STATUS_NO_PATTERN_MATCH = "no_pattern_match"
_THLB_WARMSTART_STATUSES = {
    _THLB_WARMSTART_STATUS_COMPILED_READY,
    _THLB_WARMSTART_STATUS_REVIEW_PATTERN_MATCH,
    _THLB_WARMSTART_STATUS_BLOCKED_MISSING_SOURCE,
    _THLB_WARMSTART_STATUS_MANUAL_OR_ASPATIAL,
    _THLB_WARMSTART_STATUS_NO_PATTERN_MATCH,
}
_THLB_RECONSTRUCTION_COMPARISON_BUCKETS = (
    "close_match",
    "reviewed_bridge_only",
    "strict_overcut_candidate",
    "strict_undercut_candidate",
    "blocked_or_missing_source",
    "manual_or_reviewed_override",
    "aspatial_bridge_difference",
    "not_comparable",
)

_THLB_RECONSTRUCTION_PROBLEM_OWNERSHIP_VALUES = (
    "model_endogenous",
    "data_exogenous",
    "reviewed_bridge_choice",
    "mixed",
    "not_applicable",
)
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

_EXTENT_COVERAGE_BLOCK_THRESHOLD = 0.5
_EXTENT_AREA_BLOCK_THRESHOLD = 0.25
_SOURCE_ARTIFACT_SCOPE_PRODUCTION = "production_full_tsa"
_SOURCE_ARTIFACT_SCOPE_SMOKE = "smoke_subset"
_SOURCE_ARTIFACT_SCOPE_AOI_UNKNOWN = "aoi_scoped_unknown"
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
class _LandBaseSummaryRowClassification:
    land_base_stage: str
    execution_class: str
    benchmark_role: str


_TSA29_TABLE3_ROW_CLASSIFICATIONS: dict[str, _LandBaseSummaryRowClassification] = {
    "total tsa area": _LandBaseSummaryRowClassification(
        land_base_stage="reference_target",
        execution_class="reference_only",
        benchmark_role="reference_total",
    ),
    "land not administered by the province": _LandBaseSummaryRowClassification(
        land_base_stage="glb_to_aflb",
        execution_class="drop_from_universe",
        benchmark_role="deduction",
    ),
    "non-forest": _LandBaseSummaryRowClassification(
        land_base_stage="glb_to_aflb",
        execution_class="drop_from_universe",
        benchmark_role="deduction",
    ),
    "roads and landings": _LandBaseSummaryRowClassification(
        land_base_stage="glb_to_aflb",
        execution_class="drop_from_universe",
        benchmark_role="deduction",
    ),
    "analysis forest land base": _LandBaseSummaryRowClassification(
        land_base_stage="glb_to_aflb",
        execution_class="reference_only",
        benchmark_role="reference_cumulative",
    ),
    "parks, protected areas, area-base tenures": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "old growth management areas": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "wildlife habitat areas": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "critical habitat for fish": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "lakeshore management": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "community areas of special concern": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "proven aboriginal rights areas": _LandBaseSummaryRowClassification(
        land_base_stage="aflb_to_lhlb",
        execution_class="legal_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "areas considered inoperable": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "sites with low growing timber potential": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "non-merchantable timber profiles": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "recreation features": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "growth and yield permanent sample plots": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "riparian areas": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "buffered trails": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "wildlife tree retention areas": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "cultural heritage and archaeological resources": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "timber harvesting land base": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="reference_only",
        benchmark_role="reference_cumulative",
    ),
    "future roads": _LandBaseSummaryRowClassification(
        land_base_stage="lhlb_to_thlb",
        execution_class="projected_harvest_exclusion",
        benchmark_role="deduction",
    ),
    "long-term thlb": _LandBaseSummaryRowClassification(
        land_base_stage="reference_target",
        execution_class="reference_only",
        benchmark_role="reference_cumulative",
    ),
}


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
class TsrThlbReconstructedDiagnosticSliceResult:
    """Summary of one reconstructed diagnostic slice execution."""

    recipe_path: Path
    checkpoint_path: Path
    output_path: Path
    audit_path: Path
    diagnostic_path: Path
    execution_mode: str
    baseline_signal: str
    executed_step_ids: tuple[str, ...]
    start_index: int
    end_index: int
    step_count: int
    outcome_counts: dict[str, int]
    baseline_managed_area_ha: float
    final_managed_area_ha: float
    total_seconds: float
    resumed_from_checkpoint: bool


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
class TsrThlbWarmstartBuildResult:
    """Summary of one THLB warm-start artifact build pass."""

    recipe_path: Path
    markdown_path: Path
    yaml_path: Path
    tsa: TsrOverlayTsaRecord
    milestone_count: int
    parent_step_count: int
    warmstart_status_counts: dict[str, int]


@dataclass(frozen=True)
class TsrThlbReconstructionComparisonBuildResult:
    """Summary of one strict-vs-reviewed THLB comparison build pass."""

    recipe_path: Path
    markdown_path: Path
    json_path: Path
    tsa: TsrOverlayTsaRecord
    parent_step_count: int
    comparison_bucket_counts: dict[str, int]


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


def _load_warmstart_patterns() -> tuple[dict[str, Any], ...]:
    resource = importlib_resources.files(_TSR_WARMSTART_RESOURCE_PACKAGE).joinpath(
        _THLB_WARMSTART_PATTERNS_RESOURCE
    )
    payload = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TsrRecipeError("Invalid packaged THLB warm-start motif payload.")
    motifs = payload.get("motifs")
    if not isinstance(motifs, list):
        raise TsrRecipeError(
            "Packaged THLB warm-start motif payload is missing `motifs`."
        )
    return tuple(item for item in motifs if isinstance(item, dict))


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


def default_tsr_thlb_warmstart_markdown_path(*, instance_root: Path) -> Path:
    """Return the default generated THLB warm-start checklist path."""

    return (
        instance_root.expanduser().resolve()
        / "workbench"
        / "tsr"
        / "thlb_netdown.warmstart.md"
    )


def default_tsr_thlb_warmstart_yaml_path(*, instance_root: Path) -> Path:
    """Return the default editable THLB warm-start YAML path."""

    return (
        instance_root.expanduser().resolve() / "config" / "tsr" / "thlb_warmstart.yaml"
    )


def default_tsr_thlb_reconstruction_comparison_markdown_path(
    *, instance_root: Path
) -> Path:
    """Return the default strict-vs-reviewed THLB comparison Markdown path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_reconstruction_comparison.md"
    )


def default_tsr_thlb_reconstruction_comparison_json_path(
    *, instance_root: Path
) -> Path:
    """Return the default strict-vs-reviewed THLB comparison JSON path."""

    return (
        instance_root.expanduser().resolve()
        / "config"
        / "tsr"
        / "thlb_reconstruction_comparison.json"
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


def default_tsr_thlb_reconstructed_lu_runtime_root(*, instance_root: Path) -> Path:
    """Return the default runtime root for LU-wise reconstructed THLB state."""

    return (
        instance_root.expanduser().resolve()
        / "runtime"
        / "logs"
        / "tsr"
        / "reconstructed_lu"
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


def _resolve_optional_instance_path(
    *, instance_root: Path, value: str | None
) -> Path | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (instance_root / candidate).resolve()


def _render_instance_relative_path(
    *, instance_root: Path, candidate: Path | str | None
) -> str:
    if candidate is None:
        return ""
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(instance_root).as_posix()
    except ValueError:
        return str(candidate).replace("\\", "/")


def _default_dwds_order_manifest_path(*, instance_root: Path, entry_id: str) -> Path:
    return (
        instance_root
        / "runtime"
        / "logs"
        / "tsr"
        / "dwds_orders"
        / f"{entry_id}_order_manifest.json"
    )


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


def _load_overlay_review_bbox_epsg3005(
    overlay_path: Path,
) -> tuple[float, float, float, float] | None:
    if not overlay_path.exists():
        return None
    payload = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    review_payload = payload.get("bcdc_acquisition_review")
    if not isinstance(review_payload, dict):
        return None
    bbox_payload = review_payload.get("bbox_epsg3005")
    if not isinstance(bbox_payload, list | tuple) or len(bbox_payload) != 4:
        return None
    try:
        return tuple(float(value) for value in bbox_payload)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _bbox_matches(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
    *,
    tolerance_m: float = 1.0,
) -> bool:
    return all(abs(lv - rv) <= tolerance_m for lv, rv in zip(left, right, strict=True))


def _classify_source_artifact_scope(
    *,
    instance_root: Path,
    bbox_epsg3005: tuple[float, float, float, float] | None,
) -> str | None:
    if bbox_epsg3005 is None:
        return None
    overlay_bbox = _load_overlay_review_bbox_epsg3005(
        instance_root / "config" / "tsr" / "overlay.yaml"
    )
    if overlay_bbox is not None and _bbox_matches(bbox_epsg3005, overlay_bbox):
        return _SOURCE_ARTIFACT_SCOPE_PRODUCTION
    if overlay_bbox is not None:
        return _SOURCE_ARTIFACT_SCOPE_SMOKE
    return _SOURCE_ARTIFACT_SCOPE_AOI_UNKNOWN


def _artifact_download_root_for_scope(
    *, instance_root: Path, scope: str | None
) -> Path:
    base_root = instance_root / "data" / "downloads" / "bcdc"
    if scope == _SOURCE_ARTIFACT_SCOPE_PRODUCTION:
        return base_root
    if scope in {_SOURCE_ARTIFACT_SCOPE_SMOKE, _SOURCE_ARTIFACT_SCOPE_AOI_UNKNOWN}:
        return base_root / "smoke"
    return base_root


def _probe_vector_artifact_bounds(
    artifact_path: Path,
) -> tuple[float, float, float, float] | None:
    try:
        layer = gpd.read_file(artifact_path, engine="pyogrio")
    except Exception:
        return None
    if layer.empty or "geometry" not in layer.columns:
        return None
    layer = layer.dropna(subset=["geometry"])
    layer = layer.loc[~layer.geometry.is_empty]
    if layer.empty:
        return None
    if layer.crs is None:
        layer = layer.set_crs(BC_ALBERS_EPSG)
    else:
        layer = layer.to_crs(BC_ALBERS_EPSG)
    minx, miny, maxx, maxy = layer.total_bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def _record_source_artifact_details(
    *,
    updated_entry: dict[str, Any],
    instance_root: Path,
    artifact_path: Path,
) -> None:
    updated_entry["artifact_path"] = str(
        artifact_path.resolve().relative_to(instance_root).as_posix()
    )
    artifact_bounds = _probe_vector_artifact_bounds(artifact_path)
    if artifact_bounds is not None:
        updated_entry["artifact_extent_bbox_epsg3005"] = [
            float(value) for value in artifact_bounds
        ]


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
    existing_entry: dict[str, Any] | None,
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
    order_manifest_path = ""
    if overlay_attempt is not None:
        raw_artifact_path = _render_instance_relative_path(
            instance_root=instance_root,
            candidate=overlay_attempt.get("saved_path"),
        )
        if raw_artifact_path:
            artifact_path = raw_artifact_path.removeprefix(
                f"external/{instance_root.name}/"
            )
        prior_run_status = str(overlay_attempt.get("acquisition_outcome", "pending"))
        prior_notes = str(overlay_attempt.get("notes", "")).strip()
        if prior_notes:
            notes.extend(
                part.strip() for part in prior_notes.split(" | ") if part.strip()
            )
    if existing_entry is not None:
        if not artifact_path:
            artifact_path = str(existing_entry.get("artifact_path", "")).strip()
        if prior_run_status == "pending":
            prior_run_status = str(existing_entry.get("run_status", "pending"))
        order_manifest_path = str(existing_entry.get("order_manifest_path", "")).strip()

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
        else (
            str(existing_entry.get("order_id", "")).strip()
            if existing_entry is not None
            else ""
        ),
        "submission_status": overlay_attempt.get("submission_status", "")
        if overlay_attempt is not None
        else (
            str(existing_entry.get("submission_status", "")).strip()
            if existing_entry is not None
            else ""
        ),
        "order_manifest_path": order_manifest_path,
        "failure_message": overlay_attempt.get("failure_message", "")
        if overlay_attempt is not None
        else (
            str(existing_entry.get("failure_message", "")).strip()
            if existing_entry is not None
            else ""
        ),
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
                section_number = heading_match.group("section")
                title = _normalize_whitespace(heading_match.group("title"))
                if (
                    current is not None
                    and str(current.get("section_number", "")) == section_number
                    and str(current.get("title", "")) == title
                ):
                    continue
                if current is not None:
                    subsections.append(current)
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
                normalized_line = _normalize_whitespace(line)
                current_heading = _normalize_whitespace(
                    f"{current.get('section_number', '')} {current.get('title', '')}"
                )
                if normalized_line in {
                    _normalize_whitespace(str(current.get("title", ""))),
                    current_heading,
                }:
                    continue
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
    tsa_code: str | None = None,
) -> tuple[str, str]:
    lower = label.casefold()
    if str(tsa_code or "").strip() == "29":
        classification = _TSA29_TABLE3_ROW_CLASSIFICATIONS.get(lower)
        if classification is not None:
            return classification.land_base_stage, classification.execution_class
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


def _classify_land_base_summary_row(
    *,
    label: str,
    linked_subsection: dict[str, Any] | None,
    seen_aflb_row: bool,
    seen_thlb_row: bool,
    tsa_code: str | None = None,
) -> _LandBaseSummaryRowClassification:
    stage, execution_class = _infer_parent_row_stage(
        label=label,
        linked_subsection=linked_subsection,
        seen_aflb_row=seen_aflb_row,
        seen_thlb_row=seen_thlb_row,
        tsa_code=tsa_code,
    )
    lower = label.casefold()
    if str(tsa_code or "").strip() == "29":
        classification = _TSA29_TABLE3_ROW_CLASSIFICATIONS.get(lower)
        if classification is not None:
            return classification
    if lower == "total tsa area":
        benchmark_role = "reference_total"
    elif (
        "analysis forest land base" in lower
        or "legally harvestable land base" in lower
        or "timber harvesting land base" in lower
        or "long-term thlb" in lower
    ):
        benchmark_role = "reference_cumulative"
    elif execution_class == "context_only":
        benchmark_role = "context"
    else:
        benchmark_role = "deduction"
    return _LandBaseSummaryRowClassification(
        land_base_stage=stage,
        execution_class=execution_class,
        benchmark_role=benchmark_role,
    )


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
    if parent_step_id == "thlb_parent_004_roads_and_landings":
        provenance_id = str(linked_subsection.get("provenance_id", ""))
        return (
            {
                "subrule_id": f"{parent_step_id}_draft_01",
                "human_summary": (
                    "Use the permanent-road buffers as supporting evidence only; do not "
                    "treat the tiny mapped overlap as the full existing-RTL deduction."
                ),
                "rationale": (
                    "TSA29 section 6.2.3 says existing roads, trails, and landings are "
                    "modeled non-spatially because the features are too small and "
                    "incomplete to track reliably at landscape scale."
                ),
                "candidate_layers": [
                    "whse_basemapping_dra_dgtl_road_atlas_mpar_sp",
                    "whse_forest_tenure_ften_road_section_lines_svw",
                ],
                "candidate_fields": [],
                "candidate_values": [
                    "12.5 m public/FSR half-width",
                    "7.5 m road-permit half-width",
                ],
                "candidate_operation_type": "review",
                "field_mapping_notes": [
                    "Keep the permanent-road buffers as context/supporting evidence only.",
                    "Do not let these tiny spatial overlays stand in for the full step-4 TSR benchmark.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
            {
                "subrule_id": f"{parent_step_id}_draft_02",
                "human_summary": (
                    "Apply the existing RTL deduction as a documented AFLB-stage "
                    "aspatial area reduction anchored to the TSR benchmark."
                ),
                "rationale": (
                    "The TSR benchmark for existing roads, trails, and landings is "
                    "50,434 ha, and Table 6 category totals align with that benchmark "
                    "far better than the conflicting prose sentence that says 32,526 ha."
                ),
                "candidate_layers": [],
                "candidate_fields": [],
                "candidate_values": [
                    "50,434 ha existing RTL benchmark",
                    "Residual target after any exact permanent-road overlap already removed",
                ],
                "candidate_operation_type": "aspatial_area_reduction",
                "field_mapping_notes": [
                    "Use the parsed step benchmark as the governing target.",
                    "Subtract any same-parent exact spatial removal first to avoid double-counting if those overlays ever become non-zero.",
                ],
                "confidence": "needs_review",
                "review_status": "draft",
                "prose_provenance": provenance_id,
                "hint_provenance_ids": [],
            },
        )
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
            "Crown - Municipal Parcels",
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
                    "and municipal polygons from the working land base"
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
                    "Tree Farm Licence schedule polygons and the broad `Crown Lease - Misc. lease` bucket stay in AFLB here because including them materially overcuts the TSA29 step-2 benchmark; any narrower lease-only exclusions need a more specific reviewed discriminator.",
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
        roads_fallback = _base_item(
            "compiled_03",
            "Existing roads, trails, and landings area reduction",
            "aspatial_area_reduction",
        )
        roads_fallback.update(
            {
                "benchmark_marginal_area_ha": (
                    benchmark_marginal_area_ha
                    if benchmark_marginal_area_ha is not None
                    else 50434.0
                ),
                "normalized_action": "aspatial_area_reduction",
                "normalized_subject": "Existing roads, trails, and landings area reduction",
                "normalized_predicate": (
                    "apply the TSR-cited existing RTL deduction as a residual AFLB "
                    "stand-area reduction after any exact permanent-road overlap "
                    "already removed by the same parent step"
                ),
                "linked_source_entry_ids": [],
                "subtract_parent_exact_removed_area": True,
                "notes": [
                    "TSA29 section 6.2.3 says existing roads, trails, and landings are modeled non-spatially through partial AFLB reductions because the mapped features are too small and incomplete to track reliably at landscape scale.",
                    "Use the TSR benchmark marginal deduction of 50,434 ha for this step; do not use the conflicting 32,526 ha prose sentence as the governing fallback target.",
                    "Subtract any exact same-parent permanent-road overlap already removed so the fallback only fills the remaining benchmark gap.",
                ],
            }
        )
        return (road_atlas, road_section, roads_fallback)

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
    tsa_code: str | None = None,
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
        classification = _classify_land_base_summary_row(
            label=label,
            linked_subsection=linked_subsection,
            seen_aflb_row=seen_aflb_row,
            seen_thlb_row=seen_thlb_row,
            tsa_code=tsa_code,
        )
        land_base_stage = classification.land_base_stage
        execution_class = classification.execution_class
        stage_label = _THLB_STAGE_LABELS[land_base_stage]
        benchmark_marginal_area_ha: float | None = None
        benchmark_cumulative_area_ha: float | None = None
        if classification.benchmark_role == "reference_total":
            benchmark_cumulative_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = benchmark_cumulative_area_ha
        elif lower == "analysis forest land base":
            benchmark_cumulative_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = benchmark_cumulative_area_ha
            seen_aflb_row = True
        elif lower == "timber harvesting land base":
            benchmark_cumulative_area_ha = numeric_tokens[0]
            current_cumulative_area_ha = benchmark_cumulative_area_ha
            seen_thlb_row = True
        elif classification.benchmark_role == "reference_cumulative":
            benchmark_cumulative_area_ha = numeric_tokens[0]
        elif classification.benchmark_role == "deduction":
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
    existing_entry_map = {
        str(entry.get("recommended_query", "")).casefold(): entry
        for entry in recipe.entries
    }

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
            existing_entry=existing_entry_map.get(row.recommended_query.casefold()),
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
                tsa_code=recipe.tsa.tsa_code,
            )
        )
        parent_steps = _merge_preserved_thlb_parent_step_metadata(
            existing_parent_steps=recipe.parent_steps,
            built_parent_steps=built_parent_steps,
        )
        steps = _merge_preserved_thlb_compiled_steps(
            existing_steps=recipe.steps,
            built_steps=built_compiled_steps,
            parent_steps=parent_steps,
        )
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
    warmstart_markdown_path = default_tsr_thlb_warmstart_markdown_path(
        instance_root=instance_root
    )
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
        warmstart_markdown_relative_path=(
            str(warmstart_markdown_path.relative_to(instance_root).as_posix())
            if warmstart_markdown_path.exists()
            else None
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
    base_download_root = _resolve_instance_path(
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
        order_manifest_path = str(entry.get("order_manifest_path", "")).strip()
        query = str(
            entry.get("acquisition_query") or entry.get("recommended_query", "")
        )
        override_kind = str(entry.get("override_kind", ""))
        artifact_scope = _classify_source_artifact_scope(
            instance_root=instance_root,
            bbox_epsg3005=bbox_epsg3005
            if strategy in {"wfs_fetch", "dwds_order"}
            else None,
        )
        if bbox_epsg3005 is not None and strategy in {"wfs_fetch", "dwds_order"}:
            updated["requested_bbox_epsg3005"] = [
                float(value) for value in bbox_epsg3005
            ]
        if artifact_scope is not None and strategy in {"wfs_fetch", "dwds_order"}:
            updated["artifact_scope"] = artifact_scope

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
            resolved_artifact_path = _resolve_source_artifact_path(
                instance_root=instance_root,
                source_entry=updated,
            )
            if resolved_artifact_path is not None:
                artifact_bounds = _probe_vector_artifact_bounds(resolved_artifact_path)
                if artifact_bounds is not None:
                    updated["artifact_extent_bbox_epsg3005"] = [
                        float(value) for value in artifact_bounds
                    ]
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
                download_root = _artifact_download_root_for_scope(
                    instance_root=instance_root,
                    scope=artifact_scope,
                )
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
                _record_source_artifact_details(
                    updated_entry=updated,
                    instance_root=instance_root,
                    artifact_path=fetch_result.saved_path,
                )
                updated["feature_count"] = fetch_result.feature_count
                updated["failure_message"] = ""
                updated["run_status"] = "fetched"
            except BcdcFetchError as exc:
                updated["run_status"] = "failed"
                updated["failure_message"] = str(exc)
        elif strategy == "direct_download":
            try:
                resolve_result = resolve_bcdc_candidates(query, limit=limit)
                download_result = download_direct_bcdc_resources(
                    resolve_result,
                    destination_root=base_download_root,
                    query_slug=str(
                        entry.get("recommended_query") or entry.get("entry_id") or query
                    ),
                )
                downloaded = download_result.downloaded
                if downloaded:
                    saved_path = downloaded[0].saved_path
                    _record_source_artifact_details(
                        updated_entry=updated,
                        instance_root=instance_root,
                        artifact_path=saved_path,
                    )
                    updated["failure_message"] = ""
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
            manifest_candidate = _resolve_optional_instance_path(
                instance_root=instance_root,
                value=order_manifest_path,
            )
            if manifest_candidate is not None and manifest_candidate.exists():
                try:
                    orders = load_bcdc_dwds_manifest(manifest_candidate)
                    if not orders:
                        raise BcdcDwdsError(
                            f"DWDS manifest contains no order results: {manifest_candidate}"
                        )
                    order_result = orders[0]
                    updated["order_manifest_path"] = str(
                        manifest_candidate.relative_to(instance_root).as_posix()
                    )
                    updated["order_id"] = order_result.order_id
                    updated["submission_status"] = order_result.submission_status
                    updated["failure_message"] = ""
                    existing_materialized_path = _resolve_optional_instance_path(
                        instance_root=instance_root,
                        value=order_result.materialized_artifact_path,
                    )
                    if (
                        existing_materialized_path is not None
                        and existing_materialized_path.exists()
                    ):
                        _record_source_artifact_details(
                            updated_entry=updated,
                            instance_root=instance_root,
                            artifact_path=existing_materialized_path,
                        )
                        updated["run_status"] = "materialized"
                    else:
                        order_result = follow_up_bcdc_dwds_order(
                            order_result,
                            download_root=base_download_root,
                        )
                        write_bcdc_dwds_manifest([order_result], manifest_candidate)
                        updated["order_id"] = order_result.order_id
                        updated["submission_status"] = order_result.submission_status
                        updated["failure_message"] = ""
                        if order_result.materialized_artifact_path:
                            materialized_path = Path(
                                order_result.materialized_artifact_path
                            ).expanduser()
                            if not materialized_path.is_absolute():
                                materialized_path = instance_root / materialized_path
                            _record_source_artifact_details(
                                updated_entry=updated,
                                instance_root=instance_root,
                                artifact_path=materialized_path.resolve(),
                            )
                            updated["run_status"] = "materialized"
                        else:
                            updated["run_status"] = "followup_pending"
                    if (
                        order_result.materialized_artifact_path
                        and updated.get("run_status") != "materialized"
                    ):
                        materialized_path = Path(
                            order_result.materialized_artifact_path
                        ).expanduser()
                        if not materialized_path.is_absolute():
                            materialized_path = instance_root / materialized_path
                        if materialized_path.exists():
                            _record_source_artifact_details(
                                updated_entry=updated,
                                instance_root=instance_root,
                                artifact_path=materialized_path.resolve(),
                            )
                            updated["run_status"] = "materialized"
                except BcdcDwdsError as exc:
                    updated["run_status"] = "failed"
                    updated["failure_message"] = str(exc)
            elif manifest_candidate is not None and not manifest_candidate.exists():
                updated["run_status"] = "failed"
                updated["failure_message"] = (
                    "Saved DWDS order manifest is missing; review the recipe entry or "
                    "submit a new order explicitly."
                )
            elif not allow_order:
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
                    manifest_path = _default_dwds_order_manifest_path(
                        instance_root=instance_root,
                        entry_id=str(entry.get("entry_id", "dwds_order")).strip()
                        or "dwds_order",
                    )
                    write_bcdc_dwds_manifest([order_result], manifest_path)
                    updated["run_status"] = "ordered"
                    updated["order_id"] = order_result.order_id
                    updated["submission_status"] = order_result.submission_status
                    updated["order_manifest_path"] = str(
                        manifest_path.relative_to(instance_root).as_posix()
                    )
                    updated["failure_message"] = ""
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
    expected_row_count: int | None = None,
    expected_area_ha: float | None = None,
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
        if expected_row_count is not None:
            cached_row_count = payload.get("input_row_count")
            cached_area_ha = payload.get("input_area_ha")
            if cached_row_count is None or cached_area_ha is None:
                continue
            if int(cached_row_count) != int(expected_row_count):
                continue
            if not math.isclose(
                float(cached_area_ha),
                float(expected_area_ha or 0.0),
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
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
    expected_row_count: int | None = None,
    expected_area_ha: float | None = None,
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
        if expected_row_count is not None:
            cached_row_count = payload.get("input_row_count")
            cached_area_ha = payload.get("input_area_ha")
            if cached_row_count is None or cached_area_ha is None:
                continue
            if int(cached_row_count) != int(expected_row_count):
                continue
            if not math.isclose(
                float(cached_area_ha),
                float(expected_area_ha or 0.0),
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
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
        "input_row_count": int(len(checkpoint)),
        "input_area_ha": float(checkpoint.geometry.area.astype(float).sum() / 10000.0),
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
    reconstructed = checkpoint.copy()
    thlb_binary = reconstructed.geometry.map(lambda _value: 1.0).astype(float)
    if "FOR_MGMT_LAND_BASE_IND" in checkpoint.columns:
        signal_source = "checkpoint1_raw_glb_initialization"
    else:
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


def _resume_reconstructed_land_base(
    checkpoint: gpd.GeoDataFrame,
) -> tuple[gpd.GeoDataFrame, str]:
    resumed = checkpoint.copy()
    if "SOURCE_FEATURE_ID" not in resumed.columns and "FEATURE_ID" in resumed.columns:
        resumed["SOURCE_FEATURE_ID"] = resumed["FEATURE_ID"]
    if "thlb_fact" in resumed.columns:
        thlb_fact = pd.to_numeric(resumed["thlb_fact"], errors="coerce").fillna(0.0)
    elif "thlb_raw" in resumed.columns:
        thlb_fact = pd.to_numeric(resumed["thlb_raw"], errors="coerce").fillna(0.0)
    elif "thlb" in resumed.columns:
        thlb_fact = pd.to_numeric(resumed["thlb"], errors="coerce").fillna(0.0)
    else:
        thlb_fact = resumed.geometry.map(lambda _value: 1.0).astype(float)
    resumed["thlb_fact"] = thlb_fact.clip(lower=0.0, upper=1.0)
    resumed["thlb"] = resumed["thlb_fact"].round().astype(int)
    resumed = _update_geometry_measure_columns(resumed)
    resumed["_row_id"] = range(len(resumed))
    resumed["_stand_area_sqm"] = _resolve_effective_stand_area_sqm(resumed)
    return resumed, "resumed_reconstructed_checkpoint"


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


def _chunk_reconstructed_candidate_rows(
    candidate: gpd.GeoDataFrame,
    *,
    batch_size: int | None = None,
) -> list[gpd.GeoDataFrame]:
    if candidate.empty:
        return []
    resolved_batch_size = max(1, int(batch_size or _RECONSTRUCTED_FRAGMENT_BATCH_SIZE))
    ordered = candidate.sort_values("_row_id").reset_index(drop=True)
    return [
        ordered.iloc[start : start + resolved_batch_size].copy()
        for start in range(0, len(ordered), resolved_batch_size)
    ]


def _fragment_binary_exclusion_step_chunked(
    *,
    checkpoint: gpd.GeoDataFrame,
    exclusion_geometries: gpd.GeoDataFrame,
    update_aflb_flag_on_exclusion: bool = True,
    batch_size: int | None = None,
) -> tuple[gpd.GeoDataFrame, int, int, float, int]:
    if checkpoint.empty or exclusion_geometries.empty:
        return checkpoint, 0, 0, 0.0, 0
    active = checkpoint.loc[checkpoint["thlb_fact"] > 0].copy()
    if active.empty:
        return checkpoint, 0, 0, 0.0, 0
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
        return checkpoint, 0, 0, 0.0, 0
    candidate = active.iloc[unique_indices].copy()
    untouched = checkpoint.drop(candidate.index).copy()
    exclusion_sindex = exclusion_geometries.sindex
    rebuilt_frames: list[gpd.GeoDataFrame] = [untouched]
    affected_fragment_count = 0
    affected_area_sqm = 0.0
    batch_count = 0

    for batch in _chunk_reconstructed_candidate_rows(candidate, batch_size=batch_size):
        batch_count += 1
        exclusion_indices = exclusion_sindex.query(
            batch.geometry,
            predicate="intersects",
        )
        if getattr(exclusion_indices, "ndim", 1) == 2:
            exclusion_values = exclusion_indices[1]
        else:
            exclusion_values = exclusion_indices
        unique_exclusion_indices = sorted(
            {int(index) for index in exclusion_values.tolist()}
        )
        if not unique_exclusion_indices:
            rebuilt_frames.append(batch)
            continue
        local_exclusions = exclusion_geometries.iloc[unique_exclusion_indices].copy()
        mask_geometry = _resolve_union_geometry(local_exclusions)
        if mask_geometry is None or getattr(mask_geometry, "is_empty", False):
            rebuilt_frames.append(batch)
            continue

        mask_frame = gpd.GeoDataFrame(geometry=[mask_geometry], crs=BC_ALBERS_EPSG)
        intersections = gpd.overlay(
            batch,
            mask_frame,
            how="intersection",
            keep_geom_type=False,
        )
        differences = gpd.overlay(
            batch,
            mask_frame,
            how="difference",
            keep_geom_type=False,
        )

        if not differences.empty:
            differences = differences.copy()
            differences["thlb_fact"] = 1.0
            differences["thlb"] = 1
            rebuilt_frames.append(differences)

        if intersections.empty:
            continue

        intersections = intersections.copy()
        intersections["thlb_fact"] = 0.0
        intersections["thlb"] = 0
        if (
            update_aflb_flag_on_exclusion
            and "FOR_MGMT_LAND_BASE_IND" in intersections.columns
        ):
            intersections["FOR_MGMT_LAND_BASE_IND"] = "N"
        affected_fragment_count += int(len(intersections))
        affected_area_sqm += float(intersections.geometry.area.sum())
        rebuilt_frames.append(intersections)

    rebuilt = gpd.GeoDataFrame(
        pd.concat(rebuilt_frames, ignore_index=True),
        crs=BC_ALBERS_EPSG,
    )
    rebuilt = rebuilt.loc[~rebuilt.geometry.is_empty].copy()
    rebuilt = _assign_fragment_feature_ids(rebuilt)
    return (
        rebuilt,
        int(len(candidate)),
        affected_fragment_count,
        float(affected_area_sqm / 10000.0),
        batch_count,
    )


def _load_lu_chunk_frame(chunk_path: Path) -> gpd.GeoDataFrame:
    frame = gpd.read_feather(chunk_path)
    return gpd.GeoDataFrame(frame, geometry="geometry", crs=BC_ALBERS_EPSG)


def _write_lu_chunk_frame(chunk: gpd.GeoDataFrame, *, chunk_path: Path) -> None:
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    chunk.to_feather(chunk_path)


def _prepare_reconstructed_lu_chunk_records(
    *,
    checkpoint: gpd.GeoDataFrame,
    checkpoint_path: Path,
    instance_root: Path,
) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]], dict[str, float]]:
    profiling: dict[str, float] = {
        "lu_layer_load_seconds": 0.0,
        "lu_selection_cache_lookup_seconds": 0.0,
        "lu_selection_seconds": 0.0,
        "partition_materialize_seconds": 0.0,
    }
    lu_layer_started = perf_counter()
    lu_layer = _load_landscape_unit_layer(instance_root)
    profiling["lu_layer_load_seconds"] = perf_counter() - lu_layer_started

    cache_lookup_started = perf_counter()
    cached_partition = _load_cached_landscape_unit_partition_records(
        checkpoint_path=checkpoint_path,
        instance_root=instance_root,
        expected_row_count=len(checkpoint),
        expected_area_ha=float(checkpoint.geometry.area.astype(float).sum() / 10000.0),
    )
    profiling["lu_selection_cache_lookup_seconds"] = (
        perf_counter() - cache_lookup_started
    )

    if cached_partition is not None:
        selected_landscape_units, chunk_records = cached_partition
        lu_select_started = perf_counter()
        lu_frame, _selected_names = _select_landscape_unit_rows(
            lu_layer,
            landscape_units=selected_landscape_units,
        )
        profiling["lu_selection_seconds"] = perf_counter() - lu_select_started
        if lu_frame.empty:
            raise TsrRecipeError(
                "Cached reconstructed LU partitions resolved no landscape-unit rows."
            )
        return lu_frame, [dict(item) for item in chunk_records], profiling

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

    partition_started = perf_counter()
    chunk_records = _materialize_checkpoint_landscape_unit_partitions(
        checkpoint,
        checkpoint_path=checkpoint_path,
        lu_frame=lu_frame,
        selected_landscape_units=selected_landscape_units,
        instance_root=instance_root,
    )
    profiling["partition_materialize_seconds"] = perf_counter() - partition_started
    if not chunk_records:
        raise TsrRecipeError(
            "Reconstructed LU decomposition produced no cached LU chunk files."
        )
    return lu_frame, [dict(item) for item in chunk_records], profiling


def _select_intersecting_lu_names_for_exclusions(
    *,
    exclusion_geometries: gpd.GeoDataFrame,
    lu_frame: gpd.GeoDataFrame,
) -> tuple[set[str], float]:
    if exclusion_geometries.empty or lu_frame.empty:
        return set(), 0.0
    select_started = perf_counter()
    candidate_indices = lu_frame.sindex.query(
        exclusion_geometries.geometry,
        predicate="intersects",
    )
    if getattr(candidate_indices, "ndim", 1) == 2:
        candidate_values = candidate_indices[1]
    else:
        candidate_values = candidate_indices
    unique_indices = sorted({int(index) for index in candidate_values.tolist()})
    if not unique_indices:
        return set(), perf_counter() - select_started
    lu_names = {
        str(value).strip()
        for value in lu_frame.iloc[unique_indices]
        .get("LANDSCAPE_UNIT_NAME", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .tolist()
        if str(value).strip()
    }
    return lu_names, perf_counter() - select_started


def _apply_aspatial_thlb_keep_factor(
    checkpoint: gpd.GeoDataFrame,
    *,
    keep_factor: float,
) -> tuple[gpd.GeoDataFrame, int]:
    updated = checkpoint.copy()
    active_mask = updated["thlb_fact"].astype(float) > 0.0
    if not active_mask.any():
        return updated, 0
    if "thlb" in updated.columns:
        updated["thlb"] = updated["thlb"].astype(float)
    updated.loc[active_mask, "thlb_fact"] = (
        updated.loc[active_mask, "thlb_fact"].astype(float) * keep_factor
    )
    if "thlb" in updated.columns:
        updated.loc[active_mask, "thlb"] = updated.loc[active_mask, "thlb_fact"].astype(
            float
        )
    return updated, int(active_mask.sum())


def _apply_aspatial_area_keep_factor(
    checkpoint: gpd.GeoDataFrame,
    *,
    keep_factor: float,
) -> tuple[gpd.GeoDataFrame, int]:
    updated = checkpoint.copy()
    canonical_area_sqm = _resolve_canonical_stand_area_sqm(updated)
    active_mask = canonical_area_sqm.astype(float) > 0.0
    if not active_mask.any():
        return updated, 0
    updated[TSR_EFFECTIVE_AREA_SQM_COLUMN] = (
        canonical_area_sqm.astype(float) * keep_factor
    )
    updated.loc[active_mask, "_stand_area_sqm"] = updated.loc[
        active_mask, TSR_EFFECTIVE_AREA_SQM_COLUMN
    ].astype(float)
    return updated, int(active_mask.sum())


def _apply_reconstructed_lu_aspatial_thlb_reduction(
    *,
    chunk_records: Sequence[dict[str, Any]],
    runtime_step_root: Path,
    target_removed_area_ha: float,
) -> tuple[list[dict[str, Any]], float, int, int]:
    if not chunk_records or target_removed_area_ha <= 0.0:
        return [dict(item) for item in chunk_records], 0.0, 0, 0
    current_managed_area_ha = 0.0
    frames_by_lu: dict[str, gpd.GeoDataFrame] = {}
    for record in chunk_records:
        lu_name = str(record.get("lu_name", "")).strip()
        frame = _load_lu_chunk_frame(Path(record["chunk_path"]))
        frames_by_lu[lu_name] = frame
        current_managed_area_ha += _managed_area_ha(frame)
    if current_managed_area_ha <= 0.0:
        return [dict(item) for item in chunk_records], 0.0, 0, 0
    removed_area_ha = min(float(target_removed_area_ha), current_managed_area_ha)
    keep_factor = (current_managed_area_ha - removed_area_ha) / current_managed_area_ha
    updated_records: list[dict[str, Any]] = []
    affected_row_count = 0
    touched_chunk_count = 0
    for index, record in enumerate(chunk_records, start=1):
        current_record = dict(record)
        lu_name = str(current_record.get("lu_name", "")).strip()
        updated_chunk, current_affected = _apply_aspatial_thlb_keep_factor(
            frames_by_lu[lu_name],
            keep_factor=keep_factor,
        )
        affected_row_count += current_affected
        if current_affected > 0:
            touched_chunk_count += 1
        chunk_path = (
            runtime_step_root
            / f"{index:03d}_{_normalize_step_slug(lu_name or 'chunk')}.feather"
        )
        _write_lu_chunk_frame(updated_chunk, chunk_path=chunk_path)
        current_record["chunk_path"] = chunk_path
        updated_records.append(current_record)
    return updated_records, removed_area_ha, affected_row_count, touched_chunk_count


def _apply_reconstructed_lu_aspatial_area_reduction(
    *,
    chunk_records: Sequence[dict[str, Any]],
    runtime_step_root: Path,
    target_removed_area_ha: float,
) -> tuple[list[dict[str, Any]], float, int, int]:
    if not chunk_records or target_removed_area_ha <= 0.0:
        return [dict(item) for item in chunk_records], 0.0, 0, 0
    current_area_ha = 0.0
    frames_by_lu: dict[str, gpd.GeoDataFrame] = {}
    for record in chunk_records:
        lu_name = str(record.get("lu_name", "")).strip()
        frame = _load_lu_chunk_frame(Path(record["chunk_path"]))
        frames_by_lu[lu_name] = frame
        current_area_ha += float(
            _resolve_canonical_stand_area_sqm(frame).sum() / 10000.0
        )
    if current_area_ha <= 0.0:
        return [dict(item) for item in chunk_records], 0.0, 0, 0
    removed_area_ha = min(float(target_removed_area_ha), current_area_ha)
    keep_factor = (current_area_ha - removed_area_ha) / current_area_ha
    updated_records: list[dict[str, Any]] = []
    affected_row_count = 0
    touched_chunk_count = 0
    for index, record in enumerate(chunk_records, start=1):
        current_record = dict(record)
        lu_name = str(current_record.get("lu_name", "")).strip()
        updated_chunk, current_affected = _apply_aspatial_area_keep_factor(
            frames_by_lu[lu_name],
            keep_factor=keep_factor,
        )
        affected_row_count += current_affected
        if current_affected > 0:
            touched_chunk_count += 1
        chunk_path = (
            runtime_step_root
            / f"{index:03d}_{_normalize_step_slug(lu_name or 'chunk')}.feather"
        )
        _write_lu_chunk_frame(updated_chunk, chunk_path=chunk_path)
        current_record["chunk_path"] = chunk_path
        updated_records.append(current_record)
    return updated_records, removed_area_ha, affected_row_count, touched_chunk_count


def _apply_reconstructed_lu_checkpoint_attribute_exclusion(
    *,
    chunk_records: Sequence[dict[str, Any]],
    runtime_step_root: Path,
    filters: Sequence[dict[str, Any]],
    mode: str,
) -> tuple[list[dict[str, Any]], float, int, int]:
    if not chunk_records or not filters:
        return [dict(item) for item in chunk_records], 0.0, 0, 0
    updated_records: list[dict[str, Any]] = []
    removed_area_ha = 0.0
    affected_row_count = 0
    touched_chunk_count = 0
    for index, record in enumerate(chunk_records, start=1):
        current_record = dict(record)
        lu_name = str(current_record.get("lu_name", "")).strip()
        chunk = _load_lu_chunk_frame(Path(current_record["chunk_path"]))
        updated_chunk, current_removed_area_ha = _apply_checkpoint_attribute_filters(
            chunk,
            filters=filters,
            mode=mode,
            preserve_geometry=False,
        )
        current_affected = max(len(chunk) - len(updated_chunk), 0)
        removed_area_ha += float(current_removed_area_ha)
        affected_row_count += current_affected
        if current_affected > 0:
            touched_chunk_count += 1
            chunk_path = (
                runtime_step_root
                / f"{index:03d}_{_normalize_step_slug(lu_name or 'chunk')}.feather"
            )
            _write_lu_chunk_frame(updated_chunk, chunk_path=chunk_path)
            current_record["chunk_path"] = chunk_path
        updated_records.append(current_record)
    return updated_records, removed_area_ha, affected_row_count, touched_chunk_count


def _resolve_parent_exact_removed_area_ha(
    *,
    applied_steps: Sequence[dict[str, Any]],
    parent_step_id: str,
) -> float:
    total = 0.0
    for step in applied_steps:
        if str(step.get("parent_step_id", "")).strip() != parent_step_id:
            continue
        if str(step.get("normalized_action", "")).strip() != "exclude":
            continue
        total += float(step.get("affected_area_ha", 0.0) or 0.0)
    return total


def _execute_reconstructed_lu_exclusion_step(
    *,
    chunk_records: Sequence[dict[str, Any]],
    exclusion_geometries: gpd.GeoDataFrame,
    lu_frame: gpd.GeoDataFrame,
    runtime_step_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lu_names, lu_selection_seconds = _select_intersecting_lu_names_for_exclusions(
        exclusion_geometries=exclusion_geometries,
        lu_frame=lu_frame,
    )
    if not lu_names:
        return [dict(item) for item in chunk_records], {
            "candidate_query_seconds": lu_selection_seconds,
            "lu_chunk_count": 0,
            "intersecting_exclusion_feature_count": 0,
            "candidate_row_count": 0,
            "affected_fragment_count": 0,
            "affected_area_ha": 0.0,
            "fragment_batch_count": 0,
            "overlay_seconds": 0.0,
            "write_seconds": 0.0,
        }

    exclusion_sindex = exclusion_geometries.sindex
    updated_records: list[dict[str, Any]] = []
    candidate_query_seconds = lu_selection_seconds
    overlay_seconds = 0.0
    write_seconds = 0.0
    candidate_row_count = 0
    affected_fragment_count = 0
    affected_area_ha = 0.0
    fragment_batch_count = 0
    intersecting_feature_indices: set[int] = set()
    touched_chunk_count = 0

    for index, record in enumerate(chunk_records, start=1):
        current_record = dict(record)
        lu_name = str(current_record.get("lu_name", "")).strip()
        if lu_name not in lu_names:
            updated_records.append(current_record)
            continue
        chunk = _load_lu_chunk_frame(Path(current_record["chunk_path"]))
        local_query_started = perf_counter()
        local_exclusion_indices = exclusion_sindex.query(
            chunk.geometry,
            predicate="intersects",
        )
        candidate_query_seconds += perf_counter() - local_query_started
        if getattr(local_exclusion_indices, "ndim", 1) == 2:
            local_exclusion_values = local_exclusion_indices[1]
        else:
            local_exclusion_values = local_exclusion_indices
        unique_exclusion_indices = sorted(
            {int(value) for value in local_exclusion_values.tolist()}
        )
        if not unique_exclusion_indices:
            updated_records.append(current_record)
            continue
        local_exclusions = exclusion_geometries.iloc[unique_exclusion_indices].copy()
        intersecting_feature_indices.update(unique_exclusion_indices)

        overlay_started = perf_counter()
        (
            updated_chunk,
            current_candidate_count,
            current_affected_fragment_count,
            current_affected_area_ha,
            current_fragment_batch_count,
        ) = _fragment_binary_exclusion_step_chunked(
            checkpoint=chunk,
            exclusion_geometries=local_exclusions,
        )
        overlay_seconds += perf_counter() - overlay_started
        candidate_row_count += int(current_candidate_count)
        affected_fragment_count += int(current_affected_fragment_count)
        affected_area_ha += float(current_affected_area_ha)
        fragment_batch_count += int(current_fragment_batch_count)

        if current_candidate_count > 0:
            touched_chunk_count += 1
        if current_affected_fragment_count <= 0:
            updated_records.append(current_record)
            continue

        chunk_write_started = perf_counter()
        chunk_path = (
            runtime_step_root
            / f"{index:03d}_{_normalize_step_slug(lu_name or 'chunk')}.feather"
        )
        _write_lu_chunk_frame(updated_chunk, chunk_path=chunk_path)
        write_seconds += perf_counter() - chunk_write_started
        current_record["chunk_path"] = chunk_path
        updated_records.append(current_record)

    return updated_records, {
        "candidate_query_seconds": candidate_query_seconds,
        "lu_chunk_count": touched_chunk_count,
        "intersecting_exclusion_feature_count": len(intersecting_feature_indices),
        "candidate_row_count": candidate_row_count,
        "affected_fragment_count": affected_fragment_count,
        "affected_area_ha": affected_area_ha,
        "fragment_batch_count": fragment_batch_count,
        "overlay_seconds": overlay_seconds,
        "write_seconds": write_seconds,
    }


def _merge_reconstructed_lu_chunk_records(
    chunk_records: Sequence[dict[str, Any]],
) -> tuple[gpd.GeoDataFrame, float]:
    if not chunk_records:
        return gpd.GeoDataFrame(geometry=[], crs=BC_ALBERS_EPSG), 0.0
    merge_started = perf_counter()
    merged_frames = [
        _load_lu_chunk_frame(Path(item["chunk_path"])) for item in chunk_records
    ]
    merged = gpd.GeoDataFrame(
        pd.concat(merged_frames, ignore_index=True),
        geometry="geometry",
        crs=BC_ALBERS_EPSG,
    )
    merged = merged.loc[~merged.geometry.is_empty].copy()
    merged = _assign_fragment_feature_ids(merged)
    return merged, perf_counter() - merge_started


def _summarize_reconstructed_diagnostics(
    diagnostic_steps: Sequence[dict[str, Any]],
    *,
    top_n: int = 5,
) -> dict[str, Any]:
    total_runtime_seconds = 0.0
    overlay_seconds = 0.0
    candidate_query_seconds = 0.0
    write_seconds = 0.0
    merge_seconds = 0.0
    source_load_seconds = 0.0
    slowest_steps: list[dict[str, Any]] = []

    for step in diagnostic_steps:
        total_runtime_seconds += float(step.get("total_seconds", 0.0) or 0.0)
        overlay_seconds += float(step.get("overlay_seconds", 0.0) or 0.0)
        candidate_query_seconds += float(
            step.get("candidate_query_seconds", 0.0) or 0.0
        )
        write_seconds += float(step.get("write_seconds", 0.0) or 0.0)
        merge_seconds += float(step.get("merge_seconds", 0.0) or 0.0)
        source_load_seconds += float(step.get("source_load_seconds", 0.0) or 0.0)

        step_id = str(step.get("step_id", "")).strip()
        normalized_action = str(step.get("normalized_action", "")).strip()
        if not step_id or step_id.startswith("__"):
            continue
        slowest_steps.append(
            {
                "step_id": step_id,
                "label": str(step.get("label", "")).strip(),
                "normalized_action": normalized_action,
                "spatial_application_mode": str(
                    step.get("spatial_application_mode", "")
                ).strip(),
                "run_status": str(step.get("run_status", "")).strip(),
                "total_seconds": float(step.get("total_seconds", 0.0) or 0.0),
                "overlay_seconds": float(step.get("overlay_seconds", 0.0) or 0.0),
                "candidate_query_seconds": float(
                    step.get("candidate_query_seconds", 0.0) or 0.0
                ),
                "write_seconds": float(step.get("write_seconds", 0.0) or 0.0),
                "lu_chunk_count": int(step.get("lu_chunk_count", 0) or 0),
                "intersecting_exclusion_feature_count": int(
                    step.get("intersecting_exclusion_feature_count", 0) or 0
                ),
            }
        )

    slowest_steps.sort(key=lambda item: item["total_seconds"], reverse=True)
    return {
        "total_runtime_seconds": total_runtime_seconds,
        "source_load_seconds": source_load_seconds,
        "candidate_query_seconds": candidate_query_seconds,
        "overlay_seconds": overlay_seconds,
        "write_seconds": write_seconds,
        "merge_seconds": merge_seconds,
        "slowest_steps": slowest_steps[:top_n],
    }


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


def _format_thlb_filter_value(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(f"`{item}`" for item in value)
    return f"`{value}`"


def _describe_thlb_filter(item: dict[str, Any]) -> str:
    field = str(item.get("field", "")).strip()
    operator = str(item.get("operator", "")).strip()
    value = item.get("value")
    if operator == "eq":
        return f"`{field}` = {_format_thlb_filter_value(value)}"
    if operator == "ne":
        return f"`{field}` != {_format_thlb_filter_value(value)}"
    if operator == "lt":
        return f"`{field}` < {_format_thlb_filter_value(value)}"
    if operator == "le":
        return f"`{field}` <= {_format_thlb_filter_value(value)}"
    if operator == "gt":
        return f"`{field}` > {_format_thlb_filter_value(value)}"
    if operator == "ge":
        return f"`{field}` >= {_format_thlb_filter_value(value)}"
    if operator == "in":
        return f"`{field}` in [{_format_thlb_filter_value(value)}]"
    if operator == "not_in":
        return f"`{field}` not in [{_format_thlb_filter_value(value)}]"
    if operator == "is_null":
        return f"`{field}` is null"
    if operator == "not_blank":
        return f"`{field}` is not blank"
    return f"`{field}` {operator} {_format_thlb_filter_value(value)}"


def _describe_thlb_filters(
    filters: Sequence[dict[str, Any]],
    *,
    mode: str,
) -> str:
    clauses = [
        _describe_thlb_filter(item) for item in filters if isinstance(item, dict)
    ]
    if not clauses:
        return ""
    joiner = " and " if mode == "all" else " or "
    return joiner.join(clauses)


def _collect_thlb_step_override_summaries(
    *,
    step: dict[str, Any],
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> tuple[str, ...]:
    summaries: list[str] = []
    for entry_id in step.get("linked_source_entry_ids", ()):
        source_entry = source_entry_map.get(str(entry_id).strip())
        if source_entry is None:
            continue
        override_entry = _lookup_override_for_source_entry(
            source_entry=source_entry,
            override_entries=override_entries,
        )
        if override_entry is None or not override_entry.override_kind:
            continue
        summary = (
            f"`{entry_id}` uses `{override_entry.override_kind}` from "
            "`config/tsr/source_layer_overrides.yaml`"
        )
        if override_entry.override_value:
            summary += f" with value `{override_entry.override_value}`"
        summaries.append(summary)
    return tuple(summaries)


def _describe_exact_thlb_step_logic(step: dict[str, Any]) -> str:
    operation_type = str(
        step.get("compiled_operation_type", step.get("normalized_action", ""))
    ).strip()
    spatial_mode = str(step.get("spatial_application_mode", "")).strip()
    buffer_distance = step.get("buffer_distance_m")
    source_filters = _describe_thlb_filters(
        [
            item
            for item in step.get("source_attribute_filters", ())
            if isinstance(item, dict)
        ],
        mode=str(step.get("source_attribute_mode", "all")).strip() or "all",
    )
    checkpoint_filters = _describe_thlb_filters(
        [
            item
            for item in step.get("checkpoint_attribute_filters", ())
            if isinstance(item, dict)
        ],
        mode=str(step.get("checkpoint_attribute_mode", "all")).strip() or "all",
    )
    if operation_type == "select_spatial_intersect":
        detail = "Intersect the working land base with the linked source geometry."
        if source_filters:
            detail += f" Source rows are filtered by {source_filters}."
        return detail
    if operation_type == "buffer_then_intersect":
        distance_text = (
            f"{float(buffer_distance):.3f} m"
            if buffer_distance is not None
            else "the configured distance"
        )
        detail = f"Buffer the linked source geometry by {distance_text}, then intersect the working land base."
        if source_filters:
            detail += f" Source rows are filtered by {source_filters}."
        return detail
    if operation_type == "select_attribute":
        detail = "Apply checkpoint attribute filtering to the working land base."
        if checkpoint_filters:
            detail += f" The active filter is {checkpoint_filters}."
        return detail
    if operation_type == "curve_volume_threshold_exclusion":
        threshold = step.get("curve_volume_threshold_m3_per_ha")
        metric = str(step.get("curve_volume_metric", "")).strip()
        age = step.get("curve_volume_age_years")
        threshold_text = (
            f"{float(threshold):.3f} m3/ha"
            if threshold is not None
            else "the configured threshold"
        )
        metric_text = "assigned curve volume"
        if metric == _CURVE_VOLUME_METRIC_AGE and age is not None:
            metric_text = f"assigned curve volume at age {int(float(age))}"
        elif metric == _CURVE_VOLUME_METRIC_AUTO:
            metric_text = "treated CMAI / untreated culmination curve volume"
        detail = f"Exclude rows whose {metric_text} falls below {threshold_text}."
        if checkpoint_filters:
            detail += f" This rule only evaluates rows where {checkpoint_filters}."
        return detail
    if operation_type in {"aspatial_reduction", "aspatial_area_reduction"}:
        benchmark = step.get("benchmark_marginal_area_ha")
        prefix = "Apply an aspatial area reduction"
        if spatial_mode == "aspatial_fallback":
            prefix = (
                "TSR area target applied as a documented aspatial deduction because "
                "no exact spatial implementation is available in this lane"
            )
        if benchmark is not None:
            return (
                f"{prefix} using the TSR benchmark target of {float(benchmark):.3f} ha."
            )
        return f"{prefix} using the configured TSR benchmark target."
    if operation_type == "no_deduction":
        return "Record this parent step as an explicit no-op: no executable land-base deduction is applied."
    return _describe_thlb_step_logic(step)


def _normalize_optional_thlb_review_value(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized.lower() in {"", "none", "null"}:
        return ""
    return normalized


def _format_thlb_lock_state_markdown(
    lock_state: dict[str, dict[str, Any]],
) -> list[str]:
    lines = ["## Locking / Convergence", ""]
    for scope, label in (("aflb", "AFLB"), ("thlb", "THLB")):
        payload = lock_state.get(scope, {})
        status = "locked" if bool(payload.get("locked")) else "unlocked"
        lines.append(f"- {label} lock state: `{status}`")
        locked_utc = _normalize_optional_thlb_review_value(payload.get("locked_utc"))
        if locked_utc:
            lines.append(f"  - locked UTC: `{locked_utc}`")
        locked_script_path = _normalize_optional_thlb_review_value(
            payload.get("locked_script_path")
        )
        if locked_script_path:
            lines.append(f"  - locked script: `{locked_script_path}`")
        frozen_status_path = _normalize_optional_thlb_review_value(
            payload.get("frozen_status_report_path")
        )
        if frozen_status_path:
            lines.append(f"  - frozen status report: `{frozen_status_path}`")
        frozen_audit_path = _normalize_optional_thlb_review_value(
            payload.get("frozen_audit_path")
        )
        if frozen_audit_path:
            lines.append(f"  - frozen audit: `{frozen_audit_path}`")
        note = _normalize_optional_thlb_review_value(payload.get("note"))
        if note:
            lines.append(f"  - note: {note}")
    lines.extend(
        [
            "- Lock dependency: cutting the AFLB lock automatically invalidates the THLB lock because THLB is downstream from the AFLB universe definition.",
            "",
        ]
    )
    return lines


def _normalize_sequence_strings(values: Sequence[Any]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _normalize_identifier_set(values: Sequence[str]) -> set[str]:
    return {value.strip().casefold() for value in values if value.strip()}


def _collect_parent_step_candidate_operation_types(
    parent_step: dict[str, Any], compiled_steps: Sequence[dict[str, Any]]
) -> list[str]:
    operation_types: list[str] = []
    for step in compiled_steps:
        for key in ("compiled_operation_type", "operation_type", "normalized_action"):
            value = str(step.get(key, "")).strip()
            if value:
                operation_types.append(value)
    for subrule in parent_step.get("draft_subrules", ()):
        if not isinstance(subrule, dict):
            continue
        value = str(subrule.get("candidate_operation_type", "")).strip()
        if value:
            operation_types.append(value)
    return list(dict.fromkeys(operation_types))


def _collect_parent_step_likely_source_layer_families(
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
) -> list[str]:
    families: list[str] = []
    for subrule in parent_step.get("draft_subrules", ()):
        if not isinstance(subrule, dict):
            continue
        families.extend(
            _normalize_sequence_strings(subrule.get("candidate_layers", ()))
        )
    for step in compiled_steps:
        for entry_id in _normalize_sequence_strings(
            step.get("linked_source_entry_ids", ())
        ):
            source_entry = source_entry_map.get(entry_id, {})
            recommended_query = str(source_entry.get("recommended_query", "")).strip()
            if recommended_query:
                families.append(recommended_query)
            else:
                families.append(entry_id)
    return list(dict.fromkeys(families))


def _collect_parent_step_likely_fields(parent_step: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for subrule in parent_step.get("draft_subrules", ()):
        if not isinstance(subrule, dict):
            continue
        fields.extend(_normalize_sequence_strings(subrule.get("candidate_fields", ())))
    return list(dict.fromkeys(fields))


def _collect_parent_step_likely_values(parent_step: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for subrule in parent_step.get("draft_subrules", ()):
        if not isinstance(subrule, dict):
            continue
        values.extend(_normalize_sequence_strings(subrule.get("candidate_values", ())))
    return list(dict.fromkeys(values))


def _collect_parent_step_supporting_provenance(
    parent_step: dict[str, Any],
) -> list[str]:
    values: list[str] = []
    table_provenance = str(parent_step.get("table_provenance", "")).strip()
    if table_provenance:
        values.append(table_provenance)
    subsection_number = str(parent_step.get("subsection_number", "")).strip()
    subsection_title = str(parent_step.get("subsection_title", "")).strip()
    if subsection_number or subsection_title:
        values.append(
            _normalize_whitespace(
                " ".join(part for part in (subsection_number, subsection_title) if part)
            )
        )
    values.extend(
        _normalize_sequence_strings(parent_step.get("supporting_provenance_ids", ()))
    )
    return list(dict.fromkeys(values))


def _summarize_parent_step_current_femic_state(
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    status_counts: Counter[str] = Counter()
    linked_source_statuses: dict[str, str] = {}
    for step in compiled_steps:
        status = str(step.get("run_status", step.get("step_status", ""))).strip()
        if status:
            status_counts.update([status])
        for entry_id in _normalize_sequence_strings(
            step.get("linked_source_entry_ids", ())
        ):
            source_entry = source_entry_map.get(entry_id, {})
            linked_source_statuses[entry_id] = str(
                source_entry.get("current_public_status", "")
                or source_entry.get("run_status", "")
            ).strip()
    return {
        "execution_class": str(parent_step.get("execution_class", "")).strip(),
        "ratchet_state": _infer_thlb_parent_step_ratchet_state(parent_step),
        "compiled_step_count": len(compiled_steps),
        "compiled_status_summary": dict(sorted(status_counts.items())),
        "linked_source_statuses": dict(sorted(linked_source_statuses.items())),
    }


def _is_parent_step_manual_or_aspatial(
    parent_step: dict[str, Any], compiled_steps: Sequence[dict[str, Any]]
) -> bool:
    if "aspatial" in str(parent_step.get("execution_class", "")).strip().casefold():
        return True
    for step in compiled_steps:
        operation = str(
            step.get("compiled_operation_type", "") or step.get("operation_type", "")
        ).strip()
        status = str(step.get("run_status", step.get("step_status", ""))).strip()
        if operation in {"aspatial_reduction", "no_deduction"}:
            return True
        if status in {"manual_review_required", "unsupported"}:
            return True
    for subrule in parent_step.get("draft_subrules", ()):
        if not isinstance(subrule, dict):
            continue
        operation = str(subrule.get("candidate_operation_type", "")).strip()
        review_status = str(subrule.get("review_status", "")).strip()
        if (
            operation == "aspatial_reduction"
            or review_status == "manual_review_required"
        ):
            return True
    return False


def _is_parent_step_blocked_missing_source(
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
) -> bool:
    blocked_statuses = {"no_hit", "failed", "ordered", "followup_pending"}
    for step in compiled_steps:
        missing_ids = _normalize_sequence_strings(
            step.get("missing_source_entry_ids", ())
        )
        if missing_ids:
            return True
        for entry_id in _normalize_sequence_strings(
            step.get("linked_source_entry_ids", ())
        ):
            source_entry = source_entry_map.get(entry_id)
            if source_entry is None:
                return True
            current_status = str(
                source_entry.get("current_public_status", "")
                or source_entry.get("run_status", "")
            ).strip()
            if current_status in blocked_statuses:
                return True
    if not compiled_steps:
        for subrule in parent_step.get("draft_subrules", ()):
            if not isinstance(subrule, dict):
                continue
            if _normalize_sequence_strings(subrule.get("candidate_layers", ())):
                return False
    return False


def _match_warmstart_motif(
    *,
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
    patterns: Sequence[dict[str, Any]],
) -> dict[str, Any] | None:
    stage = str(parent_step.get("land_base_stage", "")).strip().casefold()
    execution_class = str(parent_step.get("execution_class", "")).strip().casefold()
    label = str(parent_step.get("parent_label", "")).strip().casefold()
    operation_types = _normalize_identifier_set(
        _collect_parent_step_candidate_operation_types(parent_step, compiled_steps)
    )
    source_families = _normalize_identifier_set(
        _collect_parent_step_likely_source_layer_families(
            parent_step, compiled_steps, source_entry_map
        )
    )
    fields = _normalize_identifier_set(_collect_parent_step_likely_fields(parent_step))
    best_score = 0
    best_pattern: dict[str, Any] | None = None
    for pattern in patterns:
        score = 0
        substantive_hit = False
        stages = _normalize_identifier_set(pattern.get("land_base_stages", ()))
        if stages and stage in stages:
            score += 3
        execution_classes = _normalize_identifier_set(
            pattern.get("execution_classes", ())
        )
        if execution_classes and execution_class in execution_classes:
            score += 3
        pattern_operations = _normalize_identifier_set(
            pattern.get("operation_types", ())
        )
        if pattern_operations and operation_types.intersection(pattern_operations):
            score += 4
            substantive_hit = True
        for token in _normalize_sequence_strings(pattern.get("label_contains", ())):
            if token.casefold() in label:
                score += 2
                substantive_hit = True
        for token in _normalize_sequence_strings(pattern.get("source_prefixes", ())):
            token_folded = token.casefold()
            if any(item.startswith(token_folded) for item in source_families):
                score += 1
                substantive_hit = True
        for token in _normalize_sequence_strings(pattern.get("field_contains", ())):
            token_folded = token.casefold()
            if any(token_folded in item for item in fields):
                score += 1
                substantive_hit = True
        if substantive_hit and score > best_score:
            best_score = score
            best_pattern = pattern
    return best_pattern if best_score > 0 else None


def _derive_warmstart_status(
    *,
    parent_step: dict[str, Any],
    compiled_steps: Sequence[dict[str, Any]],
    source_entry_map: dict[str, dict[str, Any]],
    matched_pattern: dict[str, Any] | None,
) -> str:
    if _is_parent_step_manual_or_aspatial(parent_step, compiled_steps):
        return _THLB_WARMSTART_STATUS_MANUAL_OR_ASPATIAL
    if _is_parent_step_blocked_missing_source(
        parent_step, compiled_steps, source_entry_map
    ):
        return _THLB_WARMSTART_STATUS_BLOCKED_MISSING_SOURCE
    if compiled_steps:
        return _THLB_WARMSTART_STATUS_COMPILED_READY
    if matched_pattern is not None:
        return _THLB_WARMSTART_STATUS_REVIEW_PATTERN_MATCH
    return _THLB_WARMSTART_STATUS_NO_PATTERN_MATCH


def _build_generic_warmstart_review_questions(
    *, parent_step: dict[str, Any], warmstart_status: str
) -> list[str]:
    questions = [
        "Does the TSR row clearly belong in this stage of the GLB/AFLB/LHLB/THLB ladder?",
        "Does the current FEMIC interpretation match the plain TSR text and benchmark row?",
    ]
    if warmstart_status == _THLB_WARMSTART_STATUS_BLOCKED_MISSING_SOURCE:
        questions.append(
            "Which reviewed source layer, override, or local artifact would unblock this rule?"
        )
    elif warmstart_status == _THLB_WARMSTART_STATUS_MANUAL_OR_ASPATIAL:
        questions.append(
            "Is this step intentionally manual/aspatial in the accepted lane, or does it need a better spatial interpretation later?"
        )
    elif warmstart_status == _THLB_WARMSTART_STATUS_COMPILED_READY:
        questions.append(
            "Is the existing compiled FEMIC logic still the right executable interpretation to keep?"
        )
    else:
        questions.append(
            "Which likely layers, fields, and values should a human inspect first to finish this rule?"
        )
    if str(parent_step.get("benchmark_marginal_area_ha", "")).strip():
        questions.append(
            "Is the benchmark marginal deduction directionally plausible relative to the current FEMIC state?"
        )
    return questions


def _build_tsr_thlb_warmstart_payload(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    source_entry_map: dict[str, dict[str, Any]],
    patterns: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    milestones, parent_stage_groups = _parent_steps_grouped_by_stage(recipe)
    compiled_step_map: dict[str, list[dict[str, Any]]] = {}
    for step in recipe.steps:
        parent_step_id = str(step.get("parent_step_id", "")).strip()
        if parent_step_id:
            compiled_step_map.setdefault(parent_step_id, []).append(dict(step))

    milestone_payload = [
        {
            "parent_step_id": str(item.get("parent_step_id", "")).strip(),
            "parent_label": str(item.get("parent_label", "")).strip(),
            "land_base_stage": str(item.get("land_base_stage", "")).strip(),
            "benchmark_cumulative_area_ha": item.get("benchmark_cumulative_area_ha"),
        }
        for item in milestones
    ]

    entries: list[dict[str, Any]] = []
    for stage in _THLB_STAGE_ORDER:
        for parent_step in parent_stage_groups.get(stage, []):
            parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
            compiled_steps = compiled_step_map.get(parent_step_id, [])
            matched_pattern = _match_warmstart_motif(
                parent_step=parent_step,
                compiled_steps=compiled_steps,
                source_entry_map=source_entry_map,
                patterns=patterns,
            )
            warmstart_status = _derive_warmstart_status(
                parent_step=parent_step,
                compiled_steps=compiled_steps,
                source_entry_map=source_entry_map,
                matched_pattern=matched_pattern,
            )
            motif_id = (
                str(matched_pattern.get("motif_id", "")).strip()
                if matched_pattern
                else ""
            )
            motif_summary = (
                str(matched_pattern.get("motif_summary", "")).strip()
                if matched_pattern
                else ""
            )
            likely_source_layer_families = (
                _collect_parent_step_likely_source_layer_families(
                    parent_step,
                    compiled_steps,
                    source_entry_map,
                )
            )
            likely_fields = _collect_parent_step_likely_fields(parent_step)
            likely_values = _collect_parent_step_likely_values(parent_step)
            likely_review_questions = (
                _normalize_sequence_strings(
                    matched_pattern.get("likely_review_questions", ())
                )
                if matched_pattern
                else []
            )
            if not likely_review_questions:
                likely_review_questions = _build_generic_warmstart_review_questions(
                    parent_step=parent_step,
                    warmstart_status=warmstart_status,
                )
            suggested_operation_class = ""
            if matched_pattern is not None:
                suggested_operation_class = str(
                    matched_pattern.get("suggested_operation_class", "")
                ).strip()
            if not suggested_operation_class:
                suggested_operation_class = (
                    _collect_parent_step_candidate_operation_types(
                        parent_step, compiled_steps
                    )[0]
                    if _collect_parent_step_candidate_operation_types(
                        parent_step, compiled_steps
                    )
                    else str(parent_step.get("execution_class", "")).strip()
                )
            entries.append(
                {
                    "parent_step_id": parent_step_id,
                    "parent_label": str(parent_step.get("parent_label", "")).strip(),
                    "land_base_stage": str(
                        parent_step.get("land_base_stage", "")
                    ).strip(),
                    "benchmark_marginal_area_ha": parent_step.get(
                        "benchmark_marginal_area_ha"
                    ),
                    "benchmark_cumulative_area_ha": parent_step.get(
                        "benchmark_cumulative_area_ha"
                    ),
                    "warmstart_status": warmstart_status,
                    "motif_id": motif_id,
                    "motif_summary": motif_summary,
                    "suggested_operation_class": suggested_operation_class,
                    "likely_source_layer_families": likely_source_layer_families,
                    "likely_fields": likely_fields,
                    "likely_values": likely_values,
                    "likely_review_questions": likely_review_questions,
                    "supporting_tsr_provenance": _collect_parent_step_supporting_provenance(
                        parent_step
                    ),
                    "current_femic_state": _summarize_parent_step_current_femic_state(
                        parent_step,
                        compiled_steps,
                        source_entry_map,
                    ),
                    "human_notes": "",
                }
            )
    return {
        "tsa": recipe.tsa.to_dict(),
        "generated_utc": datetime.now(UTC).isoformat(),
        "artifact_kind": "thlb_warmstart",
        "canonical_recipe_kind": recipe.recipe_kind,
        "non_canonical_warning": (
            "Review aid only. Do not auto-promote warm-start suggestions into executable THLB logic."
        ),
        "milestones": milestone_payload,
        "entries": entries,
    }


def _build_tsr_thlb_warmstart_markdown(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    warmstart_payload: dict[str, Any],
    recipe_relative_path: str,
    yaml_relative_path: str,
) -> str:
    milestones = [
        dict(item)
        for item in warmstart_payload.get("milestones", ())
        if isinstance(item, dict)
    ]
    entries = [
        dict(item)
        for item in warmstart_payload.get("entries", ())
        if isinstance(item, dict)
    ]
    grouped_entries: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _THLB_STAGE_ORDER
    }
    for item in entries:
        stage = str(item.get("land_base_stage", "context")).strip()
        if stage not in grouped_entries:
            stage = "context"
        grouped_entries[stage].append(item)

    lines = [
        f"# THLB Warm-Start Checklist: TSA {recipe.tsa.tsa_code} ({recipe.tsa.tsa_name})",
        "",
        "- Review aid only: this checklist is not canonical executable THLB logic.",
        f"- Canonical reviewed recipe: `{recipe_relative_path}`",
        f"- Editable warm-start YAML: `{yaml_relative_path}`",
        "",
        "## How To Use This Checklist",
        "",
        "- Start from the backbone milestones so you stay oriented in the GLB/AFLB/LHLB/THLB ladder.",
        "- Treat `compiled_ready` rows as already interpreted by FEMIC, but still review whether that interpretation is the right one to keep.",
        "- Treat `blocked_missing_source` and `manual_or_aspatial` rows as honest seams, not hidden automation failures.",
        "- Copy your own notes into the paired YAML file; do not treat this Markdown as the editable source.",
        "",
        "## Backbone Milestones",
        "",
    ]
    for milestone in milestones:
        label = str(milestone.get("parent_label", "")).strip()
        stage = _stage_header_text(str(milestone.get("land_base_stage", "")).strip())
        benchmark = milestone.get("benchmark_cumulative_area_ha")
        benchmark_text = (
            f"`{float(benchmark):.3f} ha`"
            if benchmark is not None
            else "`benchmark not parsed`"
        )
        lines.append(
            f"- **{label}** (`{stage}`) -> remaining benchmark area {benchmark_text}"
        )

    lines.extend(["", "## Stage Checklist", ""])
    for stage in _THLB_STAGE_ORDER:
        stage_entries = grouped_entries.get(stage, [])
        if not stage_entries:
            continue
        lines.append(f"### {_stage_header_text(stage)}")
        lines.append("")
        for entry in stage_entries:
            lines.append(f"#### {entry.get('parent_label', '')}")
            lines.append("")
            lines.append(f"- Parent step id: `{entry.get('parent_step_id', '')}`")
            lines.append(f"- Warm-start status: `{entry.get('warmstart_status', '')}`")
            benchmark_marginal = entry.get("benchmark_marginal_area_ha")
            if benchmark_marginal is not None:
                lines.append(
                    f"- TSR row effect: benchmark marginal deduction `{float(benchmark_marginal):.3f} ha`"
                )
            benchmark_cumulative = entry.get("benchmark_cumulative_area_ha")
            if benchmark_cumulative is not None:
                lines.append(
                    f"- TSR benchmark remaining area after this row: `{float(benchmark_cumulative):.3f} ha`"
                )
            motif_summary = str(entry.get("motif_summary", "")).strip()
            motif_id = str(entry.get("motif_id", "")).strip()
            if motif_id or motif_summary:
                lines.append(
                    "- Recurring motif: "
                    + f"`{motif_id or 'unlabeled'}`"
                    + (f" | {motif_summary}" if motif_summary else "")
                )
            lines.append(
                f"- Suggested operation class to inspect first: `{entry.get('suggested_operation_class', '')}`"
            )
            current_state = entry.get("current_femic_state", {})
            if isinstance(current_state, dict):
                lines.append(
                    "- What FEMIC already has: "
                    + f"execution_class=`{current_state.get('execution_class', '')}`, "
                    + f"ratchet_state=`{current_state.get('ratchet_state', '')}`, "
                    + f"compiled_step_count=`{current_state.get('compiled_step_count', 0)}`"
                )
                compiled_summary = current_state.get("compiled_status_summary", {})
                if isinstance(compiled_summary, dict) and compiled_summary:
                    lines.append(
                        "- Current compiled statuses: "
                        + ", ".join(
                            f"`{status}`={count}"
                            for status, count in sorted(compiled_summary.items())
                        )
                    )
            likely_layers = _normalize_sequence_strings(
                entry.get("likely_source_layer_families", ())
            )
            if likely_layers:
                lines.append(
                    "- Likely source-layer families to inspect: "
                    + ", ".join(f"`{value}`" for value in likely_layers)
                )
            likely_fields = _normalize_sequence_strings(entry.get("likely_fields", ()))
            if likely_fields:
                lines.append(
                    "- Likely fields to inspect: "
                    + ", ".join(f"`{value}`" for value in likely_fields)
                )
            likely_values = _normalize_sequence_strings(entry.get("likely_values", ()))
            if likely_values:
                lines.append(
                    "- Likely values to inspect: "
                    + ", ".join(f"`{value}`" for value in likely_values)
                )
            provenance = _normalize_sequence_strings(
                entry.get("supporting_tsr_provenance", ())
            )
            if provenance:
                lines.append("- Supporting TSR provenance:")
                for value in provenance:
                    lines.append(f"  - `{value}`")
            questions = _normalize_sequence_strings(
                entry.get("likely_review_questions", ())
            )
            if questions:
                lines.append("- Human review questions:")
                for question in questions:
                    lines.append(f"  - {question}")
            lines.append("")
    return "\n".join(lines) + "\n"


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
        if spatial_mode == "blocked_exact_overlay":
            return (
                "Exact fragment-overlay execution was required for this exclusion step, but the "
                "current run blocked instead of silently falling back to a coarse approximation."
            )
        if spatial_mode == "stand_binary_majority":
            return (
                "Apply the explicit debug stand-binary fallback: whole stands are netted down when "
                "the user allows the coarse approximation path."
            )
        return (
            "Exclude the linked polygons from THLB where they intersect the working land base; "
            "the exact execution mode depends on available data and current implementation support."
        )
    if normalized_action == "aspatial_reduction":
        if spatial_mode == "aspatial_fallback":
            return (
                "TSR area target applied as a documented aspatial deduction because no "
                "exact spatial implementation is available in this lane."
            )
        return (
            "Apply a final aspatial THLB reduction of the TSR-cited magnitude after the spatially "
            "executable steps have completed."
        )
    if normalized_action == "aspatial_area_reduction":
        if spatial_mode == "aspatial_fallback":
            return (
                "TSR area target applied as a documented aspatial area deduction because no "
                "exact spatial implementation is available in this lane."
            )
        return (
            "Apply an aspatial area reduction of the TSR-cited magnitude across the active "
            "working land base."
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
    exact_logic = _describe_exact_thlb_step_logic(step)
    override_summaries = _collect_thlb_step_override_summaries(
        step=step,
        source_entry_map=source_entry_map,
        override_entries=override_entries,
    )
    if override_summaries:
        logic_mode = "user_overlay"
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
        f"- Review logic mode: `{logic_mode}`",
        f"- Exact FEMIC logic: {exact_logic}",
    ]
    page_number = step.get("page_number")
    if page_number:
        lines.append(f"- TSR page: `{page_number}`")
    raw_text = str(step.get("raw_text", "")).strip()
    if raw_text:
        lines.append(f"- TSR text: `{raw_text}`")
    lines.append(f"- FEMIC proposed logic: {_describe_thlb_step_logic(step)}")
    if override_summaries:
        lines.append("- Active user overrides:")
        for summary in override_summaries:
            lines.append(f"  - {summary}")

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
    compiled_steps = compiled_step_map.get(
        str(parent_step.get("parent_step_id", "")), []
    )
    override_summaries: list[str] = []
    exact_logic_summaries: list[str] = []
    for compiled_step in compiled_steps:
        exact_logic_summaries.append(
            f"`{compiled_step.get('label', compiled_step.get('step_id', ''))}`: "
            + _describe_exact_thlb_step_logic(compiled_step)
        )
        override_summaries.extend(
            _collect_thlb_step_override_summaries(
                step=compiled_step,
                source_entry_map=source_entry_map,
                override_entries=override_entries,
            )
        )
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
    lines.append(
        "- Review logic mode: "
        + ("`user_overlay`" if override_summaries else "`femic_core`")
    )
    if exact_logic_summaries:
        lines.append("- Exact FEMIC logic:")
        for summary in exact_logic_summaries:
            lines.append(f"  - {summary}")
    if override_summaries:
        lines.append("- Active user overrides:")
        for summary in dict.fromkeys(override_summaries):
            lines.append(f"  - {summary}")
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
_THLB_PARENT_STEP_PRESERVED_APPROVED_REVIEW_KEYS = (
    "draft_subrules",
    "compiled_logic",
)
_THLB_COMPILED_STEP_CORE_IDENTITY_KEYS = (
    "step_id",
    "parent_step_id",
    "label",
    "order_index",
    "step_kind",
    "land_base_stage",
    "stage_label",
    "execution_class",
    "provenance_id",
    "page_number",
    "row_source_kind",
    "benchmark_marginal_area_ha",
    "benchmark_cumulative_area_ha",
)


def _approval_scope_is_smoke_only(approval_scope: str) -> bool:
    normalized = approval_scope.strip().casefold()
    if not normalized:
        return False
    smoke_fragments = (
        "single_lu_smoke_subset",
        "smoke_subset",
        "single_lu_smoke",
        "map_id_smoke",
        "smoke",
    )
    return any(fragment in normalized for fragment in smoke_fragments)


def _thlb_parent_step_preserves_approved_review_logic(parent_step: dict[str, Any]) -> bool:
    if not (
        bool(parent_step.get("approved", False))
        or _infer_thlb_parent_step_ratchet_state(parent_step) == "approved"
    ):
        return False
    approval_scope = str(parent_step.get("approval_scope", "")).strip()
    if _approval_scope_is_smoke_only(approval_scope):
        return False
    return True


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
            preserve_review_logic = _thlb_parent_step_preserves_approved_review_logic(
                existing
            )
            if preserve_review_logic:
                for key in _THLB_PARENT_STEP_PRESERVED_APPROVED_REVIEW_KEYS:
                    if key in existing:
                        updated[key] = copy.deepcopy(existing[key])
        updated["ratchet_state"] = _infer_thlb_parent_step_ratchet_state(updated)
        merged.append(updated)
    return merged


def _merge_preserved_thlb_compiled_steps(
    *,
    existing_steps: Sequence[dict[str, Any]],
    built_steps: Sequence[dict[str, Any]],
    parent_steps: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_by_id = {
        str(item.get("step_id", "")).strip(): dict(item)
        for item in existing_steps
        if isinstance(item, dict) and str(item.get("step_id", "")).strip()
    }
    approved_parent_ids = {
        str(parent_step.get("parent_step_id", "")).strip()
        for parent_step in parent_steps
        if _thlb_parent_step_preserves_approved_review_logic(parent_step)
    }
    approved_parent_step_logic_by_id: dict[str, dict[str, Any]] = {}
    for parent_step in parent_steps:
        parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
        if parent_step_id not in approved_parent_ids:
            continue
        for compiled_step in parent_step.get("compiled_logic", ()) or ():
            if not isinstance(compiled_step, dict):
                continue
            step_id = str(compiled_step.get("step_id", "")).strip()
            if step_id:
                approved_parent_step_logic_by_id[step_id] = dict(compiled_step)
    merged: list[dict[str, Any]] = []
    for step in built_steps:
        updated = dict(step)
        step_id = str(updated.get("step_id", "")).strip()
        parent_step_id = str(updated.get("parent_step_id", "")).strip()
        approved_parent_step = approved_parent_step_logic_by_id.get(step_id)
        if approved_parent_step is not None:
            for key, value in approved_parent_step.items():
                if key in _THLB_COMPILED_STEP_CORE_IDENTITY_KEYS:
                    continue
                updated[key] = copy.deepcopy(value)
        elif parent_step_id in approved_parent_ids:
            existing = existing_by_id.get(str(updated.get("step_id", "")).strip())
            if existing is not None:
                for key, value in existing.items():
                    if key in _THLB_COMPILED_STEP_CORE_IDENTITY_KEYS:
                        continue
                    updated[key] = copy.deepcopy(value)
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
    allow_stand_binary_fallback: bool,
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
    warmstart_markdown_relative_path: str | None = None,
    reconstruction_comparison_markdown_relative_path: str | None = None,
    applied_steps: Sequence[dict[str, Any]],
    diagnostic_steps: Sequence[dict[str, Any]],
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
    lock_state = _current_thlb_lock_state(dict(recipe.recipe_contract))
    for step in applied_steps:
        stage = str(step.get("land_base_stage", "context"))
        if stage not in flat_stage_groups:
            stage = "context"
        flat_stage_groups[stage].append(step)
    fragment_overlay_steps = [
        step
        for step in applied_steps
        if str(step.get("spatial_application_mode", "")).strip() == "fragment_overlay"
    ]
    blocked_exact_overlay_steps = [
        step
        for step in applied_steps
        if str(step.get("spatial_application_mode", "")).strip()
        == "blocked_exact_overlay"
    ]
    stand_binary_steps = [
        step
        for step in applied_steps
        if str(step.get("spatial_application_mode", "")).strip()
        == "stand_binary_majority"
    ]
    aspatial_fallback_steps = [
        step
        for step in applied_steps
        if str(step.get("spatial_application_mode", "")).strip() == "aspatial_fallback"
    ]
    reconstructed_timing_summary = _summarize_reconstructed_diagnostics(
        diagnostic_steps
    )
    lines = [
        f"# THLB Netdown Status Report: TSA {recipe.tsa.tsa_code} ({recipe.tsa.tsa_name})",
        "",
        f"- Generated UTC: `{generated_utc}`",
        f"- Execution mode: `{execution_mode}`",
        "- Debug stand-binary fallback: "
        f"`{'enabled' if allow_stand_binary_fallback else 'disabled'}`",
        f"- Baseline signal: `{baseline_signal}`",
        f"- Recipe path: `{recipe_relative_path}`",
        f"- Checkpoint input: `{checkpoint_relative_path}`",
        f"- Output checkpoint: `{output_relative_path}`",
        f"- Audit JSON: `{audit_relative_path}`",
        f"- Runtime history copy: `{runtime_report_relative_path}`",
        (
            f"- Warm-start checklist: `{warmstart_markdown_relative_path}`"
            if warmstart_markdown_relative_path
            else "- Warm-start checklist: `not generated yet`"
        ),
        (
            "- Reconstruction comparison: "
            f"`{reconstruction_comparison_markdown_relative_path}`"
            if reconstruction_comparison_markdown_relative_path
            else "- Reconstruction comparison: `not generated yet`"
        ),
        "",
        "## Review Dashboard",
        "",
        f"- Selected MAP_ID subset: `{', '.join(selected_map_ids) if selected_map_ids else 'full input'}`",
        f"- Step count: `{step_count}`",
        f"- Input checkpoint area: `{input_area_ha:.3f} ha`",
        f"- GLB / current input proxy: `{input_area_ha:.3f} ha`",
        f"- AFLB / baseline managed area: `{baseline_managed_area_ha:.3f} ha`",
        "- LHLB current: `not yet materialized separately in the current runner`",
        f"- THLB / final managed area: `{final_managed_area_ha:.3f} ha`",
        "- Exact fragment-overlay steps: "
        f"`{len(fragment_overlay_steps)}` / "
        f"`{sum(float(step.get('affected_area_ha', 0.0) or 0.0) for step in fragment_overlay_steps):.3f} ha`",
        "- Explicit aspatial fallback steps: "
        f"`{len(aspatial_fallback_steps)}` / "
        f"`{sum(float(step.get('affected_area_ha', 0.0) or 0.0) for step in aspatial_fallback_steps):.3f} ha`",
        "- Blocked exact-overlay steps: "
        f"`{len(blocked_exact_overlay_steps)}` / "
        f"`{sum(float(step.get('candidate_row_count', 0.0) or 0.0) for step in blocked_exact_overlay_steps):.0f} candidate rows`",
        "- Debug stand-binary fallback steps: "
        f"`{len(stand_binary_steps)}` / "
        f"`{sum(float(step.get('affected_area_ha', 0.0) or 0.0) for step in stand_binary_steps):.3f} ha`",
    ]
    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        lines.extend(
            [
                "- LU-wise exact-overlay chunks touched: "
                f"`{sum(int(step.get('lu_chunk_count', 0) or 0) for step in fragment_overlay_steps)}`",
                "- LU-wise intersecting exclusion features: "
                f"`{sum(int(step.get('intersecting_exclusion_feature_count', 0) or 0) for step in fragment_overlay_steps)}`",
                "- LU-wise reconstructed runtime: "
                f"`{reconstructed_timing_summary['total_runtime_seconds'] / 60.0:.2f} min`",
            ]
        )
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
            "## Backbone Summary",
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

    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
        lines.extend(
            [
                "",
                "## Runtime Timing",
                "",
                "- Source-layer load time: "
                f"`{reconstructed_timing_summary['source_load_seconds']:.2f} s`",
                "- Candidate-query time: "
                f"`{reconstructed_timing_summary['candidate_query_seconds']:.2f} s`",
                "- Exact-overlay / fallback time: "
                f"`{reconstructed_timing_summary['overlay_seconds']:.2f} s`",
                "- Chunk-write time: "
                f"`{reconstructed_timing_summary['write_seconds']:.2f} s`",
                "- Final merge time: "
                f"`{reconstructed_timing_summary['merge_seconds']:.2f} s`",
            ]
        )
        if reconstructed_timing_summary["slowest_steps"]:
            lines.extend(["", "### Slowest Steps", ""])
            for item in reconstructed_timing_summary["slowest_steps"]:
                lines.append(
                    "- "
                    f"`{item['step_id']}` | "
                    f"mode=`{item['spatial_application_mode'] or 'n/a'}` | "
                    f"status=`{item['run_status'] or 'n/a'}` | "
                    f"total=`{item['total_seconds']:.2f} s` | "
                    f"overlay=`{item['overlay_seconds']:.2f} s` | "
                    f"LU chunks=`{item['lu_chunk_count']}` | "
                    f"source features=`{item['intersecting_exclusion_feature_count']}`"
                )

    lines.extend([""])
    lines.extend(_format_thlb_lock_state_markdown(lock_state))
    lines.extend(
        [
            "## Interpretation",
            "",
            "- Non-AFLB polygons are excluded from the reconstruction universe before THLB logic applies.",
            "- Non-THLB polygons or fragments remain inside that working universe and are assigned THLB state downstream from AFLB initialization.",
            "- GLB -> AFLB rows define the modeled universe, AFLB -> LHLB rows define legal harvestability, and LHLB -> THLB rows define projected operational harvestability.",
            "- Review the exact FEMIC logic summaries before trusting raw TSR prose; the compiled logic is the executable contract.",
            "- In reconstructed mode, explicit aspatial fallback means a TSR area target was applied honestly as a deduction bridge; it is not the same thing as exact spatial reproduction.",
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
    warmstart_markdown_relative_path: str | None = None,
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
    lock_state = _current_thlb_lock_state(dict(recipe.recipe_contract))
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
        (
            f"- Warm-start checklist: `{warmstart_markdown_relative_path}`"
            if warmstart_markdown_relative_path
            else "- Warm-start checklist: `not generated yet`"
        ),
        "",
        "## Review Dashboard",
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
    lines.extend([""])
    lines.extend(_format_thlb_lock_state_markdown(lock_state))
    lines.extend(["## Stage-by-Stage THLB Steps", ""])
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
) -> tuple[gpd.GeoDataFrame | None, list[str], bool, list[str]]:
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
    geometries, missing_sources, extent_mismatch_notes = _load_exclusion_geometries(
        instance_root=instance_root,
        linked_source_entry_ids=linked_source_entry_ids,
        source_entry_map=source_entry_map,
        preserve_attributes=bool(filters),
        allowed_geom_types=allowed_geom_types,
        bbox=bbox,
    )
    if geometries is None:
        return None, missing_sources, False, extent_mismatch_notes
    if geometries.empty:
        return geometries, missing_sources, True, extent_mismatch_notes
    if filters:
        geometries = _apply_source_attribute_filters(geometries, filters=filters)
        if geometries.empty:
            return geometries, missing_sources, True, extent_mismatch_notes
    return geometries, missing_sources, False, extent_mismatch_notes


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

    if operation_type == "no_deduction":
        runtime_notes.append("No spatial or aspatial deduction applied for this rule.")
        runtime_item["execution_status"] = "applied_noop"
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
        (
            exclusion_geometries,
            missing_sources,
            no_matching_features,
            extent_mismatch_notes,
        ) = _load_compiled_logic_geometries(
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
        if exclusion_geometries is None:
            if extent_mismatch_notes:
                runtime_item["execution_status"] = "blocked_extent_mismatch"
                runtime_notes.extend(extent_mismatch_notes)
            else:
                runtime_item["execution_status"] = "blocked_missing_source"
                runtime_item["missing_source_entry_ids"] = missing_sources
                runtime_notes.append(
                    "No fetched spatial artifact was available for the linked source entries."
                )
            runtime_item["runtime_notes"] = runtime_notes
            return checkpoint, runtime_item
        if no_matching_features:
            runtime_item["execution_status"] = "applied_noop"
            runtime_notes.extend(extent_mismatch_notes)
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
    if normalized_action == "no_deduction":
        return "no_deduction"
    return ""


def _combine_parent_step_statuses(statuses: set[str]) -> str:
    applied_statuses = {"applied", "applied_noop"}
    if "blocked_extent_mismatch" in statuses:
        return (
            "applied_with_blockers"
            if statuses & applied_statuses
            else "blocked_extent_mismatch"
        )
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
                expected_row_count=len(checkpoint),
                expected_area_ha=float(
                    checkpoint.geometry.area.astype(float).sum() / 10000.0
                ),
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
            warmstart_markdown_relative_path=(
                str(
                    default_tsr_thlb_warmstart_markdown_path(
                        instance_root=instance_root
                    )
                    .relative_to(instance_root)
                    .as_posix()
                )
                if default_tsr_thlb_warmstart_markdown_path(
                    instance_root=instance_root
                ).exists()
                else None
            ),
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
    warmstart_markdown_relative_path: str | None,
    source_entry_map: dict[str, dict[str, Any]],
    override_entries: dict[str, TsrSourceLayerOverrideEntry],
) -> nbformat.NotebookNode:
    milestones, parent_stage_groups = _parent_steps_grouped_by_stage(recipe)
    lock_state_lines = _format_thlb_lock_state_markdown(
        _current_thlb_lock_state(dict(recipe.recipe_contract))
    )
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
                    (
                        f"- Warm-start checklist: `{warmstart_markdown_relative_path}`"
                        if warmstart_markdown_relative_path
                        else "- Warm-start checklist: `not generated yet`"
                    ),
                    "- Canonicality contract: recipe YAML + script during iteration; "
                    "locked script + frozen report at approval time.",
                ]
            )
        ),
        new_markdown_cell(
            "\n".join(
                [
                    "## Review Dashboard",
                    "",
                    "Use the GLB -> AFLB -> LHLB -> THLB ladder as the governing structure.",
                    "Milestones are nodes. Parent steps are the transformation arcs between them.",
                    "Treat the exact FEMIC logic summaries as the executable contract.",
                    "Treat override and lock-state notes as first-class review signals, not footnotes.",
                ]
            )
        ),
        new_markdown_cell("\n".join(lock_state_lines)),
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
                            "### Review prompts",
                            "",
                            "- Benchmark fit / cumulative effect:",
                            "- Core FEMIC logic vs any active override:",
                            "- Lock impact if this step is accepted or revised:",
                            "- Needed follow-up: accept, refine, skip, or block?",
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


def build_tsr_thlb_warmstart(
    *,
    recipe_path: Path,
    markdown_path: Path | None = None,
    yaml_path: Path | None = None,
) -> TsrThlbWarmstartBuildResult:
    """Generate non-canonical THLB warm-start checklist artifacts."""

    (
        recipe,
        instance_root,
        source_recipe,
        source_entry_map,
        _override_entries,
    ) = _load_tsr_thlb_recipe_context(recipe_path)
    resolved_recipe_path = recipe_path.expanduser().resolve()
    resolved_markdown_path = (
        markdown_path.expanduser().resolve()
        if markdown_path is not None
        else default_tsr_thlb_warmstart_markdown_path(instance_root=instance_root)
    )
    resolved_yaml_path = (
        yaml_path.expanduser().resolve()
        if yaml_path is not None
        else default_tsr_thlb_warmstart_yaml_path(instance_root=instance_root)
    )
    for candidate_path in (resolved_markdown_path, resolved_yaml_path):
        try:
            candidate_path.relative_to(instance_root)
        except ValueError as exc:
            raise TsrRecipeError(
                "THLB warm-start artifact paths must live under the instance root."
            ) from exc

    patterns = _load_warmstart_patterns()
    warmstart_payload = _build_tsr_thlb_warmstart_payload(
        recipe=recipe,
        source_entry_map=source_entry_map,
        patterns=patterns,
    )
    markdown_text = _build_tsr_thlb_warmstart_markdown(
        recipe=recipe,
        warmstart_payload=warmstart_payload,
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        yaml_relative_path=str(
            resolved_yaml_path.relative_to(instance_root).as_posix()
        ),
    )
    resolved_yaml_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_yaml_path.write_text(
        yaml.safe_dump(warmstart_payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.write_text(markdown_text, encoding="utf-8")
    milestones, _parent_stage_groups = _parent_steps_grouped_by_stage(recipe)
    status_counts = Counter(
        str(item.get("warmstart_status", "")).strip()
        for item in warmstart_payload.get("entries", ())
        if isinstance(item, dict) and str(item.get("warmstart_status", "")).strip()
    )
    return TsrThlbWarmstartBuildResult(
        recipe_path=resolved_recipe_path,
        markdown_path=resolved_markdown_path,
        yaml_path=resolved_yaml_path,
        tsa=recipe.tsa,
        milestone_count=len(milestones),
        parent_step_count=len(
            [
                item
                for item in recipe.parent_steps
                if str(item.get("parent_kind", "")).strip() != "milestone"
            ]
        ),
        warmstart_status_counts=dict(sorted(status_counts.items())),
    )


def _normalize_float_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_reviewed_thlb_remaining_area_ha(
    recipe: TsrThlbNetdownRecipeRecord,
) -> float | None:
    candidates: list[tuple[int, float]] = []
    for parent_step in recipe.parent_steps:
        normalized_action = str(parent_step.get("normalized_action", "")).strip()
        compiled_logic = [
            dict(item)
            for item in parent_step.get("compiled_logic", ())
            if isinstance(item, dict)
        ]
        compiled_operations = {
            str(item.get("compiled_operation_type", item.get("operation_type", "")))
            .strip()
            .casefold()
            for item in compiled_logic
            if str(
                item.get("compiled_operation_type", item.get("operation_type", ""))
            ).strip()
        }
        if normalized_action == "no_deduction" or "no_deduction" in compiled_operations:
            continue
        remaining_area_ha = _normalize_float_or_none(
            parent_step.get("last_remaining_area_ha")
        )
        if remaining_area_ha is None:
            continue
        candidates.append(
            (int(parent_step.get("row_order", 0) or 0), remaining_area_ha)
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _aggregate_reconstructed_parent_step_results(
    audit_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    raw_steps = audit_payload.get("steps", ())
    if not isinstance(raw_steps, list):
        return aggregated
    for raw_step in raw_steps:
        if not isinstance(raw_step, dict):
            continue
        parent_step_id = str(raw_step.get("parent_step_id", "")).strip()
        if not parent_step_id:
            continue
        record = aggregated.setdefault(
            parent_step_id,
            {
                "reconstructed_removed_area_ha": 0.0,
                "statuses": set(),
                "spatial_modes": set(),
                "step_ids": [],
                "notes": [],
            },
        )
        record["reconstructed_removed_area_ha"] += (
            _normalize_float_or_none(raw_step.get("affected_area_ha")) or 0.0
        )
        run_status = str(
            raw_step.get("run_status", raw_step.get("step_status", ""))
        ).strip()
        if run_status:
            status_set = record["statuses"]
            if isinstance(status_set, set):
                status_set.add(run_status)
        spatial_application_mode = str(
            raw_step.get("spatial_application_mode", "")
        ).strip()
        if spatial_application_mode:
            mode_set = record["spatial_modes"]
            if isinstance(mode_set, set):
                mode_set.add(spatial_application_mode)
        step_id = str(raw_step.get("step_id", "")).strip()
        if step_id:
            step_ids = record["step_ids"]
            if isinstance(step_ids, list) and step_id not in step_ids:
                step_ids.append(step_id)
        notes = record["notes"]
        if isinstance(notes, list):
            for raw_note in raw_step.get("notes", ()):
                note_text = str(raw_note).strip()
                if note_text and note_text not in notes:
                    notes.append(note_text)
    for record in aggregated.values():
        statuses = sorted(
            value for value in record.get("statuses", set()) if isinstance(value, str)
        )
        spatial_modes = sorted(
            value
            for value in record.get("spatial_modes", set())
            if isinstance(value, str)
        )
        if "blocked_exact_overlay" in spatial_modes:
            reconstructed_status = "blocked_exact_overlay"
        elif "aspatial_fallback" in spatial_modes:
            reconstructed_status = "aspatial_fallback"
        elif "fragment_overlay" in spatial_modes:
            reconstructed_status = "fragment_overlay"
        elif statuses:
            reconstructed_status = "+".join(statuses)
        else:
            reconstructed_status = "not_executed"
        record["reconstructed_status"] = reconstructed_status
        record["statuses"] = statuses
        record["spatial_modes"] = spatial_modes
        record["reconstructed_removed_area_ha"] = float(
            record.get("reconstructed_removed_area_ha", 0.0) or 0.0
        )
    return aggregated


def _parent_step_has_reviewed_override(parent_step: dict[str, Any]) -> bool:
    approval_scope = str(parent_step.get("approval_scope", "")).strip().casefold()
    approval_note = str(parent_step.get("approval_note", "")).strip().casefold()
    ratchet_note = str(parent_step.get("ratchet_note", "")).strip().casefold()
    compiled_logic = [
        dict(item)
        for item in parent_step.get("compiled_logic", ())
        if isinstance(item, dict)
    ]
    compiled_operations = {
        str(item.get("compiled_operation_type", item.get("operation_type", "")))
        .strip()
        .casefold()
        for item in compiled_logic
        if str(
            item.get("compiled_operation_type", item.get("operation_type", ""))
        ).strip()
    }
    override_fragments = (
        "skip",
        "calibrat",
        "bridge",
        "user-directed",
        "user directed",
        "no-op",
        "no_deduction",
    )
    text_surface = " ".join((approval_scope, approval_note, ratchet_note))
    if any(fragment in text_surface for fragment in override_fragments):
        return True
    return "no_deduction" in compiled_operations


def _comparison_difference_threshold(*values: float | None) -> float:
    reference = max(
        (abs(value) for value in values if value is not None),
        default=0.0,
    )
    return max(100.0, reference * 0.05)


def _classify_thlb_reconstruction_tsr_fit(
    *,
    parent_step: dict[str, Any],
    benchmark_marginal_area_ha: float | None,
    reconstructed_removed_area_ha: float | None,
    reconstructed_status: str,
) -> tuple[str, str]:
    if str(parent_step.get("parent_kind", "")).strip() == "milestone":
        return (
            "not_comparable_to_tsr",
            "This is a backbone milestone row, so there is no direct strict-vs-TSR "
            "deduction comparison.",
        )
    if benchmark_marginal_area_ha is None:
        return (
            "not_comparable_to_tsr",
            "No TSR benchmark marginal deduction was parsed for this parent step.",
        )
    if "blocked" in reconstructed_status or "missing_source" in reconstructed_status:
        return (
            "not_comparable_to_tsr",
            "The strict lane is still blocked here, so strict-vs-TSR fit is not yet a "
            "clean execution comparison.",
        )
    strict_value = (
        reconstructed_removed_area_ha
        if reconstructed_removed_area_ha is not None
        else 0.0
    )
    delta = strict_value - benchmark_marginal_area_ha
    close_threshold = max(25000.0, abs(benchmark_marginal_area_ha) * 0.10)
    major_threshold = max(50000.0, abs(benchmark_marginal_area_ha) * 0.25)
    if abs(delta) <= close_threshold:
        return (
            "tsr_close_enough",
            "The strict lane is close enough to the TSR benchmark here for practical "
            "exploratory use.",
        )
    if delta > 0.0:
        if abs(delta) <= major_threshold:
            return (
                "strict_over_tsr_minor",
                "The strict lane is somewhat above the TSR benchmark here, but not yet "
                "in the worst problem tier.",
            )
        return (
            "strict_over_tsr_major",
            "The strict lane is materially above the TSR benchmark here, so this "
            "looks like a real strict-lane overcut seam.",
        )
    if abs(delta) <= major_threshold:
        return (
            "strict_under_tsr_minor",
            "The strict lane is somewhat below the TSR benchmark here, but not yet in "
            "the worst problem tier.",
        )
    return (
        "strict_under_tsr_major",
        "The strict lane is materially below the TSR benchmark here, so this looks "
        "like a real strict-lane undercut seam.",
    )


def _describe_reviewed_difference_role(
    *,
    role: str,
    strict_vs_reviewed_delta_ha: float | None,
) -> str:
    if role == "close_match":
        return "Reviewed and strict are also close enough here."
    if role == "reviewed_bridge_only":
        return (
            "The reviewed lane is carrying a much broader bridge here while the strict "
            "lane is not."
        )
    if role == "manual_or_reviewed_override":
        return (
            "The reviewed lane is using an accepted override, calibration, skip, or "
            "no-op that the strict lane does not automatically share."
        )
    if role == "aspatial_bridge_difference":
        return (
            "The reviewed difference here is mostly about an explicit aspatial bridge "
            "choice rather than exact spatial truth."
        )
    if role == "blocked_or_missing_source":
        return (
            "The reviewed difference here is not very informative yet because the "
            "strict lane is still blocked or missing a needed source."
        )
    if role == "not_comparable":
        return (
            "There is no stable strict-vs-reviewed comparison for this parent step yet."
        )
    if strict_vs_reviewed_delta_ha is None:
        return "The reviewed lane is providing contextual comparison only."
    if strict_vs_reviewed_delta_ha > 0.0:
        return "The reviewed lane is lighter here than the strict lane."
    if strict_vs_reviewed_delta_ha < 0.0:
        return "The reviewed lane is heavier here than the strict lane."
    return "The reviewed lane is effectively aligned with the strict lane here."


def _comparison_queue_action(
    *,
    tsr_fit_class: str,
    problem_ownership: str,
    difference_nature: str,
) -> str:
    if problem_ownership == "not_applicable" or difference_nature == "reference_only":
        return "not_applicable"
    if tsr_fit_class == "tsr_close_enough":
        return "defer_low_priority"
    if problem_ownership == "data_exogenous":
        return "improve_data_or_source"
    if problem_ownership == "reviewed_bridge_choice":
        if difference_nature == "accepted_aspatial_bridge":
            return "use_documented_aspatial_fallback"
        return "keep_reviewed_bridge"
    if difference_nature in {
        "accepted_skip_or_noop",
        "accepted_reviewed_override",
        "reviewed_bridge_semantics",
        "missing_late_stage_semantics",
    }:
        return "keep_reviewed_bridge"
    if difference_nature == "accepted_aspatial_bridge":
        return "use_documented_aspatial_fallback"
    if difference_nature in {"missing_or_blocked_data", "weak_public_coverage"}:
        return "improve_data_or_source"
    if difference_nature == "close_match":
        return "defer_low_priority"
    return "fix_strict_logic"


def _comparison_queue_action_summary(action: str) -> str:
    mapping = {
        "not_applicable": "Reference milestone only; no direct corrective action.",
        "fix_strict_logic": "Fix strict logic or semantics in FEMIC.",
        "improve_data_or_source": "Improve or replace the missing/weak source data.",
        "keep_reviewed_bridge": "Keep the reviewed bridge for now and do not force strict parity yet.",
        "use_documented_aspatial_fallback": "Keep or formalize a documented aspatial fallback.",
        "defer_low_priority": "Defer; this is not a top-priority repair right now.",
    }
    return mapping.get(action, "Further review needed.")


def _build_tsr_fit_practical_meaning(
    *,
    tsr_fit_class: str,
    reviewed_difference_role: str,
    strict_vs_reviewed_delta_ha: float | None,
    problem_ownership: str,
) -> str:
    reviewed_context = _describe_reviewed_difference_role(
        role=reviewed_difference_role,
        strict_vs_reviewed_delta_ha=strict_vs_reviewed_delta_ha,
    )
    if tsr_fit_class == "tsr_close_enough":
        return (
            "Strict is close enough to TSR here, so this is not a top-priority repair. "
            + reviewed_context
        )
    if tsr_fit_class == "strict_over_tsr_major":
        return (
            "Strict is badly high against TSR here, so this is a real problem to fix "
            "even before looking at the reviewed lane."
        )
    if tsr_fit_class == "strict_under_tsr_major":
        if problem_ownership == "data_exogenous":
            return (
                "Strict is badly low against TSR here, but the main reason looks "
                "exogenous: the needed data or source contract is missing."
            )
        return (
            "Strict is badly low against TSR here, so this is a real seam to fix or "
            "bridge explicitly."
        )
    if tsr_fit_class in {"strict_over_tsr_minor", "strict_under_tsr_minor"}:
        return (
            "Strict is off TSR here, but not in the very worst tier. "
            + reviewed_context
        )
    return reviewed_context


def _comparison_actionability(bucket: str, adjudication_action: str) -> str:
    if adjudication_action == "not_applicable":
        return "Reference milestone only; inspect cumulative checkpoint area instead of step-local logic."
    if adjudication_action == "use_documented_aspatial_fallback":
        return (
            "Decide whether this documented aspatial fallback should remain the working "
            "contract or be replaced by a better exact implementation later."
        )
    mapping = {
        "close_match": "No immediate action; keep this as a reference step.",
        "reviewed_bridge_only": (
            "Decide whether the reviewed bridge should stay an accepted difference or be "
            "translated into strict semantics."
        ),
        "strict_overcut_candidate": (
            "Inspect strict source inputs and exact logic first; this step may be "
            "cutting more area than the reviewed lane intended."
        ),
        "strict_undercut_candidate": (
            "Inspect missing strict semantics, missing source layers, or reviewed bridge "
            "logic the strict lane does not yet share."
        ),
        "blocked_or_missing_source": (
            "Acquire or repair the missing source/blocked seam before treating this as a "
            "real strict comparison."
        ),
        "manual_or_reviewed_override": (
            "Review the accepted reviewed override before changing the strict lane."
        ),
        "aspatial_bridge_difference": (
            "Decide whether this documented aspatial fallback should remain a bridge or "
            "be replaced by exact spatial logic later."
        ),
        "not_comparable": "Reference/context row only; no direct corrective action.",
    }
    return mapping.get(bucket, "Inspect manually.")


def _default_reconstruction_gap_interpretation(
    *,
    bucket: str,
    parent_step: dict[str, Any],
) -> tuple[str, str, str, str]:
    if str(parent_step.get("parent_kind", "")).strip() == "milestone":
        return (
            "not_applicable",
            "reference_only",
            "This is a backbone milestone row rather than a direct deduction step.",
            "Reference row only; no corrective action.",
        )
    mapping = {
        "close_match": (
            "mixed",
            "close_match",
            "The strict and reviewed lanes are close enough here that this step does not look like a major source of the overall THLB gap.",
            "No immediate action; treat this as a lower-priority reference step.",
        ),
        "reviewed_bridge_only": (
            "mixed",
            "reviewed_bridge_semantics",
            "The reviewed lane is carrying a materially different interpreted bridge here, while the strict lane does not reproduce that same meaning yet.",
            "Decide whether the reviewed bridge should be translated into strict semantics or retained as an accepted bridge difference.",
        ),
        "strict_overcut_candidate": (
            "model_endogenous",
            "strict_logic_overcut",
            "The strict lane appears to be selecting too much area here relative to the reviewed lane.",
            "Inspect strict source interpretation and selection logic first.",
        ),
        "strict_undercut_candidate": (
            "model_endogenous",
            "strict_logic_undercut",
            "The strict lane appears to be selecting too little area here relative to the reviewed lane.",
            "Inspect missing strict logic, missing semantics, or missing source wiring.",
        ),
        "blocked_or_missing_source": (
            "data_exogenous",
            "missing_or_blocked_data",
            "The strict lane cannot execute this step cleanly with the currently available source inputs.",
            "Acquire better data or keep this as an explicit documented fallback seam.",
        ),
        "manual_or_reviewed_override": (
            "reviewed_bridge_choice",
            "accepted_reviewed_override",
            "The reviewed lane is intentionally carrying a skip, calibration, no-op, or reviewed bridge choice here.",
            "Change this only if you intend to reopen the accepted reviewed TSA29 bridge choice.",
        ),
        "aspatial_bridge_difference": (
            "reviewed_bridge_choice",
            "accepted_aspatial_bridge",
            "This step is currently handled as a documented aspatial bridge rather than an exact spatial reproduction.",
            "Keep the fallback or replace it later with a defensible exact implementation.",
        ),
        "not_comparable": (
            "not_applicable",
            "not_comparable",
            "There is no stable strict-vs-reviewed comparison surface here yet.",
            "Reference/context only until a real comparable signal exists.",
        ),
    }
    return mapping.get(
        bucket,
        (
            "mixed",
            "not_comparable",
            "This step still needs manual interpretation.",
            "Inspect manually.",
        ),
    )


def _tsa29_reconstruction_gap_interpretation_override(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    parent_step: dict[str, Any],
) -> tuple[str, str, str, str] | None:
    if str(recipe.tsa.tsa_id).strip() != "tsa_29":
        return None
    parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
    overrides: dict[str, tuple[str, str, str, str]] = {
        "thlb_parent_002_land_not_administered_by_the_province": (
            "model_endogenous",
            "strict_logic_overcut",
            "The strict lane is using a broader ownership interpretation than the reviewed bridge, so it is cutting too much area here.",
            "Tighten the strict ownership mapping and separate the dedicated title/treaty exclusions from the generic F_OWN ownership classes.",
        ),
        "thlb_parent_003_non_forest": (
            "model_endogenous",
            "reviewed_bridge_semantics",
            "The strict lane is only doing a narrow direct waterbody removal here, while the reviewed lane is carrying a much broader non-forest interpretation; in addition, this early GLB-to-AFLB comparison is conditioned by checkpoint1/AFLB initialization rather than a literal raw-GLB replay.",
            "Decide and document the intended strict non-forest semantics before changing code again; this is not just a missing-data problem, and the current stepwise delta should be read as a baseline-conditioned diagnostic rather than a literal raw-GLB replay.",
        ),
        "thlb_parent_004_roads_and_landings": (
            "mixed",
            "accepted_aspatial_bridge",
            "The TSR itself says existing roads, trails, and landings are modeled non-spatially through partial AFLB reductions because the features are too small and incomplete to track cleanly at landscape scale. The strict lane should therefore be judged against the documented aspatial benchmark first, with the narrow permanent-road overlays treated as supporting evidence only.",
            "Keep the documented step-4 aspatial AFLB fallback in place unless you later adopt a better exact road-footprint contract.",
        ),
        "thlb_parent_006_parks_protected_areas_area_base_tenures": (
            "mixed",
            "strict_logic_undercut",
            "The strict lane is lighter than the reviewed lane here, likely because tenure and ownership semantics are still not fully aligned.",
            "Refine the strict tenure/ownership logic first, then reassess whether any supporting data gaps remain material.",
        ),
        "thlb_parent_007_old_growth_management_areas": (
            "model_endogenous",
            "strict_logic_overcut",
            "The strict lane is likely treating OGMA area too broadly relative to the reviewed TSA29 interpretation.",
            "Tighten the OGMA logic before looking for new data; this looks like an over-selection problem.",
        ),
        "thlb_parent_008_wildlife_habitat_areas": (
            "model_endogenous",
            "strict_logic_overcut",
            "The strict lane is selecting far more wildlife-area land than either the reviewed lane or the TSR benchmark supports.",
            "Audit the strict no-harvest selection logic and keep conditional/modified zones out unless the TSR clearly says otherwise.",
        ),
        "thlb_parent_009_critical_habitat_for_fish": (
            "model_endogenous",
            "strict_logic_overcut",
            "The strict lane is applying a much broader legal fish-objective surface than the reviewed lane or TSR benchmark supports.",
            "Narrow the strict fish-habitat interpretation; this is one of the clearest strict overcut seams in the whole ladder.",
        ),
        "thlb_parent_010_lakeshore_management": (
            "data_exogenous",
            "missing_or_blocked_data",
            "This step depends on a trusted Class A lake discriminator that the current public-input lane still does not have.",
            "Keep the reviewed skip or a tiny aspatial fallback unless a trustworthy lake-class source appears.",
        ),
        "thlb_parent_011_community_areas_of_special_concern": (
            "model_endogenous",
            "reviewed_bridge_semantics",
            "The strict literal source choice is not reproducing the reviewed meaning of this step at all.",
            "Fix the strict semantics/source interpretation instead of treating this as a pure missing-data problem.",
        ),
        "thlb_parent_012_proven_aboriginal_rights_areas": (
            "data_exogenous",
            "missing_or_blocked_data",
            "The strict lane still lacks a trustworthy public boundary source for this step.",
            "Keep this as a reviewed skip or documented fallback until a real source is available.",
        ),
        "thlb_parent_013_areas_considered_inoperable": (
            "reviewed_bridge_choice",
            "accepted_reviewed_override",
            "The reviewed lane uses accepted derived-attribute and calibrated bridge logic here that the strict checkpoint1 lane does not share.",
            "Keep the accepted reviewed bridge unless you explicitly decide to port its late-stage derived attributes into strict semantics.",
        ),
        "thlb_parent_014_sites_with_low_growing_timber_potential": (
            "mixed",
            "missing_late_stage_semantics",
            "The strict lane is blocked because this is late-stage curve-ready logic, not because the universe of land is inherently unknowable.",
            "Bridge or port the late-stage curve logic explicitly; do not mislabel this as a simple raw-data problem.",
        ),
        "thlb_parent_015_non_merchantable_timber_profiles": (
            "model_endogenous",
            "missing_late_stage_semantics",
            "The strict lane is missing the later broadleaf-leading yield logic that the reviewed lane applies here.",
            "Port the reviewed late-stage logic or keep this as an explicit bridge/fallback step.",
        ),
        "thlb_parent_016_recreation_features": (
            "mixed",
            "partial_strict_logic",
            "The strict lane only captures part of the reviewed recreation exclusion logic.",
            "Low-priority cleanup: improve strict logic if this step later matters to the remaining gap.",
        ),
        "thlb_parent_017_growth_and_yield_permanent_sample_plots": (
            "data_exogenous",
            "weak_public_coverage",
            "The strict lane undercuts here, but the public PSP geometry signal is weak and the absolute area is small.",
            "Treat this as a lower-priority data-coverage seam unless a better PSP source becomes available.",
        ),
        "thlb_parent_018_riparian_areas": (
            "mixed",
            "missing_or_blocked_data",
            "The strict lane is still missing some of the lake-class and special-case riparian inputs that the reviewed bridge used.",
            "Improve source coverage first, then revisit the strict riparian logic if the gap remains large.",
        ),
        "thlb_parent_019_buffered_trails": (
            "reviewed_bridge_choice",
            "accepted_reviewed_override",
            "The reviewed lane uses an accepted equivalent-corridor bridge here, while the strict lane currently does not reproduce that bridge.",
            "Keep the accepted bridge unless you explicitly decide to formalize the same equivalent-corridor logic in strict mode.",
        ),
        "thlb_parent_020_wildlife_tree_retention_areas": (
            "reviewed_bridge_choice",
            "accepted_aspatial_bridge",
            "This step is intentionally being modeled as an aspatial future-WTRA bridge rather than an exact mapped exclusion.",
            "Keep the documented aspatial fallback unless a better exact contract is deliberately adopted later.",
        ),
        "thlb_parent_021_cultural_heritage_and_archaeological_resources": (
            "reviewed_bridge_choice",
            "accepted_aspatial_bridge",
            "This step is intentionally being modeled as an aspatial THLB bridge rather than a single exact spatial layer.",
            "Keep the documented aspatial fallback unless a defensible exact spatial contract is introduced later.",
        ),
        "thlb_parent_023_future_roads": (
            "reviewed_bridge_choice",
            "accepted_skip_or_noop",
            "The accepted TSA29 closeout keeps this as an explicit 0 ha no-op tail step after step 21.",
            "Leave it alone unless you intentionally reopen the reviewed closeout decision.",
        ),
    }
    return overrides.get(parent_step_id)


def _classify_thlb_reconstruction_gap_entry(
    *,
    parent_step: dict[str, Any],
    benchmark_marginal_area_ha: float | None,
    reconstructed_removed_area_ha: float | None,
    reviewed_removed_area_ha: float | None,
    reconstructed_status: str,
    reconstructed_spatial_modes: Sequence[str],
) -> tuple[str, str]:
    if str(parent_step.get("parent_kind", "")).strip() == "milestone":
        return (
            "not_comparable",
            "This is a backbone/reference row, so there is no direct removal comparison.",
        )
    if "blocked" in reconstructed_status or "missing_source" in reconstructed_status:
        return (
            "blocked_or_missing_source",
            "The strict lane is still blocked here, so the area gap is not yet a clean "
            "modeling comparison.",
        )
    if "aspatial_fallback" in reconstructed_spatial_modes:
        return (
            "aspatial_bridge_difference",
            "The strict lane used a documented aspatial fallback here instead of exact "
            "spatial reproduction.",
        )
    if _parent_step_has_reviewed_override(parent_step):
        return (
            "manual_or_reviewed_override",
            "The reviewed lane is carrying an accepted override, skip, calibration, or "
            "no-op choice that the strict lane does not automatically share.",
        )
    threshold = _comparison_difference_threshold(
        benchmark_marginal_area_ha,
        reconstructed_removed_area_ha,
        reviewed_removed_area_ha,
    )
    strict_value = (
        reconstructed_removed_area_ha
        if reconstructed_removed_area_ha is not None
        else 0.0
    )
    if reviewed_removed_area_ha is None and strict_value <= threshold:
        return (
            "not_comparable",
            "No reviewed removal was recorded for this parent step, so there is not yet a "
            "stable strict-vs-reviewed area comparison.",
        )
    if reviewed_removed_area_ha is None and strict_value > threshold:
        return (
            "strict_overcut_candidate",
            "The strict lane removed material area here while the reviewed lane did not "
            "record a comparable removal.",
        )
    reviewed_value = reviewed_removed_area_ha or 0.0
    delta = strict_value - reviewed_value
    if abs(delta) <= threshold:
        return (
            "close_match",
            "The strict and reviewed lanes are close enough here that this parent step "
            "does not look like a major driver of the remaining gap.",
        )
    if reviewed_value > threshold and strict_value <= threshold:
        return (
            "reviewed_bridge_only",
            "The reviewed lane removed material area here, but the strict lane did not "
            "produce a comparable removal.",
        )
    if delta > 0.0:
        return (
            "strict_overcut_candidate",
            "The strict lane is removing materially more area than the reviewed lane here.",
        )
    return (
        "strict_undercut_candidate",
        "The strict lane is removing materially less area than the reviewed lane here.",
    )


def _build_tsr_thlb_reconstruction_comparison_payload(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    reconstructed_audit_payload: dict[str, Any],
    recipe_relative_path: str,
    reviewed_status_relative_path: str,
    reconstructed_audit_relative_path: str,
    comparison_markdown_relative_path: str,
    comparison_json_relative_path: str,
) -> dict[str, Any]:
    reconstructed_parent_map = _aggregate_reconstructed_parent_step_results(
        reconstructed_audit_payload
    )
    reconstructed_baseline_signal = str(
        reconstructed_audit_payload.get("baseline_signal", "")
    ).strip()
    reconstructed_baseline_managed_area_ha = _normalize_float_or_none(
        reconstructed_audit_payload.get("baseline_managed_area_ha")
    )
    reconstructed_cumulative_area_by_parent_id: dict[str, float] = {}
    if reconstructed_baseline_managed_area_ha is not None:
        running_cumulative_area_ha = float(reconstructed_baseline_managed_area_ha)
        for parent_step in sorted(
            recipe.parent_steps, key=lambda item: int(item.get("row_order", 0) or 0)
        ):
            parent_step_id = str(parent_step.get("parent_step_id", "")).strip()
            if not parent_step_id:
                continue
            if str(parent_step.get("parent_kind", "")).strip() == "milestone":
                reconstructed_cumulative_area_by_parent_id[parent_step_id] = (
                    running_cumulative_area_ha
                )
                continue
            removed_area_ha = _normalize_float_or_none(
                reconstructed_parent_map.get(parent_step_id, {}).get(
                    "reconstructed_removed_area_ha"
                )
            )
            if removed_area_ha is not None:
                running_cumulative_area_ha -= float(removed_area_ha)
            reconstructed_cumulative_area_by_parent_id[parent_step_id] = (
                running_cumulative_area_ha
            )
    milestones, parent_stage_groups = _parent_steps_grouped_by_stage(recipe)
    entries: list[dict[str, Any]] = []
    for parent_step in recipe.parent_steps:
        item = dict(parent_step)
        parent_step_id = str(item.get("parent_step_id", "")).strip()
        reconstructed_entry = reconstructed_parent_map.get(parent_step_id, {})
        benchmark_marginal_area_ha = _normalize_float_or_none(
            item.get("benchmark_marginal_area_ha")
        )
        benchmark_cumulative_area_ha = _normalize_float_or_none(
            item.get("benchmark_cumulative_area_ha")
        )
        reviewed_removed_area_ha = _normalize_float_or_none(
            item.get("last_removed_area_ha")
        )
        reconstructed_removed_area_ha = _normalize_float_or_none(
            reconstructed_entry.get("reconstructed_removed_area_ha")
        )
        reviewed_status = str(
            item.get("last_notebook_run_status", "")
        ).strip() or _infer_thlb_parent_step_ratchet_state(item)
        reconstructed_status = str(
            reconstructed_entry.get("reconstructed_status", "not_executed")
        ).strip()
        reconstructed_spatial_modes = tuple(
            str(value).strip()
            for value in reconstructed_entry.get("spatial_modes", ())
            if str(value).strip()
        )
        comparison_bucket, plain_language_reason = (
            _classify_thlb_reconstruction_gap_entry(
                parent_step=item,
                benchmark_marginal_area_ha=benchmark_marginal_area_ha,
                reconstructed_removed_area_ha=reconstructed_removed_area_ha,
                reviewed_removed_area_ha=reviewed_removed_area_ha,
                reconstructed_status=reconstructed_status,
                reconstructed_spatial_modes=reconstructed_spatial_modes,
            )
        )
        tsr_fit_class, tsr_fit_interpretation = _classify_thlb_reconstruction_tsr_fit(
            parent_step=item,
            benchmark_marginal_area_ha=benchmark_marginal_area_ha,
            reconstructed_removed_area_ha=reconstructed_removed_area_ha,
            reconstructed_status=reconstructed_status,
        )
        (
            problem_ownership,
            difference_nature,
            engineering_interpretation,
            recommended_next_move,
        ) = _default_reconstruction_gap_interpretation(
            bucket=comparison_bucket,
            parent_step=item,
        )
        override_interpretation = _tsa29_reconstruction_gap_interpretation_override(
            recipe=recipe,
            parent_step=item,
        )
        if override_interpretation is not None:
            (
                problem_ownership,
                difference_nature,
                engineering_interpretation,
                recommended_next_move,
            ) = override_interpretation
        strict_vs_tsr_delta_ha = (
            ((reconstructed_removed_area_ha or 0.0) - benchmark_marginal_area_ha)
            if benchmark_marginal_area_ha is not None
            else None
        )
        reviewed_vs_tsr_delta_ha = (
            ((reviewed_removed_area_ha or 0.0) - benchmark_marginal_area_ha)
            if benchmark_marginal_area_ha is not None
            and reviewed_removed_area_ha is not None
            else None
        )
        strict_vs_reviewed_delta_ha = (
            (reconstructed_removed_area_ha or 0.0) - reviewed_removed_area_ha
            if reviewed_removed_area_ha is not None
            and reconstructed_removed_area_ha is not None
            else None
        )
        reconstructed_cumulative_area_ha = _normalize_float_or_none(
            reconstructed_cumulative_area_by_parent_id.get(parent_step_id)
        )
        strict_vs_tsr_cumulative_delta_ha = (
            reconstructed_cumulative_area_ha - benchmark_cumulative_area_ha
            if reconstructed_cumulative_area_ha is not None
            and benchmark_cumulative_area_ha is not None
            else None
        )
        reviewed_difference_role = comparison_bucket
        practical_meaning = _build_tsr_fit_practical_meaning(
            tsr_fit_class=tsr_fit_class,
            reviewed_difference_role=reviewed_difference_role,
            strict_vs_reviewed_delta_ha=strict_vs_reviewed_delta_ha,
            problem_ownership=problem_ownership,
        )
        if (
            str(item.get("parent_kind", "")).strip() == "milestone"
            and strict_vs_tsr_cumulative_delta_ha is not None
        ):
            if abs(strict_vs_tsr_cumulative_delta_ha) <= max(
                25000.0, abs(benchmark_cumulative_area_ha or 0.0) * 0.01
            ):
                practical_meaning = (
                    "This is a milestone row. The useful question here is whether the "
                    "current strict cumulative area checkpoint is close enough to the "
                    "TSR cumulative target, and it is."
                )
            else:
                direction = (
                    "below"
                    if strict_vs_tsr_cumulative_delta_ha < 0.0
                    else "above"
                )
                practical_meaning = (
                    "This is a milestone row. The current strict cumulative area "
                    f"checkpoint is materially {direction} the TSR cumulative target, "
                    "so inspect the prior deduction steps rather than trying to fix the milestone itself."
                )
            recommended_next_move = (
                "Reference row only; inspect cumulative strict area carried into this checkpoint and fix prior deduction steps if needed."
            )
        adjudication_action = _comparison_queue_action(
            tsr_fit_class=tsr_fit_class,
            problem_ownership=problem_ownership,
            difference_nature=difference_nature,
        )
        supporting_notes: list[str] = []
        if reconstructed_spatial_modes:
            supporting_notes.append(
                "strict spatial modes: "
                + ", ".join(f"`{value}`" for value in reconstructed_spatial_modes)
            )
        reconstructed_step_ids = tuple(
            str(value).strip()
            for value in reconstructed_entry.get("step_ids", ())
            if str(value).strip()
        )
        if reconstructed_step_ids:
            supporting_notes.append(
                "strict compiled steps: "
                + ", ".join(f"`{value}`" for value in reconstructed_step_ids)
            )
        approval_scope = str(item.get("approval_scope", "")).strip()
        if approval_scope:
            supporting_notes.append(f"reviewed approval scope: `{approval_scope}`")
        ratchet_state = _infer_thlb_parent_step_ratchet_state(item)
        supporting_notes.append(f"reviewed ratchet state: `{ratchet_state}`")
        for raw_note in reconstructed_entry.get("notes", ()):
            note_text = str(raw_note).strip()
            if note_text:
                supporting_notes.append(f"strict note: {note_text}")
        entries.append(
            {
                "parent_step_id": parent_step_id,
                "parent_label": str(item.get("parent_label", "")).strip(),
                "row_order": int(item.get("row_order", 0) or 0),
                "parent_kind": str(item.get("parent_kind", "")).strip(),
                "land_base_stage": str(item.get("land_base_stage", "")).strip(),
                "stage_label": str(
                    item.get(
                        "stage_label",
                        _stage_header_text(str(item.get("land_base_stage", ""))),
                    )
                ).strip(),
                "benchmark_marginal_area_ha": benchmark_marginal_area_ha,
                "benchmark_cumulative_area_ha": benchmark_cumulative_area_ha,
                "reconstructed_removed_area_ha": reconstructed_removed_area_ha,
                "reviewed_removed_area_ha": reviewed_removed_area_ha,
                "strict_vs_tsr_delta_ha": strict_vs_tsr_delta_ha,
                "reconstructed_cumulative_area_ha": reconstructed_cumulative_area_ha,
                "strict_vs_tsr_cumulative_delta_ha": strict_vs_tsr_cumulative_delta_ha,
                "reviewed_vs_tsr_delta_ha": reviewed_vs_tsr_delta_ha,
                "strict_vs_reviewed_delta_ha": strict_vs_reviewed_delta_ha,
                "reconstructed_status": reconstructed_status,
                "reviewed_status": reviewed_status,
                "tsr_fit_class": tsr_fit_class,
                "tsr_fit_interpretation": tsr_fit_interpretation,
                "reviewed_difference_role": reviewed_difference_role,
                "comparison_bucket": comparison_bucket,
                "problem_ownership": problem_ownership,
                "difference_nature": difference_nature,
                "plain_language_reason": plain_language_reason,
                "practical_meaning": practical_meaning,
                "engineering_interpretation": engineering_interpretation,
                "recommended_next_move": recommended_next_move,
                "adjudication_action": adjudication_action,
                "adjudication_action_summary": _comparison_queue_action_summary(
                    adjudication_action
                ),
                "actionability": _comparison_actionability(
                    comparison_bucket, adjudication_action
                ),
                "supporting_notes": supporting_notes,
            }
        )
    bucket_counts = Counter(
        str(item.get("comparison_bucket", "")).strip()
        for item in entries
        if str(item.get("comparison_bucket", "")).strip()
    )
    problem_ownership_counts = Counter(
        str(item.get("problem_ownership", "")).strip()
        for item in entries
        if str(item.get("problem_ownership", "")).strip()
    )
    tsr_fit_counts = Counter(
        str(item.get("tsr_fit_class", "")).strip()
        for item in entries
        if str(item.get("tsr_fit_class", "")).strip()
    )
    adjudication_action_counts = Counter(
        str(item.get("adjudication_action", "")).strip()
        for item in entries
        if str(item.get("adjudication_action", "")).strip()
    )
    reviewed_final_managed_area_ha = _resolve_reviewed_thlb_remaining_area_ha(recipe)
    reconstructed_final_managed_area_ha = _normalize_float_or_none(
        reconstructed_audit_payload.get("final_managed_area_ha")
    )
    tsr_reported_thlb_area_ha = _normalize_float_or_none(
        reconstructed_audit_payload.get("tsr_reported_thlb_area_ha")
    )

    def _strict_vs_reviewed_gap_delta(entry: dict[str, Any]) -> float:
        reviewed_reference = _normalize_float_or_none(
            entry.get("reviewed_removed_area_ha")
        )
        if reviewed_reference is None:
            reviewed_reference = _normalize_float_or_none(
                entry.get("benchmark_marginal_area_ha")
            )
        reconstructed_value = (
            _normalize_float_or_none(entry.get("reconstructed_removed_area_ha")) or 0.0
        )
        return reconstructed_value - (reviewed_reference or 0.0)

    def _strict_vs_tsr_gap_delta(entry: dict[str, Any]) -> float:
        benchmark_reference = _normalize_float_or_none(
            entry.get("benchmark_marginal_area_ha")
        )
        if benchmark_reference is None:
            return 0.0
        reconstructed_value = (
            _normalize_float_or_none(entry.get("reconstructed_removed_area_ha")) or 0.0
        )
        return reconstructed_value - benchmark_reference

    top_strict_vs_tsr_parent_steps = sorted(
        [
            item
            for item in entries
            if str(item.get("parent_kind", "")).strip() != "milestone"
        ],
        key=lambda item: abs(_strict_vs_tsr_gap_delta(item)),
        reverse=True,
    )[:5]
    top_strict_vs_reviewed_context_steps = sorted(
        [
            item
            for item in entries
            if str(item.get("parent_kind", "")).strip() != "milestone"
        ],
        key=lambda item: abs(_strict_vs_reviewed_gap_delta(item)),
        reverse=True,
    )[:5]
    stepwise_adjudication_queue = [
        {
            "row_order": int(item.get("row_order", 0) or 0),
            "parent_step_id": str(item.get("parent_step_id", "")).strip(),
            "parent_label": str(item.get("parent_label", "")).strip(),
            "tsr_fit_class": str(item.get("tsr_fit_class", "")).strip(),
            "problem_ownership": str(item.get("problem_ownership", "")).strip(),
            "difference_nature": str(item.get("difference_nature", "")).strip(),
            "adjudication_action": str(item.get("adjudication_action", "")).strip(),
            "adjudication_action_summary": str(
                item.get("adjudication_action_summary", "")
            ).strip(),
            "recommended_next_move": str(item.get("recommended_next_move", "")).strip(),
        }
        for item in sorted(
            [
                entry
                for entry in entries
                if str(entry.get("parent_kind", "")).strip() != "milestone"
            ],
            key=lambda value: int(value.get("row_order", 0) or 0),
        )
    ]
    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "artifact_kind": "thlb_reconstruction_comparison",
        "tsa": recipe.tsa.to_dict(),
        "recipe_path": recipe_relative_path,
        "reviewed_status_path": reviewed_status_relative_path,
        "reconstructed_audit_path": reconstructed_audit_relative_path,
        "reconstructed_baseline_signal": reconstructed_baseline_signal,
        "comparison_markdown_path": comparison_markdown_relative_path,
        "comparison_json_path": comparison_json_relative_path,
        "reconstructed_final_managed_area_ha": reconstructed_final_managed_area_ha,
        "reviewed_final_managed_area_ha": reviewed_final_managed_area_ha,
        "tsr_reported_thlb_area_ha": tsr_reported_thlb_area_ha,
        "strict_vs_tsr_delta_ha": (
            reconstructed_final_managed_area_ha - tsr_reported_thlb_area_ha
            if reconstructed_final_managed_area_ha is not None
            and tsr_reported_thlb_area_ha is not None
            else None
        ),
        "reviewed_vs_tsr_delta_ha": (
            reviewed_final_managed_area_ha - tsr_reported_thlb_area_ha
            if reviewed_final_managed_area_ha is not None
            and tsr_reported_thlb_area_ha is not None
            else None
        ),
        "strict_vs_reviewed_delta_ha": (
            reconstructed_final_managed_area_ha - reviewed_final_managed_area_ha
            if reconstructed_final_managed_area_ha is not None
            and reviewed_final_managed_area_ha is not None
            else None
        ),
        "comparison_bucket_counts": dict(sorted(bucket_counts.items())),
        "problem_ownership_counts": dict(sorted(problem_ownership_counts.items())),
        "tsr_fit_counts": dict(sorted(tsr_fit_counts.items())),
        "adjudication_action_counts": dict(sorted(adjudication_action_counts.items())),
        "top_strict_vs_tsr_parent_steps": [
            {
                "parent_step_id": str(item.get("parent_step_id", "")).strip(),
                "parent_label": str(item.get("parent_label", "")).strip(),
                "tsr_fit_class": str(item.get("tsr_fit_class", "")).strip(),
                "strict_minus_tsr_removed_area_ha": _strict_vs_tsr_gap_delta(item),
            }
            for item in top_strict_vs_tsr_parent_steps
        ],
        "top_strict_vs_reviewed_context_steps": [
            {
                "parent_step_id": str(item.get("parent_step_id", "")).strip(),
                "parent_label": str(item.get("parent_label", "")).strip(),
                "reviewed_difference_role": str(
                    item.get("reviewed_difference_role", "")
                ).strip(),
                "strict_minus_reviewed_removed_area_ha": _strict_vs_reviewed_gap_delta(
                    item
                ),
            }
            for item in top_strict_vs_reviewed_context_steps
        ],
        "milestone_count": len(milestones),
        "parent_step_count": len(entries),
        "stage_counts": {
            stage: len(parent_stage_groups.get(stage, ()))
            for stage in _THLB_STAGE_ORDER
        },
        "stepwise_adjudication_queue": stepwise_adjudication_queue,
        "entries": entries,
    }


def _build_tsr_thlb_reconstruction_comparison_markdown(
    *,
    recipe: TsrThlbNetdownRecipeRecord,
    comparison_payload: dict[str, Any],
) -> str:
    entries = [
        dict(item)
        for item in comparison_payload.get("entries", ())
        if isinstance(item, dict)
    ]
    stage_groups: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _THLB_STAGE_ORDER
    }
    milestone_entries = [
        item
        for item in entries
        if str(item.get("parent_kind", "")).strip() == "milestone"
    ]
    for item in entries:
        if str(item.get("parent_kind", "")).strip() == "milestone":
            continue
        stage = str(item.get("land_base_stage", "context")).strip()
        if stage not in stage_groups:
            stage = "context"
        stage_groups[stage].append(item)
    lines = [
        (
            f"# THLB Reconstruction Comparison: TSA {recipe.tsa.tsa_code} "
            f"({recipe.tsa.tsa_name})"
        ),
        "",
        f"- Generated UTC: `{comparison_payload.get('generated_utc', '')}`",
        f"- THLB recipe path: `{comparison_payload.get('recipe_path', '')}`",
        "- Reviewed bridge status report: "
        f"`{comparison_payload.get('reviewed_status_path', '')}`",
        "- Reconstructed audit JSON: "
        f"`{comparison_payload.get('reconstructed_audit_path', '')}`",
        "- Reconstructed baseline signal: "
        f"`{comparison_payload.get('reconstructed_baseline_signal', '')}`",
        "",
        "## Summary",
        "",
    ]
    reconstructed_final = _normalize_float_or_none(
        comparison_payload.get("reconstructed_final_managed_area_ha")
    )
    reviewed_final = _normalize_float_or_none(
        comparison_payload.get("reviewed_final_managed_area_ha")
    )
    tsr_final = _normalize_float_or_none(
        comparison_payload.get("tsr_reported_thlb_area_ha")
    )
    if reconstructed_final is not None:
        lines.append(f"- Strict reconstructed THLB: `{reconstructed_final:.3f} ha`")
    if tsr_final is not None:
        lines.append(f"- TSR reported THLB: `{tsr_final:.3f} ha`")
    for label, key in (("Strict vs TSR delta", "strict_vs_tsr_delta_ha"),):
        value = _normalize_float_or_none(comparison_payload.get(key))
        if value is not None:
            lines.append(f"- {label}: `{value:.3f} ha`")
    lines.extend(["", "## Reviewed Bridge Context", ""])
    if reviewed_final is not None:
        lines.append(f"- Reviewed bridge THLB: `{reviewed_final:.3f} ha`")
    for label, key in (
        ("Reviewed vs TSR delta", "reviewed_vs_tsr_delta_ha"),
        ("Strict vs reviewed delta", "strict_vs_reviewed_delta_ha"),
    ):
        value = _normalize_float_or_none(comparison_payload.get(key))
        if value is not None:
            lines.append(f"- {label}: `{value:.3f} ha`")
    lines.extend(
        [
            "",
            "## Why Reviewed Was Accepted Anyway",
            "",
            "- The reviewed lane was accepted because its cumulative THLB was close enough to the TSR benchmark for practical exploratory modeling use.",
            "- Reviewed per-step behavior is therefore useful context, not automatic gold-standard truth for strict reconstruction.",
            "- A parent step is a top-priority strict-lane repair when strict is materially bad against TSR, not merely because strict differs from reviewed.",
            "- The current strict lane now starts from raw checkpoint1 geometry rather than an AFLB-style prefiltered subset, so early `GLB -> AFLB` rows are intended to be read as real stepwise deductions.",
            "",
            "## Strict-vs-TSR Fit Counts",
            "",
        ]
    )
    tsr_fit_counts = comparison_payload.get("tsr_fit_counts", {})
    if isinstance(tsr_fit_counts, dict):
        for fit_name, count in sorted(tsr_fit_counts.items()):
            lines.append(f"- `{fit_name}`: `{count}`")
    lines.extend(["", "## Reviewed-Difference Context Counts", ""])
    bucket_counts = comparison_payload.get("comparison_bucket_counts", {})
    if isinstance(bucket_counts, dict):
        for bucket_name, count in sorted(bucket_counts.items()):
            lines.append(f"- `{bucket_name}`: `{count}`")
    lines.extend(["", "## Problem Ownership Counts", ""])
    problem_ownership_counts = comparison_payload.get("problem_ownership_counts", {})
    if isinstance(problem_ownership_counts, dict):
        for ownership_name, count in sorted(problem_ownership_counts.items()):
            lines.append(f"- `{ownership_name}`: `{count}`")
    lines.extend(["", "## Stepwise Adjudication Queue", ""])
    stepwise_adjudication_queue = comparison_payload.get(
        "stepwise_adjudication_queue", ()
    )
    if isinstance(stepwise_adjudication_queue, list) and stepwise_adjudication_queue:
        for item in stepwise_adjudication_queue:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- "
                f"{int(item.get('row_order', 0) or 0)}. "
                f"`{item.get('parent_step_id', '')}` | "
                f"{item.get('parent_label', '')} | "
                f"action=`{item.get('adjudication_action', '')}` | "
                f"tsr-fit=`{item.get('tsr_fit_class', '')}` | "
                f"ownership=`{item.get('problem_ownership', '')}`"
            )
    else:
        lines.append("- No adjudication queue entries were available.")
    lines.extend(["", "## Top 5 Strict-vs-TSR Contributors", ""])
    top_strict_vs_tsr_parent_steps = comparison_payload.get(
        "top_strict_vs_tsr_parent_steps", ()
    )
    if (
        isinstance(top_strict_vs_tsr_parent_steps, list)
        and top_strict_vs_tsr_parent_steps
    ):
        for item in top_strict_vs_tsr_parent_steps:
            if not isinstance(item, dict):
                continue
            delta = _normalize_float_or_none(
                item.get("strict_minus_tsr_removed_area_ha")
            )
            delta_text = f"{delta:.3f} ha" if delta is not None else "n/a"
            lines.append(
                "- "
                f"`{item.get('parent_step_id', '')}` | "
                f"{item.get('parent_label', '')} | "
                f"tsr-fit=`{item.get('tsr_fit_class', '')}` | "
                f"strict-TSR marginal delta=`{delta_text}`"
            )
    else:
        lines.append("- No strict-vs-TSR contributor list was available.")
    lines.extend(["", "## Top 5 Strict-vs-Reviewed Context Differences", ""])
    top_strict_vs_reviewed_context_steps = comparison_payload.get(
        "top_strict_vs_reviewed_context_steps", ()
    )
    if (
        isinstance(top_strict_vs_reviewed_context_steps, list)
        and top_strict_vs_reviewed_context_steps
    ):
        for item in top_strict_vs_reviewed_context_steps:
            if not isinstance(item, dict):
                continue
            delta = _normalize_float_or_none(
                item.get("strict_minus_reviewed_removed_area_ha")
            )
            delta_text = f"{delta:.3f} ha" if delta is not None else "n/a"
            lines.append(
                "- "
                f"`{item.get('parent_step_id', '')}` | "
                f"{item.get('parent_label', '')} | "
                f"reviewed-role=`{item.get('reviewed_difference_role', '')}` | "
                f"strict-reviewed removed-area delta=`{delta_text}`"
            )
    else:
        lines.append("- No strict-vs-reviewed context list was available.")
    lines.extend(
        [
            "",
            "## Plain-Language Read",
            "",
            "- This report does not change THLB logic. It explains how the strict reconstructed lane fits against the TSR benchmark and uses the reviewed lane as supporting context.",
            "- The governing question is whether strict is close enough to TSR, not whether strict matches reviewed step-for-step.",
            "- Reviewed differences still matter, but mainly because they explain accepted bridges, skips, calibrations, or semantic differences that the strict lane does not automatically share.",
            "- For the current TSA29 adjudication pass, this report is an active repair ledger: once a parent step is understood well enough to choose an actionable next move, land that change before moving to the next step.",
            "- Only leave a step as analysis-only when the chosen action is explicitly to defer, keep a reviewed bridge for now, or wait on missing data/source improvements.",
        ]
    )
    if milestone_entries:
        lines.extend(["", "## Backbone Milestones", ""])
        for item in milestone_entries:
            benchmark_cumulative = _normalize_float_or_none(
                item.get("benchmark_cumulative_area_ha")
            )
            benchmark_text = (
                f"{benchmark_cumulative:.3f} ha"
                if benchmark_cumulative is not None
                else "not parsed"
            )
            reconstructed_cumulative = _normalize_float_or_none(
                item.get("reconstructed_cumulative_area_ha")
            )
            reconstructed_text = (
                f"{reconstructed_cumulative:.3f} ha"
                if reconstructed_cumulative is not None
                else "not recorded"
            )
            cumulative_delta = _normalize_float_or_none(
                item.get("strict_vs_tsr_cumulative_delta_ha")
            )
            cumulative_delta_text = (
                f"{cumulative_delta:.3f} ha"
                if cumulative_delta is not None
                else "n/a"
            )
            lines.append(
                "- "
                f"`{item.get('parent_step_id', '')}` | "
                f"{item.get('parent_label', '')} | "
                f"benchmark cumulative area=`{benchmark_text}` | "
                f"strict cumulative area=`{reconstructed_text}` | "
                f"strict cumulative delta=`{cumulative_delta_text}`"
            )
    lines.extend(["", "## Parent-Step Comparison", ""])
    for stage in _THLB_STAGE_ORDER:
        stage_entries = stage_groups.get(stage, [])
        if not stage_entries:
            continue
        lines.append(f"### {_stage_header_text(stage)}")
        lines.append("")
        for item in sorted(
            stage_entries, key=lambda value: int(value.get("row_order", 0) or 0)
        ):
            lines.extend(
                [
                    f"#### {int(item.get('row_order', 0) or 0)}. {item.get('parent_label', '')}",
                    "",
                    f"- Parent step id: `{item.get('parent_step_id', '')}`",
                    f"- Strict TSR fit: `{item.get('tsr_fit_class', '')}`",
                    f"- Reviewed difference role: `{item.get('reviewed_difference_role', '')}`",
                    f"- Problem ownership: `{item.get('problem_ownership', '')}`",
                    f"- Difference nature: `{item.get('difference_nature', '')}`",
                    f"- Reconstructed status: `{item.get('reconstructed_status', '')}`",
                    f"- Reviewed status: `{item.get('reviewed_status', '')}`",
                ]
            )
            benchmark_marginal = _normalize_float_or_none(
                item.get("benchmark_marginal_area_ha")
            )
            if benchmark_marginal is not None:
                lines.append(
                    f"- TSR benchmark marginal deduction: `{benchmark_marginal:.3f} ha`"
                )
            benchmark_cumulative = _normalize_float_or_none(
                item.get("benchmark_cumulative_area_ha")
            )
            if benchmark_cumulative is not None:
                lines.append(
                    f"- TSR benchmark cumulative area: `{benchmark_cumulative:.3f} ha`"
                )
            reconstructed_cumulative = _normalize_float_or_none(
                item.get("reconstructed_cumulative_area_ha")
            )
            if reconstructed_cumulative is not None:
                lines.append(
                    "- Strict reconstructed cumulative area at this checkpoint: "
                    f"`{reconstructed_cumulative:.3f} ha`"
                )
            strict_vs_tsr_cumulative_delta = _normalize_float_or_none(
                item.get("strict_vs_tsr_cumulative_delta_ha")
            )
            if strict_vs_tsr_cumulative_delta is not None:
                lines.append(
                    "- Strict cumulative vs TSR cumulative delta: "
                    f"`{strict_vs_tsr_cumulative_delta:.3f} ha`"
                )
            reconstructed_removed = _normalize_float_or_none(
                item.get("reconstructed_removed_area_ha")
            )
            lines.append(
                "- Strict reconstructed removed area: "
                + (
                    f"`{reconstructed_removed:.3f} ha`"
                    if reconstructed_removed is not None
                    else "`not recorded`"
                )
            )
            reviewed_removed = _normalize_float_or_none(
                item.get("reviewed_removed_area_ha")
            )
            lines.append(
                "- Reviewed bridge removed area: "
                + (
                    f"`{reviewed_removed:.3f} ha`"
                    if reviewed_removed is not None
                    else "`not recorded`"
                )
            )
            strict_vs_tsr_delta = _normalize_float_or_none(
                item.get("strict_vs_tsr_delta_ha")
            )
            if strict_vs_tsr_delta is not None:
                lines.append(f"- Strict vs TSR delta: `{strict_vs_tsr_delta:.3f} ha`")
            reviewed_vs_tsr_delta = _normalize_float_or_none(
                item.get("reviewed_vs_tsr_delta_ha")
            )
            if reviewed_vs_tsr_delta is not None:
                lines.append(
                    f"- Reviewed vs TSR delta: `{reviewed_vs_tsr_delta:.3f} ha`"
                )
            strict_vs_reviewed_delta = _normalize_float_or_none(
                item.get("strict_vs_reviewed_delta_ha")
            )
            if strict_vs_reviewed_delta is not None:
                lines.append(
                    f"- Strict vs reviewed delta: `{strict_vs_reviewed_delta:.3f} ha`"
                )
            lines.append(f"- Strict vs TSR: {item.get('tsr_fit_interpretation', '')}")
            lines.append(
                f"- Reviewed difference: {item.get('plain_language_reason', '')}"
            )
            lines.append(f"- Practical meaning: {item.get('practical_meaning', '')}")
            lines.append(
                "- Engineering interpretation: "
                f"{item.get('engineering_interpretation', '')}"
            )
            lines.append(
                f"- Recommended next move: {item.get('recommended_next_move', '')}"
            )
            lines.append(
                "- Adjudication queue action: "
                f"`{item.get('adjudication_action', '')}`"
                f" ({item.get('adjudication_action_summary', '')})"
            )
            lines.append(f"- Actionability: {item.get('actionability', '')}")
            supporting_notes = [
                str(value).strip()
                for value in item.get("supporting_notes", ())
                if str(value).strip()
            ]
            if supporting_notes:
                lines.append("- Supporting notes:")
                for note in supporting_notes:
                    lines.append(f"  - {note}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_tsr_thlb_reconstruction_comparison(
    *,
    recipe_path: Path,
    reconstructed_audit_path: Path | None = None,
    reviewed_status_path: Path | None = None,
    output_markdown_path: Path | None = None,
    output_json_path: Path | None = None,
) -> TsrThlbReconstructionComparisonBuildResult:
    """Emit a TSA29-first THLB comparison report with strict-vs-TSR as primary."""

    (
        recipe,
        instance_root,
        _source_recipe,
        _source_entry_map,
        _override_entries,
    ) = _load_tsr_thlb_recipe_context(recipe_path)
    resolved_recipe_path = recipe_path.expanduser().resolve()
    resolved_reconstructed_audit_path = (
        reconstructed_audit_path.expanduser().resolve()
        if reconstructed_audit_path is not None
        else default_tsr_thlb_reconstructed_audit_path(instance_root=instance_root)
    )
    resolved_reviewed_status_path = (
        reviewed_status_path.expanduser().resolve()
        if reviewed_status_path is not None
        else default_tsr_thlb_netdown_status_report_path(instance_root=instance_root)
    )
    resolved_markdown_path = (
        output_markdown_path.expanduser().resolve()
        if output_markdown_path is not None
        else default_tsr_thlb_reconstruction_comparison_markdown_path(
            instance_root=instance_root
        )
    )
    resolved_json_path = (
        output_json_path.expanduser().resolve()
        if output_json_path is not None
        else default_tsr_thlb_reconstruction_comparison_json_path(
            instance_root=instance_root
        )
    )
    for candidate_path in (resolved_markdown_path, resolved_json_path):
        try:
            candidate_path.relative_to(instance_root)
        except ValueError as exc:
            raise TsrRecipeError(
                "THLB reconstruction comparison artifact paths must live under the instance root."
            ) from exc
    reconstructed_audit_payload = json.loads(
        resolved_reconstructed_audit_path.read_text(encoding="utf-8")
    )
    comparison_payload = _build_tsr_thlb_reconstruction_comparison_payload(
        recipe=recipe,
        reconstructed_audit_payload=reconstructed_audit_payload,
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        reviewed_status_relative_path=str(
            resolved_reviewed_status_path.relative_to(instance_root).as_posix()
        ),
        reconstructed_audit_relative_path=str(
            resolved_reconstructed_audit_path.relative_to(instance_root).as_posix()
        ),
        comparison_markdown_relative_path=str(
            resolved_markdown_path.relative_to(instance_root).as_posix()
        ),
        comparison_json_relative_path=str(
            resolved_json_path.relative_to(instance_root).as_posix()
        ),
    )
    markdown_text = _build_tsr_thlb_reconstruction_comparison_markdown(
        recipe=recipe,
        comparison_payload=comparison_payload,
    )
    resolved_json_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_json_path.write_text(
        json.dumps(comparison_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )
    resolved_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_markdown_path.write_text(markdown_text, encoding="utf-8")
    bucket_counts = Counter(
        str(item.get("comparison_bucket", "")).strip()
        for item in comparison_payload.get("entries", ())
        if isinstance(item, dict) and str(item.get("comparison_bucket", "")).strip()
    )
    return TsrThlbReconstructionComparisonBuildResult(
        recipe_path=resolved_recipe_path,
        markdown_path=resolved_markdown_path,
        json_path=resolved_json_path,
        tsa=recipe.tsa,
        parent_step_count=len(
            [
                item
                for item in comparison_payload.get("entries", ())
                if isinstance(item, dict)
            ]
        ),
        comparison_bucket_counts=dict(sorted(bucket_counts.items())),
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
    warmstart_markdown_path = default_tsr_thlb_warmstart_markdown_path(
        instance_root=instance_root
    )
    notebook = _build_tsr_thlb_workbench_notebook(
        recipe=recipe,
        recipe_relative_path=str(
            resolved_recipe_path.relative_to(instance_root).as_posix()
        ),
        status_report_relative_path=str(
            status_report_path.relative_to(instance_root).as_posix()
        ),
        warmstart_markdown_relative_path=(
            str(warmstart_markdown_path.relative_to(instance_root).as_posix())
            if warmstart_markdown_path.exists()
            else None
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


def _parse_bbox_payload(
    value: Any,
) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list | tuple) or len(value) != 4:
        return None
    try:
        return tuple(float(item) for item in value)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _bbox_width_height(
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    minx, miny, maxx, maxy = bbox
    return max(maxx - minx, 0.0), max(maxy - miny, 0.0)


def _bbox_area(
    bbox: tuple[float, float, float, float],
) -> float:
    width, height = _bbox_width_height(bbox)
    return width * height


def _evaluate_source_extent_mismatch(
    *,
    source_entry: dict[str, Any],
    artifact_bbox_epsg3005: tuple[float, float, float, float] | None,
    target_bbox_epsg3005: tuple[float, float, float, float] | None,
) -> str | None:
    if artifact_bbox_epsg3005 is None or target_bbox_epsg3005 is None:
        return None
    strategy = str(source_entry.get("acquisition_strategy", "")).strip()
    scope = str(source_entry.get("artifact_scope", "")).strip()
    if strategy not in {"wfs_fetch", "dwds_order"} and not scope:
        return None
    source_width, source_height = _bbox_width_height(artifact_bbox_epsg3005)
    target_width, target_height = _bbox_width_height(target_bbox_epsg3005)
    target_area = _bbox_area(target_bbox_epsg3005)
    if target_width <= 0.0 or target_height <= 0.0 or target_area <= 0.0:
        return None
    width_coverage = source_width / target_width
    height_coverage = source_height / target_height
    area_coverage = _bbox_area(artifact_bbox_epsg3005) / target_area
    if (
        width_coverage >= _EXTENT_COVERAGE_BLOCK_THRESHOLD
        or height_coverage >= _EXTENT_COVERAGE_BLOCK_THRESHOLD
        or area_coverage >= _EXTENT_AREA_BLOCK_THRESHOLD
    ):
        return None
    entry_id = str(source_entry.get("entry_id", "")).strip() or "<unknown>"
    scope_label = scope or "aoi-scoped/unknown"
    return (
        f"Source artifact `{entry_id}` appears clipped relative to the current checkpoint "
        f"extent (bbox coverage: width {width_coverage:.1%}, height {height_coverage:.1%}, "
        f"area {area_coverage:.1%}; scope `{scope_label}`). Do not reuse smoke/AOI-scoped "
        "overlays for full-TSA production runs."
    )


def _load_exclusion_geometries(
    *,
    instance_root: Path,
    linked_source_entry_ids: tuple[str, ...],
    source_entry_map: dict[str, dict[str, Any]],
    preserve_attributes: bool = False,
    allowed_geom_types: tuple[str, ...] = ("Polygon", "MultiPolygon"),
    bbox: tuple[float, float, float, float] | None = None,
) -> tuple[gpd.GeoDataFrame | None, list[str], list[str]]:
    frames: list[gpd.GeoDataFrame] = []
    missing_sources: list[str] = []
    extent_mismatch_notes: list[str] = []
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
        extent_mismatch_note = _evaluate_source_extent_mismatch(
            source_entry=source_entry,
            artifact_bbox_epsg3005=(
                float(layer.total_bounds[0]),
                float(layer.total_bounds[1]),
                float(layer.total_bounds[2]),
                float(layer.total_bounds[3]),
            ),
            target_bbox_epsg3005=bbox,
        )
        if extent_mismatch_note is not None:
            extent_mismatch_notes.append(extent_mismatch_note)
            continue
        frames.append(layer)
    if not frames:
        if extent_mismatch_notes:
            return None, missing_sources, extent_mismatch_notes
        if found_artifact and not missing_sources:
            empty_geometry = gpd.GeoDataFrame(
                geometry=gpd.GeoSeries([], crs=BC_ALBERS_EPSG),
                crs=BC_ALBERS_EPSG,
            )
            return empty_geometry, missing_sources, extent_mismatch_notes
        return None, missing_sources, extent_mismatch_notes
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
    return merged, missing_sources, extent_mismatch_notes


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


def _select_reconstructed_diagnostic_steps(
    steps: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    runnable_actions = {
        "use_land_base",
        "no_deduction",
        "exclude",
        "aspatial_reduction",
        "aspatial_area_reduction",
    }
    selected: list[dict[str, Any]] = []
    for step in steps:
        normalized_action = str(step.get("normalized_action", "")).strip()
        if normalized_action in runnable_actions:
            selected.append(dict(step))
    return tuple(selected)


def _execute_tsr_thlb_recipe_steps_reconstructed_lu(
    *,
    recipe_steps: Sequence[dict[str, Any]],
    checkpoint: gpd.GeoDataFrame,
    checkpoint_path: Path,
    instance_root: Path,
    source_entry_map: dict[str, dict[str, Any]],
    total_area_benchmark_ha: float | None = None,
) -> tuple[
    gpd.GeoDataFrame, list[dict[str, Any]], dict[str, int], list[dict[str, Any]]
]:
    outcome_counts: Counter[str] = Counter()
    applied_steps: list[dict[str, Any]] = []
    diagnostic_steps: list[dict[str, Any]] = []

    lu_frame, current_chunk_records, partition_profile = (
        _prepare_reconstructed_lu_chunk_records(
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
            instance_root=instance_root,
        )
    )
    runtime_root = default_tsr_thlb_reconstructed_lu_runtime_root(
        instance_root=instance_root
    )
    runtime_root.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_root = runtime_root / f"{checkpoint_path.stem}.{run_timestamp}"
    run_root.mkdir(parents=True, exist_ok=True)

    diagnostic_steps.append(
        {
            "step_id": "__lu_partition_init__",
            "label": "Landscape Unit partition initialization",
            "normalized_action": "lu_partition_init",
            **partition_profile,
            "lu_chunk_count": len(current_chunk_records),
            "total_seconds": float(sum(partition_profile.values())),
        }
    )

    for step in recipe_steps:
        step_start = perf_counter()
        step_profile: dict[str, Any] = {
            "step_id": str(step.get("step_id", "")).strip(),
            "label": str(step.get("label", "")).strip(),
            "normalized_action": str(step.get("normalized_action", "")).strip(),
            "source_load_seconds": 0.0,
            "candidate_query_seconds": 0.0,
            "overlay_seconds": 0.0,
            "write_seconds": 0.0,
            "merge_seconds": 0.0,
            "lu_chunk_count": 0,
            "intersecting_exclusion_feature_count": 0,
        }
        updated_step = dict(step)
        normalized_action = str(step.get("normalized_action", "")).strip()
        operation_type = _resolve_compiled_operation_type(step)
        page_number = int(step.get("page_number") or 0)
        step_dir = run_root / (
            f"{int(step.get('order_index') or 0):03d}_"
            f"{_normalize_step_slug(step_profile['step_id'])}"
        )
        step_dir.mkdir(parents=True, exist_ok=True)

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
            if operation_type == "select_attribute":
                filters = [
                    dict(item)
                    for item in step.get("checkpoint_attribute_filters", ())
                    if isinstance(item, dict)
                ]
                mode = str(step.get("checkpoint_attribute_mode", "any")).strip() or "any"
                overlay_started = perf_counter()
                (
                    current_chunk_records,
                    removed_area_ha,
                    affected_row_count,
                    touched_chunk_count,
                ) = _apply_reconstructed_lu_checkpoint_attribute_exclusion(
                    chunk_records=current_chunk_records,
                    runtime_step_root=step_dir,
                    filters=filters,
                    mode=mode,
                )
                step_profile["overlay_seconds"] = perf_counter() - overlay_started
                step_profile["write_seconds"] = float(step_profile["overlay_seconds"])
                step_profile["lu_chunk_count"] = int(touched_chunk_count)
                updated_step["affected_fragment_count"] = int(affected_row_count)
                updated_step["affected_area_ha"] = float(removed_area_ha)
                if affected_row_count > 0:
                    updated_step["run_status"] = "applied"
                    updated_step["spatial_application_mode"] = (
                        "checkpoint_attribute_exclusion"
                    )
                    updated_step["run_notes"] = [
                        "Applied checkpoint-attribute exclusion directly against LU chunk geometry without requiring fetched source polygons."
                    ]
                else:
                    updated_step["run_status"] = "applied_noop"
                    updated_step["run_notes"] = [
                        "No active LU-clipped fragment rows matched the checkpoint attribute filters."
                    ]
            else:
                source_load_start = perf_counter()
                (
                    exclusion_geometries,
                    missing_sources,
                    no_matching_features,
                    extent_mismatch_notes,
                ) = _load_compiled_logic_geometries(
                    instance_root=instance_root,
                    compiled_item=step,
                    source_entry_map=source_entry_map,
                    bbox=(
                        float(checkpoint.total_bounds[0]),
                        float(checkpoint.total_bounds[1]),
                        float(checkpoint.total_bounds[2]),
                        float(checkpoint.total_bounds[3]),
                    ),
                )
                step_profile["source_load_seconds"] = perf_counter() - source_load_start
                if exclusion_geometries is None:
                    if extent_mismatch_notes:
                        updated_step["run_status"] = "blocked_extent_mismatch"
                        updated_step["run_notes"] = extent_mismatch_notes
                    else:
                        updated_step["run_status"] = "blocked_missing_source"
                        updated_step["run_notes"] = [
                            "No fetched polygon artifact was available for the linked source entries."
                        ]
                        if missing_sources:
                            updated_step["missing_source_entry_ids"] = missing_sources
                elif no_matching_features:
                    updated_step["run_status"] = "applied_noop"
                    updated_step["run_notes"] = [
                        "Fetched spatial artifacts were available, but no features matched the compiled source-attribute filters within the current reconstructed extent."
                    ]
                    if extent_mismatch_notes:
                        updated_step["run_notes"].extend(extent_mismatch_notes)
                else:
                    if operation_type == "buffer_then_intersect":
                        buffer_distance_m = float(
                            step.get("buffer_distance_m", 0.0) or 0.0
                        )
                        exclusion_geometries = exclusion_geometries.copy()
                        exclusion_geometries["geometry"] = (
                            exclusion_geometries.geometry.buffer(buffer_distance_m)
                        )
                        exclusion_geometries = exclusion_geometries.loc[
                            ~exclusion_geometries.geometry.is_empty
                        ].copy()
                    try:
                        (
                            current_chunk_records,
                            lu_step_profile,
                        ) = _execute_reconstructed_lu_exclusion_step(
                            chunk_records=current_chunk_records,
                            exclusion_geometries=exclusion_geometries,
                            lu_frame=lu_frame,
                            runtime_step_root=step_dir,
                        )
                        step_profile["candidate_query_seconds"] = float(
                            lu_step_profile["candidate_query_seconds"]
                        )
                        step_profile["overlay_seconds"] = float(
                            lu_step_profile["overlay_seconds"]
                        )
                        step_profile["write_seconds"] = float(
                            lu_step_profile["write_seconds"]
                        )
                        step_profile["lu_chunk_count"] = int(
                            lu_step_profile["lu_chunk_count"]
                        )
                        step_profile["intersecting_exclusion_feature_count"] = int(
                            lu_step_profile["intersecting_exclusion_feature_count"]
                        )
                        if int(lu_step_profile["affected_fragment_count"]) <= 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "No active LU-clipped fragment geometries intersected the exclusion mask."
                            ]
                        else:
                            updated_step["run_status"] = "applied"
                            updated_step["spatial_application_mode"] = "fragment_overlay"
                            updated_step["candidate_row_count"] = int(
                                lu_step_profile["candidate_row_count"]
                            )
                            updated_step["affected_fragment_count"] = int(
                                lu_step_profile["affected_fragment_count"]
                            )
                            updated_step["affected_area_ha"] = float(
                                lu_step_profile["affected_area_ha"]
                            )
                            updated_step["fragment_batch_count"] = int(
                                lu_step_profile["fragment_batch_count"]
                            )
                            updated_step["lu_chunk_count"] = int(
                                lu_step_profile["lu_chunk_count"]
                            )
                            updated_step["intersecting_exclusion_feature_count"] = int(
                                lu_step_profile["intersecting_exclusion_feature_count"]
                            )
                            updated_step["run_notes"] = [
                                "Applied exact LU-wise fragment/resultant exclusion with binary THLB output in EPSG:3005.",
                                "The reconstructed lane now cuts one Landscape Unit chunk at a time instead of building one full-TSA exact-overlay workload.",
                            ]
                    except Exception as exc:
                        updated_step["run_status"] = "blocked_exact_overlay"
                        updated_step["spatial_application_mode"] = "blocked_exact_overlay"
                        updated_step["run_notes"] = [
                            "Exact fragment-overlay execution was required for reconstructed mode, so this step was blocked instead of silently approximating it.",
                            f"Blocking reason: {exc}",
                        ]
                    if missing_sources:
                        updated_step["missing_source_entry_ids"] = missing_sources
        elif normalized_action == "aspatial_reduction":
            benchmark_marginal_area_ha = updated_step.get("benchmark_marginal_area_ha")
            if benchmark_marginal_area_ha is None or total_area_benchmark_ha is None:
                updated_step["run_status"] = "unsupported"
                updated_step["run_notes"] = [
                    "Aspatial reduction requires TSR benchmark marginal area and total TSA area benchmark."
                ]
            else:
                current_managed_area_ha = 0.0
                for record in current_chunk_records:
                    current_managed_area_ha += _managed_area_ha(
                        _load_lu_chunk_frame(Path(record["chunk_path"]))
                    )
                target_removed_area_ha = (
                    float(benchmark_marginal_area_ha)
                    * current_managed_area_ha
                    / total_area_benchmark_ha
                )
                fallback_started = perf_counter()
                (
                    current_chunk_records,
                    removed_area_ha,
                    affected_row_count,
                    touched_chunk_count,
                ) = _apply_reconstructed_lu_aspatial_thlb_reduction(
                    chunk_records=current_chunk_records,
                    runtime_step_root=step_dir,
                    target_removed_area_ha=target_removed_area_ha,
                )
                step_profile["overlay_seconds"] = perf_counter() - fallback_started
                step_profile["write_seconds"] = step_profile["overlay_seconds"]
                step_profile["lu_chunk_count"] = touched_chunk_count
                updated_step["run_status"] = (
                    "applied" if removed_area_ha > 0 else "applied_noop"
                )
                updated_step["spatial_application_mode"] = "aspatial_fallback"
                updated_step["affected_stand_count"] = affected_row_count
                updated_step["affected_area_ha"] = removed_area_ha
                updated_step["lu_chunk_count"] = touched_chunk_count
                updated_step["run_notes"] = [
                    "Applied the TSR area target as a documented reconstructed-mode aspatial fallback because no exact spatial implementation is available for this recipe row.",
                    "The fallback was applied across the current LU-wise reconstructed state without changing the reviewed TSA29 parent-step lane.",
                ]
        elif normalized_action == "aspatial_area_reduction":
            benchmark_marginal_area_ha = updated_step.get("benchmark_marginal_area_ha")
            if benchmark_marginal_area_ha is None or total_area_benchmark_ha is None:
                updated_step["run_status"] = "unsupported"
                updated_step["run_notes"] = [
                    "Aspatial area reduction requires TSR benchmark marginal area and total TSA area benchmark."
                ]
            else:
                residual_target_ha = float(benchmark_marginal_area_ha)
                if bool(updated_step.get("subtract_parent_exact_removed_area")):
                    residual_target_ha = max(
                        0.0,
                        residual_target_ha
                        - _resolve_parent_exact_removed_area_ha(
                            applied_steps=applied_steps,
                            parent_step_id=str(
                                updated_step.get("parent_step_id", "")
                            ).strip(),
                        ),
                    )
                current_area_ha = 0.0
                for record in current_chunk_records:
                    current_area_ha += float(
                        _resolve_canonical_stand_area_sqm(
                            _load_lu_chunk_frame(Path(record["chunk_path"]))
                        ).sum()
                        / 10000.0
                    )
                if bool(updated_step.get("subtract_parent_exact_removed_area")):
                    target_removed_area_ha = residual_target_ha
                else:
                    target_removed_area_ha = (
                        residual_target_ha * current_area_ha / total_area_benchmark_ha
                    )
                fallback_started = perf_counter()
                (
                    current_chunk_records,
                    removed_area_ha,
                    affected_row_count,
                    touched_chunk_count,
                ) = _apply_reconstructed_lu_aspatial_area_reduction(
                    chunk_records=current_chunk_records,
                    runtime_step_root=step_dir,
                    target_removed_area_ha=target_removed_area_ha,
                )
                step_profile["overlay_seconds"] = perf_counter() - fallback_started
                step_profile["write_seconds"] = step_profile["overlay_seconds"]
                step_profile["lu_chunk_count"] = touched_chunk_count
                updated_step["run_status"] = (
                    "applied" if removed_area_ha > 0 else "applied_noop"
                )
                updated_step["spatial_application_mode"] = "aspatial_fallback"
                updated_step["affected_stand_count"] = affected_row_count
                updated_step["affected_area_ha"] = removed_area_ha
                updated_step["lu_chunk_count"] = touched_chunk_count
                updated_step["run_notes"] = [
                    "Applied the TSR area target as a documented reconstructed-mode aspatial fallback because no exact spatial implementation is available for this recipe row.",
                    "This early-area deduction scales active LU-wise reconstructed stand-area fields instead of claiming exact spatial reproduction.",
                ]
                if bool(updated_step.get("subtract_parent_exact_removed_area")):
                    updated_step["run_notes"].append(
                        f"Residual fallback target after same-parent exact removal: {target_removed_area_ha:.3f} ha."
                    )
        else:
            updated_step["run_status"] = "unsupported"
            updated_step["run_notes"] = [
                f"Normalized action `{normalized_action or 'unknown'}` is not executable in v1."
            ]

        updated_step["page_number"] = page_number
        applied_steps.append(updated_step)
        outcome_counts.update([str(updated_step.get("run_status", "unsupported"))])
        step_profile["run_status"] = str(updated_step.get("run_status", "unsupported"))
        step_profile["spatial_application_mode"] = str(
            updated_step.get("spatial_application_mode", "")
        ).strip()
        step_profile["candidate_row_count"] = int(
            updated_step.get("candidate_row_count") or 0
        )
        step_profile["fragment_batch_count"] = int(
            updated_step.get("fragment_batch_count") or 0
        )
        step_profile["total_seconds"] = perf_counter() - step_start
        diagnostic_steps.append(step_profile)

    merged_checkpoint, merge_seconds = _merge_reconstructed_lu_chunk_records(
        current_chunk_records
    )
    diagnostic_steps.append(
        {
            "step_id": "__lu_merge__",
            "label": "Final reconstructed LU merge",
            "normalized_action": "lu_merge",
            "merge_seconds": merge_seconds,
            "lu_chunk_count": len(current_chunk_records),
            "total_seconds": merge_seconds,
        }
    )
    return (
        merged_checkpoint,
        applied_steps,
        dict(sorted(outcome_counts.items())),
        diagnostic_steps,
    )


def _execute_tsr_thlb_recipe_steps(
    *,
    recipe_steps: Sequence[dict[str, Any]],
    checkpoint: gpd.GeoDataFrame,
    checkpoint_path: Path,
    execution_mode: str,
    instance_root: Path,
    source_entry_map: dict[str, dict[str, Any]],
    allow_stand_binary_fallback: bool,
    total_area_benchmark_ha: float | None = None,
) -> tuple[
    gpd.GeoDataFrame, list[dict[str, Any]], dict[str, int], list[dict[str, Any]]
]:
    if (
        execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED
        and not allow_stand_binary_fallback
    ):
        return _execute_tsr_thlb_recipe_steps_reconstructed_lu(
            recipe_steps=recipe_steps,
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
            instance_root=instance_root,
            source_entry_map=source_entry_map,
            total_area_benchmark_ha=total_area_benchmark_ha,
        )
    outcome_counts: Counter[str] = Counter()
    applied_steps: list[dict[str, Any]] = []
    diagnostic_steps: list[dict[str, Any]] = []

    for step in recipe_steps:
        step_start = perf_counter()
        overlay_start = 0.0
        step_profile: dict[str, Any] = {
            "step_id": str(step.get("step_id", "")).strip(),
            "label": str(step.get("label", "")).strip(),
            "normalized_action": str(step.get("normalized_action", "")).strip(),
            "source_load_seconds": 0.0,
            "candidate_query_seconds": 0.0,
            "overlay_seconds": 0.0,
            "write_seconds": 0.0,
        }
        updated_step = dict(step)
        normalized_action = str(step.get("normalized_action", "")).strip()
        operation_type = _resolve_compiled_operation_type(step)
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
            if operation_type == "select_attribute":
                filters = [
                    dict(item)
                    for item in step.get("checkpoint_attribute_filters", ())
                    if isinstance(item, dict)
                ]
                mode = str(step.get("checkpoint_attribute_mode", "any")).strip() or "any"
                overlay_start = perf_counter()
                checkpoint, removed_area_ha = _apply_checkpoint_attribute_filters(
                    checkpoint,
                    filters=filters,
                    mode=mode,
                    preserve_geometry=False,
                )
                step_profile["overlay_seconds"] = perf_counter() - overlay_start
                updated_step["affected_area_ha"] = float(removed_area_ha)
                updated_step["run_status"] = (
                    "applied" if removed_area_ha > 0 else "applied_noop"
                )
                updated_step["run_notes"] = [
                    "Applied checkpoint-attribute exclusion directly against checkpoint geometry without requiring fetched source polygons."
                    if removed_area_ha > 0
                    else "No active checkpoint rows matched the checkpoint attribute filters."
                ]
            else:
                source_load_start = perf_counter()
                exclusion_geometries, missing_sources, extent_mismatch_notes = (
                    _load_exclusion_geometries(
                        instance_root=instance_root,
                        linked_source_entry_ids=linked_source_entry_ids,
                        source_entry_map=source_entry_map,
                        bbox=(
                            float(checkpoint.total_bounds[0]),
                            float(checkpoint.total_bounds[1]),
                            float(checkpoint.total_bounds[2]),
                            float(checkpoint.total_bounds[3]),
                        ),
                    )
                )
                step_profile["source_load_seconds"] = perf_counter() - source_load_start
                if exclusion_geometries is None:
                    if extent_mismatch_notes:
                        updated_step["run_status"] = "blocked_extent_mismatch"
                        updated_step["run_notes"] = extent_mismatch_notes
                    else:
                        updated_step["run_status"] = "blocked_missing_source"
                        updated_step["run_notes"] = [
                            "No fetched polygon artifact was available for the linked source entries."
                        ]
                        if missing_sources:
                            updated_step["missing_source_entry_ids"] = missing_sources
                else:
                    if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                        candidate_query_start = perf_counter()
                        candidate_count = _count_exclusion_candidate_rows(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        step_profile["candidate_query_seconds"] = (
                            perf_counter() - candidate_query_start
                        )
                        if candidate_count == 0:
                            updated_step["run_status"] = "applied_noop"
                            updated_step["run_notes"] = [
                                "No active land-base geometries intersected the exclusion mask."
                            ]
                        else:
                            try:
                                overlay_start = perf_counter()
                                if (
                                    allow_stand_binary_fallback
                                    and candidate_count
                                    > _RECONSTRUCTED_FRAGMENT_ROW_THRESHOLD
                                ):
                                    (
                                        checkpoint,
                                        affected_stand_count,
                                        affected_area_ha,
                                        overlap_area_ha,
                                    ) = _apply_binary_stand_exclusion(
                                        checkpoint=checkpoint,
                                        exclusion_geometries=exclusion_geometries,
                                    )
                                    step_profile["overlay_seconds"] = (
                                        perf_counter() - overlay_start
                                    )
                                    if affected_stand_count == 0:
                                        updated_step["run_status"] = "applied_noop"
                                        updated_step["run_notes"] = [
                                            "Candidate rows were found, but the explicit debug stand-binary fallback netted down no rows."
                                        ]
                                    else:
                                        updated_step["run_status"] = "applied"
                                        updated_step["spatial_application_mode"] = (
                                            "stand_binary_majority"
                                        )
                                        updated_step["candidate_row_count"] = (
                                            candidate_count
                                        )
                                        updated_step["affected_stand_count"] = (
                                            affected_stand_count
                                        )
                                        updated_step["affected_area_ha"] = (
                                            affected_area_ha
                                        )
                                        updated_step["overlap_area_ha"] = (
                                            overlap_area_ha
                                        )
                                        updated_step["run_notes"] = [
                                            "Applied the user-enabled debug stand-binary fallback because the candidate-row workload exceeded the exact fragment-overlay threshold.",
                                            "Representative-point containment was used as the coarse stand-binary approximation.",
                                        ]
                                else:
                                    (
                                        checkpoint,
                                        exact_candidate_count,
                                        affected_fragment_count,
                                        affected_area_ha,
                                        fragment_batch_count,
                                    ) = _fragment_binary_exclusion_step_chunked(
                                        checkpoint=checkpoint,
                                        exclusion_geometries=exclusion_geometries,
                                    )
                                    step_profile["overlay_seconds"] = (
                                        perf_counter() - overlay_start
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
                                        updated_step["candidate_row_count"] = (
                                            exact_candidate_count
                                        )
                                        updated_step["affected_fragment_count"] = (
                                            affected_fragment_count
                                        )
                                        updated_step["affected_area_ha"] = (
                                            affected_area_ha
                                        )
                                        updated_step["fragment_batch_count"] = (
                                            fragment_batch_count
                                        )
                                        updated_step["run_notes"] = [
                                            "Applied exact fragment/resultant exclusion with binary THLB output in EPSG:3005.",
                                            "Large candidate workloads are chunked deterministically instead of silently falling back to coarse stand-binary approximation.",
                                        ]
                            except Exception as exc:
                                if overlay_start:
                                    step_profile["overlay_seconds"] = (
                                        perf_counter() - overlay_start
                                    )
                                if allow_stand_binary_fallback:
                                    fallback_start = perf_counter()
                                    (
                                        checkpoint,
                                        affected_stand_count,
                                        affected_area_ha,
                                        overlap_area_ha,
                                    ) = _apply_binary_stand_exclusion(
                                        checkpoint=checkpoint,
                                        exclusion_geometries=exclusion_geometries,
                                    )
                                    step_profile["overlay_seconds"] += (
                                        perf_counter() - fallback_start
                                    )
                                    if affected_stand_count == 0:
                                        updated_step["run_status"] = "applied_noop"
                                        updated_step["run_notes"] = [
                                            "Exact fragment-overlay execution failed, and the explicit debug stand-binary fallback netted down no rows."
                                        ]
                                    else:
                                        updated_step["run_status"] = "applied"
                                        updated_step["spatial_application_mode"] = (
                                            "stand_binary_majority"
                                        )
                                        updated_step["candidate_row_count"] = (
                                            candidate_count
                                        )
                                        updated_step["affected_stand_count"] = (
                                            affected_stand_count
                                        )
                                        updated_step["affected_area_ha"] = (
                                            affected_area_ha
                                        )
                                        updated_step["overlap_area_ha"] = (
                                            overlap_area_ha
                                        )
                                        updated_step["fallback_trigger"] = (
                                            "exact_overlay_exception"
                                        )
                                        updated_step["run_notes"] = [
                                            "Exact fragment-overlay execution failed, so the user-enabled debug stand-binary fallback was used instead.",
                                            f"Fallback reason: {exc}",
                                        ]
                                else:
                                    updated_step["run_status"] = "blocked_exact_overlay"
                                    updated_step["spatial_application_mode"] = (
                                        "blocked_exact_overlay"
                                    )
                                    updated_step["candidate_row_count"] = (
                                        candidate_count
                                    )
                                    updated_step["run_notes"] = [
                                        "Exact fragment-overlay execution was required for reconstructed mode, so this step was blocked instead of silently approximating it.",
                                        f"Blocking reason: {exc}",
                                    ]
                    else:
                        overlay_start = perf_counter()
                        exclusion_fraction = _compute_exclusion_fraction(
                            checkpoint=checkpoint,
                            exclusion_geometries=exclusion_geometries,
                        )
                        step_profile["overlay_seconds"] = perf_counter() - overlay_start
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
            if execution_mode != TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                updated_step["run_status"] = "unsupported"
                updated_step["run_notes"] = [
                    "Aspatial reduction steps are preserved for review in this execution lane."
                ]
            else:
                benchmark_marginal_area_ha = updated_step.get(
                    "benchmark_marginal_area_ha"
                )
                if (
                    benchmark_marginal_area_ha is None
                    or total_area_benchmark_ha is None
                ):
                    updated_step["run_status"] = "unsupported"
                    updated_step["run_notes"] = [
                        "Aspatial reduction requires TSR benchmark marginal area and total TSA area benchmark."
                    ]
                else:
                    current_managed_area_ha = _managed_area_ha(checkpoint)
                    target_removed_area_ha = (
                        float(benchmark_marginal_area_ha)
                        * current_managed_area_ha
                        / total_area_benchmark_ha
                    )
                    checkpoint, removed_area_ha, affected_row_count = (
                        _apply_aspatial_thlb_reduction(
                            checkpoint,
                            target_removed_area_ha=target_removed_area_ha,
                        )
                    )
                    updated_step["run_status"] = (
                        "applied" if removed_area_ha > 0 else "applied_noop"
                    )
                    updated_step["spatial_application_mode"] = "aspatial_fallback"
                    updated_step["affected_stand_count"] = affected_row_count
                    updated_step["affected_area_ha"] = removed_area_ha
                    updated_step["run_notes"] = [
                        "Applied the TSR area target as a documented reconstructed-mode aspatial fallback because no exact spatial implementation is available for this recipe row.",
                        "The deduction stayed recipe-driven; no blocked spatial row was auto-converted into fallback.",
                    ]
        elif normalized_action == "aspatial_area_reduction":
            benchmark_marginal_area_ha = updated_step.get("benchmark_marginal_area_ha")
            if benchmark_marginal_area_ha is None or total_area_benchmark_ha is None:
                updated_step["run_status"] = "unsupported"
                updated_step["run_notes"] = [
                    "Aspatial area reduction requires TSR benchmark marginal area and total TSA area benchmark."
                ]
            else:
                residual_target_ha = float(benchmark_marginal_area_ha)
                if bool(updated_step.get("subtract_parent_exact_removed_area")):
                    residual_target_ha = max(
                        0.0,
                        residual_target_ha
                        - _resolve_parent_exact_removed_area_ha(
                            applied_steps=applied_steps,
                            parent_step_id=str(
                                updated_step.get("parent_step_id", "")
                            ).strip(),
                        ),
                    )
                current_area_ha = float(
                    _resolve_canonical_stand_area_sqm(checkpoint).sum() / 10000.0
                )
                if bool(updated_step.get("subtract_parent_exact_removed_area")):
                    target_removed_area_ha = residual_target_ha
                else:
                    target_removed_area_ha = (
                        residual_target_ha * current_area_ha / total_area_benchmark_ha
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
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                    updated_step["spatial_application_mode"] = "aspatial_fallback"
                updated_step["affected_stand_count"] = affected_row_count
                updated_step["affected_area_ha"] = removed_area_ha
                if execution_mode == TSR_THLB_EXECUTION_MODE_RECONSTRUCTED:
                    updated_step["run_notes"] = [
                        "Applied the TSR area target as a documented reconstructed-mode aspatial fallback because no exact spatial implementation is available for this recipe row.",
                        "This early-area deduction shrinks stand-area attributes across the active AFLB subset instead of changing THLB retention directly.",
                    ]
                    if bool(updated_step.get("subtract_parent_exact_removed_area")):
                        updated_step["run_notes"].append(
                            f"Residual fallback target after same-parent exact removal: {target_removed_area_ha:.3f} ha."
                        )
                else:
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
        step_profile["run_status"] = str(updated_step.get("run_status", "unsupported"))
        step_profile["spatial_application_mode"] = str(
            updated_step.get("spatial_application_mode", "")
        ).strip()
        step_profile["candidate_row_count"] = int(
            updated_step.get("candidate_row_count") or 0
        )
        step_profile["fragment_batch_count"] = int(
            updated_step.get("fragment_batch_count") or 0
        )
        step_profile["total_seconds"] = perf_counter() - step_start
        diagnostic_steps.append(step_profile)

    return (
        checkpoint,
        applied_steps,
        dict(sorted(outcome_counts.items())),
        diagnostic_steps,
    )


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
    allow_stand_binary_fallback: bool = False,
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

    checkpoint, applied_steps, outcome_counts, _diagnostic_steps = (
        _execute_tsr_thlb_recipe_steps(
            recipe_steps=recipe.steps,
            checkpoint=checkpoint,
            checkpoint_path=resolved_checkpoint_path,
            execution_mode=execution_mode,
            instance_root=instance_root,
            source_entry_map=source_entry_map,
            allow_stand_binary_fallback=allow_stand_binary_fallback,
            total_area_benchmark_ha=total_area_benchmark_ha,
        )
    )

    final_managed_area_ha = _managed_area_ha(checkpoint)
    reconstructed_timing_summary = _summarize_reconstructed_diagnostics(
        _diagnostic_steps
    )
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
        "allow_stand_binary_fallback": allow_stand_binary_fallback,
        "baseline_signal": baseline_signal,
        "input_area_ha": input_area_ha,
        "baseline_managed_area_ha": baseline_managed_area_ha,
        "final_managed_area_ha": final_managed_area_ha,
        "legacy_reference_managed_area_ha": legacy_reference_managed_area_ha,
        "tsr_reported_aflb_area_ha": tsr_reported_aflb_area_ha,
        "tsr_reported_thlb_area_ha": tsr_reported_thlb_area_ha,
        "fragment_overlay_step_count": int(
            sum(
                1
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "fragment_overlay"
            )
        ),
        "aspatial_fallback_step_count": int(
            sum(
                1
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "aspatial_fallback"
            )
        ),
        "aspatial_fallback_area_ha": float(
            sum(
                float(step.get("affected_area_ha", 0.0) or 0.0)
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "aspatial_fallback"
            )
        ),
        "blocked_exact_overlay_step_count": int(
            sum(
                1
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "blocked_exact_overlay"
            )
        ),
        "stand_binary_fallback_step_count": int(
            sum(
                1
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "stand_binary_majority"
            )
        ),
        "lu_fragment_overlay_chunk_count": int(
            sum(
                int(step.get("lu_chunk_count", 0) or 0)
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "fragment_overlay"
            )
        ),
        "lu_fragment_overlay_feature_count": int(
            sum(
                int(step.get("intersecting_exclusion_feature_count", 0) or 0)
                for step in applied_steps
                if str(step.get("spatial_application_mode", "")).strip()
                == "fragment_overlay"
            )
        ),
        "step_count": len(applied_steps),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "reconstructed_timing_summary": reconstructed_timing_summary,
        "diagnostic_steps": _diagnostic_steps,
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
        allow_stand_binary_fallback=allow_stand_binary_fallback,
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
        warmstart_markdown_relative_path=(
            str(
                default_tsr_thlb_warmstart_markdown_path(instance_root=instance_root)
                .relative_to(instance_root)
                .as_posix()
            )
            if default_tsr_thlb_warmstart_markdown_path(
                instance_root=instance_root
            ).exists()
            else None
        ),
        reconstruction_comparison_markdown_relative_path=(
            str(
                default_tsr_thlb_reconstruction_comparison_markdown_path(
                    instance_root=instance_root
                )
                .relative_to(instance_root)
                .as_posix()
            )
            if default_tsr_thlb_reconstruction_comparison_markdown_path(
                instance_root=instance_root
            ).exists()
            else None
        ),
        applied_steps=applied_steps,
        diagnostic_steps=_diagnostic_steps,
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


def run_tsr_thlb_reconstructed_diagnostic_slice(
    *,
    recipe_path: Path,
    output_path: Path,
    audit_path: Path,
    diagnostic_path: Path,
    checkpoint_path: Path | None = None,
    resume_checkpoint_path: Path | None = None,
    start_index: int = 0,
    end_index: int | None = None,
    allow_stand_binary_fallback: bool = False,
) -> TsrThlbReconstructedDiagnosticSliceResult:
    """Run one reconstructed diagnostic step slice without mutating live recipe surfaces."""

    resolved_recipe_path = recipe_path.expanduser().resolve()
    recipe = load_tsr_thlb_netdown_recipe(resolved_recipe_path)
    instance_root = resolved_recipe_path.parents[2]
    source_layer_recipe_path = _resolve_instance_path(
        instance_root, recipe.instance_inputs.source_layer_recipe_path
    )
    source_recipe = load_tsr_source_layers_recipe(source_layer_recipe_path)
    source_entry_map = _load_source_recipe_entry_map(source_recipe)

    if resume_checkpoint_path is not None and checkpoint_path is not None:
        raise TsrRecipeError(
            "Choose either `checkpoint_path` or `resume_checkpoint_path`, not both."
        )
    resolved_checkpoint_path = (
        resume_checkpoint_path.expanduser().resolve()
        if resume_checkpoint_path is not None
        else (
            checkpoint_path.expanduser().resolve()
            if checkpoint_path is not None
            else _find_tsr_checkpoint_path(instance_root=instance_root, mode="earliest")
        )
    )
    checkpoint = _load_checkpoint_geodataframe(resolved_checkpoint_path)
    if resume_checkpoint_path is not None:
        checkpoint, baseline_signal = _resume_reconstructed_land_base(checkpoint)
    else:
        checkpoint, baseline_signal = _initialize_reconstructed_land_base(checkpoint)
    baseline_managed_area_ha = _managed_area_ha(checkpoint)
    total_area_benchmark_ha = _resolve_tsr_total_area_benchmark(recipe)

    executable_steps = _select_reconstructed_diagnostic_steps(recipe.steps)
    bounded_start = max(0, int(start_index))
    bounded_end = (
        len(executable_steps)
        if end_index is None
        else min(len(executable_steps), max(bounded_start, int(end_index)))
    )
    selected_steps = executable_steps[bounded_start:bounded_end]
    if not selected_steps:
        raise TsrRecipeError(
            "No reconstructed diagnostic steps were selected for the requested slice."
        )

    run_start = perf_counter()
    checkpoint, applied_steps, outcome_counts, diagnostic_steps = (
        _execute_tsr_thlb_recipe_steps(
            recipe_steps=selected_steps,
            checkpoint=checkpoint,
            checkpoint_path=resolved_checkpoint_path,
            execution_mode=TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
            instance_root=instance_root,
            source_entry_map=source_entry_map,
            allow_stand_binary_fallback=allow_stand_binary_fallback,
            total_area_benchmark_ha=total_area_benchmark_ha,
        )
    )
    execution_seconds = perf_counter() - run_start

    checkpoint["thlb_fact"] = checkpoint["thlb_fact"].fillna(0.0).clip(0.0, 1.0)
    checkpoint["thlb"] = checkpoint["thlb_fact"].round().astype(int)
    checkpoint["thlb_raw"] = checkpoint["thlb_fact"]
    checkpoint["thlb_area"] = (
        checkpoint["_stand_area_sqm"] * checkpoint["thlb_fact"] / 10000.0
    )
    checkpoint = _update_geometry_measure_columns(checkpoint)
    final_managed_area_ha = _managed_area_ha(checkpoint)

    write_start = perf_counter()
    output_frame = checkpoint.drop(
        columns=["_row_id", "_stand_area_sqm"], errors="ignore"
    )
    resolved_output_path = output_path.expanduser().resolve()
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    output_frame.to_feather(resolved_output_path)
    output_write_seconds = perf_counter() - write_start

    resolved_audit_path = audit_path.expanduser().resolve()
    resolved_audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "recipe_path": str(resolved_recipe_path.relative_to(instance_root).as_posix()),
        "checkpoint_path": str(
            resolved_checkpoint_path.relative_to(instance_root).as_posix()
        ),
        "output_path": str(resolved_output_path.relative_to(instance_root).as_posix()),
        "execution_mode": TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        "allow_stand_binary_fallback": allow_stand_binary_fallback,
        "baseline_signal": baseline_signal,
        "baseline_managed_area_ha": baseline_managed_area_ha,
        "final_managed_area_ha": final_managed_area_ha,
        "start_index": bounded_start,
        "end_index": bounded_end,
        "step_count": len(applied_steps),
        "outcome_counts": outcome_counts,
        "steps": applied_steps,
    }
    resolved_audit_path.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    resolved_diagnostic_path = diagnostic_path.expanduser().resolve()
    resolved_diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "recipe_path": str(resolved_recipe_path.relative_to(instance_root).as_posix()),
        "checkpoint_path": str(
            resolved_checkpoint_path.relative_to(instance_root).as_posix()
        ),
        "output_path": str(resolved_output_path.relative_to(instance_root).as_posix()),
        "audit_path": str(resolved_audit_path.relative_to(instance_root).as_posix()),
        "execution_mode": TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        "allow_stand_binary_fallback": allow_stand_binary_fallback,
        "baseline_signal": baseline_signal,
        "resumed_from_checkpoint": resume_checkpoint_path is not None,
        "start_index": bounded_start,
        "end_index": bounded_end,
        "selected_step_ids": [
            str(step.get("step_id", "")).strip() for step in selected_steps
        ],
        "baseline_managed_area_ha": baseline_managed_area_ha,
        "final_managed_area_ha": final_managed_area_ha,
        "execution_seconds": execution_seconds,
        "output_write_seconds": output_write_seconds,
        "total_seconds": execution_seconds + output_write_seconds,
        "step_profiles": diagnostic_steps,
    }
    resolved_diagnostic_path.write_text(
        json.dumps(diagnostic_payload, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    return TsrThlbReconstructedDiagnosticSliceResult(
        recipe_path=resolved_recipe_path,
        checkpoint_path=resolved_checkpoint_path,
        output_path=resolved_output_path,
        audit_path=resolved_audit_path,
        diagnostic_path=resolved_diagnostic_path,
        execution_mode=TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        baseline_signal=baseline_signal,
        executed_step_ids=tuple(
            str(step.get("step_id", "")).strip() for step in selected_steps
        ),
        start_index=bounded_start,
        end_index=bounded_end,
        step_count=len(applied_steps),
        outcome_counts=outcome_counts,
        baseline_managed_area_ha=baseline_managed_area_ha,
        final_managed_area_ha=final_managed_area_ha,
        total_seconds=execution_seconds + output_write_seconds,
        resumed_from_checkpoint=resume_checkpoint_path is not None,
    )
