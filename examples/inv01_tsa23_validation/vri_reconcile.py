"""Join the full TSA 23 grid to VRI polygons and report agreement.

This is a screening check.  VRI is an interpreted polygon inventory, not an
independent field sample; see notes/reports/inv01-tsa23-vri-reconciliation.md.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import wkb

VRI_COLUMNS = [
    "FEATURE_ID",
    "POLYGON_ID",
    "MAP_ID",
    "POLYGON_AREA",
    "BEC_ZONE_CODE",
    "BEC_SUBZONE",
    "PROJ_AGE_1",
    "PROJ_HEIGHT_1",
    "BASAL_AREA",
    "LIVE_STAND_VOLUME_125",
    "SPECIES_CD_1",
    "CROWN_CLOSURE",
    "thlb",
    "geometry",
]


def load_boundary(path: Path) -> object:
    if path.suffix.lower() == ".feather":
        frame = pd.read_feather(path)
        return wkb.loads(frame.geometry.iloc[0])
    frame = gpd.read_file(path)
    return frame.geometry.union_all() if hasattr(frame.geometry, "union_all") else frame.geometry.unary_union


def metrics(frame: pd.DataFrame, pred: str, obs: str) -> dict[str, object] | None:
    x = frame[[pred, obs]].dropna()
    x = x[(x[obs] > 0) & (x[pred] > 0)]
    if len(x) < 3:
        return None
    p = x[pred].to_numpy(float)
    o = x[obs].to_numpy(float)
    err = p - o
    slope, intercept = np.polyfit(o, p, 1)
    return {
        "n": len(x),
        "pred_mean": float(p.mean()),
        "obs_mean": float(o.mean()),
        "pred_median": float(np.median(p)),
        "obs_median": float(np.median(o)),
        "bias": float(err.mean()),
        "mae": float(np.abs(err).mean()),
        "rmse": float(np.sqrt(np.mean(err * err))),
        "relative_bias_pct": float(100 * err.mean() / o.mean()),
        "r": float(np.corrcoef(o, p)[0, 1]),
        "slope": float(slope),
        "intercept": float(intercept),
        "p10_error": float(np.quantile(err, 0.1)),
        "p90_error": float(np.quantile(err, 0.9)),
    }


def by_group(frame: pd.DataFrame, pred: str, obs: str, group: str, min_n: int = 100) -> list[dict[str, object]]:
    out = []
    for key, subset in frame.groupby(group, dropna=False):
        result = metrics(subset, pred, obs)
        if result and result["n"] >= min_n:
            result[group] = str(key)
            out.append(result)
    return sorted(out, key=lambda item: -int(item["n"]))


def add_classes(frame: pd.DataFrame) -> None:
    frame["PROJ_HEIGHT_1_class"] = pd.cut(
        frame["PROJ_HEIGHT_1"], [0, 10, 15, 20, 25, 100], labels=["<10", "10-15", "15-20", "20-25", "25+"], right=False
    )
    frame["BASAL_AREA_class"] = pd.cut(
        frame["BASAL_AREA"], [0, 10, 20, 30, 100], labels=["<10", "10-20", "20-30", "30+"], right=False
    )
    frame["LIVE_STAND_VOLUME_125_class"] = pd.cut(
        frame["LIVE_STAND_VOLUME_125"], [0, 50, 100, 150, 200, 2000], labels=["<50", "50-100", "100-150", "150-200", "200+"], right=False
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--vri", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--grid-crs", default="EPSG:3157")
    parser.add_argument("--vri-crs", default="EPSG:3005")
    parser.add_argument("--write-cells", action="store_true", help="Write the joined cell table (large).")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    vri = pd.read_feather(args.vri)[VRI_COLUMNS].copy()
    vri["geometry"] = [wkb.loads(value) for value in vri.geometry]
    vri = gpd.GeoDataFrame(vri, geometry="geometry", crs=args.vri_crs)
    vri = vri[vri.geometry.notna() & ~vri.geometry.is_empty]
    vri = vri[pd.to_numeric(vri.POLYGON_AREA, errors="coerce") > 0].copy()

    features = pd.read_parquet(args.features)
    inventory = pd.read_parquet(args.inventory)
    inventory = inventory.pivot_table(index="fragment_id", columns="attribute", values="value", aggfunc="first").reset_index()
    features = features.merge(inventory, on="fragment_id", how="left", validate="one_to_one")
    transformer = Transformer.from_crs(args.grid_crs, args.vri_crs, always_xy=True)
    x, y = transformer.transform(features.x_center.to_numpy(), features.y_center.to_numpy())
    points = gpd.GeoDataFrame(
        features[["fragment_id", "source_tile", "Lhmean", "Lhp95", "CC2m", "lorey_height_m", "ba_m2_ha", "vol_m3_ha"]].copy(),
        geometry=gpd.points_from_xy(x, y),
        crs=args.vri_crs,
    )
    joined = gpd.sjoin(points, vri, how="inner", predicate="within")
    joined = joined.sort_values(["FEATURE_ID", "POLYGON_AREA"], ascending=[True, True]).drop_duplicates("fragment_id", keep="first")
    joined = joined.drop(columns=["geometry", "index_right"], errors="ignore")
    if args.write_cells:
        joined.to_parquet(args.out_dir / "cells_vri.parquet", index=False)
    add_classes(joined)

    specs = {
        "height": ("lorey_height_m", "PROJ_HEIGHT_1"),
        "ba": ("ba_m2_ha", "BASAL_AREA"),
        "volume": ("vol_m3_ha", "LIVE_STAND_VOLUME_125"),
    }
    output: dict[str, object] = {
        "run_id": "inv01-tsa23-vri-reconciliation",
        "total_feature_cells": len(features),
        "vri_join_cells": len(joined),
        "vri_join_share": float(len(joined) / len(features)),
        "boundary": str(args.boundary),
        "attributes": {},
        "coverage": {
            "height_model_cells": int(features.lorey_height_m.notna().sum()),
            "ba_volume_model_cells": int(features.ba_m2_ha.notna().sum()),
        },
    }
    for label, (pred, obs) in specs.items():
        output["attributes"][label] = {
            "cell": metrics(joined, pred, obs),
            "polygon": metrics(
                joined[[pred, obs, "FEATURE_ID"]].dropna().groupby("FEATURE_ID", as_index=False).agg({pred: "mean", obs: "first"}),
                pred,
                obs,
            ),
            "by_bec": by_group(joined, pred, obs, "BEC_ZONE_CODE"),
            "by_vri_class": by_group(joined, pred, obs, f"{obs}_class"),
        }
    (args.out_dir / "vri_metrics.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("total_feature_cells", "vri_join_cells", "vri_join_share")}, indent=2))


if __name__ == "__main__":
    main()
