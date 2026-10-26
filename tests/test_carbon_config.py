"""Tests for instance-level carbon configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from femic.carbon import (
    load_carbon_instance_config,
    to_export_config,
)

CONFIG = Path(__file__).resolve().parents[1] / "config" / "carbon"


def test_tsa24_defaults_load() -> None:
    """The TSA24 default config resolves the crosswalks and pinned defaults."""
    config = load_carbon_instance_config(CONFIG / "tsa24.yaml")
    assert config.tsa_codes == ("24",)
    assert config.admin_boundary == "British Columbia"
    assert config.eco_boundary == "Montane Cordillera"
    assert config.cbm_defaults_version == "1.2.9300.391"
    assert config.cbm_defaults_sha256 is not None
    assert config.review_status == "draft"
    export = to_export_config(config)
    assert export.species_map["SW"].cbm_species == "White spruce"
    assert export.fallback_softwood == "Unspecified softwood species"


def test_mkrf_defaults_load() -> None:
    """The MKRF config uses the same contract with a Pacific boundary."""
    config = load_carbon_instance_config(CONFIG / "mkrf.yaml")
    assert config.tsa_codes == ("mkrf",)
    assert config.eco_boundary == "Pacific Maritime"
    export = to_export_config(config)
    assert export.crosswalk_dir == CONFIG


def _write_config(payload: dict[str, object], tmp_path: Path, name: str) -> Path:
    """Write a temp config with absolute crosswalk paths."""
    carbon = payload["carbon"]
    assert isinstance(carbon, dict)
    for key, file_name in (
        ("species_map", "species_map.bc.csv"),
        ("eco_boundary_map", "eco_boundary.bc.csv"),
        ("disturbance_map", "disturbance_map.bc.csv"),
        ("land_class_map", "land_class.bc.csv"),
    ):
        carbon[key] = str(CONFIG / file_name)
    path = tmp_path / name
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


def test_boundary_mismatch_fails(tmp_path: Path) -> None:
    """A TSA row that disagrees with the configured boundary is rejected."""
    payload = yaml.safe_load((CONFIG / "tsa24.yaml").read_text(encoding="utf-8"))
    payload["carbon"]["eco_boundary"] = "Pacific Maritime"
    path = _write_config(payload, tmp_path, "bad.yaml")
    with pytest.raises(ValueError, match="Pacific Maritime"):
        load_carbon_instance_config(path)


def test_unknown_tsa_fails(tmp_path: Path) -> None:
    """A TSA code without an eco-boundary row is rejected."""
    payload = yaml.safe_load((CONFIG / "tsa24.yaml").read_text(encoding="utf-8"))
    payload["carbon"]["tsa_codes"] = ["zz"]
    path = _write_config(payload, tmp_path, "bad.yaml")
    with pytest.raises(ValueError, match="no eco-boundary row"):
        load_carbon_instance_config(path)


def test_missing_schema_version_fails(tmp_path: Path) -> None:
    """The config requires the documented schema version."""
    payload = yaml.safe_load((CONFIG / "tsa24.yaml").read_text(encoding="utf-8"))
    payload["carbon"]["schema_version"] = "9.9"
    path = _write_config(payload, tmp_path, "bad.yaml")
    with pytest.raises(ValueError, match="schema_version"):
        load_carbon_instance_config(path)


def test_optional_validation_totals_parse(tmp_path: Path) -> None:
    """Optional fixture totals are available to the validate command."""
    payload = yaml.safe_load((CONFIG / "tsa24.yaml").read_text(encoding="utf-8"))
    payload["carbon"]["validation"] = {
        "expected_area_ha": 5.0,
        "expected_track_count": 1,
    }
    path = _write_config(payload, tmp_path, "fixture.yaml")
    config = load_carbon_instance_config(path)
    assert config.expected_area_ha == 5.0
    assert config.expected_track_count == 1
