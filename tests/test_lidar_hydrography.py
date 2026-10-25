from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString

from femic.lidar import hydrography
from femic.lidar.hydrography import (
    StreamCandidateError,
    accumulate_d8_flow,
    compare_stream_candidates,
    derive_d8_flow_direction,
    derive_stream_candidates,
    fill_dem_depressions,
)
from femic.lidar.terrain import TerrainProcessingError

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    transform: rasterio.transform.Affine | None = None,
    crs: str | None = "EPSG:3005",
    nodata: float | None = -9999.0,
    dtype: str = "float32",
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
        dtype=dtype,
        crs=crs,
        transform=transform or from_origin(0, height, 1, 1),
        nodata=nodata,
    ) as dataset:
        dataset.write(values.astype(dtype), 1)
    return path


def _east_dem(height: int = 5, width: int = 5) -> np.ndarray:
    return np.tile(10.0 - np.arange(width, dtype=float), (height, 1))


def _vector_reference(path: Path, *, crs: str = "EPSG:3005") -> Path:
    frame = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[LineString([(3.5, 0.0), (3.5, 5.0)])],
        crs=crs,
    )
    frame.to_file(path, driver="GeoJSON")
    return path


def test_fill_depressions_rejects_bad_arrays_and_epsilon() -> None:
    with pytest.raises(StreamCandidateError, match="epsilon"):
        fill_dem_depressions(np.zeros((2, 2)), np.ones((2, 2)), epsilon=0)
    with pytest.raises(StreamCandidateError, match="must match"):
        fill_dem_depressions(np.zeros((2, 2)), np.ones((3, 3)))


def test_fill_depressions_fills_a_bowl() -> None:
    elevation = np.full((3, 3), 10.0)
    elevation[1, 1] = 1.0
    valid = np.ones((3, 3), dtype=bool)

    filled, isolated = fill_dem_depressions(elevation, valid)

    assert isolated == 0
    assert filled[1, 1] > 10.0
    assert filled[0, 0] == 10.0


def test_fill_depressions_reports_isolated_valid_cells() -> None:
    elevation = np.full((3, 3), 5.0)
    valid = np.zeros((3, 3), dtype=bool)
    valid[1, 1] = True

    filled, isolated = fill_dem_depressions(elevation, valid)

    assert isolated == 1
    assert filled[1, 1] == 5.0


def test_d8_direction_and_accumulation_flow_east() -> None:
    elevation = _east_dem(height=3, width=4)
    valid = np.ones((3, 4), dtype=bool)

    direction, downstream = derive_d8_flow_direction(
        elevation,
        valid,
        resolution_x=1.0,
        resolution_y=1.0,
    )
    accumulation = accumulate_d8_flow(elevation, downstream, valid)

    assert np.all(direction[:, :3] == 1)
    assert np.all(direction[:, 3] == -1)
    assert np.allclose(accumulation, [[1, 2, 3, 4]] * 3)


def test_d8_and_fill_skip_invalid_neighbours() -> None:
    elevation = _east_dem(height=3, width=3)
    valid = np.ones((3, 3), dtype=bool)
    valid[0, 1] = False

    filled, isolated = fill_dem_depressions(elevation, valid)
    direction, downstream = derive_d8_flow_direction(
        filled,
        valid,
        resolution_x=1.0,
        resolution_y=1.0,
    )

    assert isolated == 0
    assert direction.shape == (3, 3)
    assert downstream.shape == (3, 3)


def test_stream_candidates_warn_for_isolated_valid_cells(tmp_path: Path) -> None:
    values = np.full((5, 5), -9999.0)
    values[0, :] = 10.0
    values[-1, :] = 10.0
    values[:, 0] = 10.0
    values[:, -1] = 10.0
    values[2, 2] = 1.0
    source = _write_raster(tmp_path / "isolated.tif", values)

    result = derive_stream_candidates(source, tmp_path / "streams")

    assert any("not connected" in warning for warning in result.manifest.warnings)


def test_reference_vector_without_crs_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    reference = tmp_path / "reference.geojson"
    reference.write_text("{}")

    monkeypatch.setattr(
        hydrography.gpd,
        "read_file",
        lambda path: gpd.GeoDataFrame(
            {"id": [1]},
            geometry=[LineString([(0, 0), (1, 1)])],
            crs=None,
        ),
    )

    with pytest.raises(StreamCandidateError, match="no CRS"):
        derive_stream_candidates(
            source,
            tmp_path / "streams",
            reference_path=reference,
        )


def test_d8_and_accumulation_reject_bad_shapes() -> None:
    with pytest.raises(StreamCandidateError, match="positive resolution"):
        derive_d8_flow_direction(
            np.zeros((2, 2)),
            np.ones((2, 2)),
            resolution_x=0,
            resolution_y=1,
        )
    with pytest.raises(StreamCandidateError, match="must match"):
        derive_d8_flow_direction(
            np.zeros((2, 2)),
            np.ones((3, 3)),
            resolution_x=1,
            resolution_y=1,
        )
    with pytest.raises(StreamCandidateError, match="share one shape"):
        accumulate_d8_flow(
            np.zeros((2, 2)),
            np.zeros((2, 2), dtype=np.int64),
            np.ones((3, 3), dtype=bool),
        )


def test_derive_stream_candidates_east_valley(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    output = tmp_path / "streams"

    result = derive_stream_candidates(
        source,
        output,
        accumulation_threshold=4,
        generated_utc=GENERATED_UTC,
    )

    assert result.manifest.schema_version == hydrography.STREAM_CANDIDATE_SCHEMA_VERSION
    assert result.manifest.qa["candidate_cells"] == 10
    assert result.manifest.qa["candidate_area_ha"] == pytest.approx(0.001)
    assert result.manifest.comparison is None
    assert result.stream_path.is_file()
    assert result.accumulation_path.is_file()
    assert result.manifest_path.is_file()
    assert result.review_path.is_file()
    with rasterio.open(result.stream_path) as dataset:
        stream = dataset.read(1)
        assert dataset.nodata == 255
    assert np.all(stream[:, 3:] == 1)
    assert np.all(stream[:, :3] == 0)
    with rasterio.open(result.accumulation_path) as dataset:
        accumulation = dataset.read(1)
    assert np.max(accumulation) == pytest.approx(5.0)
    manifest = result.manifest.to_dict()
    assert manifest["parameters"]["flow_routing"] == "d8"
    assert manifest["parameters"]["resampling"] == "none"
    assert manifest["outputs"]["stream_candidates"] == "stream_candidates.tif"
    assert len(manifest["caveats"]) >= 4
    review = result.review_path.read_text()
    assert "Terrain-derived stream candidates" in review
    assert "Review checklist" in review
    assert "not an authoritative stream layer" in review


def test_derive_stream_candidates_compares_reference_raster(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    reference_values = np.zeros((5, 5), dtype=np.uint8)
    reference_values[:, 3:] = 1
    reference = _write_raster(
        tmp_path / "reference.tif",
        reference_values,
        dtype="uint8",
        nodata=0,
    )

    result = derive_stream_candidates(
        source,
        tmp_path / "streams",
        accumulation_threshold=4,
        reference_path=reference,
        generated_utc=GENERATED_UTC,
    )

    comparison = result.manifest.comparison
    assert comparison is not None
    assert comparison.precision == pytest.approx(1.0)
    assert comparison.recall == pytest.approx(1.0)
    assert comparison.f1 == pytest.approx(1.0)
    assert comparison.jaccard == pytest.approx(1.0)
    assert comparison.true_positive == 10
    assert comparison.candidate_area_ha == pytest.approx(0.001)


def test_derive_stream_candidates_compares_reference_vector(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    reference = _vector_reference(tmp_path / "reference.geojson")

    result = derive_stream_candidates(
        source,
        tmp_path / "streams",
        accumulation_threshold=4,
        reference_path=reference,
        reference_all_touched=True,
    )

    comparison = result.manifest.comparison
    assert comparison is not None
    assert comparison.reference_cells > 0
    assert comparison.true_positive > 0
    assert comparison.precision is not None
    assert comparison.recall is not None


def test_reference_misalignment_and_crs_are_rejected(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    shifted = _write_raster(
        tmp_path / "shifted.tif",
        np.ones((5, 5), dtype=np.uint8),
        transform=from_origin(1, 5, 1, 1),
        dtype="uint8",
        nodata=0,
    )
    with pytest.raises(StreamCandidateError, match="share the DEM grid"):
        derive_stream_candidates(
            source,
            tmp_path / "streams",
            reference_path=shifted,
        )

    wrong_crs = _vector_reference(tmp_path / "wrong_crs.geojson", crs="EPSG:4326")
    with pytest.raises(StreamCandidateError, match="does not match"):
        derive_stream_candidates(
            source,
            tmp_path / "streams",
            reference_path=wrong_crs,
        )


def test_empty_and_unreadable_reference_vectors(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    empty = tmp_path / "empty.geojson"
    gpd.GeoDataFrame({"id": []}, geometry=[], crs="EPSG:3005").to_file(
        empty,
        driver="GeoJSON",
    )

    result = derive_stream_candidates(
        source,
        tmp_path / "streams",
        accumulation_threshold=4,
        reference_path=empty,
    )
    assert result.manifest.comparison is not None
    assert result.manifest.comparison.reference_cells == 0
    assert result.manifest.comparison.recall is None
    assert any("no features" in warning for warning in result.manifest.warnings)

    bad = tmp_path / "bad.geojson"
    bad.write_text("not-geojson")
    with pytest.raises(StreamCandidateError, match="Unable to read"):
        derive_stream_candidates(
            source,
            tmp_path / "streams",
            reference_path=bad,
        )


def test_stream_candidate_errors_and_no_fill(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    with pytest.raises(StreamCandidateError, match="at least 1"):
        derive_stream_candidates(source, tmp_path / "streams", accumulation_threshold=0)

    geographic = _write_raster(
        tmp_path / "geographic.tif",
        _east_dem(),
        crs="EPSG:4326",
    )
    with pytest.raises(TerrainProcessingError, match="projected CRS"):
        derive_stream_candidates(geographic, tmp_path / "streams")

    no_fill = derive_stream_candidates(
        source,
        tmp_path / "streams_no_fill",
        accumulation_threshold=4,
        fill_depressions=False,
    )
    assert any("disabled" in warning for warning in no_fill.manifest.warnings)

    empty = derive_stream_candidates(
        source,
        tmp_path / "streams_empty",
        accumulation_threshold=999,
    )
    assert empty.manifest.qa["candidate_cells"] == 0
    assert any("No cells" in warning for warning in empty.manifest.warnings)


def test_compare_stream_candidates_metrics() -> None:
    candidate = np.array([[1, 1, 0], [0, 0, 0]], dtype=bool)
    reference = np.array([[1, 0, 0], [1, 0, 0]], dtype=bool)

    comparison = compare_stream_candidates(candidate, reference, pixel_area_m2=100.0)

    assert comparison.candidate_cells == 2
    assert comparison.reference_cells == 2
    assert comparison.true_positive == 1
    assert comparison.false_positive == 1
    assert comparison.false_negative == 1
    assert comparison.precision == pytest.approx(0.5)
    assert comparison.recall == pytest.approx(0.5)
    assert comparison.f1 == pytest.approx(0.5)
    assert comparison.jaccard == pytest.approx(1 / 3)
    assert comparison.candidate_area_ha == pytest.approx(0.02)
    assert comparison.to_dict()["candidate_cells"] == 2

    with pytest.raises(StreamCandidateError, match="must match"):
        compare_stream_candidates(candidate, np.ones((3, 3), dtype=bool))


def test_empty_masks_produce_none_ratios() -> None:
    comparison = compare_stream_candidates(
        np.zeros((2, 2), dtype=bool),
        np.zeros((2, 2), dtype=bool),
    )

    assert comparison.precision is None
    assert comparison.recall is None
    assert comparison.f1 is None
    assert comparison.jaccard is None


def test_result_to_dict(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "dem.tif", _east_dem())
    result = derive_stream_candidates(
        source,
        tmp_path / "streams",
        accumulation_threshold=4,
        generated_utc=GENERATED_UTC,
    )

    payload = result.to_dict()
    assert payload["stream_path"].endswith("stream_candidates.tif")
    assert payload["manifest"]["qa"]["candidate_cells"] == 10
