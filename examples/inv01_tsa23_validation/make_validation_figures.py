"""Generate the VRI comparison and omitted-tile priority figures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import wkb
from shapely.geometry import box
from shapely.ops import unary_union


def load_boundary(path: Path) -> object:
    if path.suffix.lower() == ".feather":
        frame = pd.read_feather(path)
        return wkb.loads(frame.geometry.iloc[0])
    frame = gpd.read_file(path)
    return frame.geometry.union_all() if hasattr(frame.geometry, "union_all") else frame.geometry.unary_union


def vri_figure(cells_path: Path, output: Path) -> None:
    cells = pd.read_parquet(cells_path)
    specs = [
        ("lorey_height_m", "PROJ_HEIGHT_1", "Lorey height (m)", "VRI projected height (m)"),
        ("ba_m2_ha", "BASAL_AREA", "Predicted BA (m2/ha)", "VRI basal area (m2/ha)"),
        ("vol_m3_ha", "LIVE_STAND_VOLUME_125", "Predicted gross volume (m3/ha)", "VRI live volume >=12.5 (m3/ha)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (pred, obs, xlabel, ylabel) in zip(axes, specs, strict=True):
        data = cells[[pred, obs]].dropna()
        data = data[(data[pred] > 0) & (data[obs] > 0)]
        if len(data) > 300_000:
            data = data.sample(300_000, random_state=42)
        p = data[pred].to_numpy(float)
        o = data[obs].to_numpy(float)
        heat = ax.hexbin(o, p, gridsize=80, mincnt=1, bins="log", cmap="viridis", linewidths=0)
        limit = max(np.quantile(o, 0.995), np.quantile(p, 0.995))
        ax.plot([0, limit], [0, limit], color="#b2182b", linestyle="--", linewidth=1)
        ax.set_xlim(0, limit)
        ax.set_ylim(0, limit)
        ax.set_xlabel(ylabel)
        ax.set_ylabel(xlabel)
        error = p - o
        ax.set_title(f"n={len(data):,}  bias={error.mean():+.2f}  RMSE={np.sqrt((error**2).mean()):.2f}", fontsize=10)
        ax.grid(alpha=0.2)
    fig.suptitle("INV-01 TSA 23: model vs VRI polygon attributes (not independent validation)", fontsize=13)
    fig.colorbar(heat, ax=axes, shrink=0.7, label="log10 cell count")
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def gap_figure(selection_path: Path, manifest_path: Path, boundary_path: Path, gap_path: Path, vertices_path: Path, destinations_path: Path, output: Path) -> None:
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    points = [tile for tile in selection["tiles"] if tile["product"] == "point_cloud"]
    manifest = pd.read_csv(manifest_path)
    processed_ids = set(manifest.tile_id)
    boundary = load_boundary(boundary_path)
    processed = gpd.GeoDataFrame(
        [{"tile_id": tile["tile_id"], "geometry": box(*tile["bbox_epsg3005"])} for tile in points if tile["tile_id"] in processed_ids],
        crs="EPSG:3005",
    )
    all_tiles = gpd.GeoDataFrame(
        [{"tile_id": tile["tile_id"], "geometry": box(*tile["bbox_epsg3005"])} for tile in points],
        crs="EPSG:3005",
    )
    missing = gpd.read_file(gap_path)
    vertices = pd.read_csv(vertices_path)
    destinations = pd.read_csv(destinations_path)
    mills = []
    for name, vertex_id in zip(destinations["name"], destinations["vertex_id"], strict=True):
        row = vertices.loc[vertices.vertex_id == vertex_id].iloc[0]
        mills.append((name, row.x, row.y))

    no_point = boundary.difference(unary_union(all_tiles.geometry.tolist()))
    fig, ax = plt.subplots(figsize=(11, 11))
    gpd.GeoSeries([boundary], crs="EPSG:3005").plot(ax=ax, facecolor="#f4f4f0", edgecolor="#333333", linewidth=1.2, zorder=1)
    gpd.GeoSeries([no_point], crs="EPSG:3005").plot(ax=ax, facecolor="#d9d9d9", edgecolor="#888888", linewidth=0.4, hatch="///", zorder=2)
    processed.plot(ax=ax, facecolor="#b7d9c0", edgecolor="#7fa88c", linewidth=0.05, alpha=0.45, zorder=3)
    colors = {"A": "#b2182b", "B": "#ef8a62", "C": "#fddbc7"}
    for tier in ("C", "B", "A"):
        missing[missing.priority_tier == tier].plot(ax=ax, color=colors[tier], edgecolor="#555555", linewidth=0.08, alpha=0.85, zorder=4)
    gpd.GeoSeries([boundary], crs="EPSG:3005").boundary.plot(ax=ax, color="#111111", linewidth=1.4, zorder=5)
    for name, x, y in mills:
        ax.scatter([x], [y], marker="*", s=180, color="#1f4e79", edgecolor="white", linewidth=0.6, zorder=6)
        ax.annotate(name.replace("destination.", "").replace("_", " "), (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7, color="#1f4e79", zorder=7)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(
        "TSA 23 INV-01: omitted point-cloud tiles by priority\n907 tiles with no matching fine-resolution 1 m DEM",
        fontsize=13,
        loc="left",
    )
    handles = [
        Patch(facecolor="#b7d9c0", edgecolor="#7fa88c", label="processed (5,899 tiles)"),
        Patch(facecolor="#d9d9d9", edgecolor="#888888", hatch="///", label="no public point cloud (2,466 km2)"),
        Patch(facecolor=colors["A"], edgecolor="#555555", label="A: top 20% priority (182)"),
        Patch(facecolor=colors["B"], edgecolor="#555555", label="B: next 30% (272)"),
        Patch(facecolor=colors["C"], edgecolor="#555555", label="C: remaining 50% (453)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#1f4e79", markersize=12, label="mill destination"),
    ]
    ax.legend(handles=handles, loc="lower left", frameon=True, fontsize=9)
    fig.tight_layout()
    fig.savefig(output, dpi=250, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-vri", type=Path, required=True)
    parser.add_argument("--gap-gpkg", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--destinations", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    vri_figure(args.cells_vri, args.out_dir / "inv01-tsa23-vri-reconciliation.png")
    gap_figure(args.selection, args.manifest, args.boundary, args.gap_gpkg, args.vertices, args.destinations, args.out_dir / "inv01-tsa23-gap-priority.png")


if __name__ == "__main__":
    main()
