"""Apply linear EFI attribute models to row-wise metrics.

This module is the execution layer above ``femic.efi.model.v1``. A model card
describes the claim; a coefficients document supplies the linear form; this
module predicts, checks the applicability domain, and backtests against
observed values.

The linear form is intentionally simple. It is a transport for published or
project coefficients, not a new statistical method.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from femic.contracts.efi import (
    EFI_ATTRIBUTE_UNITS,
    EFIContractError,
    EFIModelCard,
    read_efi_model_card,
)

EFI_COEFFICIENTS_SCHEMA_VERSION = "femic.efi.coefficients.v1"

_REQUIRED_COEFFICIENT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "model_id",
    "model_version",
    "attribute",
    "unit",
    "intercept",
    "coefficients",
)
_ALLOWED_COEFFICIENT_FIELDS: frozenset[str] = frozenset(_REQUIRED_COEFFICIENT_FIELDS)


class EFIApplicationError(RuntimeError):
    """Raised when an EFI model cannot be loaded, applied, or backtested."""


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    """Return a mapping, or raise an application error."""
    if not isinstance(value, Mapping):
        raise EFIApplicationError(f"{field} must be a mapping")
    return value


def _require_text(value: object, field: str) -> str:
    """Return a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise EFIApplicationError(f"{field} must be a non-empty string")
    return value.strip()


def _require_number(value: object, field: str) -> float:
    """Return a finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EFIApplicationError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise EFIApplicationError(f"{field} must be finite")
    return number


@dataclass(frozen=True)
class LinearEFIModel:
    """A model card plus a linear predictor.

    Attributes
    ----------
    card : EFIModelCard
        Validated model card that defines the target, predictors, accuracy, and
        applicability domain.
    intercept : float
        Model intercept.
    coefficients : dict[str, float]
        Predictor coefficients, keyed by the card's predictor names.
    """

    card: EFIModelCard
    intercept: float
    coefficients: dict[str, float]

    def predict(self, metrics: Mapping[str, float]) -> float:
        """Predict one value from a mapping of predictor metrics.

        Parameters
        ----------
        metrics : mapping[str, float]
            Predictor values keyed by the card's predictor names.

        Returns
        -------
        float
            ``intercept + sum(coefficient * metric)``.

        Raises
        ------
        EFIApplicationError
            If a predictor is missing or non-finite.
        """
        total = self.intercept
        for predictor, coefficient in self.coefficients.items():
            if predictor not in metrics:
                raise EFIApplicationError(
                    f"missing predictor {predictor!r} for model {self.card.model_id!r}"
                )
            total += coefficient * _require_number(metrics[predictor], predictor)
        return total


def load_linear_efi_model(card_path: Path, coefficients_path: Path) -> LinearEFIModel:
    """Load and validate a model card and its coefficients.

    Parameters
    ----------
    card_path : pathlib.Path
        ``femic.efi.model.v1`` JSON card.
    coefficients_path : pathlib.Path
        ``femic.efi.coefficients.v1`` JSON document.

    Returns
    -------
    LinearEFIModel
        The validated model.

    Raises
    ------
    EFIApplicationError
        If the coefficients document is malformed, its identity does not match
        the card, its predictor set does not match the card, or the card is
        invalid.
    """
    try:
        card = read_efi_model_card(card_path)
    except EFIContractError as exc:
        raise EFIApplicationError(f"invalid model card: {exc}") from exc

    if coefficients_path.suffix.lower() != ".json":
        raise EFIApplicationError("coefficients must be JSON")
    payload = _require_mapping(
        json.loads(coefficients_path.read_text(encoding="utf-8")),
        "coefficients",
    )
    unknown = set(payload) - _ALLOWED_COEFFICIENT_FIELDS
    if unknown:
        raise EFIApplicationError(
            f"unknown coefficient fields: {', '.join(sorted(str(name) for name in unknown))}"
        )
    missing = [field for field in _REQUIRED_COEFFICIENT_FIELDS if field not in payload]
    if missing:
        raise EFIApplicationError(f"missing coefficient fields: {', '.join(missing)}")
    schema_version = _require_text(payload["schema_version"], "schema_version")
    if schema_version != EFI_COEFFICIENTS_SCHEMA_VERSION:
        raise EFIApplicationError(
            f"coefficients schema_version must be {EFI_COEFFICIENTS_SCHEMA_VERSION!r}"
        )
    if _require_text(payload["model_id"], "model_id") != card.model_id:
        raise EFIApplicationError("coefficient model_id does not match the card")
    if _require_text(payload["model_version"], "model_version") != card.model_version:
        raise EFIApplicationError("coefficient model_version does not match the card")
    attribute = _require_text(payload["attribute"], "attribute")
    if attribute != card.attribute:
        raise EFIApplicationError("coefficient attribute does not match the card")
    unit = _require_text(payload["unit"], "unit")
    if unit != card.unit:
        raise EFIApplicationError("coefficient unit does not match the card")

    raw_coefficients = _require_mapping(payload["coefficients"], "coefficients")
    coefficients: dict[str, float] = {}
    for predictor, value in raw_coefficients.items():
        name = _require_text(predictor, "coefficients key")
        coefficients[name] = _require_number(value, f"coefficient {name!r}")
    if set(coefficients) != set(card.predictors):
        raise EFIApplicationError(
            "coefficient predictors must exactly match the card predictors"
        )
    intercept = _require_number(payload["intercept"], "intercept")
    expected_unit = EFI_ATTRIBUTE_UNITS[card.attribute]
    if expected_unit and unit != expected_unit:
        raise EFIApplicationError(
            f"unit for {card.attribute!r} must be {expected_unit!r}"
        )
    return LinearEFIModel(card=card, intercept=intercept, coefficients=coefficients)


def _row_predictors(
    row: Mapping[str, object],
    model: LinearEFIModel,
    predictor_columns: Mapping[str, str] | None,
    row_number: int,
) -> dict[str, float]:
    """Collect and validate the predictor values for one row."""
    values: dict[str, float] = {}
    for predictor in model.coefficients:
        column = (
            predictor_columns[predictor]
            if predictor_columns is not None and predictor in predictor_columns
            else predictor
        )
        if column not in row:
            raise EFIApplicationError(
                f"row {row_number} is missing predictor column {column!r}"
            )
        values[predictor] = _require_number(
            row[column], f"row {row_number} column {column!r}"
        )
    return values


def _row_domain(
    row: Mapping[str, object], model: LinearEFIModel
) -> tuple[bool, tuple[str, ...]]:
    """Check one row against the card's applicability domain."""
    region = row.get("region")
    species = row.get("species")
    age = row.get("age")
    height = row.get("height", row.get("height_m"))
    check = model.card.applies_to(
        region=None if region is None else str(region),
        species=None if species is None else str(species),
        age=None if age is None else _require_number(age, "age"),
        height=None if height is None else _require_number(height, "height"),
    )
    return check.in_domain, check.reasons


def apply_linear_model(
    rows: Sequence[Mapping[str, object]],
    model: LinearEFIModel,
    *,
    predictor_columns: Mapping[str, str] | None = None,
    require_domain: bool = False,
    out_of_domain: str = "flag",
) -> list[dict[str, object]]:
    """Apply a linear model to row-wise metrics.

    Parameters
    ----------
    rows : sequence[mapping[str, object]]
        Attribute rows. The model's predictor names are used as column names
        unless ``predictor_columns`` maps them to different columns.
    model : LinearEFIModel
        Loaded model.
    predictor_columns : mapping[str, str] | None, optional
        Predictor name to row-column mapping.
    require_domain : bool, optional
        If true, an out-of-domain row raises instead of being flagged.
    out_of_domain : {"flag", "drop"}, optional
        ``"flag"`` keeps the row with ``model_in_domain`` false; ``"drop"``
        omits it. ``require_domain`` takes precedence.

    Returns
    -------
    list[dict[str, object]]
        Copies of the input rows with ``predicted_<attribute>``, model
        provenance, ``model_in_domain``, and ``model_domain_reasons`` fields.

    Raises
    ------
    EFIApplicationError
        If a row is not a mapping, a predictor is missing or non-finite, the
        out-of-domain policy is unknown, or a domain failure is required to
        raise.
    """
    if out_of_domain not in {"flag", "drop"}:
        raise EFIApplicationError("out_of_domain must be 'flag' or 'drop'")
    if predictor_columns is not None:
        missing = [
            predictor
            for predictor in model.coefficients
            if predictor not in predictor_columns
        ]
        if missing:
            raise EFIApplicationError(
                f"predictor_columns is missing: {', '.join(missing)}"
            )

    predictions: list[dict[str, object]] = []
    predicted_field = f"predicted_{model.card.attribute}"
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise EFIApplicationError(f"row {row_number} must be a mapping")
        metrics = _row_predictors(row, model, predictor_columns, row_number)
        in_domain, reasons = _row_domain(row, model)
        if not in_domain and require_domain:
            raise EFIApplicationError(
                f"row {row_number} is out of domain: {'; '.join(reasons)}"
            )
        if not in_domain and out_of_domain == "drop":
            continue
        output = dict(row)
        output[predicted_field] = model.predict(metrics)
        output["model_id"] = model.card.model_id
        output["model_version"] = model.card.model_version
        output["model_attribute"] = model.card.attribute
        output["model_unit"] = model.card.unit
        output["model_rmse"] = model.card.validation.rmse
        output["model_bias"] = model.card.validation.bias
        output["model_licence_id"] = model.card.licence_id
        output["model_in_domain"] = in_domain
        output["model_domain_reasons"] = list(reasons)
        predictions.append(output)
    return predictions


def backtest_linear_model(
    rows: Sequence[Mapping[str, object]],
    model: LinearEFIModel,
    *,
    observed_column: str,
    predictor_columns: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Backtest a linear model against observed values.

    Parameters
    ----------
    rows : sequence[mapping[str, object]]
        Attribute rows with predictor columns and an observed target.
    model : LinearEFIModel
        Loaded model.
    observed_column : str
        Row column holding the observed target in ``model.card.unit``.
    predictor_columns : mapping[str, str] | None, optional
        Predictor name to row-column mapping.

    Returns
    -------
    dict[str, object]
        Sample size, in/out-of-domain counts, bias, RMSE, MAE, R-squared when
        defined, and the observed/predicted ranges. Out-of-domain rows are
        counted but excluded from the metrics.

    Raises
    ------
    EFIApplicationError
        If no in-domain row has an observed value, or an observed value is
        non-numeric.
    """
    predictions = apply_linear_model(
        rows,
        model,
        predictor_columns=predictor_columns,
        out_of_domain="flag",
    )
    in_domain = [row for row in predictions if row["model_in_domain"] is True]
    out_of_domain_count = len(predictions) - len(in_domain)
    pairs: list[tuple[float, float]] = []
    predicted_field = f"predicted_{model.card.attribute}"
    for row_number, row in enumerate(in_domain, start=1):
        if observed_column not in row:
            raise EFIApplicationError(
                f"in-domain row {row_number} is missing observed column "
                f"{observed_column!r}"
            )
        observed = _require_number(row[observed_column], observed_column)
        predicted = _require_number(row[predicted_field], predicted_field)
        pairs.append((observed, predicted))
    if not pairs:
        raise EFIApplicationError(
            "backtest has no in-domain rows with an observed value"
        )

    errors = [predicted - observed for observed, predicted in pairs]
    bias = sum(errors) / len(errors)
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors))
    mae = sum(abs(error) for error in errors) / len(errors)
    observed_values = [observed for observed, _ in pairs]
    predicted_values = [predicted for _, predicted in pairs]
    mean_observed = sum(observed_values) / len(observed_values)
    ss_total = sum((value - mean_observed) ** 2 for value in observed_values)
    ss_residual = sum(error * error for error in errors)
    r2 = None if ss_total == 0 else 1.0 - (ss_residual / ss_total)
    return {
        "model_id": model.card.model_id,
        "model_version": model.card.model_version,
        "attribute": model.card.attribute,
        "unit": model.card.unit,
        "n": len(pairs),
        "in_domain_count": len(pairs),
        "out_of_domain_count": out_of_domain_count,
        "bias": bias,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "observed_min": min(observed_values),
        "observed_max": max(observed_values),
        "predicted_min": min(predicted_values),
        "predicted_max": max(predicted_values),
    }
