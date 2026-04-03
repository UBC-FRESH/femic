from __future__ import annotations

from pathlib import Path

import pandas as pd

from femic.pipeline.vdyp_io import import_vdyp_tables, write_vdyp_infiles_plylyr


def test_write_vdyp_infiles_plylyr_filters_and_sorts(tmp_path: Path) -> None:
    ply = pd.DataFrame(
        {
            "FEATURE_ID": [3, 1, 2],
            "A": [30, 10, 20],
            "B": [300, 100, 200],
            "X1": [0, 0, 0],
            "X2": [0, 0, 0],
            "X3": [0, 0, 0],
            "X4": [0, 0, 0],
            "X5": [0, 0, 0],
        }
    )
    lyr = pd.DataFrame(
        {
            "FEATURE_ID": [3, 1, 2, 4],
            "C": [3000, 1000, 2000, 4000],
            "D": [30, 10, 20, 40],
            "Y1": [0, 0, 0, 0],
            "Y2": [0, 0, 0, 0],
            "Y3": [0, 0, 0, 0],
            "Y4": [0, 0, 0, 0],
            "Y5": [0, 0, 0, 0],
        }
    )

    write_vdyp_infiles_plylyr(
        [3, 1],
        ply,
        lyr,
        vdyp_io_dirname=str(tmp_path),
        vdyp_ply_csv="ply.csv",
        vdyp_lyr_csv="lyr.csv",
    )

    ply_out = pd.read_csv(tmp_path / "ply.csv")
    lyr_out = pd.read_csv(tmp_path / "lyr.csv")

    assert ply_out["FEATURE_ID"].tolist() == [1, 3]
    assert lyr_out["FEATURE_ID"].tolist() == [1, 3]


def test_write_vdyp_infiles_plylyr_drops_unmatched_polygons(tmp_path: Path) -> None:
    ply = pd.DataFrame(
        {
            "FEATURE_ID": [30, 10, 20],
            "A": [300, 100, 200],
            "B": [3000, 1000, 2000],
            "X1": [0, 0, 0],
            "X2": [0, 0, 0],
            "X3": [0, 0, 0],
            "X4": [0, 0, 0],
            "X5": [0, 0, 0],
        }
    )
    lyr = pd.DataFrame(
        {
            "FEATURE_ID": [30, 20, 20],
            "C": [3000, 2000, 2001],
            "D": [30, 20, 21],
            "Y1": [0, 0, 0],
            "Y2": [0, 0, 0],
            "Y3": [0, 0, 0],
            "Y4": [0, 0, 0],
            "Y5": [0, 0, 0],
        }
    )

    write_vdyp_infiles_plylyr(
        [30, 10, 20],
        ply,
        lyr,
        vdyp_io_dirname=str(tmp_path),
        vdyp_ply_csv="ply.csv",
        vdyp_lyr_csv="lyr.csv",
    )

    ply_out = pd.read_csv(tmp_path / "ply.csv")
    lyr_out = pd.read_csv(tmp_path / "lyr.csv")

    assert ply_out["FEATURE_ID"].tolist() == [20, 30]
    assert lyr_out["FEATURE_ID"].tolist() == [20, 20, 30]


def test_write_vdyp_infiles_plylyr_preserves_layer_order_within_feature(
    tmp_path: Path,
) -> None:
    ply = pd.DataFrame(
        {
            "FEATURE_ID": [2, 1],
            "A": [20, 10],
            "B": [200, 100],
            "X1": [0, 0],
            "X2": [0, 0],
            "X3": [0, 0],
            "X4": [0, 0],
            "X5": [0, 0],
        }
    )
    lyr = pd.DataFrame(
        {
            "FEATURE_ID": [2, 1, 1, 2],
            "LAYER_LEVEL_CODE": ["secondary", "older", "younger", "primary"],
            "D": [20, 10, 11, 21],
            "Y1": [0, 0, 0, 0],
            "Y2": [0, 0, 0, 0],
            "Y3": [0, 0, 0, 0],
            "Y4": [0, 0, 0, 0],
            "Y5": [0, 0, 0, 0],
        }
    )

    write_vdyp_infiles_plylyr(
        [2, 1],
        ply,
        lyr,
        vdyp_io_dirname=str(tmp_path),
        vdyp_ply_csv="ply.csv",
        vdyp_lyr_csv="lyr.csv",
    )

    lyr_out = pd.read_csv(tmp_path / "lyr.csv")

    assert lyr_out["FEATURE_ID"].tolist() == [1, 1, 2, 2]
    assert lyr_out["LAYER_LEVEL_CODE"].tolist() == [
        "older",
        "younger",
        "secondary",
        "primary",
    ]


def test_import_vdyp_tables_returns_empty_for_nonmatching_content(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "console.txt"
    out_path.write_text("no vdyp tables here\n", encoding="utf-8")

    parsed = import_vdyp_tables(out_path)

    assert parsed == {}


def test_import_vdyp_tables_uses_table_number_keys_when_polygon_repeats(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "console.txt"
    out_path.write_text(
        (
            "vvvvvvvvvv Table Number: 1 District: Map Name: 092L053 Polygon: 79 Layer: 1 - Primary\n"
            " Age  Vdwb\n"
            " ---- ----\n"
            "  10   1.0\n"
            "^\n"
            "vvvvvvvvvv Table Number: 2 District: Map Name: 092L063 Polygon: 79 Layer: 1 - Primary\n"
            " Age  Vdwb\n"
            " ---- ----\n"
            "  10   2.0\n"
            "^\n"
        ),
        encoding="utf-8",
    )

    parsed = import_vdyp_tables(out_path)

    assert set(parsed.keys()) == {1, 2}
    assert parsed[1].attrs["vdyp_polygon_id"] == 79
    assert parsed[1].attrs["vdyp_map_name"] == "092L053"
    assert parsed[2].attrs["vdyp_polygon_id"] == 79
    assert parsed[2].attrs["vdyp_map_name"] == "092L063"
