"""Structural checks for the carbon-domain crosswalk config."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[1] / "config" / "carbon"
CBM_ECO_BOUNDARIES = {
    "Atlantic Maritime",
    "Boreal Cordillera",
    "Boreal Plains",
    "Boreal Shield East",
    "Boreal Shield West",
    "Hudson Plains",
    "Mixedwood Plains",
    "Montane Cordillera",
    "Pacific Maritime",
    "Semiarid Prairies",
    "Subhumid Prairies",
    "Taiga Cordillera",
    "Taiga Plains",
    "Taiga Shield East",
    "Taiga Shield West",
}


def _rows(name: str) -> list[dict[str, str]]:
    """Read one crosswalk CSV as dictionaries."""
    with (CONFIG / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_species_map_is_typed_and_unique() -> None:
    """Every species row has a type, a confidence, and a unique BC code."""
    rows = _rows("species_map.bc.csv")
    assert rows
    assert len({row["bc_species"] for row in rows}) == len(rows)
    for row in rows:
        assert row["bc_species"]
        assert row["cbm_species"]
        assert row["wood_type"] in {"softwood", "hardwood"}
        assert row["confidence"] in {"high", "medium", "low"}
    assert {row["bc_species"] for row in rows} >= {"UNK_SW", "UNK_HW"}


def test_eco_boundary_map_uses_cbm_names() -> None:
    """Every TSA row names a CBM eco boundary and the BC admin boundary."""
    rows = _rows("eco_boundary.bc.csv")
    assert rows
    assert len({row["tsa_code"] for row in rows}) == len(rows)
    for row in rows:
        assert row["admin_boundary"] == "British Columbia"
        assert row["eco_boundary"] in CBM_ECO_BOUNDARIES
        assert row["confidence"] in {"high", "medium", "low"}


def test_disturbance_map_is_typed() -> None:
    """Every treatment row has a boolean removal flag and non-negative ages."""
    rows = _rows("disturbance_map.bc.csv")
    assert rows
    assert len({row["treatment_pattern"] for row in rows}) == len(rows)
    for row in rows:
        assert row["default_dist_type"]
        assert row["removes_biomass"] in {"true", "false"}
        assert int(row["transition_reset_age"]) >= 0
        assert int(row["regen_delay"]) >= 0
        assert row["confidence"] in {"high", "medium", "low"}


def test_land_class_map_is_valid() -> None:
    """Every IFM state has a land class in the CBM range."""
    rows = _rows("land_class.bc.csv")
    assert rows
    assert len({row["ifm"] for row in rows}) == len(rows)
    for row in rows:
        assert 0 <= int(row["landclass"]) <= 22


def test_example_config_parses() -> None:
    """The example configuration is valid YAML with the expected block."""
    data = yaml.safe_load((CONFIG / "carbon.example.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    carbon = data["carbon"]
    assert carbon["schema_version"] == "0.1"
    assert carbon["admin_boundary"] == "British Columbia"
    assert carbon["fallback"]["softwood_species"] == "Unspecified softwood species"


def test_species_map_uses_vri_codes() -> None:
    """Every non-fallback species key has a public VRI code."""
    vri = {row["vri_code"] for row in _rows("vri_species_codes.csv")}
    species = _rows("species_map.bc.csv")
    for row in species:
        code = row["vri_code"]
        if code:
            assert code in vri, (row["bc_species"], code)
    by_code = {row["bc_species"]: row for row in species}
    assert by_code["BL"]["cbm_species"] == "Subalpine fir (or alpine fir)"
    assert by_code["SB"]["cbm_species"] == "Black spruce"
    assert by_code["EP"]["cbm_species"] == "White birch"
    assert by_code["DR"]["cbm_species"] == "Red alder"
    assert by_code["PA"]["cbm_species"] == "Whitebark pine"
    assert by_code["QG"]["cbm_species"] == "Garry oak"


def test_unmanaged_land_class_is_sixteen() -> None:
    """CBM land class 16 is Unmanaged Forest Land; managed remains 0."""
    rows = {row["ifm"]: row for row in _rows("land_class.bc.csv")}
    assert rows["managed"]["landclass"] == "0"
    assert rows["unmanaged"]["landclass"] == "16"
