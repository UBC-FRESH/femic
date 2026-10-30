"""Rank TSA 23 point-cloud tiles that were omitted from the full-run manifest.

The output is a coverage-priority screen, not an economic or operational harvest
priority.  See notes/reports/inv01-tsa23-gap-priority.md.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely import wkb
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.strtree import STRtree


def load_boundary(path: Path) -> object:
    if path.suffix.lower() == ".feather":
        frame = pd.read_feather(path)
        return wkb.loads(frame.geometry.iloc[0])
    frame = gpd.read_file(path)
    return frame.geometry.union_all() if hasattr(frame.geometry, "union_all") else frame.geometry.unary_union


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--vri", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True, help="c5 network vertices CSV with vertex_id,x,y")
    parser.add_argument("--destinations", type=Path, required=True, help="c5 route destinations CSV with name,vertex_id")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    tiles = selection["tiles"]
    points = [tile for tile in tiles if tile["product"] == "point_cloud"]
    dems = [tile for tile in tiles if tile["product"] == "dem"]
    manifest = pd.read_csv(args.manifest)
    manifest_ids = set(manifest.tile_id)
    boundary = load_boundary(args.boundary)

    tsa_tiles = []
    for tile in points:
        geom = box(*tile["bbox_epsg3005"])
        area = geom.intersection(boundary).area
        if area > 0:
            tsa_tiles.append((tile, geom, area))
    missing = [(tile, geom, area) for tile, geom, area in tsa_tiles if tile["tile_id"] not in manifest_ids]
    matched = [(tile, geom, area) for tile, geom, area in tsa_tiles if tile["tile_id"] in manifest_ids]
    if not missing:
        raise SystemExit("No omitted tiles found")

    dem_geometries = [box(*tile["bbox_epsg3005"]) for tile in dems]
    dem_tree = STRtree(dem_geometries)
    for tile, geom, _ in missing:
        idx = dem_tree.query(geom, predicate="intersects")
        tile["_dem_candidates"] = len(idx)
        tile["_dem_years"] = sorted({dems[int(i)].get("acquisition_year") for i in idx})

    vri = pd.read_feather(args.vri)[
        ["FEATURE_ID", "POLYGON_AREA", "BEC_ZONE_CODE", "PROJ_AGE_1", "PROJ_HEIGHT_1", "BASAL_AREA", "LIVE_STAND_VOLUME_125", "SPECIES_CD_1", "CROWN_CLOSURE", "thlb", "geometry"]
    ].copy()
    vri["geometry"] = [wkb.loads(value) for value in vri.geometry]
    vri = gpd.GeoDataFrame(vri, geometry="geometry", crs="EPSG:3005")
    vri = vri[pd.to_numeric(vri.POLYGON_AREA, errors="coerce") > 0].copy()
    for column in ("PROJ_HEIGHT_1", "BASAL_AREA", "LIVE_STAND_VOLUME_125"):
        vri[column] = pd.to_numeric(vri[column], errors="coerce")
    vri_tree = STRtree(vri.geometry.tolist())

    vertices = pd.read_csv(args.vertices)
    road_tree = cKDTree(vertices[["x", "y"]].to_numpy(float))
    destinations = pd.read_csv(args.destinations)
    destination_xy = {}
    for name, vertex_id in zip(destinations["name"], destinations["vertex_id"], strict=True):
        row = vertices.loc[vertices.vertex_id == vertex_id].iloc[0]
        destination_xy[name] = np.array([row.x, row.y], dtype=float)

    rows = []
    for tile, geom, area in missing:
        intersections = []
        for index in vri_tree.query(geom, predicate="intersects"):
            vri_row = vri.iloc[int(index)]
            overlap = geom.intersection(vri_row.geometry).area
            if overlap > 0:
                intersections.append((overlap, vri_row))

        def weighted(column: str, rows: list[tuple[float, pd.Series]]) -> float:
            numerator = sum(overlap * float(row[column]) for overlap, row in rows if pd.notna(row[column]))
            denominator = sum(overlap for overlap, row in rows if pd.notna(row[column]))
            return numerator / denominator if denominator else float("nan")

        centroid = geom.centroid
        nearest_road = float(road_tree.query([centroid.x, centroid.y])[0]) / 1000
        mill_km = {name: float(math.dist((centroid.x, centroid.y), xy)) / 1000 for name, xy in destination_xy.items()}
        nearest_mill = min(mill_km, key=mill_km.get)
        forest_ha = sum(overlap for overlap, _ in intersections) / 10000
        thlb_ha = sum(overlap for overlap, row in intersections if row.thlb == 1) / 10000
        score = forest_ha * (1 - 0.5 * min(nearest_road / 20, 1)) * (1 - 0.25 * min(mill_km[nearest_mill] / 150, 1))
        rows.append(
            {
                "tile_id": tile["tile_id"],
                "filename": tile["filename"],
                "year": tile.get("acquisition_year"),
                "tsa_area_ha": area / 10000,
                "forest_vri_ha": forest_ha,
                "thlb_vri_ha": thlb_ha,
                "vri_height_m": weighted("PROJ_HEIGHT_1", intersections),
                "vri_ba_m2_ha": weighted("BASAL_AREA", intersections),
                "vri_vol_m3_ha": weighted("LIVE_STAND_VOLUME_125", intersections),
                "road_distance_km": nearest_road,
                "mill_095_km": mill_km.get("destination.MILL_95_LBR", float("nan")),
                "mill_694_km": mill_km.get("destination.MILL_694_LGH", float("nan")),
                "mill_733_km": mill_km.get("destination.MILL_733_LGH", float("nan")),
                "nearest_mill": nearest_mill,
                "priority_score": score,
                "dem_candidates": tile["_dem_candidates"],
                "dem_years": ",".join(str(year) for year in tile["_dem_years"]),
                "geometry": geom,
            }
        )

    output = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3005").sort_values("priority_score", ascending=False).reset_index(drop=True)
    output["priority_rank"] = np.arange(1, len(output) + 1)
    count = len(output)
    output["priority_tier"] = np.where(
        output.priority_rank <= int(np.ceil(0.2 * count)),
        "A",
        np.where(output.priority_rank <= int(np.ceil(0.5 * count)), "B", "C"),
    )
    output.to_file(args.out_dir / "inv01-tsa23-gap-priority.gpkg", driver="GPKG", index=False)
    output.drop(columns="geometry").to_csv(args.out_dir / "inv01-tsa23-gap-priority.csv", index=False)

    missing_union = unary_union([geom for _, geom, _ in missing])
    matched_union = unary_union([geom for _, geom, _ in matched])
    all_union = unary_union([geom for _, geom, _ in tsa_tiles])
    summary = {
        "run_id": "inv01-tsa23-gap-priority",
        "tsa_area_km2": boundary.area / 1e6,
        "tsa_point_tiles": len(tsa_tiles),
        "matched_tiles": len(matched),
        "missing_tiles": len(missing),
        "missing_tile_footprint_km2": missing_union.area / 1e6,
        "missing_tsa_km2": missing_union.intersection(boundary).area / 1e6,
        "missing_share_of_tsa": missing_union.intersection(boundary).area / boundary.area,
        "missing_forest_vri_km2": float(output.forest_vri_ha.sum() / 100),
        "missing_thlb_km2": float(output.thlb_vri_ha.sum() / 100),
        "missing_priority_A": int((output.priority_tier == "A").sum()),
        "missing_priority_B": int((output.priority_tier == "B").sum()),
        "missing_priority_C": int((output.priority_tier == "C").sum()),
        "matched_tsa_km2": matched_union.intersection(boundary).area / 1e6,
        "all_point_tsa_km2": all_union.intersection(boundary).area / 1e6,
        "tsa_without_any_point_km2": boundary.difference(all_union).area / 1e6,
        "tsa_without_matched_point_km2": boundary.difference(matched_union).area / 1e6,
        "missing_with_any_dem": int((output.dem_candidates > 0).sum()),
    }
    (args.out_dir / "inv01-tsa23-gap-priority.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
