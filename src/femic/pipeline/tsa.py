"""TSA-level constants and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from femic.pipeline.bundle import tsa_curve_id_prefix
from femic.pipeline.io import resolve_windows_annex_pointer_payload_path

TARGET_NSTRATA_BY_TSA: dict[str, int] = {
    "08": 9,
    "16": 13,
    "24": 8,
    "40": 7,
    "41": 10,
}
DEFAULT_TARGET_NSTRATA = 10
MIN_STANDCOUNT = 1000


def normalize_tsa_code(tsa_code: Any) -> str:
    """Return canonical TSA code token used across legacy stage tables.

    Numeric values are normalized to zero-padded width-2 strings (for example
    ``8`` -> ``"08"``). Non-numeric tokens are stripped and lower-cased so
    named custom-boundary codes remain stable.
    """
    text = str(tsa_code).strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text.lower()


def target_nstrata_for(tsa_code: str) -> int:
    """Return configured target number of strata for a TSA code.

    Unknown TSA codes fall back to a conservative default so ad-hoc TSA runs
    (for example, pipeline smoke tests on new TSA codes) do not hard-fail.
    """
    tsa = normalize_tsa_code(tsa_code)
    return TARGET_NSTRATA_BY_TSA.get(tsa, DEFAULT_TARGET_NSTRATA)


def select_tsa_slice(*, f_table: Any, tsa_value: Any) -> Any:
    """Return a TSA-filtered slice that is robust to index dtype drift.

    Legacy stage-01a code historically selected TSA rows via ``f.loc[[tsa]]``.
    That can fail when upstream data carries TSA keys as numeric values while the
    run-profile TSA list is normalized as strings (for example ``"29"`` vs ``29``).
    This helper tries equivalent string/int forms before failing.
    """
    candidates = [tsa_value]
    tsa_str = str(tsa_value)
    tsa_norm = normalize_tsa_code(tsa_value)
    if tsa_str not in {str(v) for v in candidates}:
        candidates.append(tsa_str)
    if tsa_norm not in candidates:
        candidates.append(tsa_norm)
    if tsa_str.isdigit():
        tsa_int = int(tsa_str)
        if tsa_int not in candidates:
            candidates.append(tsa_int)
        tsa_zfill = tsa_str.zfill(2)
        if tsa_zfill not in candidates:
            candidates.append(tsa_zfill)
    for candidate in candidates:
        try:
            return f_table.loc[[candidate]]
        except KeyError:
            continue
    try:
        normalized_index = f_table.index.map(normalize_tsa_code)
        mask = normalized_index == tsa_norm
        if bool(getattr(mask, "any", lambda: False)()):
            return f_table.loc[mask]
    except Exception:
        pass
    available_preview = sorted({normalize_tsa_code(v) for v in list(f_table.index)})[
        :20
    ]
    raise KeyError(
        f"TSA key {tsa_value!r} was not found in stage-01a table index "
        f"(index_dtype={getattr(f_table.index, 'dtype', None)!r}). "
        f"Tried candidates: {candidates!r}. "
        f"Available normalized TSA keys (first 20): {available_preview!r}"
    )


def build_strata_summary(
    *,
    f_table: Any,
    stratum_col: str,
    pd_module: Any,
    tsa_code: str | None = None,
    target_nstrata: int | None = None,
    target_coverage: float | None = None,
    min_standcount: int = MIN_STANDCOUNT,
) -> tuple[Any, list[str], float]:
    """Build per-stratum summary table used by legacy TSA orchestration.

    If ``target_coverage`` is provided, strata are selected by descending area until
    cumulative coverage reaches the threshold (0 < target_coverage <= 1). Otherwise
    a fixed top-N selection is used.
    """
    resolved_target = target_nstrata
    if resolved_target is None:
        if tsa_code is None:
            raise ValueError("either target_nstrata or tsa_code must be provided")
        resolved_target = target_nstrata_for(tsa_code)
    if target_coverage is not None and not (0.0 < float(target_coverage) <= 1.0):
        raise ValueError("target_coverage must satisfy 0 < target_coverage <= 1")

    strata_gb1 = f_table.groupby(level=stratum_col)
    totalarea_p_sum = strata_gb1.totalarea_p.sum().sort_values(ascending=False)
    strata_gb2 = f_table.groupby(level=stratum_col)
    site_index_iqr = strata_gb2.SITE_INDEX.quantile(
        0.75
    ) - strata_gb2.SITE_INDEX.quantile(0.25)
    strata_df = pd_module.DataFrame(totalarea_p_sum)
    strata_df["site_index_std"] = strata_gb2.SITE_INDEX.std()
    strata_df["site_index_iqr"] = site_index_iqr
    strata_df["site_index_median"] = strata_gb2.SITE_INDEX.median()
    strata_df["stand_count"] = strata_gb2.FEATURE_ID.count()
    strata_df["coverage"] = strata_gb2.totalarea_p.sum()
    strata_df["crown_closure"] = strata_gb2.CROWN_CLOSURE.median()
    filtered = strata_df[strata_df.stand_count >= min_standcount]
    # Small custom-boundary runs can have far fewer stands per stratum than
    # provincial TSA runs; retain top strata instead of producing an empty/NaN
    # summary table.
    if filtered.empty and not strata_df.empty:
        filtered = strata_df.copy()
    if target_coverage is not None and not filtered.empty:
        cumulative = filtered.coverage.cumsum()
        selected_n = int((cumulative < float(target_coverage)).sum()) + 1
        selected_n = min(max(selected_n, 1), int(filtered.shape[0]))
        strata_df = filtered.head(selected_n).copy()
    else:
        strata_df = filtered.head(resolved_target).copy()
    largestn_strata_codes = list(strata_df.index.values)
    median_si = (
        f_table[f_table.index.isin(largestn_strata_codes)]
        .groupby(level=stratum_col)
        .SITE_INDEX.median()
    )
    strata_df["median_si"] = median_si.reindex(strata_df.index)
    return strata_df, largestn_strata_codes, float(site_index_iqr.mean())


def resolve_si_level_quantiles_for_stratum(
    *,
    stratum_si_stats: Any,
    stratum_code: Any,
    si_levelquants: Mapping[str, Sequence[float]],
) -> dict[str, tuple[int, int, int]]:
    """Resolve per-stratum SI quantile bands.

    The current policy is to apply strict, fixed L/M/H bands for all strata
    (for example L=5-35, M=35-65, H=65-95) as provided by `si_levelquants`.
    """
    del stratum_si_stats, stratum_code
    return {
        level: (int(values[0]), int(values[1]), int(values[2]))
        for level, values in si_levelquants.items()
    }


def build_stratum_lexmatch_alias_map(
    *,
    f_table: Any,
    stratum_col: str,
    selected_strata_codes: Sequence[str],
    levenshtein_fn: Callable[[str, str], int],
) -> dict[str, str]:
    """Build best-match aliases from non-selected lexmatch strata to selected strata."""
    selected_codes = list(selected_strata_codes)
    names1 = set(f_table.loc[selected_codes].stratum_lexmatch.dropna().unique())
    names2 = set(f_table.stratum_lexmatch.dropna().unique()) - names1
    if not names1 or not names2:
        return {}

    stratum_key = (
        f_table.reset_index().groupby(f"{stratum_col}_lexmatch")[stratum_col].first()
    )
    totalarea_p_sum = f_table.groupby(f"{stratum_col}_lexmatch").totalarea_p.sum()
    lev_dist = {n2: {n1: levenshtein_fn(n1, n2) for n1 in names1} for n2 in names2}
    lev_dist_low = {
        n2: {
            n1: (lev_dist[n2][n1], totalarea_p_sum.loc[n1])
            for n1 in lev_dist[n2]
            if lev_dist[n2][n1] == min(lev_dist[n2].values())
        }
        for n2 in names2
    }
    return {
        stratum_key.loc[n2]: stratum_key[
            max(lev_dist_low[n2].items(), key=lambda i: i[1])[0]
        ]
        for n2 in names2
    }


def apply_stratum_alias_map(
    *,
    f_table: Any,
    stratum_col: str,
    selected_strata_codes: Sequence[str],
    best_match: Mapping[str, str],
) -> str:
    """Apply selected+alias stratum mapping and return matched-column name."""
    selected = set(selected_strata_codes)
    matched_col = f"{stratum_col}_matched"
    f_table[matched_col] = [
        key if key in selected else best_match.get(key, key)
        for key in f_table[stratum_col].values
    ]
    return matched_col


def assign_stratum_matches_from_au_table(
    *,
    f_table: Any,
    au_table: Any,
    tsa_list: Sequence[str],
    stratum_col: str,
    levenshtein_fn: Callable[[str, str], int] | None = None,
    message_fn: Callable[[str], Any] = print,
) -> Any:
    """Assign `stratum_matched` values by TSA using AU-table strata as targets."""
    matched_col = f"{stratum_col}_matched"
    if levenshtein_fn is None:
        distance_mod = __import__("distance")
        levenshtein_fn = distance_mod.levenshtein
    table = f_table.copy()
    if "FEATURE_ID" not in table.columns:
        table = table.reset_index()
    if matched_col not in table.columns:
        table[matched_col] = None

    table = table.set_index("FEATURE_ID")
    for tsa in tsa_list:
        message_fn(f"matching tsa {tsa}")
        strata_candidates = au_table.loc[
            au_table["tsa"] == tsa, "stratum_code"
        ].unique()
        selected_strata_codes = [str(code) for code in strata_candidates]
        if not selected_strata_codes:
            continue

        tsa_rows = table.loc[table["tsa_code"] == tsa].copy().reset_index()
        if tsa_rows.empty:
            continue
        tsa_rows = tsa_rows.set_index(stratum_col)
        totalarea = tsa_rows.FEATURE_AREA_SQM.sum()
        if float(totalarea) <= 0.0:
            continue
        tsa_rows["totalarea_p"] = tsa_rows.FEATURE_AREA_SQM / totalarea
        best_match = build_stratum_lexmatch_alias_map(
            f_table=tsa_rows,
            stratum_col=stratum_col,
            selected_strata_codes=selected_strata_codes,
            levenshtein_fn=levenshtein_fn,
        )
        tsa_rows = tsa_rows.reset_index()
        apply_stratum_alias_map(
            f_table=tsa_rows,
            stratum_col=stratum_col,
            selected_strata_codes=selected_strata_codes,
            best_match=best_match,
        )
        matched = tsa_rows[["FEATURE_ID", matched_col]].set_index("FEATURE_ID")[
            matched_col
        ]
        table[matched_col] = matched.where(~matched.isnull(), table[matched_col])
    return table


def assign_si_levels_from_stratum_quantiles(
    *,
    f_table: Any,
    si_levelquants: Mapping[str, Sequence[int]],
    allowed_levels_by_stratum: Mapping[str, Sequence[str]] | None = None,
    stratum_matched_col: str = "stratum_matched",
    site_index_col: str = "SITE_INDEX",
    si_level_col: str = "si_level",
    message_fn: Callable[[str], Any] = print,
) -> tuple[Any, Any]:
    """Assign SI-level labels within each matched stratum from configured quantile bands."""
    import pandas as pd

    table = f_table.copy()
    if stratum_matched_col not in table.columns:
        return table, pd.DataFrame()
    if table[stratum_matched_col].dropna().empty:
        if si_level_col not in table.columns:
            table[si_level_col] = None
        return table, pd.DataFrame()
    table[si_level_col] = None
    stratum_si_stats = table.groupby(stratum_matched_col)[site_index_col].describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )
    for stratum_code in stratum_si_stats.index:
        message_fn(str(stratum_code))
        level_quants = resolve_si_level_quantiles_for_stratum(
            stratum_si_stats=stratum_si_stats,
            stratum_code=stratum_code,
            si_levelquants=si_levelquants,
        )
        if allowed_levels_by_stratum is not None:
            allowed = {
                str(level)
                for level in allowed_levels_by_stratum.get(str(stratum_code), [])
            }
            if allowed:
                fallback_quantiles = {
                    "L": (5, 20, 35),
                    "M": (35, 50, 65),
                    "H": (65, 80, 95),
                }
                restricted: dict[str, tuple[int, int, int]] = {}
                for level in ("L", "M", "H"):
                    if level not in allowed:
                        continue
                    restricted[level] = level_quants.get(
                        level, fallback_quantiles[level]
                    )
                if restricted:
                    level_quants = restricted
        if not level_quants:
            continue
        quantile_triplets = {
            level: tuple(int(v) for v in values)
            for level, values in level_quants.items()
        }
        min_q_lo = min(q_lo for q_lo, _q_mid, _q_hi in quantile_triplets.values())
        max_q_hi = max(q_hi for _q_lo, _q_mid, q_hi in quantile_triplets.values())
        for si_level, quantiles in quantile_triplets.items():
            q_lo, _q_mid, q_hi = [int(v) for v in quantiles]
            si_lo = (
                float("-inf")
                if q_lo == min_q_lo
                else stratum_si_stats.loc[stratum_code].loc[f"{q_lo}%"]
            )
            si_hi = (
                float("inf")
                if q_hi == max_q_hi
                else stratum_si_stats.loc[stratum_code].loc[f"{q_hi}%"]
            )
            table.loc[
                (table[stratum_matched_col] == stratum_code)
                & (table[site_index_col] >= si_lo)
                & (table[site_index_col] <= si_hi),
                si_level_col,
            ] = si_level
    return table, stratum_si_stats


def lookup_scsi_au_base(
    *,
    scsi_au: Mapping[str, Mapping[tuple[str, str], int]],
    tsa_code: Any,
    stratum_code: Any,
    si_level: Any,
) -> int | None:
    """Lookup base AU id for a TSA/stratum/SI combination."""
    tsa_map = scsi_au.get(str(tsa_code))
    if not tsa_map:
        return None
    return tsa_map.get((str(stratum_code), str(si_level)))


def assign_au_ids_from_scsi(
    *,
    f_table: Any,
    scsi_au: Mapping[str, Mapping[tuple[str, str], int]],
    tsa_col: str = "tsa_code",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
    au_col: str = "au",
) -> Any:
    """Assign absolute AU ids from `scsi_au` lookup map."""
    table = f_table.copy()
    if tsa_col not in table.columns and (
        getattr(table.index, "name", None) == tsa_col
        or tsa_col in list(getattr(table.index, "names", []))
    ):
        table = table.reset_index()
    if tsa_col not in table.columns:
        table = table.reset_index()
        if tsa_col not in table.columns and "index" in table.columns:
            table = table.rename(columns={"index": tsa_col})
    if tsa_col not in table.columns:
        table[tsa_col] = None
    table[au_col] = [
        (
            None
            if (
                (
                    au_base := lookup_scsi_au_base(
                        scsi_au=scsi_au,
                        tsa_code=tsa_code,
                        stratum_code=stratum_code,
                        si_level=si_level,
                    )
                )
                is None
            )
            else (100000 * tsa_curve_id_prefix(str(tsa_code)) + au_base)
        )
        for tsa_code, stratum_code, si_level in zip(
            table[tsa_col].values,
            table[stratum_matched_col].values,
            table[si_level_col].values,
        )
    ]
    return table


def summarize_missing_au_mappings(
    *,
    f_table: Any,
    au_col: str = "au",
    tsa_col: str = "tsa_code",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
    top_n: int = 10,
) -> Any:
    """Return top-N missing AU mapping combinations for diagnostics."""
    return (
        f_table.loc[
            f_table[au_col].isnull(), [tsa_col, stratum_matched_col, si_level_col]
        ]
        .value_counts()
        .head(top_n)
    )


def emit_missing_au_mapping_warning(
    *,
    summary: Any,
    message_fn: Callable[[Any], Any] = print,
    header: str = "Warning: missing AU mappings for some strata (top 10 shown):",
) -> None:
    """Emit legacy warning lines for missing AU mapping diagnostics."""
    message_fn(header)
    message_fn(summary)


def build_au_assignment_null_summary(
    *,
    f_table: Any,
    site_index_col: str = "SITE_INDEX",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
) -> dict[str, int | None]:
    """Build null-diagnostics summary used when AU assignment yields no rows."""
    return {
        "rows": int(len(f_table)),
        "site_index_null": int(f_table[site_index_col].isnull().sum())
        if site_index_col in f_table
        else None,
        "stratum_matched_null": int(f_table[stratum_matched_col].isnull().sum())
        if stratum_matched_col in f_table
        else None,
        "si_level_null": int(f_table[si_level_col].isnull().sum())
        if si_level_col in f_table
        else None,
    }


def build_missing_au_assignment_summary(
    *,
    f_table: Any,
    au_col: str = "au",
    tsa_col: str = "tsa_code",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
    area_col: str = "FEATURE_AREA_SQM",
    top_n: int = 10,
) -> dict[str, Any]:
    """Summarize residual unmapped AU rows after the imputation pass."""
    missing = f_table.loc[f_table[au_col].isnull()].copy()
    summary: dict[str, Any] = {
        "rows": int(len(missing)),
        "area_sqm": 0.0,
        "top_missing": [],
    }
    if missing.empty:
        return summary
    if area_col in missing.columns:
        summary["area_sqm"] = float(missing[area_col].fillna(0.0).sum())
    grouped = (
        missing.loc[:, [tsa_col, stratum_matched_col, si_level_col]]
        .value_counts(dropna=False)
        .head(top_n)
    )
    summary["top_missing"] = [
        {
            "tsa_code": idx[0],
            "stratum_matched": idx[1],
            "si_level": idx[2],
            "count": int(count),
        }
        for idx, count in grouped.items()
    ]
    return summary


def validate_nonempty_au_assignment(
    *,
    f_table: Any,
    au_col: str = "au",
    site_index_col: str = "SITE_INDEX",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
) -> None:
    """Raise with null diagnostics when AU assignment produces no mapped rows."""
    if not f_table[au_col].isnull().all():
        return
    null_summary = build_au_assignment_null_summary(
        f_table=f_table,
        site_index_col=site_index_col,
        stratum_matched_col=stratum_matched_col,
        si_level_col=si_level_col,
    )
    raise ValueError(
        "AU assignment produced no rows; check SITE_INDEX/stratum matching and "
        f"si_level assignment. Summary: {null_summary}"
    )


def validate_complete_au_assignment(
    *,
    f_table: Any,
    au_col: str = "au",
    tsa_col: str = "tsa_code",
    stratum_matched_col: str = "stratum_matched",
    si_level_col: str = "si_level",
    site_index_col: str = "SITE_INDEX",
    area_col: str = "FEATURE_AREA_SQM",
    top_n: int = 10,
) -> None:
    """Raise when any post-imputation AFLB rows still lack AU assignment."""
    validate_nonempty_au_assignment(
        f_table=f_table,
        au_col=au_col,
        site_index_col=site_index_col,
        stratum_matched_col=stratum_matched_col,
        si_level_col=si_level_col,
    )
    missing = f_table.loc[f_table[au_col].isnull()]
    if missing.empty:
        return
    summary = build_missing_au_assignment_summary(
        f_table=f_table,
        au_col=au_col,
        tsa_col=tsa_col,
        stratum_matched_col=stratum_matched_col,
        si_level_col=si_level_col,
        area_col=area_col,
        top_n=top_n,
    )
    raise ValueError(
        "AU assignment left residual AFLB rows unmapped after lexicographical "
        f"stratum-matching imputation. Summary: {summary}"
    )


def assign_thlb_area_and_flag(
    *,
    f_table: Any,
    species_spruce: Sequence[str],
    species_pine: Sequence[str],
    species_aspen: Sequence[str],
    species_fir: Sequence[str],
    tsa_col: str = "tsa_code",
    thlb_raw_col: str = "thlb_raw",
    area_col: str = "FEATURE_AREA_SQM",
    species_col: str = "SPECIES_CD_1",
    site_index_col: str = "SITE_INDEX",
    thlb_area_col: str = "thlb_area",
    thlb_col: str = "thlb",
) -> Any:
    """Assign THLB area and THLB binary flag using legacy TSA-specific rules."""
    table = f_table.copy()
    spruce = set(species_spruce)
    pine = set(species_pine)
    aspen = set(species_aspen)
    fir = set(species_fir)
    excluded_tsa08_species = {"SB", "E", "EA", "EB", "LT"}

    thlb_area_values: list[float] = []
    thlb_values: list[int] = []
    for row in table.itertuples(index=False):
        tsa_code = getattr(row, tsa_col)
        thlb_raw = getattr(row, thlb_raw_col)
        species = getattr(row, species_col)
        site_index = getattr(row, site_index_col)
        feature_area = getattr(row, area_col)

        thlb_area = float(thlb_raw) * float(feature_area) * 0.000001
        if str(tsa_code) == "08":
            if thlb_raw < 90:
                thlb_area = 0.0
            elif species in spruce and site_index < 10:
                thlb_area = 0.0
            elif species in pine and site_index < 15:
                thlb_area = 0.0
            elif species in aspen and site_index < 15:
                thlb_area = 0.0
            elif species in fir and site_index < 10:
                thlb_area = 0.0
            elif species in excluded_tsa08_species:
                thlb_area = 0.0

        thlb_thresh = 50
        if str(tsa_code) == "08":
            thlb_thresh = 93
        elif str(tsa_code) == "24":
            thlb_thresh = 69
        thlb_flag = 1 if thlb_raw > thlb_thresh else 0

        thlb_area_values.append(thlb_area)
        thlb_values.append(thlb_flag)

    table[thlb_area_col] = thlb_area_values
    table[thlb_col] = thlb_values
    return table


def mean_thlb_for_geometry(
    *,
    geometry: Any,
    raster_src: Any,
    mask_fn: Callable[..., Any],
    np_module: Any,
    default_on_error: float = 0.0,
) -> float:
    """Compute mean THLB raster value for one geometry with legacy error fallback."""
    try:
        array, _ = mask_fn(raster_src, [geometry], crop=True)
    except (ValueError, TypeError, RuntimeError, OSError):
        return float(default_on_error)
    valid = array[array >= 0]
    if getattr(valid, "size", 0) == 0:
        return float(default_on_error)
    mean_value = np_module.mean(valid)
    if not np_module.isfinite(mean_value):
        return float(default_on_error)
    return float(mean_value)


def assign_thlb_raw_from_raster(
    *,
    f_table: Any,
    thlb_raster_path: str | Path,
    rio_module: Any,
    mask_fn: Callable[..., Any],
    np_module: Any,
    row_apply_fn: Callable[..., Any],
    geometry_col: str = "geometry",
    out_col: str = "thlb_raw",
    default_on_error: float = 0.0,
) -> Any:
    """Assign per-row raw THLB values by masking a THLB raster."""
    table = f_table.copy()
    readable_path = resolve_windows_annex_pointer_payload_path(Path(thlb_raster_path))
    with rio_module.open(readable_path) as src:

        def _mean(row: Any) -> float:
            try:
                geometry = row[geometry_col]
            except (KeyError, TypeError, IndexError):
                geometry = getattr(row, geometry_col)
            return mean_thlb_for_geometry(
                geometry=geometry,
                raster_src=src,
                mask_fn=mask_fn,
                np_module=np_module,
                default_on_error=default_on_error,
            )

        table[out_col] = row_apply_fn(table, _mean, axis=1)
    return table
