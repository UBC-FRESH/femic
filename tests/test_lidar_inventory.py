from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli.main import app
from femic.lidar.inventory import (
    LidarInventoryError,
    build_inventory_als,
    load_inventory_als_model,
    write_inventory_als,
)
from femic.lidar.products import build_lidar_product_bundle

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "lidar"
SELECTION_MANIFEST = FIXTURE_ROOT / "selection_manifest.json"
PRODUCT_PLAN = FIXTURE_ROOT / "product_plan.json"
MODEL_CARD = FIXTURE_ROOT / "inventory_model.json"
GENERATED_UTC = "2026-10-29T00:00:00+00:00"


def _bundle(tmp_path: Path) -> Path:
    return build_lidar_product_bundle(
        selection_manifest_path=SELECTION_MANIFEST,
        product_plan_path=PRODUCT_PLAN,
        output_dir=tmp_path / "bundle",
        generated_utc=GENERATED_UTC,
    ).bundle_dir


def test_load_inventory_model_card() -> None:
    model = load_inventory_als_model(MODEL_CARD)

    assert model.model_id == "fixture-identity-lorey-height"
    assert model.attribute == "lorey_height_m"
    assert model.coefficients == {"lorey_height_m": 1.0}
    assert model.rmse == 0.0
    assert model.sha256


def test_apply_inventory_model_to_bundle(tmp_path: Path) -> None:
    result = build_inventory_als(
        _bundle(tmp_path),
        MODEL_CARD,
        generated_utc=GENERATED_UTC,
    )

    assert result.bundle_id
    assert result.schema_version == "femic.inventory.als.v1"
    assert len(result.rows) == 1
    row = result.rows[0]
    assert row.fragment_id == "lidarbc:1:1"
    assert row.attribute == "lorey_height_m"
    assert row.value == pytest.approx(12.5)
    assert row.model_id == "fixture-identity-lorey-height"
    assert row.rmse == 0.0
    assert result.validation is None
    assert "No plot/observation" in result.warnings[0]


def test_write_inventory_outputs(tmp_path: Path) -> None:
    result = build_inventory_als(_bundle(tmp_path), MODEL_CARD, generated_utc=GENERATED_UTC)
    paths = write_inventory_als(result, tmp_path / "inventory")

    assert paths["table"].is_file()
    assert paths["manifest"].is_file()
    text = paths["table"].read_text(encoding="utf-8")
    assert "fragment_id,attribute,value,model_id,rmse,model_version,unit,source" in text
    assert "lidarbc:1:1,lorey_height_m,12.5" in text
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "femic.inventory.als.v1"
    assert manifest["model"]["model_id"] == "fixture-identity-lorey-height"


def test_plot_validation_lane(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    plots = tmp_path / "plots.csv"
    plots.write_text(
        "fragment_id,attribute,observed\nlidarbc:1:1,lorey_height_m,12.0\n",
        encoding="utf-8",
    )

    result = build_inventory_als(bundle, MODEL_CARD, plots_path=plots)

    assert result.validation is not None
    assert result.validation.matched_rows == 1
    assert result.validation.bias == pytest.approx(0.5)
    assert result.validation.mae == pytest.approx(0.5)
    assert result.validation.rmse == pytest.approx(0.5)


def test_missing_predictor_refuses(tmp_path: Path) -> None:
    model = json.loads(MODEL_CARD.read_text(encoding="utf-8"))
    model["coefficients"] = {"not_in_canopy": 1.0}
    model["predictor_ranges"] = {}
    model_path = tmp_path / "bad-model.json"
    model_path.write_text(json.dumps(model), encoding="utf-8")

    with pytest.raises(LidarInventoryError, match="missing model predictor"):
        build_inventory_als(_bundle(tmp_path), model_path)


def test_invalid_predictor_range_refuses(tmp_path: Path) -> None:
    model = json.loads(MODEL_CARD.read_text(encoding="utf-8"))
    model["predictor_ranges"] = {"lorey_height_m": [0.0, 5.0]}
    model_path = tmp_path / "range-model.json"
    model_path.write_text(json.dumps(model), encoding="utf-8")

    with pytest.raises(LidarInventoryError, match="outside the model-card range"):
        build_inventory_als(_bundle(tmp_path), model_path)


def test_cli_inventory_outputs(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    out = tmp_path / "inventory"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "lidar",
            "inventory",
            "--bundle",
            str(bundle),
            "--model",
            str(MODEL_CARD),
            "--output-dir",
            str(out),
            "--generated-utc",
            GENERATED_UTC,
        ],
        prog_name="femic",
    )

    assert result.exit_code == 0, result.output
    assert (out / "inventory_als.csv").is_file()
    assert (out / "inventory_als.json").is_file()
