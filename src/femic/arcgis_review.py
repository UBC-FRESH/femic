"""ArcGIS Pro review-project helpers for FEMIC instances."""

from __future__ import annotations

import json
import os
import re
import tempfile
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from femic.arcgis_pro import (
    find_arcgis_blank_project_template,
    find_arcgis_pro_python,
    run_arcgis_python,
)
from femic.pipeline.io import resolve_windows_annex_pointer_payload_path


DEFAULT_ARCGIS_REVIEW_OUTPUT_DIR = Path("workbench/arcgis_review")
DEFAULT_ARCGIS_REVIEW_LAYER_DIR_NAME = "layers"
DEFAULT_ARCGIS_REVIEW_MAP_NAME_SUFFIX = "Review"
DEFAULT_ARCGIS_REVIEW_PROJECT_SUFFIX = "_review"


@dataclass(frozen=True)
class ReviewLayerSpec:
    """One vector layer to add to the ArcGIS review project."""

    name: str
    artifact_path: Path
    source_path: Path
    source_layer_name: str | None
    geometry_family: str
    transparency: int
    draw_order: int
    default_visibility: bool


@dataclass(frozen=True)
class ArcgisReviewProjectResult:
    """Paths and counts for one emitted ArcGIS review project."""

    project_path: Path
    manifest_path: Path
    layer_count: int
    skipped_notes: tuple[str, ...]


def default_arcgis_review_output_dir(*, instance_root: Path) -> Path:
    """Return the default output root for emitted ArcGIS review bundles."""
    return instance_root / DEFAULT_ARCGIS_REVIEW_OUTPUT_DIR


def _classify_review_layer(path: Path) -> tuple[str, int, int]:
    name = path.stem.upper()
    if "STANDS" in name:
        return "polygon", 75, 0
    if "FRAGMENTS" in name:
        return "polygon", 82, 5
    if "CHECKPOINT" in name or "THLB" in name:
        return "polygon", 68, 10
    if "FADM_TSA" in name:
        return "polygon", 0, 1000
    if "FWA_LAKES" in name:
        return "polygon", 35, 120
    if "ROAD" in name or "HIGHWAY" in name:
        return "line", 0, 900
    if "CUT_BLOCK" in name:
        return "polygon", 55, 700
    if "OGMA" in name:
        return "polygon", 45, 760
    if "PARK" in name or "PROTECTED" in name:
        return "polygon", 40, 780
    if "WILDLIFE" in name or "UNGULATE" in name or "WHA" in name:
        return "polygon", 50, 770
    if "TERRAIN" in name or "BURN" in name or "VISUAL" in name:
        return "polygon", 55, 740
    if "BOUNDARIES" in name or "TFL" in name or "BCTS" in name:
        return "polygon", 25, 850
    if "TENURE" in name or "LIC" in name:
        return "polygon", 45, 730
    if "BEC" in name or "VEG_COMP" in name:
        return "polygon", 70, 200
    if "CONTOUR" in name:
        return "line", 0, 950
    return "polygon", 60, 500


def _resolve_gpkg_layer_name(path: Path) -> str | None:
    resolved = resolve_windows_annex_pointer_payload_path(path)
    try:
        import fiona  # type: ignore[import-untyped]

        layers = list(fiona.listlayers(resolved))
    except Exception:
        layers = []
    if layers:
        return str(layers[0])
    return None


def _iter_reviewable_vector_artifacts(
    instance_root: Path,
) -> tuple[list[Path], list[str]]:
    root = instance_root.resolve()
    candidates: list[Path] = []
    skipped_notes: list[str] = []
    skipped_smoke_artifacts = 0
    search_roots = (
        root / "data",
        root / "output",
    )
    seen: set[Path] = set()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for suffix in ("*.shp", "*.gpkg"):
            for path in sorted(search_root.rglob(suffix)):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                try:
                    relative_path = resolved.relative_to(root)
                except ValueError:
                    relative_path = resolved
                if len(relative_path.parts) >= 4 and relative_path.parts[:4] == (
                    "data",
                    "downloads",
                    "bcdc",
                    "smoke",
                ):
                    skipped_smoke_artifacts += 1
                    continue
                if resolved in seen:
                    continue
                seen.add(resolved)
                candidates.append(resolved)
    if skipped_smoke_artifacts:
        skipped_notes.append(
            "Skipped "
            f"{skipped_smoke_artifacts} smoke-scoped cached BCDC review layer(s) under "
            "data/downloads/bcdc/smoke."
        )
    if not candidates:
        skipped_notes.append(
            "No instance-local .shp or .gpkg review layers were discovered under data/ or output/."
        )
    return candidates, skipped_notes


def _dedupe_layer_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    deduped: list[str] = []
    for name in names:
        count = seen.get(name, 0) + 1
        seen[name] = count
        deduped.append(name if count == 1 else f"{name} ({count})")
    return deduped


def discover_arcgis_review_layers(
    *, instance_root: Path
) -> tuple[list[ReviewLayerSpec], tuple[str, ...]]:
    """Discover reviewable vector layers from one FEMIC instance root."""
    artifacts, skipped_notes = _iter_reviewable_vector_artifacts(instance_root)
    display_names = _dedupe_layer_names([path.stem for path in artifacts])
    specs: list[ReviewLayerSpec] = []
    for artifact_path, display_name in zip(artifacts, display_names, strict=True):
        geometry_family, transparency, draw_order = _classify_review_layer(
            artifact_path
        )
        specs.append(
            ReviewLayerSpec(
                name=display_name,
                artifact_path=artifact_path,
                source_path=resolve_windows_annex_pointer_payload_path(artifact_path),
                source_layer_name=(
                    _resolve_gpkg_layer_name(artifact_path)
                    if artifact_path.suffix.lower() == ".gpkg"
                    else None
                ),
                geometry_family=geometry_family,
                transparency=transparency,
                draw_order=draw_order,
                default_visibility=False,
            )
        )
    specs.sort(
        key=lambda item: (
            item.draw_order,
            item.name.casefold(),
            str(item.artifact_path).casefold(),
        )
    )
    return specs, tuple(skipped_notes)


def _sanitize_project_name(project_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", project_name.strip())
    return cleaned.strip("._-") or "arcgis_review"


def _stage_gpkg_layer_for_arcgis(*, spec: ReviewLayerSpec, staging_root: Path) -> Path:
    import geopandas as gpd  # type: ignore[import-untyped]

    safe_name = _sanitize_project_name(spec.name)
    layer_root = staging_root / safe_name
    layer_root.mkdir(parents=True, exist_ok=True)
    staged_path = layer_root / f"{safe_name}.shp"
    if staged_path.exists():
        return staged_path
    read_kwargs: dict[str, str] = {}
    if spec.source_layer_name:
        read_kwargs["layer"] = spec.source_layer_name
    table = gpd.read_file(spec.artifact_path, **read_kwargs)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Column names longer than 10 characters will be truncated when saved to ESRI Shapefile.",
        )
        warnings.filterwarnings(
            "ignore",
            message="Normalized/laundered field name: .*",
            category=RuntimeWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message="Value '.*' of field .* has been truncated to 254 characters.*",
            category=RuntimeWarning,
        )
        table.to_file(staged_path, index=False)
    return staged_path


def _stage_review_layer_sources_for_arcgis(
    *,
    specs: list[ReviewLayerSpec],
    staging_root: Path,
) -> tuple[list[ReviewLayerSpec], tuple[str, ...]]:
    prepared_specs: list[ReviewLayerSpec] = []
    notes: list[str] = []
    staged_gpkg_count = 0
    for spec in specs:
        if spec.artifact_path.suffix.lower() != ".gpkg":
            prepared_specs.append(spec)
            continue
        staged_path = _stage_gpkg_layer_for_arcgis(spec=spec, staging_root=staging_root)
        prepared_specs.append(
            ReviewLayerSpec(
                name=spec.name,
                artifact_path=spec.artifact_path,
                source_path=staged_path,
                source_layer_name=None,
                geometry_family=spec.geometry_family,
                transparency=spec.transparency,
                draw_order=spec.draw_order,
                default_visibility=spec.default_visibility,
            )
        )
        staged_gpkg_count += 1
    if staged_gpkg_count:
        notes.append(
            "Staged "
            f"{staged_gpkg_count} GeoPackage review layer(s) as shapefiles for ArcGIS Pro "
            "project compatibility."
        )
    return prepared_specs, tuple(notes)


def _default_project_name(instance_root: Path) -> str:
    return f"{instance_root.name}{DEFAULT_ARCGIS_REVIEW_PROJECT_SUFFIX}"


ARCGIS_REVIEW_PROJECT_BUILDER_CODE = r"""
from __future__ import annotations

import json
from pathlib import Path

import arcpy


def _write_layer_file(
    source_path: str,
    source_layer_name: str | None,
    layer_file: str,
    layer_name: str,
) -> None:
    layer_file_path = Path(layer_file)
    layer_file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_layer_name = f"tmp_{layer_name}".replace(" ", "_").replace("-", "_")
    if arcpy.Exists(temp_layer_name):
        arcpy.management.Delete(temp_layer_name)
    if arcpy.Exists(str(layer_file_path)):
        arcpy.management.Delete(str(layer_file_path))
    if source_layer_name:
        previous_workspace = arcpy.env.workspace
        try:
            arcpy.env.workspace = source_path
            feature_classes = arcpy.ListFeatureClasses() or []
            selected_name = source_layer_name
            if selected_name not in feature_classes:
                main_name = f"main.{selected_name}"
                if main_name in feature_classes:
                    selected_name = main_name
                elif len(feature_classes) == 1:
                    selected_name = feature_classes[0]
            arcpy.management.MakeFeatureLayer(selected_name, temp_layer_name)
        finally:
            arcpy.env.workspace = previous_workspace
    else:
        arcpy.management.MakeFeatureLayer(source_path, temp_layer_name)
    arcpy.management.SaveToLayerFile(temp_layer_name, str(layer_file_path), "ABSOLUTE")
    arcpy.management.Delete(temp_layer_name)


def _apply_layer_defaults(layer: object, spec: dict[str, object]) -> None:
    try:
        layer.name = str(spec["name"])
    except Exception:
        pass
    try:
        layer.transparency = int(spec["transparency"])
    except Exception:
        pass
    try:
        layer.visible = bool(spec["default_visibility"])
    except Exception:
        pass


payload_path = Path(__import__("sys").argv[1])
payload = json.loads(payload_path.read_text(encoding="utf-8"))
blank_aprx = Path(payload["blank_aprx_path"])
project_path = Path(payload["project_path"])
manifest_path = Path(payload["manifest_path"])
layer_file_root = Path(payload["layer_file_root"])
project_path.parent.mkdir(parents=True, exist_ok=True)
layer_file_root.mkdir(parents=True, exist_ok=True)
if project_path.exists():
    project_path.unlink()

aprx = arcpy.mp.ArcGISProject(str(blank_aprx))
aprx.saveACopy(str(project_path))
aprx = arcpy.mp.ArcGISProject(str(project_path))
map_obj = aprx.listMaps()[0]
map_obj.name = payload["map_name"]

added_layers = []
boundary_layer = None
for spec in payload["layers"]:
    layer_file_path = layer_file_root / f"{spec['name']}.lyrx"
    _write_layer_file(
        str(spec["source_path"]),
        spec.get("source_layer_name"),
        str(layer_file_path),
        str(spec["name"]),
    )
    map_obj.addLayer(arcpy.mp.LayerFile(str(layer_file_path)), "TOP")
    layer = map_obj.listLayers()[0]
    _apply_layer_defaults(layer, spec)
    upper_name = str(spec["name"]).upper()
    if boundary_layer is None and ("FADM_TSA" in upper_name or "BOUNDARY" in upper_name):
        boundary_layer = layer
    added_layers.append(
        {
            "name": spec["name"],
            "artifact_path": spec["artifact_path"],
            "source_path": spec["source_path"],
            "source_layer_name": spec.get("source_layer_name"),
            "geometry_family": spec["geometry_family"],
            "transparency": spec["transparency"],
            "draw_order": spec["draw_order"],
            "default_visibility": spec["default_visibility"],
            "layer_file": str(layer_file_path),
        }
    )

if boundary_layer is not None:
    try:
        map_obj.defaultCamera.setExtent(boundary_layer.getExtent())
    except Exception:
        pass

aprx.save()
manifest_path.write_text(
    json.dumps(
        {
            "project_path": str(project_path),
            "layer_count": len(added_layers),
            "layers": added_layers,
            "skipped_notes": payload.get("skipped_notes", []),
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(project_path)
print(manifest_path)
"""


def build_arcgis_review_project(
    *,
    instance_root: Path,
    output_dir: Path | None = None,
    project_name: str | None = None,
    arcgis_runner: Callable[..., object] = run_arcgis_python,
) -> ArcgisReviewProjectResult:
    """Emit a manifest-backed ArcGIS Pro review project for one FEMIC instance."""
    if os.name != "nt":
        raise RuntimeError(
            "ArcGIS review project emit is supported on Windows only because it depends on ArcGIS Pro."
        )
    arcgis_python = find_arcgis_pro_python()
    if arcgis_python is None:
        raise FileNotFoundError(
            "ArcGIS Pro Python not found. Install ArcGIS Pro or set ARCGIS_PRO_PYTHON / "
            "ARCGIS_PRO_PYTHON_WRAPPER before running femic prep arcgis-review-project."
        )
    blank_aprx_path = find_arcgis_blank_project_template(arcgis_python)
    if blank_aprx_path is None:
        raise FileNotFoundError(
            "ArcGIS Pro Blank.aprx template not found. Verify the local ArcGIS Pro installation."
        )

    resolved_instance_root = instance_root.expanduser().resolve()
    resolved_output_dir = (
        output_dir.expanduser().resolve()
        if output_dir is not None
        else default_arcgis_review_output_dir(instance_root=resolved_instance_root)
    )
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    safe_project_name = _sanitize_project_name(
        project_name or _default_project_name(resolved_instance_root)
    )
    project_path = resolved_output_dir / f"{safe_project_name}.aprx"
    manifest_path = resolved_output_dir / f"{safe_project_name}_manifest.json"
    layer_file_root = resolved_output_dir / DEFAULT_ARCGIS_REVIEW_LAYER_DIR_NAME
    staging_root = resolved_output_dir / "sources"
    specs, skipped_notes = discover_arcgis_review_layers(
        instance_root=resolved_instance_root
    )
    prepared_specs, preparation_notes = _stage_review_layer_sources_for_arcgis(
        specs=specs,
        staging_root=staging_root,
    )
    payload = {
        "blank_aprx_path": str(blank_aprx_path),
        "project_path": str(project_path),
        "manifest_path": str(manifest_path),
        "layer_file_root": str(layer_file_root),
        "map_name": f"{resolved_instance_root.name} {DEFAULT_ARCGIS_REVIEW_MAP_NAME_SUFFIX}",
        "layers": [
            {
                **asdict(spec),
                "artifact_path": str(spec.artifact_path),
                "source_path": str(spec.source_path),
            }
            for spec in prepared_specs
        ],
        "skipped_notes": [*skipped_notes, *preparation_notes],
    }
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as payload_file:
        json.dump(payload, payload_file, indent=2)
        payload_file.write("\n")
        payload_path = Path(payload_file.name)
    try:
        arcgis_runner(
            code=ARCGIS_REVIEW_PROJECT_BUILDER_CODE,
            args=[str(payload_path)],
        )
    finally:
        payload_path.unlink(missing_ok=True)
    return ArcgisReviewProjectResult(
        project_path=project_path,
        manifest_path=manifest_path,
        layer_count=len(prepared_specs),
        skipped_notes=tuple([*skipped_notes, *preparation_notes]),
    )
