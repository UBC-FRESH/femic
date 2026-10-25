from __future__ import annotations

import csv
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Point, box
from typer.testing import CliRunner

from femic.cli import main as cli_main
from femic.lidar import canopy as canopy_module
from femic.lidar import trees as trees_module
from femic.lidar.canopy import (
    CanopyProcessingError,
    build_canopy_products,
    compare_canopy_to_vri,
    derive_canopy_height_model,
    derive_canopy_structure,
)
from femic.lidar.terrain import TerrainProcessingError
from femic.lidar.trees import (
    TreeProductError,
    inspect_individual_tree_product,
    summarize_individual_trees_by_block,
    write_individual_tree_summary,
    write_tree_block_summary_csv,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    transform: rasterio.transform.Affine | None = None,
    crs: str = "EPSG:3005",
    nodata: float | None = -9999.0,
) -> Path:
    height, width = values.shape
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform or from_origin(0, height, 1, 1),
        nodata=nodata,
    ) as dataset:
        dataset.write(values.astype(np.float32), 1)
    return path


def _dsm_dem(tmp_path: Path) -> tuple[Path, Path]:
    dem = np.tile(100.0 + np.arange(10, dtype=float), (10, 1))
    dsm = dem + 10.0
    return (
        _write_raster(tmp_path / "dem.tif", dem),
        _write_raster(tmp_path / "dsm.tif", dsm),
    )


def _vri(path: Path, *, crs: str = "EPSG:3005") -> Path:
    frame = gpd.GeoDataFrame(
        {
            "feature_id": [1],
            "proj_height_1": [8.0],
            "crown_closure": [80.0],
        },
        geometry=[box(0, 0, 5, 5)],
        crs=crs,
    )
    frame.to_file(path, driver="GeoJSON")
    return path


def _trees_and_blocks(tmp_path: Path) -> tuple[Path, Path]:
    trees = gpd.GeoDataFrame(
        {
            "tree_id": ["t1", "t2", "t2", "t3", "t4"],
            "height_m": [10.0, 12.0, 12.0, None, 11.0],
            "crown_radius_m": [2.0, 2.5, 2.5, 1.5, 2.0],
            "species": ["HW", "CW", "CW", "HW", "FD"],
        },
        geometry=[
            Point(1, 1),
            Point(2, 2),
            Point(3, 3),
            Point(5, 5),
            Point(20, 20),
        ],
        crs="EPSG:3005",
    )
    blocks = gpd.GeoDataFrame(
        {"block_id": ["b1", "b2"]},
        geometry=[box(0, 0, 4, 4), box(4, 4, 6, 6)],
        crs="EPSG:3005",
    )
    tree_path = tmp_path / "trees.geojson"
    block_path = tmp_path / "blocks.geojson"
    trees.to_file(tree_path, driver="GeoJSON")
    blocks.to_file(block_path, driver="GeoJSON")
    return tree_path, block_path


def test_derive_chm_and_structure(tmp_path: Path) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    chm = derive_canopy_height_model(
        dsm,
        dem,
        tmp_path / "chm.tif",
        vertical_datum="CGVD2013",
        generated_utc=GENERATED_UTC,
    )

    assert chm.valid_pixels == 100
    assert chm.nodata_pixels == 0
    assert chm.negative_pixels == 0
    assert chm.vertical_datum == "CGVD2013"
    assert chm.height_metrics["mean_m"] == pytest.approx(10.0)
    assert chm.height_metrics["p95_m"] == pytest.approx(10.0)
    assert chm.cover_fractions["ge_2m"] == pytest.approx(100.0)
    assert chm.cover_fractions["ge_20m"] == pytest.approx(0.0)
    assert chm.valid_area_ha == pytest.approx(0.01)

    structure = derive_canopy_structure(chm.path, generated_utc=GENERATED_UTC)
    assert structure.valid_pixels == 100
    assert structure.height_metrics["mean_m"] == pytest.approx(10.0)
    assert structure.to_dict()["thresholds_m"] == [2.0, 5.0, 10.0, 20.0]


def test_chm_negative_nodata_and_no_clamp(tmp_path: Path) -> None:
    dem = np.tile(100.0 + np.arange(10, dtype=float), (10, 1))
    dsm = dem + 10.0
    dsm[0, 0] = 90.0
    dem[0, 1] = -9999.0
    dem_path = _write_raster(tmp_path / "dem.tif", dem)
    dsm_path = _write_raster(tmp_path / "dsm.tif", dsm)

    clamped = derive_canopy_height_model(
        dsm_path,
        dem_path,
        tmp_path / "chm_clamped.tif",
    )
    assert clamped.negative_pixels == 1
    assert clamped.height_metrics["min_m"] == pytest.approx(0.0)
    assert any("clamped" in warning for warning in clamped.warnings)

    raw = derive_canopy_height_model(
        dsm_path,
        dem_path,
        tmp_path / "chm_raw.tif",
        clamp_negative=False,
    )
    assert raw.height_metrics["min_m"] < 0.0
    assert raw.nodata_pixels == 1


def test_chm_rejects_misaligned_and_geographic(tmp_path: Path) -> None:
    dem, _dsm = _dsm_dem(tmp_path)
    shifted = _write_raster(
        tmp_path / "shifted.tif",
        np.ones((10, 10)),
        transform=from_origin(1, 10, 1, 1),
    )
    with pytest.raises(CanopyProcessingError, match="same grid"):
        derive_canopy_height_model(shifted, dem, tmp_path / "chm.tif")

    geographic_dem = _write_raster(
        tmp_path / "geographic_dem.tif",
        np.ones((10, 10)),
        crs="EPSG:4326",
    )
    geographic_dsm = _write_raster(
        tmp_path / "geographic_dsm.tif",
        np.ones((10, 10)) * 2.0,
        crs="EPSG:4326",
    )
    with pytest.raises(TerrainProcessingError, match="projected CRS"):
        derive_canopy_height_model(
            geographic_dsm,
            geographic_dem,
            tmp_path / "chm.tif",
        )

    with pytest.raises(CanopyProcessingError, match="non-negative"):
        derive_canopy_structure(dem, thresholds_m=(-1.0,))
    with pytest.raises(CanopyProcessingError, match="At least one"):
        derive_canopy_structure(dem, thresholds_m=())


def test_build_canopy_products_with_vri(tmp_path: Path) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    vri = _vri(tmp_path / "vri.geojson")
    output = tmp_path / "canopy"

    report = build_canopy_products(
        dsm,
        dem,
        output,
        vertical_datum="CGVD2013",
        vri_path=vri,
        generated_utc=GENERATED_UTC,
    )

    assert report.vri_comparison is not None
    comparison = report.vri_comparison
    assert comparison.matched_count == 1
    assert comparison.height_bias_m == pytest.approx(2.0)
    assert comparison.height_mae_m == pytest.approx(2.0)
    assert comparison.cover_bias_pct == pytest.approx(20.0)
    assert comparison.rows[0].chm_p95_m == pytest.approx(10.0)
    assert (output / "chm.tif").is_file()
    assert (output / "canopy_structure.json").is_file()
    assert (output / "canopy_qa.json").is_file()
    assert (output / "canopy_qa.csv").is_file()
    assert (output / "vri_canopy_comparison.csv").is_file()
    payload = json.loads((output / "canopy_qa.json").read_text())
    assert payload["schema_version"] == "femic.lidar.canopy_qa.v1"
    assert payload["vri_comparison"]["matched_count"] == 1
    with (output / "canopy_qa.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["product"] == "chm"


def test_vri_errors_and_no_overlap(tmp_path: Path) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    chm = derive_canopy_height_model(dsm, dem, tmp_path / "chm.tif")

    missing_field = gpd.GeoDataFrame(
        {"feature_id": [1], "crown_closure": [80.0]},
        geometry=[box(0, 0, 5, 5)],
        crs="EPSG:3005",
    )
    missing_path = tmp_path / "missing.geojson"
    missing_field.to_file(missing_path, driver="GeoJSON")
    with pytest.raises(CanopyProcessingError, match="height field"):
        compare_canopy_to_vri(chm.path, missing_path)

    wrong_crs = _vri(tmp_path / "wrong_crs.geojson", crs="EPSG:4326")
    with pytest.raises(CanopyProcessingError, match="does not match"):
        compare_canopy_to_vri(chm.path, wrong_crs)

    outside = gpd.GeoDataFrame(
        {
            "feature_id": [2],
            "proj_height_1": [8.0],
            "crown_closure": [80.0],
        },
        geometry=[box(100, 100, 105, 105)],
        crs="EPSG:3005",
    )
    outside_path = tmp_path / "outside.geojson"
    outside.to_file(outside_path, driver="GeoJSON")
    comparison = compare_canopy_to_vri(chm.path, outside_path)
    assert comparison.matched_count == 0
    assert comparison.skipped_count == 1
    assert any("No VRI polygons" in warning for warning in comparison.warnings)


def test_canopy_cli(tmp_path: Path) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    vri = _vri(tmp_path / "vri.geojson")
    output = tmp_path / "canopy"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "canopy",
            "--dem",
            str(dem),
            "--dsm",
            str(dsm),
            "--output-dir",
            str(output),
            "--vertical-datum",
            "CGVD2013",
            "--vri",
            str(vri),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "canopy products built" in result.output
    assert "vri_matched: 1" in result.output
    assert (output / "chm.tif").is_file()


def test_canopy_cli_error(tmp_path: Path) -> None:
    dem, _dsm = _dsm_dem(tmp_path)
    shifted = _write_raster(
        tmp_path / "shifted.tif",
        np.ones((10, 10)),
        transform=from_origin(1, 10, 1, 1),
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "canopy",
            "--dem",
            str(dem),
            "--dsm",
            str(shifted),
            "--output-dir",
            str(tmp_path / "canopy"),
        ],
    )

    assert result.exit_code == 1
    assert "canopy error" in result.output


def test_inspect_individual_tree_product(tmp_path: Path) -> None:
    trees, _ = _trees_and_blocks(tmp_path)

    summary = inspect_individual_tree_product(trees, generated_utc=GENERATED_UTC)

    assert summary.feature_count == 5
    assert summary.unique_tree_count == 4
    assert summary.duplicate_tree_count == 2
    assert summary.missing_height_count == 1
    assert summary.height_metrics["count"] == 4
    assert summary.crown_metrics["count"] == 5
    assert summary.species_counts == {"CW": 2, "FD": 1, "HW": 2}
    assert summary.geometry_types == ("Point",)
    assert summary.crs == "EPSG:3005"

    path = write_individual_tree_summary(summary, tmp_path / "summary.json")
    assert json.loads(path.read_text())["feature_count"] == 5


def test_tree_product_rejects_bad_inputs(tmp_path: Path) -> None:
    trees, _ = _trees_and_blocks(tmp_path)
    payload = gpd.read_file(trees)
    missing = payload.drop(columns=["height_m"])
    missing_path = tmp_path / "missing.geojson"
    missing.to_file(missing_path, driver="GeoJSON")
    with pytest.raises(TreeProductError, match="missing"):
        inspect_individual_tree_product(missing_path)

    polygons = gpd.GeoDataFrame(
        {"tree_id": ["p1"], "height_m": [10.0]},
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:3005",
    )
    polygon_path = tmp_path / "polygons.geojson"
    polygons.to_file(polygon_path, driver="GeoJSON")
    with pytest.raises(TreeProductError, match="point-based"):
        inspect_individual_tree_product(polygon_path)


def test_tree_block_summary(tmp_path: Path) -> None:
    trees, blocks = _trees_and_blocks(tmp_path)

    summary = summarize_individual_trees_by_block(
        trees,
        blocks,
        generated_utc=GENERATED_UTC,
    )

    assert len(summary.rows) == 2
    first, second = summary.rows
    assert first.block_id == "b1"
    assert first.tree_count == 3
    assert first.mean_height_m == pytest.approx(11.3333333)
    assert first.max_height_m == pytest.approx(12.0)
    assert second.block_id == "b2"
    assert second.tree_count == 1
    assert any("outside all blocks" in warning for warning in summary.warnings)

    csv_path = write_tree_block_summary_csv(
        summary,
        tmp_path / "blocks.csv",
    )
    assert "block_id,tree_count" in csv_path.read_text()
    assert "b1" in csv_path.read_text()


def test_tree_block_crs_mismatch(tmp_path: Path) -> None:
    trees, _blocks = _trees_and_blocks(tmp_path)
    blocks_frame = gpd.GeoDataFrame(
        {"block_id": ["b1"]},
        geometry=[box(-1, -1, 1, 1)],
        crs="EPSG:4326",
    )
    wrong_blocks = tmp_path / "wrong_blocks.geojson"
    blocks_frame.to_file(wrong_blocks, driver="GeoJSON")

    with pytest.raises(TreeProductError, match="CRS do not match"):
        summarize_individual_trees_by_block(trees, wrong_blocks)


def test_tree_cli_and_instance_default(tmp_path: Path) -> None:
    trees, blocks = _trees_and_blocks(tmp_path)
    instance = tmp_path / "instance"
    instance.mkdir()

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "trees",
            "--product",
            str(trees),
            "--instance-root",
            str(instance),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "tree product summary written" in result.output
    assert (instance / "data/lidar/trees/tree_product_summary.json").is_file()

    block_result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "trees",
            "--product",
            str(trees),
            "--blocks",
            str(blocks),
            "--output-dir",
            str(tmp_path / "tree_blocks"),
        ],
    )
    assert block_result.exit_code == 0, block_result.output
    assert "tree block summary written" in block_result.output
    assert (tmp_path / "tree_blocks/tree_block_summary.csv").is_file()


def test_vri_min_pixels_missing_fields_and_read_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    chm = derive_canopy_height_model(dsm, dem, tmp_path / "chm.tif")
    vri = _vri(tmp_path / "vri.geojson")

    with pytest.raises(CanopyProcessingError, match="min_valid_pixels"):
        compare_canopy_to_vri(chm.path, vri, min_valid_pixels=0)

    no_id = gpd.read_file(vri).drop(columns=["feature_id"])
    no_id_path = tmp_path / "no_id.geojson"
    no_id.to_file(no_id_path, driver="GeoJSON")
    with pytest.raises(CanopyProcessingError, match="identifier field"):
        compare_canopy_to_vri(chm.path, no_id_path)

    no_cover = gpd.read_file(vri).drop(columns=["crown_closure"])
    no_cover_path = tmp_path / "no_cover.geojson"
    no_cover.to_file(no_cover_path, driver="GeoJSON")
    with pytest.raises(CanopyProcessingError, match="cover field"):
        compare_canopy_to_vri(chm.path, no_cover_path)

    bad_path = tmp_path / "bad.geojson"
    bad_path.write_text("not-geojson")
    with pytest.raises(CanopyProcessingError, match="Unable to read VRI"):
        compare_canopy_to_vri(chm.path, bad_path)

    empty_geometry = gpd.GeoDataFrame(
        {
            "feature_id": [1],
            "proj_height_1": [8.0],
            "crown_closure": [80.0],
        },
        geometry=[None],
        crs="EPSG:3005",
    )
    monkeypatch.setattr(
        canopy_module.gpd,
        "read_file",
        lambda path: empty_geometry,
    )
    comparison = compare_canopy_to_vri(chm.path, vri)
    assert comparison.matched_count == 0
    assert comparison.skipped_count == 1

    no_crs = empty_geometry.set_crs(None, allow_override=True)
    monkeypatch.setattr(canopy_module.gpd, "read_file", lambda path: no_crs)
    with pytest.raises(CanopyProcessingError, match="no CRS"):
        compare_canopy_to_vri(chm.path, vri)
    monkeypatch.undo()

    tiny = gpd.GeoDataFrame(
        {
            "feature_id": [3],
            "proj_height_1": [8.0],
            "crown_closure": [80.0],
        },
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:3005",
    )
    tiny_path = tmp_path / "tiny.geojson"
    tiny.to_file(tiny_path, driver="GeoJSON")
    comparison = compare_canopy_to_vri(chm.path, tiny_path)
    assert comparison.matched_count == 0
    assert comparison.skipped_count == 1


def test_canopy_all_nodata_and_duplicate_thresholds(tmp_path: Path) -> None:
    nodata = np.full((5, 5), -9999.0)
    dem = _write_raster(tmp_path / "dem.tif", nodata)
    dsm = _write_raster(tmp_path / "dsm.tif", nodata)
    chm = derive_canopy_height_model(dsm, dem, tmp_path / "chm.tif")

    assert chm.valid_pixels == 0
    assert chm.height_metrics["mean_m"] is None
    assert chm.cover_fractions["ge_2m"] == 0.0

    structure = derive_canopy_structure(
        chm.path,
        thresholds_m=(2.0, 2.0, 5.0),
    )
    assert structure.thresholds_m == (2.0, 5.0)


def test_build_canopy_without_vri(tmp_path: Path) -> None:
    dem, dsm = _dsm_dem(tmp_path)
    report = build_canopy_products(dsm, dem, tmp_path / "canopy")
    assert report.vri_comparison is None


def test_optional_float_canopy_helper() -> None:
    assert canopy_module._optional_float(None) is None
    assert canopy_module._optional_float(3) == 3.0
    assert canopy_module._optional_float("3.5") == 3.5
    assert canopy_module._optional_float("bad") is None
    assert canopy_module._optional_float(object()) is None
    assert canopy_module._optional_float(float("nan")) is None


def test_tree_warnings_and_helpers(tmp_path: Path) -> None:
    trees = gpd.GeoDataFrame(
        {"tree_id": ["t1"], "height_m": [10.0]},
        geometry=[Point(1, 1)],
        crs="EPSG:4326",
    )
    path = tmp_path / "trees.geojson"
    trees.to_file(path, driver="GeoJSON")

    summary = inspect_individual_tree_product(path)
    assert any("not projected" in warning for warning in summary.warnings)
    assert any("crown field" in warning for warning in summary.warnings)
    assert any("species field" in warning for warning in summary.warnings)
    assert summary.species_counts == {}
    assert summary.crown_metrics["count"] == 0


def test_tree_read_errors_and_empty_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad = tmp_path / "bad.geojson"
    bad.write_text("not-geojson")
    with pytest.raises(TreeProductError, match="Unable to read"):
        inspect_individual_tree_product(bad)

    monkeypatch.setattr(
        trees_module.gpd,
        "read_file",
        lambda path: gpd.GeoDataFrame(
            {"tree_id": [], "height_m": []},
            geometry=[],
            crs="EPSG:3005",
        ),
    )
    with pytest.raises(TreeProductError, match="no features"):
        inspect_individual_tree_product(bad)


def test_tree_block_missing_field_and_all_within(tmp_path: Path) -> None:
    trees, blocks = _trees_and_blocks(tmp_path)
    blocks_frame = gpd.read_file(blocks).rename(columns={"block_id": "other"})
    wrong_blocks = tmp_path / "wrong_blocks.geojson"
    blocks_frame.to_file(wrong_blocks, driver="GeoJSON")
    with pytest.raises(TreeProductError, match="block_id"):
        summarize_individual_trees_by_block(trees, wrong_blocks)

    all_blocks = gpd.GeoDataFrame(
        {"block_id": ["all"]},
        geometry=[box(-1, -1, 30, 30)],
        crs="EPSG:3005",
    )
    all_blocks_path = tmp_path / "all_blocks.geojson"
    all_blocks.to_file(all_blocks_path, driver="GeoJSON")
    summary = summarize_individual_trees_by_block(
        trees,
        all_blocks_path,
        species_field=None,
    )
    assert len(summary.rows) == 1
    assert summary.rows[0].tree_count == 5
    assert summary.rows[0].species_counts == {}
    assert not any("outside all blocks" in warning for warning in summary.warnings)
    assert summary.to_dict()["rows"][0]["block_id"] == "all"
    assert summary.rows[0].to_dict()["tree_count"] == 5


def test_tree_block_read_error_and_numeric_helpers(tmp_path: Path) -> None:
    trees, _ = _trees_and_blocks(tmp_path)
    bad_blocks = tmp_path / "bad.json"
    bad_blocks.write_text("not-json")
    with pytest.raises(TreeProductError, match="Unable to read"):
        summarize_individual_trees_by_block(trees, bad_blocks)

    assert trees_module._numeric_values([object()]).size == 0
    assert trees_module._distribution(np.asarray([], dtype=float))["count"] == 0


def test_tree_no_crs_and_block_empty_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trees, blocks = _trees_and_blocks(tmp_path)
    no_crs = gpd.read_file(trees).set_crs(None, allow_override=True)
    monkeypatch.setattr(trees_module.gpd, "read_file", lambda path: no_crs)
    with pytest.raises(TreeProductError, match="no CRS"):
        inspect_individual_tree_product(trees)

    empty_blocks = gpd.GeoDataFrame(
        {"block_id": []},
        geometry=[],
        crs="EPSG:3005",
    )
    trees_frame = gpd.read_file(trees)
    monkeypatch.setattr(
        trees_module.gpd,
        "read_file",
        lambda path: (
            empty_blocks if str(path).endswith("blocks.geojson") else trees_frame
        ),
    )
    with pytest.raises(TreeProductError, match="must both contain"):
        summarize_individual_trees_by_block(trees, blocks)

    monkeypatch.undo()
    with pytest.raises(TreeProductError, match="missing"):
        summarize_individual_trees_by_block(trees, blocks, height_field="missing")
