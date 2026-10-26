"""Audit selected LidarBC DEM tiles and record compound CRS metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import rasterio  # type: ignore[import-untyped]
from pyproj import CRS as PyprojCRS

SCHEMA_VERSION = "femic.chapman_dem_metadata.v1"
DEFAULT_SELECTION = Path("/tmp/opencode/chapman_lidar_selection.json")
DEFAULT_OUTPUT = Path("runtime/p118_chapman/dem_metadata_audit.json")


def audit_dem_metadata(
    selection_path: Path,
    *,
    limit: int = 0,
    generated_utc: str | None = None,
) -> dict[str, object]:
    """Probe DEM tiles and summarize their CRS and vertical datum."""
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
    records: list[dict[str, object]] = []
    failures: list[str] = []
    for tile in dem_tiles:
        url = tile.get("download_url")
        filename = tile.get("filename")
        if not isinstance(url, str) or not url:
            failures.append(f"{filename}: no download_url")
            continue
        try:
            record = _probe_tile(url)
        except (OSError, RuntimeError, ValueError) as exc:
            failures.append(f"{filename}: {exc}")
            continue
        records.append(
            {
                "tile_id": tile.get("tile_id"),
                "filename": filename,
                "acquisition_year": tile.get("acquisition_year"),
                **record,
            }
        )
    if not records:
        raise RuntimeError("No DEM tile metadata could be read.")
    unique_crs = sorted({str(record["crs_epsg"]) for record in records})
    unique_vertical = sorted(
        {
            str(record["vertical_datum"])
            for record in records
            if record["vertical_datum"]
        }
    )
    unique_horizontal = sorted(
        {
            str(record["horizontal_epsg"])
            for record in records
            if record["horizontal_epsg"]
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated_utc or datetime.now(UTC).isoformat(),
        "selection_manifest": str(selection_path),
        "selection_sha256": _sha256(selection_path),
        "tile_count": len(dem_tiles),
        "probed_count": len(records),
        "failure_count": len(failures),
        "failures": failures,
        "crs_epsg": unique_crs,
        "horizontal_epsg": unique_horizontal,
        "vertical_datum": unique_vertical,
        "vertical_epsg": sorted(
            {
                str(record["vertical_epsg"])
                for record in records
                if record["vertical_epsg"]
            }
        ),
        "resolution_m": sorted({str(record["resolution_m"]) for record in records}),
        "nodata": sorted({str(record["nodata"]) for record in records}),
        "receptor": {
            "candidate": "Chapman Creek water-system intake / WTP, Reservoir Road, Sechelt",
            "status": "unreviewed",
            "geometry": None,
            "evidence": [
                "UBC Chapman Creek study area: https://blogs.ubc.ca/mstaats8/methods-2/study-area",
                "SCRD Chapman water system backgrounder: https://letstalk.scrd.ca/29788/widgets/126451/documents/83185",
                "EOCP Chapman WTP profile: https://eocp.ca/wp-content/uploads/2012/10/plants-Sunshine-Coast-Regional-District.pdf",
                "Reservoir Road locality: https://www.openstreetmap.org/way/164627850",
            ],
            "note": "No reviewed point or polygon is selected; do not infer one from the road.",
        },
        "records": records,
    }


def _probe_tile(url: str) -> dict[str, object]:
    with (
        rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"),
        rasterio.open(f"/vsicurl/{url}") as dataset,
    ):
        crs = dataset.crs
        if crs is None:
            raise RuntimeError("tile has no CRS")
        return {
            **_crs_metadata(PyprojCRS.from_wkt(crs.to_wkt())),
            "resolution_m": [float(value) for value in dataset.res],
            "nodata": dataset.nodata,
        }


def _crs_metadata(crs: PyprojCRS) -> dict[str, object]:
    if crs.is_compound and len(crs.sub_crs_list) >= 2:
        horizontal = crs.sub_crs_list[0]
        vertical = crs.sub_crs_list[1]
        return {
            "crs_epsg": crs.to_epsg(),
            "horizontal_epsg": (
                str(horizontal.to_epsg()) if horizontal.to_epsg() is not None else None
            ),
            "vertical_datum": vertical.name,
            "vertical_epsg": (
                str(vertical.to_epsg()) if vertical.to_epsg() is not None else None
            ),
        }
    return {
        "crs_epsg": crs.to_epsg(),
        "horizontal_epsg": str(crs.to_epsg()) if crs.to_epsg() is not None else None,
        "vertical_datum": None,
        "vertical_epsg": None,
    }


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"Expected a JSON object: {path}")
    return {str(key): value for key, value in payload.items()}


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
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--generated-utc")
    args = parser.parse_args(argv)
    try:
        result = audit_dem_metadata(
            args.selection,
            limit=args.limit,
            generated_utc=args.generated_utc,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, f"DEM metadata audit failed: {exc}\n")
    _write_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
