"""VDYP table I/O helpers extracted from legacy TSA runner."""

from __future__ import annotations

import csv
import io
import importlib
from pathlib import Path
import re
from typing import Any, cast


def _build_aligned_vdyp_input_tables(
    *,
    feature_ids: list[int] | Any,
    vdyp_ply: Any,
    vdyp_lyr: Any,
) -> tuple[Any, Any]:
    """Filter VDYP polygon/layer tables to a shared, stably ordered feature set."""
    vdyp_ply_ = vdyp_ply[vdyp_ply.FEATURE_ID.isin(feature_ids)].copy()
    vdyp_lyr_ = vdyp_lyr[vdyp_lyr.FEATURE_ID.isin(feature_ids)].copy()

    common_feature_ids = set(vdyp_ply_["FEATURE_ID"]).intersection(
        vdyp_lyr_["FEATURE_ID"]
    )
    vdyp_ply_ = vdyp_ply_[vdyp_ply_.FEATURE_ID.isin(common_feature_ids)].copy()
    vdyp_lyr_ = vdyp_lyr_[vdyp_lyr_.FEATURE_ID.isin(common_feature_ids)].copy()

    # Keep same-feature layer rows in source order while still grouping batches by feature.
    vdyp_ply_.sort_values(by="FEATURE_ID", inplace=True, kind="mergesort")
    vdyp_lyr_.sort_values(by="FEATURE_ID", inplace=True, kind="mergesort")
    return vdyp_ply_, vdyp_lyr_


def write_vdyp_infiles_plylyr(
    feature_ids: list[int] | Any,
    vdyp_ply: Any,
    vdyp_lyr: Any,
    vdyp_io_dirname: str = "vdyp_io",
    vdyp_ply_csv: str = "vdyp_ply.csv",
    vdyp_lyr_csv: str = "vdyp_lyr.csv",
) -> None:
    """Write filtered/sorted VDYP polygon and layer CSV input tables."""
    vdyp_io_dir = Path(vdyp_io_dirname)
    vdyp_io_dir.mkdir(parents=True, exist_ok=True)

    vdyp_ply_, vdyp_lyr_ = _build_aligned_vdyp_input_tables(
        feature_ids=feature_ids,
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
    )
    vdyp_ply_.to_csv(
        vdyp_io_dir / vdyp_ply_csv,
        columns=list(vdyp_ply.columns)[:-5],
        index=False,
        quoting=csv.QUOTE_NONNUMERIC,
    )

    vdyp_lyr_.to_csv(
        vdyp_io_dir / vdyp_lyr_csv,
        columns=list(vdyp_lyr.columns)[:-5],
        index=False,
        quoting=csv.QUOTE_NONNUMERIC,
    )


def import_vdyp_tables(filename: str | Path) -> dict[int, Any]:
    """Parse VDYP console output tables keyed by per-run table number."""
    pd = importlib.import_module("pandas")

    text = Path(filename).read_text(encoding="utf-8", errors="ignore")
    chunks = re.findall(r"(?<=vvvvvvvvvv.).*?(?=\^)", text, re.DOTALL)
    result: dict[int, Any] = {}
    for chunk in chunks:
        lines = chunk.split("\n")
        table_number_match = re.search(r"Table Number:\s*(\d+)", lines[0])
        map_name_match = re.search(r"Map Name:\s*([A-Za-z0-9]+)", lines[0])
        polygon_match = re.search(r"(?<=Polygon:.)\d+", lines[0])
        if table_number_match is None and polygon_match is None:
            continue
        table_number = (
            int(table_number_match.group(1))
            if table_number_match is not None
            else int(cast(re.Match[str], polygon_match).group())
        )
        polygon_id = int(polygon_match.group()) if polygon_match is not None else None
        map_name = map_name_match.group(1) if map_name_match is not None else None
        result_ = pd.read_fwf(
            io.StringIO(chunk),
            skiprows=[0, 2],
            index_col="Age",
            infer_nrows=200,
        )
        if isinstance(result_, pd.DataFrame):
            if polygon_id is not None:
                result_.attrs["vdyp_polygon_id"] = polygon_id
            if map_name is not None:
                result_.attrs["vdyp_map_name"] = map_name
            result_.attrs["vdyp_table_number"] = table_number
            result[table_number] = result_
    return result
