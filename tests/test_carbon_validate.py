"""Validation and fixture tests for static carbon packages."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from femic.carbon import CarbonValidationError, validate_carbon_package
from femic.cli.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "carbon" / "tsa24_minimal"


def _copy_fixture(tmp_path: Path) -> Path:
    """Copy the public-safe fixture into a writable directory."""
    target = tmp_path / "package"
    shutil.copytree(FIXTURE, target)
    return target


def _rewrite_table(package: Path, name: str, frame: pd.DataFrame) -> None:
    """Rewrite one table and keep the manifest hash and fingerprint coherent."""
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    file_name = manifest["table_files"][name]
    path = package / file_name
    frame.to_csv(path, index=False)
    manifest["table_hashes"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if "track_name" in frame:
        manifest["totals"]["track_count"] = int(frame["track_name"].nunique())
    if "area_ha" in frame:
        manifest["totals"]["inventory_area_ha"] = float(frame["area_ha"].sum())
    if name == "yield":
        manifest["totals"]["yield_rows"] = int(frame.shape[0])
    manifest["package_id"] = f"femic-carbon-fixture-{_fingerprint(manifest)[:12]}"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def _fingerprint(manifest: dict[str, object]) -> str:
    """Mirror the producer fingerprint for rewritten fixtures."""
    digest = hashlib.sha256()
    table_hashes = manifest["table_hashes"]
    assert isinstance(table_hashes, dict)
    for name in sorted(table_hashes):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(table_hashes[name]).encode("ascii"))
        digest.update(b"\0")
    sources = manifest["sources"]
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source, dict)
        digest.update(str(source.get("path", "")).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(source.get("sha256", "")).encode("ascii"))
        digest.update(b"\0")
    boundaries = manifest["boundaries"]
    assert isinstance(boundaries, dict)
    digest.update(str(boundaries.get("admin", "")).encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(boundaries.get("eco", "")).encode("utf-8"))
    digest.update(b"\0")
    defaults = manifest["cbm_defaults"]
    assert isinstance(defaults, dict)
    digest.update(str(defaults.get("sha256", "")).encode("ascii"))
    return digest.hexdigest()


def test_public_tsa24_fixture_validates() -> None:
    """The committed TSA24 fixture satisfies the producer contract."""
    result = validate_carbon_package(FIXTURE)
    assert result.track_count == 1
    assert result.inventory_area_ha == pytest.approx(5.0)
    assert result.yield_rows == 31


def test_expected_area_mismatch_fails() -> None:
    """The validator rejects an expected-area mismatch."""
    with pytest.raises(CarbonValidationError, match="expected"):
        validate_carbon_package(FIXTURE, expected_area_ha=6.0)


def test_expected_track_mismatch_fails() -> None:
    """The validator rejects an expected-track mismatch."""
    with pytest.raises(CarbonValidationError, match="track count"):
        validate_carbon_package(FIXTURE, expected_track_count=2)


def test_manifest_package_id_mismatch_fails(tmp_path: Path) -> None:
    """A package id that does not carry the manifest fingerprint is rejected."""
    package = _copy_fixture(tmp_path)
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_id"] = "femic-carbon-fixture-000000000000"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CarbonValidationError, match="fingerprint"):
        validate_carbon_package(package)


def test_manifest_hash_mismatch_fails(tmp_path: Path) -> None:
    """The validator rejects a changed table without a manifest update."""
    package = _copy_fixture(tmp_path)
    inventory_path = package / "inventory.csv"
    inventory = pd.read_csv(inventory_path, dtype=str)
    inventory.loc[0, "area_ha"] = "4.0"
    inventory.to_csv(inventory_path, index=False)
    with pytest.raises(CarbonValidationError, match="hash mismatch"):
        validate_carbon_package(package)


def test_missing_track_classifier_fails(tmp_path: Path) -> None:
    """Every inventory track must be present in the track classifier."""
    package = _copy_fixture(tmp_path)
    classifiers = pd.read_csv(package / "classifiers.csv", dtype=str)
    classifiers = classifiers.loc[classifiers["classifier"] != "track"]
    _rewrite_table(package, "classifiers", classifiers)
    with pytest.raises(CarbonValidationError, match="track classifier mismatch"):
        validate_carbon_package(package)


def test_missing_leading_species_classifier_fails(tmp_path: Path) -> None:
    """Every leading species must be in the species classifier."""
    package = _copy_fixture(tmp_path)
    classifiers = pd.read_csv(package / "classifiers.csv", dtype=str)
    classifiers = classifiers.loc[classifiers["classifier"] != "species"]
    _rewrite_table(package, "classifiers", classifiers)
    with pytest.raises(CarbonValidationError, match="leading species"):
        validate_carbon_package(package)


def test_missing_table_file_fails(tmp_path: Path) -> None:
    """A package with a missing table is rejected."""
    package = _copy_fixture(tmp_path)
    (package / "yield.csv").unlink()
    with pytest.raises(CarbonValidationError, match="missing"):
        validate_carbon_package(package)


def test_cli_validate_succeeds() -> None:
    """The CLI reports a valid fixture with zero exit status."""
    result = CliRunner().invoke(app, ["carbon", "validate", str(FIXTURE)])
    assert result.exit_code == 0
    assert "carbon package valid" in result.output
    assert "tracks=1" in result.output


def test_cli_validate_fails_on_area() -> None:
    """The CLI maps a validation failure to a non-zero exit status."""
    result = CliRunner().invoke(
        app,
        ["carbon", "validate", str(FIXTURE), "--expect-area-ha", "6"],
    )
    assert result.exit_code == 1
    assert "does not match expected" in result.output
