"""Build a raw-source GLB clip for one named TSA."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile

import geopandas as gpd  # type: ignore[import-untyped]

from femic.arcgis_pro import run_arcgis_python

DEFAULT_RAW_VRI_2024_ZIP_RELATIVE_PATH = Path(
    "bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
)
DEFAULT_INSTANCE_TSA_BOUNDARY_RELATIVE_PATH = Path(
    "data/downloads/bcdc/WHSE_ADMIN_BOUNDARIES_FADM_TSA/WHSE_ADMIN_BOUNDARIES_FADM_TSA.gpkg"
)
DEFAULT_OUTPUT_ROOT_RELATIVE_PATH = Path("runtime/logs/glb_build")
DEFAULT_VRI_FEATURE_CLASS_NAME = "VEG_COMP_LYR_R1_POLY"
GLB_SUMMARY_JSON_NAME = "glb_summary.json"
GLB_SUMMARY_MARKDOWN_NAME = "glb_summary.md"
GLB_OUTPUT_GDB_NAME = "clipped_glb.gdb"
GLB_OUTPUT_FEATURE_CLASS_NAME = "tsa_glb_vri_2024"


@dataclass(frozen=True)
class TsaBoundarySelection:
    """Resolved active TSA boundary selection."""

    selector: str
    tsa_number: str
    tsa_name: str
    area_ha: float
    shapefile_path: Path
    source_path: Path


@dataclass(frozen=True)
class GlbBuildResult:
    """Summary of a raw-source GLB build."""

    tsa_selector: str
    tsa_number: str
    tsa_name: str
    source_zip_path: Path
    boundary_source_path: Path
    output_dir: Path
    clipped_glb_gdb_path: Path
    clipped_glb_feature_class: str
    summary_json_path: Path
    summary_markdown_path: Path
    feature_count: int
    clipped_area_ha: float
    boundary_area_ha: float
    area_delta_ha: float


def _resolve_external_data_root(*, source_root: Path) -> Path:
    env_root = os.environ.get("FEMIC_EXTERNAL_DATA_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return (source_root / "external" / "femic-public-data" / "data").resolve()


def resolve_default_raw_vri_2024_zip(*, source_root: Path) -> Path:
    """Return the default 2024 VRI zip path under FEMIC external data."""
    return (
        _resolve_external_data_root(source_root=source_root)
        / DEFAULT_RAW_VRI_2024_ZIP_RELATIVE_PATH
    ).resolve()


def resolve_default_tsa_boundary_path(*, instance_root: Path) -> Path:
    """Return the default active TSA boundary layer path for one instance."""
    return (instance_root / DEFAULT_INSTANCE_TSA_BOUNDARY_RELATIVE_PATH).resolve()


def _load_active_tsa_boundary(
    *,
    boundary_path: Path,
    tsa_selector: str,
    scratch_dir: Path,
) -> TsaBoundarySelection:
    boundary_gdf = gpd.read_file(boundary_path)
    if boundary_gdf.empty:
        raise ValueError(f"No TSA boundary rows found in {boundary_path}")
    tsa_name_field = (
        "TSA_NAME"
        if "TSA_NAME" in boundary_gdf.columns
        else "TSA_NUMBER_DESCRIPTION"
        if "TSA_NUMBER_DESCRIPTION" in boundary_gdf.columns
        else None
    )
    selector = tsa_selector.strip()
    selector_lower = selector.casefold()
    if selector.isdigit():
        selected = boundary_gdf.loc[
            boundary_gdf["TSA_NUMBER"].astype(str).str.fullmatch(selector)
        ]
    elif selector_lower.startswith("tsa_") and selector_lower[4:].isdigit():
        tsa_number = selector_lower[4:]
        selected = boundary_gdf.loc[
            boundary_gdf["TSA_NUMBER"].astype(str).str.fullmatch(tsa_number)
        ]
    else:
        if tsa_name_field is None:
            raise ValueError(
                "TSA name field missing from boundary layer "
                f"{boundary_path}; checked TSA_NAME and TSA_NUMBER_DESCRIPTION"
            )
        selected = boundary_gdf.loc[
            boundary_gdf[tsa_name_field].astype(str).str.casefold() == selector_lower
        ]
    if selected.empty:
        raise ValueError(
            f"Could not resolve TSA selector '{tsa_selector}' in {boundary_path}"
        )
    if "TSB_NUMBER" in selected.columns:
        active = selected.loc[selected["TSB_NUMBER"].isna()]
        if not active.empty:
            selected = active
    selected = selected.iloc[[0]].copy().to_crs(3005)
    boundary_area_ha = float(selected.geometry.area.sum() / 10000.0)
    tsa_number = str(int(selected.iloc[0]["TSA_NUMBER"])).zfill(2)
    tsa_name = str(
        selected.iloc[0].get("TSA_NAME")
        or selected.iloc[0].get("TSA_NUMBER_DESCRIPTION")
        or f"TSA {tsa_number}"
    )
    shapefile_root = scratch_dir / "tsa_boundary"
    if shapefile_root.exists():
        shutil.rmtree(shapefile_root)
    shapefile_root.mkdir(parents=True, exist_ok=True)
    shapefile_path = shapefile_root / f"tsa_{tsa_number}_boundary.shp"
    selected.to_file(shapefile_path)
    return TsaBoundarySelection(
        selector=tsa_selector,
        tsa_number=tsa_number,
        tsa_name=tsa_name,
        area_ha=boundary_area_ha,
        shapefile_path=shapefile_path,
        source_path=boundary_path,
    )


def _run_glb_clip_with_arcgis(
    *,
    source_feature_class_path: Path,
    boundary_shapefile_path: Path,
    output_gdb_path: Path,
    output_feature_class_name: str,
    summary_json_path: Path,
) -> None:
    code = r"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import arcpy

source_fc = sys.argv[1]
boundary_fc = sys.argv[2]
output_gdb = Path(sys.argv[3])
output_fc_name = sys.argv[4]
summary_json = Path(sys.argv[5])

arcpy.env.overwriteOutput = True
output_gdb.parent.mkdir(parents=True, exist_ok=True)
if not arcpy.Exists(str(output_gdb)):
    arcpy.management.CreateFileGDB(str(output_gdb.parent), output_gdb.name)
output_fc = str(output_gdb / output_fc_name)
if arcpy.Exists(output_fc):
    arcpy.management.Delete(output_fc)
arcpy.analysis.PairwiseClip(source_fc, boundary_fc, output_fc)
feature_count = int(arcpy.management.GetCount(output_fc).getOutput(0))
area_sq_m = 0.0
with arcpy.da.SearchCursor(output_fc, ["SHAPE@AREA"]) as cursor:
    for row in cursor:
        area_sq_m += float(row[0] or 0.0)
summary = {
    "feature_count": feature_count,
    "clipped_area_ha": area_sq_m / 10000.0,
    "output_feature_class": output_fc,
}
summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
"""
    run_arcgis_python(
        code=code,
        args=[
            str(source_feature_class_path),
            str(boundary_shapefile_path),
            str(output_gdb_path),
            output_feature_class_name,
            str(summary_json_path),
        ],
    )


def _write_glb_summary_markdown(*, result: GlbBuildResult) -> None:
    lines = [
        f"# TSA {result.tsa_number} Raw GLB Summary",
        "",
        f"- TSA selector: `{result.tsa_selector}`",
        f"- TSA name: `{result.tsa_name}`",
        f"- Raw VRI zip: `{result.source_zip_path}`",
        f"- Boundary source: `{result.boundary_source_path}`",
        f"- Boundary area (ha): `{result.boundary_area_ha:.3f}`",
        f"- Clipped stand count: `{result.feature_count}`",
        f"- Clipped stand geometry area (ha): `{result.clipped_area_ha:.3f}`",
        f"- Area delta vs boundary (ha): `{result.area_delta_ha:.3f}`",
        (
            "- Clipped GLB output: "
            f"`{result.clipped_glb_gdb_path / result.clipped_glb_feature_class}`"
        ),
        "",
        (
            "This artifact was built directly from raw source geometry. "
            "Checkpoints were not used as the input baseline."
        ),
    ]
    result.summary_markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_tsa_raw_glb(
    *,
    source_root: Path,
    instance_root: Path,
    tsa: str,
    output_dir: Path | None = None,
    source_zip_path: Path | None = None,
    boundary_path: Path | None = None,
    arcgis_runner=_run_glb_clip_with_arcgis,
) -> GlbBuildResult:
    """Clip raw 2024 provincial VRI to one TSA boundary and report GLB area."""
    resolved_source_zip_path = (
        source_zip_path.resolve()
        if source_zip_path is not None
        else resolve_default_raw_vri_2024_zip(source_root=source_root)
    )
    if not resolved_source_zip_path.exists():
        raise FileNotFoundError(
            f"Raw 2024 VRI zip not found: {resolved_source_zip_path}"
        )
    resolved_boundary_path = (
        boundary_path.resolve()
        if boundary_path is not None
        else resolve_default_tsa_boundary_path(instance_root=instance_root)
    )
    if not resolved_boundary_path.exists():
        raise FileNotFoundError(
            f"TSA boundary layer not found: {resolved_boundary_path}"
        )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    resolved_output_dir = (
        output_dir.resolve()
        if output_dir is not None
        else (
            instance_root
            / DEFAULT_OUTPUT_ROOT_RELATIVE_PATH
            / f"tsa{tsa}_raw_glb_{timestamp}"
        ).resolve()
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = resolved_output_dir / GLB_SUMMARY_JSON_NAME
    summary_markdown_path = resolved_output_dir / GLB_SUMMARY_MARKDOWN_NAME
    clipped_glb_gdb_path = resolved_output_dir / GLB_OUTPUT_GDB_NAME
    with tempfile.TemporaryDirectory(prefix="femic_glb_") as tmp_dir:
        scratch_dir = Path(tmp_dir)
        boundary_selection = _load_active_tsa_boundary(
            boundary_path=resolved_boundary_path,
            tsa_selector=tsa,
            scratch_dir=scratch_dir,
        )
        extract_root = scratch_dir / "vri_extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(resolved_source_zip_path, "r") as zf:
            zf.extractall(extract_root)
        extracted_gdb_path = extract_root / resolved_source_zip_path.stem
        if not extracted_gdb_path.exists():
            candidates = tuple(extract_root.glob("*.gdb"))
            if len(candidates) != 1:
                raise FileNotFoundError(
                    f"Could not identify extracted FileGDB under {extract_root}"
                )
            extracted_gdb_path = candidates[0]
        source_feature_class_path = extracted_gdb_path / DEFAULT_VRI_FEATURE_CLASS_NAME
        arcgis_runner(
            source_feature_class_path=source_feature_class_path,
            boundary_shapefile_path=boundary_selection.shapefile_path,
            output_gdb_path=clipped_glb_gdb_path,
            output_feature_class_name=GLB_OUTPUT_FEATURE_CLASS_NAME,
            summary_json_path=summary_json_path,
        )
        summary_payload = json.loads(summary_json_path.read_text(encoding="utf-8"))
    clipped_area_ha = float(summary_payload["clipped_area_ha"])
    feature_count = int(summary_payload["feature_count"])
    result = GlbBuildResult(
        tsa_selector=tsa,
        tsa_number=boundary_selection.tsa_number,
        tsa_name=boundary_selection.tsa_name,
        source_zip_path=resolved_source_zip_path,
        boundary_source_path=resolved_boundary_path,
        output_dir=resolved_output_dir,
        clipped_glb_gdb_path=clipped_glb_gdb_path,
        clipped_glb_feature_class=GLB_OUTPUT_FEATURE_CLASS_NAME,
        summary_json_path=summary_json_path,
        summary_markdown_path=summary_markdown_path,
        feature_count=feature_count,
        clipped_area_ha=clipped_area_ha,
        boundary_area_ha=boundary_selection.area_ha,
        area_delta_ha=clipped_area_ha - boundary_selection.area_ha,
    )
    _write_glb_summary_markdown(result=result)
    summary_payload.update(
        {
            "tsa_selector": result.tsa_selector,
            "tsa_number": result.tsa_number,
            "tsa_name": result.tsa_name,
            "source_zip_path": str(result.source_zip_path),
            "boundary_source_path": str(result.boundary_source_path),
            "output_dir": str(result.output_dir),
            "clipped_glb_gdb_path": str(result.clipped_glb_gdb_path),
            "clipped_glb_feature_class": result.clipped_glb_feature_class,
            "boundary_area_ha": result.boundary_area_ha,
            "area_delta_ha": result.area_delta_ha,
        }
    )
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2), encoding="utf-8"
    )
    return result
