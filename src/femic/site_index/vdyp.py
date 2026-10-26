"""VDYP layer site-index values used by FEMIC curves.

The VDYP layer table already carries ``ESTIMATED_SITE_INDEX`` and the species
the estimate applies to. This reader selects the primary layer and returns one
site-index value per feature. It does not run VDYP or refit a curve.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

from femic.site_index.vri import normalise_species

VDYP_SCHEMA_VERSION = "femic.vdyp.site-index.v1"
VDYP_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "feature_id",
    "species",
    "species_key",
    "si_vdyp",
    "layer_level",
)


class VdypError(RuntimeError):
    """Raised when a VDYP layer table cannot provide site-index fields."""


def load_vdyp_site_index(path: Path) -> pd.DataFrame:
    """Read primary-layer VDYP site index from a Feather, Parquet, or CSV.

    Parameters
    ----------
    path : pathlib.Path
        VDYP layer table with ``FEATURE_ID``, ``ESTIMATED_SITE_INDEX``, and
        ``EST_SITE_INDEX_SPECIES_CD``. If ``LAYER_LEVEL_CODE`` is present, only
        the primary layer (``1``) is kept.

    Returns
    -------
    pandas.DataFrame
        One row per feature with the VDYP site index and the species the
        estimate applies to.

    Raises
    ------
    VdypError
        If required columns are missing or no usable rows remain.
    """
    suffix = path.suffix.lower()
    if suffix == ".feather":
        frame = pd.read_feather(path)
    elif suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise VdypError(f"unsupported VDYP table suffix: {path.suffix!r}")

    columns = {str(column).upper(): column for column in frame.columns}
    feature_column = columns.get("FEATURE_ID")
    site_column = columns.get("ESTIMATED_SITE_INDEX")
    species_column = columns.get("EST_SITE_INDEX_SPECIES_CD")
    if feature_column is None:
        raise VdypError(f"{path} is missing FEATURE_ID")
    if site_column is None:
        raise VdypError(f"{path} is missing ESTIMATED_SITE_INDEX")
    if species_column is None:
        raise VdypError(f"{path} is missing EST_SITE_INDEX_SPECIES_CD")

    out = pd.DataFrame(
        {
            "feature_id": pd.to_numeric(frame[feature_column], errors="coerce"),
            "species": frame[species_column],
            "si_vdyp": pd.to_numeric(frame[site_column], errors="coerce"),
            "layer_level": (
                frame[columns["LAYER_LEVEL_CODE"]].astype("string")
                if "LAYER_LEVEL_CODE" in columns
                else pd.Series(index=frame.index, dtype="string")
            ),
        }
    )
    if "LAYER_LEVEL_CODE" in columns:
        out = out[out["layer_level"].fillna("1").astype(str) == "1"]
    out["species_key"] = out["species"].map(normalise_species)
    out = out.dropna(subset=["feature_id", "si_vdyp"])
    out = out.drop_duplicates(subset=["feature_id"], keep="first")
    if out.empty:
        raise VdypError(f"{path} contains no usable VDYP site-index rows")
    out["feature_id"] = out["feature_id"].astype("Int64")
    out["schema_version"] = VDYP_SCHEMA_VERSION
    return cast(pd.DataFrame, out.loc[:, VDYP_COLUMNS]).reset_index(drop=True)
