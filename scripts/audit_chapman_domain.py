"""Audit the acquired Chapman Creek domain layers and LidarBC coverage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shapely.geometry import box, shape  # type: ignore[import-untyped]
from shapely.ops import unary_union  # type: ignore[import-untyped]

SCHEMA_VERSION = "femic.chapman_domain_audit.v1"
RUNTIME_ROOT = Path("runtime/p118_chapman")
LIDAR_SELECTION = Path("/tmp/opencode/chapman_lidar_selection.json")


def audit_domain(
    runtime_root: Path,
    *,
    lidar_selection: Path | None = None,
    generated_utc: str | None = None,
) -> dict[str, object]:
    """Audit the public domain layers and optional LidarBC selection."""
    root = runtime_root.expanduser().resolve()
    watersheds = _read_geojson(root / "watersheds.geojson")
    streams = _read_geojson(root / "streams.geojson")
    roads = _read_geojson(root / "roads.geojson")
    gauges = _read_geojson(root / "gauges.geojson")
    geometries = [_geometry(feature) for feature in _features(watersheds)]
    geometries = [geometry for geometry in geometries if geometry is not None]
    if not geometries:
        raise RuntimeError("No watershed polygons were found.")
    union = unary_union(geometries)
    area_ha = union.area / 10000.0
    gauge_records = [
        {
            "gauge_id": _property_text(feature, "gauge_id"),
            "station_name": _property_text(feature, "station_name"),
            "drainage_area_km2": _property_float(feature, "drainage_area_km2"),
        }
        for feature in _features(gauges)
    ]
    gauge_areas = [
        float(record["drainage_area_km2"])
        for record in gauge_records
        if isinstance(record["drainage_area_km2"], float)
    ]
    gauge_area_km2 = max(gauge_areas) if gauge_areas else None
    result: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated_utc or datetime.now(UTC).isoformat(),
        "runtime_root": str(root),
        "watershed": {
            "part_count": len(geometries),
            "area_ha": area_ha,
            "bounds_epsg3005": list(union.bounds),
            "is_valid": union.is_valid,
            "gauge_drainage_area_km2": gauge_area_km2,
            "gauge_drainage_area_ha": (
                gauge_area_km2 * 100.0 if gauge_area_km2 is not None else None
            ),
            "gauge_records": gauge_records,
            "area_ratio_to_gauge": (
                area_ha / (gauge_area_km2 * 100.0) if gauge_area_km2 else None
            ),
        },
        "layers": {
            "streams": _layer_summary(streams),
            "roads": _layer_summary(roads),
            "gauges": _layer_summary(gauges),
        },
        "gaps": [
            "Current public daily gauge series is not confirmed.",
            "Reviewed Chapman water-system receptor geometry is missing.",
            "Culvert and road-stream crossing inventory is missing.",
            "DEM mosaic, vertical datum, and native UTM tile review are pending.",
            "Hydrologist review and reviewed WS4 crosswalk are missing.",
        ],
    }
    if lidar_selection is not None and lidar_selection.is_file():
        result["lidar"] = _audit_lidar(lidar_selection, union)
    else:
        result["lidar"] = {"available": False, "reason": "selection manifest missing"}
    return result


def _audit_lidar(
    path: Path, union: Any
) -> dict[str, object]:  # Shapely geometry is untyped here.
    payload = _read_json(path)
    tiles = payload.get("tiles")
    if not isinstance(tiles, list):
        raise TypeError("LidarBC selection has no tiles list.")
    products: dict[str, dict[str, object]] = {}
    warnings: list[str] = []
    for product in ("dem", "dsm", "point_cloud"):
        selected: list[Mapping[str, object]] = [
            tile
            for tile in tiles
            if isinstance(tile, Mapping) and tile.get("product") == product
        ]
        geometries: list[object] = []
        years: set[int] = set()
        projections: set[str] = set()
        missing_vertical = 0
        for tile in selected:
            bbox = tile.get("bbox_epsg3005")
            if not isinstance(bbox, list) or len(bbox) != 4:
                continue
            geometries.append(
                box(
                    float(bbox[0]),
                    float(bbox[1]),
                    float(bbox[2]),
                    float(bbox[3]),
                )
            )
            year = tile.get("acquisition_year")
            if isinstance(year, int):
                years.add(year)
            projection = tile.get("projection")
            if isinstance(projection, str):
                projections.add(projection)
            if tile.get("vertical_datum") is None:
                missing_vertical += 1
        if geometries:
            covered = unary_union(geometries).intersection(union).area / 10000.0
        else:
            covered = 0.0
        products[product] = {
            "tile_count": len(selected),
            "intersecting_tile_count": len(geometries),
            "covered_area_ha": covered,
            "uncovered_area_ha": max(0.0, union.area / 10000.0 - covered),
            "acquisition_years": sorted(years),
            "projections": sorted(projections),
            "vertical_datum_missing": missing_vertical,
        }
        if missing_vertical:
            warnings.append(
                f"{product}: {missing_vertical} tiles have no vertical datum."
            )
    return {
        "available": True,
        "selection_manifest": str(path),
        "selection_sha256": _sha256(path),
        "products": products,
        "warnings": warnings,
    }


def _layer_summary(payload: Mapping[str, object]) -> dict[str, object]:
    features = _features(payload)
    geometries = [_geometry(feature) for feature in features]
    valid = [geometry for geometry in geometries if geometry is not None]
    bounds = unary_union(valid).bounds if valid else None
    return {
        "feature_count": len(features),
        "bounds_epsg3005_or_native": list(bounds) if bounds else None,
    }


def _read_geojson(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"Missing GeoJSON layer: {path}")
    return _read_json(path)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"Expected a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _features(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    features = payload.get("features")
    if not isinstance(features, list):
        return ()
    return tuple(item for item in features if isinstance(item, Mapping))


def _geometry(feature: Mapping[str, object]) -> object | None:
    geometry = feature.get("geometry")
    if not isinstance(geometry, Mapping):
        return None
    try:
        return shape(geometry)
    except (TypeError, ValueError):
        return None


def _property_text(feature: Mapping[str, object], key: str) -> str | None:
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        return None
    value = properties.get(key)
    return str(value) if isinstance(value, str) and value.strip() else None


def _property_float(feature: Mapping[str, object], key: str) -> float | None:
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        return None
    value = properties.get(key)
    if value is None:
        return None
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=RUNTIME_ROOT)
    parser.add_argument("--lidar-selection", type=Path, default=LIDAR_SELECTION)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--generated-utc")
    args = parser.parse_args(argv)
    output = args.output or args.runtime_root / "domain_audit.json"
    try:
        result = audit_domain(
            args.runtime_root,
            lidar_selection=args.lidar_selection,
            generated_utc=args.generated_utc,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, f"Chapman domain audit failed: {exc}\n")
    _write_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
