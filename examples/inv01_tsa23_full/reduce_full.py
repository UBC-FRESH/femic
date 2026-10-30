"""Reduce batch parts, clip to a boundary, apply TSA 23 IDF cards, and map."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely import contains_xy, wkb
from shapely.ops import transform as shapely_transform
from shapely.ops import unary_union


def load_boundary(path: Path, crs: str = "EPSG:3157"):
    if path.suffix.lower() == ".feather":
        frame = pd.read_feather(path)
        geometry = [wkb.loads(value) for value in frame.geometry]
        boundary = geometry[0] if len(geometry) == 1 else unary_union(geometry)
        boundary = shapely_transform(
            Transformer.from_crs("EPSG:3005", crs, always_xy=True).transform, boundary
        )
    else:
        import geopandas as gpd

        frame = gpd.read_file(path)
        if frame.crs is not None and frame.crs.to_string() != crs:
            frame = frame.to_crs(crs)
        boundary = frame.geometry.union_all() if hasattr(frame.geometry, "union_all") else frame.geometry.unary_union
    return boundary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--origin-x", type=float, default=549275.0)
    parser.add_argument("--origin-y", type=float, default=5784675.0)
    parser.add_argument("--grid-size-m", type=float, default=25.0)
    parser.add_argument("--raster", action="store_true", help="Write a 3-band 25 m GeoTIFF")
    args = parser.parse_args()
    parts = sorted(args.parts.glob("batch_*.parquet"))
    if not parts:
        raise SystemExit(f"No batch parts in {args.parts}")
    frame = pd.concat([pd.read_parquet(path) for path in parts], ignore_index=True)
    print(f"raw rows={len(frame)}", flush=True)
    frame = frame.drop_duplicates("fragment_id", keep="first").reset_index(drop=True)
    boundary = load_boundary(args.boundary)
    inside = contains_xy(boundary, frame.x_center.to_numpy(), frame.y_center.to_numpy())
    frame = frame[inside].reset_index(drop=True)
    print(f"inside rows={len(frame)}", flush=True)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.out_dir / "features_full.parquet", index=False)

    rows = []
    for name in ("lorey_height", "basal_area", "gross_volume"):
        card_path = args.models / f"als_tsa23_idf_{name}_2026.json"
        card = json.loads(card_path.read_text(encoding="utf-8"))
        features = list(card["coefficients"])
        valid = pd.Series(True, index=frame.index)
        for feature in features:
            low, high = card["predictor_ranges"][feature]
            valid &= frame[feature].between(low, high)
        selected = frame[valid]
        if card["link"] == "log":
            values = card["intercept"] + sum(
                card["coefficients"][feature] * np.log(selected[feature].to_numpy(float))
                for feature in features
            )
            values = np.exp(values) * card["output_scale"]
        else:
            values = (
                card["intercept"]
                + sum(card["coefficients"][feature] * selected[feature].to_numpy(float) for feature in features)
            ) * card["output_scale"]
        print(f"{name} cells={len(selected)}", flush=True)
        for fragment_id, value in zip(selected.fragment_id, values):
            rows.append(
                {
                    "fragment_id": fragment_id,
                    "attribute": card["attribute"],
                    "value": float(value),
                    "model_id": card["model_id"],
                    "rmse": card["rmse"],
                    "model_version": card["model_version"],
                    "unit": card["unit"],
                    "source": card["source"],
                }
            )
    inventory = pd.DataFrame(rows)
    inventory.to_parquet(args.out_dir / "inventory_full.parquet", index=False)
    summary = {
        "feature_cells": len(frame),
        "attribute_summary": {},
    }
    for attribute, group in inventory.groupby("attribute"):
        summary["attribute_summary"][attribute] = {
            "cells": len(group),
            "mean": float(group.value.mean()),
            "median": float(group.value.median()),
            "min": float(group.value.min()),
            "max": float(group.value.max()),
            "rmse": float(group.rmse.iloc[0]),
        }
    (args.out_dir / "summary_full.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if args.raster:
        predictions = inventory.pivot_table(index="fragment_id", columns="attribute", values="value")
        points = frame[["fragment_id", "x_center", "y_center"]].set_index("fragment_id").join(predictions)
        width = math.ceil((points.x_center.max() - args.origin_x) / args.grid_size_m) + 1
        height = math.ceil((args.origin_y - points.y_center.min()) / args.grid_size_m) + 1
        columns = np.floor((points.x_center.to_numpy() - args.origin_x) / args.grid_size_m).astype(int)
        rows_index = np.floor((args.origin_y - points.y_center.to_numpy()) / args.grid_size_m).astype(int)
        bands = {
            "lorey_height_m": "lorey_height_m",
            "ba_m2_ha": "ba_m2_ha",
            "vol_m3_ha": "vol_m3_ha",
        }
        arrays = {name: np.full((height, width), -9999.0, dtype="float32") for name in bands}
        for name, column in bands.items():
            values = points[column].to_numpy(float)
            ok = np.isfinite(values) & (columns >= 0) & (columns < width) & (rows_index >= 0) & (rows_index < height)
            arrays[name][rows_index[ok], columns[ok]] = values[ok].astype("float32")
        output = args.out_dir / "tsa23_idf_full_25m.tif"
        with rasterio.open(
            output,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=3,
            dtype="float32",
            crs="EPSG:3157",
            transform=from_origin(args.origin_x, args.origin_y, args.grid_size_m, args.grid_size_m),
            nodata=-9999.0,
            compress="deflate",
            tiled=True,
        ) as dataset:
            for index, name in enumerate(bands, 1):
                dataset.write(arrays[name], index)
                dataset.set_band_description(index, name)
        print(f"wrote {output}", flush=True)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
