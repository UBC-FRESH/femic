from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin

from femic.lidar import terrain
from femic.lidar.terrain import (
    TerrainProcessingError,
    build_terrain_products,
    compute_zonal_statistics,
    derive_slope_percent,
    inspect_terrain_raster,
    rasterize_point_cloud,
    write_terrain_qa_report,
    write_terrain_qa_summary_csv,
)

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    transform: Affine | None = None,
    crs: str | None = "EPSG:3005",
    nodata: float | None = -9999.0,
    count: int = 1,
) -> Path:
    height, width = values.shape
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype="float32",
        crs=crs,
        transform=transform or from_origin(0, height, 1, 1),
        nodata=nodata,
    ) as dataset:
        for band in range(1, count + 1):
            dataset.write(values.astype(np.float32), band)
    return path


def _plane(height: int = 5, width: int = 5) -> np.ndarray:
    return np.tile(np.arange(width, dtype=float), (height, 1))


def test_inspect_raster_metadata(tmp_path: Path) -> None:
    path = _write_raster(tmp_path / "dem.tif", _plane())

    metadata = inspect_terrain_raster(path)

    assert metadata.crs == "EPSG:3005"
    assert metadata.width == 5
    assert metadata.height == 5
    assert metadata.resolution_x == 1.0
    assert metadata.resolution_y == 1.0
    assert metadata.nodata == -9999.0
    assert metadata.band_count == 1
    assert metadata.bounds == (0.0, 0.0, 5.0, 5.0)
    assert metadata.to_dict()["path"] == str(path.resolve())


def test_derive_slope_percent_from_plane(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _plane())
    output = tmp_path / "slope.tif"

    result = derive_slope_percent(source, output, generated_utc=GENERATED_UTC)

    assert result.product == "slope_percent"
    assert result.algorithm == "horn_3x3"
    assert result.valid_pixels == 25
    assert result.nodata_pixels == 0
    assert result.min_value == pytest.approx(50.0)
    assert result.max_value == pytest.approx(100.0)
    assert result.mean_value == pytest.approx(80.0)
    assert result.metadata.crs == "EPSG:3005"
    assert result.parameters["resampling"] == "none"
    with rasterio.open(output) as dataset:
        slope = dataset.read(1)
        assert dataset.crs is not None
        assert dataset.transform == from_origin(0, 5, 1, 1)
    assert np.allclose(slope[1:-1, 1:-1], 100.0)


def test_derive_slope_percent_flat_and_nodata(tmp_path: Path) -> None:
    flat = np.zeros((5, 5), dtype=float)
    flat_path = _write_raster(tmp_path / "flat.tif", flat)
    flat_result = derive_slope_percent(flat_path, tmp_path / "flat_slope.tif")
    assert flat_result.max_value == pytest.approx(0.0)

    with_hole = flat.copy()
    with_hole[2, 2] = -9999.0
    hole_path = _write_raster(tmp_path / "hole.tif", with_hole)
    hole_result = derive_slope_percent(
        hole_path,
        tmp_path / "hole_slope.tif",
        nodata=-1.0,
    )
    with rasterio.open(hole_result.path) as dataset:
        slope = dataset.read(1)
        assert dataset.nodata == -1.0
    assert np.all(slope[1:4, 1:4] == -1.0)
    assert hole_result.nodata_pixels == 9


def test_slope_rejects_geographic_rotated_and_multiband_inputs(
    tmp_path: Path,
) -> None:
    geographic = _write_raster(
        tmp_path / "geographic.tif",
        _plane(),
        crs="EPSG:4326",
    )
    with pytest.raises(TerrainProcessingError, match="projected CRS"):
        derive_slope_percent(geographic, tmp_path / "out.tif")

    rotated = _write_raster(
        tmp_path / "rotated.tif",
        _plane(),
        transform=Affine(1, 0.1, 0, 0, -1, 0),
    )
    with pytest.raises(TerrainProcessingError, match="unrotated"):
        derive_slope_percent(rotated, tmp_path / "out.tif")

    multiband = _write_raster(
        tmp_path / "multiband.tif",
        _plane(),
        count=2,
    )
    with pytest.raises(TerrainProcessingError, match="exactly one band"):
        derive_slope_percent(multiband, tmp_path / "out.tif")

    no_crs = _write_raster(tmp_path / "no_crs.tif", _plane(), crs=None)
    with pytest.raises(TerrainProcessingError, match="no CRS"):
        derive_slope_percent(no_crs, tmp_path / "out.tif")


def test_build_terrain_products_writes_qa(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _plane())
    output_dir = tmp_path / "terrain"

    report = build_terrain_products(
        source,
        output_dir,
        generated_utc=GENERATED_UTC,
    )

    assert report.product_count == 1
    assert report.products[0].path == (output_dir / "slope_percent.tif").resolve()
    assert (output_dir / "terrain_qa.json").is_file()
    assert (output_dir / "terrain_qa.csv").is_file()
    payload = json.loads((output_dir / "terrain_qa.json").read_text())
    assert payload["schema_version"] == terrain.LIDAR_TERRAIN_QA_SCHEMA_VERSION
    assert payload["summary"]["product_count"] == 1
    assert payload["products"][0]["product"] == "slope_percent"
    with (output_dir / "terrain_qa.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["product"] == "slope_percent"
    assert rows[0]["crs"] == "EPSG:3005"


def test_build_terrain_products_custom_qa_paths_and_errors(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _plane())
    json_path = tmp_path / "custom" / "qa.json"
    csv_path = tmp_path / "custom" / "qa.csv"

    build_terrain_products(
        source,
        tmp_path / "terrain",
        qa_json_path=json_path,
        qa_csv_path=csv_path,
    )
    assert json_path.is_file()
    assert csv_path.is_file()

    with pytest.raises(TerrainProcessingError, match="At least one"):
        build_terrain_products(source, tmp_path / "terrain", products=())
    with pytest.raises(TerrainProcessingError, match="Unsupported"):
        build_terrain_products(source, tmp_path / "terrain", products=("aspect",))


def test_rasterize_point_cloud_aggregations(tmp_path: Path) -> None:
    points = [
        (0.2, 0.5, 10.0),
        (0.8, 0.5, 20.0),
        (1.2, 0.5, 30.0),
        (float("nan"), 0.5, 99.0),
    ]
    kwargs = {
        "output_path": tmp_path / "points.tif",
        "bbox_epsg3005": (0, 0, 2, 1),
        "resolution_m": 1.0,
        "generated_utc": GENERATED_UTC,
    }

    minimum = rasterize_point_cloud(points, aggregation="min", **kwargs)
    with rasterio.open(minimum.path) as dataset:
        assert np.allclose(dataset.read(1), [[10.0, 30.0]])

    maximum = rasterize_point_cloud(points, aggregation="max", **kwargs)
    with rasterio.open(maximum.path) as dataset:
        assert np.allclose(dataset.read(1), [[20.0, 30.0]])

    mean = rasterize_point_cloud(points, aggregation="mean", **kwargs)
    with rasterio.open(mean.path) as dataset:
        assert np.allclose(dataset.read(1), [[15.0, 30.0]])

    count = rasterize_point_cloud(points, aggregation="count", **kwargs)
    with rasterio.open(count.path) as dataset:
        assert np.allclose(dataset.read(1), [[2.0, 1.0]])
    assert count.parameters["point_count"] == 4
    assert count.parameters["rasterized_point_count"] == 3
    assert count.warnings


def test_rasterize_point_cloud_nodata_and_errors(tmp_path: Path) -> None:
    result = rasterize_point_cloud(
        [(0.2, 0.5, 10.0)],
        output_path=tmp_path / "points.tif",
        bbox_epsg3005=(0, 0, 2, 1),
        resolution_m=1.0,
    )
    with rasterio.open(result.path) as dataset:
        assert np.allclose(dataset.read(1), [[10.0, -9999.0]])

    with pytest.raises(TerrainProcessingError, match="aggregation"):
        rasterize_point_cloud(
            [(0.2, 0.5, 10.0)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 1, 1),
            resolution_m=1.0,
            aggregation="median",
        )
    with pytest.raises(TerrainProcessingError, match="native CRS"):
        rasterize_point_cloud(
            [(0.2, 0.5, 10.0)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 1, 1),
            resolution_m=1.0,
            crs="EPSG:4326",
        )
    with pytest.raises(TerrainProcessingError, match="resolution_m"):
        rasterize_point_cloud(
            [(0.2, 0.5, 10.0)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 1, 1),
            resolution_m=0,
        )
    with pytest.raises(TerrainProcessingError, match="Invalid point-cloud AOI"):
        rasterize_point_cloud(
            [(0.2, 0.5, 10.0)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 0, 1),
            resolution_m=1.0,
        )
    with pytest.raises(TerrainProcessingError, match="No finite points"):
        rasterize_point_cloud(
            [(5.0, 5.0, 10.0)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 1, 1),
            resolution_m=1.0,
        )
    with pytest.raises(TerrainProcessingError, match="three values"):
        rasterize_point_cloud(
            [(0.2, 0.5)],
            output_path=tmp_path / "x.tif",
            bbox_epsg3005=(0, 0, 1, 1),
            resolution_m=1.0,
        )


def _zonal_rasters(tmp_path: Path) -> tuple[Path, Path]:
    zones = np.array(
        [
            [1, 1, 2],
            [1, 1, 2],
            [0, 0, 3],
        ],
        dtype=float,
    )
    values = np.array(
        [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, -9999],
        ],
        dtype=float,
    )
    return (
        _write_raster(tmp_path / "zones.tif", zones),
        _write_raster(tmp_path / "values.tif", values),
    )


def test_compute_zonal_statistics(tmp_path: Path) -> None:
    zones, values = _zonal_rasters(tmp_path)

    result = compute_zonal_statistics(
        zones,
        values,
        statistics=("count", "mean", "median", "min", "max", "std", "sum"),
        generated_utc=GENERATED_UTC,
    )

    assert len(result.rows) == 3
    first, second, empty = result.rows
    assert first.zone_id == 1
    assert first.count == 4
    assert first.mean == pytest.approx(3.0)
    assert first.minimum == 1.0
    assert first.maximum == 5.0
    assert first.median == pytest.approx(3.0)
    assert first.stddev == pytest.approx(1.58113883)
    assert first.total == pytest.approx(12.0)
    assert first.area_ha == pytest.approx(0.0004)
    assert second.zone_id == 2
    assert second.count == 2
    assert second.mean == pytest.approx(4.5)
    assert empty.zone_id == 3
    assert empty.count == 0
    assert empty.mean is None
    assert result.to_dict()["statistics"] == [
        "count",
        "mean",
        "median",
        "min",
        "max",
        "std",
        "sum",
    ]
    assert result.warnings[0].startswith("No reprojection")

    subset = compute_zonal_statistics(zones, values, statistics=("count",))
    assert subset.rows[0].mean is None
    assert subset.rows[0].median is None
    assert subset.rows[0].minimum is None
    assert subset.rows[0].maximum is None
    assert subset.rows[0].stddev is None
    assert subset.rows[0].total is None


def test_zonal_statistics_geographic_area_is_omitted(tmp_path: Path) -> None:
    zones = np.array([[1, 1]], dtype=float)
    values = np.array([[1, 2]], dtype=float)
    zones_path = _write_raster(tmp_path / "zones.tif", zones, crs="EPSG:4326")
    values_path = _write_raster(tmp_path / "values.tif", values, crs="EPSG:4326")

    result = compute_zonal_statistics(zones_path, values_path)

    assert result.rows[0].area_ha is None
    assert any("Area hectares" in warning for warning in result.warnings)


def test_zonal_statistics_rejects_misalignment_and_bad_zones(
    tmp_path: Path,
) -> None:
    zones, values = _zonal_rasters(tmp_path)
    shifted = _write_raster(
        tmp_path / "shifted.tif",
        np.ones((3, 3)),
        transform=from_origin(1, 3, 1, 1),
    )
    with pytest.raises(TerrainProcessingError, match="same grid"):
        compute_zonal_statistics(zones, shifted)

    fractional = _write_raster(tmp_path / "fractional.tif", np.full((3, 3), 1.5))
    with pytest.raises(TerrainProcessingError, match="integer zone IDs"):
        compute_zonal_statistics(fractional, values)

    with pytest.raises(TerrainProcessingError, match="At least one"):
        compute_zonal_statistics(zones, values, statistics=())
    with pytest.raises(TerrainProcessingError, match="Unsupported"):
        compute_zonal_statistics(zones, values, statistics=("p95",))


def test_qa_writers_and_result_payloads(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _plane())
    report = build_terrain_products(source, tmp_path / "terrain")
    json_path = write_terrain_qa_report(report, tmp_path / "qa" / "report.json")
    csv_path = write_terrain_qa_summary_csv(report, tmp_path / "qa" / "report.csv")

    assert json.loads(json_path.read_text())["summary"]["product_count"] == 1
    assert csv_path.read_text().startswith("product,path,algorithm")
    assert report.to_dict()["products"][0]["valid_pixels"] == 25


def test_all_nodata_slope_and_projection_helpers(tmp_path: Path) -> None:
    all_nodata = np.full((3, 3), -9999.0)
    path = _write_raster(tmp_path / "nodata.tif", all_nodata)
    result = derive_slope_percent(path, tmp_path / "slope.tif")
    assert result.valid_pixels == 0
    assert result.min_value is None
    assert result.max_value is None
    assert result.mean_value is None

    metadata = inspect_terrain_raster(path)
    assert not terrain._is_projected_metres(
        terrain.TerrainRasterMetadata(
            path=metadata.path,
            crs="",
            transform=metadata.transform,
            width=metadata.width,
            height=metadata.height,
            resolution_x=metadata.resolution_x,
            resolution_y=metadata.resolution_y,
            nodata=metadata.nodata,
            dtype=metadata.dtype,
            band_count=metadata.band_count,
            bounds=metadata.bounds,
        )
    )
    assert not terrain._is_projected_metres(
        terrain.TerrainRasterMetadata(
            path=metadata.path,
            crs="not-a-crs",
            transform=metadata.transform,
            width=metadata.width,
            height=metadata.height,
            resolution_x=metadata.resolution_x,
            resolution_y=metadata.resolution_y,
            nodata=metadata.nodata,
            dtype=metadata.dtype,
            band_count=metadata.band_count,
            bounds=metadata.bounds,
        )
    )
    with pytest.raises(TerrainProcessingError, match="positive pixel resolution"):
        terrain._require_projected_metre_grid(
            terrain.TerrainRasterMetadata(
                path=metadata.path,
                crs=metadata.crs,
                transform=metadata.transform,
                width=metadata.width,
                height=metadata.height,
                resolution_x=0.0,
                resolution_y=metadata.resolution_y,
                nodata=metadata.nodata,
                dtype=metadata.dtype,
                band_count=metadata.band_count,
                bounds=metadata.bounds,
            )
        )


def test_missing_raster_errors(tmp_path: Path) -> None:
    with pytest.raises(TerrainProcessingError, match="Unable to read raster"):
        inspect_terrain_raster(tmp_path / "missing.tif")
    with pytest.raises(TerrainProcessingError, match="Unable to read raster"):
        derive_slope_percent(tmp_path / "missing.tif", tmp_path / "out.tif")
