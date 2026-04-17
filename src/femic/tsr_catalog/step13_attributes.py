"""Step 13 TSR stand-attribute compilation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Callable, cast
import urllib.request
import zipfile

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
import pandas as pd
import rasterio  # type: ignore[import-untyped]
from rasterio.enums import Resampling  # type: ignore[import-untyped]
from rasterio.features import rasterize  # type: ignore[import-untyped]
from rasterio.merge import merge  # type: ignore[import-untyped]
from rasterio.vrt import WarpedVRT  # type: ignore[import-untyped]
from shapely.geometry import (  # type: ignore[import-untyped]
    GeometryCollection,
    LineString,
    MultiLineString,
    box,
)
from shapely.geometry.base import BaseGeometry  # type: ignore[import-untyped]
from shapely.ops import linemerge, nearest_points, split, unary_union  # type: ignore[import-untyped]

from femic.bcdc_catalog import resolve_bcdc_candidates
from femic.bcdc_fetch import BC_ALBERS_EPSG
from femic.pipeline.bundle import assign_curve_ids_from_au_table, tsa_curve_id_prefix
from femic.pipeline.tsa import (
    assign_au_ids_from_scsi,
    assign_si_levels_from_stratum_quantiles,
    assign_stratum_matches_from_au_table,
    normalize_tsa_code,
    validate_nonempty_au_assignment,
)
from femic.pipeline.vri import assign_stratum_codes_with_lexmatch

from .recipes import (
    TsrRecipeError,
    default_tsr_source_layers_recipe_path,
    load_tsr_source_layers_recipe,
)

_STEP13_ATTRIBUTE_OUTPUT_RELATIVE_PATH = Path(
    "data/tsr/lhlb_curve_ready_checkpoint.feather"
)
_STEP13_ATTRIBUTE_AUDIT_BASENAME = "thlb_step13_compile_attributes"
_STEP13_DEM_QUERY = "digital elevation model for british columbia cded 1 250 000"
_STEP13_DEM_TILE_SUFFIX = "_e.dem.zip"
_STEP13_DEM_DOWNLOAD_SLUG = (
    "digital_elevation_model_for_british_columbia_cded_1_250_000"
)
_STEP13_DEM_SOURCE_ENTRY_ID = "bc_dem_cded_250k"
_STEP13_HIGHWAY_SOURCE_ENTRY_ID = "whse_imagery_and_base_maps_mot_highway_profiles_sp"
_STEP13_DEFAULT_SLOPE_THRESHOLD_EAST = 70.0
_STEP13_DEFAULT_SLOPE_THRESHOLD_WEST = 40.0
_STEP13_STRAT_BEC_GROUPING = "zone"
_STEP13_STRAT_SPECIES_COMBO_COUNT = 1
_STEP13_STRAT_INCLUDE_TM_SPECIES2_FOR_SINGLE = True
_STEP13_SI_LEVEL_QUANTILES: dict[str, list[int]] = {
    "L": [5, 20, 35],
    "M": [35, 50, 65],
    "H": [65, 80, 95],
}


@dataclass(frozen=True)
class TsrThlbStep13AttributeCompileResult:
    """Summary of one step-13 checkpoint-attribute compilation run."""

    instance_root: Path
    checkpoint_path: Path
    output_path: Path
    audit_path: Path
    dem_dataset_page_url: str
    dem_resource_root_url: str
    dem_tile_ids: tuple[str, ...]
    dem_tile_paths: tuple[Path, ...]
    highway_artifact_path: Path
    highway_filter_field: str
    highway_filter_value: str
    stand_count: int
    slope_value_count: int
    highway_side_counts: dict[str, int]
    steep_slope_flag_count: int
    curve_ready_row_count: int
    missing_curve1_count: int


def _row_apply(
    df: pd.DataFrame, func: Callable[[pd.Series], object], axis: int = 1
) -> pd.Series:
    del axis
    return cast(pd.Series, df.apply(func, axis="columns"))


def default_tsr_thlb_step13_attribute_output_path(*, instance_root: Path) -> Path:
    """Return the default enriched checkpoint output path for TSR step 13."""

    return instance_root.expanduser().resolve() / _STEP13_ATTRIBUTE_OUTPUT_RELATIVE_PATH


def compile_tsr_thlb_step13_attributes(
    *,
    instance_root: Path,
    checkpoint_path: Path | None = None,
    output_path: Path | None = None,
) -> TsrThlbStep13AttributeCompileResult:
    """Compile the TSR step-13 stand attributes onto the curve-ready checkpoint."""

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_checkpoint_path = (
        checkpoint_path.expanduser().resolve()
        if checkpoint_path is not None
        else resolved_instance_root / "data" / "ria_vri_vclr1p_checkpoint7.feather"
    )
    if not resolved_checkpoint_path.exists():
        raise TsrRecipeError(
            f"TSR step-13 checkpoint feather not found: {resolved_checkpoint_path}"
        )
    resolved_output_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else default_tsr_thlb_step13_attribute_output_path(
            instance_root=resolved_instance_root
        )
    )
    audit_path = _default_step13_attribute_audit_path(
        instance_root=resolved_instance_root
    )

    checkpoint = gpd.read_feather(resolved_checkpoint_path)
    if checkpoint.crs is None:
        checkpoint = checkpoint.set_crs(BC_ALBERS_EPSG)
    else:
        checkpoint = checkpoint.to_crs(BC_ALBERS_EPSG)
    if "MAP_ID" not in checkpoint.columns:
        raise TsrRecipeError(
            "TSR step-13 attribute compilation requires a `MAP_ID` checkpoint column."
        )
    if "geometry" not in checkpoint.columns:
        raise TsrRecipeError(
            "TSR step-13 attribute compilation requires checkpoint geometry."
        )

    dem_dataset_page_url, dem_resource_root_url, dem_tile_ids, dem_tile_paths = (
        _prepare_dem_tile_paths(
            checkpoint=checkpoint, instance_root=resolved_instance_root
        )
    )
    slope_percent, slope_transform = _build_slope_percent_raster(
        checkpoint=checkpoint,
        dem_paths=dem_tile_paths,
    )
    slope_series = _summarize_polygon_median_raster_values(
        checkpoint=checkpoint,
        raster_values=slope_percent,
        transform=slope_transform,
    )
    highway_artifact_path, highway_geometry = _load_highway_97_geometry(
        instance_root=resolved_instance_root
    )
    highway_side = _classify_checkpoint_side_of_highway(
        checkpoint=checkpoint,
        highway_geometry=highway_geometry,
    )
    steep_slope_flag = _derive_step13_steep_slope_flag(
        slope_series=slope_series,
        highway_side=highway_side,
    )

    enriched = checkpoint.copy()
    enriched["femic_slope_pct_median"] = slope_series.astype(float)
    enriched["femic_hwy97_side"] = highway_side
    enriched["femic_step13_steep_slope_flag"] = steep_slope_flag
    enriched = _assign_curve_ready_bundle_fields(
        checkpoint=enriched,
        instance_root=resolved_instance_root,
    )
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_feather(resolved_output_path)

    side_counts = {
        str(key): int(value)
        for key, value in highway_side.value_counts(dropna=False).items()
    }
    slope_value_count = int(slope_series.notna().sum())
    steep_slope_flag_count = int(steep_slope_flag.sum())
    missing_curve1_count = int(pd.Series(enriched.get("curve1")).isna().sum())
    audit_payload = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "instance_root": str(resolved_instance_root),
        "checkpoint_path": str(resolved_checkpoint_path),
        "output_path": str(resolved_output_path),
        "dem": {
            "query": _STEP13_DEM_QUERY,
            "dataset_page_url": dem_dataset_page_url,
            "resource_root_url": dem_resource_root_url,
            "tile_ids": list(dem_tile_ids),
            "tile_paths": [str(path) for path in dem_tile_paths],
        },
        "highway_97": {
            "source_entry_id": _STEP13_HIGHWAY_SOURCE_ENTRY_ID,
            "artifact_path": str(highway_artifact_path),
            "filter_field": "HIGHWAY_NUMBER",
            "filter_value": "97",
        },
        "checkpoint_summary": {
            "stand_count": int(len(enriched)),
            "slope_value_count": slope_value_count,
            "highway_side_counts": side_counts,
            "steep_slope_flag_count": steep_slope_flag_count,
            "curve_ready_row_count": int(len(enriched)),
            "missing_curve1_count": missing_curve1_count,
        },
        "step13_rule": {
            "east_threshold_pct": _STEP13_DEFAULT_SLOPE_THRESHOLD_EAST,
            "west_threshold_pct": _STEP13_DEFAULT_SLOPE_THRESHOLD_WEST,
            "flag_definition": (
                "east of Highway 97 and slope > 70 percent, or west of Highway 97 "
                "and slope > 40 percent"
            ),
        },
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")

    return TsrThlbStep13AttributeCompileResult(
        instance_root=resolved_instance_root,
        checkpoint_path=resolved_checkpoint_path,
        output_path=resolved_output_path,
        audit_path=audit_path,
        dem_dataset_page_url=dem_dataset_page_url,
        dem_resource_root_url=dem_resource_root_url,
        dem_tile_ids=dem_tile_ids,
        dem_tile_paths=dem_tile_paths,
        highway_artifact_path=highway_artifact_path,
        highway_filter_field="HIGHWAY_NUMBER",
        highway_filter_value="97",
        stand_count=len(enriched),
        slope_value_count=slope_value_count,
        highway_side_counts=side_counts,
        steep_slope_flag_count=steep_slope_flag_count,
        curve_ready_row_count=len(enriched),
        missing_curve1_count=missing_curve1_count,
    )


def _assign_curve_ready_bundle_fields(
    *,
    checkpoint: gpd.GeoDataFrame,
    instance_root: Path,
) -> gpd.GeoDataFrame:
    bundle_root = instance_root / "data" / "model_input_bundle"
    au_table_path = bundle_root / "au_table.csv"
    if not au_table_path.exists():
        raise TsrRecipeError(
            "TSR late-stage curve-ready promotion requires `data/model_input_bundle/au_table.csv`."
        )
    au_table = pd.read_csv(au_table_path)
    if au_table.empty:
        raise TsrRecipeError(
            "TSR late-stage curve-ready promotion requires a non-empty AU table."
        )

    tsa_values = sorted(
        {
            normalize_tsa_code(value)
            for value in au_table.get("tsa", pd.Series(dtype=object)).dropna().tolist()
        }
    )
    if not tsa_values:
        raise TsrRecipeError(
            "AU table does not contain any TSA codes for late-stage curve-ready promotion."
        )
    if len(tsa_values) != 1:
        raise TsrRecipeError(
            "TSR late-stage curve-ready promotion expects a single-TSA AU table, "
            f"found {tsa_values!r}."
        )
    tsa_code = tsa_values[0]
    au_table = au_table.copy()
    au_table["tsa"] = au_table["tsa"].apply(normalize_tsa_code)

    enriched = checkpoint.copy()
    enriched["tsa_code"] = tsa_code
    enriched = assign_stratum_codes_with_lexmatch(
        f_table=enriched,
        row_apply_fn=_row_apply,
        bec_grouping=_STEP13_STRAT_BEC_GROUPING,
        species_combo_count=_STEP13_STRAT_SPECIES_COMBO_COUNT,
        include_tm_species2_for_single=_STEP13_STRAT_INCLUDE_TM_SPECIES2_FOR_SINGLE,
    )
    enriched = assign_stratum_matches_from_au_table(
        f_table=enriched,
        au_table=au_table,
        tsa_list=[tsa_code],
        stratum_col="stratum",
        message_fn=lambda _msg: None,
    )
    allowed_levels_by_stratum = cast(
        dict[str, list[str]],
        au_table.groupby("stratum_code")["si_level"]
        .apply(lambda s: sorted({str(value) for value in s.dropna().values}))
        .to_dict(),
    )
    enriched, _ = assign_si_levels_from_stratum_quantiles(
        f_table=enriched,
        si_levelquants=_STEP13_SI_LEVEL_QUANTILES,
        allowed_levels_by_stratum=allowed_levels_by_stratum,
        stratum_matched_col="stratum_matched",
        site_index_col="SITE_INDEX",
        si_level_col="si_level",
        message_fn=lambda _msg: None,
    )

    scsi_au = {
        tsa_code: {
            (str(row.stratum_code), str(row.si_level)): int(float(str(row.au_id)))
            - 100000 * tsa_curve_id_prefix(tsa_code)
            for row in au_table.itertuples(index=False)
            if pd.notna(row.au_id) and pd.notna(row.stratum_code) and pd.notna(row.si_level)
        }
    }
    enriched = assign_au_ids_from_scsi(
        f_table=enriched,
        scsi_au=scsi_au,
        tsa_col="tsa_code",
        stratum_matched_col="stratum_matched",
        si_level_col="si_level",
        au_col="au",
    )
    validate_nonempty_au_assignment(
        f_table=enriched,
        au_col="au",
        site_index_col="SITE_INDEX",
        stratum_matched_col="stratum_matched",
        si_level_col="si_level",
    )
    enriched = assign_curve_ids_from_au_table(
        f_table=enriched,
        au_table=au_table,
        pd_module=pd,
        np_module=np,
        au_col="au",
        proj_age_col="PROJ_AGE_1",
        managed_curve_col="treated_curve_id",
        unmanaged_curve_col="untreated_curve_id",
        curve1_col="curve1",
        curve2_col="curve2",
        managed_age_cutoff=60,
    )
    return enriched


def _default_step13_attribute_audit_path(*, instance_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return (
        instance_root.expanduser().resolve()
        / "runtime"
        / "logs"
        / "tsr"
        / f"{_STEP13_ATTRIBUTE_AUDIT_BASENAME}.{stamp}.json"
    )


def _prepare_dem_tile_paths(
    *,
    checkpoint: gpd.GeoDataFrame,
    instance_root: Path,
) -> tuple[str, str, tuple[str, ...], tuple[Path, ...]]:
    dataset_page_url, resource_root_url = _resolve_step13_dem_metadata()
    letterblocks = _required_dem_letterblocks(checkpoint)
    download_root = (
        instance_root / "data" / "downloads" / "bcdc" / _STEP13_DEM_DOWNLOAD_SLUG
    )
    tile_ids: list[str] = []
    tile_paths: list[Path] = []
    missing_tiles: list[str] = []
    for letterblock in letterblocks:
        archive_names = _list_dem_archives_for_letterblock(
            resource_root_url=resource_root_url,
            letterblock=letterblock,
        )
        for archive_name in archive_names:
            tile_ids.append(archive_name.removesuffix(".dem.zip"))
            try:
                tile_paths.append(
                    _materialize_dem_tile(
                        archive_name=archive_name,
                        resource_root_url=resource_root_url,
                        download_root=download_root,
                    )
                )
            except Exception:
                missing_tiles.append(archive_name)
    if missing_tiles:
        raise TsrRecipeError(
            "Unable to materialize one or more required DEM tiles for TSR step 13: "
            + ", ".join(missing_tiles)
        )
    return dataset_page_url, resource_root_url, tuple(tile_ids), tuple(tile_paths)


def _resolve_step13_dem_metadata() -> tuple[str, str]:
    resolve_result = resolve_bcdc_candidates(_STEP13_DEM_QUERY, limit=5)
    top_match = resolve_result.top_match
    if top_match is None:
        raise TsrRecipeError(
            "Unable to resolve the BC DEM dataset needed for TSR step 13."
        )
    resource_root_url = ""
    for resource in top_match.resources:
        if resource.url and resource.url.startswith("https://pub.data.gov.bc.ca/"):
            resource_root_url = resource.url.rstrip("/") + "/"
            break
    if not resource_root_url:
        raise TsrRecipeError(
            "The BC DEM top match did not expose a direct public download root."
        )
    return top_match.dataset_page_url, resource_root_url


def _required_dem_letterblocks(checkpoint: gpd.GeoDataFrame) -> tuple[str, ...]:
    letterblocks = sorted(
        {
            str(value).strip().lower()[:4]
            for value in checkpoint["MAP_ID"].dropna()
            if str(value).strip()
        }
    )
    if not letterblocks:
        raise TsrRecipeError(
            "Checkpoint did not expose any MAP_ID values for TSR step-13 DEM lookup."
        )
    return tuple(letterblocks)


def _list_dem_archives_for_letterblock(
    *,
    resource_root_url: str,
    letterblock: str,
) -> tuple[str, ...]:
    letterblock_dir = _dem_letterblock_directory(letterblock)
    with urllib.request.urlopen(f"{resource_root_url}{letterblock_dir}/") as response:
        html = response.read().decode("utf-8", errors="ignore")
    archive_names = sorted(
        {
            match.group(1)
            for match in re.finditer(
                r'href="([0-9a-z]+_[ew]\.dem\.zip)"',
                html,
                flags=re.IGNORECASE,
            )
        }
    )
    if not archive_names:
        raise TsrRecipeError(
            f"No DEM archives were discoverable for letterblock `{letterblock}`."
        )
    return tuple(archive_names)


def _dem_letterblock_directory(letterblock: str) -> str:
    return letterblock[1:] if letterblock.startswith("0") else letterblock


def _materialize_dem_tile(
    *,
    archive_name: str,
    resource_root_url: str,
    download_root: Path,
) -> Path:
    tile_prefix = archive_name[:4]
    letterblock_dir = _dem_letterblock_directory(tile_prefix)
    archive_path = download_root / tile_prefix / archive_name
    dem_path = archive_path.with_suffix("")
    if dem_path.exists():
        return dem_path
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        tile_url = f"{resource_root_url}{letterblock_dir}/{archive_name}"
        _download_url_to_path(tile_url, archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        dem_members = [
            member
            for member in archive.namelist()
            if member.lower().endswith(".dem")
            and Path(member).name.lower() == dem_path.name
        ]
        if not dem_members:
            dem_members = [
                member
                for member in archive.namelist()
                if member.lower().endswith(".dem")
            ]
        if not dem_members:
            raise TsrRecipeError(
                f"DEM archive did not contain a .dem file: {archive_path}"
            )
        archive.extract(dem_members[0], path=archive_path.parent)
        extracted = archive_path.parent / dem_members[0]
    if extracted != dem_path:
        extracted.rename(dem_path)
    return dem_path


def _download_url_to_path(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
        handle.write(response.read())


def _build_slope_percent_raster(
    *,
    checkpoint: gpd.GeoDataFrame,
    dem_paths: tuple[Path, ...],
) -> tuple[np.ndarray, rasterio.Affine]:
    bounds = tuple(float(value) for value in checkpoint.total_bounds)
    sources = []
    vrts = []
    try:
        for path in dem_paths:
            source = rasterio.open(path)
            sources.append(source)
            vrts.append(
                WarpedVRT(
                    source,
                    crs=BC_ALBERS_EPSG,
                    resampling=Resampling.bilinear,
                )
            )
        mosaic, transform = merge(vrts, bounds=bounds, masked=True)
    finally:
        for vrt in vrts:
            vrt.close()
        for source in sources:
            source.close()
    band = mosaic[0]
    if np.ma.isMaskedArray(band):
        elevation = np.ma.asarray(band, dtype=np.float32).filled(np.nan)
    else:
        elevation = np.asarray(band, dtype=np.float32)
    slope_percent = _compute_slope_percent(
        elevation=elevation,
        xres=abs(float(transform.a)),
        yres=abs(float(transform.e)),
    )
    slope_percent[~np.isfinite(elevation)] = np.nan
    return slope_percent.astype(np.float32), transform


def _compute_slope_percent(
    *,
    elevation: np.ndarray,
    xres: float,
    yres: float,
) -> np.ndarray:
    grad_y = np.zeros_like(elevation, dtype=np.float32)
    grad_x = np.zeros_like(elevation, dtype=np.float32)
    if elevation.shape[0] > 1:
        grad_y = np.gradient(elevation, yres, axis=0)
    if elevation.shape[1] > 1:
        grad_x = np.gradient(elevation, xres, axis=1)
    return np.sqrt(np.square(grad_x) + np.square(grad_y)) * 100.0


def _summarize_polygon_median_raster_values(
    *,
    checkpoint: gpd.GeoDataFrame,
    raster_values: np.ndarray,
    transform: rasterio.Affine,
) -> pd.Series:
    zone_ids = np.arange(1, len(checkpoint) + 1, dtype=np.int32)
    zones = rasterize(
        (
            (geometry, int(zone_id))
            for geometry, zone_id in zip(checkpoint.geometry, zone_ids, strict=False)
            if geometry is not None and not geometry.is_empty
        ),
        out_shape=raster_values.shape,
        transform=transform,
        fill=0,
        all_touched=False,
        dtype=np.int32,
    )
    valid = (zones > 0) & np.isfinite(raster_values)
    medians = pd.Series(np.nan, index=checkpoint.index, dtype=float)
    if valid.any():
        values = pd.DataFrame(
            {
                "zone_id": zones[valid].astype(np.int32),
                "raster_value": raster_values[valid].astype(np.float32),
            }
        )
        grouped = values.groupby("zone_id", sort=False)["raster_value"].median()
        grouped_values = grouped.to_dict()
        for zone_id, value in grouped_values.items():
            medians.iat[int(cast(int, zone_id)) - 1] = float(value)
    missing_mask = medians.isna()
    if missing_mask.any():
        medians.loc[missing_mask] = _sample_raster_at_representative_points(
            checkpoint=checkpoint.loc[missing_mask],
            raster_values=raster_values,
            transform=transform,
        ).to_numpy()
    return medians


def _sample_raster_at_representative_points(
    *,
    checkpoint: gpd.GeoDataFrame,
    raster_values: np.ndarray,
    transform: rasterio.Affine,
) -> pd.Series:
    samples = pd.Series(np.nan, index=checkpoint.index, dtype=float)
    inverse_transform = ~transform
    row_count, col_count = raster_values.shape
    for row_index, point in checkpoint.geometry.representative_point().items():
        col_f, row_f = inverse_transform * (point.x, point.y)
        col = int(np.floor(col_f))
        row = int(np.floor(row_f))
        if 0 <= row < row_count and 0 <= col < col_count:
            value = float(raster_values[row, col])
            if np.isfinite(value):
                samples.at[row_index] = value
    return samples


def _load_highway_97_geometry(*, instance_root: Path) -> tuple[Path, LineString]:
    source_recipe = load_tsr_source_layers_recipe(
        default_tsr_source_layers_recipe_path(instance_root=instance_root)
    )
    source_entry_map = {
        str(entry.get("entry_id", "")).strip(): dict(entry)
        for entry in source_recipe.entries
        if isinstance(entry, dict)
    }
    source_entry = source_entry_map.get(_STEP13_HIGHWAY_SOURCE_ENTRY_ID)
    if source_entry is None:
        raise TsrRecipeError(
            f"TSR source-layer recipe is missing `{_STEP13_HIGHWAY_SOURCE_ENTRY_ID}`."
        )
    artifact_path_text = str(source_entry.get("artifact_path", "")).strip()
    if not artifact_path_text:
        raise TsrRecipeError(
            f"TSR source-layer recipe entry `{_STEP13_HIGHWAY_SOURCE_ENTRY_ID}` has no artifact path."
        )
    artifact_path = (instance_root / artifact_path_text).expanduser().resolve()
    if not artifact_path.exists():
        raise TsrRecipeError(f"Highway 97 artifact not found: {artifact_path}")
    layer = gpd.read_file(artifact_path)
    if layer.crs is None:
        layer = layer.set_crs(BC_ALBERS_EPSG)
    else:
        layer = layer.to_crs(BC_ALBERS_EPSG)
    if "HIGHWAY_NUMBER" not in layer.columns:
        raise TsrRecipeError(
            f"Highway profile artifact is missing `HIGHWAY_NUMBER`: {artifact_path}"
        )
    highway = layer.loc[layer["HIGHWAY_NUMBER"].astype(str).str.strip() == "97"].copy()
    if highway.empty:
        raise TsrRecipeError(
            "Highway profile artifact did not contain Highway 97 features."
        )
    unioned = unary_union(highway.geometry.tolist())
    line = _coerce_primary_linestring(unioned)
    if line is None or line.is_empty:
        raise TsrRecipeError("Unable to derive a working Highway 97 line geometry.")
    return artifact_path, line


def _coerce_primary_linestring(geometry: object) -> LineString | None:
    if isinstance(geometry, LineString):
        return geometry
    if isinstance(geometry, MultiLineString):
        line_parts = [part for part in geometry.geoms if isinstance(part, LineString)]
        if not line_parts:
            return None
        return max(line_parts, key=lambda part: part.length)
    if isinstance(geometry, GeometryCollection):
        parts: list[LineString] = []
        for item in geometry.geoms:
            if isinstance(item, LineString):
                parts.append(item)
            elif isinstance(item, MultiLineString):
                parts.extend(
                    part for part in item.geoms if isinstance(part, LineString)
                )
        if not parts:
            return None
        merged = linemerge(parts)
        return _coerce_primary_linestring(merged)
    return None


def _classify_checkpoint_side_of_highway(
    *,
    checkpoint: gpd.GeoDataFrame,
    highway_geometry: LineString,
) -> pd.Series:
    extent_polygon = box(*checkpoint.total_bounds).buffer(1000.0)
    west_polygon, east_polygon = _split_extent_by_highway(
        extent_polygon=extent_polygon,
        highway_geometry=highway_geometry,
    )
    side = pd.Series(index=checkpoint.index, dtype="object")
    if west_polygon is not None and east_polygon is not None:
        west_area = checkpoint.geometry.intersection(west_polygon).area
        east_area = checkpoint.geometry.intersection(east_polygon).area
        side.loc[east_area > west_area] = "east"
        side.loc[west_area > east_area] = "west"
    unresolved = side.isna()
    if unresolved.any():
        side.loc[unresolved] = _classify_points_relative_to_highway(
            points=checkpoint.loc[unresolved].geometry.representative_point(),
            highway_geometry=highway_geometry,
        ).to_numpy()
    return side.astype("string")


def _split_extent_by_highway(
    *,
    extent_polygon: BaseGeometry,
    highway_geometry: LineString,
) -> tuple[BaseGeometry | None, BaseGeometry | None]:
    extended_line = _extend_linestring(
        line=highway_geometry,
        extension_distance=max(
            extent_polygon.bounds[2] - extent_polygon.bounds[0],
            extent_polygon.bounds[3] - extent_polygon.bounds[1],
        )
        * 2.0,
    )
    pieces = split(extent_polygon, extended_line)
    polygons = [
        piece
        for piece in pieces.geoms
        if piece.geom_type in {"Polygon", "MultiPolygon"}
    ]
    if len(polygons) < 2:
        return None, None
    sorted_polygons = sorted(polygons, key=lambda item: item.centroid.x)
    west_polygon = sorted_polygons[0]
    east_polygon = unary_union(sorted_polygons[1:])
    return west_polygon, east_polygon


def _extend_linestring(*, line: LineString, extension_distance: float) -> LineString:
    coords = list(line.coords)
    if len(coords) < 2:
        return line
    start = np.asarray(coords[0], dtype=float)
    start_next = np.asarray(coords[1], dtype=float)
    end_prev = np.asarray(coords[-2], dtype=float)
    end = np.asarray(coords[-1], dtype=float)
    start_vector = start - start_next
    end_vector = end - end_prev
    start_unit = start_vector / np.linalg.norm(start_vector)
    end_unit = end_vector / np.linalg.norm(end_vector)
    extended_start = tuple((start + start_unit * extension_distance).tolist())
    extended_end = tuple((end + end_unit * extension_distance).tolist())
    return LineString([extended_start, *coords, extended_end])


def _classify_points_relative_to_highway(
    *,
    points: gpd.GeoSeries,
    highway_geometry: LineString,
) -> pd.Series:
    side = pd.Series(index=points.index, dtype="object")
    for row_index, point in points.items():
        _, nearest_on_highway = nearest_points(point, highway_geometry)
        side.at[row_index] = "east" if point.x > nearest_on_highway.x else "west"
    return side


def _derive_step13_steep_slope_flag(
    *,
    slope_series: pd.Series,
    highway_side: pd.Series,
) -> pd.Series:
    east_mask = highway_side.eq("east") & slope_series.gt(
        _STEP13_DEFAULT_SLOPE_THRESHOLD_EAST
    )
    west_mask = highway_side.eq("west") & slope_series.gt(
        _STEP13_DEFAULT_SLOPE_THRESHOLD_WEST
    )
    return (east_mask | west_mask).fillna(False).astype(bool)
