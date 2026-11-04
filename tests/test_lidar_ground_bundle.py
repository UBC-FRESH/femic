"""Contract tests for the optional ground-bundle reader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.ground_bundle import (
    GROUND_BUNDLE_SCHEMA_VERSION,
    GROUND_QA_SCHEMA_VERSION,
    GroundBundleError,
    read_ground_bundle,
)

RUNNER = CliRunner()
PARAMETER_SHA256 = "a" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_laz(path: Path, *, real: bool) -> int:
    if not real:
        path.write_bytes(b"not a real laz")
        return 100
    laspy = pytest.importorskip("laspy")
    header = laspy.LasHeader(point_format=3, version="1.4")
    las = laspy.LasData(header)
    las.x = [0.0, 1.0, 2.0]
    las.y = [0.0, 1.0, 2.0]
    las.z = [0.0, 1.0, 2.0]
    las.classification = [2, 2, 2]
    las.add_extra_dim(laspy.ExtraBytesParams(name="is_ground", type="uint8"))
    las.add_extra_dim(laspy.ExtraBytesParams(name="hag", type="float32"))
    las.add_extra_dim(laspy.ExtraBytesParams(name="is_low", type="uint8"))
    las.add_extra_dim(laspy.ExtraBytesParams(name="ref_class", type="uint8"))
    las.is_ground = [1, 1, 0]
    las.hag = [0.0, 0.0, 1.5]
    las.is_low = [1, 1, 0]
    las.ref_class = [2, 2, 2]
    las.write(path)
    return len(las)


def _write_bundle(
    root: Path,
    *,
    real_laz: bool = False,
    qa_mutate: Any = None,
    manifest_mutate: Any = None,
) -> Path:
    root.mkdir()
    point_count = _write_laz(root / "ground.laz", real=real_laz)
    qa: dict[str, object] = {
        "schema_version": GROUND_QA_SCHEMA_VERSION,
        "created_utc": "2026-11-04T00:00:00Z",
        "point_count": point_count,
        "ground_count": 2,
        "low_point_count": 2,
        "sor_removed": 0,
        "sor_removed_fraction": 0.0,
        "seed_count": 1,
        "iterations": 1,
        "tin_warning": None,
        "hag_percentiles_m": {"50": 0.0},
        "class_counts": {"2": point_count},
        "predicted_ground_by_class": {
            "2": {"points": point_count, "predicted_ground": 2}
        },
        "runtime_seconds": 0.1,
        "parameter_sha256": PARAMETER_SHA256,
        "ground_truth_used": False,
        "note": "fixture",
        "warnings": [],
    }
    if callable(qa_mutate):
        qa_mutate(qa)
    qa_path = root / "qa.json"
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    manifest: dict[str, object] = {
        "schema_version": GROUND_BUNDLE_SCHEMA_VERSION,
        "created_utc": "2026-11-04T00:00:00Z",
        "source": {
            "path": "tile.laz",
            "sha256": "b" * 64,
            "crs": "EPSG:3157",
            "vertical_datum": "CGVD2013",
            "point_count": point_count,
        },
        "output": {
            "path": "ground.laz",
            "sha256": _sha256(root / "ground.laz"),
            "point_count": point_count,
        },
        "parameters": {},
        "parameter_sha256": PARAMETER_SHA256,
        "method": {"name": "ptd-inspired-ground"},
        "qa": {"path": "qa.json", "sha256": _sha256(qa_path)},
        "warnings": [],
    }
    if callable(manifest_mutate):
        manifest_mutate(manifest)
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def test_read_ground_bundle_valid(tmp_path: Path) -> None:
    """A valid bundle returns metadata and optional point inspection."""
    root = _write_bundle(tmp_path / "bundle", real_laz=True)
    bundle = read_ground_bundle(root)
    assert bundle.point_count == 3
    assert bundle.ground_count == 2
    assert bundle.low_point_count == 2
    assert bundle.point_inspection is not None
    assert set(bundle.point_inspection.dimensions) >= {
        "is_ground",
        "hag",
        "is_low",
        "ref_class",
    }
    assert bundle.warnings == ()


def test_read_ground_bundle_without_inspection(tmp_path: Path) -> None:
    """The reader can validate a bundle without opening the LAZ."""
    root = _write_bundle(tmp_path / "bundle", real_laz=False)
    bundle = read_ground_bundle(root, inspect_points=False)
    assert bundle.point_inspection is None
    assert bundle.point_count == 100


def test_read_ground_bundle_rejects_missing_laz(tmp_path: Path) -> None:
    """A missing ground LAZ is an error."""
    root = _write_bundle(tmp_path / "bundle", real_laz=False)
    (root / "ground.laz").unlink()
    with pytest.raises(GroundBundleError, match="does not exist"):
        read_ground_bundle(root, inspect_points=False)


def test_read_ground_bundle_rejects_bad_schema(tmp_path: Path) -> None:
    """A wrong manifest schema version is rejected."""
    root = _write_bundle(
        tmp_path / "bundle",
        manifest_mutate=lambda payload: payload.__setitem__("schema_version", "bad"),
    )
    with pytest.raises(GroundBundleError, match="unsupported bundle schema"):
        read_ground_bundle(root, inspect_points=False)


def test_read_ground_bundle_rejects_hash_mismatch(tmp_path: Path) -> None:
    """A modified QA file breaks the manifest hash."""
    root = _write_bundle(tmp_path / "bundle", real_laz=False)
    qa_path = root / "qa.json"
    qa_path.write_text(qa_path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(GroundBundleError, match="QA SHA-256"):
        read_ground_bundle(root, inspect_points=False)


def test_read_ground_bundle_rejects_count_mismatch(tmp_path: Path) -> None:
    """A count mismatch between manifest and QA is rejected."""
    root = _write_bundle(
        tmp_path / "bundle",
        qa_mutate=lambda payload: payload.__setitem__("point_count", 999),
    )
    with pytest.raises(GroundBundleError, match="point counts differ"):
        read_ground_bundle(root, inspect_points=False)


def test_read_ground_bundle_rejects_missing_qa_field(tmp_path: Path) -> None:
    """A required QA field is mandatory."""
    root = _write_bundle(
        tmp_path / "bundle",
        qa_mutate=lambda payload: payload.pop("ground_count"),
    )
    with pytest.raises(GroundBundleError, match="ground_count"):
        read_ground_bundle(root, inspect_points=False)


def test_ground_bundle_cli(tmp_path: Path) -> None:
    """The CLI prints JSON for a valid bundle and exits non-zero for invalid input."""
    root = _write_bundle(tmp_path / "bundle", real_laz=False)
    result = RUNNER.invoke(
        app,
        ["lidar", "ground-bundle", str(root), "--no-inspect-points", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["point_count"] == 100
    assert payload["bundle_schema_version"] == GROUND_BUNDLE_SCHEMA_VERSION
    bad = RUNNER.invoke(
        app,
        ["lidar", "ground-bundle", str(root), "--no-inspect-points", "--json"],
    )
    assert bad.exit_code == 0
    (root / "manifest.json").write_text("{}\n", encoding="utf-8")
    invalid = RUNNER.invoke(
        app,
        ["lidar", "ground-bundle", str(root), "--no-inspect-points"],
    )
    assert invalid.exit_code == 1
