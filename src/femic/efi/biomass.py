"""Remote-sensing biomass yield curves and declared carbon conversion.

This module carries published RSYC curves (Tompalski et al. 2024, 2025) as data.
It evaluates the published nonlinear form, checks the age domain, and applies an
explicit carbon fraction. It does not fit a new model and does not copy the R
package code.

The curve form is::

    AGB = b1 * exp(-b4 * age) * (1 - exp(-b2 * age)) ** b3

where AGB is aboveground dry biomass in tonnes per hectare. The optional volume
curve uses the same form and is kept separate so biomass and volume are never
summed into the same account.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

BIOMASS_CURVE_SCHEMA_VERSION = "femic.efi.biomass_curve.v1"

_CURVE_FIELDS = frozenset(
    {"model_id", "model_version", "response", "unit", "b1", "b2", "b3", "b4"}
)
_REQUIRED_FAMILY_FIELDS = (
    "schema_version",
    "source_id",
    "source_url",
    "licence_id",
    "curves",
)
_REQUIRED_CURVE_FIELDS = (
    "curve_id",
    "species",
    "region",
    "ecodistrict",
    "age_min",
    "age_max",
    "carbon_fraction",
    "carbon_fraction_source",
    "agb",
)
_CURVE_RECORD_FIELDS = frozenset(_REQUIRED_CURVE_FIELDS + ("volume", "validation_note"))


class BiomassCurveError(ValueError):
    """Raised when a biomass curve document or evaluation is invalid."""


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BiomassCurveError(f"{field} must be a non-empty string")
    return value.strip()


def _require_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BiomassCurveError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise BiomassCurveError(f"{field} must be finite")
    return number


def _require_mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BiomassCurveError(f"{field} must be a mapping")
    return value


@dataclass(frozen=True, slots=True)
class RSYCCurve:
    """One published RSYC response curve.

    Attributes
    ----------
    model_id : str
        Stable model identifier.
    model_version : str
        Published model version.
    response : str
        ``agb`` or ``volume``.
    unit : str
        ``t_ha`` for AGB or ``m3_ha`` for volume.
    b1, b2, b3, b4 : float
        Published equation parameters.
    """

    model_id: str
    model_version: str
    response: str
    unit: str
    b1: float
    b2: float
    b3: float
    b4: float

    def evaluate(self, age: float) -> float:
        """Evaluate the curve at a stand age.

        Parameters
        ----------
        age : float
            Stand age in years. Must be finite and greater than zero.

        Returns
        -------
        float
            Response in the curve unit.

        Raises
        ------
        BiomassCurveError
            If the age is not finite or not positive.
        """
        value = _require_number(age, "age")
        if value <= 0:
            raise BiomassCurveError("age must be positive")
        return (
            self.b1
            * math.exp(-self.b4 * value)
            * (1.0 - math.exp(-self.b2 * value)) ** self.b3
        )


@dataclass(frozen=True, slots=True)
class BiomassCurve:
    """One species/ecodistrict biomass curve with a declared carbon fraction.

    Attributes
    ----------
    curve_id : str
        Stable curve identifier.
    species : str
        Species code, for example ``PSEU.MEN``.
    region : str
        Broad region.
    ecodistrict : str
        Ecodistrict name.
    age_min, age_max : float
        Accepted stand-age domain.
    agb : RSYCCurve
        Aboveground biomass curve in ``t_ha``.
    volume : RSYCCurve or None
        Optional volume curve in ``m3_ha`` for comparison.
    carbon_fraction : float
        Declared dry-biomass carbon fraction in [0, 1].
    carbon_fraction_source : str
        Source for the carbon fraction.
    source_id, source_url, licence_id : str
        Family provenance.
    validation_note : str or None
        Optional validation note.
    """

    curve_id: str
    species: str
    region: str
    ecodistrict: str
    age_min: float
    age_max: float
    agb: RSYCCurve
    volume: RSYCCurve | None
    carbon_fraction: float
    carbon_fraction_source: str
    source_id: str
    source_url: str
    licence_id: str
    validation_note: str | None = None

    def _check_age(self, age: float) -> float:
        value = _require_number(age, "age")
        if value < self.age_min or value > self.age_max:
            raise BiomassCurveError(
                f"age {value} is outside the curve domain [{self.age_min}, {self.age_max}]"
            )
        return value

    def agb_t_ha(self, age: float) -> float:
        """Return aboveground biomass in tonnes per hectare."""
        return self.agb.evaluate(self._check_age(age))

    def volume_m3_ha(self, age: float) -> float | None:
        """Return volume in cubic metres per hectare, or ``None`` when absent."""
        checked = self._check_age(age)
        return None if self.volume is None else self.volume.evaluate(checked)

    def carbon_t_c_ha(self, age: float) -> float:
        """Return biomass carbon in tonnes of carbon per hectare."""
        return self.agb_t_ha(age) * self.carbon_fraction

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly curve record."""
        return {
            "curve_id": self.curve_id,
            "species": self.species,
            "region": self.region,
            "ecodistrict": self.ecodistrict,
            "age_min": self.age_min,
            "age_max": self.age_max,
            "agb": asdict(self.agb),
            "volume": None if self.volume is None else asdict(self.volume),
            "carbon_fraction": self.carbon_fraction,
            "carbon_fraction_source": self.carbon_fraction_source,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "licence_id": self.licence_id,
            "validation_note": self.validation_note,
        }


@dataclass(frozen=True, slots=True)
class BiomassCurveFamily:
    """A validated family of RSYC biomass curves."""

    source_id: str
    source_url: str
    licence_id: str
    curves: tuple[BiomassCurve, ...]

    def select(
        self,
        *,
        species: str | None = None,
        region: str | None = None,
        ecodistrict: str | None = None,
    ) -> tuple[BiomassCurve, ...]:
        """Select curves by species, region, and ecodistrict.

        Returns
        -------
        tuple of BiomassCurve
            Matching curves. Empty when nothing matches.
        """
        selected = list(self.curves)
        if species is not None:
            selected = [curve for curve in selected if curve.species == species]
        if region is not None:
            selected = [curve for curve in selected if curve.region == region]
        if ecodistrict is not None:
            selected = [curve for curve in selected if curve.ecodistrict == ecodistrict]
        return tuple(selected)

    def select_one(
        self,
        *,
        species: str | None = None,
        region: str | None = None,
        ecodistrict: str | None = None,
    ) -> BiomassCurve:
        """Select exactly one curve or raise a clear error."""
        selected = self.select(species=species, region=region, ecodistrict=ecodistrict)
        if not selected:
            raise BiomassCurveError(
                "no curve matches the requested species/region/ecodistrict"
            )
        if len(selected) > 1:
            ids = ", ".join(curve.curve_id for curve in selected)
            raise BiomassCurveError(
                f"multiple curves match; narrow the selection: {ids}"
            )
        return selected[0]


def _parse_curve(payload: Mapping[str, Any], field: str) -> RSYCCurve:
    unknown = set(payload) - _CURVE_FIELDS
    if unknown:
        raise BiomassCurveError(
            f"{field} has unknown fields: {', '.join(sorted(unknown))}"
        )
    missing = [name for name in _CURVE_FIELDS if name not in payload]
    if missing:
        raise BiomassCurveError(f"{field} is missing fields: {', '.join(missing)}")
    response = _require_text(payload["response"], f"{field}.response")
    unit = _require_text(payload["unit"], f"{field}.unit")
    expected_unit = {"agb": "t_ha", "volume": "m3_ha"}.get(response)
    if expected_unit is None:
        raise BiomassCurveError(f"{field}.response must be 'agb' or 'volume'")
    if unit != expected_unit:
        raise BiomassCurveError(
            f"{field}.unit must be {expected_unit!r} for response {response!r}"
        )
    b1 = _require_number(payload["b1"], f"{field}.b1")
    b2 = _require_number(payload["b2"], f"{field}.b2")
    b3 = _require_number(payload["b3"], f"{field}.b3")
    b4 = _require_number(payload["b4"], f"{field}.b4")
    if min(b1, b2, b3) <= 0:
        raise BiomassCurveError(f"{field} b1, b2, and b3 must be positive")
    if b4 < 0:
        raise BiomassCurveError(f"{field}.b4 must be non-negative")
    return RSYCCurve(
        model_id=_require_text(payload["model_id"], f"{field}.model_id"),
        model_version=_require_text(payload["model_version"], f"{field}.model_version"),
        response=response,
        unit=unit,
        b1=b1,
        b2=b2,
        b3=b3,
        b4=b4,
    )


def load_biomass_curves(path: str | Path) -> BiomassCurveFamily:
    """Load and validate a ``femic.efi.biomass_curve.v1`` document.

    Parameters
    ----------
    path : str or Path
        JSON curve document.

    Returns
    -------
    BiomassCurveFamily
        Validated curves and family provenance.

    Raises
    ------
    BiomassCurveError
        If the document is malformed, a required field is missing, a curve has
        an invalid domain, or the carbon fraction/source is absent.
    """
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BiomassCurveError(
            f"biomass curve document does not exist: {source}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise BiomassCurveError(
            f"biomass curve document is not JSON: {source}"
        ) from exc
    document = _require_mapping(payload, "biomass curve document")
    unknown = set(document) - set(_REQUIRED_FAMILY_FIELDS) - {"notes"}
    if unknown:
        raise BiomassCurveError(f"unknown family fields: {', '.join(sorted(unknown))}")
    missing = [name for name in _REQUIRED_FAMILY_FIELDS if name not in document]
    if missing:
        raise BiomassCurveError(f"missing family fields: {', '.join(missing)}")
    if (
        _require_text(document["schema_version"], "schema_version")
        != BIOMASS_CURVE_SCHEMA_VERSION
    ):
        raise BiomassCurveError(
            f"schema_version must be {BIOMASS_CURVE_SCHEMA_VERSION!r}"
        )
    source_id = _require_text(document["source_id"], "source_id")
    source_url = _require_text(document["source_url"], "source_url")
    licence_id = _require_text(document["licence_id"], "licence_id")
    raw_curves = document["curves"]
    if not isinstance(raw_curves, list) or not raw_curves:
        raise BiomassCurveError("curves must be a non-empty list")
    curves: list[BiomassCurve] = []
    for index, item in enumerate(raw_curves):
        field = f"curves[{index}]"
        record = _require_mapping(item, field)
        unknown_curve = set(record) - _CURVE_RECORD_FIELDS
        if unknown_curve:
            raise BiomassCurveError(
                f"{field} has unknown fields: {', '.join(sorted(unknown_curve))}"
            )
        missing_curve = [name for name in _REQUIRED_CURVE_FIELDS if name not in record]
        if missing_curve:
            raise BiomassCurveError(
                f"{field} is missing fields: {', '.join(missing_curve)}"
            )
        carbon_fraction = _require_number(
            record["carbon_fraction"], f"{field}.carbon_fraction"
        )
        if not 0 <= carbon_fraction <= 1:
            raise BiomassCurveError(f"{field}.carbon_fraction must be in [0, 1]")
        age_min = _require_number(record["age_min"], f"{field}.age_min")
        age_max = _require_number(record["age_max"], f"{field}.age_max")
        if age_min <= 0 or age_max < age_min:
            raise BiomassCurveError(f"{field} has an invalid age domain")
        agb = _parse_curve(
            _require_mapping(record["agb"], f"{field}.agb"), f"{field}.agb"
        )
        if agb.response != "agb":
            raise BiomassCurveError(f"{field}.agb response must be 'agb'")
        volume = None
        if record.get("volume") is not None:
            volume = _parse_curve(
                _require_mapping(record["volume"], f"{field}.volume"), f"{field}.volume"
            )
            if volume.response != "volume":
                raise BiomassCurveError(f"{field}.volume response must be 'volume'")
        curves.append(
            BiomassCurve(
                curve_id=_require_text(record["curve_id"], f"{field}.curve_id"),
                species=_require_text(record["species"], f"{field}.species"),
                region=_require_text(record["region"], f"{field}.region"),
                ecodistrict=_require_text(
                    record["ecodistrict"], f"{field}.ecodistrict"
                ),
                age_min=age_min,
                age_max=age_max,
                agb=agb,
                volume=volume,
                carbon_fraction=carbon_fraction,
                carbon_fraction_source=_require_text(
                    record["carbon_fraction_source"], f"{field}.carbon_fraction_source"
                ),
                source_id=source_id,
                source_url=source_url,
                licence_id=licence_id,
                validation_note=(
                    None
                    if record.get("validation_note") is None
                    else _require_text(
                        record["validation_note"], f"{field}.validation_note"
                    )
                ),
            )
        )
    if len({curve.curve_id for curve in curves}) != len(curves):
        raise BiomassCurveError("curve_id values must be unique")
    return BiomassCurveFamily(
        source_id=source_id,
        source_url=source_url,
        licence_id=licence_id,
        curves=tuple(curves),
    )
