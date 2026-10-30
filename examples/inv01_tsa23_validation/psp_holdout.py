"""Build the TSA 23 PSP visit table and evaluate the current IDF cards.

The raw PSP CSVs are public FAIB extracts; fetch them with
``nemora.ingest.faib.download_faib_csvs(..., dataset="psp")`` first.  This
script reconstructs ground attributes from live trees DBH >= 9.1 cm and computes
exact-support first-return metrics for selected plots.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import laspy
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely.geometry import Point, box
from shapely.strtree import STRtree

TREE_COLUMNS = ["SITE_IDENTIFIER", "CLSTR_ID", "VISIT_NUMBER", "PLOT", "DBH", "HEIGHT", "LV_D", "PHF_TREE", "BA_TREE", "VOL_WSV"]


def read_ground(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    header = pd.read_csv(raw_dir / "faib_header.csv", low_memory=False)
    header["SITE_IDENTIFIER"] = pd.to_numeric(header.SITE_IDENTIFIER, errors="coerce").astype("Int64")
    header = header[header.TSA == 23].copy()
    visits = pd.read_csv(raw_dir / "faib_sample_byvisit.csv", low_memory=False)
    visits["SITE_IDENTIFIER"] = pd.to_numeric(visits.SITE_IDENTIFIER, errors="coerce").astype("Int64")
    visits = visits[visits.SITE_IDENTIFIER.isin(header.SITE_IDENTIFIER)]
    trees = pd.read_csv(raw_dir / "faib_tree_detail.csv", low_memory=False, usecols=TREE_COLUMNS)
    trees["SITE_IDENTIFIER"] = pd.to_numeric(trees.SITE_IDENTIFIER, errors="coerce").astype("Int64")
    trees = trees[trees.SITE_IDENTIFIER.isin(header.SITE_IDENTIFIER)]
    trees = trees[(trees.LV_D == "L") & (trees.DBH >= 9.1)].copy()
    trees["ba_exp"] = trees.BA_TREE * trees.PHF_TREE
    trees["vol_exp"] = trees.VOL_WSV * trees.PHF_TREE
    trees["height_ba"] = trees.HEIGHT * trees.ba_exp
    agg = trees.groupby(["SITE_IDENTIFIER", "CLSTR_ID", "VISIT_NUMBER"], as_index=False).agg(
        n_trees=("DBH", "size"), ba_m2_ha=("ba_exp", "sum"), vol_m3_ha=("vol_exp", "sum"), height_ba=("height_ba", "sum"), ba=("ba_exp", "sum")
    )
    agg["lorey_height_m"] = agg.height_ba / agg.ba
    agg = agg.drop(columns=["height_ba", "ba"])
    output = visits.merge(agg, on=["SITE_IDENTIFIER", "CLSTR_ID", "VISIT_NUMBER"], how="left")
    output = output.merge(header[["SITE_IDENTIFIER", "BEC_ZONE", "BEC_SBZ", "BC_ALBERS_X", "BC_ALBERS_Y", "Latitude", "Longitude"]], on="SITE_IDENTIFIER", how="left")
    return header, output


def point_candidates(header: pd.DataFrame, selection: Path, manifest: Path) -> pd.DataFrame:
    data = json.loads(selection.read_text(encoding="utf-8"))
    point_tiles = [tile for tile in data["tiles"] if tile["product"] == "point_cloud"]
    tree = STRtree([box(*tile["bbox_epsg3005"]) for tile in point_tiles])
    processed = set(pd.read_csv(manifest).tile_id)
    rows = []
    for row in header.itertuples(index=False):
        point = Point(row.BC_ALBERS_X, row.BC_ALBERS_Y)
        for index in tree.query(point, predicate="intersects"):
            tile = point_tiles[int(index)]
            rows.append(
                {
                    "SITE_IDENTIFIER": int(row.SITE_IDENTIFIER),
                    "tile_id": tile["tile_id"],
                    "filename": tile["filename"],
                    "tile_year": tile.get("acquisition_year"),
                    "processed": tile["tile_id"] in processed,
                }
            )
    return pd.DataFrame(rows)


def build_holdout(raw_dir: Path, selection: Path, manifest: Path, out_dir: Path) -> pd.DataFrame:
    header, visits = read_ground(raw_dir)
    candidates = point_candidates(header, selection, manifest)
    visits = visits[visits.MEAS_YR >= 2017].copy()
    visits = visits.merge(candidates, on="SITE_IDENTIFIER", how="inner")
    visits["year_gap"] = (visits.MEAS_YR - visits.tile_year).abs()
    visits = visits.sort_values(["SITE_IDENTIFIER", "year_gap", "processed"], ascending=[True, True, False]).drop_duplicates("SITE_IDENTIFIER")
    visits.to_csv(out_dir / "psp_recent_candidates.csv", index=False)
    return visits


def find_dem(plot: pd.Series, selection: Path, pointcloud_year: int) -> tuple[Path, str] | None:
    data = json.loads(selection.read_text(encoding="utf-8"))
    point = Point(float(plot.BC_ALBERS_X), float(plot.BC_ALBERS_Y))
    candidates = []
    for tile in data["tiles"]:
        if tile["product"] != "dem":
            continue
        if box(*tile["bbox_epsg3005"]).contains(point):
            year_gap = abs(int(tile.get("acquisition_year") or 0) - pointcloud_year)
            candidates.append((year_gap, 0 if tile["layer_id"] == 6 else 1, tile))
    if not candidates:
        return None
    tile = min(candidates, key=lambda item: (item[0], item[1]))[2]
    return Path(tile["filename"]), tile["filename"]


def compute_features(raw_dir: Path, selection: Path, manifest: Path, pointcloud_dir: Path, dem_dir: Path, sites: list[int], out_dir: Path) -> pd.DataFrame:
    header, visits = read_ground(raw_dir)
    plot_header = pd.read_csv(raw_dir / "faib_plot_header.csv", low_memory=False)
    plot_header["SITE_IDENTIFIER"] = plot_header.SITE_IDENTIFIER.astype(int)
    plot_header["VISIT_NUMBER"] = plot_header.VISIT_NUMBER.astype(int)
    selected = visits[visits.SITE_IDENTIFIER.isin(sites)].sort_values(["SITE_IDENTIFIER", "MEAS_YR"]).groupby("SITE_IDENTIFIER").tail(1).copy()
    selected = selected.merge(plot_header[["SITE_IDENTIFIER", "VISIT_NUMBER", "PLOT_AREA_MAIN"]], on=["SITE_IDENTIFIER", "VISIT_NUMBER"], how="left")
    transformer = Transformer.from_crs("EPSG:3005", "EPSG:3157", always_xy=True)
    rows = []
    for site, group in selected.groupby("SITE_IDENTIFIER"):
        plot = group.iloc[0]
        year = int(plot.MEAS_YR)
        point_record = point_candidates(header, selection, manifest)
        point_record = point_record[point_record.SITE_IDENTIFIER == site].sort_values("tile_year", key=lambda s: (s - year).abs()).iloc[0]
        laz_path = pointcloud_dir / point_record.filename
        dem_record = find_dem(plot, selection, int(point_record.tile_year))
        if dem_record is None:
            raise FileNotFoundError(f"No DEM candidate for {site}")
        dem_name, _ = dem_record
        dem_path = dem_dir / dem_name.name
        if not laz_path.exists() or not dem_path.exists():
            raise FileNotFoundError(f"Missing point cloud or DEM for {site}: {laz_path}, {dem_path}")
        ux, uy = transformer.transform(float(plot.BC_ALBERS_X), float(plot.BC_ALBERS_Y))
        radius = math.sqrt(float(plot.PLOT_AREA_MAIN) * 10000 / math.pi)
        xs, ys, zs = [], [], []
        with laspy.open(laz_path) as reader:
            for chunk in reader.chunk_iterator(5_000_000):
                x, y, z, return_number = np.asarray(chunk.x), np.asarray(chunk.y), np.asarray(chunk.z), np.asarray(chunk.return_number)
                first = return_number == 1
                x, y, z = x[first], y[first], z[first]
                keep = (x - ux) ** 2 + (y - uy) ** 2 <= radius**2
                if keep.any():
                    xs.append(x[keep]); ys.append(y[keep]); zs.append(z[keep])
        if not xs:
            continue
        x, y, z = np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)
        with rasterio.open(dem_path) as dataset:
            ground = np.array([value[0] for value in dataset.sample(zip(x, y))], dtype=float)
        heights = z - ground
        heights = heights[np.isfinite(heights)]
        all_first = int(heights.size)
        above = heights[heights > 2.0]
        if above.size < 10:
            continue
        rows.append(
            {
                "SITE_IDENTIFIER": int(site),
                "VISIT_NUMBER": int(plot.VISIT_NUMBER),
                "MEAS_YR": year,
                "BEC_ZONE": plot.BEC_ZONE,
                "lorey_height_m_obs": float(plot.lorey_height_m),
                "ba_m2_ha_obs": float(plot.ba_m2_ha),
                "vol_m3_ha_obs": float(plot.vol_m3_ha),
                "Lhmean": float(above.mean()),
                "Lhcv": float(above.std() / above.mean()),
                "Lhp95": float(np.percentile(above, 95)),
                "CC2m": float(100 * above.size / all_first),
                "all_first": all_first,
                "above2m": int(above.size),
                "radius_m": radius,
                "pointcloud": laz_path.name,
                "dem": dem_path.name,
            }
        )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["height_pred"] = 1.9441063309517714 + 0.8351084469592212 * frame.Lhp95
        frame["ba_pred"] = np.exp(-4.724750214946937 + 0.8686310009684395 * np.log(frame.Lhmean) + 1.3794686095244624 * np.log(frame.CC2m)) * 1.008780042159369
        frame["vol_pred"] = np.exp(-4.009416713953133 + 1.7395991112544076 * np.log(frame.Lhmean) + 1.1516782963514058 * np.log(frame.CC2m)) * 1.004526898452813
        frame.to_csv(out_dir / "psp_holdout.csv", index=False)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pointcloud-dir", type=Path, required=True)
    parser.add_argument("--dem-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sites", type=int, nargs="*", default=[4025090, 4025091, 4025094, 4025095])
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    build_holdout(args.raw_dir, args.selection, args.manifest, args.out_dir)
    frame = compute_features(args.raw_dir, args.selection, args.manifest, args.pointcloud_dir, args.dem_dir, args.sites, args.out_dir)
    print(frame.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
