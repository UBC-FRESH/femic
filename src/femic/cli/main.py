"""Typer-based CLI entry point for FEMIC."""

from __future__ import annotations

import json
import os
import csv
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path, PosixPath, WindowsPath
import shutil
from typing import Any
import zipfile

import typer
import yaml
from rich.console import Console

from femic import __version__
from femic.account_surface import summarize_account_surface
from femic.geospatial_preflight import run_geospatial_preflight
from femic.instance_bootstrap import bootstrap_instance_workspace
from femic.instance_context import (
    INSTANCE_ROOT_ENV,
    InstanceContext,
    resolve_instance_context,
)
from femic.fmg import (
    DEFAULT_CC_MAX_AGE,
    DEFAULT_CC_MIN_AGE,
    DEFAULT_CC_TRANSITION_IFM,
    DEFAULT_FRAGMENTS_CRS,
    DEFAULT_HORIZON_YEARS,
    DEFAULT_IFM_SOURCE_COL,
    DEFAULT_IFM_TARGET_MANAGED_SHARE,
    DEFAULT_IFM_THRESHOLD,
    DEFAULT_SERAL_STAGE_CONFIG_PATH,
    DEFAULT_SILVICULTURE_CONFIG_PATH,
    DEFAULT_START_YEAR,
    DEFAULT_WOODSTOCK_OUTPUT_DIR,
    export_patchworks_package,
    export_woodstock_package,
)
from femic.patchworks_runtime import (
    DEFAULT_PATCHWORKS_CONFIG_PATH,
    DEFAULT_PATCHWORKS_LOG_DIR,
    PatchworksConfigError,
    PatchworksTopologyBackend,
    build_patchworks_blocks_dataset,
    format_command_for_display,
    load_patchworks_runtime_config,
    run_patchworks_command,
    run_patchworks_preflight,
)
from femic.rebuild_baseline import (
    apply_diff_allowlist,
    build_current_snapshot,
    diff_snapshots,
    load_diff_allowlist,
    load_snapshot,
    resolve_baseline_path,
    save_snapshot,
)
from femic.rebuild_invariants import (
    append_invariant_payload_to_report,
    build_species_account_policy_invariants,
    collect_rebuild_metrics,
    evaluate_invariants,
    has_fatal_invariant_failures,
)
from femic.rebuild_runner import JsonRebuildReportSink, RebuildRunner, RebuildStep
from femic.rebuild_spec import load_rebuild_spec, validate_rebuild_spec_payload
from femic.release_packaging import build_release_package
from femic.pipeline.io import (
    build_pipeline_run_config,
    file_sha256,
    load_pipeline_run_profile,
    resolve_legacy_external_data_paths,
    resolve_effective_run_options,
)
from femic.pipeline.tipsy_config import (
    discover_tipsy_config_tsas,
    load_tipsy_tsa_config,
)
from femic.vdyp.reporting import (
    VdypWarningBudget,
    evaluate_warning_budget,
    summarize_curve_selection_rows,
    summarize_vdyp_logs,
)
from femic.ws3_smoke import run_ws3_smoke
from femic.workflows.legacy import run_data_prep, run_post_tipsy_bundle_with_manifest

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Forest Estate Model Input Compiler (FEMIC).",
)
prep_app = typer.Typer(
    add_completion=False, no_args_is_help=True, help="Prepare data inputs."
)
vdyp_app = typer.Typer(
    add_completion=False, no_args_is_help=True, help="Run VDYP workflows."
)
tsa_app = typer.Typer(
    add_completion=False, no_args_is_help=True, help="Process individual TSAs."
)
tipsy_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Validate TIPSY config handoff files.",
)
export_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Export model artifacts for downstream planning systems.",
)
patchworks_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Run proprietary Patchworks Matrix Builder (Wine on Linux, native on Windows).",
)
instance_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Initialize and manage deployment-instance workspaces.",
)
console = Console()

_HostPath = WindowsPath if sys.platform.startswith("win") else PosixPath

DATA_ROOT_OPTION = typer.Option(
    Path("data"),
    "--data-root",
    help="Root directory for input data.",
)
OUTPUT_ROOT_OPTION = typer.Option(
    Path("outputs"),
    "--output-root",
    help="Root directory for generated outputs.",
)
TSA_OPTION = typer.Option(
    None,
    "--tsa",
    help="Limit processing to TSA code(s). Can be provided multiple times.",
    show_default=False,
)
RESUME_OPTION = typer.Option(
    False,
    "--resume",
    help="Skip steps that appear to be completed already.",
)
DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    help="Show planned work without executing.",
)
VERBOSE_OPTION = typer.Option(
    False,
    "--verbose",
    "-v",
    help="Enable verbose output.",
)
VERSION_OPTION = typer.Option(
    False,
    "--version",
    help="Show version and exit.",
)
DEBUG_OPTION = typer.Option(
    False,
    "--debug",
    help="Enable rich tracebacks.",
)
SKIP_CHECKS_OPTION = typer.Option(
    False,
    "--skip-checks",
    help="Skip preflight checks for external tools and inputs.",
)
DEBUG_ROWS_OPTION = typer.Option(
    None,
    "--debug-rows",
    help="Limit pipeline input rows for faster debugging (uses head(N)).",
    show_default=False,
)
RUN_ID_OPTION = typer.Option(
    None,
    "--run-id",
    help="Optional run identifier for manifest/log file naming.",
    show_default=False,
)
LOG_DIR_OPTION = typer.Option(
    Path("vdyp_io/logs"),
    "--log-dir",
    help="Directory for run manifests and run-scoped VDYP JSONL logs.",
)
RUN_CONFIG_OPTION = typer.Option(
    None,
    "--run-config",
    help="YAML/JSON run profile used to seed TSA/strata and mode defaults.",
    show_default=False,
)
INSTANCE_ROOT_OPTION = typer.Option(
    None,
    "--instance-root",
    help=(
        "Root directory for deployment-instance files. "
        f"Defaults to CWD (or {INSTANCE_ROOT_ENV} env var when set)."
    ),
    show_default=False,
)
CASE_RUN_CONFIG_OPTION = typer.Option(
    Path("config/run_profile.case_template.yaml"),
    "--run-config",
    help="YAML/JSON run profile for case preflight validation.",
)
CASE_TIPSY_CONFIG_DIR_OPTION = typer.Option(
    Path("config/tipsy"),
    "--tipsy-config-dir",
    help="Directory containing case TIPSY config files (tsaXX.yaml / tsak3z.yaml).",
)
CASE_STRICT_WARNINGS_OPTION = typer.Option(
    False,
    "--strict-warnings",
    help="Fail preflight when warnings are present.",
)
EXPORT_BUNDLE_DIR_OPTION = typer.Option(
    Path("data/model_input_bundle"),
    "--bundle-dir",
    help="Directory containing au_table.csv / curve_table.csv / curve_points_table.csv.",
)
EXPORT_CHECKPOINT_OPTION = typer.Option(
    Path("data/ria_vri_vclr1p_checkpoint7.feather"),
    "--checkpoint",
    help="Stand checkpoint feather used to build fragments shapefile.",
)
EXPORT_OUTPUT_DIR_OPTION = typer.Option(
    Path("output/patchworks"),
    "--output-dir",
    help="Output directory for ForestModel XML + fragments shapefile.",
)
EXPORT_START_YEAR_OPTION = typer.Option(
    DEFAULT_START_YEAR,
    "--start-year",
    help="Patchworks ForestModel start year.",
)
EXPORT_HORIZON_YEARS_OPTION = typer.Option(
    DEFAULT_HORIZON_YEARS,
    "--horizon-years",
    help="Patchworks ForestModel planning horizon in years.",
)
EXPORT_CC_MIN_AGE_OPTION = typer.Option(
    DEFAULT_CC_MIN_AGE,
    "--cc-min-age",
    help="Clearcut minimum operability age for exported treatment rule.",
)
EXPORT_CC_MAX_AGE_OPTION = typer.Option(
    DEFAULT_CC_MAX_AGE,
    "--cc-max-age",
    help="Clearcut maximum operability age for exported treatment rule.",
)
EXPORT_CC_TRANSITION_IFM_OPTION = typer.Option(
    DEFAULT_CC_TRANSITION_IFM,
    "--cc-transition-ifm",
    help=(
        "Optional post-CC IFM transition assignment (managed|unmanaged). "
        "By default no IFM transition assign is written."
    ),
)
EXPORT_FRAGMENTS_CRS_OPTION = typer.Option(
    DEFAULT_FRAGMENTS_CRS,
    "--fragments-crs",
    help="CRS assigned to exported fragments shapefile.",
)
EXPORT_IFM_SOURCE_COL_OPTION = typer.Option(
    DEFAULT_IFM_SOURCE_COL,
    "--ifm-source-col",
    help=(
        "Optional checkpoint column to use for managed/unmanaged assignment "
        "(for example: thlb_raw)."
    ),
    show_default=False,
)
EXPORT_IFM_THRESHOLD_OPTION = typer.Option(
    DEFAULT_IFM_THRESHOLD,
    "--ifm-threshold",
    help=(
        "Optional numeric threshold applied to the IFM source column "
        "(managed when value > threshold)."
    ),
    show_default=False,
)
EXPORT_IFM_TARGET_MANAGED_SHARE_OPTION = typer.Option(
    DEFAULT_IFM_TARGET_MANAGED_SHARE,
    "--ifm-target-managed-share",
    help=(
        "Optional target managed fraction by stand count (0<share<1). "
        "When set, top-N stands by IFM source value are marked managed."
    ),
    show_default=False,
)
EXPORT_SERAL_STAGE_CONFIG_OPTION = typer.Option(
    DEFAULT_SERAL_STAGE_CONFIG_PATH,
    "--seral-stage-config",
    help=(
        "Optional YAML file defining per-AU seral-stage age boundaries for "
        "ForestModel export."
    ),
    show_default=False,
)
EXPORT_SILVICULTURE_CONFIG_OPTION = typer.Option(
    DEFAULT_SILVICULTURE_CONFIG_PATH,
    "--silviculture-config",
    help=(
        "Optional YAML file defining silviculture treatment scaffold parameters "
        "for ForestModel export."
    ),
    show_default=False,
)
EXPORT_WOODSTOCK_OUTPUT_DIR_OPTION = typer.Option(
    DEFAULT_WOODSTOCK_OUTPUT_DIR,
    "--output-dir",
    help="Output directory for Woodstock compatibility CSV files.",
)
EXPORT_RELEASE_CASE_ID_OPTION = typer.Option(
    None,
    "--case-id",
    help="Case identifier used in release bundle naming (for example: k3z, tsa29).",
    show_default=False,
)
EXPORT_RELEASE_OUTPUT_ROOT_OPTION = typer.Option(
    Path("releases"),
    "--output-root",
    help="Root directory where versioned release bundle folders are created.",
)
EXPORT_RELEASE_PATCHWORKS_DIR_OPTION = typer.Option(
    Path("output/patchworks_k3z_validated"),
    "--patchworks-dir",
    help="Patchworks output directory to package (contains forestmodel.xml + fragments).",
)
EXPORT_RELEASE_WOODSTOCK_DIR_OPTION = typer.Option(
    None,
    "--woodstock-dir",
    help="Optional Woodstock output directory to include in release package.",
    show_default=False,
)
EXPORT_RELEASE_LOGS_DIR_OPTION = typer.Option(
    Path("vdyp_io/logs"),
    "--logs-dir",
    help="Log directory used to include run manifests and Patchworks runtime logs.",
)
EXPORT_RELEASE_RUN_ID_OPTION = typer.Option(
    None,
    "--run-id",
    help="Optional release run-id suffix; defaults to UTC timestamp.",
    show_default=False,
)
EXPORT_RELEASE_STRICT_OPTION = typer.Option(
    True,
    "--strict/--no-strict",
    help="Fail packaging if required model-input/Patchworks artifacts are missing.",
)
EXPORT_DUAL_PATCHWORKS_OUTPUT_DIR_OPTION = typer.Option(
    Path("output/patchworks"),
    "--patchworks-output-dir",
    help="Output directory for Patchworks ForestModel + fragments.",
)
EXPORT_DUAL_WOODSTOCK_OUTPUT_DIR_OPTION = typer.Option(
    DEFAULT_WOODSTOCK_OUTPUT_DIR,
    "--woodstock-output-dir",
    help="Output directory for Woodstock compatibility CSV files.",
)
EXPORT_DUAL_WITH_WS3_SMOKE_OPTION = typer.Option(
    False,
    "--with-ws3-smoke/--no-ws3-smoke",
    help="Run ws3 smoke validation after Woodstock export.",
)
EXPORT_DUAL_WS3_COMMAND_OPTION = typer.Option(
    None,
    "--ws3-command",
    help="Optional shell command that executes ws3 smoke simulation.",
    show_default=False,
)
EXPORT_DUAL_WS3_WORKDIR_OPTION = typer.Option(
    None,
    "--ws3-workdir",
    help="Optional working directory for ws3 command execution.",
    show_default=False,
)
EXPORT_DUAL_WS3_REPORT_OPTION = typer.Option(
    Path("evidence/ws3_smoke_report.latest.json"),
    "--ws3-report",
    help="Output path for ws3 smoke JSON report.",
)
EXPORT_DUAL_WS3_REQUIRE_COMMAND_OPTION = typer.Option(
    False,
    "--ws3-require-command/--ws3-allow-no-command",
    help="Fail ws3 smoke step when --ws3-command is not provided.",
)
EXPORT_DUAL_WS3_TIMEOUT_OPTION = typer.Option(
    600,
    "--ws3-timeout-seconds",
    help="Timeout in seconds for ws3 smoke command execution.",
)
EXPORT_DUAL_WS3_REPO_PATH_OPTION = typer.Option(
    None,
    "--ws3-repo-path",
    help="Optional path to local ws3 source checkout (added to PYTHONPATH for builtin smoke).",
    show_default=False,
)
EXPORT_DUAL_WS3_BUILTIN_SMOKE_OPTION = typer.Option(
    False,
    "--ws3-builtin-smoke/--no-ws3-builtin-smoke",
    help="Run builtin ws3 model smoke using FEMIC->ws3 bridge files.",
)
EXPORT_DUAL_WS3_BRIDGE_DIR_OPTION = typer.Option(
    None,
    "--ws3-bridge-dir",
    help="Optional output directory for generated ws3 Woodstock section files.",
    show_default=False,
)
INSTANCE_REBUILD_RUN_CONFIG_OPTION = typer.Option(
    Path("config/run_profile.case_template.yaml"),
    "--run-config",
    help="Run profile used for rebuild validation and execution.",
)
INSTANCE_REBUILD_SPEC_OPTION = typer.Option(
    Path("config/rebuild.spec.yaml"),
    "--spec",
    help="Path to rebuild spec YAML used for schema validation and execution contract checks.",
)
INSTANCE_REBUILD_TIPSY_CONFIG_DIR_OPTION = typer.Option(
    Path("config/tipsy"),
    "--tipsy-config-dir",
    help="Directory containing tsa*.yaml TIPSY configs for case preflight.",
)
INSTANCE_REBUILD_LOG_DIR_OPTION = typer.Option(
    Path("vdyp_io/logs"),
    "--log-dir",
    help="Directory for rebuild runner reports and step logs.",
)
INSTANCE_REBUILD_RUN_ID_OPTION = typer.Option(
    None,
    "--run-id",
    help="Optional rebuild run identifier (defaults to UTC timestamp).",
    show_default=False,
)
INSTANCE_REBUILD_WITH_PATCHWORKS_OPTION = typer.Option(
    False,
    "--with-patchworks/--no-patchworks",
    help="Include Patchworks preflight + matrix-builder steps in instance rebuild.",
)
INSTANCE_REBUILD_DRY_RUN_OPTION = typer.Option(
    False,
    "--dry-run",
    help="Print the planned rebuild step sequence without executing any step.",
)
INSTANCE_REBUILD_PATCHWORKS_CONFIG_OPTION = typer.Option(
    Path("config/patchworks.runtime.yaml"),
    "--patchworks-config",
    help="Patchworks runtime config used when --with-patchworks is enabled.",
)
INSTANCE_REBUILD_BASELINE_OPTION = typer.Option(
    Path("config/rebuild.baseline.json"),
    "--baseline",
    help="Baseline snapshot JSON for structural diff checks.",
)
INSTANCE_REBUILD_WRITE_BASELINE_OPTION = typer.Option(
    False,
    "--write-baseline",
    help="Write/update baseline snapshot before evaluating baseline diff metrics.",
)
INSTANCE_REBUILD_ALLOWLIST_OPTION = typer.Option(
    Path("config/rebuild.allowlist.yaml"),
    "--allowlist",
    help="Optional YAML/JSON allowlist for intentional baseline diffs.",
)
INSTANCE_EVIDENCE_REPORT_OPTION = typer.Option(
    None,
    "--report",
    help="Path to instance_rebuild_report-<run_id>.json. Defaults to latest in --log-dir.",
    show_default=False,
)
INSTANCE_EVIDENCE_OUTPUT_OPTION = typer.Option(
    Path("evidence/reference_rebuild_report.latest.json"),
    "--output",
    help="Output path for normalized rebuild evidence payload.",
)
INSTANCE_EVIDENCE_LOG_DIR_OPTION = typer.Option(
    Path("vdyp_io/logs"),
    "--log-dir",
    help="Log directory used when auto-selecting latest rebuild report.",
)
INSTANCE_REFERENCE_ROOT_OPTION = typer.Option(
    Path("instances/reference"),
    "--reference-root",
    help="Repository-relative path to the maintainer reference instance.",
)
INSTANCE_EVIDENCE_MAX_WARN_INCREASE_OPTION = typer.Option(
    None,
    "--max-warn-increase",
    help=(
        "Optional threshold for allowed increase in invariant_warn_count "
        "compared to existing output evidence."
    ),
    show_default=False,
)
INSTANCE_EVIDENCE_MAX_BASELINE_DIFF_INCREASE_OPTION = typer.Option(
    None,
    "--max-baseline-diff-increase",
    help=(
        "Optional threshold for allowed increase in summary.baseline_diff_count "
        "compared to existing output evidence."
    ),
    show_default=False,
)
INSTANCE_ACCOUNT_SURFACE_OUTPUT_OPTION = typer.Option(
    None,
    "--output",
    help="Optional JSON output path for account-surface summary.",
    show_default=False,
)
INSTANCE_WS3_SMOKE_WOODSTOCK_DIR_OPTION = typer.Option(
    DEFAULT_WOODSTOCK_OUTPUT_DIR,
    "--woodstock-dir",
    help="Woodstock output directory to validate.",
)
INSTANCE_WS3_SMOKE_OUTPUT_OPTION = typer.Option(
    Path("evidence/ws3_smoke_report.latest.json"),
    "--output",
    help="Output path for ws3 smoke JSON report.",
)
INSTANCE_WS3_SMOKE_COMMAND_OPTION = typer.Option(
    None,
    "--ws3-command",
    help="Optional shell command that executes ws3 smoke simulation.",
    show_default=False,
)
INSTANCE_WS3_SMOKE_WORKDIR_OPTION = typer.Option(
    None,
    "--ws3-workdir",
    help="Optional working directory for ws3 command execution.",
    show_default=False,
)
INSTANCE_WS3_SMOKE_REQUIRE_COMMAND_OPTION = typer.Option(
    False,
    "--require-command/--allow-no-command",
    help="Fail when ws3 command is not provided.",
)
INSTANCE_WS3_SMOKE_TIMEOUT_OPTION = typer.Option(
    600,
    "--timeout-seconds",
    help="Timeout in seconds for ws3 command execution.",
)
INSTANCE_WS3_SMOKE_REPO_PATH_OPTION = typer.Option(
    None,
    "--ws3-repo-path",
    help="Optional path to local ws3 source checkout (added to PYTHONPATH for builtin smoke).",
    show_default=False,
)
INSTANCE_WS3_SMOKE_BUILTIN_OPTION = typer.Option(
    True,
    "--builtin-model-smoke/--no-builtin-model-smoke",
    help="Run builtin ws3 model smoke using FEMIC->ws3 bridge files.",
)
INSTANCE_WS3_SMOKE_BRIDGE_DIR_OPTION = typer.Option(
    None,
    "--ws3-bridge-dir",
    help="Optional output directory for generated ws3 Woodstock section files.",
    show_default=False,
)
PATCHWORKS_CONFIG_OPTION = typer.Option(
    DEFAULT_PATCHWORKS_CONFIG_PATH,
    "--config",
    help="Patchworks runtime YAML/JSON config path.",
)
PATCHWORKS_LOG_DIR_OPTION = typer.Option(
    DEFAULT_PATCHWORKS_LOG_DIR,
    "--log-dir",
    help="Directory for Patchworks runtime stdout/stderr and manifest logs.",
)
PATCHWORKS_RUN_ID_OPTION = typer.Option(
    None,
    "--run-id",
    help="Optional run identifier for Patchworks runtime logs.",
    show_default=False,
)
PATCHWORKS_MODEL_DIR_OPTION = typer.Option(
    None,
    "--model-dir",
    help=(
        "Patchworks model root folder. Defaults to an inferred root based on "
        "runtime config paths."
    ),
    show_default=False,
)
PATCHWORKS_FRAGMENTS_SHP_OPTION = typer.Option(
    None,
    "--fragments-shp",
    help=(
        "Fragments shapefile used to derive blocks. Defaults to "
        "matrix_builder.fragments_path with .shp suffix."
    ),
    show_default=False,
)
PATCHWORKS_TOPOLOGY_RADIUS_OPTION = typer.Option(
    200.0,
    "--topology-radius",
    help=(
        "Neighbour search radius (map units/metres) for generated "
        "topology_blocks_<radius>r.csv."
    ),
)
PATCHWORKS_TOPOLOGY_BACKEND_OPTION = typer.Option(
    "python",
    "--topology-backend",
    help=(
        "Topology builder backend. Use `python` for FEMIC's native builder or "
        "`patchworks-raster` for the noninteractive Patchworks raster builder on Windows."
    ),
)
VDYP_CURVE_LOG_OPTION = typer.Option(
    Path("vdyp_io/logs/vdyp_curve_events.jsonl"),
    "--curve-log",
    help="Path to VDYP curve-event JSONL log.",
)
VDYP_RUN_LOG_OPTION = typer.Option(
    Path("vdyp_io/logs/vdyp_runs.jsonl"),
    "--run-log",
    help="Path to VDYP run-event JSONL log.",
)
VDYP_EXPECTED_FIRST_AGE_OPTION = typer.Option(
    1.0,
    "--expected-first-age",
    help="Expected first age point used for curve anchoring checks.",
)
VDYP_EXPECTED_FIRST_VOLUME_OPTION = typer.Option(
    1e-6,
    "--expected-first-volume",
    help="Expected first volume point used for curve anchoring checks.",
)
VDYP_TOLERANCE_OPTION = typer.Option(
    1e-12,
    "--tolerance",
    help="Absolute tolerance for first-point anchor comparisons.",
)
VDYP_MISMATCH_LIMIT_OPTION = typer.Option(
    10,
    "--mismatch-limit",
    help="Maximum number of first-point mismatches to print.",
)
VDYP_MAX_CURVE_WARNINGS_OPTION = typer.Option(
    None,
    "--max-curve-warnings",
    help="Fail if curve warning events exceed this threshold.",
    show_default=False,
)
VDYP_MAX_FIRST_POINT_MISMATCHES_OPTION = typer.Option(
    None,
    "--max-first-point-mismatches",
    help="Fail if first-point mismatches exceed this threshold.",
    show_default=False,
)
VDYP_MAX_CURVE_PARSE_ERRORS_OPTION = typer.Option(
    None,
    "--max-curve-parse-errors",
    help="Fail if curve-log parse errors exceed this threshold.",
    show_default=False,
)
VDYP_MAX_RUN_PARSE_ERRORS_OPTION = typer.Option(
    None,
    "--max-run-parse-errors",
    help="Fail if run-log parse errors exceed this threshold.",
    show_default=False,
)
VDYP_MIN_CURVE_EVENTS_OPTION = typer.Option(
    None,
    "--min-curve-events",
    help="Fail if curve events are below this threshold.",
    show_default=False,
)
VDYP_MIN_RUN_EVENTS_OPTION = typer.Option(
    None,
    "--min-run-events",
    help="Fail if run events are below this threshold.",
    show_default=False,
)
VDYP_SELECTION_SUMMARY_OUT_OPTION = typer.Option(
    None,
    "--selection-summary-out",
    help="Optional CSV output path for per-stratum curve-selection summary.",
    show_default=False,
)


def _preflight_checks(*, resume: bool, instance_context: InstanceContext) -> None:
    repo_root = instance_context.root
    source_root = _source_tree_root()
    errors: list[str] = []
    warnings: list[str] = []

    data_root = repo_root / "data"
    source_data_root = source_root / "data"

    def _resolve_required(primary: Path, fallback: Path | None = None) -> Path | None:
        if primary.exists():
            return primary
        if fallback is not None and fallback.exists():
            return fallback
        return None

    if not data_root.exists():
        errors.append(f"Missing data directory: {data_root}")
    else:
        # Clean runs can regenerate checkpoint/boundary caches from source inputs.
        required_files: list[tuple[Path, Path | None]] = [
            (
                data_root / "tipsy_params_columns",
                source_data_root / "tipsy_params_columns",
            ),
        ]
        if resume:
            required_files.extend(
                [
                    (data_root / "tsa_boundaries.feather", None),
                    (data_root / "ria_vri_vclr1p_checkpoint1.feather", None),
                ]
            )
        for primary, fallback in required_files:
            resolved = _resolve_required(primary, fallback)
            if resolved is None:
                errors.append(f"Missing required file: {primary}")

        optional_files = [
            data_root / "vdyp_ply.feather",
            data_root / "vdyp_lyr.feather",
            data_root / "vdyp_results.pkl",
        ]
        for path_obj in optional_files:
            if not path_obj.exists():
                warnings.append(f"Optional cache missing: {path_obj}")

    maptiles_path = repo_root / "ria_maptiles.csv"
    source_maptiles_path = source_root / "ria_maptiles.csv"
    if not maptiles_path.exists() and not source_maptiles_path.exists():
        warnings.append(f"Optional maptiles file missing: {maptiles_path}")

    vdyp_cfg = _resolve_required(
        repo_root / "vdyp_io" / "VDYP_CFG", source_root / "vdyp_io" / "VDYP_CFG"
    )
    if vdyp_cfg is None:
        errors.append(
            f"Missing VDYP configuration directory: {repo_root / 'vdyp_io' / 'VDYP_CFG'}"
        )

    vdyp_exe = _resolve_required(
        repo_root / "VDYP7" / "VDYP7" / "VDYP7Console.exe",
        source_root / "VDYP7" / "VDYP7" / "VDYP7Console.exe",
    )
    if vdyp_exe is None:
        errors.append(
            f"Missing VDYP executable: {repo_root / 'VDYP7' / 'VDYP7' / 'VDYP7Console.exe'}"
        )

    windows_host = os.name == "nt"
    wine = shutil.which("wine")
    if not windows_host and not wine:
        if resume:
            warnings.append(
                "wine not found on PATH (resume may still work if caches exist)"
            )
        else:
            errors.append(
                "wine not found on PATH (required to run VDYP on non-Windows systems)"
            )
    if windows_host:
        if shutil.which("git") is None:
            errors.append(
                "git not found on PATH (required for Windows FEMIC runtime workflows)"
            )
        if (
            shutil.which("git-annex") is None
            and shutil.which("git-annex.exe") is None
            and shutil.which("git-annex.cmd") is None
        ):
            errors.append(
                "git-annex not found on PATH (required for annex-backed Windows data workflows)"
            )

    for message in warnings:
        console.print(f"[yellow]Warning:[/yellow] {message}")

    if errors:
        for message in errors:
            console.print(f"[red]Error:[/red] {message}")
        raise typer.Exit(code=1)


def _source_tree_root() -> Path:
    """Return the FEMIC source checkout root that owns this CLI module."""
    return _HostPath(__file__).resolve().parents[3]


def _resolve_datalad_executable(source_root: Path) -> str | None:
    """Resolve a usable DataLad executable, preferring PATH then the local .venv."""
    path_tool = shutil.which("datalad")
    if path_tool:
        return path_tool
    venv_tool = source_root / ".venv" / "Scripts" / "datalad.exe"
    if venv_tool.exists():
        return str(venv_tool)
    return None


def _run_preflight_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_s: int = 15,
) -> tuple[bool, str]:
    """Run a small external command used for runtime preflight smoke checks."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, ""
    detail = (
        result.stderr.strip() or result.stdout.strip() or f"exit={result.returncode}"
    )
    return False, detail


def _validate_windows_annex_runtime(
    *,
    source_root: Path,
    external_paths: Any,
) -> tuple[list[str], list[str]]:
    """Return Windows annex/DataLad runtime findings for annex-backed public data."""
    errors: list[str] = []
    warnings: list[str] = []

    if os.name != "nt":
        return errors, warnings

    public_data_root = (source_root / "external" / "femic-public-data").resolve()
    required_paths = [
        external_paths.vri_vclr1p_path,
        external_paths.vdyp_input_pandl_path,
        external_paths.tsa_boundaries_path,
        external_paths.site_prod_bc_gdb_path,
    ]
    resolved_required_paths = [
        _HostPath(str(path_obj)).resolve() for path_obj in required_paths
    ]
    if not any(
        path_obj.is_relative_to(public_data_root)
        for path_obj in resolved_required_paths
    ):
        return errors, warnings

    if shutil.which("git") is None:
        errors.append(
            "git not found on PATH (required to validate annex-backed public-data runtime)"
        )
        return errors, warnings

    annex_probe_ok, annex_detail = _run_preflight_command(
        ["git", "-C", str(public_data_root), "annex", "version"],
        cwd=source_root,
    )
    if not annex_probe_ok:
        errors.append(
            f"git-annex is not usable in external/femic-public-data: {annex_detail}"
        )

    datalad_exe = _resolve_datalad_executable(source_root)
    if datalad_exe is None:
        warnings.append(
            "DataLad executable not found (looked on PATH and in .venv\\Scripts\\datalad.exe)"
        )
        return errors, warnings

    datalad_ok, datalad_detail = _run_preflight_command(
        [datalad_exe, "status", str(public_data_root)],
        cwd=source_root,
    )
    if not datalad_ok:
        errors.append(
            "DataLad status check failed for external/femic-public-data: "
            f"{datalad_detail}"
        )

    return errors, warnings


def _enable_rich_tracebacks() -> None:
    try:
        from rich.traceback import install
    except (ModuleNotFoundError, ImportError):
        return
    install(show_locals=True, width=140, extra_lines=2)


def _emit_stub(name: str) -> None:
    console.print(f"[yellow]Not implemented yet:[/yellow] {name}")
    console.print(
        "Use the legacy scripts (`00_data-prep.py`, `01a_run-tsa.py`, `01b_run-tsa.py`) for now."
    )
    raise typer.Exit(code=1)


def _normalize_case_code(value: str) -> str:
    code = str(value).strip()
    return code.zfill(2) if code.isdigit() else code.lower()


def _resolve_cli_instance_context(
    *,
    instance_root: Path | None,
    allow_legacy_fallback: bool = True,
) -> InstanceContext:
    legacy_repo_root = Path(__file__).resolve().parents[3]
    context = resolve_instance_context(
        instance_root=instance_root,
        env=os.environ,
        cwd=Path.cwd(),
        legacy_repo_root=legacy_repo_root,
        allow_legacy_fallback=allow_legacy_fallback,
    )
    for warning in context.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    return context


def _collect_rebuild_artifact_references(
    *, log_dir: Path, run_id: str
) -> dict[str, list[str]]:
    run_manifest = log_dir / f"run_manifest-{run_id}.json"
    patchworks_manifest = log_dir / f"patchworks_matrixbuilder_manifest-{run_id}.json"
    patchworks_stdout = log_dir / f"patchworks_matrixbuilder_stdout-{run_id}.log"
    patchworks_stderr = log_dir / f"patchworks_matrixbuilder_stderr-{run_id}.log"
    report_path = log_dir / f"instance_rebuild_report-{run_id}.json"

    groups = {
        "run_manifests": [run_manifest],
        "patchworks_manifests": [patchworks_manifest],
        "patchworks_logs": [patchworks_stdout, patchworks_stderr],
        "rebuild_reports": [report_path],
    }
    references: dict[str, list[str]] = {}
    for group_name, paths in groups.items():
        references[group_name] = [
            str(path.resolve()) for path in paths if path.exists()
        ]
    return references


@app.callback()
def main(
    version: bool = VERSION_OPTION,
    debug: bool = DEBUG_OPTION,
) -> None:
    """Handle top-level CLI flags before delegating to subcommands."""
    if debug:
        _enable_rich_tracebacks()
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@instance_app.command("init")
def instance_init(
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing template files in the instance root.",
    ),
    download_bc_vri: bool = typer.Option(
        True,
        "--download-bc-vri/--no-download-bc-vri",
        help="Download BC-wide VRI 2024 datasets into standard instance paths.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Assume yes for interactive prompts.",
    ),
) -> None:
    """Create and initialize an instance workspace from packaged templates."""
    context = _resolve_cli_instance_context(
        instance_root=instance_root,
        allow_legacy_fallback=False,
    )

    should_download = download_bc_vri
    if should_download and not yes:
        should_download = typer.confirm(
            "Download BC-wide VRI datasets now? (default: Yes)",
            default=True,
        )

    try:
        result = bootstrap_instance_workspace(
            instance_root=context.root,
            overwrite=overwrite,
            include_bc_vri_download=should_download,
            message_fn=lambda message: console.print(
                f"[blue]instance:[/blue] {message}"
            ),
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        console.print(f"[red]Instance init failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]instance init completed[/green] "
        f"root={result.instance_root} "
        f"written={len(result.written_files)} "
        f"dirs={len(result.created_dirs)}"
    )
    if result.skipped_files:
        console.print(f"skipped_files={len(result.skipped_files)}")
    if result.downloaded_archives:
        console.print(
            "downloaded_archives="
            f"{len(result.downloaded_archives)} extracted_dirs={len(result.extracted_dirs)}"
        )
    geo = run_geospatial_preflight(run_shapefile_smoke=False)
    if geo.errors:
        console.print(
            "[yellow]Geospatial runtime check:[/yellow] dependencies not ready yet. "
            "Run `femic prep geospatial-preflight` after installing Fiona/GDAL."
        )
        console.print(
            f"[yellow]Install hint ({geo.os_family}):[/yellow] {geo.install_hint}"
        )


@instance_app.command("rebuild")
def instance_rebuild(
    spec: Path = INSTANCE_REBUILD_SPEC_OPTION,
    run_config: Path = INSTANCE_REBUILD_RUN_CONFIG_OPTION,
    tipsy_config_dir: Path = INSTANCE_REBUILD_TIPSY_CONFIG_DIR_OPTION,
    log_dir: Path = INSTANCE_REBUILD_LOG_DIR_OPTION,
    run_id: str | None = INSTANCE_REBUILD_RUN_ID_OPTION,
    with_patchworks: bool = INSTANCE_REBUILD_WITH_PATCHWORKS_OPTION,
    dry_run: bool = INSTANCE_REBUILD_DRY_RUN_OPTION,
    patchworks_config: Path = INSTANCE_REBUILD_PATCHWORKS_CONFIG_OPTION,
    baseline: Path = INSTANCE_REBUILD_BASELINE_OPTION,
    write_baseline: bool = INSTANCE_REBUILD_WRITE_BASELINE_OPTION,
    allowlist: Path = INSTANCE_REBUILD_ALLOWLIST_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Execute the reproducible instance rebuild flow and write evidence artifacts."""
    context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_spec = context.resolve_path(spec)
    resolved_run_config = context.resolve_path(run_config)
    resolved_tipsy_config_dir = context.resolve_path(tipsy_config_dir)
    resolved_log_dir = context.resolve_path(log_dir)
    resolved_patchworks_config = context.resolve_path(patchworks_config)
    resolved_baseline = resolve_baseline_path(
        baseline_path=context.resolve_path(baseline),
        instance_root=context.root,
    )
    resolved_allowlist = context.resolve_path(allowlist)
    effective_run_id = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    try:
        spec_payload = load_rebuild_spec(resolved_spec)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        console.print(f"[red]Invalid rebuild spec:[/red] {resolved_spec}: {exc}")
        raise typer.Exit(code=1) from exc
    spec_errors = validate_rebuild_spec_payload(spec_payload)
    if spec_errors:
        console.print(f"[red]Rebuild spec validation failed:[/red] {resolved_spec}")
        for issue in spec_errors:
            console.print(f"[red]-[/red] {issue}")
        raise typer.Exit(code=1)

    steps: list[RebuildStep] = [
        RebuildStep(
            step_id="validate_case",
            action=lambda _ctx: (
                prep_validate_case(
                    run_config=resolved_run_config,
                    tipsy_config_dir=resolved_tipsy_config_dir,
                    strict_warnings=True,
                    instance_root=context.root,
                ),
                {"run_config": str(resolved_run_config)},
            )[1],
        ),
        RebuildStep(
            step_id="geospatial_preflight",
            action=lambda _ctx: (
                prep_geospatial_preflight(
                    strict_warnings=False,
                    skip_shapefile_smoke=False,
                ),
                {"geospatial_check": "ok"},
            )[1],
            depends_on=("validate_case",),
        ),
        RebuildStep(
            step_id="compile_upstream",
            action=lambda _ctx: (
                run_all(
                    data_root=Path("data"),
                    output_root=Path("outputs"),
                    tsa=None,
                    resume=False,
                    dry_run=False,
                    verbose=True,
                    skip_checks=False,
                    debug_rows=None,
                    run_id=effective_run_id,
                    log_dir=resolved_log_dir,
                    run_config=resolved_run_config,
                    instance_root=context.root,
                ),
                {"run_id": effective_run_id},
            )[1],
            depends_on=("geospatial_preflight",),
        ),
        RebuildStep(
            step_id="post_tipsy_bundle",
            action=lambda _ctx: (
                tsa_post_tipsy(
                    tsa=None,
                    verbose=True,
                    run_id=effective_run_id,
                    log_dir=resolved_log_dir,
                    run_config=resolved_run_config,
                    instance_root=context.root,
                ),
                {"post_tipsy": "ok"},
            )[1],
            depends_on=("compile_upstream",),
        ),
    ]
    if with_patchworks:
        steps.extend(
            [
                RebuildStep(
                    step_id="patchworks_preflight",
                    action=lambda _ctx: (
                        patchworks_preflight(
                            config=resolved_patchworks_config,
                            instance_root=context.root,
                        ),
                        {"patchworks_preflight": "ok"},
                    )[1],
                    depends_on=("post_tipsy_bundle",),
                ),
                RebuildStep(
                    step_id="patchworks_matrix_build",
                    action=lambda _ctx: (
                        patchworks_matrix_build(
                            config=resolved_patchworks_config,
                            log_dir=resolved_log_dir,
                            run_id=effective_run_id,
                            interactive=False,
                            instance_root=context.root,
                        ),
                        {"patchworks_matrix_build": "ok"},
                    )[1],
                    depends_on=("patchworks_preflight",),
                ),
            ]
        )

    report_path = resolved_log_dir / f"instance_rebuild_report-{effective_run_id}.json"
    if dry_run:
        console.print(
            f"[yellow]instance rebuild dry-run[/yellow] run_id={effective_run_id} "
            f"steps={len(steps)} report={report_path}"
        )
        for idx, step in enumerate(steps, start=1):
            deps = ", ".join(step.depends_on) if step.depends_on else "<none>"
            console.print(f"{idx}. {step.step_id} (depends_on={deps})")
        return

    runner = RebuildRunner(
        steps=steps,
        report_sink=JsonRebuildReportSink(path=report_path),
    )
    report = runner.run(
        run_id=effective_run_id,
        context={"instance_root": str(context.root)},
    )
    artifact_refs = _collect_rebuild_artifact_references(
        log_dir=resolved_log_dir,
        run_id=effective_run_id,
    )
    try:
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        report_payload["artifact_references"] = artifact_refs
        report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass

    invariants_payload = spec_payload.get("invariants", [])
    runtime_payload = spec_payload.get("runtime", {})
    policy_invariants = build_species_account_policy_invariants(
        runtime_payload.get("species_account_policy")
        if isinstance(runtime_payload, dict)
        else None
    )
    resolved_invariants: list[dict[str, Any]] = []
    if isinstance(invariants_payload, list):
        resolved_invariants.extend(
            item for item in invariants_payload if isinstance(item, dict)
        )
    resolved_invariants.extend(policy_invariants)
    metrics = collect_rebuild_metrics(
        instance_root=context.root,
        log_dir=resolved_log_dir,
        run_id=effective_run_id,
        patchworks_config_path=resolved_patchworks_config,
    )
    account_surface_summary: dict[str, Any] | None = None
    if resolved_patchworks_config.exists():
        try:
            runtime_config = load_patchworks_runtime_config(resolved_patchworks_config)
            accounts_csv_path = runtime_config.matrix_output_dir / "accounts.csv"
            if accounts_csv_path.exists():
                account_surface_summary = summarize_account_surface(
                    accounts_csv_path=accounts_csv_path,
                    products_csv_path=runtime_config.matrix_output_dir / "products.csv",
                    curves_csv_path=runtime_config.matrix_output_dir / "curves.csv",
                )
                diagnosis = account_surface_summary.get("diagnosis", {})
                if isinstance(diagnosis, dict):
                    metrics["account_surface.total_ok_species_empty_signature"] = bool(
                        diagnosis.get("total_ok_species_empty_signature", False)
                    )
                    metrics["account_surface.species_count"] = int(
                        account_surface_summary.get("species_count", 0) or 0
                    )
        except (
            FileNotFoundError,
            PatchworksConfigError,
            json.JSONDecodeError,
            yaml.YAMLError,
            OSError,
            ValueError,
        ):
            account_surface_summary = None
    baseline_diff_payload: dict[str, object] | None = None
    baseline_allowlist_payload: dict[str, object] | None = None
    baseline_allowlist_result: dict[str, object] | None = None
    baseline_snapshot_payload: dict[str, object] | None = None
    current_snapshot_payload: dict[str, object] | None = None
    baseline_status = "unavailable"
    baseline_unexpected_diff_threshold = 0
    if isinstance(runtime_payload, dict):
        raw_threshold = runtime_payload.get("baseline_unexpected_diff_threshold", 0)
        try:
            baseline_unexpected_diff_threshold = int(raw_threshold)
        except (TypeError, ValueError):
            baseline_unexpected_diff_threshold = 0
    if resolved_patchworks_config.exists():
        try:
            current_snapshot_payload = build_current_snapshot(
                patchworks_config_path=resolved_patchworks_config
            )
            if write_baseline or not resolved_baseline.exists():
                save_snapshot(
                    path=resolved_baseline,
                    snapshot=current_snapshot_payload,
                )
                baseline_status = (
                    "written" if write_baseline else "initialized_missing_baseline"
                )
            if resolved_baseline.exists():
                baseline_snapshot_payload = load_snapshot(resolved_baseline)
                baseline_diff_payload = diff_snapshots(
                    baseline=baseline_snapshot_payload,
                    current=current_snapshot_payload,
                )
                metrics["baseline_match"] = baseline_diff_payload["baseline_match"]
                metrics["baseline_diff_count"] = baseline_diff_payload["diff_count"]
                baseline_allowlist_payload = load_diff_allowlist(resolved_allowlist)
                if baseline_allowlist_payload:
                    baseline_allowlist_result = apply_diff_allowlist(
                        diff_payload=baseline_diff_payload,
                        allowlist_payload=baseline_allowlist_payload,
                    )
                    metrics["baseline_allowlist_match"] = baseline_allowlist_result[
                        "allowlist_match"
                    ]
                    metrics["baseline_unexpected_diff_count"] = (
                        baseline_allowlist_result["unexpected_diff_count"]
                    )
                if baseline_status == "unavailable":
                    baseline_status = "evaluated"
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            metrics["baseline_match"] = None
            metrics["baseline_diff_count"] = None
            metrics["baseline_allowlist_match"] = None
            metrics["baseline_unexpected_diff_count"] = None
            baseline_status = f"error: {exc}"

    invariant_results = evaluate_invariants(
        invariants=resolved_invariants,
        metrics=metrics,
    )
    try:
        append_invariant_payload_to_report(
            report_path=report_path,
            metrics=metrics,
            invariant_results=invariant_results,
        )
        if baseline_status != "unavailable":
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            report_payload["baseline"] = {
                "status": baseline_status,
                "path": str(resolved_baseline),
                "diff": baseline_diff_payload,
                "allowlist_path": str(resolved_allowlist),
                "allowlist": baseline_allowlist_payload,
                "allowlist_result": baseline_allowlist_result,
                "current_snapshot": current_snapshot_payload,
                "baseline_snapshot": baseline_snapshot_payload,
            }
            if account_surface_summary is not None:
                diagnostics_payload = report_payload.get("diagnostics", {})
                if not isinstance(diagnostics_payload, dict):
                    diagnostics_payload = {}
                diagnostics_payload["account_surface"] = account_surface_summary
                report_payload["diagnostics"] = diagnostics_payload
            report_path.write_text(
                json.dumps(report_payload, indent=2), encoding="utf-8"
            )
        elif account_surface_summary is not None:
            report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            diagnostics_payload = report_payload.get("diagnostics", {})
            if not isinstance(diagnostics_payload, dict):
                diagnostics_payload = {}
            diagnostics_payload["account_surface"] = account_surface_summary
            report_payload["diagnostics"] = diagnostics_payload
            report_path.write_text(
                json.dumps(report_payload, indent=2), encoding="utf-8"
            )
    except (OSError, json.JSONDecodeError):
        pass

    status = "[green]ok[/green]" if not report.failed else "[red]failed[/red]"
    console.print(
        f"instance rebuild {status} run_id={effective_run_id} "
        f"steps={len(report.outcomes)} report={report_path}"
    )
    console.print(
        "artifact_refs: "
        f"run_manifests={len(artifact_refs.get('run_manifests', []))} "
        f"patchworks_manifests={len(artifact_refs.get('patchworks_manifests', []))} "
        f"patchworks_logs={len(artifact_refs.get('patchworks_logs', []))}"
    )
    for outcome in report.outcomes:
        console.print(
            f"- {outcome.step_id}: {outcome.status} "
            f"duration={outcome.duration_seconds:.2f}s"
        )
        if outcome.error:
            console.print(f"  [red]{outcome.error}[/red]")
    fatal_invariant_failure = has_fatal_invariant_failures(invariant_results)
    if invariant_results:
        summary = {
            "pass": sum(1 for item in invariant_results if item.status == "pass"),
            "warn": sum(1 for item in invariant_results if item.status == "warn"),
            "fail": sum(1 for item in invariant_results if item.status == "fail"),
        }
        console.print(
            "invariants: "
            f"pass={summary['pass']} warn={summary['warn']} fail={summary['fail']}"
        )
        for item in invariant_results:
            marker = "green" if item.status == "pass" else "yellow"
            if item.status == "fail":
                marker = "red"
            console.print(
                f"[{marker}]- {item.invariant_id}: {item.status}[/{marker}] "
                f"{item.message}"
            )
            if item.status in {"warn", "fail"} and item.remediation:
                console.print(f"  remediation: {item.remediation}")
    if baseline_status != "unavailable":
        console.print(
            "baseline: "
            f"status={baseline_status} "
            f"path={resolved_baseline} "
            f"diff_count={metrics.get('baseline_diff_count')} "
            f"unexpected_diff_count={metrics.get('baseline_unexpected_diff_count')}"
        )
    if account_surface_summary is not None:
        diagnosis = account_surface_summary.get("diagnosis", {})
        signature = (
            diagnosis.get("total_ok_species_empty_signature", False)
            if isinstance(diagnosis, dict)
            else False
        )
        console.print(
            "account_surface: "
            f"species={account_surface_summary.get('species_count')} "
            f"au={account_surface_summary.get('au_count')} "
            f"total_ok_species_empty={bool(signature)}"
        )
    unexpected_diff_count_value = metrics.get("baseline_unexpected_diff_count")
    unexpected_diff_count = (
        int(unexpected_diff_count_value)
        if isinstance(unexpected_diff_count_value, (int, float))
        else 0
    )
    unexpected_diff_regression = (
        unexpected_diff_count > baseline_unexpected_diff_threshold
    )
    if unexpected_diff_regression:
        console.print(
            "[red]unexpected baseline diffs exceed threshold:[/red] "
            f"{unexpected_diff_count} > {baseline_unexpected_diff_threshold}"
        )
        console.print(
            "remediation: review rebuild report `baseline.allowlist_result`, "
            "update config/rebuild.allowlist.yaml for intentional changes, "
            "or regenerate baseline with --write-baseline."
        )
    try:
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        report_payload["regression_gate"] = {
            "baseline_unexpected_diff_count": unexpected_diff_count,
            "baseline_unexpected_diff_threshold": baseline_unexpected_diff_threshold,
            "unexpected_diff_regression": unexpected_diff_regression,
            "fatal_invariant_failure": fatal_invariant_failure,
            "step_failure": report.failed,
        }
        report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass
    if report.failed or fatal_invariant_failure or unexpected_diff_regression:
        if fatal_invariant_failure and not report.failed:
            console.print("[red]Fatal rebuild invariant regression detected.[/red]")
        raise typer.Exit(code=1)


@instance_app.command("validate-spec")
def instance_validate_spec(
    spec: Path = INSTANCE_REBUILD_SPEC_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Validate rebuild-spec structure and required fields for an instance."""
    context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_spec = context.resolve_path(spec)
    try:
        payload = load_rebuild_spec(resolved_spec)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        console.print(f"[red]Invalid rebuild spec:[/red] {resolved_spec}: {exc}")
        raise typer.Exit(code=1) from exc
    issues = validate_rebuild_spec_payload(payload)
    if issues:
        console.print(f"[red]Rebuild spec validation failed:[/red] {resolved_spec}")
        for issue in issues:
            console.print(f"[red]-[/red] {issue}")
        raise typer.Exit(code=1)
    console.print(f"[green]Rebuild spec valid[/green] {resolved_spec}")


@instance_app.command("promote-evidence")
def instance_promote_evidence(
    report: Path | None = INSTANCE_EVIDENCE_REPORT_OPTION,
    output: Path = INSTANCE_EVIDENCE_OUTPUT_OPTION,
    log_dir: Path = INSTANCE_EVIDENCE_LOG_DIR_OPTION,
    max_warn_increase: int | None = INSTANCE_EVIDENCE_MAX_WARN_INCREASE_OPTION,
    max_baseline_diff_increase: int | None = (
        INSTANCE_EVIDENCE_MAX_BASELINE_DIFF_INCREASE_OPTION
    ),
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Promote a rebuild report into normalized release-gate evidence JSON."""
    context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_log_dir = context.resolve_path(log_dir)
    if report is None:
        candidates = sorted(resolved_log_dir.glob("instance_rebuild_report-*.json"))
        if not candidates:
            console.print(f"[red]No rebuild reports found in:[/red] {resolved_log_dir}")
            raise typer.Exit(code=1)
        resolved_report = candidates[-1]
    else:
        resolved_report = context.resolve_path(report)
    resolved_output = context.resolve_path(output)

    try:
        source_payload = json.loads(resolved_report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Invalid rebuild report:[/red] {resolved_report}: {exc}")
        raise typer.Exit(code=1) from exc

    invariant_results = source_payload.get("invariant_results", [])
    pass_count = sum(
        1
        for item in invariant_results
        if isinstance(item, dict) and item.get("status") == "pass"
    )
    warn_count = sum(
        1
        for item in invariant_results
        if isinstance(item, dict) and item.get("status") == "warn"
    )
    fail_count = sum(
        1
        for item in invariant_results
        if isinstance(item, dict) and item.get("status") == "fail"
    )
    metrics = source_payload.get("metrics", {})
    baseline_diff_count = (
        metrics.get("baseline_diff_count") if isinstance(metrics, dict) else None
    )
    regression_gate = source_payload.get("regression_gate", {})
    if not isinstance(regression_gate, dict):
        regression_gate = {}
    diagnostics_payload = source_payload.get("diagnostics", {})
    account_surface_payload = (
        diagnostics_payload.get("account_surface", {})
        if isinstance(diagnostics_payload, dict)
        else {}
    )
    diagnosis_payload = (
        account_surface_payload.get("diagnosis", {})
        if isinstance(account_surface_payload, dict)
        else {}
    )
    total_ok_species_empty_signature = (
        bool(diagnosis_payload.get("total_ok_species_empty_signature", False))
        if isinstance(diagnosis_payload, dict)
        else False
    )
    failed = bool(
        source_payload.get("failed")
        or regression_gate.get("step_failure")
        or regression_gate.get("fatal_invariant_failure")
        or regression_gate.get("unexpected_diff_regression")
    )
    normalized = {
        "report_schema_version": "1.0",
        "instance_id": context.root.name or "instance",
        "run_id": source_payload.get("run_id"),
        "status": "failed" if failed else "ok",
        "report_path": str(resolved_report),
        "regression_gate": {
            "step_failure": bool(regression_gate.get("step_failure", False)),
            "fatal_invariant_failure": bool(
                regression_gate.get("fatal_invariant_failure", False)
            ),
            "unexpected_diff_regression": bool(
                regression_gate.get("unexpected_diff_regression", False)
            ),
            "baseline_unexpected_diff_threshold": regression_gate.get(
                "baseline_unexpected_diff_threshold"
            ),
            "baseline_unexpected_diff_count": regression_gate.get(
                "baseline_unexpected_diff_count"
            ),
        },
        "summary": {
            "invariant_pass_count": pass_count,
            "invariant_warn_count": warn_count,
            "invariant_fail_count": fail_count,
            "baseline_diff_count": baseline_diff_count,
            "account_surface_total_ok_species_empty_signature": (
                total_ok_species_empty_signature
            ),
            "account_surface_species_count": account_surface_payload.get(
                "species_count"
            )
            if isinstance(account_surface_payload, dict)
            else None,
        },
    }
    previous_payload: dict[str, object] | None = None
    if resolved_output.exists():
        try:
            loaded = json.loads(resolved_output.read_text(encoding="utf-8"))
            previous_payload = loaded if isinstance(loaded, dict) else None
        except (OSError, json.JSONDecodeError):
            previous_payload = None

    previous_summary = (
        previous_payload.get("summary", {})
        if isinstance(previous_payload, dict)
        else {}
    )
    if not isinstance(previous_summary, dict):
        previous_summary = {}
    previous_warn_count = int(previous_summary.get("invariant_warn_count", 0) or 0)
    previous_baseline_diff_count = int(
        previous_summary.get("baseline_diff_count", 0) or 0
    )
    current_baseline_diff_count = (
        int(baseline_diff_count) if isinstance(baseline_diff_count, (int, float)) else 0
    )
    warn_increase = warn_count - previous_warn_count
    baseline_diff_increase = current_baseline_diff_count - previous_baseline_diff_count
    trend_warnings: list[str] = []
    if max_warn_increase is not None and warn_increase > max_warn_increase:
        trend_warnings.append(
            f"invariant_warn_count increased by {warn_increase} (> {max_warn_increase})"
        )
    if (
        max_baseline_diff_increase is not None
        and baseline_diff_increase > max_baseline_diff_increase
    ):
        trend_warnings.append(
            "baseline_diff_count increased by "
            f"{baseline_diff_increase} (> {max_baseline_diff_increase})"
        )
    normalized["trend_drift"] = {
        "previous_summary": previous_summary,
        "warn_increase": warn_increase,
        "baseline_diff_increase": baseline_diff_increase,
        "thresholds": {
            "max_warn_increase": max_warn_increase,
            "max_baseline_diff_increase": max_baseline_diff_increase,
        },
        "warnings": trend_warnings,
    }
    try:
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    except OSError as exc:
        console.print(f"[red]Failed writing evidence:[/red] {resolved_output}: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]Promoted rebuild evidence[/green] "
        f"report={resolved_report} output={resolved_output} status={normalized['status']}"
    )
    for warning in trend_warnings:
        console.print(f"[yellow]trend drift warning:[/yellow] {warning}")


@instance_app.command("refresh-reference-evidence")
def instance_refresh_reference_evidence(
    report: Path | None = INSTANCE_EVIDENCE_REPORT_OPTION,
    reference_root: Path = INSTANCE_REFERENCE_ROOT_OPTION,
    max_warn_increase: int | None = INSTANCE_EVIDENCE_MAX_WARN_INCREASE_OPTION,
    max_baseline_diff_increase: int | None = (
        INSTANCE_EVIDENCE_MAX_BASELINE_DIFF_INCREASE_OPTION
    ),
) -> None:
    """Refresh maintainer reference evidence artifact from latest rebuild report."""

    instance_promote_evidence(
        report=report,
        output=Path("evidence/reference_rebuild_report.latest.json"),
        log_dir=Path("vdyp_io/logs"),
        max_warn_increase=max_warn_increase,
        max_baseline_diff_increase=max_baseline_diff_increase,
        instance_root=reference_root,
    )


@instance_app.command("account-surface")
def instance_account_surface(
    config: Path = PATCHWORKS_CONFIG_OPTION,
    output: Path | None = INSTANCE_ACCOUNT_SURFACE_OUTPUT_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Summarize species/AU account coverage from tracks/accounts.csv."""
    context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_config = context.resolve_path(config)
    try:
        runtime_config = load_patchworks_runtime_config(resolved_config)
    except (
        FileNotFoundError,
        PatchworksConfigError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        console.print(f"[red]Patchworks config error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    accounts_csv_path = runtime_config.matrix_output_dir / "accounts.csv"
    if not accounts_csv_path.exists():
        console.print(f"[red]accounts.csv not found:[/red] {accounts_csv_path}")
        raise typer.Exit(code=1)

    summary = summarize_account_surface(
        accounts_csv_path=accounts_csv_path,
        products_csv_path=runtime_config.matrix_output_dir / "products.csv",
        curves_csv_path=runtime_config.matrix_output_dir / "curves.csv",
    )
    if output is not None:
        output_path = context.resolve_path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        console.print(f"summary_json: {output_path}")

    console.print(
        "[green]account surface summary[/green] "
        f"accounts={summary['total_accounts']} "
        f"species={summary['species_count']} "
        f"complete_species={summary['species_complete_count']} "
        f"au={summary['au_count']}"
    )
    if summary["species_missing_yield"]:
        console.print(
            "species_missing_yield: " + ", ".join(summary["species_missing_yield"])
        )
    if summary["species_missing_harvest_cc"]:
        console.print(
            "species_missing_harvest_cc: "
            + ", ".join(summary["species_missing_harvest_cc"])
        )
    diagnosis = summary.get("diagnosis", {})
    if isinstance(diagnosis, dict) and diagnosis.get(
        "total_ok_species_empty_signature"
    ):
        console.print(
            "[red]diagnosis:[/red] detected `total OK, species-wise empty` signature."
        )
        for step in diagnosis.get("recommended_next_checks", []):
            console.print(f"- {step}")


@app.command("run")
def run_all(
    data_root: Path = DATA_ROOT_OPTION,
    output_root: Path = OUTPUT_ROOT_OPTION,
    tsa: list[str] | None = TSA_OPTION,
    resume: bool = RESUME_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    verbose: bool = VERBOSE_OPTION,
    skip_checks: bool = SKIP_CHECKS_OPTION,
    debug_rows: int | None = DEBUG_ROWS_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    log_dir: Path = LOG_DIR_OPTION,
    run_config: Path | None = RUN_CONFIG_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Run the end-to-end data-prep pipeline from current CLI inputs/profile."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_output_root = instance_context.resolve_path(output_root)
    resolved_log_dir = instance_context.resolve_path(log_dir)
    resolved_run_config = (
        instance_context.resolve_path(run_config) if run_config is not None else None
    )

    run_profile = None
    run_config_sha256: str | None = None
    if resolved_run_config is not None:
        try:
            run_profile = load_pipeline_run_profile(resolved_run_config)
            run_config_sha256 = file_sha256(resolved_run_config)
        except (
            FileNotFoundError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            console.print(f"[red]Invalid run config:[/red] {exc}")
            raise typer.Exit(code=1) from exc
    effective = resolve_effective_run_options(
        tsa_list=tsa,
        resume=resume,
        dry_run=dry_run,
        verbose=verbose,
        skip_checks=skip_checks,
        debug_rows=debug_rows,
        run_id=run_id,
        log_dir=resolved_log_dir,
        profile=run_profile,
    )
    if effective.strata_list:
        console.print(
            "[yellow]Warning:[/yellow] run config strata selection is recorded but not "
            "yet wired into legacy execution filtering."
        )
    if data_root != Path("data"):
        console.print(
            "[red]--data-root override is not wired yet; keep default data/ under the "
            "instance root.[/red]"
        )
        raise typer.Exit(code=1)
    if effective.dry_run:
        console.print(
            f"[yellow]Dry run:[/yellow] femic run tsa={effective.tsa_list or 'ALL'} "
            f"resume={effective.resume} debug_rows={effective.debug_rows} "
            f"run_id={effective.run_id or 'AUTO'} log_dir={effective.log_dir}"
        )
        raise typer.Exit()
    if not effective.skip_checks:
        _preflight_checks(
            resume=effective.resume,
            instance_context=instance_context,
        )
    if effective.verbose:
        console.print(
            f"Running legacy pipeline for tsa={effective.tsa_list or 'ALL'} "
            f"(resume={effective.resume}, debug_rows={effective.debug_rows}, "
            f"run_id={effective.run_id or 'AUTO'})"
        )
    pipeline_run_config = build_pipeline_run_config(
        tsa_list=effective.tsa_list,
        resume=effective.resume,
        debug_rows=effective.debug_rows,
        run_id=effective.run_id,
        log_dir=effective.log_dir,
        output_root=resolved_output_root,
        run_config_path=resolved_run_config,
        run_config_sha256=run_config_sha256,
        boundary_path=effective.boundary_path,
        boundary_layer=effective.boundary_layer,
        boundary_code=effective.boundary_code,
        strat_bec_grouping=effective.strat_bec_grouping,
        strat_species_combo_count=effective.strat_species_combo_count,
        strat_include_tm_species2_for_single=(
            effective.strat_include_tm_species2_for_single
        ),
        strat_top_area_coverage=effective.strat_top_area_coverage,
        vdyp_sampling_mode=effective.vdyp_sampling_mode,
        vdyp_two_pass_rebin=effective.vdyp_two_pass_rebin,
        vdyp_min_stands_per_si_bin=effective.vdyp_min_stands_per_si_bin,
        vdyp_toe_shift_years=effective.vdyp_toe_shift_years,
        managed_curve_mode=effective.managed_curve_mode,
        managed_curve_x_scale=effective.managed_curve_x_scale,
        managed_curve_y_scale=effective.managed_curve_y_scale,
        managed_curve_truncate_at_culm=effective.managed_curve_truncate_at_culm,
        managed_curve_max_age=effective.managed_curve_max_age,
        instance_root=instance_context.root,
    )
    manifest_path = run_data_prep(pipeline_run_config)
    console.print(f"Run manifest: {manifest_path}")


@prep_app.command("run")
def prep_run(
    data_root: Path = DATA_ROOT_OPTION,
    output_root: Path = OUTPUT_ROOT_OPTION,
    tsa: list[str] | None = TSA_OPTION,
    resume: bool = RESUME_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    verbose: bool = VERBOSE_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Placeholder prep command retained for CLI compatibility."""
    _ = (data_root, output_root, tsa, resume, dry_run, verbose, instance_root)
    _emit_stub("femic prep run")


@prep_app.command("validate-case")
def prep_validate_case(
    run_config: Path = CASE_RUN_CONFIG_OPTION,
    tipsy_config_dir: Path = CASE_TIPSY_CONFIG_DIR_OPTION,
    strict_warnings: bool = CASE_STRICT_WARNINGS_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Validate run config, case selections, and required input paths."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_run_config = instance_context.resolve_path(run_config)
    resolved_tipsy_config_dir = instance_context.resolve_path(tipsy_config_dir)

    try:
        profile = load_pipeline_run_profile(resolved_run_config)
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        console.print(f"[red]Invalid run config:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    effective = resolve_effective_run_options(
        tsa_list=None,
        resume=False,
        dry_run=False,
        verbose=False,
        skip_checks=False,
        debug_rows=None,
        run_id=None,
        log_dir=Path("vdyp_io/logs"),
        profile=profile,
    )

    _preflight_checks(
        resume=effective.resume,
        instance_context=instance_context,
    )

    errors: list[str] = []
    warnings: list[str] = []
    case_codes: set[str] = set()

    if profile.boundary_path is None and not profile.tsa_list:
        errors.append(
            "Run profile must set either selection.tsa or "
            "selection.boundary_path + selection.boundary_code."
        )

    if profile.boundary_path is not None:
        boundary_path = instance_context.resolve_path(Path(profile.boundary_path))
        if not boundary_path.exists():
            errors.append(
                f"Boundary path does not exist: {boundary_path} "
                "(set selection.boundary_path to an existing geometry file)."
            )
        if not profile.boundary_code:
            errors.append(
                "selection.boundary_code is required when selection.boundary_path is set."
            )
        else:
            case_codes.add(_normalize_case_code(profile.boundary_code))

    if profile.tsa_list:
        case_codes.update(_normalize_case_code(code) for code in profile.tsa_list)

    for code in sorted(case_codes):
        try:
            cfg = load_tipsy_tsa_config(
                tsa_code=code,
                config_dir=resolved_tipsy_config_dir,
            )
        except ValueError as exc:
            errors.append(f"Invalid TIPSY config for {code}: {exc}")
            continue
        if cfg is None:
            expected_yaml = resolved_tipsy_config_dir / f"tsa{code}.yaml"
            expected_yml = resolved_tipsy_config_dir / f"tsa{code}.yml"
            errors.append(
                f"Missing TIPSY config for {code} in {resolved_tipsy_config_dir} "
                f"(expected {expected_yaml.name} or {expected_yml.name})."
            )

    external_paths = resolve_legacy_external_data_paths(
        repo_root=instance_context.root,
        env_override=os.environ.get("FEMIC_EXTERNAL_DATA_ROOT"),
    )
    source_root = _source_tree_root()
    required_external_paths = {
        "VRI source": external_paths.vri_vclr1p_path,
        "VDYP polygon/layer source": external_paths.vdyp_input_pandl_path,
        "TSA boundaries source": external_paths.tsa_boundaries_path,
        "Site productivity source": external_paths.site_prod_bc_gdb_path,
    }
    for label, path in required_external_paths.items():
        if not path.exists():
            errors.append(
                f"Missing {label}: {path} "
                "(set FEMIC_EXTERNAL_DATA_ROOT or restore expected dataset path)."
            )

    annex_errors, annex_warnings = _validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )
    errors.extend(annex_errors)
    warnings.extend(annex_warnings)

    if not resolved_tipsy_config_dir.exists():
        errors.append(
            f"TIPSY config directory does not exist: {resolved_tipsy_config_dir} "
            "(create directory and add tsa*.yaml case configs)."
        )

    if not effective.log_dir.exists():
        warnings.append(
            f"Log directory does not exist yet: {effective.log_dir} "
            "(it will be created during run execution)."
        )

    for message in warnings:
        console.print(f"[yellow]Warning:[/yellow] {message}")

    if errors or (strict_warnings and warnings):
        for message in errors:
            console.print(f"[red]Error:[/red] {message}")
        if strict_warnings and warnings:
            console.print(
                "[red]Error:[/red] strict warning mode enabled and warnings were found."
            )
        raise typer.Exit(code=1)

    targets = ", ".join(sorted(case_codes)) if case_codes else "<none>"
    console.print(
        f"[green]Case preflight passed[/green] run_config={resolved_run_config} "
        f"targets=[{targets}] tipsy_config_dir={resolved_tipsy_config_dir}"
    )


@prep_app.command("geospatial-preflight")
def prep_geospatial_preflight(
    strict_warnings: bool = CASE_STRICT_WARNINGS_OPTION,
    skip_shapefile_smoke: bool = typer.Option(
        False,
        "--skip-shapefile-smoke",
        help="Skip Fiona shapefile read/write smoke test.",
    ),
) -> None:
    """Verify geospatial runtime dependencies and optional shapefile smoke checks."""
    result = run_geospatial_preflight(run_shapefile_smoke=not skip_shapefile_smoke)
    console.print(
        "[green]Geospatial preflight passed[/green] "
        if result.ok and not result.warnings
        else "[yellow]Geospatial preflight completed with findings[/yellow]"
    )
    console.print(f"os_family={result.os_family}")
    if result.gdal_version is not None:
        console.print(f"gdal_version={result.gdal_version}")
    else:
        console.print("gdal_version=unknown")
    console.print(f"install_hint: {result.install_hint}")
    for warning in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")
    for error in result.errors:
        console.print(f"[red]Error:[/red] {error}")
    if result.errors:
        raise typer.Exit(code=1)
    if strict_warnings and result.warnings:
        raise typer.Exit(code=1)


@vdyp_app.command("run")
def vdyp_run(
    data_root: Path = DATA_ROOT_OPTION,
    output_root: Path = OUTPUT_ROOT_OPTION,
    tsa: list[str] | None = TSA_OPTION,
    resume: bool = RESUME_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    verbose: bool = VERBOSE_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Placeholder VDYP command retained for CLI compatibility."""
    _ = (data_root, output_root, tsa, resume, dry_run, verbose, instance_root)
    _emit_stub("femic vdyp run")


@vdyp_app.command("report")
def vdyp_report(
    curve_log: Path = VDYP_CURVE_LOG_OPTION,
    run_log: Path = VDYP_RUN_LOG_OPTION,
    expected_first_age: float = VDYP_EXPECTED_FIRST_AGE_OPTION,
    expected_first_volume: float = VDYP_EXPECTED_FIRST_VOLUME_OPTION,
    tolerance: float = VDYP_TOLERANCE_OPTION,
    mismatch_limit: int = VDYP_MISMATCH_LIMIT_OPTION,
    max_curve_warnings: int | None = VDYP_MAX_CURVE_WARNINGS_OPTION,
    max_first_point_mismatches: int | None = VDYP_MAX_FIRST_POINT_MISMATCHES_OPTION,
    max_curve_parse_errors: int | None = VDYP_MAX_CURVE_PARSE_ERRORS_OPTION,
    max_run_parse_errors: int | None = VDYP_MAX_RUN_PARSE_ERRORS_OPTION,
    min_curve_events: int | None = VDYP_MIN_CURVE_EVENTS_OPTION,
    min_run_events: int | None = VDYP_MIN_RUN_EVENTS_OPTION,
    selection_summary_out: Path | None = VDYP_SELECTION_SUMMARY_OUT_OPTION,
) -> None:
    """Summarize VDYP logs and enforce warning/error budget thresholds."""
    summary = summarize_vdyp_logs(
        curve_log_path=curve_log,
        run_log_path=run_log,
        expected_first_age=expected_first_age,
        expected_first_volume=expected_first_volume,
        tolerance=tolerance,
        mismatch_limit=mismatch_limit,
    )
    console.print(f"Curve events: {summary.curve_events} ({curve_log})")
    console.print(f"Curve parse errors: {summary.curve_parse_errors}")
    console.print(f"Curve status counts: {summary.curve_status_counts}")
    console.print(f"Curve stage counts: {summary.curve_stage_counts}")
    console.print(f"Curve TSA counts: {summary.curve_tsa_counts}")
    console.print(f"Curve warning events: {summary.curve_warning_events}")
    console.print(
        "First-point checks: "
        f"events={summary.first_point_events} "
        f"matches={summary.first_point_matches} "
        f"mismatches={summary.first_point_mismatches}"
    )
    if summary.first_point_mismatch_rows:
        console.print("First-point mismatches (limited):")
        for mismatch_row in summary.first_point_mismatch_rows:
            context = mismatch_row.get("context")
            if not isinstance(context, dict):
                context = {}
            console.print(
                f"- tsa={context.get('tsa')} stratum={context.get('stratum_code')} "
                f"si={context.get('si_level')} "
                f"first_age={mismatch_row.get('first_age')} "
                f"first_volume={mismatch_row.get('first_volume')} "
                f"status={mismatch_row.get('status')} "
                f"stage={mismatch_row.get('stage')}"
            )

    console.print(f"Run events: {summary.run_events} ({run_log})")
    console.print(f"Run parse errors: {summary.run_parse_errors}")
    console.print(f"Run status counts: {summary.run_status_counts}")
    console.print(f"Run phase counts: {summary.run_phase_counts}")
    console.print(f"Run TSA counts: {summary.run_tsa_counts}")

    selection_rows = summarize_curve_selection_rows(curve_log_path=curve_log)
    selected_path_counts: dict[str, int] = {}
    for selection_row in selection_rows:
        selected_path_counts[selection_row.selected_path] = (
            selected_path_counts.get(selection_row.selected_path, 0) + 1
        )
    console.print(f"Curve selection rows: {len(selection_rows)}")
    if selected_path_counts:
        console.print(
            f"Selected-path counts: {dict(sorted(selected_path_counts.items()))}"
        )
    if selection_summary_out is not None:
        selection_summary_out.parent.mkdir(parents=True, exist_ok=True)
        with selection_summary_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "tsa",
                    "stratum_code",
                    "si_level",
                    "selected_path",
                    "fit_quality_gate_failed",
                    "left_toe_censor_selected",
                    "merchantable_floor_selected",
                    "tail_blend_selected",
                ],
            )
            writer.writeheader()
            for selection_row in selection_rows:
                writer.writerow(
                    {
                        "tsa": selection_row.tsa,
                        "stratum_code": selection_row.stratum_code,
                        "si_level": selection_row.si_level,
                        "selected_path": selection_row.selected_path,
                        "fit_quality_gate_failed": selection_row.fit_quality_gate_failed,
                        "left_toe_censor_selected": selection_row.left_toe_censor_selected,
                        "merchantable_floor_selected": selection_row.merchantable_floor_selected,
                        "tail_blend_selected": selection_row.tail_blend_selected,
                    }
                )
        console.print(f"Selection summary CSV: {selection_summary_out}")

    budget = VdypWarningBudget(
        max_curve_warnings=max_curve_warnings,
        max_first_point_mismatches=max_first_point_mismatches,
        max_curve_parse_errors=max_curve_parse_errors,
        max_run_parse_errors=max_run_parse_errors,
        min_curve_events=min_curve_events,
        min_run_events=min_run_events,
    )
    violations = evaluate_warning_budget(summary, budget)
    if violations:
        console.print("[red]VDYP warning-budget violations:[/red]")
        for violation in violations:
            console.print(f"- {violation}")
        raise typer.Exit(code=1)


@tsa_app.command("run")
def tsa_run(
    data_root: Path = DATA_ROOT_OPTION,
    output_root: Path = OUTPUT_ROOT_OPTION,
    tsa: list[str] | None = TSA_OPTION,
    resume: bool = RESUME_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    verbose: bool = VERBOSE_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Placeholder TSA command retained for CLI compatibility."""
    _ = (data_root, output_root, tsa, resume, dry_run, verbose, instance_root)
    _emit_stub("femic tsa run")


@tsa_app.command("post-tipsy")
def tsa_post_tipsy(
    tsa: list[str] | None = TSA_OPTION,
    verbose: bool = VERBOSE_OPTION,
    run_id: str | None = RUN_ID_OPTION,
    log_dir: Path = LOG_DIR_OPTION,
    run_config: Path | None = RUN_CONFIG_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Build post-TIPSY bundle tables for selected TSA/case targets."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_log_dir = instance_context.resolve_path(Path(log_dir))
    resolved_run_config = (
        instance_context.resolve_path(run_config) if run_config is not None else None
    )
    run_profile = None
    if resolved_run_config is not None:
        try:
            run_profile = load_pipeline_run_profile(resolved_run_config)
        except (
            FileNotFoundError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            console.print(f"[red]Invalid run config:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    targets_raw = tsa if tsa else (run_profile.tsa_list if run_profile else [])
    targets = [str(v).zfill(2) for v in targets_raw] if targets_raw else []
    if not targets:
        console.print(
            "[red]Provide at least one TSA via --tsa or selection.tsa in --run-config "
            "for post-tipsy.[/red]"
        )
        raise typer.Exit(code=1)
    effective_run_id = (
        run_id
        if run_id is not None
        else (run_profile.run_id if run_profile is not None else None)
    )
    effective_verbose = verbose or (
        run_profile.verbose if run_profile is not None else False
    )
    effective_log_dir = (
        instance_context.resolve_path(run_profile.log_dir)
        if (
            run_profile is not None
            and Path(log_dir) == Path("vdyp_io/logs")
            and run_profile.log_dir is not None
        )
        else resolved_log_dir
    )
    run_result = run_post_tipsy_bundle_with_manifest(
        tsa_list=targets,
        run_id=effective_run_id,
        log_dir=effective_log_dir,
        repo_root=instance_context.root,
        data_root=(instance_context.root / "data"),
        message_fn=console.print
        if effective_verbose
        else (lambda *_args, **_kwargs: None),
        managed_curve_mode=(
            run_profile.managed_curve_mode if run_profile is not None else None
        ),
        managed_curve_x_scale=(
            run_profile.managed_curve_x_scale if run_profile is not None else None
        ),
        managed_curve_y_scale=(
            run_profile.managed_curve_y_scale if run_profile is not None else None
        ),
        managed_curve_truncate_at_culm=(
            run_profile.managed_curve_truncate_at_culm
            if run_profile is not None
            else None
        ),
        managed_curve_max_age=(
            run_profile.managed_curve_max_age if run_profile is not None else None
        ),
    )
    result = run_result.result
    console.print(
        f"[green]post-tipsy completed[/green] tsa={result.tsa_list} "
        f"au_rows={result.au_rows} curves={result.curve_rows} "
        f"curve_points={result.curve_points_rows}"
    )
    console.print(f"Run manifest: {run_result.manifest_path}")
    console.print(f"au_table: {result.au_table_path}")
    console.print(f"curve_table: {result.curve_table_path}")
    console.print(f"curve_points_table: {result.curve_points_table_path}")


@tipsy_app.command("validate")
def tipsy_validate(
    config_dir: Path = typer.Option(
        Path("config/tipsy"),
        "--config-dir",
        help="Directory containing tsaXX.yaml files.",
    ),
    tsa: list[str] | None = TSA_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Validate per-TSA TIPSY YAML config availability and parseability."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_config_dir = instance_context.resolve_path(config_dir)
    found = discover_tipsy_config_tsas(resolved_config_dir)
    if not found:
        console.print(f"[red]No TIPSY configs found in {resolved_config_dir}[/red]")
        raise typer.Exit(code=1)
    targets = sorted({str(v).zfill(2) for v in tsa}) if tsa else sorted(found.keys())
    missing = [code for code in targets if code not in found]
    if missing:
        console.print(f"[red]Missing TSA config files:[/red] {', '.join(missing)}")
        raise typer.Exit(code=1)
    for code in targets:
        load_tipsy_tsa_config(tsa_code=code, config_dir=resolved_config_dir)
    console.print(
        f"[green]Validated TIPSY configs:[/green] {', '.join(targets)} "
        f"(dir={resolved_config_dir})"
    )


@export_app.command("patchworks")
def export_patchworks(
    tsa: list[str] | None = TSA_OPTION,
    bundle_dir: Path = EXPORT_BUNDLE_DIR_OPTION,
    checkpoint: Path = EXPORT_CHECKPOINT_OPTION,
    output_dir: Path = EXPORT_OUTPUT_DIR_OPTION,
    start_year: int = EXPORT_START_YEAR_OPTION,
    horizon_years: int = EXPORT_HORIZON_YEARS_OPTION,
    cc_min_age: int = EXPORT_CC_MIN_AGE_OPTION,
    cc_max_age: int = EXPORT_CC_MAX_AGE_OPTION,
    cc_transition_ifm: str | None = EXPORT_CC_TRANSITION_IFM_OPTION,
    fragments_crs: str = EXPORT_FRAGMENTS_CRS_OPTION,
    ifm_source_col: str | None = EXPORT_IFM_SOURCE_COL_OPTION,
    ifm_threshold: float | None = EXPORT_IFM_THRESHOLD_OPTION,
    ifm_target_managed_share: float | None = (EXPORT_IFM_TARGET_MANAGED_SHARE_OPTION),
    seral_stage_config: Path | None = EXPORT_SERAL_STAGE_CONFIG_OPTION,
    silviculture_config: Path | None = EXPORT_SILVICULTURE_CONFIG_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Export a Patchworks model package for the selected TSA/case targets."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_bundle_dir = instance_context.resolve_path(bundle_dir)
    resolved_checkpoint = instance_context.resolve_path(checkpoint)
    resolved_output_dir = instance_context.resolve_path(output_dir)
    resolved_seral_stage_config = (
        instance_context.resolve_path(seral_stage_config)
        if isinstance(seral_stage_config, Path)
        else None
    )
    resolved_silviculture_config = (
        instance_context.resolve_path(silviculture_config)
        if isinstance(silviculture_config, Path)
        else None
    )
    targets = (
        [str(v).zfill(2) if str(v).isdigit() else str(v).lower() for v in tsa]
        if tsa
        else []
    )
    if not targets:
        console.print(
            "[red]Provide at least one TSA via --tsa for patchworks export.[/red]"
        )
        raise typer.Exit(code=1)
    try:
        result = export_patchworks_package(
            bundle_dir=resolved_bundle_dir,
            checkpoint_path=resolved_checkpoint,
            output_dir=resolved_output_dir,
            tsa_list=targets,
            start_year=start_year,
            horizon_years=horizon_years,
            cc_min_age=cc_min_age,
            cc_max_age=cc_max_age,
            cc_transition_ifm=cc_transition_ifm,
            fragments_crs=fragments_crs,
            ifm_source_col=ifm_source_col,
            ifm_threshold=ifm_threshold,
            ifm_target_managed_share=ifm_target_managed_share,
            seral_stage_config_path=resolved_seral_stage_config,
            silviculture_config_path=resolved_silviculture_config,
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Patchworks export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]patchworks export completed[/green] "
        f"tsa={result.tsa_list} au={result.au_count} "
        f"fragments={result.fragment_count} curves={result.curve_count}"
    )
    console.print(f"forestmodel_xml: {result.forestmodel_xml_path}")
    console.print(f"fragments_shp: {result.fragments_shapefile_path}")


@export_app.command("woodstock")
def export_woodstock(
    tsa: list[str] | None = TSA_OPTION,
    bundle_dir: Path = EXPORT_BUNDLE_DIR_OPTION,
    checkpoint: Path = EXPORT_CHECKPOINT_OPTION,
    output_dir: Path = EXPORT_WOODSTOCK_OUTPUT_DIR_OPTION,
    cc_min_age: int = EXPORT_CC_MIN_AGE_OPTION,
    cc_max_age: int = EXPORT_CC_MAX_AGE_OPTION,
    fragments_crs: str = EXPORT_FRAGMENTS_CRS_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Export Woodstock CSV artifacts for the selected TSA/case targets."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_bundle_dir = instance_context.resolve_path(bundle_dir)
    resolved_checkpoint = instance_context.resolve_path(checkpoint)
    resolved_output_dir = instance_context.resolve_path(output_dir)
    targets = (
        [str(v).zfill(2) if str(v).isdigit() else str(v).lower() for v in tsa]
        if tsa
        else []
    )
    if not targets:
        console.print(
            "[red]Provide at least one TSA via --tsa for woodstock export.[/red]"
        )
        raise typer.Exit(code=1)
    try:
        result = export_woodstock_package(
            bundle_dir=resolved_bundle_dir,
            checkpoint_path=resolved_checkpoint,
            output_dir=resolved_output_dir,
            tsa_list=targets,
            cc_min_age=cc_min_age,
            cc_max_age=cc_max_age,
            fragments_crs=fragments_crs,
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Woodstock export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]woodstock export completed[/green] "
        f"tsa={result.tsa_list} yield_rows={result.yield_rows} "
        f"area_rows={result.area_rows} action_rows={result.action_rows} "
        f"transition_rows={result.transition_rows}"
    )
    console.print(f"yields_csv: {result.yields_csv_path}")
    console.print(f"areas_csv: {result.areas_csv_path}")
    console.print(f"actions_csv: {result.actions_csv_path}")
    console.print(f"transitions_csv: {result.transitions_csv_path}")


@export_app.command("release")
def export_release(
    case_id: str | None = EXPORT_RELEASE_CASE_ID_OPTION,
    output_root: Path = EXPORT_RELEASE_OUTPUT_ROOT_OPTION,
    bundle_dir: Path = EXPORT_BUNDLE_DIR_OPTION,
    patchworks_dir: Path = EXPORT_RELEASE_PATCHWORKS_DIR_OPTION,
    woodstock_dir: Path | None = EXPORT_RELEASE_WOODSTOCK_DIR_OPTION,
    logs_dir: Path = EXPORT_RELEASE_LOGS_DIR_OPTION,
    run_id: str | None = EXPORT_RELEASE_RUN_ID_OPTION,
    strict: bool = EXPORT_RELEASE_STRICT_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Assemble and validate a user-facing release bundle."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    effective_case_id = case_id.strip() if case_id and case_id.strip() else "case"
    resolved_output_root = instance_context.resolve_path(output_root)
    resolved_bundle_dir = instance_context.resolve_path(bundle_dir)
    resolved_patchworks_dir = instance_context.resolve_path(patchworks_dir)
    resolved_woodstock_dir = (
        instance_context.resolve_path(woodstock_dir)
        if woodstock_dir is not None
        else None
    )
    resolved_logs_dir = instance_context.resolve_path(logs_dir)
    try:
        result = build_release_package(
            case_id=effective_case_id,
            output_root=resolved_output_root,
            model_input_bundle_dir=resolved_bundle_dir,
            patchworks_output_dir=resolved_patchworks_dir,
            woodstock_output_dir=resolved_woodstock_dir,
            logs_dir=resolved_logs_dir,
            run_id=run_id,
            strict=strict,
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Release package build failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]release package built[/green] id={result.release_id} "
        f"dir={result.release_dir}"
    )
    console.print(f"manifest: {result.manifest_path}")
    console.print(f"handoff_notes: {result.handoff_notes_path}")


@export_app.command("dual")
def export_dual(
    tsa: list[str] | None = TSA_OPTION,
    bundle_dir: Path = EXPORT_BUNDLE_DIR_OPTION,
    checkpoint: Path = EXPORT_CHECKPOINT_OPTION,
    patchworks_output_dir: Path = EXPORT_DUAL_PATCHWORKS_OUTPUT_DIR_OPTION,
    woodstock_output_dir: Path = EXPORT_DUAL_WOODSTOCK_OUTPUT_DIR_OPTION,
    start_year: int = EXPORT_START_YEAR_OPTION,
    horizon_years: int = EXPORT_HORIZON_YEARS_OPTION,
    cc_min_age: int = EXPORT_CC_MIN_AGE_OPTION,
    cc_max_age: int = EXPORT_CC_MAX_AGE_OPTION,
    cc_transition_ifm: str | None = EXPORT_CC_TRANSITION_IFM_OPTION,
    fragments_crs: str = EXPORT_FRAGMENTS_CRS_OPTION,
    ifm_source_col: str | None = EXPORT_IFM_SOURCE_COL_OPTION,
    ifm_threshold: float | None = EXPORT_IFM_THRESHOLD_OPTION,
    ifm_target_managed_share: float | None = (EXPORT_IFM_TARGET_MANAGED_SHARE_OPTION),
    seral_stage_config: Path | None = EXPORT_SERAL_STAGE_CONFIG_OPTION,
    silviculture_config: Path | None = EXPORT_SILVICULTURE_CONFIG_OPTION,
    with_ws3_smoke: bool = EXPORT_DUAL_WITH_WS3_SMOKE_OPTION,
    ws3_command: str | None = EXPORT_DUAL_WS3_COMMAND_OPTION,
    ws3_workdir: Path | None = EXPORT_DUAL_WS3_WORKDIR_OPTION,
    ws3_report: Path = EXPORT_DUAL_WS3_REPORT_OPTION,
    ws3_require_command: bool = EXPORT_DUAL_WS3_REQUIRE_COMMAND_OPTION,
    ws3_timeout_seconds: int = EXPORT_DUAL_WS3_TIMEOUT_OPTION,
    ws3_repo_path: Path | None = EXPORT_DUAL_WS3_REPO_PATH_OPTION,
    ws3_builtin_smoke: bool = EXPORT_DUAL_WS3_BUILTIN_SMOKE_OPTION,
    ws3_bridge_dir: Path | None = EXPORT_DUAL_WS3_BRIDGE_DIR_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Export both Patchworks and Woodstock artifacts, then optionally run ws3 smoke."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_bundle_dir = instance_context.resolve_path(bundle_dir)
    resolved_checkpoint = instance_context.resolve_path(checkpoint)
    resolved_patchworks_output_dir = instance_context.resolve_path(
        patchworks_output_dir
    )
    resolved_woodstock_output_dir = instance_context.resolve_path(woodstock_output_dir)
    resolved_seral_stage_config = (
        instance_context.resolve_path(seral_stage_config)
        if isinstance(seral_stage_config, Path)
        else None
    )
    resolved_silviculture_config = (
        instance_context.resolve_path(silviculture_config)
        if isinstance(silviculture_config, Path)
        else None
    )
    resolved_ws3_report = instance_context.resolve_path(ws3_report)
    resolved_ws3_workdir = (
        instance_context.resolve_path(ws3_workdir)
        if isinstance(ws3_workdir, Path)
        else None
    )
    resolved_ws3_repo_path = (
        instance_context.resolve_path(ws3_repo_path)
        if isinstance(ws3_repo_path, Path)
        else None
    )
    resolved_ws3_bridge_dir = (
        instance_context.resolve_path(ws3_bridge_dir)
        if isinstance(ws3_bridge_dir, Path)
        else None
    )
    targets = (
        [str(v).zfill(2) if str(v).isdigit() else str(v).lower() for v in tsa]
        if tsa
        else []
    )
    if not targets:
        console.print("[red]Provide at least one TSA via --tsa for dual export.[/red]")
        raise typer.Exit(code=1)

    try:
        patchworks_result = export_patchworks_package(
            bundle_dir=resolved_bundle_dir,
            checkpoint_path=resolved_checkpoint,
            output_dir=resolved_patchworks_output_dir,
            tsa_list=targets,
            start_year=start_year,
            horizon_years=horizon_years,
            cc_min_age=cc_min_age,
            cc_max_age=cc_max_age,
            cc_transition_ifm=cc_transition_ifm,
            fragments_crs=fragments_crs,
            ifm_source_col=ifm_source_col,
            ifm_threshold=ifm_threshold,
            ifm_target_managed_share=ifm_target_managed_share,
            seral_stage_config_path=resolved_seral_stage_config,
            silviculture_config_path=resolved_silviculture_config,
        )
        woodstock_result = export_woodstock_package(
            bundle_dir=resolved_bundle_dir,
            checkpoint_path=resolved_checkpoint,
            output_dir=resolved_woodstock_output_dir,
            tsa_list=targets,
            cc_min_age=cc_min_age,
            cc_max_age=cc_max_age,
            fragments_crs=fragments_crs,
        )
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]Dual export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]dual export completed[/green] "
        f"tsa={patchworks_result.tsa_list} "
        f"patchworks_curves={patchworks_result.curve_count} "
        f"woodstock_yields={woodstock_result.yield_rows}"
    )
    console.print(
        f"patchworks_forestmodel_xml: {patchworks_result.forestmodel_xml_path}"
    )
    console.print(f"woodstock_yields_csv: {woodstock_result.yields_csv_path}")

    if with_ws3_smoke:
        smoke = run_ws3_smoke(
            woodstock_dir=resolved_woodstock_output_dir,
            output_path=resolved_ws3_report,
            ws3_command=ws3_command,
            ws3_workdir=resolved_ws3_workdir,
            timeout_seconds=ws3_timeout_seconds,
            require_command=ws3_require_command,
            ws3_repo_path=resolved_ws3_repo_path,
            run_builtin_model_smoke=ws3_builtin_smoke,
            ws3_bridge_dir=resolved_ws3_bridge_dir,
        )
        if smoke.status == "ok":
            console.print(
                f"[green]ws3 smoke ok[/green] report={resolved_ws3_report} "
                f"message={smoke.message}"
            )
        elif smoke.status == "warn":
            console.print(
                f"[yellow]ws3 smoke warning[/yellow] report={resolved_ws3_report} "
                f"message={smoke.message}"
            )
        else:
            console.print(
                f"[red]ws3 smoke failed[/red] report={resolved_ws3_report} "
                f"message={smoke.message}"
            )
            raise typer.Exit(code=1)


@instance_app.command("ws3-smoke")
def instance_ws3_smoke(
    woodstock_dir: Path = INSTANCE_WS3_SMOKE_WOODSTOCK_DIR_OPTION,
    output: Path = INSTANCE_WS3_SMOKE_OUTPUT_OPTION,
    ws3_command: str | None = INSTANCE_WS3_SMOKE_COMMAND_OPTION,
    ws3_workdir: Path | None = INSTANCE_WS3_SMOKE_WORKDIR_OPTION,
    require_command: bool = INSTANCE_WS3_SMOKE_REQUIRE_COMMAND_OPTION,
    timeout_seconds: int = INSTANCE_WS3_SMOKE_TIMEOUT_OPTION,
    ws3_repo_path: Path | None = INSTANCE_WS3_SMOKE_REPO_PATH_OPTION,
    builtin_model_smoke: bool = INSTANCE_WS3_SMOKE_BUILTIN_OPTION,
    ws3_bridge_dir: Path | None = INSTANCE_WS3_SMOKE_BRIDGE_DIR_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Run ws3 smoke validation for Woodstock outputs and emit a JSON report."""
    context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_woodstock_dir = context.resolve_path(woodstock_dir)
    resolved_output = context.resolve_path(output)
    resolved_ws3_workdir = (
        context.resolve_path(ws3_workdir) if isinstance(ws3_workdir, Path) else None
    )
    resolved_ws3_repo_path = (
        context.resolve_path(ws3_repo_path) if isinstance(ws3_repo_path, Path) else None
    )
    resolved_ws3_bridge_dir = (
        context.resolve_path(ws3_bridge_dir)
        if isinstance(ws3_bridge_dir, Path)
        else None
    )
    result = run_ws3_smoke(
        woodstock_dir=resolved_woodstock_dir,
        output_path=resolved_output,
        ws3_command=ws3_command,
        ws3_workdir=resolved_ws3_workdir,
        timeout_seconds=timeout_seconds,
        require_command=require_command,
        ws3_repo_path=resolved_ws3_repo_path,
        run_builtin_model_smoke=builtin_model_smoke,
        ws3_bridge_dir=resolved_ws3_bridge_dir,
    )
    color = "green" if result.status == "ok" else "yellow"
    if result.status == "failed":
        color = "red"
    console.print(
        f"[{color}]ws3 smoke {result.status}[/{color}] "
        f"rows(y/a/ac/t)=({result.yields_rows}/{result.areas_rows}/"
        f"{result.actions_rows}/{result.transitions_rows}) "
        f"report={resolved_output}"
    )
    console.print(result.message)
    if result.status == "failed":
        raise typer.Exit(code=1)


@patchworks_app.command("preflight")
def patchworks_preflight(
    config: Path = PATCHWORKS_CONFIG_OPTION,
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Run Patchworks runtime preflight checks from a config file."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_config = instance_context.resolve_path(config)
    try:
        runtime_config = load_patchworks_runtime_config(resolved_config)
    except (
        FileNotFoundError,
        PatchworksConfigError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        console.print(f"[red]Patchworks config error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    result = run_patchworks_preflight(config=runtime_config)

    for message in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {message}")
    if result.errors:
        for message in result.errors:
            console.print(f"[red]Error:[/red] {message}")
        raise typer.Exit(code=1)

    console.print(
        "[green]Patchworks preflight passed[/green] "
        f"jar={runtime_config.jar_path} "
        f"launcher={result.launcher_executable} "
        f"license={runtime_config.license_env}={runtime_config.license_value} "
        f"spshome={runtime_config.spshome}"
    )
    if result.license_host:
        console.print(f"license_host={result.license_host}")


@patchworks_app.command("matrix-build")
def patchworks_matrix_build(
    config: Path = PATCHWORKS_CONFIG_OPTION,
    log_dir: Path = PATCHWORKS_LOG_DIR_OPTION,
    run_id: str | None = PATCHWORKS_RUN_ID_OPTION,
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Launch Patchworks app chooser instead of direct Matrix Builder invocation.",
    ),
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Run Patchworks matrix-builder and emit logs/manifests."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_config = instance_context.resolve_path(config)
    resolved_log_dir = instance_context.resolve_path(log_dir)
    try:
        runtime_config = load_patchworks_runtime_config(resolved_config)
        result = run_patchworks_command(
            config=runtime_config,
            interactive=interactive,
            log_dir=resolved_log_dir,
            run_id=run_id,
        )
    except (
        FileNotFoundError,
        PatchworksConfigError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        console.print(f"[red]Patchworks runtime failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    mode = "appchooser" if interactive else "matrix-builder"
    console.print(
        f"[green]Patchworks {mode} run complete[/green] "
        f"run_id={result.run_id} returncode={result.returncode}"
    )
    console.print(f"command: {format_command_for_display(result.command)}")
    console.print(f"stdout_log: {result.stdout_log_path}")
    console.print(f"stderr_log: {result.stderr_log_path}")
    console.print(f"manifest: {result.manifest_path}")
    if not interactive:
        try:
            manifest_payload = json.loads(
                result.manifest_path.read_text(encoding="utf-8")
            )
            accounts_sync = manifest_payload.get("accounts_sync", {})
            if isinstance(accounts_sync, dict):
                status = str(accounts_sync.get("status", "")).strip()
                if status == "synced":
                    console.print(
                        "accounts_sync: synced "
                        f"proto={accounts_sync.get('protoaccounts_path')} "
                        f"accounts={accounts_sync.get('accounts_path')} "
                        f"backup={accounts_sync.get('backup_path')}"
                    )
                elif status:
                    console.print(f"accounts_sync: {status}")
        except (OSError, json.JSONDecodeError):
            pass
    for failure in result.failures:
        console.print(f"[red]Runtime failure:[/red] {failure}")
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


@patchworks_app.command("build-blocks")
def patchworks_build_blocks(
    config: Path = PATCHWORKS_CONFIG_OPTION,
    model_dir: Path | None = PATCHWORKS_MODEL_DIR_OPTION,
    fragments_shp: Path | None = PATCHWORKS_FRAGMENTS_SHP_OPTION,
    topology_radius: float = PATCHWORKS_TOPOLOGY_RADIUS_OPTION,
    topology_backend: PatchworksTopologyBackend = PATCHWORKS_TOPOLOGY_BACKEND_OPTION,
    with_topology: bool = typer.Option(
        True,
        "--with-topology/--no-topology",
        help="Write blocks/topology_blocks_<radius>r.csv alongside blocks.shp.",
    ),
    instance_root: Path | None = INSTANCE_ROOT_OPTION,
) -> None:
    """Generate model-local Patchworks blocks (and optional topology) artifacts."""
    instance_context = _resolve_cli_instance_context(instance_root=instance_root)
    resolved_config = instance_context.resolve_path(config)
    resolved_model_dir = (
        instance_context.resolve_path(model_dir) if model_dir is not None else None
    )
    resolved_fragments_shp = (
        instance_context.resolve_path(fragments_shp)
        if fragments_shp is not None
        else None
    )
    try:
        runtime_config = load_patchworks_runtime_config(resolved_config)
        result = build_patchworks_blocks_dataset(
            config=runtime_config,
            model_dir=resolved_model_dir,
            fragments_shapefile_path=resolved_fragments_shp,
            topology_radius_m=topology_radius,
            build_topology=with_topology,
            topology_backend=topology_backend,
        )
    except (
        FileNotFoundError,
        ModuleNotFoundError,
        PatchworksConfigError,
        json.JSONDecodeError,
        yaml.YAMLError,
    ) as exc:
        console.print(f"[red]Patchworks block build failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        "[green]Patchworks blocks build complete[/green] "
        f"model_dir={result.model_dir} blocks={result.block_count}"
    )
    console.print(
        f"blocks_shapefile: {result.blocks_shapefile_path} "
        f"(BLOCK <- {result.stand_id_field})"
    )
    if result.topology_csv_path is not None:
        console.print(
            "topology_csv: "
            f"{result.topology_csv_path} edges={result.topology_edge_count} "
            f"radius={result.topology_radius_m} backend={topology_backend}"
        )


app.add_typer(prep_app, name="prep")
app.add_typer(vdyp_app, name="vdyp")
app.add_typer(tsa_app, name="tsa")
app.add_typer(tipsy_app, name="tipsy")
app.add_typer(export_app, name="export")
app.add_typer(patchworks_app, name="patchworks")
app.add_typer(instance_app, name="instance")
