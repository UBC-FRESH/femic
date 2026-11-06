"""Tests for the RSYC biomass curve family and carbon conversion."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.efi.biomass import (
    BiomassCurveError,
    load_biomass_curves,
)

REPO = Path(__file__).resolve().parents[1]
CURVES = REPO / "config" / "efi" / "biomass" / "rsyc_cariboo_pilot.json"
RUNNER = CliRunner()


def _document() -> dict[str, object]:
    return json.loads(CURVES.read_text(encoding="utf-8"))


def test_loads_published_curves_and_evaluates() -> None:
    """The pilot curves load and reproduce the published equation."""
    family = load_biomass_curves(CURVES)
    assert family.source_id == "tompalski-et-al-2025-rsyc-national"
    assert family.licence_id == "CC-BY-4.0"
    curve = family.select_one(species="PSEU.MEN")
    assert curve.agb.unit == "t_ha"
    assert curve.volume is not None
    assert curve.volume.unit == "m3_ha"
    assert curve.agb_t_ha(50) == pytest.approx(103.381917, abs=1e-5)
    assert curve.volume_m3_ha(50) == pytest.approx(223.982562, abs=1e-5)
    assert curve.carbon_t_c_ha(50) == pytest.approx(48.589501, abs=1e-5)
    assert curve.carbon_fraction == 0.47
    assert curve.carbon_fraction_source


def test_biomass_and_volume_curves_are_separate() -> None:
    """The curves have different units and are not summed."""
    family = load_biomass_curves(CURVES)
    for curve in family.curves:
        for age in (20, 50, 100):
            agb = curve.agb_t_ha(age)
            volume = curve.volume_m3_ha(age)
            assert agb > 0
            assert volume is not None and volume > 0
            assert 0.4 < agb / volume < 0.6


def test_pilot_curves_are_non_negative_and_monotonic_to_peak() -> None:
    """The pilot curves are finite, non-negative, and increasing to age 100."""
    family = load_biomass_curves(CURVES)
    for curve in family.curves:
        values = [curve.agb_t_ha(age) for age in range(1, 101, 5)]
        assert all(value >= 0 for value in values)
        assert all(right >= left for left, right in itertools.pairwise(values))


def test_age_domain_is_enforced() -> None:
    """Ages outside the curve domain fail."""
    curve = load_biomass_curves(CURVES).select_one(species="PSEU.MEN")
    with pytest.raises(BiomassCurveError, match="outside the curve domain"):
        curve.agb_t_ha(0)
    with pytest.raises(BiomassCurveError, match="outside the curve domain"):
        curve.agb_t_ha(301)


def test_selection_requires_a_unique_match() -> None:
    """Ambiguous and empty selections fail clearly."""
    family = load_biomass_curves(CURVES)
    with pytest.raises(BiomassCurveError, match="multiple curves"):
        family.select_one(region="Montane Cordillera")
    with pytest.raises(BiomassCurveError, match="no curve"):
        family.select_one(species="PSEU.MEN", ecodistrict="Nowhere")


def test_missing_carbon_fraction_fails(tmp_path: Path) -> None:
    """The conversion factor is mandatory."""
    document = _document()
    document["curves"][0].pop("carbon_fraction")  # type: ignore[index]
    path = tmp_path / "curves.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(BiomassCurveError, match="carbon_fraction"):
        load_biomass_curves(path)


def test_missing_carbon_fraction_source_fails(tmp_path: Path) -> None:
    """The conversion source is mandatory."""
    document = _document()
    document["curves"][0].pop("carbon_fraction_source")  # type: ignore[index]
    path = tmp_path / "curves.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(BiomassCurveError, match="carbon_fraction_source"):
        load_biomass_curves(path)


def test_cli_prints_biomass_volume_and_carbon() -> None:
    """The CLI exposes the independent curve and conversion."""
    result = RUNNER.invoke(
        app,
        [
            "efi",
            "biomass-curve",
            str(CURVES),
            "--species",
            "PSEU.MEN",
            "--age",
            "50",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["curve"]["species"] == "PSEU.MEN"
    assert payload["agb_t_ha"] == pytest.approx(103.381917, abs=1e-5)
    assert payload["volume_m3_ha"] == pytest.approx(223.982562, abs=1e-5)
    assert payload["carbon_t_c_ha"] == pytest.approx(48.589501, abs=1e-5)
    assert payload["carbon_fraction"] == 0.47
    assert payload["source_url"]
    assert payload["licence_id"] == "CC-BY-4.0"
