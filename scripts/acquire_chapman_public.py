"""Acquire public Chapman Creek hydrology-domain layers.

The bulk GeoJSON is written to an ignored runtime directory. This script
commits only the acquisition recipe and provenance; it does not build a flood
model or claim complete domain coverage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

WFS_ROOT = "https://openmaps.gov.bc.ca/geo/pub"
WATERSHED_PREFIX = "900-127577"
BBOX = "1163000,493000,1170000,500000,EPSG:3005"
STATIONS = ("08GA046", "08GA060", "08GA078")
LICENCE_ID = "OGL-BC"
SCHEMA_VERSION = "femic.chapman_acquisition.v1"
GAPS = (
    "LidarBC DEM/DSM tiles are not downloaded by this script.",
    "No reviewed Chapman water-system receptor geometry is selected.",
    "The historical WSC record ends in 2003; no current public daily series is confirmed.",
    "Culvert and road-crossing inventory is absent.",
    "Hydrologist review and a reviewed WS4 crosswalk are still required.",
)


def wfs_url(
    layer: str,
    *,
    cql_filter: str | None = None,
    bbox: str | None = None,
    count: int = 5000,
) -> str:
    """Build a WFS 2.0 GeoJSON query URL."""
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": f"pub:{layer}",
        "outputFormat": "application/json",
        "count": str(count),
    }
    if cql_filter is not None:
        params["CQL_FILTER"] = cql_filter
    if bbox is not None:
        params["bbox"] = bbox
    return f"{WFS_ROOT}/{layer}/ows?{urllib.parse.urlencode(params)}"


def station_url(station_number: str) -> str:
    """Build a Water Survey of Canada station metadata URL."""
    return (
        "https://api.weather.gc.ca/collections/hydrometric-stations/items?"
        + urllib.parse.urlencode({"STATION_NUMBER": station_number, "f": "json"})
    )


def acquire(
    output_root: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    timeout: int = 120,
) -> dict[str, object]:
    """Acquire the public layers and write provenance.

    Parameters
    ----------
    output_root : Path
        Ignored runtime directory for bulk GeoJSON.
    dry_run : bool, optional
        Print the planned queries without writing data.
    force : bool, optional
        Overwrite an existing output directory.
    timeout : int, optional
        Per-request timeout in seconds.

    Returns
    -------
    dict[str, object]
        Provenance manifest, or the planned queries in dry-run mode.
    """
    root = output_root.expanduser().resolve()
    queries = _queries()
    if dry_run:
        return {
            "dry_run": True,
            "output_root": str(root),
            "queries": queries,
            "gaps": list(GAPS),
        }
    if root.exists() and any(root.iterdir()) and not force:
        raise RuntimeError(f"Output directory is not empty: {root}; pass --force")
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for query in queries:
        payload = _fetch_json(str(query["url"]), timeout=timeout)
        path = root / str(query["path"])
        _write_json(path, payload)
        records.append(
            {
                "id": query["id"],
                "role": query["role"],
                "source_url": query["url"],
                "relative_path": str(query["path"]),
                "licence_id": LICENCE_ID,
                "crs": query["crs"],
                "bbox": _bbox_from_geojson(payload),
                "feature_count": _feature_count(payload),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    station_payload = _station_collection(timeout=timeout)
    station_path = root / "gauges.geojson"
    _write_json(station_path, station_payload)
    records.append(
        {
            "id": "wsc_gauges",
            "role": "gauge",
            "source_url": "https://api.weather.gc.ca/collections/hydrometric-stations",
            "relative_path": "gauges.geojson",
            "licence_id": "OGL-Canada",
            "crs": "EPSG:4326",
            "bbox": _bbox_from_geojson(station_payload),
            "feature_count": _feature_count(station_payload),
            "size_bytes": station_path.stat().st_size,
            "sha256": _sha256(station_path),
        }
    )
    watershed_area_ha = sum(
        _area_ha(feature)
        for feature in _features(_read_json(root / "watersheds.geojson"))
    )
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).isoformat(),
        "output_root": str(root),
        "bbox_epsg_3005": BBOX,
        "watershed_code_prefix": WATERSHED_PREFIX,
        "watershed_area_ha": watershed_area_ha,
        "licence_id": LICENCE_ID,
        "sources": records,
        "gaps": list(GAPS),
        "notes": (
            "Bulk public layers are runtime data and are not tracked. "
            "The watershed layer is the full code-prefix union, not one local polygon."
        ),
    }
    _write_json(root / "provenance.json", manifest)
    return manifest


def _queries() -> tuple[dict[str, object], ...]:
    return (
        {
            "id": "fwa_watersheds",
            "role": "watershed",
            "path": "watersheds.geojson",
            "crs": "EPSG:3005",
            "url": wfs_url(
                "WHSE_BASEMAPPING.FWA_WATERSHEDS_POLY",
                cql_filter=f"FWA_WATERSHED_CODE LIKE '{WATERSHED_PREFIX}%'",
                count=5000,
            ),
        },
        {
            "id": "fwa_streams",
            "role": "stream",
            "path": "streams.geojson",
            "crs": "EPSG:3005",
            "url": wfs_url(
                "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP",
                bbox=BBOX,
                count=5000,
            ),
        },
        {
            "id": "dra_roads",
            "role": "road",
            "path": "roads.geojson",
            "crs": "EPSG:3005",
            "url": wfs_url(
                "WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP",
                bbox=BBOX,
                count=5000,
            ),
        },
    )


def _fetch_json(url: str, *, timeout: int) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "FEMIC-Chapman-acquisition/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload: object = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"Expected a JSON object from {url}")
    return {str(key): value for key, value in payload.items()}


def _station_collection(*, timeout: int) -> dict[str, object]:
    features: list[dict[str, object]] = []
    for station in STATIONS:
        payload = _fetch_json(station_url(station), timeout=timeout)
        for feature in _features(payload):
            geometry = feature.get("geometry")
            if not isinstance(geometry, Mapping):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, Mapping):
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "gauge_id": properties.get("STATION_NUMBER"),
                        "station_name": properties.get("STATION_NAME"),
                        "drainage_area_km2": properties.get("DRAINAGE_AREA_GROSS"),
                        "status": properties.get("STATUS_EN"),
                        "licence_id": "OGL-Canada",
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}


def _features(payload: Mapping[str, object]) -> Sequence[Mapping[str, object]]:
    features = payload.get("features")
    if not isinstance(features, list):
        return ()
    return tuple(item for item in features if isinstance(item, Mapping))


def _feature_count(payload: Mapping[str, object]) -> int:
    return len(_features(payload))


def _area_ha(feature: Mapping[str, object]) -> float:
    properties = feature.get("properties")
    if not isinstance(properties, Mapping):
        return 0.0
    value = properties.get("AREA_HA", 0.0)
    try:
        parsed = float(str(value))
    except (TypeError, ValueError):
        return 0.0
    return parsed if math.isfinite(parsed) and parsed > 0 else 0.0


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


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"Expected a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _bbox_from_geojson(payload: Mapping[str, object]) -> list[float] | None:
    coords: list[tuple[float, float]] = []
    for feature in _features(payload):
        geometry = feature.get("geometry")
        if isinstance(geometry, Mapping):
            _collect_coords(geometry.get("coordinates"), coords)
    if not coords:
        return None
    xs, ys = zip(*coords, strict=True)
    return [min(xs), min(ys), max(xs), max(ys)]


def _collect_coords(value: object, target: list[tuple[float, float]]) -> None:
    if not isinstance(value, (list, tuple)) or not value:
        return
    if len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
        x, y = float(value[0]), float(value[1])
        if math.isfinite(x) and math.isfinite(y):
            target.append((x, y))
        return
    for item in value:
        _collect_coords(item, target)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("runtime/p118_chapman"),
        help="Ignored runtime directory for bulk GeoJSON.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)
    try:
        result = acquire(
            args.output_root,
            dry_run=args.dry_run,
            force=args.force,
            timeout=args.timeout,
        )
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        parser.exit(1, f"Chapman acquisition failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
