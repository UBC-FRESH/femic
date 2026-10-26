"""Reconcile VRI, VDYP, and SIBEC site-index values.

The reconciliation is intentionally a reporting layer. It records the values
each existing BC product provides, the differences between them, and a
documented reference value. It never rewrites a curve, changes an AAC, or fits
a new site-index model.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

RECONCILIATION_SCHEMA_VERSION = "femic.site-index.reconciliation.v2"
DEFAULT_DELTA_THRESHOLD = 2.0
DEFAULT_MIN_SIBEC_PLOT_COUNT = 7
RECONCILIATION_COLUMNS: tuple[str, ...] = (
    "feature_id",
    "bec_unit",
    "species_vri",
    "species_vdyp",
    "species_match",
    "si_vri",
    "si_vri_est",
    "si_vdyp",
    "si_sibec_vri",
    "si_sibec_vri_min",
    "si_sibec_vri_max",
    "si_sibec_vri_se",
    "si_sibec_vri_plot_count",
    "si_sibec_vri_site_series_count",
    "si_sibec_vri_source",
    "si_sibec_vdyp",
    "si_sibec_vdyp_min",
    "si_sibec_vdyp_max",
    "si_sibec_vdyp_plot_count",
    "si_sibec_vdyp_source",
    "delta_vri_vdyp",
    "delta_vri_sibec",
    "delta_vdyp_sibec",
    "delta_vri_sibec_range",
    "delta_vdyp_sibec_range",
    "delta_abs_max",
    "si_source_count",
    "si_status",
    "si_reference",
    "si_reference_source",
    "delta_reference_curve",
    "proj_age",
    "proj_height",
)


class SiteIndexReconciliationError(RuntimeError):
    """Raised when reconciliation inputs cannot be joined consistently."""


def _range_exceedance(
    value: pd.Series, lower: pd.Series, upper: pd.Series
) -> pd.Series:
    """Return the distance outside ``[lower, upper]``, or zero inside."""
    outside_low = (lower - value).clip(lower=0.0)
    outside_high = (value - upper).clip(lower=0.0)
    exceedance = outside_low.combine(outside_high, max)
    return exceedance.where(value.notna() & lower.notna() & upper.notna())


def reconcile_site_index(
    vri: pd.DataFrame,
    vdyp: pd.DataFrame,
    sibec_by_bgc_unit: pd.DataFrame,
    *,
    delta_threshold: float = DEFAULT_DELTA_THRESHOLD,
    min_sibec_plot_count: int = DEFAULT_MIN_SIBEC_PLOT_COUNT,
) -> pd.DataFrame:
    """Join VRI, VDYP, and SIBEC site-index values feature by feature.

    Parameters
    ----------
    vri : pandas.DataFrame
        Output of :func:`femic.site_index.vri.load_vri_site_index`.
    vdyp : pandas.DataFrame
        Output of :func:`femic.site_index.vdyp.load_vdyp_site_index`.
    sibec_by_bgc_unit : pandas.DataFrame
        Output of :func:`femic.site_index.sibec.aggregate_sibec_by_bgc_unit`.
    delta_threshold : float, optional
        Absolute difference in metres above which a row is flagged as a
        conflict. The default is ``2.0`` m.
    min_sibec_plot_count : int, optional
        Minimum SIBEC plot count for SIBEC to become the reference value when
        VRI has no ``SITE_INDEX``. The default is ``7``.

    Returns
    -------
    pandas.DataFrame
        One row per VRI feature with source values, pairwise deltas, coverage
        status, and the documented reference value/source. The VDYP value is
        always the current curve input; the reference value is a comparison
        value and is not applied automatically.
    """
    if vri.empty:
        raise SiteIndexReconciliationError("VRI site-index table is empty")
    if delta_threshold < 0:
        raise SiteIndexReconciliationError("delta_threshold must be non-negative")
    if min_sibec_plot_count < 0:
        raise SiteIndexReconciliationError("min_sibec_plot_count must be non-negative")

    vdyp_use = vdyp.loc[:, ["feature_id", "species", "species_key", "si_vdyp"]].rename(
        columns={
            "species": "species_vdyp",
            "species_key": "species_key_vdyp",
        }
    )
    sibec_vri = sibec_by_bgc_unit.loc[
        :,
        [
            "bgc_unit_key",
            "species_key",
            "si_sibec_mean",
            "si_sibec_min",
            "si_sibec_max",
            "si_sibec_se",
            "si_sibec_plot_count",
            "si_sibec_site_series_count",
        ],
    ].copy()
    sibec_vri["si_sibec_vri_source"] = (
        sibec_by_bgc_unit["si_sibec_source"]
        if "si_sibec_source" in sibec_by_bgc_unit.columns
        else pd.NA
    )
    sibec_vri = sibec_vri.rename(
        columns={
            "bgc_unit_key": "bec_unit_key",
            "si_sibec_mean": "si_sibec_vri",
            "si_sibec_min": "si_sibec_vri_min",
            "si_sibec_max": "si_sibec_vri_max",
            "si_sibec_se": "si_sibec_vri_se",
            "si_sibec_plot_count": "si_sibec_vri_plot_count",
            "si_sibec_site_series_count": "si_sibec_vri_site_series_count",
        }
    )
    sibec_vdyp = sibec_by_bgc_unit.loc[
        :,
        [
            "bgc_unit_key",
            "species_key",
            "si_sibec_mean",
            "si_sibec_min",
            "si_sibec_max",
            "si_sibec_plot_count",
        ],
    ].copy()
    sibec_vdyp["si_sibec_vdyp_source"] = (
        sibec_by_bgc_unit["si_sibec_source"]
        if "si_sibec_source" in sibec_by_bgc_unit.columns
        else pd.NA
    )
    sibec_vdyp = sibec_vdyp.rename(
        columns={
            "bgc_unit_key": "bec_unit_key",
            "species_key": "species_key_vdyp",
            "si_sibec_mean": "si_sibec_vdyp",
            "si_sibec_min": "si_sibec_vdyp_min",
            "si_sibec_max": "si_sibec_vdyp_max",
            "si_sibec_plot_count": "si_sibec_vdyp_plot_count",
        }
    )

    frame = vri.merge(vdyp_use, on="feature_id", how="left", validate="one_to_one")
    frame = frame.rename(columns={"species": "species_vri"})
    frame = frame.merge(
        sibec_vri,
        on=["bec_unit_key", "species_key"],
        how="left",
        validate="many_to_one",
    )
    frame = frame.merge(
        sibec_vdyp,
        on=["bec_unit_key", "species_key_vdyp"],
        how="left",
        validate="many_to_one",
    )

    frame["species_match"] = (
        frame["species_key"].notna()
        & frame["species_key_vdyp"].notna()
        & frame["species_key"].eq(frame["species_key_vdyp"])
    )

    frame["delta_vri_vdyp"] = frame["si_vdyp"] - frame["si_vri"]
    frame.loc[~frame["species_match"], "delta_vri_vdyp"] = np.nan
    frame["delta_vri_sibec"] = frame["si_sibec_vri"] - frame["si_vri"]
    frame["delta_vdyp_sibec"] = frame["si_sibec_vdyp"] - frame["si_vdyp"]
    frame["delta_vri_sibec_range"] = _range_exceedance(
        frame["si_vri"],
        frame["si_sibec_vri_min"],
        frame["si_sibec_vri_max"],
    )
    frame["delta_vdyp_sibec_range"] = _range_exceedance(
        frame["si_vdyp"],
        frame["si_sibec_vdyp_min"],
        frame["si_sibec_vdyp_max"],
    )
    frame["delta_abs_max"] = (
        frame[["delta_vri_vdyp", "delta_vri_sibec_range", "delta_vdyp_sibec_range"]]
        .abs()
        .max(axis=1, skipna=True)
    )

    frame["si_source_count"] = (
        frame[["si_vri", "si_vdyp", "si_sibec_vri"]].notna().sum(axis=1).astype(int)
    )
    has_any = frame["si_source_count"] > 0
    complete = frame[["si_vri", "si_vdyp", "si_sibec_vri"]].notna().all(axis=1)
    conflict = frame["delta_abs_max"] > float(delta_threshold)
    frame["si_status"] = np.select(
        [~has_any, conflict, complete],
        ["missing", "conflict", "complete"],
        default="partial",
    )

    reference = pd.Series(np.nan, index=frame.index, dtype=float)
    reference_source = pd.Series(pd.NA, index=frame.index, dtype="string")

    mask = frame["si_vri"].notna()
    reference.loc[mask] = frame.loc[mask, "si_vri"]
    reference_source.loc[mask] = "vri"

    mask = (
        reference.isna()
        & frame["si_sibec_vri"].notna()
        & (frame["si_sibec_vri_plot_count"].fillna(0) >= int(min_sibec_plot_count))
    )
    reference.loc[mask] = frame.loc[mask, "si_sibec_vri"]
    reference_source.loc[mask] = "sibec"

    mask = reference.isna() & frame["si_vdyp"].notna()
    reference.loc[mask] = frame.loc[mask, "si_vdyp"]
    reference_source.loc[mask] = "vdyp"

    mask = reference.isna() & frame["si_vri_est"].notna()
    reference.loc[mask] = frame.loc[mask, "si_vri_est"]
    reference_source.loc[mask] = "vri_estimate"

    frame["si_reference"] = reference
    frame["si_reference_source"] = reference_source
    frame["delta_reference_curve"] = frame["si_reference"] - frame["si_vdyp"]

    frame = frame.sort_values("feature_id").reset_index(drop=True)
    return cast(pd.DataFrame, frame.loc[:, RECONCILIATION_COLUMNS])


def _delta_summary(values: pd.Series) -> dict[str, object]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p90_abs": None,
            "max_abs": None,
        }
    return {
        "count": int(clean.size),
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "p90_abs": float(clean.abs().quantile(0.9)),
        "max_abs": float(clean.abs().max()),
    }


def summarize_reconciliation(
    frame: pd.DataFrame,
    *,
    delta_threshold: float = DEFAULT_DELTA_THRESHOLD,
) -> dict[str, object]:
    """Return a JSON-serializable coverage and conflict summary."""
    if frame.empty:
        return {
            "schema_version": RECONCILIATION_SCHEMA_VERSION,
            "feature_count": 0,
            "delta_threshold": float(delta_threshold),
        }

    def count_non_null(column: str) -> int:
        return int(frame[column].notna().sum())

    status = frame["si_status"]
    conflict = frame[status == "conflict"]
    both_species = frame["species_vri"].notna() & frame["species_vdyp"].notna()
    top_bec = (
        conflict.groupby("bec_unit", dropna=True)
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    top_species = (
        conflict.groupby("species_vri", dropna=True)
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    feature_count = len(frame)
    return {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "feature_count": feature_count,
        "delta_threshold": float(delta_threshold),
        "coverage": {
            "si_vri": count_non_null("si_vri"),
            "si_vri_est": count_non_null("si_vri_est"),
            "si_vdyp": count_non_null("si_vdyp"),
            "si_sibec_vri": count_non_null("si_sibec_vri"),
            "si_sibec_vdyp": count_non_null("si_sibec_vdyp"),
        },
        "sibec_sources": {
            "si_sibec_vri": {
                str(key): int(value)
                for key, value in frame["si_sibec_vri_source"]
                .fillna("none")
                .value_counts()
                .items()
            },
            "si_sibec_vdyp": {
                str(key): int(value)
                for key, value in frame["si_sibec_vdyp_source"]
                .fillna("none")
                .value_counts()
                .items()
            },
        },
        "status_counts": {
            value: int((status == value).sum())
            for value in ("complete", "conflict", "partial", "missing")
        },
        "species_mismatch_count": int((both_species & ~frame["species_match"]).sum()),
        "deltas": {
            "vri_vdyp": _delta_summary(frame["delta_vri_vdyp"]),
            "vri_sibec_mean": _delta_summary(frame["delta_vri_sibec"]),
            "vdyp_sibec_mean": _delta_summary(frame["delta_vdyp_sibec"]),
            "vri_sibec_range": _delta_summary(frame["delta_vri_sibec_range"]),
            "vdyp_sibec_range": _delta_summary(frame["delta_vdyp_sibec_range"]),
            "reference_curve": _delta_summary(frame["delta_reference_curve"]),
        },
        "top_conflict_bec_units": {
            str(key): int(value) for key, value in top_bec.items()
        },
        "top_conflict_species": {
            str(key): int(value) for key, value in top_species.items()
        },
        "reference_sources": {
            str(key): int(value)
            for key, value in frame["si_reference_source"]
            .fillna("none")
            .value_counts()
            .items()
        },
    }
