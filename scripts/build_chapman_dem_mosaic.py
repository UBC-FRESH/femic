"""Build the native-resolution Chapman Creek DEM mosaic and manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio  # type: ignore[import-untyped]
from pyproj import CRS as PyprojCRS
from pyproj import Transformer
from rasterio.features import geometry_mask  # type: ignore[import-untyped]
from rasterio.merge import merge  # type: ignore[import-untyped]
from rasterio.vrt import WarpedVRT  # type: ignore[import-untyped]
from shapely import transform as shapely_transform_geometry  # type: ignore[import-untyped]
from shapely.geometry import shape  # type: ignore[import-untyped]
from shapely.ops import unary_union  # type: ignore[import-untyped]

SCHEMA_VERSION = "femic.chapman_dem_mosaic.v1"
DEFAULT_SELECTION = Path("/tmp/opencode/chapman_lidar_selection.json")
DEFAULT_OUTPUT = Path("runtime/p118_chapman/dem_mosaic_3157_cgvd2013.tif")
DEFAULT_MANIFEST = Path("runtime/p118_chapman/dem_mosaic_manifest.json")
DEFAULT_AUDIT = Path("runtime/p118_chapman/domain_audit.json")
NODATA = -32767.0


def build_mosaic(
    selection_path: Path,
    output_path: Path,
    *,
    manifest_path: Path | None = None,
    domain_audit_path: Path | None = None,
    watershed_path: Path | None = None,
    watershed_crs: str = "EPSG:3005",
    limit: int = 0,
    generated_utc: str | None = None,
) -> dict[str, object]:
    """Build a native-CRS DEM mosaic and write its manifest."""
    selection = _read_json(selection_path)
    tiles = selection.get("tiles")
    if not isinstance(tiles, list):
        raise TypeError("LidarBC selection has no tiles list.")
    dem_tiles = [
        tile
        for tile in tiles
        if isinstance(tile, Mapping) and tile.get("product") == "dem"
    ]
    if limit > 0:
        dem_tiles = dem_tiles[:limit]
    if not dem_tiles:
        raise RuntimeError("No DEM tiles selected.")
    sources = []
    compound_tiles = 0
    two_d_tiles = 0
    with ExitStack() as stack:
        for tile in dem_tiles:
            url = tile.get("download_url")
            if not isinstance(url, str) or not url:
                continue
            path = f"/vsicurl/{url}" if url.startswith("http") else url
            source = stack.enter_context(rasterio.open(path))
            if source.crs is not None and source.crs.to_epsg() == 6653:
                compound_tiles += 1
            else:
                two_d_tiles += 1
            sources.append(
                stack.enter_context(
                    WarpedVRT(
                        source,
                        src_crs=PyprojCRS.from_epsg(3157),
                        crs=PyprojCRS.from_epsg(3157),
                    )
                )
            )
        if not sources:
            raise RuntimeError("No readable DEM tiles found.")
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            array, transform = merge(
                sources,
                nodata=NODATA,
                method="first",
            )
        source = sources[0]
        vertical_status = "resolved" if two_d_tiles == 0 else "mixed_unresolved"
        profile = {
            "driver": "GTiff",
            "dtype": "float32",
            "count": 1,
            "crs": source.crs,
            "transform": transform,
            "nodata": NODATA,
            "width": array.shape[2],
            "height": array.shape[1],
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
            "compress": "deflate",
            "predictor": 3,
            "BIGTIFF": "IF_SAFER",
        }
        output = output_path.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        data = np.asarray(array, dtype=np.float32)
        if data.ndim == 3:
            data = data[0]
        data[data == -9999.0] = NODATA
        watershed_geometry = _watershed_geometry(
            watershed_path, source_crs=watershed_crs
        )
        clipped = watershed_geometry is not None
        if watershed_geometry is not None:
            inside = geometry_mask(
                [watershed_geometry],
                out_shape=data.shape,
                transform=transform,
                invert=True,
            )
            data[~inside] = NODATA
        with rasterio.open(output, "w", **profile) as destination:
            destination.write(data, 1)
        valid = data != NODATA
        valid_pixels = int(np.count_nonzero(valid))
        pixel_area_ha = abs(transform.a * transform.e) / 10000.0
        valid_area_ha = valid_pixels * pixel_area_ha
        watershed_area_ha = _watershed_area(domain_audit_path)
        bounds = rasterio.transform.array_bounds(
            data.shape[1], data.shape[0], transform
        )
        manifest: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "generated_utc": generated_utc or datetime.now(UTC).isoformat(),
            "mosaic_path": str(output),
            "mosaic_size_bytes": output.stat().st_size,
            "mosaic_sha256": _sha256(output),
            "source_selection": str(selection_path),
            "source_selection_sha256": _sha256(selection_path),
            "source_tile_count": len(sources),
            "clipped_to_watershed": clipped,
            "crs_epsg": 3157,
            "horizontal_epsg": 3157,
            "vertical_datum": (
                "CGVD2013(CGG2013) height"
                if two_d_tiles == 0
                else "mixed: CGVD2013 for compound tiles; unknown for 2D tiles"
            ),
            "vertical_epsg": "6647" if two_d_tiles == 0 else None,
            "vertical_status": vertical_status,
            "compound_tile_count": compound_tiles,
            "two_d_tile_count": two_d_tiles,
            "resolution_m": [abs(float(transform.a)), abs(float(transform.e))],
            "bounds": list(bounds),
            "valid_pixels": valid_pixels,
            "nodata_pixels": int(data.size - valid_pixels),
            "valid_area_ha": valid_area_ha,
            "watershed_area_ha": watershed_area_ha,
            "edge_gap_ha": (
                max(0.0, watershed_area_ha - valid_area_ha)
                if watershed_area_ha is not None
                else None
            ),
            "valid_min": float(np.min(data[valid])) if valid_pixels else None,
            "valid_max": float(np.max(data[valid])) if valid_pixels else None,
            "nodata": NODATA,
            "nodata_handling": "normalized source -9999 and -32767 to -32767; no gap fill",
            "receptor_status": "unreviewed; no geometry inferred",
            "crosswalk_status": "missing",
            "caveats": (
                "Native 1 m CGVD2013 DEM mosaic; no gap fill.",
                "2D tiles without vertical metadata are excluded and counted as a coverage gap.",
                "Edge gap is unfilled and must be reviewed outside the mosaic.",
                "Receptor and WS4 crosswalk remain blockers.",
            ),
        }
    manifest_target = manifest_path or DEFAULT_MANIFEST
    _write_json(manifest_target, manifest)
    return manifest


def _watershed_geometry(
    path: Path | None,
    *,
    source_crs: str = "EPSG:3005",
) -> object | None:
    target = path or Path("runtime/p118_chapman/watersheds.geojson")
    if not target.is_file():
        return None
    payload = _read_json(target)
    features = payload.get("features")
    if not isinstance(features, list):
        return None
    geometries = []
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        geometry = feature.get("geometry")
        if isinstance(geometry, Mapping):
            geometries.append(shape(geometry))
    if not geometries:
        return None
    union = unary_union(geometries)
    transformer = Transformer.from_crs(source_crs, "EPSG:3157", always_xy=True)

    def reproject(coords: np.ndarray) -> np.ndarray:
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely_transform_geometry(union, reproject)


def _watershed_area(path: Path | None) -> float | None:
    target = path or DEFAULT_AUDIT
    if not target.is_file():
        return None
    payload = _read_json(target)
    watershed = payload.get("watershed")
    if not isinstance(watershed, Mapping):
        return None
    area = watershed.get("area_ha")
    return float(area) if isinstance(area, (int, float)) else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"Expected a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--domain-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument(
        "--watershed",
        type=Path,
        default=Path("runtime/p118_chapman/watersheds.geojson"),
    )
    parser.add_argument("--watershed-crs", default="EPSG:3005")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--generated-utc")
    args = parser.parse_args(argv)
    try:
        result = build_mosaic(
            args.selection,
            args.output,
            manifest_path=args.manifest,
            domain_audit_path=args.domain_audit,
            watershed_path=args.watershed,
            watershed_crs=args.watershed_crs,
            limit=args.limit,
            generated_utc=args.generated_utc,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, f"Chapman DEM mosaic failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
