"""Tests for the EFI model application and backtest engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.efi.application import (
    EFIApplicationError,
    LinearEFIModel,
    apply_linear_model,
    backtest_linear_model,
    load_linear_efi_model,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "efi"
CARD = FIXTURE_ROOT / "site_index_card.json"
COEFFICIENTS = FIXTURE_ROOT / "site_index_coefficients.json"


def _model() -> LinearEFIModel:
    return load_linear_efi_model(CARD, COEFFICIENTS)


def _rows() -> list[dict[str, object]]:
    return [
        {
            "fragment_id": 1,
            "chm_p95": 30.0,
            "canopy_cover_2m": 0.6,
            "region": "CWH",
            "species": "Fd",
            "age": 60,
            "height": 30.0,
            "observed_site_index": 23.5,
        },
        {
            "fragment_id": 2,
            "chm_p95": 25.0,
            "canopy_cover_2m": 0.5,
            "region": "CWH",
            "species": "Cw",
            "age": 80,
            "height": 25.0,
            "observed_site_index": 20.5,
        },
        {
            "fragment_id": 3,
            "chm_p95": 35.0,
            "canopy_cover_2m": 0.7,
            "region": "CWH",
            "species": "Fd",
            "age": 100,
            "height": 35.0,
            "observed_site_index": 25.0,
        },
    ]


def test_load_model_and_predict() -> None:
    model = _model()

    assert model.card.model_id == "als-site-index-cwh-v1"
    assert model.intercept == pytest.approx(5.0)
    assert model.coefficients == {
        "chm_p95": pytest.approx(0.7),
        "canopy_cover_2m": pytest.approx(-5.0),
    }
    assert model.predict({"chm_p95": 30.0, "canopy_cover_2m": 0.6}) == pytest.approx(
        23.0
    )


def test_apply_linear_model_adds_prediction_and_provenance() -> None:
    rows = _rows()
    predictions = apply_linear_model(rows, _model())

    assert len(predictions) == 3
    assert predictions[0]["predicted_site_index"] == pytest.approx(23.0)
    assert predictions[1]["predicted_site_index"] == pytest.approx(20.0)
    assert predictions[2]["predicted_site_index"] == pytest.approx(26.0)
    assert predictions[0]["model_id"] == "als-site-index-cwh-v1"
    assert predictions[0]["model_version"] == "0.1.0-pilot"
    assert predictions[0]["model_attribute"] == "site_index"
    assert predictions[0]["model_unit"] == "m"
    assert predictions[0]["model_rmse"] == pytest.approx(2.1)
    assert predictions[0]["model_in_domain"] is True
    assert predictions[0]["model_domain_reasons"] == []
    assert rows[0]["fragment_id"] == 1
    assert "predicted_site_index" not in rows[0]


def test_out_of_domain_row_is_flagged() -> None:
    row = {
        "chm_p95": 20.0,
        "canopy_cover_2m": 0.4,
        "region": "ICH",
        "species": "Sx",
        "age": 200,
        "height": 90.0,
    }

    prediction = apply_linear_model([row], _model())[0]

    assert prediction["model_in_domain"] is False
    reasons = prediction["model_domain_reasons"]
    assert isinstance(reasons, list)
    assert any("region" in reason for reason in reasons)
    assert any("species" in reason for reason in reasons)
    assert any("age" in reason for reason in reasons)
    assert any("height" in reason for reason in reasons)


def test_require_domain_raises() -> None:
    row = {
        "chm_p95": 20.0,
        "canopy_cover_2m": 0.4,
        "region": "ICH",
        "species": "Sx",
        "age": 200,
        "height": 90.0,
    }

    with pytest.raises(EFIApplicationError, match="out of domain"):
        apply_linear_model([row], _model(), require_domain=True)


def test_drop_policy_omits_out_of_domain_rows() -> None:
    rows = [
        {
            "fragment_id": 1,
            "chm_p95": 30.0,
            "canopy_cover_2m": 0.6,
            "region": "CWH",
            "species": "Fd",
            "age": 60,
            "height": 30.0,
        },
        {
            "fragment_id": 2,
            "chm_p95": 20.0,
            "canopy_cover_2m": 0.4,
            "region": "ICH",
            "species": "Sx",
            "age": 200,
            "height": 90.0,
        },
    ]

    predictions = apply_linear_model(rows, _model(), out_of_domain="drop")

    assert len(predictions) == 1
    assert predictions[0]["fragment_id"] == 1


def test_backtest_reports_metrics() -> None:
    metrics = backtest_linear_model(
        _rows(), _model(), observed_column="observed_site_index"
    )

    assert metrics["model_id"] == "als-site-index-cwh-v1"
    assert metrics["attribute"] == "site_index"
    assert metrics["n"] == 3
    assert metrics["in_domain_count"] == 3
    assert metrics["out_of_domain_count"] == 0
    assert metrics["bias"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["rmse"] == pytest.approx(0.70710678, rel=1e-6)
    assert metrics["mae"] == pytest.approx(0.66666667, rel=1e-6)
    assert metrics["r2"] == pytest.approx(0.85714286, rel=1e-6)


def test_backtest_excludes_out_of_domain_rows() -> None:
    rows = _rows()
    rows.append(
        {
            "fragment_id": 4,
            "chm_p95": 20.0,
            "canopy_cover_2m": 0.4,
            "region": "ICH",
            "species": "Sx",
            "age": 200,
            "height": 90.0,
            "observed_site_index": 15.0,
        }
    )

    metrics = backtest_linear_model(
        rows, _model(), observed_column="observed_site_index"
    )

    assert metrics["n"] == 3
    assert metrics["out_of_domain_count"] == 1


def test_predictor_column_mapping_is_supported() -> None:
    rows = [
        {
            "fragment_id": 1,
            "chm95": 30.0,
            "cover2": 0.6,
            "region": "CWH",
            "species": "Fd",
            "age": 60,
            "height": 30.0,
        }
    ]

    prediction = apply_linear_model(
        rows,
        _model(),
        predictor_columns={"chm_p95": "chm95", "canopy_cover_2m": "cover2"},
    )[0]

    assert prediction["predicted_site_index"] == pytest.approx(23.0)


def test_missing_predictor_column_is_rejected() -> None:
    rows = [
        {
            "fragment_id": 1,
            "chm_p95": 30.0,
            "region": "CWH",
            "species": "Fd",
            "age": 60,
            "height": 30.0,
        }
    ]

    with pytest.raises(EFIApplicationError, match="missing predictor column"):
        apply_linear_model(rows, _model())


def test_coefficient_model_id_must_match_card(tmp_path: Path) -> None:
    payload = json.loads(COEFFICIENTS.read_text(encoding="utf-8"))
    payload["model_id"] = "other-model"
    target = tmp_path / "coefficients.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EFIApplicationError, match="model_id does not match"):
        load_linear_efi_model(CARD, target)


def test_coefficient_predictors_must_match_card(tmp_path: Path) -> None:
    payload = json.loads(COEFFICIENTS.read_text(encoding="utf-8"))
    payload["coefficients"] = {"chm_p95": 0.7}
    target = tmp_path / "coefficients.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EFIApplicationError, match="predictors must exactly match"):
        load_linear_efi_model(CARD, target)


def test_unknown_coefficient_field_is_rejected(tmp_path: Path) -> None:
    payload = json.loads(COEFFICIENTS.read_text(encoding="utf-8"))
    payload["extra"] = "nope"
    target = tmp_path / "coefficients.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EFIApplicationError, match="unknown coefficient fields"):
        load_linear_efi_model(CARD, target)


def test_backtest_requires_an_observed_column() -> None:
    rows = [
        {
            key: value
            for key, value in _rows()[0].items()
            if key != "observed_site_index"
        }
    ]

    with pytest.raises(EFIApplicationError, match="missing observed column"):
        backtest_linear_model(rows, _model(), observed_column="observed_site_index")
