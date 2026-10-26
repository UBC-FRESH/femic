"""Tests for published EFI cards and the attribute-table annotation seam."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.contracts.efi import read_efi_model_card
from femic.efi import (
    EFI_ATTRIBUTE_TABLE_SCHEMA_VERSION,
    EFIApplicationError,
    annotate_attribute_table,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = ROOT / "config" / "efi" / "models"
HEIGHT_CARD = MODEL_ROOT / "als_loreys_height_cwh_2015.json"
SITE_CARD = MODEL_ROOT / "als_site_index_loblolly_seus_2019.json"
ATTRIBUTE_ROWS = Path(__file__).parent / "fixtures" / "efi" / "attribute_rows.csv"
runner = CliRunner()


def test_published_cards_are_valid_and_distinct() -> None:
    height = read_efi_model_card(HEIGHT_CARD)
    site = read_efi_model_card(SITE_CARD)

    assert height.attribute == "height"
    assert height.validation.rmse == pytest.approx(2.88)
    assert height.training.region == "CWH"
    assert height.training.species == ("Cw", "Hw", "Hm")
    assert site.attribute == "site_index"
    assert site.validation.rmse == pytest.approx(3.8)
    assert site.training.region == "southeastern USA"
    assert site.training.species == ("Pinus taeda",)
    assert height.training.region != site.training.region
    assert height.training.species != site.training.species


def test_annotate_table_flags_out_of_domain_rows(tmp_path: Path) -> None:
    output = tmp_path / "annotated.csv"
    summary_path = tmp_path / "summary.json"

    result = annotate_attribute_table(
        ATTRIBUTE_ROWS,
        HEIGHT_CARD,
        output,
        summary_path=summary_path,
    )

    assert result.row_count == 3
    assert result.rows_written == 3
    assert result.in_domain_count == 2
    assert result.out_of_domain_count == 1
    assert result.model_id == "published-als-loreys-height-cwh-2015"
    assert result.columns_added[0] == "model_card_schema_version"
    assert result.summary_path == summary_path

    frame = pd.read_csv(output)
    assert list(frame["model_id"].unique()) == ["published-als-loreys-height-cwh-2015"]
    assert frame["model_rmse"].tolist() == pytest.approx([2.88, 2.88, 2.88])
    assert frame["model_in_domain"].tolist() == [True, False, True]
    reasons = json.loads(
        frame.loc[frame["fragment_id"] == 2, "model_domain_reasons"].item()
    )
    assert any("region" in reason for reason in reasons)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["schema_version"] == EFI_ATTRIBUTE_TABLE_SCHEMA_VERSION
    assert summary["out_of_domain_count"] == 1


def test_drop_policy_omits_out_of_domain_rows(tmp_path: Path) -> None:
    output = tmp_path / "annotated.parquet"

    result = annotate_attribute_table(
        ATTRIBUTE_ROWS,
        HEIGHT_CARD,
        output,
        domain_policy="drop",
    )

    assert result.rows_written == 2
    frame = pd.read_parquet(output)
    assert frame["fragment_id"].tolist() == [1, 3]
    assert frame["model_id"].nunique() == 1


def test_require_policy_raises(tmp_path: Path) -> None:
    with pytest.raises(EFIApplicationError, match="outside model"):
        annotate_attribute_table(
            ATTRIBUTE_ROWS,
            HEIGHT_CARD,
            tmp_path / "annotated.csv",
            domain_policy="require",
        )


def test_annotation_can_use_the_site_index_card(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "fragment_id": 10,
                "region": "southeastern USA",
                "species": "Pinus taeda",
                "age": 20,
                "height": 18.0,
            },
            {
                "fragment_id": 11,
                "region": "CWH",
                "species": "Cw",
                "age": 60,
                "height": 30.0,
            },
        ]
    )
    source = tmp_path / "rows.csv"
    frame.to_csv(source, index=False)

    result = annotate_attribute_table(
        source,
        SITE_CARD,
        tmp_path / "annotated.csv",
    )

    assert result.in_domain_count == 1
    assert result.out_of_domain_count == 1


def test_annotation_rejects_unknown_policy(tmp_path: Path) -> None:
    with pytest.raises(EFIApplicationError, match="domain_policy"):
        annotate_attribute_table(
            ATTRIBUTE_ROWS,
            HEIGHT_CARD,
            tmp_path / "annotated.csv",
            domain_policy="ignore",
        )


def test_cli_annotates_a_table(tmp_path: Path) -> None:
    output = tmp_path / "annotated.csv"
    summary = tmp_path / "summary.json"
    result = runner.invoke(
        app,
        [
            "efi",
            "annotate",
            str(ATTRIBUTE_ROWS),
            "--card",
            str(HEIGHT_CARD),
            "--output",
            str(output),
            "--summary",
            str(summary),
        ],
    )

    assert result.exit_code == 0, result.stdout + result.stderr
    assert output.is_file()
    assert summary.is_file()
    assert "published-als-loreys-height-cwh-2015" in result.stdout
