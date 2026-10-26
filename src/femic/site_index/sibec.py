"""SIBEC site-index estimates from the public BC workbook.

SIBEC provides mean plot site index and standard error by BEC unit, site
series, and tree species. This module turns the public workbook into a tidy
table and aggregates site-series rows to the BEC-unit/species grain used by
VRI and VDYP reconciliation.

This is an ingest adapter. It does not estimate or fit site index.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

SIBEC_SCHEMA_VERSION = "femic.sibec.v1"
SIBEC_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "region",
    "bgc_unit",
    "site_series",
    "site_association",
    "species",
    "plot_count",
    "mean_site_index",
    "standard_error",
)

_COLUMN_ALIASES: dict[str, str] = {
    "region": "region",
    "bgcunit": "bgc_unit",
    "bgc_unit": "bgc_unit",
    "siteseries": "site_series",
    "site_series": "site_series",
    "siteassociation": "site_association",
    "site_association": "site_association",
    "treespp": "species",
    "tree_spp": "species",
    "species": "species",
    "plotcountspp": "plot_count",
    "plot_count": "plot_count",
    "plotcount": "plot_count",
    "meanplotsiteindex": "mean_site_index",
    "mean_site_index": "mean_site_index",
    "meansiteindex": "mean_site_index",
    "standarderrorofmean": "standard_error",
    "standard_error": "standard_error",
    "standarderror": "standard_error",
}


class SibecError(RuntimeError):
    """Raised when the SIBEC table is missing or malformed."""


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Map source column names to the canonical SIBEC names."""
    renamed: dict[str, str] = {}
    for column in frame.columns:
        key = str(column).strip().lower().replace(" ", "").replace("_", "")
        canonical = _COLUMN_ALIASES.get(key)
        if canonical is not None:
            renamed[column] = canonical
    return frame.rename(columns=renamed)


def load_sibec_table(path: Path, *, sheet_name: str | int = 0) -> pd.DataFrame:
    """Load a SIBEC workbook or CSV into the tidy ``femic.sibec.v1`` table.

    Parameters
    ----------
    path : pathlib.Path
        XLSX workbook or CSV export.
    sheet_name : str or int, optional
        Worksheet for an XLSX file. The public 2013 approximation workbook has
        its header on the third row.

    Returns
    -------
    pandas.DataFrame
        Tidy SIBEC table with ``schema_version``, region, BGC unit, site
        series, site association, species, plot count, mean site index, and
        standard error.

    Raises
    ------
    SibecError
        If the file has no usable rows or is missing required columns.
    """
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, sheet_name=sheet_name, header=2)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise SibecError(f"unsupported SIBEC table suffix: {path.suffix!r}")

    frame = _normalise_columns(frame)
    required = {
        "bgc_unit",
        "species",
        "mean_site_index",
    }
    missing = required - set(frame.columns)
    if missing:
        raise SibecError(
            f"{path} is missing SIBEC columns: {', '.join(sorted(missing))}"
        )
    frame = frame.copy()
    frame["bgc_unit"] = frame["bgc_unit"].astype("string").str.strip()
    frame["species"] = frame["species"].astype("string").str.strip().str.upper()
    frame["mean_site_index"] = pd.to_numeric(frame["mean_site_index"], errors="coerce")
    frame["plot_count"] = pd.to_numeric(
        frame.get("plot_count", pd.Series(index=frame.index, dtype=float)),
        errors="coerce",
    )
    frame["standard_error"] = pd.to_numeric(
        frame.get("standard_error", pd.Series(index=frame.index, dtype=float)),
        errors="coerce",
    )
    frame = frame.dropna(subset=["bgc_unit", "species", "mean_site_index"])
    if frame.empty:
        raise SibecError(f"{path} contains no usable SIBEC rows")
    frame["schema_version"] = SIBEC_SCHEMA_VERSION
    for optional in ("region", "site_series", "site_association"):
        if optional not in frame.columns:
            frame[optional] = None
        elif optional == "site_series":
            frame[optional] = frame[optional].astype("string")
    return cast(pd.DataFrame, frame.loc[:, SIBEC_COLUMNS]).reset_index(drop=True)


def aggregate_sibec_by_bgc_unit(table: pd.DataFrame) -> pd.DataFrame:
    """Aggregate SIBEC site-series rows to BEC-unit/species.

    Parameters
    ----------
    table : pandas.DataFrame
        Tidy SIBEC table from :func:`load_sibec_table`.

    Returns
    -------
    pandas.DataFrame
        One row per BEC unit and species with weighted mean SI (weighted by
        plot count when available, otherwise unweighted), minimum, maximum,
        mean standard error, site-series count, and total plot count.
    """
    if table.empty:
        raise SibecError("SIBEC table is empty")
    frame = table.copy()
    frame["bgc_unit_key"] = (
        frame["bgc_unit"].str.upper().str.replace(" ", "", regex=False)
    )
    frame["species_key"] = frame["species"].str.upper()
    rows: list[dict[str, object]] = []
    for (bgc_unit_key, species_key), group in frame.groupby(
        ["bgc_unit_key", "species_key"], dropna=False, sort=True
    ):
        values = group["mean_site_index"].astype(float)
        weights = group["plot_count"].fillna(0.0).astype(float)
        if float(weights.sum()) > 0:
            mean_si = float((values * weights).sum() / weights.sum())
        else:
            mean_si = float(values.mean())
        rows.append(
            {
                "bgc_unit_key": bgc_unit_key,
                "species_key": species_key,
                "bgc_unit": str(group["bgc_unit"].iloc[0]),
                "species": species_key,
                "si_sibec_mean": mean_si,
                "si_sibec_min": float(values.min()),
                "si_sibec_max": float(values.max()),
                "si_sibec_se": float(group["standard_error"].mean())
                if group["standard_error"].notna().any()
                else None,
                "si_sibec_plot_count": int(weights.sum())
                if float(weights.sum()) > 0
                else 0,
                "si_sibec_site_series_count": int(group["site_series"].nunique())
                if "site_series" in group
                else len(group),
            }
        )
    return pd.DataFrame.from_records(rows)
