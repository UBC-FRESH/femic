"""Tests for the optional ground-bundle block summary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.ground_bundle import (
    GROUND_BUNDLE_SCHEMA_VERSION,
    GROUND_QA_SCHEMA_VERSION,
)
from femic.lidar.ground_summary import (
    GroundSummaryError,
    _horizontal_crs,
    summarize_ground_bundle,
)

RUNNER = CliRunner()
PARAMETER_SHA256 = "a" * 64
CRS = "EPSG:3157"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_bundle(root: Path) -> Path:
    laspy = pytest.importorskip("laspy")
    from pyproj import CRS as PyprojCRS

    root.mkdir()
    header = laspy.LasHeader(point_format=3, version="1.4")
    header.add_crs(PyprojCRS.from_user_input(CRS))
    las = laspy.LasData(header)
    las.x = [0.0, 5.0, 0.0, 10.0, 15.0, 10.0]
    las.y = [0.0, 0.0, 5.0, 0.0, 0.0, 5.0]
    las.z = [0.0, 0.0, 0.0, 5.0, 5.0, 5.0]
    las.classification = [2, 2, 2, 1, 1, 1]
    las.add_extra_dim(laspy.ExtraBytesParams(name="is_ground", type=np.uint8))
    las.add_extra_dim(laspy.ExtraBytesParams(name="hag", type=np.float32))
    las.add_extra_dim(laspy.ExtraBytesParams(name="is_low", type=np.uint8))
    las.add_extra_dim(laspy.ExtraBytesParams(name="ref_class", type=np.uint8))
    las.is_ground = [1, 1, 1, 0, 0, 0]
    las.hag = [0.0, 0.0, 0.0, 5.0, 5.0, 5.0]
    las.is_low = [1, 1, 1, 0, 0, 0]
    las.ref_class = [2, 2, 2, 1, 1, 1]
    ground_path = root / "ground.laz"
    las.write(ground_path)

    qa: dict[str, object] = {
        "schema_version": GROUND_QA_SCHEMA_VERSION,
        "point_count": 6,
        "ground_count": 3,
        "low_point_count": 3,
        "sor_removed": 0,
        "sor_removed_fraction": 0.0,
        "seed_count": 1,
        "iterations": 1,
        "tin_warning": None,
        "hag_percentiles_m": {"50": 2.5},
        "class_counts": {"1": 3, "2": 3},
        "predicted_ground_by_class": {},
        "runtime_seconds": 0.1,
        "parameter_sha256": PARAMETER_SHA256,
        "ground_truth_used": False,
        "note": "fixture",
        "warnings": [],
    }
    qa_path = root / "qa.json"
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    manifest: dict[str, object] = {
        "schema_version": GROUND_BUNDLE_SCHEMA_VERSION,
        "source": {
            "path": "tile.laz",
            "sha256": "b" * 64,
            "crs": CRS,
            "vertical_datum": "CGVD2013",
            "point_count": 6,
        },
        "output": {
            "path": "ground.laz",
            "sha256": _sha256(ground_path),
            "point_count": 6,
        },
        "parameter_sha256": PARAMETER_SHA256,
        "qa": {"path": "qa.json", "sha256": _sha256(qa_path)},
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _write_polygons(path: Path, *, crs: str = CRS, id_field: str = "block_id") -> Path:
    frame = gpd.GeoDataFrame(
        {id_field: ["B1"], "geometry": [box(-1.0, -1.0, 16.0, 6.0)]},
        crs=crs,
    )
    frame.to_file(path, driver="GeoJSON")
    return path


def test_horizontal_crs_strips_vertical_component() -> None:
    """A compound CRS compares equal to its horizontal component."""
    from pyproj import CRS as PyprojCRS

    assert _horizontal_crs("EPSG:3157+5703").equals(PyprojCRS.from_epsg(3157))


def test_summarize_ground_bundle(tmp_path: Path) -> None:
    """A matching polygon gets counts and HAG statistics."""
    bundle = _write_bundle(tmp_path / "bundle")
    polygons = _write_polygons(tmp_path / "blocks.geojson")
    result = summarize_ground_bundle(
        bundle,
        polygons,
        tmp_path / "summary.csv",
        id_field="block_id",
    )
    assert result.csv_path.exists()
    assert result.manifest_path.exists()
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.polygon_id == "B1"
    assert row.point_count == 6
    assert row.ground_count == 3
    assert row.ground_fraction == 0.5
    assert row.low_count == 3
    assert row.low_fraction == 0.5
    assert row.hag_mean == 2.5
    assert row.hag_p50 == 2.5
    assert row.hag_p95 == 5.0
    assert row.hag_max == 5.0
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["schema_version"] == "femic.ground-summary.v1"
    assert manifest["row_count"] == 1


def test_summarize_rejects_crs_mismatch(tmp_path: Path) -> None:
    """A polygon CRS that differs from the point CRS is rejected."""
    bundle = _write_bundle(tmp_path / "bundle")
    polygons = _write_polygons(tmp_path / "blocks.geojson", crs="EPSG:4326")
    with pytest.raises(GroundSummaryError, match="CRS differ"):
        summarize_ground_bundle(
            bundle,
            polygons,
            tmp_path / "summary.csv",
            id_field="block_id",
        )


def test_summarize_rejects_missing_id_field(tmp_path: Path) -> None:
    """A missing identifier field is rejected."""
    bundle = _write_bundle(tmp_path / "bundle")
    polygons = _write_polygons(tmp_path / "blocks.geojson")
    with pytest.raises(GroundSummaryError, match="id field"):
        summarize_ground_bundle(
            bundle,
            polygons,
            tmp_path / "summary.csv",
            id_field="missing",
        )


def test_summarize_refuses_existing_output(tmp_path: Path) -> None:
    """Existing output is not overwritten unless requested."""
    bundle = _write_bundle(tmp_path / "bundle")
    polygons = _write_polygons(tmp_path / "blocks.geojson")
    out = tmp_path / "summary.csv"
    summarize_ground_bundle(bundle, polygons, out, id_field="block_id")
    with pytest.raises(GroundSummaryError, match="output exists"):
        summarize_ground_bundle(bundle, polygons, out, id_field="block_id")
    summarize_ground_bundle(
        bundle,
        polygons,
        out,
        id_field="block_id",
        overwrite=True,
    )


def test_ground_summary_cli(tmp_path: Path) -> None:
    """The CLI writes a summary and prints JSON."""
    bundle = _write_bundle(tmp_path / "bundle")
    polygons = _write_polygons(tmp_path / "blocks.geojson")
    out = tmp_path / "summary.csv"
    result = RUNNER.invoke(
        app,
        [
            "lidar",
            "ground-summary",
            str(bundle),
            "--polygons",
            str(polygons),
            "--out",
            str(out),
            "--id-field",
            "block_id",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["row_count"] == 1
    assert payload["rows"][0]["ground_fraction"] == 0.5
