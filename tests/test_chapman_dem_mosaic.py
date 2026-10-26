from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import rasterio  # type: ignore[import-untyped]
from pyproj import CRS
from rasterio.transform import from_origin  # type: ignore[import-untyped]


def _mosaic_module() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_chapman_dem_mosaic.py"
    )
    spec = importlib.util.spec_from_file_location("build_chapman_dem_mosaic", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the DEM mosaic script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mosaic = _mosaic_module()


def _tile(path: Path, x0: float, value: float) -> Path:
    data = np.full((10, 10), value, dtype="float32")
    data[0, 0] = -9999.0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=10,
        height=10,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(6653),
        transform=from_origin(x0, 20, 1, 1),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data, 1)
    return path


def _selection(path: Path, tiles: list[Path]) -> Path:
    path.write_text(
        json.dumps(
            {
                "tiles": [
                    {
                        "product": "dem",
                        "tile_id": f"t{index}",
                        "filename": tile.name,
                        "download_url": str(tile),
                    }
                    for index, tile in enumerate(tiles)
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_build_mosaic_preserves_compound_crs(tmp_path: Path) -> None:
    first = _tile(tmp_path / "a.tif", 0, 10.0)
    second = _tile(tmp_path / "b.tif", 10, 20.0)
    selection = _selection(tmp_path / "selection.json", [first, second])
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"watershed": {"area_ha": 0.03}}), encoding="utf-8")
    output = tmp_path / "mosaic.tif"
    manifest_path = tmp_path / "manifest.json"

    result = mosaic.build_mosaic(
        selection,
        output,
        manifest_path=manifest_path,
        domain_audit_path=audit,
        watershed_path=tmp_path / "missing.geojson",
        generated_utc="2026-10-26T00:00:00+00:00",
    )

    assert output.is_file()
    assert manifest_path.is_file()
    assert result["crs_epsg"] == 3157
    assert result["horizontal_epsg"] == 3157
    assert result["vertical_epsg"] == "6647"
    assert result["vertical_status"] == "resolved"
    assert result["compound_tile_count"] == 2
    assert result["two_d_tile_count"] == 0
    assert result["source_tile_count"] == 2
    assert result["valid_pixels"] == 198
    assert result["nodata_pixels"] == 2
    assert result["valid_area_ha"] == pytest.approx(0.0198)
    assert result["edge_gap_ha"] == pytest.approx(0.0102)
    assert result["nodata"] == -32767.0
    with rasterio.open(output) as dataset:
        assert dataset.crs.to_epsg() == 3157
        assert dataset.res == (1.0, 1.0)
        assert dataset.nodata == pytest.approx(-32767.0)


def test_build_mosaic_rejects_no_dem(tmp_path: Path) -> None:
    selection = tmp_path / "selection.json"
    selection.write_text(
        json.dumps({"tiles": [{"product": "dsm", "download_url": "x"}]}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="No DEM tiles"):
        mosaic.build_mosaic(selection, tmp_path / "out.tif")


def test_cli_builds_mosaic(tmp_path: Path) -> None:
    first = _tile(tmp_path / "a.tif", 0, 10.0)
    selection = _selection(tmp_path / "selection.json", [first])
    output = tmp_path / "out.tif"
    manifest = tmp_path / "manifest.json"
    code = mosaic.main(
        [
            "--selection",
            str(selection),
            "--output",
            str(output),
            "--manifest",
            str(manifest),
            "--watershed",
            str(tmp_path / "missing.geojson"),
            "--generated-utc",
            "2026-10-26T00:00:00+00:00",
        ]
    )
    assert code == 0
    assert output.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["schema_version"] == mosaic.SCHEMA_VERSION


def test_mixed_vertical_metadata_is_explicit(tmp_path: Path) -> None:
    compound = _tile(tmp_path / "a.tif", 0, 10.0)
    two_d = tmp_path / "b.tif"
    data = np.full((10, 10), 20.0, dtype="float32")
    with rasterio.open(
        two_d,
        "w",
        driver="GTiff",
        width=10,
        height=10,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(3157),
        transform=from_origin(10, 20, 1, 1),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(data, 1)
    selection = _selection(tmp_path / "selection.json", [compound, two_d])

    result = mosaic.build_mosaic(
        selection,
        tmp_path / "mixed.tif",
        manifest_path=tmp_path / "mixed.json",
        watershed_path=tmp_path / "missing.geojson",
        generated_utc="2026-10-26T00:00:00+00:00",
    )
    assert result["vertical_status"] == "mixed_unresolved"
    assert result["vertical_epsg"] is None
    assert result["compound_tile_count"] == 1
    assert result["two_d_tile_count"] == 1


def test_mosaic_clips_to_watershed(tmp_path: Path) -> None:
    tile = _tile(tmp_path / "a.tif", 0, 10.0)
    selection = _selection(tmp_path / "selection.json", [tile])
    watershed = tmp_path / "watershed.geojson"
    watershed.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[0, 10], [5, 10], [5, 20], [0, 20], [0, 10]]
                            ],
                        },
                        "properties": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = mosaic.build_mosaic(
        selection,
        tmp_path / "clipped.tif",
        manifest_path=tmp_path / "manifest.json",
        watershed_path=watershed,
        watershed_crs="EPSG:3157",
        generated_utc="2026-10-26T00:00:00+00:00",
    )
    assert result["clipped_to_watershed"] is True
    assert result["valid_pixels"] == 49
    assert result["valid_area_ha"] == pytest.approx(0.0049)
