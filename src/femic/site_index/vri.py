"""VRI site-index fields and BEC/species keys.

The VRI checkpoint already carries ``SITE_INDEX`` and ``EST_SITE_INDEX`` per
polygon. This reader selects those fields and builds the BEC-unit and species
keys used by SIBEC and VDYP reconciliation.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

VRI_SCHEMA_VERSION = "femic.vri.site-index.v1"
VRI_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "feature_id",
    "bec_unit",
    "bec_unit_key",
    "species",
    "species_key",
    "species_pct",
    "si_vri",
    "si_vri_est",
    "proj_age",
    "proj_height",
)

# VRI codes that need a canonical key before joining SIBEC/VDYP.
SPECIES_ALIASES: dict[str, str] = {
    "H": "HW",
    "HW": "HW",
    "HM": "HM",
    "FD": "FD",
    "FDC": "FD",
    "CW": "CW",
    "BA": "BA",
    "YC": "YC",
    "BL": "BL",
    "SS": "SS",
    "SX": "SX",
    "PL": "PL",
    "SE": "SE",
    "EP": "EP",
    "AT": "AT",
    "AC": "AT",
    "BG": "BG",
    "LW": "LW",
    "PA": "PA",
    "PY": "PY",
    "SB": "SB",
    "SW": "SW",
    "DR": "DR",
    "LT": "LT",
    "PW": "PW",
}


class VriError(RuntimeError):
    """Raised when a VRI table cannot provide site-index fields."""


def _is_missing(value: object) -> bool:
    """Return True for scalar missing values without broad ``pd.isna`` typing."""
    if value is None or value is pd.NA:
        return True
    return bool(pd.Series([value]).isna().iloc[0])


def normalise_species(value: object) -> str | None:
    """Return the canonical species key for a VRI or SIBEC code."""
    if _is_missing(value):
        return None
    text = str(value).strip().upper()
    if not text or text == "NAN":
        return None
    return SPECIES_ALIASES.get(text, text)


def compose_bec_unit(zone: object, subzone: object, variant: object) -> str | None:
    """Compose a BEC unit such as ``CWHvh3`` from VRI fields."""
    parts = []
    for value in (zone, subzone, variant):
        if _is_missing(value):
            continue
        text = str(value).strip()
        if text and text.lower() != "nan":
            parts.append(text)
    if len(parts) < 2:
        return None
    return "".join(parts)


def load_vri_site_index(path: Path) -> pd.DataFrame:
    """Read VRI site-index fields from a Feather, Parquet, or CSV table.

    Parameters
    ----------
    path : pathlib.Path
        VRI checkpoint or export.

    Returns
    -------
    pandas.DataFrame
        One row per VRI feature with BEC unit, canonical species key, VRI
        ``SITE_INDEX``, ``EST_SITE_INDEX``, and projection attributes.

    Raises
    ------
    VriError
        If a required identifier or site-index column is missing, or no usable
        rows remain.
    """
    suffix = path.suffix.lower()
    if suffix == ".feather":
        frame = pd.read_feather(path)
    elif suffix == ".parquet":
        frame = pd.read_parquet(path)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise VriError(f"unsupported VRI table suffix: {path.suffix!r}")

    columns = {str(column).upper(): column for column in frame.columns}
    feature_column = columns.get("FEATURE_ID")
    if feature_column is None:
        raise VriError(f"{path} is missing FEATURE_ID")
    site_column = columns.get("SITE_INDEX")
    est_column = columns.get("EST_SITE_INDEX")
    if site_column is None and est_column is None:
        raise VriError(f"{path} has neither SITE_INDEX nor EST_SITE_INDEX")

    def pick(name: str) -> pd.Series:
        column = columns.get(name)
        if column is None:
            return pd.Series(index=frame.index, dtype=object)
        return frame[column]

    out = pd.DataFrame(
        {
            "feature_id": pd.to_numeric(frame[feature_column], errors="coerce"),
            "bec_unit": [
                compose_bec_unit(zone, subzone, variant)
                for zone, subzone, variant in zip(
                    pick("BEC_ZONE_CODE"),
                    pick("BEC_SUBZONE"),
                    pick("BEC_VARIANT"),
                    strict=False,
                )
            ],
            "species": pick("SPECIES_CD_1"),
            "species_pct": pd.to_numeric(pick("SPECIES_PCT_1"), errors="coerce"),
            "si_vri": pd.to_numeric(
                frame[site_column]
                if site_column is not None
                else pd.Series(index=frame.index, dtype=float),
                errors="coerce",
            ),
            "si_vri_est": pd.to_numeric(
                frame[est_column]
                if est_column is not None
                else pd.Series(index=frame.index, dtype=float),
                errors="coerce",
            ),
            "proj_age": pd.to_numeric(pick("PROJ_AGE_1"), errors="coerce"),
            "proj_height": pd.to_numeric(pick("PROJ_HEIGHT_1"), errors="coerce"),
        }
    )
    out["feature_id"] = out["feature_id"].astype("Int64")
    out["species_key"] = out["species"].map(normalise_species)
    out["bec_unit_key"] = out["bec_unit"].str.upper().str.replace(" ", "", regex=False)
    out = out.dropna(subset=["feature_id"])
    out = out.drop_duplicates(subset=["feature_id"], keep="first")
    if out.empty:
        raise VriError(f"{path} contains no usable VRI site-index rows")
    out["schema_version"] = VRI_SCHEMA_VERSION
    return cast(pd.DataFrame, out.loc[:, VRI_COLUMNS]).reset_index(drop=True)
