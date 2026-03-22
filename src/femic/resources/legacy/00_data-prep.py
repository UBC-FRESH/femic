# Auto-generated from 00_data-prep.ipynb

# --- cell 3 ---
import os
import matplotlib.pyplot as plt

# import datatable

import pandas as pd
import geopandas as gpd
import pickle
import seaborn as sns
from shapely.ops import unary_union, Polygon
import numpy as np
from numpy.polynomial import Polynomial
import csv
from scipy.optimize import curve_fit
import rasterio as rio
from rasterio.plot import show
from rasterio.mask import mask
from rasterio.io import MemoryFile
from geocube.api.core import make_geocube
import subprocess
from rasterio.plot import show, show_hist
import warnings
from pympler import asizeof

# import ipcmagic
import ipyparallel as ipp
import mapply

try:
    import fiona  # noqa: F401
except ModuleNotFoundError:
    fiona = None

import affine

# from osgeo import gdal
from scipy.optimize import curve_fit as _curve_fit
from pathlib import Path
import sys

try:
    from femic.pipeline.bundle import (
        assign_curve_ids_from_au_table,
        build_bundle_tables_from_curves,
        bundle_tables_ready,
        emit_missing_au_curve_mapping_warning,
        ensure_au_table_index,
        ensure_scsi_au_from_table,
        load_bundle_tables,
        resolve_bundle_paths,
        write_bundle_tables,
    )
    from femic.pipeline.legacy_runtime import (
        build_legacy_01a_runtime_config,
        build_legacy_01b_runtime_config,
    )
    from femic.pipeline.io import (
        build_legacy_data_artifact_paths,
        build_ria_vri_checkpoint_paths,
        resolve_legacy_external_data_paths,
    )
    from femic.pipeline.vdyp import build_vdyp_cache_paths
    from femic.pipeline.vri import (
        assign_stratum_codes_with_lexmatch,
        assign_forest_type_from_species_pct,
        derive_species_list_from_slots,
        filter_post_thlb_stands,
        normalize_and_filter_checkpoint2_records,
    )
    from femic.pipeline.siteprod import (
        assign_siteprod_from_raster,
        export_and_stack_siteprod_layers,
        list_siteprod_layers,
    )
    from femic.pipeline.species_volume import compile_species_volume_columns
    from femic.pipeline.stages import (
        execute_legacy_tsa_stage,
        initialize_parallel_execution_backend,
        initialize_legacy_tsa_stage_state,
        prepare_tsa_index,
        should_skip_if_outputs_exist,
    )
    from femic.pipeline.tsa import (
        assign_au_ids_from_scsi,
        assign_thlb_raw_from_raster,
        assign_thlb_area_and_flag,
        assign_si_levels_from_stratum_quantiles,
        assign_stratum_matches_from_au_table,
        emit_missing_au_mapping_warning,
        summarize_missing_au_mappings,
        validate_nonempty_au_assignment,
    )
    from femic.pipeline.tipsy import (
        tipsy_input_dat_path,
        tipsy_params_excel_path,
        tipsy_stage_output_paths,
    )
    from femic.pipeline.stands import (
        DEFAULT_STANDS_PROP_NAMES,
        DEFAULT_STANDS_PROP_TYPES,
        build_stands_column_map,
        export_stands_shapefiles,
        should_skip_stands_export,
    )
except ModuleNotFoundError:
    _src_dir = Path(__file__).resolve().parent / "src"
    if _src_dir.is_dir():
        sys.path.insert(0, str(_src_dir))
    from femic.pipeline.bundle import (
        assign_curve_ids_from_au_table,
        build_bundle_tables_from_curves,
        bundle_tables_ready,
        emit_missing_au_curve_mapping_warning,
        ensure_au_table_index,
        ensure_scsi_au_from_table,
        load_bundle_tables,
        resolve_bundle_paths,
        write_bundle_tables,
    )
    from femic.pipeline.legacy_runtime import (
        build_legacy_01a_runtime_config,
        build_legacy_01b_runtime_config,
    )
    from femic.pipeline.io import (
        build_legacy_data_artifact_paths,
        build_ria_vri_checkpoint_paths,
        resolve_legacy_external_data_paths,
    )
    from femic.pipeline.vdyp import build_vdyp_cache_paths
    from femic.pipeline.vri import (
        assign_stratum_codes_with_lexmatch,
        assign_forest_type_from_species_pct,
        derive_species_list_from_slots,
        filter_post_thlb_stands,
        normalize_and_filter_checkpoint2_records,
    )
    from femic.pipeline.siteprod import (
        assign_siteprod_from_raster,
        export_and_stack_siteprod_layers,
        list_siteprod_layers,
    )
    from femic.pipeline.species_volume import compile_species_volume_columns
    from femic.pipeline.stages import (
        execute_legacy_tsa_stage,
        initialize_parallel_execution_backend,
        initialize_legacy_tsa_stage_state,
        prepare_tsa_index,
        should_skip_if_outputs_exist,
    )
    from femic.pipeline.tsa import (
        assign_au_ids_from_scsi,
        assign_thlb_raw_from_raster,
        assign_thlb_area_and_flag,
        assign_si_levels_from_stratum_quantiles,
        assign_stratum_matches_from_au_table,
        emit_missing_au_mapping_warning,
        summarize_missing_au_mappings,
        validate_nonempty_au_assignment,
    )
    from femic.pipeline.tipsy import (
        tipsy_input_dat_path,
        tipsy_params_excel_path,
        tipsy_stage_output_paths,
    )
    from femic.pipeline.stands import (
        DEFAULT_STANDS_PROP_NAMES,
        DEFAULT_STANDS_PROP_TYPES,
        build_stands_column_map,
        export_stands_shapefiles,
        should_skip_stands_export,
    )

# --- cell 5 ---
pd.set_option(
    "display.max_rows", 300
)  # bump this parameter up if you want to see more table rows
pd.set_option(
    "display.max_columns", 30
)  # bump this parameter up if you want to see more table rows

warnings.filterwarnings("ignore", message=".*initial implementation of Parquet.*")
# Swifter can speed up row-wise apply, but it has been unstable in this pipeline context.
# Default to plain pandas apply; allow explicit opt-in via FEMIC_USE_SWIFTER=1.
_use_swifter = os.environ.get("FEMIC_USE_SWIFTER", "0") == "1"
if _use_swifter:
    import swifter

    swifter.set_defaults(
        scheduler="synchronous",
        progress_bar=False,
        allow_dask_on_strings=False,
    )


def _row_apply(df, func, axis=1):
    if _use_swifter:
        return df.swifter.apply(func, axis=axis)
    return df.apply(func, axis=axis)


# --- cell 7 ---
# %ipcluster --help
# %load_ext ipyparallel
# %ipcluster start -n 16
_disable_ipp = os.environ.get("FEMIC_DISABLE_IPP", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)
_parallel_backend = initialize_parallel_execution_backend(
    disable_ipp=_disable_ipp,
    ipp_module=ipp,
    print_fn=print,
)
_use_ipp = _parallel_backend.use_ipp
rc = _parallel_backend.rc
lbview = _parallel_backend.lbview

# --- cell 9 ---
_instance_root_env = os.environ.get("FEMIC_INSTANCE_ROOT")
_repo_root = (
    Path(_instance_root_env).expanduser().resolve()
    if _instance_root_env
    else Path(__file__).resolve().parent
)
_external_paths = resolve_legacy_external_data_paths(
    repo_root=_repo_root,
    env_override=os.environ.get("FEMIC_EXTERNAL_DATA_ROOT"),
)
vri_vclr1p_path = _external_paths.vri_vclr1p_path
_legacy_data_paths = build_legacy_data_artifact_paths(output_root=_repo_root / "data")
ria_stands_path = _legacy_data_paths.ria_stands_path
tsa_boundaries_path = _external_paths.tsa_boundaries_path
print(f"using VRI source: {vri_vclr1p_path}")
print(f"using TSA boundaries source: {tsa_boundaries_path}")
ria_maptiles_path = str((_repo_root / "ria_maptiles.csv").resolve())
vdyp_input_pandl_path = _external_paths.vdyp_input_pandl_path
if not vdyp_input_pandl_path.exists():
    vdyp_input_pandl_path = _legacy_data_paths.vdyp_input_pandl_path
print(f"using VDYP input source: {vdyp_input_pandl_path}")

site_prod_bc_gdb_path = (
    _external_paths.site_prod_bc_gdb_path
)  # ESRI File Geodatabase containing 22 species-wise site productivity raster layers
if not site_prod_bc_gdb_path.exists():
    site_prod_bc_gdb_path = _legacy_data_paths.site_prod_bc_gdb_path
print(f"using site productivity source: {site_prod_bc_gdb_path}")

tsa_boundaries_feather_path = _legacy_data_paths.tsa_boundaries_feather_path
_ria_vri_checkpoint_paths = build_ria_vri_checkpoint_paths(
    output_root=_repo_root / "data"
)
ria_vri_vclr1p_checkpoint1_feather_path = _ria_vri_checkpoint_paths[1]
ria_vri_vclr1p_checkpoint2_feather_path = _ria_vri_checkpoint_paths[2]
ria_vri_vclr1p_checkpoint3_feather_path = _ria_vri_checkpoint_paths[3]
ria_vri_vclr1p_checkpoint4_feather_path = _ria_vri_checkpoint_paths[4]
ria_vri_vclr1p_checkpoint5_feather_path = _ria_vri_checkpoint_paths[5]
ria_vri_vclr1p_checkpoint6_feather_path = _ria_vri_checkpoint_paths[6]
ria_vri_vclr1p_checkpoint7_feather_path = _ria_vri_checkpoint_paths[7]
ria_vri_vclr1p_checkpoint8_feather_path = _ria_vri_checkpoint_paths[8]
vri_vclr1p_categorical_columns_path = (
    _legacy_data_paths.vri_vclr1p_categorical_columns_path
)
ria_vclr1p_feature_tif_path = _legacy_data_paths.ria_vclr1p_feature_tif_path

arc_raster_rescue_exe_path = Path("../ArcRasterRescue/build/arc_raster_rescue.exe")
siteprod_gdb_path = site_prod_bc_gdb_path
siteprod_tmpexport_tif_path_prefix = (
    _legacy_data_paths.siteprod_tmpexport_tif_path_prefix
)
siteprod_tif_path = _legacy_data_paths.siteprod_tif_path

vdyp_ply_feather_path = _legacy_data_paths.vdyp_ply_feather_path
vdyp_lyr_feather_path = _legacy_data_paths.vdyp_lyr_feather_path
vdyp_results_tsa_pickle_path_prefix = (
    _legacy_data_paths.vdyp_results_tsa_pickle_path_prefix
)
vdyp_results_pickle_path = _legacy_data_paths.vdyp_results_pickle_path
vdyp_curves_smooth_tsa_feather_path_prefix = (
    _legacy_data_paths.vdyp_curves_smooth_tsa_feather_path_prefix
)
vdyp_curves_smooth_feather_path = _legacy_data_paths.vdyp_curves_smooth_feather_path

tipsy_params_path_prefix = _legacy_data_paths.tipsy_params_path_prefix

_default_ria_tsas = ["08", "16", "24", "40", "41"]
_femic_tsa_list = os.environ.get("FEMIC_TSA_LIST")
if _femic_tsa_list:
    ria_tsas = [tsa.strip() for tsa in _femic_tsa_list.split(",") if tsa.strip()]
else:
    ria_tsas = _default_ria_tsas
_femic_resume = os.environ.get("FEMIC_RESUME", "0") == "1"
_femic_debug_rows_raw = os.environ.get("FEMIC_DEBUG_ROWS")
_femic_no_cache_raw = os.environ.get("FEMIC_NO_CACHE", "0")
_femic_thlb_diag_raw = os.environ.get("FEMIC_THLB_DIAGNOSTICS", "0")
_femic_boundary_path_raw = os.environ.get("FEMIC_BOUNDARY_PATH")
_femic_boundary_layer = os.environ.get("FEMIC_BOUNDARY_LAYER")
_femic_boundary_code = os.environ.get("FEMIC_BOUNDARY_CODE")
_femic_strat_bec_grouping = os.environ.get("FEMIC_STRAT_BEC_GROUPING", "zone")
_femic_strat_species_combo_count_raw = os.environ.get(
    "FEMIC_STRAT_SPECIES_COMBO_COUNT", "1"
)
_femic_strat_include_tm_species2_raw = os.environ.get(
    "FEMIC_STRAT_INCLUDE_TM_SPECIES2_FOR_SINGLE", "1"
)
_femic_strat_top_area_coverage_raw = os.environ.get(
    "FEMIC_STRAT_TOP_AREA_COVERAGE", "0.8"
)
_femic_vdyp_sampling_mode_raw = os.environ.get("FEMIC_VDYP_SAMPLING_MODE", "auto")
_femic_vdyp_two_pass_rebin_raw = os.environ.get("FEMIC_VDYP_TWO_PASS_REBIN", "0")
_femic_vdyp_min_stands_per_si_bin_raw = os.environ.get(
    "FEMIC_VDYP_MIN_STANDS_PER_SI_BIN", "25"
)
_femic_thlb_diagnostics = _femic_thlb_diag_raw.strip().lower() in (
    "1",
    "true",
    "yes",
)
try:
    _femic_debug_rows = int(_femic_debug_rows_raw) if _femic_debug_rows_raw else None
except ValueError:
    _femic_debug_rows = None
_femic_no_cache_env = _femic_no_cache_raw.strip().lower() in ("1", "true", "yes")
_femic_custom_boundary = bool(_femic_boundary_path_raw)
_femic_no_cache = (
    _femic_no_cache_env
    or _femic_debug_rows is not None
    or _femic_custom_boundary
    or not _femic_resume
)
_femic_resume_effective = _femic_resume and not _femic_no_cache
si_levels = ["L", "M", "H"]
try:
    _femic_strat_species_combo_count = max(1, int(_femic_strat_species_combo_count_raw))
except ValueError:
    _femic_strat_species_combo_count = 1
_femic_strat_include_tm_species2_for_single = (
    _femic_strat_include_tm_species2_raw.strip().lower() in ("1", "true", "yes")
)
try:
    _femic_strat_top_area_coverage = (
        float(_femic_strat_top_area_coverage_raw)
        if _femic_strat_top_area_coverage_raw not in (None, "")
        else None
    )
except ValueError:
    _femic_strat_top_area_coverage = None
if _femic_strat_top_area_coverage is not None and not (
    0.0 < _femic_strat_top_area_coverage <= 1.0
):
    print(
        "warning: invalid FEMIC_STRAT_TOP_AREA_COVERAGE=%s; expected 0<value<=1, ignoring"
        % _femic_strat_top_area_coverage_raw
    )
    _femic_strat_top_area_coverage = None
_femic_vdyp_two_pass_rebin = _femic_vdyp_two_pass_rebin_raw.strip().lower() in (
    "1",
    "true",
    "yes",
)
_femic_vdyp_sampling_mode_token = _femic_vdyp_sampling_mode_raw.strip().lower()
if _femic_vdyp_sampling_mode_token in {"auto", "all"}:
    _femic_vdyp_sampling_mode: str | int = _femic_vdyp_sampling_mode_token
elif (
    _femic_vdyp_sampling_mode_token.isdigit()
    and int(_femic_vdyp_sampling_mode_token) > 0
):
    _femic_vdyp_sampling_mode = int(_femic_vdyp_sampling_mode_token)
else:
    print(
        "warning: invalid FEMIC_VDYP_SAMPLING_MODE=%s; expected auto|all|positive-int, using auto"
        % _femic_vdyp_sampling_mode_raw
    )
    _femic_vdyp_sampling_mode = "auto"
try:
    _femic_vdyp_min_stands_per_si_bin = int(_femic_vdyp_min_stands_per_si_bin_raw)
except ValueError:
    _femic_vdyp_min_stands_per_si_bin = 25
if _femic_vdyp_min_stands_per_si_bin <= 0:
    print(
        "warning: invalid FEMIC_VDYP_MIN_STANDS_PER_SI_BIN=%s; expected positive integer, using 25"
        % _femic_vdyp_min_stands_per_si_bin_raw
    )
    _femic_vdyp_min_stands_per_si_bin = 25


def _apply_debug_rows(_df, _label=None):
    if not _femic_debug_rows:
        return _df
    if _label:
        print(f"debug: limiting VRI input rows to {_femic_debug_rows} ({_label})")
    else:
        print(f"debug: limiting VRI input rows to {_femic_debug_rows}")
    return _df.head(_femic_debug_rows).copy()


if _femic_no_cache:
    print("debug: disabling cached checkpoint reuse")
if _femic_custom_boundary:
    print(
        "custom boundary mode: %s (layer=%s)"
        % (_femic_boundary_path_raw, _femic_boundary_layer or "<default>")
    )
print(
    "stratum key config: bec_grouping=%s species_combo_count=%d include_tm_species2_for_single=%s top_area_coverage=%s"
    % (
        _femic_strat_bec_grouping,
        _femic_strat_species_combo_count,
        _femic_strat_include_tm_species2_for_single,
        _femic_strat_top_area_coverage,
    )
)
print(
    "vdyp run config: sampling_mode=%s two_pass_rebin=%s min_stands_per_si_bin=%s"
    % (
        _femic_vdyp_sampling_mode,
        _femic_vdyp_two_pass_rebin,
        _femic_vdyp_min_stands_per_si_bin,
    )
)

raster_pxw = raster_pxh = 100

_tipsy_params_columns_path = _legacy_data_paths.tipsy_params_columns_path
if not _tipsy_params_columns_path.exists():
    _femic_source_root = os.environ.get("FEMIC_SOURCE_ROOT")
    if _femic_source_root:
        _source_candidate = Path(_femic_source_root) / "data" / "tipsy_params_columns"
        if _source_candidate.exists():
            _tipsy_params_columns_path = _source_candidate
tipsy_params_columns = [
    line.strip() for line in _tipsy_params_columns_path.read_text().splitlines()
]

# --- cell 11 ---
species_spruce = ["S", "SB", "SE", "SN", "SS", "SW", "SX", "SXE", "SXL", "SXW"]
species_pine = ["P", "PA", "PJ", "PL", "PLC", "PLI", "PM"]
species_fir = ["B", "BA", "BB", "BG", "BL", "BM", "BP"]
species_larch = ["L", "LA", "LS", "LT", "LW"]
species_cedar = ["C", "CW"]
species_hemlock = ["HM", "HWI", "HW"]
species_douglasfir = ["F", "FD", "FDC", "FDI"]

species_aspen = ["AC", "ACB", "ACT", "AD", "AT", "AX"]
species_birch = ["E", "EA", "EB", "EE", "EP", "EW", "EXP"]
species_willow = ["W", "WA", "WB", "WD", "WP", "WS"]
species_alder = ["D", "DR"]
species_cherry = ["V"]
species_dogwood = ["GP"]
species_oak = ["Q"]
species_maple = ["M", "MB", "MV"]

# --- cell 13 ---
if not arc_raster_rescue_exe_path.is_file():
    # Notebook cell only built the tool; in script keep a no-op.
    pass

# --- cell 15 ---
import_tsa_boundaries_data = 1 if _femic_no_cache else 0
if import_tsa_boundaries_data:
    if _femic_custom_boundary:
        read_kwargs = {}
        if _femic_boundary_layer:
            read_kwargs["layer"] = _femic_boundary_layer
        custom_boundary = gpd.read_file(_femic_boundary_path_raw, **read_kwargs)
        if custom_boundary.empty:
            raise ValueError(
                "Custom boundary file returned zero features: %s"
                % _femic_boundary_path_raw
            )
        boundary_code = _femic_boundary_code
        if not boundary_code:
            if len(ria_tsas) != 1:
                raise ValueError(
                    "Set FEMIC_BOUNDARY_CODE when running custom boundary mode with "
                    "multiple tsa codes."
                )
            boundary_code = ria_tsas[0]
        custom_geom = unary_union(list(custom_boundary.geometry.values))
        tsa_boundaries = gpd.GeoDataFrame(
            {"TSA_NUMBER": [boundary_code], "geometry": [custom_geom]},
            crs=custom_boundary.crs,
        ).set_index("TSA_NUMBER")
    else:
        tsa_boundaries = gpd.read_file(tsa_boundaries_path)
        tsa_boundaries = (
            tsa_boundaries[["TSA_NUMBER", "geometry"]]
            .loc[tsa_boundaries.TSA_NUMBER.isin(ria_tsas)]
            .dissolve(by="TSA_NUMBER")
        )
        tsa_boundaries["geometry"] = tsa_boundaries.geometry.simplify(
            tolerance=1000, preserve_topology=True
        )
    _missing_tsas = [tsa for tsa in ria_tsas if tsa not in tsa_boundaries.index]
    if _missing_tsas:
        raise ValueError(
            "Boundary geometry missing requested tsa codes: %s (available=%s)"
            % (_missing_tsas, list(tsa_boundaries.index))
        )
    tsa_boundaries.to_feather(tsa_boundaries_feather_path)
else:
    tsa_boundaries = gpd.read_feather(tsa_boundaries_feather_path)

# tsa_extent_all = Polygon(unary_union(list(tsa_boundaries.geometry.values)).exterior)

# --- cell 17 ---
import_vri_vclr1p_data = 1 if _femic_no_cache else 0  # set to False to use cached data
if import_vri_vclr1p_data:
    print("loading VRI data from source")

    def load_vri_vclr1p(vri_vclr1p_path, tsa_code, tsa_mask, ignore_geometry=False):
        import geopandas as gpd  # local import required to play nice with ipp engines

        result = gpd.read_file(
            vri_vclr1p_path, mask=tsa_mask, ignore_geometry=ignore_geometry
        )
        result["tsa_code"] = tsa_code
        return result

    tsa_gdfs = lbview.map_async(
        load_vri_vclr1p,
        [vri_vclr1p_path for tsa in ria_tsas],
        ria_tsas,
        [tsa_boundaries.loc[tsa].geometry for tsa in ria_tsas],
        ordered=True,
    )
    rc.wait_interactive()
    ria_vri_vclr1p = pd.concat(tsa_gdfs, axis=0, ignore_index=True)
    ria_vri_vclr1p.to_feather(ria_vri_vclr1p_checkpoint1_feather_path)
else:
    print("loading VRI data from checkpoint1 feather")
    ria_vri_vclr1p = gpd.read_feather(ria_vri_vclr1p_checkpoint1_feather_path)
    ria_vri_vclr1p = _apply_debug_rows(ria_vri_vclr1p, "checkpoint1")

f = ria_vri_vclr1p


# Normalize TSA codes to zero-padded strings for consistent indexing.
def _normalize_tsa_code(_value):
    try:
        return f"{int(_value):02d}"
    except (TypeError, ValueError):
        return str(_value).zfill(2)


if "tsa_code" in f.columns:
    f["tsa_code"] = f["tsa_code"].apply(_normalize_tsa_code)

f = _apply_debug_rows(f, "checkpoint1")

# --- cell 19 ---
# map layer indices to layer species codes
siteprod_layerspecies, siteprod_specieslayer = list_siteprod_layers(
    arc_raster_rescue_exe_path=arc_raster_rescue_exe_path,
    siteprod_gdb_path=siteprod_gdb_path,
    run_fn=subprocess.run,
)

if not siteprod_tif_path.is_file():
    print("Extracting siteprod raster data from ESRI File Geodatabase...")
    export_and_stack_siteprod_layers(
        arc_raster_rescue_exe_path=arc_raster_rescue_exe_path,
        site_prod_bc_gdb_path=site_prod_bc_gdb_path,
        site_prod_bc_layerspecies=siteprod_layerspecies,
        siteprod_layerspecies=siteprod_layerspecies,
        siteprod_tmpexport_tif_path_prefix=siteprod_tmpexport_tif_path_prefix,
        siteprod_tif_path=siteprod_tif_path,
        run_fn=subprocess.run,
        rio_module=rio,
        message_fn=print,
    )


species_list = derive_species_list_from_slots(f_table=ria_vri_vclr1p)

# --- cell 24 ---
process_checkpoint2 = 1 if _femic_no_cache else 0
if process_checkpoint2:
    f = normalize_and_filter_checkpoint2_records(f_table=f)
    # implies f.BCLCS_LEVEL_1 == 'V'
    # f = f[f.BCLCS_LEVEL_5 != 'OP']
    # vri_vclr1p_categorical_columns = open(vri_vclr1p_categorical_columns_path).read().split('\n')
    # for c in vri_vclr1p_categorical_columns:
    #    f[c] = f[c].astype('category')
    f = assign_siteprod_from_raster(
        f_table=f,
        siteprod_tif_path=siteprod_tif_path,
        siteprod_specieslayer=siteprod_specieslayer,
        rio_module=rio,
        mask_fn=mask,
        np_module=np,
        row_apply_fn=_row_apply,
        out_col="siteprod",
    )
    f.to_feather(ria_vri_vclr1p_checkpoint2_feather_path)
else:
    print("loading VRI data from checkpoint2 feather")
    f = gpd.read_feather(ria_vri_vclr1p_checkpoint2_feather_path)
    f = _apply_debug_rows(f, "checkpoint2")

# --- cell 26 ---
f.reset_index(inplace=True)

# --- cell 27 ---
process_checkpoint3 = 1 if _femic_no_cache else 1
if process_checkpoint3:
    f = compile_species_volume_columns(
        f_table=f,
        species_list=species_list,
        map_async_fn=lbview.map_async,
        wait_fn=rc.wait_interactive,
        message_fn=print,
    )
    f.to_feather(ria_vri_vclr1p_checkpoint3_feather_path)
else:
    print("loading VRI data from checkpoint3 feather")
    f = gpd.read_feather(ria_vri_vclr1p_checkpoint3_feather_path)
    f = _apply_debug_rows(f, "checkpoint3")


# --- cell 29 ---
# --- cell 33 ---
f = assign_stratum_codes_with_lexmatch(
    f_table=f,
    row_apply_fn=_row_apply,
    bec_grouping=_femic_strat_bec_grouping,
    species_combo_count=_femic_strat_species_combo_count,
    include_tm_species2_for_single=_femic_strat_include_tm_species2_for_single,
)

# --- cell 34 ---
stratum_col = "stratum"

# --- cell 36 ---
# f['forest_type'] = f.reset_index().swifter.apply(classify_stand_forest_type, axis=1)
f = assign_forest_type_from_species_pct(f_table=f, out_col="forest_type")

# --- cell 38 ---
f.to_feather(ria_vri_vclr1p_checkpoint4_feather_path)

# --- cell 42 ---
# f = f.reset_index().set_index('tsa_code')

# --- cell 44 ---
_legacy_stage_state = initialize_legacy_tsa_stage_state()
vdyp_curves_smooth = _legacy_stage_state.vdyp_curves_smooth
vdyp_results = _legacy_stage_state.vdyp_results
tipsy_params = _legacy_stage_state.tipsy_params
tipsy_curves = _legacy_stage_state.tipsy_curves
scsi_au = _legacy_stage_state.scsi_au
au_scsi = _legacy_stage_state.au_scsi
results = _legacy_stage_state.results

# --- cell 52 ---
f = prepare_tsa_index(f_table=f, tsa_column="tsa_code")

# --- cell 54 ---
# In no-cache/debug/custom-boundary mode, always rebuild VDYP bootstrap results
# instead of reusing stale per-TSA pickle caches.
force_run_vdyp = 1 if _femic_no_cache else 0
vdyp_out_cache = None
curve_fit_impl = _curve_fit
si_levelquants = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}


def _should_skip_01a(tsa):
    vdyp_cache_paths = build_vdyp_cache_paths(
        tsa_code=tsa,
        vdyp_results_tsa_pickle_path_prefix=vdyp_results_tsa_pickle_path_prefix,
        vdyp_curves_smooth_tsa_feather_path_prefix=vdyp_curves_smooth_tsa_feather_path_prefix,
    )
    return should_skip_if_outputs_exist(
        resume_effective=_femic_resume_effective,
        output_paths=(
            tipsy_input_dat_path(tsa=tsa),
            tipsy_params_excel_path(
                tsa=tsa,
                tipsy_params_path_prefix=tipsy_params_path_prefix,
            ),
            vdyp_cache_paths["vdyp_curves_smooth_tsa_feather_path"],
        ),
        skip_message=f"resume: skipping 01a for tsa {tsa} (outputs exist)",
    )


def _build_01a_run_kwargs(tsa):
    stratum_col = "stratum"
    runtime_config = build_legacy_01a_runtime_config(
        tsa_code=tsa,
        resume_effective=_femic_resume_effective,
        force_run_vdyp=bool(force_run_vdyp),
        kwarg_overrides_for_tsa=None,
        vdyp_results_pickle_path=vdyp_results_pickle_path,
        vdyp_input_pandl_path=vdyp_input_pandl_path,
        vdyp_ply_feather_path=vdyp_ply_feather_path,
        vdyp_lyr_feather_path=vdyp_lyr_feather_path,
        tipsy_params_columns=tipsy_params_columns,
        tipsy_params_path_prefix=tipsy_params_path_prefix,
        vdyp_results_tsa_pickle_path_prefix=vdyp_results_tsa_pickle_path_prefix,
        vdyp_curves_smooth_tsa_feather_path_prefix=vdyp_curves_smooth_tsa_feather_path_prefix,
        parallel_worker_count=len(rc),
        vdyp_out_cache=vdyp_out_cache,
        curve_fit_impl=curve_fit_impl,
        target_area_coverage=_femic_strat_top_area_coverage,
        vdyp_sampling_mode=_femic_vdyp_sampling_mode,
        vdyp_two_pass_rebin=_femic_vdyp_two_pass_rebin,
        min_stands_per_si_bin=_femic_vdyp_min_stands_per_si_bin,
    )
    return dict(
        tsa=tsa,
        stratum_col=stratum_col,
        f=f,
        si_levels=si_levels,
        results=results,
        vdyp_results=vdyp_results,
        vdyp_curves_smooth=vdyp_curves_smooth,
        scsi_au=scsi_au,
        au_scsi=au_scsi,
        tipsy_params=tipsy_params,
        si_levelquants=si_levelquants,
        species_list=species_list,
        runtime_config=runtime_config,
    )


# --- cell 58 ---
# loop over tsas here and run notebook 01_run-tsa_step2
def _should_skip_01b(tsa):
    tipsy_curves_path, tipsy_sppcomp_path = tipsy_stage_output_paths(tsa=tsa)
    return should_skip_if_outputs_exist(
        resume_effective=_femic_resume_effective,
        output_paths=(
            tipsy_curves_path,
            tipsy_sppcomp_path,
        ),
        skip_message=f"resume: skipping 01b for tsa {tsa} (outputs exist)",
    )


def _build_01b_run_kwargs(tsa):
    runtime_config = build_legacy_01b_runtime_config(
        tipsy_params_path_prefix=tipsy_params_path_prefix,
    )
    return dict(
        tsa=tsa,
        results=results,
        au_scsi=au_scsi,
        tipsy_curves=tipsy_curves,
        vdyp_curves_smooth=vdyp_curves_smooth,
        runtime_config=runtime_config,
    )


# --- cell 64 ---
canfi_map = {
    "AC": 1211,
    "AT": 1201,
    "BL": 304,
    "CW": 301,
    "EP": 1303,
    "FD": 500,
    "FDI": 500,
    "FDC": 500,
    "HW": 402,
    "PL": 204,
    "PLI": 204,
    "SB": 101,
    "SS": 103,
    "SE": 104,
    "SW": 105,
    "SX": 100,
    "S": 100,
    "YC": 302,
}


# --- cell 65 ---
def canfi_species(stratum_code):
    s = stratum_code.split("_")[-1].split("+")[0]
    result = canfi_map.get(s)
    if result is None:
        result = canfi_map.get(s[:2], 100)
        print(
            "warning: missing CANFI mapping for species %s (stratum=%s); using %s"
            % (s, stratum_code, result)
        )
    return result


# --- cell 67 ---
def _run_post_01b_bundle_and_curve_assignment_stage(
    *,
    f_table,
    bundle_paths,
    femic_resume_effective,
    femic_no_cache,
    normalize_tsa_code_fn,
    apply_debug_rows_fn,
    checkpoint1_path,
    checkpoint5_path,
    checkpoint6_path,
    checkpoint7_path,
    legacy_data_paths,
    scsi_au,
    vdyp_curves_smooth,
    tipsy_curves,
    ria_tsas,
    canfi_species_fn,
):
    _bundle_ready = bundle_tables_ready(paths=bundle_paths)
    if femic_resume_effective and _bundle_ready:
        au_table, curve_table, curve_points_table = load_bundle_tables(
            paths=bundle_paths,
            pd_module=pd,
            normalize_tsa_code_fn=normalize_tsa_code_fn,
        )
        ensure_scsi_au_from_table(
            au_table=au_table,
            scsi_au=scsi_au,
            normalize_tsa_code_fn=normalize_tsa_code_fn,
        )
    else:
        _bundle_assembly = build_bundle_tables_from_curves(
            tsa_list=ria_tsas,
            vdyp_curves_smooth=vdyp_curves_smooth,
            tipsy_curves=tipsy_curves,
            scsi_au=scsi_au,
            canfi_species_fn=canfi_species_fn,
            pd_module=pd,
            message_fn=print,
        )
        _missing_df = _bundle_assembly.missing_au_curve_mappings
        emit_missing_au_curve_mapping_warning(
            missing_df=_missing_df, message_fn=print, top_n=10
        )
        au_table = _bundle_assembly.au_table
        curve_table = _bundle_assembly.curve_table
        curve_points_table = _bundle_assembly.curve_points_table
        if "tsa" in au_table.columns:
            au_table["tsa"] = au_table["tsa"].apply(normalize_tsa_code_fn)
        ensure_scsi_au_from_table(
            au_table=au_table,
            scsi_au=scsi_au,
            normalize_tsa_code_fn=normalize_tsa_code_fn,
        )
        write_bundle_tables(
            paths=bundle_paths,
            au_table=au_table,
            curve_table=curve_table,
            curve_points_table=curve_points_table,
        )

    f_ = f_table
    if "tsa_code" not in f_.columns and "tsa_code" in list(
        getattr(f_.index, "names", [])
    ):
        f_ = f_.reset_index("tsa_code")
    if not femic_no_cache:
        f_ = gpd.read_feather(checkpoint1_path)
        f_ = apply_debug_rows_fn(f_, "checkpoint1-reload")

    f_ = assign_thlb_raw_from_raster(
        f_table=f_,
        thlb_raster_path=legacy_data_paths.misc_thlb_tif_path,
        rio_module=rio,
        mask_fn=mask,
        np_module=np,
        row_apply_fn=_row_apply,
        out_col="thlb_raw",
    )
    f_ = filter_post_thlb_stands(f_table=f_)
    f_ = assign_stratum_codes_with_lexmatch(
        f_table=f_,
        row_apply_fn=_row_apply,
        bec_grouping=_femic_strat_bec_grouping,
        species_combo_count=_femic_strat_species_combo_count,
        include_tm_species2_for_single=_femic_strat_include_tm_species2_for_single,
    )
    f_.to_feather(checkpoint5_path)

    if au_table.empty:
        print(
            "warning: au_table is empty after 01b/bundle assembly; skipping AU/curve "
            "assignment stage (likely missing or incompatible TIPSY output for current "
            "strata)."
        )
        f_["au"] = np.nan
        f_["managed_curve_id"] = np.nan
        f_["unmanaged_curve_id"] = np.nan
        f_["curve1"] = np.nan
        f_["curve2"] = np.nan
        f_.to_feather(checkpoint6_path)
        f_.to_feather(checkpoint7_path)
        return f_, au_table, curve_table, curve_points_table

    stratum_col = "stratum"
    f_[f"{stratum_col}_matched"] = None
    f_ = assign_stratum_matches_from_au_table(
        f_table=f_,
        au_table=au_table,
        tsa_list=ria_tsas,
        stratum_col=stratum_col,
        message_fn=print,
    )
    si_levelquants_local = {"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]}
    allowed_levels_by_stratum = (
        au_table.groupby("stratum_code")["si_level"]
        .apply(lambda s: sorted({str(v) for v in s.dropna().values}))
        .to_dict()
    )
    f_, _stratum_si_stats = assign_si_levels_from_stratum_quantiles(
        f_table=f_,
        si_levelquants=si_levelquants_local,
        allowed_levels_by_stratum=allowed_levels_by_stratum,
        stratum_matched_col="stratum_matched",
        site_index_col="SITE_INDEX",
        si_level_col="si_level",
        message_fn=print,
    )
    f_ = assign_au_ids_from_scsi(
        f_table=f_,
        scsi_au=scsi_au,
        tsa_col="tsa_code",
        stratum_matched_col="stratum_matched",
        si_level_col="si_level",
        au_col="au",
    )
    if f_["au"].isnull().any():
        _missing = summarize_missing_au_mappings(
            f_table=f_,
            au_col="au",
            tsa_col="tsa_code",
            stratum_matched_col="stratum_matched",
            si_level_col="si_level",
            top_n=10,
        )
        emit_missing_au_mapping_warning(summary=_missing, message_fn=print)
    validate_nonempty_au_assignment(
        f_table=f_,
        au_col="au",
        site_index_col="SITE_INDEX",
        stratum_matched_col="stratum_matched",
        si_level_col="si_level",
    )
    f_ = f_[~f_.au.isnull()]
    f_.to_feather(checkpoint6_path)

    au_table = ensure_au_table_index(au_table=au_table, au_id_col="au_id")
    f_ = assign_curve_ids_from_au_table(
        f_table=f_,
        au_table=au_table,
        pd_module=pd,
        np_module=np,
        au_col="au",
        proj_age_col="PROJ_AGE_1",
        managed_curve_col="managed_curve_id",
        unmanaged_curve_col="unmanaged_curve_id",
        curve1_col="curve1",
        curve2_col="curve2",
        managed_age_cutoff=60,
    )
    f_.to_feather(checkpoint7_path)
    return f_, au_table, curve_table, curve_points_table


def _run_legacy_tsa_orchestration_stage(
    *,
    f_table,
    ria_tsas,
    legacy_data_paths,
    scsi_au,
    vdyp_curves_smooth,
    tipsy_curves,
):
    execute_legacy_tsa_stage(
        script_path=Path(__file__).with_name("01a_run-tsa.py"),
        module_name="run_tsa_01a",
        tsa_list=ria_tsas[:],
        should_skip_fn=_should_skip_01a,
        build_run_kwargs_fn=_build_01a_run_kwargs,
    )

    execute_legacy_tsa_stage(
        script_path=Path(__file__).with_name("01b_run-tsa.py"),
        module_name="run_tsa_01b",
        tsa_list=ria_tsas[:],
        should_skip_fn=_should_skip_01b,
        build_run_kwargs_fn=_build_01b_run_kwargs,
    )

    bundle_paths = resolve_bundle_paths(
        base_dir=legacy_data_paths.model_input_bundle_dir,
        ensure_dir=True,
    )
    return _run_post_01b_bundle_and_curve_assignment_stage(
        f_table=f_table,
        bundle_paths=bundle_paths,
        femic_resume_effective=_femic_resume_effective,
        femic_no_cache=_femic_no_cache,
        normalize_tsa_code_fn=_normalize_tsa_code,
        apply_debug_rows_fn=_apply_debug_rows,
        checkpoint1_path=ria_vri_vclr1p_checkpoint1_feather_path,
        checkpoint5_path=ria_vri_vclr1p_checkpoint5_feather_path,
        checkpoint6_path=ria_vri_vclr1p_checkpoint6_feather_path,
        checkpoint7_path=ria_vri_vclr1p_checkpoint7_feather_path,
        legacy_data_paths=legacy_data_paths,
        scsi_au=scsi_au,
        vdyp_curves_smooth=vdyp_curves_smooth,
        tipsy_curves=tipsy_curves,
        ria_tsas=ria_tsas,
        canfi_species_fn=canfi_species,
    )


f, au_table, curve_table, curve_points_table = _run_legacy_tsa_orchestration_stage(
    f_table=f,
    ria_tsas=ria_tsas,
    legacy_data_paths=_legacy_data_paths,
    scsi_au=scsi_au,
    vdyp_curves_smooth=vdyp_curves_smooth,
    tipsy_curves=tipsy_curves,
)

# --- cell 115 ---
if not _femic_no_cache:
    f = gpd.read_feather(ria_vri_vclr1p_checkpoint7_feather_path)
    f = _apply_debug_rows(f, "checkpoint7")

# --- cell 116 ---
if _femic_thlb_diagnostics:
    f.thlb_raw.describe()

# --- cell 117 ---
if _femic_thlb_diagnostics:
    f.thlb_raw.hist()

# --- cell 118 ---
f.reset_index(inplace=True)


# --- cell 119-122 ---
f = assign_thlb_area_and_flag(
    f_table=f,
    species_spruce=species_spruce,
    species_pine=species_pine,
    species_aspen=species_aspen,
    species_fir=species_fir,
    tsa_col="tsa_code",
    thlb_raw_col="thlb_raw",
    area_col="FEATURE_AREA_SQM",
    species_col="SPECIES_CD_1",
    site_index_col="SITE_INDEX",
    thlb_area_col="thlb_area",
    thlb_col="thlb",
)

# --- cell 126 ---
f.to_feather(ria_vri_vclr1p_checkpoint8_feather_path)


columns = build_stands_column_map(
    prop_names=DEFAULT_STANDS_PROP_NAMES,
    prop_types=DEFAULT_STANDS_PROP_TYPES,
)

# --- cell 133 ---
_skip_stands_shp_raw = os.environ.get("FEMIC_SKIP_STANDS_SHP")
_skip_stands_shp = should_skip_stands_export(
    skip_raw=_skip_stands_shp_raw,
    default_skip=_femic_no_cache,
)
if _skip_stands_shp:
    print(
        "debug: skipping stand shapefile export (set FEMIC_SKIP_STANDS_SHP=0 to enable)"
    )
else:
    export_stands_shapefiles(
        tsa_list=ria_tsas[:],
        f_table=f,
        au_table=au_table,
        columns_map=columns,
        output_root=_legacy_data_paths.stands_shp_dir,
        pd_module=pd,
        message_fn=print,
    )
