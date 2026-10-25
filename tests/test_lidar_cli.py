from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from typer.testing import CliRunner

from femic.cli import main as cli_main
from femic.lidar.catalog import LIDARBC_SOURCE, LidarTileSelection

GENERATED_UTC = "2026-10-25T00:00:00+00:00"


def _write_dem(path: Path, *, crs: str = "EPSG:3005") -> Path:
    values = np.tile(10.0 - np.arange(5, dtype=float), (5, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=5,
        height=5,
        count=1,
        dtype="float32",
        crs=crs,
        transform=from_origin(0, 5, 1, 1),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(values, 1)
    return path


def test_lidar_discover_writes_selection_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_discover(
        bbox: tuple[float, float, float, float],
        products: tuple[str, ...],
        *,
        generated_utc: str | None = None,
        **kwargs: object,
    ) -> LidarTileSelection:
        return LidarTileSelection(
            source=LIDARBC_SOURCE,
            generated_utc=generated_utc or GENERATED_UTC,
            aoi_bbox_epsg3005=tuple(bbox),
            products=tuple(products),
            tiles=(),
        )

    monkeypatch.setattr(cli_main, "discover_lidarbc_tiles", fake_discover)
    manifest = tmp_path / "selection.json"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "discover",
            "--bbox",
            "0,0,10,10",
            "--product",
            "dem",
            "--manifest-path",
            str(manifest),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "selection manifest written" in result.output
    assert "tiles: 0" in result.output
    assert manifest.is_file()
    payload = json.loads(manifest.read_text())
    assert payload["schema_version"] == "femic.lidar.selection.v1"
    assert payload["products"] == ["dem"]


def test_lidar_discover_instance_root_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_discover(
        bbox: tuple[float, float, float, float],
        products: tuple[str, ...],
        *,
        generated_utc: str | None = None,
        **kwargs: object,
    ) -> LidarTileSelection:
        return LidarTileSelection(
            source=LIDARBC_SOURCE,
            generated_utc=generated_utc or GENERATED_UTC,
            aoi_bbox_epsg3005=tuple(bbox),
            products=tuple(products),
            tiles=(),
        )

    monkeypatch.setattr(cli_main, "discover_lidarbc_tiles", fake_discover)
    instance = tmp_path / "instance"
    instance.mkdir()

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "discover",
            "--bbox",
            "0,0,10,10",
            "--instance-root",
            str(instance),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (instance / "metadata/lidar/lidarbc_selection.json").is_file()


def test_lidar_discover_rejects_bad_bbox() -> None:
    result = CliRunner().invoke(
        cli_main.app,
        ["lidar", "discover", "--bbox", "0,0,0,10"],
    )

    assert result.exit_code == 1
    assert "discovery error" in result.output


def test_lidar_terrain_builds_products(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif")
    output = tmp_path / "terrain"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "terrain",
            "--dem",
            str(dem),
            "--output-dir",
            str(output),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "terrain products built" in result.output
    assert "products: 1" in result.output
    assert (output / "slope_percent.tif").is_file()
    assert (output / "terrain_qa.json").is_file()
    assert (output / "terrain_qa.csv").is_file()


def test_lidar_terrain_instance_root_default(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif")
    instance = tmp_path / "instance"
    instance.mkdir()

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "terrain",
            "--dem",
            str(dem),
            "--instance-root",
            str(instance),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (instance / "data/lidar/terrain/slope_percent.tif").is_file()


def test_lidar_terrain_reports_unsupported_product(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "terrain",
            "--dem",
            str(dem),
            "--output-dir",
            str(tmp_path / "terrain"),
            "--product",
            "aspect",
        ],
    )

    assert result.exit_code == 1
    assert "terrain error" in result.output


def test_lidar_streams_builds_candidates(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif")
    output = tmp_path / "streams"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "streams",
            "--dem",
            str(dem),
            "--output-dir",
            str(output),
            "--accumulation-threshold",
            "4",
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert "stream candidates built" in result.output
    assert "candidate_cells: 10" in result.output
    assert (output / "stream_candidates.tif").is_file()
    assert (output / "stream_candidates_manifest.json").is_file()
    assert (output / "stream_candidates_review.md").is_file()


def test_lidar_streams_instance_root_default(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif")
    instance = tmp_path / "instance"
    instance.mkdir()

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "streams",
            "--dem",
            str(dem),
            "--instance-root",
            str(instance),
            "--accumulation-threshold",
            "4",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (instance / "data/lidar/streams/stream_candidates.tif").is_file()


def test_lidar_streams_reports_errors(tmp_path: Path) -> None:
    dem = _write_dem(tmp_path / "dem.tif", crs="EPSG:4326")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "streams",
            "--dem",
            str(dem),
            "--output-dir",
            str(tmp_path / "streams"),
        ],
    )

    assert result.exit_code == 1
    assert "stream-candidate error" in result.output


def test_lidar_materialize_instance_root_default_plan(tmp_path: Path) -> None:
    instance = tmp_path / "instance"
    instance.mkdir()
    selection = Path(__file__).parent / "fixtures/lidar/selection_manifest.json"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "materialize",
            "--selection-manifest",
            str(selection),
            "--instance-root",
            str(instance),
            "--plan-only",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (instance / "data/lidar/materialization.json").is_file()


def test_lidar_bundle_instance_root_default(tmp_path: Path) -> None:
    instance = tmp_path / "instance"
    instance.mkdir()
    fixtures = Path(__file__).parent / "fixtures/lidar"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "lidar",
            "bundle",
            "--selection-manifest",
            str(fixtures / "selection_manifest.json"),
            "--product-plan",
            str(fixtures / "product_plan.json"),
            "--instance-root",
            str(instance),
            "--generated-utc",
            GENERATED_UTC,
        ],
    )

    assert result.exit_code == 0, result.output
    assert (instance / "data/lidar/products/manifest.json").is_file()


def test_lidar_help_lists_full_workflow() -> None:
    result = CliRunner().invoke(cli_main.app, ["lidar", "--help"])

    assert result.exit_code == 0
    for command in (
        "discover",
        "materialize",
        "materialization-status",
        "terrain",
        "streams",
        "bundle",
        "inspect",
    ):
        assert command in result.stdout
