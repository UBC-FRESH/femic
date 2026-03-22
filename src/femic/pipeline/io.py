"""I/O-oriented helpers shared across pipeline entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tomllib
from typing import Callable, Iterable, Mapping, Sequence
import uuid

import yaml


DEFAULT_DEV_CONFIG_PATH = Path("config/dev.toml")
FALLBACK_DEFAULT_TSA_LIST = ["08"]
DEFAULT_RUN_CONFIG_PATH = Path("config/run_profile.yaml")
DEFAULT_LEGACY_VRI_RELATIVE_PATHS: tuple[Path, ...] = (
    Path("bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb"),
    Path("bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb"),
)
DEFAULT_LEGACY_VDYP_INPUT_RELATIVE_PATHS: tuple[Path, ...] = (
    Path("bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb"),
    Path("bc/vri/2019/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"),
    Path("VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb"),
)


def load_default_tsa_list(config_path: Path = DEFAULT_DEV_CONFIG_PATH) -> list[str]:
    """Load default TSA list from a dev-facing TOML config file."""
    if not config_path.exists():
        return FALLBACK_DEFAULT_TSA_LIST.copy()
    try:
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return FALLBACK_DEFAULT_TSA_LIST.copy()
    run_cfg = parsed.get("run", {})
    if not isinstance(run_cfg, dict):
        return FALLBACK_DEFAULT_TSA_LIST.copy()
    default_tsa_list = run_cfg.get("default_tsa_list")
    if not isinstance(default_tsa_list, list) or not default_tsa_list:
        return FALLBACK_DEFAULT_TSA_LIST.copy()
    return [str(tsa).zfill(2) for tsa in default_tsa_list]


def normalize_tsa_list(
    tsa_list: Iterable[str] | None, *, default_tsa_list: Iterable[str] | None = None
) -> list[str]:
    """Return zero-padded TSA codes, defaulting to configured dev defaults."""
    if not tsa_list:
        if default_tsa_list is None:
            return load_default_tsa_list()
        return [str(tsa).zfill(2) for tsa in default_tsa_list]
    return [str(tsa).zfill(2) for tsa in tsa_list]


def build_ria_vri_checkpoint_paths(
    *,
    output_root: str | Path = "data",
    count: int = 8,
    stem_prefix: str = "ria_vri_vclr1p_checkpoint",
    suffix: str = ".feather",
) -> dict[int, Path]:
    """Build ordered legacy VRI checkpoint artifact paths."""
    root = Path(output_root)
    return {
        idx: root / f"{stem_prefix}{idx}{suffix}" for idx in range(1, int(count) + 1)
    }


@dataclass(frozen=True)
class RunPaths:
    """Resolved filesystem roots used by the legacy workflow wrapper."""

    repo_root: Path
    script_path: Path
    log_dir: Path


@dataclass(frozen=True)
class PipelineRunConfig:
    """Explicit run configuration passed from CLI into workflow wrappers."""

    tsa_list: list[str]
    resume: bool
    debug_rows: int | None = None
    run_id: str | None = None
    log_dir: Path | None = None
    output_root: Path = Path("outputs")
    run_config_path: Path | None = None
    run_config_sha256: str | None = None
    boundary_path: Path | None = None
    boundary_layer: str | None = None
    boundary_code: str | None = None
    strat_bec_grouping: str | None = None
    strat_species_combo_count: int | None = None
    strat_include_tm_species2_for_single: bool | None = None
    strat_top_area_coverage: float | None = None
    vdyp_sampling_mode: str | int | None = None
    vdyp_two_pass_rebin: bool | None = None
    vdyp_min_stands_per_si_bin: int | None = None
    vdyp_toe_shift_years: float | None = None
    managed_curve_mode: str | None = None
    managed_curve_x_scale: float | None = None
    managed_curve_y_scale: float | None = None
    managed_curve_truncate_at_culm: bool | None = None
    managed_curve_max_age: int | None = None
    instance_root: Path | None = None


@dataclass(frozen=True)
class PipelineRunProfile:
    """Config-file driven run profile for selecting TSAs/strata and mode flags."""

    tsa_list: list[str] | None = None
    strata_list: list[str] | None = None
    resume: bool = False
    dry_run: bool = False
    verbose: bool = False
    skip_checks: bool = False
    debug_rows: int | None = None
    run_id: str | None = None
    log_dir: Path | None = None
    boundary_path: Path | None = None
    boundary_layer: str | None = None
    boundary_code: str | None = None
    strat_bec_grouping: str | None = None
    strat_species_combo_count: int | None = None
    strat_include_tm_species2_for_single: bool | None = None
    strat_top_area_coverage: float | None = None
    vdyp_sampling_mode: str | int | None = None
    vdyp_two_pass_rebin: bool | None = None
    vdyp_min_stands_per_si_bin: int | None = None
    vdyp_toe_shift_years: float | None = None
    managed_curve_mode: str | None = None
    managed_curve_x_scale: float | None = None
    managed_curve_y_scale: float | None = None
    managed_curve_truncate_at_culm: bool | None = None
    managed_curve_max_age: int | None = None


@dataclass(frozen=True)
class EffectiveRunOptions:
    """Resolved run options after merging CLI values with optional profile config."""

    tsa_list: list[str]
    strata_list: list[str]
    resume: bool
    dry_run: bool
    verbose: bool
    skip_checks: bool
    debug_rows: int | None
    run_id: str | None
    log_dir: Path
    boundary_path: Path | None
    boundary_layer: str | None
    boundary_code: str | None
    strat_bec_grouping: str | None
    strat_species_combo_count: int | None
    strat_include_tm_species2_for_single: bool | None
    strat_top_area_coverage: float | None
    vdyp_sampling_mode: str | int | None
    vdyp_two_pass_rebin: bool | None
    vdyp_min_stands_per_si_bin: int | None
    vdyp_toe_shift_years: float | None
    managed_curve_mode: str | None
    managed_curve_x_scale: float | None
    managed_curve_y_scale: float | None
    managed_curve_truncate_at_culm: bool | None
    managed_curve_max_age: int | None


@dataclass(frozen=True)
class LegacyExecutionPlan:
    """Fully resolved execution inputs for legacy subprocess runs."""

    script_path: Path
    run_paths: RunPaths
    run_id: str
    run_uuid: str
    tsa_list: list[str]
    manifest_path: Path
    checkpoint_paths: list[Path]
    output_root: Path
    output_version_tag: str
    run_config_path: Path | None
    run_config_sha256: str | None
    env: dict[str, str]
    cmd: list[str]
    working_dir: Path


@dataclass(frozen=True)
class LegacyDataArtifactPaths:
    """Legacy data artifact paths used by 00_data-prep orchestration."""

    ria_stands_path: Path
    vdyp_input_pandl_path: Path
    site_prod_bc_gdb_path: Path
    tsa_boundaries_feather_path: Path
    vri_vclr1p_categorical_columns_path: Path
    ria_vclr1p_feature_tif_path: Path
    siteprod_gdb_path: Path
    siteprod_tmpexport_tif_path_prefix: Path
    siteprod_tif_path: Path
    siteprod_bandmap_path: Path
    vdyp_ply_feather_path: Path
    vdyp_lyr_feather_path: Path
    vdyp_results_tsa_pickle_path_prefix: Path
    vdyp_results_pickle_path: Path
    vdyp_curves_smooth_tsa_feather_path_prefix: Path
    vdyp_curves_smooth_feather_path: Path
    tipsy_params_path_prefix: Path
    tipsy_params_columns_path: Path
    model_input_bundle_dir: Path
    misc_thlb_tif_path: Path
    stands_shp_dir: Path


@dataclass(frozen=True)
class LegacyExternalDataPaths:
    """Resolved external source roots consumed by legacy 00_data-prep."""

    external_data_root: Path
    vri_vclr1p_path: Path
    vdyp_input_pandl_path: Path
    tsa_boundaries_path: Path
    site_prod_bc_gdb_path: Path
    siteprod_tif_path: Path
    siteprod_bandmap_path: Path


@dataclass(frozen=True)
class LegacySiteProdArtifacts:
    """Resolved SiteProd artifacts for Stage 00 runtime selection."""

    siteprod_tif_path: Path
    siteprod_bandmap_path: Path
    use_prestacked: bool
    source_label: str


def resolve_legacy_external_data_paths(
    *,
    repo_root: str | Path,
    env_override: str | None = None,
    required_vri_rel: str | Path | None = None,
    vri_rel_candidates: Sequence[str | Path] | None = None,
    vdyp_input_rel_candidates: Sequence[str | Path] | None = None,
    tsa_boundaries_rel: str | Path = "bc/tsa/FADM_TSA.gdb",
    siteprod_rel_candidates: Sequence[str | Path] | None = None,
) -> LegacyExternalDataPaths:
    """Resolve legacy external data root + canonical VRI/TSA source paths."""
    root = Path(repo_root)
    candidates = [
        Path(env_override) if env_override else None,
        root / "data",
        root / ".." / "data",
        Path.home() / "data",
    ]
    resolved_candidates = [candidate.resolve() for candidate in candidates if candidate]
    if vri_rel_candidates is not None:
        required_vri_paths = [Path(path) for path in vri_rel_candidates]
    elif required_vri_rel is not None:
        required_vri_paths = [Path(required_vri_rel)]
    else:
        required_vri_paths = list(DEFAULT_LEGACY_VRI_RELATIVE_PATHS)
    required_tsa_path = Path(tsa_boundaries_rel)
    required_siteprod_paths = (
        [Path(path) for path in siteprod_rel_candidates]
        if siteprod_rel_candidates is not None
        else [
            Path("bc/siteprod/Site_Prod_BC.gdb"),
            Path("Site_Prod_BC.gdb"),
        ]
    )
    required_vdyp_paths = (
        [Path(path) for path in vdyp_input_rel_candidates]
        if vdyp_input_rel_candidates is not None
        else list(DEFAULT_LEGACY_VDYP_INPUT_RELATIVE_PATHS)
    )

    def _resolve_vri_path(candidate_root: Path) -> Path | None:
        for rel_path in required_vri_paths:
            resolved = candidate_root / rel_path
            if resolved.exists():
                return resolved
        return None

    def _resolve_vdyp_path(candidate_root: Path) -> Path | None:
        for rel_path in required_vdyp_paths:
            resolved = candidate_root / rel_path
            if resolved.exists():
                return resolved
        return None

    def _resolve_siteprod_path(candidate_root: Path) -> Path | None:
        for rel_path in required_siteprod_paths:
            resolved = candidate_root / rel_path
            if resolved.exists():
                return resolved
        return None

    external_data_root = resolved_candidates[0]
    selected_vri_path: Path | None = None
    selected_vdyp_path: Path | None = None
    for candidate in resolved_candidates:
        resolved_vri = _resolve_vri_path(candidate)
        resolved_vdyp = _resolve_vdyp_path(candidate)
        if (
            resolved_vri is not None
            and resolved_vdyp is not None
            and (candidate / required_tsa_path).exists()
        ):
            external_data_root = candidate
            selected_vri_path = resolved_vri
            selected_vdyp_path = resolved_vdyp
            break
    else:
        for candidate in resolved_candidates:
            resolved_vri = _resolve_vri_path(candidate)
            resolved_vdyp = _resolve_vdyp_path(candidate)
            if resolved_vri is not None:
                external_data_root = candidate
                selected_vri_path = resolved_vri
                selected_vdyp_path = resolved_vdyp
                break

    if selected_vri_path is None:
        selected_vri_path = external_data_root / required_vri_paths[0]
    if selected_vdyp_path is None:
        selected_vdyp_path = external_data_root / required_vdyp_paths[0]
    selected_siteprod_path = _resolve_siteprod_path(external_data_root)
    if selected_siteprod_path is None:
        selected_siteprod_path = external_data_root / required_siteprod_paths[0]

    return LegacyExternalDataPaths(
        external_data_root=external_data_root,
        vri_vclr1p_path=selected_vri_path,
        vdyp_input_pandl_path=selected_vdyp_path,
        tsa_boundaries_path=external_data_root / required_tsa_path,
        site_prod_bc_gdb_path=selected_siteprod_path,
        siteprod_tif_path=external_data_root / 'bc' / 'siteprod' / 'siteprod.tif',
        siteprod_bandmap_path=external_data_root / 'bc' / 'siteprod' / 'siteprod.bandmap.json',
    )


def build_legacy_data_artifact_paths(
    *,
    output_root: str | Path = "data",
) -> LegacyDataArtifactPaths:
    """Build legacy 00_data-prep artifact path payload under one data root."""
    root = Path(output_root)
    return LegacyDataArtifactPaths(
        ria_stands_path=root / "veg_comp_lyr_r1_poly-ria.shp",
        vdyp_input_pandl_path=root / "VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb",
        site_prod_bc_gdb_path=root / "bc" / "siteprod" / "Site_Prod_BC.gdb",
        tsa_boundaries_feather_path=root / "tsa_boundaries.feather",
        vri_vclr1p_categorical_columns_path=root / "vri_vclr1p_categorical_columns",
        ria_vclr1p_feature_tif_path=root / "ria_vclr1p_feature_raster.tif",
        siteprod_gdb_path=root / "bc" / "siteprod" / "Site_Prod_BC.gdb",
        siteprod_tmpexport_tif_path_prefix=root / "site_prod_bc_",
        siteprod_tif_path=root / "siteprod.tif",
        siteprod_bandmap_path=root / "siteprod.bandmap.json",
        vdyp_ply_feather_path=root / "vdyp_ply.feather",
        vdyp_lyr_feather_path=root / "vdyp_lyr.feather",
        vdyp_results_tsa_pickle_path_prefix=root / "vdyp_results-tsa",
        vdyp_results_pickle_path=root / "vdyp_results.pkl",
        vdyp_curves_smooth_tsa_feather_path_prefix=root / "vdyp_curves_smooth-tsa",
        vdyp_curves_smooth_feather_path=root / "vdyp_curves_smooth.feather",
        tipsy_params_path_prefix=root / "tipsy_params_tsa",
        tipsy_params_columns_path=root / "tipsy_params_columns",
        model_input_bundle_dir=root / "model_input_bundle",
        misc_thlb_tif_path=root / "misc.thlb.tif",
        stands_shp_dir=root / "shp",
    )


def resolve_legacy_siteprod_artifacts(
    *,
    legacy_data_paths: LegacyDataArtifactPaths,
    external_data_paths: LegacyExternalDataPaths,
) -> LegacySiteProdArtifacts:
    """Prefer canonical pre-stacked SiteProd artifacts when both TIFF + band map exist."""
    instance_tif = legacy_data_paths.siteprod_tif_path
    instance_bandmap = legacy_data_paths.siteprod_bandmap_path
    if instance_tif.exists() and instance_bandmap.exists():
        return LegacySiteProdArtifacts(
            siteprod_tif_path=instance_tif,
            siteprod_bandmap_path=instance_bandmap,
            use_prestacked=True,
            source_label="instance-local pre-stacked SiteProd",
        )

    external_tif = external_data_paths.siteprod_tif_path
    external_bandmap = external_data_paths.siteprod_bandmap_path
    if external_tif.exists() and external_bandmap.exists():
        return LegacySiteProdArtifacts(
            siteprod_tif_path=external_tif,
            siteprod_bandmap_path=external_bandmap,
            use_prestacked=True,
            source_label="external canonical pre-stacked SiteProd",
        )

    return LegacySiteProdArtifacts(
        siteprod_tif_path=instance_tif,
        siteprod_bandmap_path=instance_bandmap,
        use_prestacked=False,
        source_label="legacy export-and-stack fallback",
    )


def resolve_legacy_thlb_raster_path(
    *,
    legacy_data_paths: LegacyDataArtifactPaths,
    external_data_paths: LegacyExternalDataPaths,
    exists_fn: Callable[[Path], bool] | None = None,
) -> Path:
    """Resolve THLB raster path with external-data fallback for instance clones."""
    exists = exists_fn or Path.exists
    instance_path = legacy_data_paths.misc_thlb_tif_path
    if exists(instance_path):
        return instance_path
    fallback_path = external_data_paths.external_data_root / "misc.thlb.tif"
    if exists(fallback_path):
        return fallback_path
    return instance_path


def _normalize_optional_str_list(value: object, *, field_name: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(item) for item in value]


def _normalize_optional_bool(value: object, *, field_name: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _normalize_optional_int(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _normalize_optional_positive_int(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    normalized = _normalize_optional_int(value, field_name=field_name)
    if normalized is None or normalized <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return normalized


def _normalize_optional_float(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _normalize_optional_path(value: object, *, field_name: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string path")
    return Path(value)


def _normalize_optional_str(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _normalize_optional_vdyp_sampling_mode(
    value: object, *, field_name: str
) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0 when integer")
        return int(value)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be 'auto', 'all', or positive integer")
    normalized = value.strip().lower()
    if normalized in {"auto", "all"}:
        return normalized
    if normalized.isdigit() and int(normalized) > 0:
        return int(normalized)
    raise ValueError(f"{field_name} must be 'auto', 'all', or positive integer")


def _normalize_optional_managed_curve_mode(
    value: object, *, field_name: str
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be 'tipsy' or 'vdyp_transform'")
    normalized = value.strip().lower()
    if normalized not in {"tipsy", "vdyp_transform"}:
        raise ValueError(f"{field_name} must be 'tipsy' or 'vdyp_transform'")
    return normalized


def load_pipeline_run_profile(config_path: Path) -> PipelineRunProfile:
    """Load YAML/JSON run profile used to seed CLI options."""
    if not config_path.exists():
        raise FileNotFoundError(f"Run config not found: {config_path}")
    suffix = config_path.suffix.lower()
    raw_text = config_path.read_text(encoding="utf-8")
    if suffix == ".json":
        parsed = json.loads(raw_text)
    elif suffix in {".yaml", ".yml"}:
        parsed = yaml.safe_load(raw_text)
    else:
        raise ValueError(f"Unsupported run config format: {config_path}")
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError("Run config root must be a mapping")

    selection = parsed.get("selection", {})
    if selection is None:
        selection = {}
    if not isinstance(selection, dict):
        raise ValueError("selection must be a mapping")

    modes = parsed.get("modes", {})
    if modes is None:
        modes = {}
    if not isinstance(modes, dict):
        raise ValueError("modes must be a mapping")

    run = parsed.get("run", {})
    if run is None:
        run = {}
    if not isinstance(run, dict):
        raise ValueError("run must be a mapping")
    stratification = selection.get("stratification", {})
    if stratification is None:
        stratification = {}
    if not isinstance(stratification, dict):
        raise ValueError("selection.stratification must be a mapping")

    return PipelineRunProfile(
        tsa_list=_normalize_optional_str_list(
            selection.get("tsa"), field_name="selection.tsa"
        ),
        strata_list=_normalize_optional_str_list(
            selection.get("strata"), field_name="selection.strata"
        ),
        boundary_path=_normalize_optional_path(
            selection.get("boundary_path"), field_name="selection.boundary_path"
        ),
        boundary_layer=_normalize_optional_str(
            selection.get("boundary_layer"), field_name="selection.boundary_layer"
        ),
        boundary_code=_normalize_optional_str(
            selection.get("boundary_code"), field_name="selection.boundary_code"
        ),
        strat_bec_grouping=_normalize_optional_str(
            stratification.get("bec_grouping"),
            field_name="selection.stratification.bec_grouping",
        ),
        strat_species_combo_count=_normalize_optional_int(
            stratification.get("species_combo_count"),
            field_name="selection.stratification.species_combo_count",
        ),
        strat_include_tm_species2_for_single=(
            _normalize_optional_bool(
                stratification.get("include_tm_species2_for_single"),
                field_name=("selection.stratification.include_tm_species2_for_single"),
            )
            if "include_tm_species2_for_single" in stratification
            else None
        ),
        strat_top_area_coverage=_normalize_optional_float(
            stratification.get("top_area_coverage"),
            field_name="selection.stratification.top_area_coverage",
        ),
        vdyp_sampling_mode=_normalize_optional_vdyp_sampling_mode(
            modes.get("vdyp_sampling_mode"),
            field_name="modes.vdyp_sampling_mode",
        ),
        vdyp_two_pass_rebin=(
            _normalize_optional_bool(
                modes.get("vdyp_two_pass_rebin"),
                field_name="modes.vdyp_two_pass_rebin",
            )
            if "vdyp_two_pass_rebin" in modes
            else None
        ),
        vdyp_min_stands_per_si_bin=_normalize_optional_positive_int(
            modes.get("vdyp_min_stands_per_si_bin"),
            field_name="modes.vdyp_min_stands_per_si_bin",
        ),
        vdyp_toe_shift_years=_normalize_optional_float(
            modes.get("vdyp_toe_shift_years"),
            field_name="modes.vdyp_toe_shift_years",
        ),
        managed_curve_mode=_normalize_optional_managed_curve_mode(
            modes.get("managed_curve_mode"),
            field_name="modes.managed_curve_mode",
        ),
        managed_curve_x_scale=_normalize_optional_float(
            modes.get("managed_curve_x_scale"),
            field_name="modes.managed_curve_x_scale",
        ),
        managed_curve_y_scale=_normalize_optional_float(
            modes.get("managed_curve_y_scale"),
            field_name="modes.managed_curve_y_scale",
        ),
        managed_curve_truncate_at_culm=(
            _normalize_optional_bool(
                modes.get("managed_curve_truncate_at_culm"),
                field_name="modes.managed_curve_truncate_at_culm",
            )
            if "managed_curve_truncate_at_culm" in modes
            else None
        ),
        managed_curve_max_age=_normalize_optional_positive_int(
            modes.get("managed_curve_max_age"),
            field_name="modes.managed_curve_max_age",
        ),
        resume=_normalize_optional_bool(modes.get("resume"), field_name="modes.resume"),
        dry_run=_normalize_optional_bool(
            modes.get("dry_run"), field_name="modes.dry_run"
        ),
        verbose=_normalize_optional_bool(
            modes.get("verbose"), field_name="modes.verbose"
        ),
        skip_checks=_normalize_optional_bool(
            modes.get("skip_checks"), field_name="modes.skip_checks"
        ),
        debug_rows=_normalize_optional_int(
            modes.get("debug_rows"), field_name="modes.debug_rows"
        ),
        run_id=_normalize_optional_str(run.get("run_id"), field_name="run.run_id"),
        log_dir=_normalize_optional_path(run.get("log_dir"), field_name="run.log_dir"),
    )


def file_sha256(path: Path) -> str:
    """Return SHA256 hex digest for file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_effective_run_options(
    *,
    tsa_list: list[str] | None,
    resume: bool,
    dry_run: bool,
    verbose: bool,
    skip_checks: bool,
    debug_rows: int | None,
    run_id: str | None,
    log_dir: Path,
    profile: PipelineRunProfile | None,
) -> EffectiveRunOptions:
    """Merge CLI run values with profile defaults and normalize for execution."""
    active_profile = profile or PipelineRunProfile()
    merged_tsa = tsa_list if tsa_list else active_profile.tsa_list
    merged_debug_rows = (
        debug_rows if debug_rows is not None else active_profile.debug_rows
    )
    merged_run_id = run_id if run_id is not None else active_profile.run_id
    merged_log_dir = (
        active_profile.log_dir
        if log_dir == Path("vdyp_io/logs") and active_profile.log_dir is not None
        else log_dir
    )
    return EffectiveRunOptions(
        tsa_list=normalize_tsa_list(merged_tsa),
        strata_list=active_profile.strata_list or [],
        resume=resume or active_profile.resume,
        dry_run=dry_run or active_profile.dry_run,
        verbose=verbose or active_profile.verbose,
        skip_checks=skip_checks or active_profile.skip_checks,
        debug_rows=merged_debug_rows,
        run_id=merged_run_id,
        log_dir=Path(merged_log_dir),
        boundary_path=active_profile.boundary_path,
        boundary_layer=active_profile.boundary_layer,
        boundary_code=active_profile.boundary_code,
        strat_bec_grouping=active_profile.strat_bec_grouping,
        strat_species_combo_count=active_profile.strat_species_combo_count,
        strat_include_tm_species2_for_single=(
            active_profile.strat_include_tm_species2_for_single
        ),
        strat_top_area_coverage=active_profile.strat_top_area_coverage,
        vdyp_sampling_mode=active_profile.vdyp_sampling_mode,
        vdyp_two_pass_rebin=active_profile.vdyp_two_pass_rebin,
        vdyp_min_stands_per_si_bin=active_profile.vdyp_min_stands_per_si_bin,
        vdyp_toe_shift_years=active_profile.vdyp_toe_shift_years,
        managed_curve_mode=active_profile.managed_curve_mode,
        managed_curve_x_scale=active_profile.managed_curve_x_scale,
        managed_curve_y_scale=active_profile.managed_curve_y_scale,
        managed_curve_truncate_at_culm=active_profile.managed_curve_truncate_at_culm,
        managed_curve_max_age=active_profile.managed_curve_max_age,
    )


def resolve_run_paths(
    *,
    script_path: Path,
    instance_root: Path | None = None,
    log_dir: Path | None = None,
) -> RunPaths:
    """Resolve canonical script/repo/log paths for a pipeline run invocation."""
    repo_root = (
        instance_root.expanduser().resolve()
        if instance_root is not None
        else script_path.parent.resolve()
    )
    return RunPaths(
        repo_root=repo_root,
        script_path=script_path.resolve(),
        log_dir=(log_dir or (repo_root / "vdyp_io" / "logs")).resolve(),
    )


def build_pipeline_run_config(
    *,
    tsa_list: Iterable[str] | None,
    resume: bool,
    debug_rows: int | None = None,
    run_id: str | None = None,
    log_dir: Path | None = None,
    output_root: Path = Path("outputs"),
    run_config_path: Path | None = None,
    run_config_sha256: str | None = None,
    boundary_path: Path | None = None,
    boundary_layer: str | None = None,
    boundary_code: str | None = None,
    strat_bec_grouping: str | None = None,
    strat_species_combo_count: int | None = None,
    strat_include_tm_species2_for_single: bool | None = None,
    strat_top_area_coverage: float | None = None,
    vdyp_sampling_mode: str | int | None = None,
    vdyp_two_pass_rebin: bool | None = None,
    vdyp_min_stands_per_si_bin: int | None = None,
    vdyp_toe_shift_years: float | None = None,
    managed_curve_mode: str | None = None,
    managed_curve_x_scale: float | None = None,
    managed_curve_y_scale: float | None = None,
    managed_curve_truncate_at_culm: bool | None = None,
    managed_curve_max_age: int | None = None,
    instance_root: Path | None = None,
) -> PipelineRunConfig:
    """Create normalized pipeline run configuration from CLI inputs."""
    normalized_tsas = normalize_tsa_list(tsa_list)
    return PipelineRunConfig(
        tsa_list=normalized_tsas,
        resume=resume,
        debug_rows=debug_rows,
        run_id=run_id,
        log_dir=log_dir,
        output_root=Path(output_root),
        run_config_path=Path(run_config_path) if run_config_path is not None else None,
        run_config_sha256=run_config_sha256,
        boundary_path=Path(boundary_path) if boundary_path is not None else None,
        boundary_layer=boundary_layer,
        boundary_code=boundary_code,
        strat_bec_grouping=strat_bec_grouping,
        strat_species_combo_count=strat_species_combo_count,
        strat_include_tm_species2_for_single=strat_include_tm_species2_for_single,
        strat_top_area_coverage=strat_top_area_coverage,
        vdyp_sampling_mode=vdyp_sampling_mode,
        vdyp_two_pass_rebin=vdyp_two_pass_rebin,
        vdyp_min_stands_per_si_bin=vdyp_min_stands_per_si_bin,
        vdyp_toe_shift_years=vdyp_toe_shift_years,
        managed_curve_mode=managed_curve_mode,
        managed_curve_x_scale=managed_curve_x_scale,
        managed_curve_y_scale=managed_curve_y_scale,
        managed_curve_truncate_at_culm=managed_curve_truncate_at_culm,
        managed_curve_max_age=managed_curve_max_age,
        instance_root=Path(instance_root) if instance_root is not None else None,
    )


def build_legacy_execution_plan(
    *,
    run_config: PipelineRunConfig,
    script_path: Path,
    python_executable: str,
    base_env: Mapping[str, str],
) -> LegacyExecutionPlan:
    """Resolve all command/env/path details needed to execute the legacy script."""
    run_paths = resolve_run_paths(
        script_path=script_path,
        instance_root=run_config.instance_root,
        log_dir=run_config.log_dir,
    )
    run_id = run_config.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = run_paths.log_dir / f"run_manifest-{run_id}.json"
    checkpoint_paths = [
        Path(f"data/vdyp_prep-tsa{tsa}.pkl") for tsa in run_config.tsa_list
    ]

    env = dict(base_env)
    env["FEMIC_TSA_LIST"] = ",".join(run_config.tsa_list)
    env["FEMIC_RESUME"] = "1" if run_config.resume else "0"
    # Stage 00 cache loading is controlled by FEMIC_NO_CACHE in the legacy script.
    # For non-resume runs, force no-cache mode so a clean slate can rebuild end-to-end.
    env["FEMIC_NO_CACHE"] = "0" if run_config.resume else "1"
    if run_config.debug_rows:
        env["FEMIC_DEBUG_ROWS"] = str(run_config.debug_rows)
    else:
        env.pop("FEMIC_DEBUG_ROWS", None)
    env["FEMIC_RUN_ID"] = run_id
    env["FEMIC_LOG_DIR"] = str(run_paths.log_dir)
    env["FEMIC_OUTPUT_ROOT"] = str(Path(run_config.output_root))
    env["FEMIC_INSTANCE_ROOT"] = str(run_paths.repo_root)
    # Keep legacy script stdout/stderr unbuffered so long Stage 00 work
    # emits progress continuously (important for diagnosing long-running runs).
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("FEMIC_SOURCE_ROOT", str(script_path.resolve().parents[4]))
    env.setdefault(
        "FEMIC_VDYP_CFG_DIR",
        str(
            (Path(env["FEMIC_SOURCE_ROOT"]) / "VDYP7" / "VDYP7" / "VDYP_CFG").resolve()
        ),
    )
    if run_config.run_config_path is not None:
        env["FEMIC_RUN_CONFIG_PATH"] = str(run_config.run_config_path)
    if run_config.run_config_sha256 is not None:
        env["FEMIC_RUN_CONFIG_SHA256"] = run_config.run_config_sha256
    if run_config.boundary_path is not None:
        env["FEMIC_BOUNDARY_PATH"] = run_config.boundary_path.as_posix()
    if run_config.boundary_layer:
        env["FEMIC_BOUNDARY_LAYER"] = run_config.boundary_layer
    if run_config.boundary_code:
        env["FEMIC_BOUNDARY_CODE"] = run_config.boundary_code
    if run_config.strat_bec_grouping:
        env["FEMIC_STRAT_BEC_GROUPING"] = run_config.strat_bec_grouping
    if run_config.strat_species_combo_count is not None:
        env["FEMIC_STRAT_SPECIES_COMBO_COUNT"] = str(
            int(run_config.strat_species_combo_count)
        )
    if run_config.strat_include_tm_species2_for_single is not None:
        env["FEMIC_STRAT_INCLUDE_TM_SPECIES2_FOR_SINGLE"] = (
            "1" if run_config.strat_include_tm_species2_for_single else "0"
        )
    if run_config.strat_top_area_coverage is not None:
        env["FEMIC_STRAT_TOP_AREA_COVERAGE"] = str(
            float(run_config.strat_top_area_coverage)
        )
    if run_config.vdyp_sampling_mode is not None:
        env["FEMIC_VDYP_SAMPLING_MODE"] = str(run_config.vdyp_sampling_mode)
    if run_config.vdyp_two_pass_rebin is not None:
        env["FEMIC_VDYP_TWO_PASS_REBIN"] = (
            "1" if bool(run_config.vdyp_two_pass_rebin) else "0"
        )
    if run_config.vdyp_min_stands_per_si_bin is not None:
        env["FEMIC_VDYP_MIN_STANDS_PER_SI_BIN"] = str(
            int(run_config.vdyp_min_stands_per_si_bin)
        )
    if run_config.vdyp_toe_shift_years is not None:
        env["FEMIC_VDYP_TOE_SHIFT_YEARS"] = str(float(run_config.vdyp_toe_shift_years))
    if run_config.managed_curve_mode is not None:
        env["FEMIC_MANAGED_CURVE_MODE"] = str(run_config.managed_curve_mode)
    if run_config.managed_curve_x_scale is not None:
        env["FEMIC_MANAGED_CURVE_X_SCALE"] = str(
            float(run_config.managed_curve_x_scale)
        )
    if run_config.managed_curve_y_scale is not None:
        env["FEMIC_MANAGED_CURVE_Y_SCALE"] = str(
            float(run_config.managed_curve_y_scale)
        )
    if run_config.managed_curve_truncate_at_culm is not None:
        env["FEMIC_MANAGED_CURVE_TRUNCATE_AT_CULM"] = (
            "1" if run_config.managed_curve_truncate_at_culm else "0"
        )
    if run_config.managed_curve_max_age is not None:
        env["FEMIC_MANAGED_CURVE_MAX_AGE"] = str(int(run_config.managed_curve_max_age))
    env.setdefault("FEMIC_RUN_UUID", str(uuid.uuid4()))
    run_uuid = env["FEMIC_RUN_UUID"]

    cmd = [python_executable, str(script_path)]
    return LegacyExecutionPlan(
        script_path=script_path,
        run_paths=run_paths,
        run_id=run_id,
        run_uuid=run_uuid,
        tsa_list=run_config.tsa_list,
        manifest_path=manifest_path,
        checkpoint_paths=checkpoint_paths,
        output_root=Path(run_config.output_root),
        output_version_tag=run_id,
        run_config_path=run_config.run_config_path,
        run_config_sha256=run_config.run_config_sha256,
        env=env,
        cmd=cmd,
        working_dir=run_paths.repo_root,
    )
