"""Annotate FEMIC attribute tables with an EFI model card.

This is the file-level seam between ``femic.efi.model.v1`` and the attribute
tables produced by an instance or a downstream synthesis workflow. It attaches
model provenance and an explicit applicability decision to every row. It does
not apply a model prediction or change a curve.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from femic.contracts.efi import EFIModelCard, read_efi_model_card
from femic.efi.application import EFIApplicationError

EFI_ATTRIBUTE_TABLE_SCHEMA_VERSION = "femic.efi.attribute_table.v1"

_DOMAIN_POLICIES = frozenset({"flag", "drop", "require"})
_SUPPORTED_SUFFIXES = frozenset({".csv", ".parquet", ".feather"})


@dataclass(frozen=True, slots=True)
class EFIAttributeAnnotationResult:
    """Summary of one attribute-table annotation run."""

    input_path: Path
    output_path: Path
    summary_path: Path | None
    model_id: str
    model_version: str
    attribute: str
    row_count: int
    rows_written: int
    in_domain_count: int
    out_of_domain_count: int
    domain_policy: str
    columns_added: tuple[str, ...]


def _read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".feather":
        return pd.read_feather(path)
    raise EFIApplicationError(f"unsupported attribute-table suffix: {path.suffix!r}")


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(path, index=False)
    elif suffix == ".parquet":
        frame.to_parquet(path, index=False)
    elif suffix == ".feather":
        frame.reset_index(drop=True).to_feather(path)
    else:
        raise EFIApplicationError(
            f"unsupported attribute-table suffix: {path.suffix!r}"
        )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _row_value(row: Mapping[object, object], column: str | None) -> object:
    if column is None:
        return None
    return row.get(column)


def _metadata(card: EFIModelCard) -> dict[str, object]:
    return {
        "model_card_schema_version": card.schema_version,
        "model_id": card.model_id,
        "model_version": card.model_version,
        "model_attribute": card.attribute,
        "model_unit": card.unit,
        "model_rmse": card.validation.rmse,
        "model_bias": card.validation.bias,
        "model_licence_id": card.licence_id,
        "model_applicability": json.dumps(card.applicability.to_dict(), sort_keys=True),
    }


def annotate_attribute_table(
    input_path: str | Path,
    card_path: str | Path,
    output_path: str | Path,
    *,
    summary_path: str | Path | None = None,
    domain_policy: str = "flag",
    region_column: str | None = "region",
    species_column: str | None = "species",
    age_column: str | None = "age",
    height_column: str | None = "height",
) -> EFIAttributeAnnotationResult:
    """Attach an EFI model card and applicability decision to an attribute table.

    Parameters
    ----------
    input_path:
        CSV, Parquet, or Feather attribute table.
    card_path:
        ``femic.efi.model.v1`` JSON model card.
    output_path:
        Destination table. The suffix selects CSV, Parquet, or Feather.
    summary_path:
        Optional JSON summary path.
    domain_policy:
        ``flag`` keeps every row and writes ``model_in_domain`` /
        ``model_domain_reasons``; ``drop`` omits out-of-domain rows; ``require``
        raises on the first out-of-domain row.
    region_column, species_column, age_column, height_column:
        Row columns used for the applicability check. Set a column to ``None``
        when the table does not carry that dimension.

    Returns
    -------
    EFIAttributeAnnotationResult
        Paths, row counts, and the model identity.

    Raises
    ------
    EFIApplicationError
        If the card, input, output suffix, policy, or domain fails.
    """
    policy = domain_policy.strip().lower()
    if policy not in _DOMAIN_POLICIES:
        raise EFIApplicationError(
            f"domain_policy must be one of: {', '.join(sorted(_DOMAIN_POLICIES))}"
        )
    source = Path(input_path)
    output = Path(output_path)
    if source.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise EFIApplicationError(
            f"unsupported input attribute-table suffix: {source.suffix!r}"
        )
    if output.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise EFIApplicationError(
            f"unsupported output attribute-table suffix: {output.suffix!r}"
        )
    if not source.is_file():
        raise EFIApplicationError(f"attribute table does not exist: {source}")

    card = read_efi_model_card(Path(card_path))
    frame = _read_table(source)
    metadata = _metadata(card)
    added_columns = tuple(metadata) + ("model_in_domain", "model_domain_reasons")
    output_columns = list(frame.columns) + list(added_columns)
    rows: list[dict[str, object]] = []
    in_domain_count = 0
    out_of_domain_count = 0

    for row_number, record in enumerate(frame.to_dict("records"), start=1):
        check = card.applies_to(
            region=_optional_text(_row_value(record, region_column)),
            species=_optional_text(_row_value(record, species_column)),
            age=_optional_float(_row_value(record, age_column)),
            height=_optional_float(_row_value(record, height_column)),
        )
        if check.in_domain:
            in_domain_count += 1
        else:
            out_of_domain_count += 1
            if policy == "require":
                reasons = "; ".join(check.reasons)
                raise EFIApplicationError(
                    f"row {row_number} is outside model {card.model_id!r}: {reasons}"
                )
            if policy == "drop":
                continue
        annotated: dict[str, object] = {
            str(key): value for key, value in record.items()
        }
        annotated.update(metadata)
        annotated["model_in_domain"] = check.in_domain
        annotated["model_domain_reasons"] = json.dumps(list(check.reasons))
        rows.append(annotated)

    result = pd.DataFrame.from_records(rows, columns=output_columns)
    _write_table(result, output)
    summary = {
        "schema_version": EFI_ATTRIBUTE_TABLE_SCHEMA_VERSION,
        "model_card_schema_version": card.schema_version,
        "model_id": card.model_id,
        "model_version": card.model_version,
        "attribute": card.attribute,
        "unit": card.unit,
        "input_path": str(source),
        "output_path": str(output),
        "row_count": len(frame),
        "rows_written": len(result),
        "in_domain_count": in_domain_count,
        "out_of_domain_count": out_of_domain_count,
        "domain_policy": policy,
        "columns_added": list(added_columns),
    }
    summary_file = None if summary_path is None else Path(summary_path)
    if summary_file is not None:
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return EFIAttributeAnnotationResult(
        input_path=source,
        output_path=output,
        summary_path=summary_file,
        model_id=card.model_id,
        model_version=card.model_version,
        attribute=card.attribute,
        row_count=len(frame),
        rows_written=len(result),
        in_domain_count=in_domain_count,
        out_of_domain_count=out_of_domain_count,
        domain_policy=policy,
        columns_added=added_columns,
    )
