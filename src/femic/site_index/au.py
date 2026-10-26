"""AU-level TSA site-index reader and summary.

The TSA ``03_input-<tsa>.csv`` table is at the analysis-unit grain, not the VRI
polygon/layer grain. This module reports it separately so the two grains are
never silently conflated.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

from femic.site_index.vri import normalise_species

AU_SCHEMA_VERSION = "femic.site-index.au.v1"
AU_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "au_id",
    "bec_zone",
    "bec_subzone",
    "planted_species",
    "natural_species",
    "leading_species",
    "species",
    "species_key",
    "si_au",
    "is_leading",
)


class AuSiteIndexError(RuntimeError):
    """Raised when a TSA AU-level site-index table cannot be read."""


def _pick_column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series(index=frame.index, dtype=object)
    return frame[name]


def load_au_site_index(path: Path) -> pd.DataFrame:
    """Read a TSA ``03_input`` table into a long AU/species site-index table.

    Parameters
    ----------
    path:
        CSV, Feather, or Parquet TSA input table. The table must contain
        ``feature_id`` and one or more ``<species>_si`` columns.

    Returns
    -------
    pandas.DataFrame
        One row per AU/species with the AU identifier, BEC zone/subzone,
        planted/natural leading species, the species SI value, and a leading
        species flag.

    Raises
    ------
    AuSiteIndexError
        If the table has no feature identifier or no species SI columns.
    """
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".feather":
        frame = pd.read_feather(path)
    elif suffix == ".parquet":
        frame = pd.read_parquet(path)
    else:
        raise AuSiteIndexError(f"unsupported AU table suffix: {path.suffix!r}")
    if "feature_id" not in frame.columns:
        raise AuSiteIndexError(f"{path} is missing feature_id")

    si_columns = [column for column in frame.columns if str(column).endswith("_si")]
    if not si_columns:
        raise AuSiteIndexError(f"{path} has no <species>_si columns")

    return_frame = frame.copy()
    return_frame["au_id"] = pd.to_numeric(return_frame["feature_id"], errors="coerce")
    return_frame["bec_zone"] = _pick_column(return_frame, "bec_zone")
    return_frame["bec_subzone"] = _pick_column(return_frame, "bec_subzone")
    return_frame["planted_species"] = _pick_column(return_frame, "planted_species1")
    return_frame["natural_species"] = _pick_column(return_frame, "natural_species1")
    return_frame["leading_species"] = return_frame["planted_species"].where(
        return_frame["planted_species"].notna()
        & return_frame["planted_species"].astype("string").str.strip().ne(""),
        return_frame["natural_species"],
    )
    return_frame["leading_species_key"] = return_frame["leading_species"].map(
        normalise_species
    )

    long = cast(
        pd.DataFrame,
        return_frame.melt(
            id_vars=[
                "au_id",
                "bec_zone",
                "bec_subzone",
                "planted_species",
                "natural_species",
                "leading_species",
                "leading_species_key",
            ],
            value_vars=si_columns,
            var_name="species_column",
            value_name="si_au",
        ),
    )
    long["species_key"] = (
        long["species_column"].str.removesuffix("_si").map(normalise_species)
    )
    long["species"] = long["species_key"]
    long["si_au"] = pd.to_numeric(long["si_au"], errors="coerce")
    long = long.dropna(subset=["au_id", "species_key", "si_au"])
    long["is_leading"] = long["species_key"].eq(long["leading_species_key"])
    long["schema_version"] = AU_SCHEMA_VERSION
    long = long.drop(columns=["species_column", "leading_species_key"])
    long = cast(pd.DataFrame, long.loc[:, AU_COLUMNS])
    return long.sort_values(["au_id", "species_key"], kind="stable").reset_index(
        drop=True
    )


def summarize_au_site_index(table: pd.DataFrame) -> dict[str, object]:
    """Return a JSON-serializable AU-level site-index summary."""
    if table.empty:
        return {
            "schema_version": AU_SCHEMA_VERSION,
            "au_count": 0,
            "row_count": 0,
            "grain": "analysis_unit_species",
        }
    leading = table[table["is_leading"]]
    leading_values = leading["si_au"].astype(float)
    return {
        "schema_version": AU_SCHEMA_VERSION,
        "grain": "analysis_unit_species",
        "au_count": int(table["au_id"].nunique()),
        "row_count": len(table),
        "species_count": int(table["species_key"].nunique()),
        "bec_zones": sorted(
            str(value) for value in table["bec_zone"].dropna().unique()
        ),
        "leading_species_counts": {
            str(key): int(value)
            for key, value in leading["species_key"].value_counts().items()
        },
        "leading_si": {
            "count": int(leading_values.size),
            "min": float(leading_values.min()) if leading_values.size else None,
            "max": float(leading_values.max()) if leading_values.size else None,
            "mean": float(leading_values.mean()) if leading_values.size else None,
            "median": float(leading_values.median()) if leading_values.size else None,
        },
    }
