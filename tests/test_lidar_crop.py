"""Tests for the local LAZ bbox crop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.crop import LazCropError, crop_laz_by_bbox

RUNNER = CliRunner()


def _write_laz(path: Path) -> Path:
    laspy = pytest.importorskip("laspy")
    header = laspy.LasHeader(point_format=3, version="1.4")
    las = laspy.LasData(header)
    las.x = [0.0, 1.0, 2.0, 10.0]
    las.y = [0.0, 1.0, 2.0, 10.0]
    las.z = [0.0, 1.0, 2.0, 10.0]
    las.classification = [2, 2, 2, 1]
    las.write(path)
    return path


def test_crop_laz_by_bbox(tmp_path: Path) -> None:
    """Only in-bbox points are written and a manifest is produced."""
    source = _write_laz(tmp_path / "tile.laz")
    out = tmp_path / "crop.laz"
    result = crop_laz_by_bbox(source, out, (0.5, 0.5, 3.0, 3.0))
    assert result.input_point_count == 4
    assert result.output_point_count == 2
    assert out.exists()
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["schema_version"] == "femic.laz_crop.v1"
    assert manifest["output"]["point_count"] == 2

    laspy = pytest.importorskip("laspy")
    cropped = laspy.read(out)
    assert len(cropped) == 2
    assert sorted(float(value) for value in cropped.x) == [1.0, 2.0]


def test_crop_rejects_empty_bbox(tmp_path: Path) -> None:
    """A bbox with no points fails and does not write an output."""
    source = _write_laz(tmp_path / "tile.laz")
    out = tmp_path / "crop.laz"
    with pytest.raises(LazCropError, match="no points"):
        crop_laz_by_bbox(source, out, (100.0, 100.0, 101.0, 101.0))
    assert not out.exists()


def test_crop_refuses_existing_output(tmp_path: Path) -> None:
    """Existing output is refused unless overwrite is set."""
    source = _write_laz(tmp_path / "tile.laz")
    out = tmp_path / "crop.laz"
    crop_laz_by_bbox(source, out, (0.0, 0.0, 3.0, 3.0))
    with pytest.raises(LazCropError, match="output exists"):
        crop_laz_by_bbox(source, out, (0.0, 0.0, 3.0, 3.0))
    crop_laz_by_bbox(source, out, (0.0, 0.0, 3.0, 3.0), overwrite=True)


def test_crop_rejects_invalid_bbox(tmp_path: Path) -> None:
    """A reversed bbox is rejected."""
    source = _write_laz(tmp_path / "tile.laz")
    with pytest.raises(LazCropError, match="bbox"):
        crop_laz_by_bbox(source, tmp_path / "crop.laz", (10.0, 0.0, 0.0, 10.0))


def test_laz_crop_cli(tmp_path: Path) -> None:
    """The CLI writes a crop and prints JSON."""
    source = _write_laz(tmp_path / "tile.laz")
    out = tmp_path / "crop.laz"
    result = RUNNER.invoke(
        app,
        [
            "lidar",
            "crop",
            "--laz",
            str(source),
            "--bbox",
            "0.5,0.5,3,3",
            "--out",
            str(out),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output_point_count"] == 2
    assert out.exists()
