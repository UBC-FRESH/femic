"""Versioned EFI model-card contract for ALS-derived inventory attributes.

This module owns the ``femic.efi.model.v1`` model card: the metadata that
travels with an area-based or tree-level EFI model. It records what the model
predicts, what it was trained on, how accurate it is, where it applies, and
what licence governs it.

The card is not a validation certificate and not a model registry. It makes the
claim inspectable; it does not make the claim true.
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

EFI_MODEL_SCHEMA_VERSION = "femic.efi.model.v1"

#: Canonical target attributes and their required units.
EFI_ATTRIBUTE_UNITS: dict[str, str] = {
    "height": "m",
    "volume": "m3_ha",
    "basal_area": "m2_ha",
    "density": "stems_ha",
    "canopy_cover": "fraction",
    "species_fraction": "fraction",
    "site_index": "m",
    "biomass": "t_ha",
    "carbon": "tC_ha",
    "other": "",
}

EFI_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "model_id",
    "model_version",
    "attribute",
    "unit",
    "predictors",
    "training",
    "validation",
    "applicability",
    "licence_id",
    "created_utc",
)
EFI_OPTIONAL_FIELDS: tuple[str, ...] = ("notes",)
EFI_ALLOWED_FIELDS: frozenset[str] = frozenset(
    EFI_REQUIRED_FIELDS + EFI_OPTIONAL_FIELDS
)


class EFIContractError(ValueError):
    """Raised when a model card violates ``femic.efi.model.v1``."""


def _require_text(value: object, field: str) -> str:
    """Return a non-empty string, or raise a contract error."""
    if not isinstance(value, str) or not value.strip():
        raise EFIContractError(f"{field} must be a non-empty string")
    return value.strip()


def _require_int(value: object, field: str) -> int:
    """Return an integer, rejecting booleans and non-integers."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise EFIContractError(f"{field} must be an integer")
    return value


def _require_number(value: object, field: str) -> float:
    """Return a finite number, rejecting booleans, NaN, and infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EFIContractError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise EFIContractError(f"{field} must be finite")
    return number


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    """Return a mapping, or raise a contract error."""
    if not isinstance(value, Mapping):
        raise EFIContractError(f"{field} must be a mapping")
    return value


def _require_timestamp(value: object, field: str) -> datetime:
    """Return a timezone-aware ISO-8601 timestamp."""
    text = _require_text(value, field)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise EFIContractError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EFIContractError(f"{field} must include a timezone")
    return parsed


def _require_text_list(
    value: object, field: str, *, allow_empty: bool
) -> tuple[str, ...]:
    """Validate a list of non-empty, unique strings."""
    if not isinstance(value, list):
        raise EFIContractError(f"{field} must be a list")
    if not allow_empty and not value:
        raise EFIContractError(f"{field} must be a non-empty list")
    items = tuple(_require_text(item, field) for item in value)
    if len(set(items)) != len(items):
        raise EFIContractError(f"{field} must not contain duplicates")
    return items


def _build_schema() -> dict[str, object]:
    """Build the JSON Schema document for an EFI model card."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://femic.ubc.ca/schemas/efi.model.v1.json",
        "title": "FEMIC efi.model.v1 model card",
        "type": "object",
        "additionalProperties": False,
        "required": list(EFI_REQUIRED_FIELDS),
        "properties": {
            "schema_version": {"const": EFI_MODEL_SCHEMA_VERSION},
            "model_id": {"type": "string", "minLength": 1},
            "model_version": {"type": "string", "minLength": 1},
            "attribute": {"type": "string", "enum": sorted(EFI_ATTRIBUTE_UNITS)},
            "unit": {"type": "string"},
            "predictors": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
                "uniqueItems": True,
            },
            "training": {"$ref": "#/$defs/training"},
            "validation": {"$ref": "#/$defs/validation"},
            "applicability": {"$ref": "#/$defs/applicability"},
            "licence_id": {"type": "string", "minLength": 1},
            "created_utc": {"type": "string", "format": "date-time"},
            "notes": {"type": ["string", "null"]},
        },
        "$defs": {
            "training": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "source_id",
                    "source_version",
                    "region",
                    "plot_count",
                ],
                "properties": {
                    "source_id": {"type": "string", "minLength": 1},
                    "source_version": {"type": "string", "minLength": 1},
                    "region": {"type": "string", "minLength": 1},
                    "plot_count": {"type": "integer", "minimum": 0},
                    "species": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "uniqueItems": True,
                    },
                    "period": {"type": ["string", "null"]},
                    "notes": {"type": ["string", "null"]},
                },
            },
            "validation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["design", "n", "rmse", "bias", "unit"],
                "properties": {
                    "design": {"type": "string", "minLength": 1},
                    "n": {"type": "integer", "minimum": 1},
                    "rmse": {"type": "number", "minimum": 0},
                    "bias": {"type": "number"},
                    "unit": {"type": "string", "minLength": 1},
                    "r2": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                    "notes": {"type": ["string", "null"]},
                },
            },
            "applicability": {
                "type": "object",
                "additionalProperties": False,
                "required": ["regions", "species"],
                "properties": {
                    "regions": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "uniqueItems": True,
                    },
                    "species": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "uniqueItems": True,
                    },
                    "age_min": {"type": ["integer", "null"], "minimum": 0},
                    "age_max": {"type": ["integer", "null"], "minimum": 0},
                    "height_min": {"type": ["number", "null"], "minimum": 0},
                    "height_max": {"type": ["number", "null"], "minimum": 0},
                    "notes": {"type": ["string", "null"]},
                },
            },
        },
    }


#: JSON Schema for one ``femic.efi.model.v1`` model card. Call
#: :func:`efi_model_schema` for a defensive copy.
EFI_MODEL_SCHEMA: dict[str, object] = _build_schema()


def efi_model_schema() -> dict[str, object]:
    """Return a defensive copy of the ``femic.efi.model.v1`` JSON Schema.

    Returns
    -------
    dict[str, object]
        A copy of the schema document, safe for a caller to mutate.
    """
    return copy.deepcopy(EFI_MODEL_SCHEMA)


@dataclass(frozen=True)
class EFITrainingData:
    """Training-data provenance for an EFI model card."""

    source_id: str
    source_version: str
    region: str
    plot_count: int
    species: tuple[str, ...] = ()
    period: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form."""
        return {
            "source_id": self.source_id,
            "source_version": self.source_version,
            "region": self.region,
            "plot_count": self.plot_count,
            "species": list(self.species),
            "period": self.period,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> EFITrainingData:
        """Validate and construct training data."""
        if not isinstance(payload, Mapping):
            raise EFIContractError("training must be a mapping")
        required = ("source_id", "source_version", "region", "plot_count")
        missing = [field for field in required if field not in payload]
        if missing:
            raise EFIContractError(f"missing training fields: {', '.join(missing)}")
        unknown = set(payload) - {
            "source_id",
            "source_version",
            "region",
            "plot_count",
            "species",
            "period",
            "notes",
        }
        if unknown:
            raise EFIContractError(
                f"unknown training fields: {', '.join(sorted(str(name) for name in unknown))}"
            )
        plot_count = _require_int(payload["plot_count"], "training.plot_count")
        if plot_count < 0:
            raise EFIContractError("training.plot_count must be non-negative")
        species = _require_text_list(
            payload.get("species", []), "training.species", allow_empty=True
        )
        period = payload.get("period")
        notes = payload.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise EFIContractError("training.notes must be a string or null")
        return cls(
            source_id=_require_text(payload["source_id"], "training.source_id"),
            source_version=_require_text(
                payload["source_version"], "training.source_version"
            ),
            region=_require_text(payload["region"], "training.region"),
            plot_count=plot_count,
            species=species,
            period=None if period is None else _require_text(period, "training.period"),
            notes=None if notes is None else str(notes),
        )


@dataclass(frozen=True)
class EFIValidation:
    """Validation evidence for an EFI model card."""

    design: str
    n: int
    rmse: float
    bias: float
    unit: str
    r2: float | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form."""
        return {
            "design": self.design,
            "n": self.n,
            "rmse": self.rmse,
            "bias": self.bias,
            "unit": self.unit,
            "r2": self.r2,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> EFIValidation:
        """Validate and construct validation evidence."""
        if not isinstance(payload, Mapping):
            raise EFIContractError("validation must be a mapping")
        required = ("design", "n", "rmse", "bias", "unit")
        missing = [field for field in required if field not in payload]
        if missing:
            raise EFIContractError(f"missing validation fields: {', '.join(missing)}")
        unknown = set(payload) - {"design", "n", "rmse", "bias", "unit", "r2", "notes"}
        if unknown:
            raise EFIContractError(
                f"unknown validation fields: {', '.join(sorted(str(name) for name in unknown))}"
            )
        n = _require_int(payload["n"], "validation.n")
        if n < 1:
            raise EFIContractError("validation.n must be at least 1")
        rmse = _require_number(payload["rmse"], "validation.rmse")
        if rmse < 0:
            raise EFIContractError("validation.rmse must be non-negative")
        r2 = payload.get("r2")
        r2_value = None if r2 is None else _require_number(r2, "validation.r2")
        if r2_value is not None and (r2_value < 0 or r2_value > 1):
            raise EFIContractError("validation.r2 must be between 0 and 1")
        notes = payload.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise EFIContractError("validation.notes must be a string or null")
        return cls(
            design=_require_text(payload["design"], "validation.design"),
            n=n,
            rmse=rmse,
            bias=_require_number(payload["bias"], "validation.bias"),
            unit=_require_text(payload["unit"], "validation.unit"),
            r2=r2_value,
            notes=None if notes is None else str(notes),
        )


@dataclass(frozen=True)
class EFIApplicability:
    """Applicability domain for an EFI model card."""

    regions: tuple[str, ...]
    species: tuple[str, ...]
    age_min: int | None = None
    age_max: int | None = None
    height_min: float | None = None
    height_max: float | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form."""
        return {
            "regions": list(self.regions),
            "species": list(self.species),
            "age_min": self.age_min,
            "age_max": self.age_max,
            "height_min": self.height_min,
            "height_max": self.height_max,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> EFIApplicability:
        """Validate and construct an applicability domain."""
        if not isinstance(payload, Mapping):
            raise EFIContractError("applicability must be a mapping")
        required = ("regions", "species")
        missing = [field for field in required if field not in payload]
        if missing:
            raise EFIContractError(
                f"missing applicability fields: {', '.join(missing)}"
            )
        unknown = set(payload) - {
            "regions",
            "species",
            "age_min",
            "age_max",
            "height_min",
            "height_max",
            "notes",
        }
        if unknown:
            raise EFIContractError(
                f"unknown applicability fields: {', '.join(sorted(str(name) for name in unknown))}"
            )
        regions = _require_text_list(
            payload["regions"], "applicability.regions", allow_empty=True
        )
        species = _require_text_list(
            payload["species"], "applicability.species", allow_empty=True
        )
        if not regions and not species:
            raise EFIContractError(
                "applicability must name at least one region or species"
            )
        age_min = payload.get("age_min")
        age_max = payload.get("age_max")
        age_min_value = (
            None if age_min is None else _require_int(age_min, "applicability.age_min")
        )
        age_max_value = (
            None if age_max is None else _require_int(age_max, "applicability.age_max")
        )
        if age_min_value is not None and age_min_value < 0:
            raise EFIContractError("applicability.age_min must be non-negative")
        if age_max_value is not None and age_max_value < 0:
            raise EFIContractError("applicability.age_max must be non-negative")
        if (
            age_min_value is not None
            and age_max_value is not None
            and age_min_value > age_max_value
        ):
            raise EFIContractError("applicability.age_min must not exceed age_max")
        height_min = payload.get("height_min")
        height_max = payload.get("height_max")
        height_min_value = (
            None
            if height_min is None
            else _require_number(height_min, "applicability.height_min")
        )
        height_max_value = (
            None
            if height_max is None
            else _require_number(height_max, "applicability.height_max")
        )
        if height_min_value is not None and height_min_value < 0:
            raise EFIContractError("applicability.height_min must be non-negative")
        if height_max_value is not None and height_max_value < 0:
            raise EFIContractError("applicability.height_max must be non-negative")
        if (
            height_min_value is not None
            and height_max_value is not None
            and height_min_value > height_max_value
        ):
            raise EFIContractError(
                "applicability.height_min must not exceed height_max"
            )
        notes = payload.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise EFIContractError("applicability.notes must be a string or null")
        return cls(
            regions=regions,
            species=species,
            age_min=age_min_value,
            age_max=age_max_value,
            height_min=height_min_value,
            height_max=height_max_value,
            notes=None if notes is None else str(notes),
        )


@dataclass(frozen=True)
class EFIApplicabilityCheck:
    """Result of checking a query against an applicability domain."""

    in_domain: bool
    reasons: tuple[str, ...]
    model_id: str
    model_version: str


@dataclass(frozen=True)
class EFIModelCard:
    """One validated ``femic.efi.model.v1`` model card."""

    model_id: str
    model_version: str
    attribute: str
    unit: str
    predictors: tuple[str, ...]
    training: EFITrainingData
    validation: EFIValidation
    applicability: EFIApplicability
    licence_id: str
    created_utc: str
    notes: str | None = None
    schema_version: str = EFI_MODEL_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the canonical dict form, including nested objects."""
        return {
            "schema_version": self.schema_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "attribute": self.attribute,
            "unit": self.unit,
            "predictors": list(self.predictors),
            "training": self.training.to_dict(),
            "validation": self.validation.to_dict(),
            "applicability": self.applicability.to_dict(),
            "licence_id": self.licence_id,
            "created_utc": self.created_utc,
            "notes": self.notes,
        }

    def applies_to(
        self,
        *,
        region: str | None = None,
        species: str | None = None,
        age: float | None = None,
        height: float | None = None,
    ) -> EFIApplicabilityCheck:
        """Check a query against the card's applicability domain.

        Parameters
        ----------
        region : str | None, optional
            Region or BEC label to test.
        species : str | None, optional
            Species label to test.
        age : float | None, optional
            Stand age in years.
        height : float | None, optional
            Stand or tree height in the card's unit.

        Returns
        -------
        EFIApplicabilityCheck
            ``in_domain`` is false when a restricted dimension is missing from
            the query or falls outside the domain. ``reasons`` explains each
            failure.
        """
        reasons: list[str] = []
        if self.applicability.regions:
            if region is None:
                reasons.append("region not provided")
            elif region not in self.applicability.regions:
                reasons.append(
                    f"region {region!r} not in {list(self.applicability.regions)!r}"
                )
        if self.applicability.species:
            if species is None:
                reasons.append("species not provided")
            elif species not in self.applicability.species:
                reasons.append(
                    f"species {species!r} not in {list(self.applicability.species)!r}"
                )
        if (
            self.applicability.age_min is not None
            or self.applicability.age_max is not None
        ):
            if age is None:
                reasons.append("age not provided")
            else:
                age_value = _require_number(age, "age")
                if (
                    self.applicability.age_min is not None
                    and age_value < self.applicability.age_min
                ):
                    reasons.append(
                        f"age {age_value} below {self.applicability.age_min}"
                    )
                if (
                    self.applicability.age_max is not None
                    and age_value > self.applicability.age_max
                ):
                    reasons.append(
                        f"age {age_value} above {self.applicability.age_max}"
                    )
        if (
            self.applicability.height_min is not None
            or self.applicability.height_max is not None
        ):
            if height is None:
                reasons.append("height not provided")
            else:
                height_value = _require_number(height, "height")
                if (
                    self.applicability.height_min is not None
                    and height_value < self.applicability.height_min
                ):
                    reasons.append(
                        f"height {height_value} below {self.applicability.height_min}"
                    )
                if (
                    self.applicability.height_max is not None
                    and height_value > self.applicability.height_max
                ):
                    reasons.append(
                        f"height {height_value} above {self.applicability.height_max}"
                    )
        return EFIApplicabilityCheck(
            in_domain=not reasons,
            reasons=tuple(reasons),
            model_id=self.model_id,
            model_version=self.model_version,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> EFIModelCard:
        """Validate and construct a model card from a mapping."""
        validate_efi_model_card(payload)
        return cls(
            model_id=_require_text(payload["model_id"], "model_id"),
            model_version=_require_text(payload["model_version"], "model_version"),
            attribute=_require_text(payload["attribute"], "attribute"),
            unit=_require_text(payload["unit"], "unit"),
            predictors=_require_text_list(
                payload["predictors"], "predictors", allow_empty=False
            ),
            training=EFITrainingData.from_dict(
                _require_mapping(payload["training"], "training")
            ),
            validation=EFIValidation.from_dict(
                _require_mapping(payload["validation"], "validation")
            ),
            applicability=EFIApplicability.from_dict(
                _require_mapping(payload["applicability"], "applicability")
            ),
            licence_id=_require_text(payload["licence_id"], "licence_id"),
            created_utc=_require_text(payload["created_utc"], "created_utc"),
            notes=None if payload.get("notes") is None else str(payload["notes"]),
        )


def validate_efi_model_card(payload: Mapping[str, object]) -> None:
    """Validate one model card against ``femic.efi.model.v1``.

    Parameters
    ----------
    payload : mapping[str, object]
        Candidate model card.

    Raises
    ------
    EFIContractError
        If the card is not a mapping, has unknown or missing fields, carries an
        unsupported attribute, has a unit that does not match the attribute,
        has duplicate or empty predictors, has invalid nested metadata, or has
        a validation unit that does not match the card unit.
    """
    if not isinstance(payload, Mapping):
        raise EFIContractError("EFI model card must be a mapping")
    unknown = set(payload) - EFI_ALLOWED_FIELDS
    if unknown:
        raise EFIContractError(
            f"unknown EFI model fields: {', '.join(sorted(str(name) for name in unknown))}"
        )
    missing = [field for field in EFI_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise EFIContractError(f"missing EFI model fields: {', '.join(missing)}")

    schema_version = _require_text(payload["schema_version"], "schema_version")
    if schema_version != EFI_MODEL_SCHEMA_VERSION:
        raise EFIContractError(f"schema_version must be {EFI_MODEL_SCHEMA_VERSION!r}")
    _require_text(payload["model_id"], "model_id")
    _require_text(payload["model_version"], "model_version")
    attribute = _require_text(payload["attribute"], "attribute")
    if attribute not in EFI_ATTRIBUTE_UNITS:
        supported = ", ".join(sorted(EFI_ATTRIBUTE_UNITS))
        raise EFIContractError(
            f"attribute must be one of: {supported}; got {attribute!r}"
        )
    unit = _require_text(payload["unit"], "unit")
    expected_unit = EFI_ATTRIBUTE_UNITS[attribute]
    if expected_unit and unit != expected_unit:
        raise EFIContractError(
            f"unit for {attribute!r} must be {expected_unit!r}; got {unit!r}"
        )
    _require_text_list(payload["predictors"], "predictors", allow_empty=False)

    training = EFITrainingData.from_dict(
        _require_mapping(payload["training"], "training")
    )
    validation = EFIValidation.from_dict(
        _require_mapping(payload["validation"], "validation")
    )
    applicability = EFIApplicability.from_dict(
        _require_mapping(payload["applicability"], "applicability")
    )
    if validation.unit != unit:
        raise EFIContractError(
            f"validation.unit {validation.unit!r} must match card unit {unit!r}"
        )
    if applicability.regions and training.region not in applicability.regions:
        raise EFIContractError("training.region must be in applicability.regions")
    _require_text(payload["licence_id"], "licence_id")
    _require_timestamp(payload["created_utc"], "created_utc")
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise EFIContractError("notes must be a string or null")


def read_efi_model_card(path: Path) -> EFIModelCard:
    """Read and validate one EFI model card from JSON.

    Parameters
    ----------
    path : pathlib.Path
        ``.json`` file containing one model card.

    Returns
    -------
    EFIModelCard
        The validated model card.

    Raises
    ------
    EFIContractError
        If the suffix is unsupported or the card is invalid.
    """
    if path.suffix.lower() != ".json":
        raise EFIContractError("EFI model cards must be JSON")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise EFIContractError(f"{path} must contain a model-card object")
    return EFIModelCard.from_dict(payload)


def write_efi_model_card(path: Path, card: EFIModelCard) -> None:
    """Write one validated EFI model card to JSON.

    Parameters
    ----------
    path : pathlib.Path
        Destination ``.json`` path.
    card : EFIModelCard
        Model card to write.

    Raises
    ------
    EFIContractError
        If the suffix is unsupported or the card is invalid.
    """
    if path.suffix.lower() != ".json":
        raise EFIContractError("EFI model cards must be JSON")
    validate_efi_model_card(card.to_dict())
    path.write_text(
        json.dumps(card.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def summarize_efi_model_card(card: EFIModelCard) -> dict[str, object]:
    """Return a compact, provenance-bearing summary of a model card.

    Parameters
    ----------
    card : EFIModelCard
        Validated model card.

    Returns
    -------
    dict[str, object]
        Model identity, target, predictors, training source and region,
        validation design and accuracy, applicability domain, and licence.
    """
    validate_efi_model_card(card.to_dict())
    return {
        "schema_version": EFI_MODEL_SCHEMA_VERSION,
        "model_id": card.model_id,
        "model_version": card.model_version,
        "attribute": card.attribute,
        "unit": card.unit,
        "predictors": list(card.predictors),
        "training": card.training.to_dict(),
        "validation": card.validation.to_dict(),
        "applicability": card.applicability.to_dict(),
        "licence_id": card.licence_id,
        "created_utc": card.created_utc,
    }


def annotate_attribute_rows(
    rows: Sequence[Mapping[str, object]], card: EFIModelCard
) -> list[dict[str, object]]:
    """Attach model metadata to attribute rows.

    Parameters
    ----------
    rows : sequence[mapping[str, object]]
        Attribute rows to annotate. They are copied, not mutated.
    card : EFIModelCard
        Model card to attach.

    Returns
    -------
    list[dict[str, object]]
        Copies of the rows with ``model_id``, ``model_version``,
        ``model_attribute``, ``model_unit``, ``model_rmse``, ``model_bias``,
        ``model_licence_id``, and ``model_applicability`` fields.

    Raises
    ------
    EFIContractError
        If a row is not a mapping or the card is invalid.
    """
    validate_efi_model_card(card.to_dict())
    metadata: dict[str, object] = {
        "model_id": card.model_id,
        "model_version": card.model_version,
        "model_attribute": card.attribute,
        "model_unit": card.unit,
        "model_rmse": card.validation.rmse,
        "model_bias": card.validation.bias,
        "model_licence_id": card.licence_id,
        "model_applicability": card.applicability.to_dict(),
    }
    annotated: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise EFIContractError("attribute rows must be mappings")
        annotated_row = dict(row)
        annotated_row.update(metadata)
        annotated.append(annotated_row)
    return annotated
