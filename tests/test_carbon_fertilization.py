"""Tests for public-data fertilization response and emissions audit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from femic.carbon.fertilization import (
    fertilization_audit,
    fertilized_curve,
    load_fertilization_config,
    load_tipsy_fertilization_response,
    tipsy_response_percent,
    write_fertilization_audit,
)
from femic.cli.main import app

CONFIG = Path("config/carbon/fertilization.bc.yaml")


def test_tipsy_response_tables_parse() -> None:
    """The public TIPSY table has the expected species and positive response."""
    config = load_fertilization_config(CONFIG)
    assert config.response_file is not None
    response = load_tipsy_fertilization_response(config.response_file)
    assert {"FDC", "FDI", "PLI", "SS", "SW"}.issubset(
        {key[0] for key in response.tables}
    )
    percent = tipsy_response_percent(
        response, species_code="SW", site_index=20, response_age=20
    )
    assert percent > 0


def test_fertilized_curve_uses_public_response() -> None:
    """The curve is unchanged before the response and lifted after it."""
    config = load_fertilization_config(CONFIG)
    base = ((0.0, 0.0), (10.0, 50.0), (20.0, 100.0), (30.0, 150.0), (40.0, 200.0))
    fert = fertilized_curve(
        curve=base,
        response_age=20,
        config=config,
        species_code="SW",
        site_index=20,
    )
    assert fert[2] == pytest.approx(base[2])
    assert fert[3][1] > base[3][1]
    assert fert[4][1] > fert[3][1]


def test_fertilization_audit_accounts() -> None:
    """The audit converts public factors into accounts and totals."""
    config = load_fertilization_config(CONFIG)
    blocks = pd.DataFrame({"block_id": [1, 2], "area_ha": [10.0, 5.0]})
    schedule = pd.DataFrame(
        {
            "block_id": [1, 2],
            "treatment": ["f1", "f2"],
            "offset": [1, 1],
        }
    )
    result = fertilization_audit(schedule=schedule, block_areas=blocks, config=config)
    assert result.total_area_ha == pytest.approx(15.0)
    accounts = result.accounts.set_index(["offset", "account"])["value"]
    assert accounts.loc[(1, "fertilization.area_ha")] == pytest.approx(15.0)
    assert accounts.loc[(1, "fertilization.dose_kg_n")] == pytest.approx(3000.0)
    assert accounts.loc[(1, "fertilization.co2e_t")] > 0


def test_fertilization_audit_writes_manifest(tmp_path: Path) -> None:
    """The audit writer emits accounts and a manifest."""
    config = load_fertilization_config(CONFIG)
    blocks = pd.DataFrame({"block_id": [1], "area_ha": [2.0]})
    schedule = pd.DataFrame({"block_id": [1], "treatment": ["f1"], "offset": [0]})
    result = fertilization_audit(schedule=schedule, block_areas=blocks, config=config)
    accounts = write_fertilization_audit(result, tmp_path)
    assert accounts.is_file()
    assert (tmp_path / "fertilization_manifest.json").is_file()


def test_cli_fertilization_audit(tmp_path: Path) -> None:
    """The CLI reads a compiled dataset and schedule."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    pd.DataFrame({"block_id": [1], "area_ha": [2.0]}).to_parquet(
        dataset / "blocks.parquet", index=False
    )
    schedule = tmp_path / "schedule.csv"
    schedule.write_text("block_id,treatment,offset\n1,f1,0\n", encoding="utf-8")
    result = CliRunner().invoke(
        app,
        [
            "carbon",
            "fertilization-audit",
            "--dataset",
            str(dataset),
            "--schedule",
            str(schedule),
            "--fertilization-config",
            str(CONFIG),
            "--out",
            str(tmp_path / "audit"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "fertilization audit complete" in result.output
    assert (tmp_path / "audit" / "fertilization_accounts.csv").is_file()


def test_cli_fertilization_curve(tmp_path: Path) -> None:
    """The CLI materializes a fertilized yield curve from the package."""
    package = Path("tests/fixtures/carbon/tsa24_minimal")
    track = "AU(2401000)+IFM(managed)+treatment()"
    out = tmp_path / "fertilized.csv"
    result = CliRunner().invoke(
        app,
        [
            "carbon",
            "fertilization-curve",
            "--package",
            str(package),
            "--track",
            track,
            "--species",
            "SW",
            "--site-index",
            "20",
            "--response-age",
            "10",
            "--fertilization-config",
            str(CONFIG),
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    assert out.with_suffix(".json").is_file()
    assert "fertilized curve written" in result.output
