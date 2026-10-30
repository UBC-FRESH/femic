"""Pair LidarBC point-cloud and DEM tiles for one TSA boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkb
from shapely.geometry import box
from shapely.strtree import STRtree


def load_boundary(path: Path) -> gpd.GeoDataFrame:
    if path.suffix.lower() == ".feather":
        frame = pd.read_feather(path)
        geometry = [wkb.loads(value) for value in frame.geometry]
        return gpd.GeoDataFrame(frame.drop(columns=["geometry"]), geometry=geometry, crs="EPSG:3005")
    return gpd.read_file(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True, help="LidarBC selection JSON")
    parser.add_argument("--boundary", type=Path, required=True, help="TSA boundary (GeoPackage/GeoJSON/feather)")
    parser.add_argument("--output", type=Path, required=True, help="Output tile-manifest CSV")
    parser.add_argument("--point-layer", type=int, default=4)
    parser.add_argument("--dem-layer", type=int, default=5)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    tiles = selection["tiles"]
    point = [t for t in tiles if t["product"] == "point_cloud" and t["layer_id"] == args.point_layer]
    dem = [t for t in tiles if t["product"] == "dem" and t["layer_id"] == args.dem_layer]
    if not point or not dem:
        raise SystemExit(f"No point-cloud/DEM tiles found in {args.selection}")

    boundary = load_boundary(args.boundary)
    dissolved = boundary.geometry.union_all() if hasattr(boundary.geometry, "union_all") else boundary.geometry.unary_union

    def tile_geometry(tile: dict) -> object:
        b = tile["bbox_epsg3005"]
        return box(b[0], b[1], b[2], b[3])

    dem_geoms = [tile_geometry(tile) for tile in dem]
    tree = STRtree(dem_geoms)
    rows: list[dict[str, object]] = []
    missing = 0
    for point_tile in point:
        geom = tile_geometry(point_tile)
        if not geom.intersects(dissolved):
            continue
        candidates = []
        for index in tree.query(geom):
            dem_tile = dem[int(index)]
            dem_geom = dem_geoms[int(index)]
            intersection = geom.intersection(dem_geom).area
            if intersection <= 0:
                continue
            year_gap = abs((dem_tile.get("acquisition_year") or 0) - (point_tile.get("acquisition_year") or 0))
            candidates.append((year_gap, -intersection, dem_tile))
        if not candidates:
            missing += 1
            continue
        candidates.sort(key=lambda item: (item[0], item[1]))
        dem_tile = candidates[0][2]
        b = point_tile["bbox_epsg3005"]
        rows.append(
            {
                "tile_id": point_tile["tile_id"],
                "filename": point_tile["filename"],
                "url": point_tile["download_url"],
                "year": point_tile.get("acquisition_year"),
                "projection": point_tile.get("projection"),
                "xmin": b[0],
                "ymin": b[1],
                "xmax": b[2],
                "ymax": b[3],
                "dem_tile_id": dem_tile["tile_id"],
                "dem_filename": dem_tile["filename"],
                "dem_url": dem_tile["download_url"],
                "dem_year": dem_tile.get("acquisition_year"),
                "dem_projection": dem_tile.get("projection"),
            }
        )
    frame = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(f"wrote {len(frame)} tile pairs; {missing} point tiles had no DEM match")


if __name__ == "__main__":
    main()
