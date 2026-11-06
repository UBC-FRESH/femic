"""Contract tests for the optional sidecar ground-bundle adapter."""

from __future__ import annotations

import json
from pathlib import Path

import laspy
import numpy as np
import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.ground_adapter import (
    GroundAdapterParameters,
    write_ground_bundle,
)

RUNNER = CliRunner()


def _write_laz(
    path: Path,
    points: np.ndarray,
    classes: np.ndarray,
) -> None:
    """Write a small LAS/LAZ fixture.

    Parameters
    ----------
    path : Path
        Destination file.
    points : ndarray
        Point coordinates with shape ``(N, 3)``.
    classes : ndarray
        LAS classification values with shape ``(N,)``.
    """
    header = laspy.LasHeader(point_format=3, version="1.4")
    las = laspy.LasData(header)
    las.x = points[:, 0]
    las.y = points[:, 1]
    las.z = points[:, 2]
    las.classification = classes.astype(np.uint8)
    las.write(path)


def _ground_fixture(path: Path) -> None:
    """Write a flat ground plane with one above-ground point.

    Parameters
    ----------
    path : Path
        Destination file.
    """
    axis = np.linspace(0.0, 9.0, 10)
    xx, yy = np.meshgrid(axis, axis)
    ground = np.column_stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)])
    points = np.vstack([ground, np.array([[5.0, 5.0, 5.0]])])
    classes = np.concatenate(
        [np.full(ground.shape[0], 2, dtype=np.uint8), np.array([1], dtype=np.uint8)]
    )
    _write_laz(path, points, classes)


def test_parameters_hash_is_canonical() -> None:
    """The parameter hash is stable and changes with the parameters."""
    first = GroundAdapterParameters()
    second = GroundAdapterParameters()
    different = GroundAdapterParameters(max_angle_deg=20.0)
    assert first.sha256() == second.sha256()
    assert first.sha256() != different.sha256()
    assert len(first.sha256()) == 64


def test_write_ground_bundle_creates_bundle(tmp_path: Path) -> None:
    """The writer produces the LAZ, manifest, QA, and aligned extra dimensions."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    out = tmp_path / "bundle"
    result = write_ground_bundle(
        source,
        out,
        crs="EPSG:3157",
        vertical_datum="CGVD2013",
    )

    assert result.ground_laz.exists()
    assert result.manifest_path.exists()
    assert result.qa_path.exists()
    assert result.point_count == 101
    assert result.ground_count >= 100
    assert result.low_point_count >= 0

    manifest = json.loads(result.manifest_path.read_text())
    qa = json.loads(result.qa_path.read_text())
    assert manifest["schema_version"] == "femic.ground-bundle.v1"
    assert qa["schema_version"] == "femic.ground-qa.v1"
    assert manifest["source"]["crs"] == "EPSG:3157"
    assert manifest["source"]["vertical_datum"] == "CGVD2013"
    assert len(manifest["source"]["sha256"]) == 64
    assert len(manifest["output"]["sha256"]) == 64
    assert manifest["parameter_sha256"] == GroundAdapterParameters().sha256()
    assert qa["ground_truth_used"] is False
    assert qa["point_count"] == 101

    written = laspy.read(result.ground_laz)
    assert len(written) == 101
    assert np.asarray(written.is_ground).shape == (101,)
    assert np.asarray(written.hag).shape == (101,)
    assert np.asarray(written.is_low).shape == (101,)
    assert np.asarray(written.ref_class).shape == (101,)
    assert int(np.count_nonzero(np.asarray(written.is_ground))) == result.ground_count


def test_write_ground_bundle_warns_for_missing_metadata(tmp_path: Path) -> None:
    """Missing CRS and vertical datum are warnings, not crashes."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    result = write_ground_bundle(source, tmp_path / "bundle")
    joined = " ".join(result.warnings)
    assert "CRS is missing" in joined
    assert "vertical datum is missing" in joined


def test_write_ground_bundle_refuses_existing_output(tmp_path: Path) -> None:
    """An existing bundle is not overwritten unless requested."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    out = tmp_path / "bundle"
    write_ground_bundle(source, out, crs="EPSG:3157", vertical_datum="CGVD2013")
    with pytest.raises(FileExistsError):
        write_ground_bundle(source, out, crs="EPSG:3157", vertical_datum="CGVD2013")
    write_ground_bundle(
        source,
        out,
        crs="EPSG:3157",
        vertical_datum="CGVD2013",
        overwrite=True,
    )


def test_write_ground_bundle_rejects_empty_cloud(tmp_path: Path) -> None:
    """An empty input cloud fails clearly."""
    source = tmp_path / "empty.laz"
    _write_laz(
        source,
        np.zeros((0, 3), dtype=np.float64),
        np.zeros(0, dtype=np.uint8),
    )
    with pytest.raises(ValueError, match="no points"):
        write_ground_bundle(source, tmp_path / "bundle")


def test_ground_adapter_cli(tmp_path: Path) -> None:
    """The CLI writes a bundle through the same contract."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    out = tmp_path / "bundle"
    result = RUNNER.invoke(
        app,
        [
            "lidar",
            "ground-bundle-build",
            str(source),
            str(out),
            "--crs",
            "EPSG:3157",
            "--vertical-datum",
            "CGVD2013",
        ],
    )
    assert result.exit_code == 0
    assert (out / "ground.laz").exists()
    assert (out / "manifest.json").exists()
    assert (out / "qa.json").exists()


def test_ground_adapter_cli_json(tmp_path: Path) -> None:
    """The CLI JSON result includes the written paths and counts."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    out = tmp_path / "bundle"
    result = RUNNER.invoke(
        app,
        [
            "lidar",
            "ground-bundle-build",
            str(source),
            str(out),
            "--crs",
            "EPSG:3157",
            "--vertical-datum",
            "CGVD2013",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["ground_laz"].endswith("ground.laz")
    assert payload["manifest_path"].endswith("manifest.json")
    assert payload["qa_path"].endswith("qa.json")
    assert payload["point_count"] > 0
    assert payload["ground_count"] >= 0
    assert payload["low_point_count"] >= 0


def test_near_surface_parameters_are_recorded(tmp_path: Path) -> None:
    """The opt-in near-surface pass is recorded without changing the default."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    strict = write_ground_bundle(
        source,
        tmp_path / "strict",
        crs="EPSG:3157",
        vertical_datum="CGVD2013",
    )
    expanded = write_ground_bundle(
        source,
        tmp_path / "expanded",
        crs="EPSG:3157",
        vertical_datum="CGVD2013",
        parameters=GroundAdapterParameters(
            include_near_surface=True,
            near_surface_tolerance_m=0.2,
        ),
    )
    strict_manifest = json.loads(strict.manifest_path.read_text())
    expanded_manifest = json.loads(expanded.manifest_path.read_text())
    expanded_qa = json.loads(expanded.qa_path.read_text())
    assert strict_manifest["parameters"]["include_near_surface"] is False
    assert expanded_manifest["parameters"]["include_near_surface"] is True
    assert expanded_manifest["parameters"]["near_surface_tolerance_m"] == 0.2
    assert expanded.ground_count >= strict.ground_count
    assert expanded_qa["include_near_surface"] is True
    assert expanded_qa["near_surface_tolerance_m"] == 0.2
    assert expanded_qa["near_surface_added"] >= 0
    assert expanded_qa["strict_ground_count"] <= expanded_qa["ground_count"]


def test_ground_adapter_cli_near_surface(tmp_path: Path) -> None:
    """The CLI exposes the opt-in near-surface pass."""
    source = tmp_path / "tile.laz"
    _ground_fixture(source)
    out = tmp_path / "bundle"
    result = RUNNER.invoke(
        app,
        [
            "lidar",
            "ground-bundle-build",
            str(source),
            str(out),
            "--crs",
            "EPSG:3157",
            "--vertical-datum",
            "CGVD2013",
            "--include-near-surface",
            "--near-surface-tolerance-m",
            "0.2",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["parameters"]["include_near_surface"] is True
    assert manifest["parameters"]["near_surface_tolerance_m"] == 0.2
