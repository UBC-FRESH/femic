"""Tests for the ``femic.efi.model.v1`` contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from femic.contracts.efi import (
    EFI_MODEL_SCHEMA_VERSION,
    EFIContractError,
    EFIModelCard,
    annotate_attribute_rows,
    efi_model_schema,
    read_efi_model_card,
    summarize_efi_model_card,
    validate_efi_model_card,
    write_efi_model_card,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "contracts"
HEIGHT_FIXTURE = FIXTURE_ROOT / "efi_model_height_v1.json"
VOLUME_FIXTURE = FIXTURE_ROOT / "efi_model_volume_v1.json"


def _height_card() -> EFIModelCard:
    return read_efi_model_card(HEIGHT_FIXTURE)


def _volume_card() -> EFIModelCard:
    return read_efi_model_card(VOLUME_FIXTURE)


def _card_dict() -> dict[str, object]:
    return _height_card().to_dict()


def test_height_card_reads() -> None:
    card = _height_card()

    assert card.model_id == "als-height-cwh-v1"
    assert card.model_version == "1.0.0"
    assert card.attribute == "height"
    assert card.unit == "m"
    assert card.predictors == ("chm_p95", "canopy_cover_2m")
    assert card.training.region == "CWH"
    assert card.training.plot_count == 120
    assert card.validation.rmse == pytest.approx(1.8)
    assert card.validation.bias == pytest.approx(-0.2)
    assert card.validation.r2 == pytest.approx(0.82)
    assert card.applicability.regions == ("CWH",)
    assert card.licence_id == "OGL-BC"


def test_volume_card_reads() -> None:
    card = _volume_card()

    assert card.attribute == "volume"
    assert card.unit == "m3_ha"
    assert card.validation.rmse == pytest.approx(42.0)
    assert card.applicability.species == ("Fd", "Hw")


def test_json_round_trip_is_identical(tmp_path: Path) -> None:
    card = _height_card()
    target = tmp_path / "model.json"

    write_efi_model_card(target, card)

    assert read_efi_model_card(target) == card


def test_summary_carries_validation_and_applicability() -> None:
    summary = summarize_efi_model_card(_height_card())

    assert summary["schema_version"] == EFI_MODEL_SCHEMA_VERSION
    assert summary["model_id"] == "als-height-cwh-v1"
    assert summary["attribute"] == "height"
    validation = summary["validation"]
    assert isinstance(validation, dict)
    assert validation["rmse"] == pytest.approx(1.8)
    applicability = summary["applicability"]
    assert isinstance(applicability, dict)
    assert applicability["regions"] == ["CWH"]


def test_applies_to_accepts_an_in_domain_query() -> None:
    check = _height_card().applies_to(region="CWH", species="Fd", age=60, height=30.0)

    assert check.in_domain is True
    assert check.reasons == ()
    assert check.model_id == "als-height-cwh-v1"


def test_applies_to_rejects_out_of_domain_query() -> None:
    check = _height_card().applies_to(region="ICH", species="Sx", age=200, height=90.0)

    assert check.in_domain is False
    assert any("region" in reason for reason in check.reasons)
    assert any("species" in reason for reason in check.reasons)
    assert any("age" in reason for reason in check.reasons)
    assert any("height" in reason for reason in check.reasons)


def test_applies_to_rejects_missing_restricted_dimensions() -> None:
    check = _height_card().applies_to()

    assert check.in_domain is False
    assert "region not provided" in check.reasons
    assert "species not provided" in check.reasons
    assert "age not provided" in check.reasons
    assert "height not provided" in check.reasons


def test_annotate_attribute_rows_attaches_model_metadata() -> None:
    rows = [
        {"fragment_id": 1001, "height_m": 24.5},
        {"fragment_id": 1002, "height_m": 26.0},
    ]

    annotated = annotate_attribute_rows(rows, _height_card())

    assert annotated[0]["fragment_id"] == 1001
    assert annotated[0]["model_id"] == "als-height-cwh-v1"
    assert annotated[0]["model_rmse"] == pytest.approx(1.8)
    assert annotated[0]["model_attribute"] == "height"
    assert annotated[0]["model_licence_id"] == "OGL-BC"
    assert rows[0] == {"fragment_id": 1001, "height_m": 24.5}


def test_missing_validation_rmse_is_rejected() -> None:
    card = _card_dict()
    validation = card["validation"]
    assert isinstance(validation, dict)
    validation.pop("rmse")

    with pytest.raises(EFIContractError, match="missing validation fields: rmse"):
        validate_efi_model_card(card)


def test_unit_must_match_attribute() -> None:
    card = _card_dict()
    card["unit"] = "m3_ha"

    with pytest.raises(EFIContractError, match="unit for 'height'"):
        validate_efi_model_card(card)


def test_predictors_must_be_non_empty() -> None:
    card = _card_dict()
    card["predictors"] = []

    with pytest.raises(EFIContractError, match="predictors must be a non-empty list"):
        validate_efi_model_card(card)


def test_duplicate_predictors_are_rejected() -> None:
    card = _card_dict()
    card["predictors"] = ["chm_p95", "chm_p95"]

    with pytest.raises(
        EFIContractError, match="predictors must not contain duplicates"
    ):
        validate_efi_model_card(card)


def test_applicability_needs_a_region_or_species() -> None:
    card = _card_dict()
    applicability = card["applicability"]
    assert isinstance(applicability, dict)
    applicability["regions"] = []
    applicability["species"] = []

    with pytest.raises(EFIContractError, match="at least one region or species"):
        validate_efi_model_card(card)


def test_age_bounds_must_be_ordered() -> None:
    card = _card_dict()
    applicability = card["applicability"]
    assert isinstance(applicability, dict)
    applicability["age_min"] = 120
    applicability["age_max"] = 20

    with pytest.raises(EFIContractError, match="age_min must not exceed age_max"):
        validate_efi_model_card(card)


def test_rmse_must_be_non_negative() -> None:
    card = _card_dict()
    validation = card["validation"]
    assert isinstance(validation, dict)
    validation["rmse"] = -1.0

    with pytest.raises(EFIContractError, match="validation.rmse must be non-negative"):
        validate_efi_model_card(card)


def test_training_region_must_be_in_applicability() -> None:
    card = _card_dict()
    training = card["training"]
    assert isinstance(training, dict)
    training["region"] = "ICH"

    with pytest.raises(
        EFIContractError, match="training.region must be in applicability.regions"
    ):
        validate_efi_model_card(card)


def test_validation_unit_must_match_card_unit() -> None:
    card = _card_dict()
    validation = card["validation"]
    assert isinstance(validation, dict)
    validation["unit"] = "cm"

    with pytest.raises(EFIContractError, match="validation.unit"):
        validate_efi_model_card(card)


def test_unknown_attribute_is_rejected() -> None:
    card = _card_dict()
    card["attribute"] = "leaf_area"

    with pytest.raises(EFIContractError, match="attribute must be one of"):
        validate_efi_model_card(card)


def test_timestamp_requires_timezone() -> None:
    card = _card_dict()
    card["created_utc"] = "2026-10-25T00:00:00"

    with pytest.raises(EFIContractError, match="must include a timezone"):
        validate_efi_model_card(card)


def test_unknown_field_is_rejected() -> None:
    card = _card_dict()
    card["extra"] = "nope"

    with pytest.raises(EFIContractError, match="unknown EFI model fields: extra"):
        validate_efi_model_card(card)


def test_schema_is_a_defensive_copy() -> None:
    first = efi_model_schema()
    first["title"] = "mutated"

    assert efi_model_schema()["title"] == "FEMIC efi.model.v1 model card"
    required = efi_model_schema()["required"]
    assert isinstance(required, list)
    assert "validation" in required
    assert "applicability" in required


def test_json_card_must_be_an_object(tmp_path: Path) -> None:
    target = tmp_path / "model.json"
    target.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(EFIContractError, match="must contain a model-card object"):
        read_efi_model_card(target)
