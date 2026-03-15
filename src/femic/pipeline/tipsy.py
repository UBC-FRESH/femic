"""Reusable TIPSY parameter helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from femic.pipeline.diagnostics import build_timestamped_event


DEFAULT_TIPSY_BATCH_COLUMNS_1BASED: dict[str, tuple[int, int]] = {
    # Canonical BatchTIPSY GUI ranges from user screenshots.
    "AU": (1, 6),
    "TBLno": (7, 12),
    "BEC": (14, 17),
    # Keep proportion in a wider field so values like 0.3/0.85 fit while
    # preserving the downstream BatchTIPSY column anchors in user runbooks.
    "Proportion": (31, 39),
    "Regen_Delay": (40, 42),
    "Density": (47, 51),
    "PCT_1": (61, 63),
    "Regen_Method": (64, 64),
    "Util_DBH_cm": (74, 77),
    "OAF1": (80, 83),
    "OAF2": (86, 89),
    "FIZ": (93, 93),
    "SPP_1": (97, 99),
    "SI": (108, 111),
    "GW_1": (113, 116),
    "GW_age_1": (123, 125),
    "SPP_2": (129, 131),
    "PCT_2": (136, 137),
    "GW_2": (139, 142),
    "GW_age_2": (149, 151),
    "SPP_3": (155, 157),
    "PCT_3": (162, 163),
    "GW_3": (165, 168),
    "GW_age_3": (175, 177),
    "SPP_4": (181, 183),
    "PCT_4": (188, 189),
    "GW_4": (191, 194),
    "GW_age_4": (201, 203),
    "SPP_5": (207, 209),
    "PCT_5": (214, 215),
    "GW_5": (217, 220),
    "GW_age_5": (229, 231),
}
DEFAULT_TIPSY_DAT_ROW_STARTS: dict[str, int] = {
    col: start - 1 for col, (start, _end) in DEFAULT_TIPSY_BATCH_COLUMNS_1BASED.items()
}
DEFAULT_TIPSY_DAT_ROW_WIDTHS: dict[str, int] = {
    col: (end - start + 1)
    for col, (start, end) in DEFAULT_TIPSY_BATCH_COLUMNS_1BASED.items()
}
DEFAULT_TIPSY_DAT_HEADER_STARTS: dict[str, int] = {
    **DEFAULT_TIPSY_DAT_ROW_STARTS,
    "AU": 3,
}
_TIPSY_TEXT_COLUMNS = {
    "BEC",
    "Regen_Method",
    "FIZ",
    "SPP_1",
    "SPP_2",
    "SPP_3",
    "SPP_4",
    "SPP_5",
}


def _tipsy_dat_widths_from_starts(starts: Mapping[str, int]) -> dict[str, int]:
    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    widths: dict[str, int] = {}
    for idx, (key, start) in enumerate(ordered):
        next_start = ordered[idx + 1][1] if idx + 1 < len(ordered) else 231
        widths[key] = int(next_start - start)
    return widths


DEFAULT_TIPSY_DAT_COL_WIDTHS = DEFAULT_TIPSY_DAT_ROW_WIDTHS.copy()
DEFAULT_TIPSY_DAT_LINE_LENGTH = 231


def _format_tipsy_dat_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(float(value)):
            return ""
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _render_tipsy_dat_line(
    *,
    values: Mapping[str, Any],
    starts: Mapping[str, int],
    widths: Mapping[str, int],
    left_align_all: bool = False,
) -> str:
    line_len = max(starts[col] + widths[col] for col in starts)
    chars = [" "] * int(line_len)
    for col, start in starts.items():
        width = int(widths[col])
        text = _format_tipsy_dat_value(values.get(col, ""))[:width]
        if left_align_all or col in _TIPSY_TEXT_COLUMNS or col in {"AU", "TBLno"}:
            field = text.ljust(width)
        else:
            field = text.rjust(width)
        chars[start : start + width] = list(field)
    return "".join(chars)


def _validate_tipsy_dat_row(
    *,
    line: str,
    values: Mapping[str, Any],
    starts: Mapping[str, int],
    widths: Mapping[str, int],
) -> None:
    if len(line) != DEFAULT_TIPSY_DAT_LINE_LENGTH:
        raise ValueError(
            f"TIPSY DAT row length {len(line)} != expected {DEFAULT_TIPSY_DAT_LINE_LENGTH}"
        )
    for col in starts:
        expected = _format_tipsy_dat_value(values.get(col, ""))
        width = int(widths[col])
        if len(expected) > width:
            raise ValueError(
                f"TIPSY DAT value overflow for {col}: {expected!r} exceeds width {width}"
            )
        start = int(starts[col])
        actual = line[start : start + width].strip()
        if expected != actual:
            raise ValueError(
                f"TIPSY DAT slice mismatch for {col}: expected={expected!r}, actual={actual!r}"
            )


@dataclass(frozen=True)
class TIPSYCandidateEvaluation:
    """Eligibility outcome and derived metrics for one stratum+SI candidate."""

    eligible: bool
    reason: str | None
    species_map: Mapping[str, Any]
    leading_species: str | None
    bec: str
    max_vol: float
    min_vol: float
    operable_years: float
    si_vri_iqrlo: float
    si_spr_iqrlo: float
    si_vri_med: float
    si_spr_med: float
    min_si: float | None


def _tipsy_candidate_exception_types() -> tuple[type[Exception], ...]:
    """Candidate-evaluation failures that preserve legacy debug+re-raise behavior."""
    return (ValueError, KeyError, TypeError, AttributeError, RuntimeError, IndexError)


def compute_vdyp_site_index(
    vdyp_out: Mapping[Any, Any],
    *,
    ndigits: int = 1,
) -> float:
    """Compute mean SI across VDYP output tables, rounded for TIPSY input."""
    values: list[float] = []
    for table in vdyp_out.values():
        try:
            value = float(table["SI"].mean())
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            continue
        if np.isfinite(value):
            values.append(value)
    if not values:
        return float("nan")
    return round(float(np.mean(values)), ndigits)


def compute_vdyp_oaf1(vdyp_out: Mapping[Any, Any]) -> float:
    """Compute OAF1 from mean VDYP `% Stk` values, handling malformed tables."""
    stockability: list[float] = []
    for table in vdyp_out.values():
        try:
            value = float(table["% Stk"].iloc[0])
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            continue
        if np.isfinite(value):
            stockability.append(value)
    if not stockability:
        return float("nan")
    return round(float(np.mean(stockability)) * 0.01, 2)


def build_tipsy_warning_event(
    *,
    tsa: str,
    stratumi: int,
    sc: str,
    si_level: str,
    au: int,
    reason: str,
) -> dict[str, Any]:
    """Build standardized warning payload for TIPSY-input stage issues."""
    return build_timestamped_event(
        event="vdyp_curve_fit",
        status="warning",
        stage="tipsy_input",
        reason=reason,
        context={
            "tsa": tsa,
            "stratum_index": int(stratumi),
            "stratum_code": sc,
            "si_level": si_level,
            "au": int(au),
        },
    )


def build_tipsy_input_table(
    *,
    tipsy_params_for_tsa: Mapping[int, Mapping[str, Mapping[str, Any]]],
    tipsy_params_columns: Sequence[str],
    pd_module: Any,
    table_key: str = "f",
) -> Any:
    """Build TIPSY input table rows from per-AU parameter payloads."""
    rows: list[Any] = []
    for au in tipsy_params_for_tsa:
        table_map = tipsy_params_for_tsa[au].get(table_key)
        if table_map is None:
            continue
        if "TBLno" not in table_map:
            raise KeyError(f"missing TBLno in tipsy_params[{au!r}][{table_key!r}]")
        rows.append(pd_module.DataFrame(table_map, index=[table_map["TBLno"]]))
    if not rows:
        raise RuntimeError("No TIPSY parameter tables generated.")
    return pd_module.concat(rows)[list(tipsy_params_columns)]


def write_tipsy_input_exports(
    *,
    tipsy_table: Any,
    tsa: str,
    tipsy_params_path_prefix: str,
    dat_path_template: str = "./data/02_input-tsa{tsa}.dat",
) -> tuple[str, str]:
    """Write TIPSY input exports to XLSX and DAT outputs for one TSA."""
    table = tipsy_table.copy()
    unnamed_cols = [col for col in table.columns if str(col).startswith("Unnamed:")]
    if unnamed_cols:
        table = table.drop(columns=unnamed_cols)

    tipsy_excel_path = f"{tipsy_params_path_prefix}{tsa}.xlsx"
    tipsy_dat_path = dat_path_template.format(tsa=tsa)
    table.to_excel(
        tipsy_excel_path,
        index=False,
        sheet_name="TIPSY_inputTBL",
    )
    ordered_cols = list(DEFAULT_TIPSY_DAT_ROW_STARTS.keys())
    for col in ordered_cols:
        if col not in table.columns:
            table[col] = ""
    row_starts = {col: DEFAULT_TIPSY_DAT_ROW_STARTS[col] for col in ordered_cols}
    row_widths = {col: DEFAULT_TIPSY_DAT_ROW_WIDTHS[col] for col in ordered_cols}
    header_starts = {col: DEFAULT_TIPSY_DAT_HEADER_STARTS[col] for col in ordered_cols}
    header_widths = _tipsy_dat_widths_from_starts(header_starts)
    lines = [
        _render_tipsy_dat_line(
            values={col: col for col in ordered_cols},
            starts=header_starts,
            widths=header_widths,
            left_align_all=True,
        )
    ]
    for row in table[ordered_cols].itertuples(index=False):
        row_map = {col: val for col, val in zip(ordered_cols, row)}
        row_line = _render_tipsy_dat_line(
            values=row_map,
            starts=row_starts,
            widths=row_widths,
        )
        _validate_tipsy_dat_row(
            line=row_line,
            values=row_map,
            starts=row_starts,
            widths=row_widths,
        )
        lines.append(row_line)
    Path(tipsy_dat_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tipsy_excel_path, tipsy_dat_path


def tipsy_params_excel_path(
    *,
    tsa: str,
    tipsy_params_path_prefix: str | Path,
) -> Path:
    """Build legacy per-TSA TIPSY parameter workbook path."""
    return Path(f"{tipsy_params_path_prefix}{tsa}.xlsx")


def tipsy_input_dat_path(
    *,
    tsa: str,
    input_root: str | Path = "data",
    filename_template: str = "02_input-tsa{tsa}.dat",
) -> Path:
    """Build legacy per-TSA BatchTIPSY DAT handoff path."""
    return Path(input_root) / filename_template.format(tsa=tsa)


def tipsy_stage_output_paths(
    *,
    tsa: str,
    output_root: str | Path = "data",
) -> tuple[Path, Path]:
    """Build legacy 01b per-TSA output CSV paths."""
    root = Path(output_root)
    return (
        root / f"tipsy_curves_tsa{tsa}.csv",
        root / f"tipsy_sppcomp_tsa{tsa}.csv",
    )


def validate_tipsy_output_is_fresh(
    *,
    tipsy_input_excel_path: str | Path,
    tipsy_input_dat_path: str | Path | None = None,
    tipsy_output_path: str | Path,
    allow_stale: bool = False,
) -> None:
    """Fail fast when BatchTIPSY output is older than the current input workbook.

    Canonical operator contract uses ``02_input-tsaXX.dat`` as the real
    BatchTIPSY input; ``tipsy_params_tsaXX.xlsx`` is a human-readable mirror.
    This catches stale-output scenarios that would silently yield mismatched
    treated-curve overlays and downstream artifacts.
    """
    if allow_stale:
        return
    excel_path = Path(tipsy_input_excel_path)
    dat_path = Path(tipsy_input_dat_path) if tipsy_input_dat_path else None
    output_path = Path(tipsy_output_path)
    if not output_path.is_file():
        return
    if dat_path is not None and not dat_path.is_file():
        raise RuntimeError(
            "Missing canonical BatchTIPSY input DAT file: "
            f"{dat_path}. Generate 02_input-tsaXX.dat in Stage 01a before "
            "running Stage 01b/post-TIPSY."
        )
    input_candidates = []
    if dat_path is not None:
        input_candidates.append(dat_path)
    if excel_path.is_file():
        input_candidates.append(excel_path)
    if not input_candidates:
        return
    newest_input = max(input_candidates, key=lambda path: path.stat().st_mtime)
    input_mtime = newest_input.stat().st_mtime
    output_mtime = output_path.stat().st_mtime
    if output_mtime < input_mtime:
        raise RuntimeError(
            "Stale BatchTIPSY output detected: "
            f"{output_path} is older than {newest_input}. "
            "Regenerate 04_output-tsaXX.out from the current "
            "02_input-tsaXX.dat handoff (and matching workbook), then rerun "
            "FEMIC stage 01b/post-TIPSY."
        )


def evaluate_tipsy_candidate(
    *,
    sc: str,
    vdyp_curve_df: Any,
    result_si: Mapping[str, Any],
    exclusion: Mapping[str, Any],
    min_operable_years: float,
    si_iqrlo_quantile: float,
    siteprod_si_fallback_by_species: Mapping[str, float] | None = None,
) -> TIPSYCandidateEvaluation:
    """Evaluate whether a stratum+SI candidate is usable for TIPSY parameter generation."""
    sc_tokens = sc.split("_")
    if len(sc_tokens) < 2 or not sc_tokens[1]:
        raise ValueError(f"invalid stratum code format: {sc!r}")
    bec = sc_tokens[0]
    min_vol = float(exclusion["min_vol"](sc_tokens[1][0]))
    max_vol = float(vdyp_curve_df.volume.max())
    if max_vol < min_vol:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="max_vol_too_low",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=float("nan"),
            si_vri_iqrlo=float("nan"),
            si_spr_iqrlo=float("nan"),
            si_vri_med=float("nan"),
            si_spr_med=float("nan"),
            min_si=None,
        )
    operable_ages = vdyp_curve_df[vdyp_curve_df.volume >= min_vol].age
    operable_years = float(operable_ages.max() - operable_ages.min())
    if operable_years < min_operable_years:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="operability_window_too_narrow",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=float("nan"),
            si_spr_iqrlo=float("nan"),
            si_vri_med=float("nan"),
            si_spr_med=float("nan"),
            min_si=None,
        )
    ss = result_si["ss"]
    si_vri_iqrlo = float(ss.SITE_INDEX.quantile(si_iqrlo_quantile))
    si_vri_med = float(ss.SITE_INDEX.median())
    siteprod_series = ss.get("siteprod")
    if siteprod_series is None:
        si_spr_iqrlo = si_vri_iqrlo
        si_spr_med = si_vri_med
    else:
        siteprod_series = siteprod_series.dropna()
        siteprod_series = siteprod_series[siteprod_series > 0]
        if siteprod_series.empty:
            si_spr_iqrlo = si_vri_iqrlo
            si_spr_med = si_vri_med
        else:
            si_spr_iqrlo = float(siteprod_series.quantile(si_iqrlo_quantile))
            si_spr_med = float(siteprod_series.median())
    species_map: Mapping[str, Any] = result_si.get("species", {})
    if not species_map:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="no_species_candidates",
            species_map={},
            leading_species=None,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=None,
        )
    leading_species = list(species_map.keys())[0]
    if (siteprod_series is None) or siteprod_series.empty:
        fallback_si = None
        if siteprod_si_fallback_by_species:
            fallback_si = siteprod_si_fallback_by_species.get(
                str(leading_species).upper()
            )
        if fallback_si is not None and np.isfinite(float(fallback_si)):
            si_spr_iqrlo = float(fallback_si)
            si_spr_med = float(fallback_si)
    min_si = float(exclusion["min_si"](leading_species))
    if min(si_vri_iqrlo, si_spr_iqrlo) < min_si:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="si_too_low",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    if leading_species in exclusion["excl_leading_species"]:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="excluded_leading_species",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    if bec in exclusion["excl_bec"]:
        return TIPSYCandidateEvaluation(
            eligible=False,
            reason="excluded_bec",
            species_map=species_map,
            leading_species=leading_species,
            bec=bec,
            max_vol=max_vol,
            min_vol=min_vol,
            operable_years=operable_years,
            si_vri_iqrlo=si_vri_iqrlo,
            si_spr_iqrlo=si_spr_iqrlo,
            si_vri_med=si_vri_med,
            si_spr_med=si_spr_med,
            min_si=min_si,
        )
    return TIPSYCandidateEvaluation(
        eligible=True,
        reason=None,
        species_map=species_map,
        leading_species=leading_species,
        bec=bec,
        max_vol=max_vol,
        min_vol=min_vol,
        operable_years=operable_years,
        si_vri_iqrlo=si_vri_iqrlo,
        si_spr_iqrlo=si_spr_iqrlo,
        si_vri_med=si_vri_med,
        si_spr_med=si_spr_med,
        min_si=min_si,
    )


def build_tipsy_params_for_tsa(
    *,
    tsa: str,
    results_for_tsa: Sequence[tuple[int, str, Mapping[str, Any]]],
    si_levels: Sequence[str],
    vdyp_curves_smooth_tsa: Any,
    vdyp_results_for_tsa: Mapping[int, Mapping[str, Any]],
    exclusion: Mapping[str, Any],
    tipsy_param_builder: Any,
    vdyp_curve_events_path: Any = None,
    append_jsonl_fn: Any = None,
    min_operable_years: float = 50.0,
    si_iqrlo_quantile: float = 0.50,
    si_merge_enabled: bool = True,
    si_merge_max_relative_gap: float = 0.08,
    si_merge_max_window_nrmse: float = 0.12,
    si_merge_min_common_ages: int = 5,
    si_merge_age_min: int = 30,
    si_merge_age_max: int = 250,
    verbose: bool = True,
    message_fn: Any = print,
) -> tuple[
    dict[tuple[str, str], int],
    dict[int, tuple[str, str]],
    dict[int, dict[str, dict[str, Any]]],
]:
    """Select eligible strata+SI combos and build TIPSY params for one TSA."""
    scsi_au_tsa: dict[tuple[str, str], int] = {}
    au_scsi_tsa: dict[int, tuple[str, str]] = {}
    tipsy_params_tsa: dict[int, dict[str, dict[str, Any]]] = {}

    vdyp_indexed = vdyp_curves_smooth_tsa.set_index(["stratum_code", "si_level"])
    vdyp_strata = set(vdyp_indexed.index.get_level_values("stratum_code"))
    siteprod_si_fallback_by_species = getattr(
        tipsy_param_builder,
        "siteprod_si_fallback_by_species",
        None,
    )
    if not isinstance(siteprod_si_fallback_by_species, Mapping):
        siteprod_si_fallback_by_species = None

    def _curve_df(sc_code: str, si_level: str) -> Any | None:
        try:
            df_ = vdyp_indexed.loc[sc_code, si_level]
        except KeyError:
            return None
        if not hasattr(df_, "columns") and hasattr(df_, "to_frame"):
            df_ = df_.to_frame().T
        return df_

    def _curve_merge_metrics(df_a: Any, df_b: Any) -> tuple[float, float, float]:
        series_a = (
            df_a[(df_a["age"] >= si_merge_age_min) & (df_a["age"] <= si_merge_age_max)]
            .groupby("age")["volume"]
            .mean()
        )
        series_b = (
            df_b[(df_b["age"] >= si_merge_age_min) & (df_b["age"] <= si_merge_age_max)]
            .groupby("age")["volume"]
            .mean()
        )
        common_ages = sorted(set(series_a.index).intersection(series_b.index))
        if len(common_ages) < int(si_merge_min_common_ages):
            return float("inf"), float("inf"), float("inf")
        a_vals = series_a.loc[common_ages].values.astype(float)
        b_vals = series_b.loc[common_ages].values.astype(float)
        denom = np.maximum(np.maximum(np.abs(a_vals), np.abs(b_vals)), 1e-9)
        rel_gap = np.abs(a_vals - b_vals) / denom
        if rel_gap.size == 0:
            return float("inf"), float("inf"), float("inf")
        diff = a_vals - b_vals
        rmse = float(np.sqrt(np.mean(np.square(diff))))
        scale = float(np.maximum(np.nanmean(np.maximum(a_vals, b_vals)), 1e-9))
        nrmse = float(rmse / scale)
        return float(np.nanmax(rel_gap)), rmse, nrmse

    for stratumi, sc, result in results_for_tsa:
        message_fn(sc)
        if sc not in vdyp_strata:
            if verbose:
                message_fn("  missing vdyp curves for stratum", sc)
            continue

        present_levels = [
            si_level
            for si_level in si_levels
            if _curve_df(sc, si_level) is not None
            and isinstance(result.get(si_level), Mapping)
        ]
        merge_groups: list[list[str]] = []
        if si_merge_enabled and present_levels:
            for level in present_levels:
                if not merge_groups:
                    merge_groups.append([level])
                    continue
                prev_level = merge_groups[-1][-1]
                prev_df = _curve_df(sc, prev_level)
                cur_df = _curve_df(sc, level)
                if prev_df is None or cur_df is None:
                    merge_groups.append([level])
                    continue
                gap, rmse, nrmse = _curve_merge_metrics(prev_df, cur_df)
                if (gap <= float(si_merge_max_relative_gap)) and (
                    nrmse <= float(si_merge_max_window_nrmse)
                ):
                    merge_groups[-1].append(level)
                    if verbose:
                        message_fn(
                            "    merge metrics",
                            f"{prev_level}+{level}",
                            f"gap={gap:0.3f}",
                            f"rmse={rmse:0.1f}",
                            f"nrmse={nrmse:0.3f}",
                        )
                else:
                    merge_groups.append([level])
        elif present_levels:
            merge_groups = [[level] for level in present_levels]

        if merge_groups:
            message_fn(
                "  si-groups",
                ", ".join("[" + "+".join(group) + "]" for group in merge_groups),
            )

        # Map all SI levels (including non-representatives) to their group representative.
        representative_for_level: dict[str, str] = {}
        group_by_representative: dict[str, list[str]] = {}
        for group in merge_groups:
            rep = group[len(group) // 2]
            group_by_representative[rep] = group
            for level in group:
                representative_for_level[level] = rep

        for i, si_level in enumerate(si_levels, start=1):
            if si_level not in representative_for_level:
                if verbose:
                    message_fn("  missing fit result for", sc, si_level)
                continue
            rep_level = representative_for_level[si_level]
            if si_level != rep_level:
                continue
            au = 1000 * i + stratumi
            group_levels = group_by_representative.get(rep_level, [rep_level])
            result_si = result.get(rep_level)
            if not isinstance(result_si, Mapping):
                if verbose:
                    message_fn("  missing fit result for", sc, rep_level)
                continue
            df = _curve_df(sc, rep_level)
            if df is None:
                if verbose:
                    message_fn("  missing vdyp curves for", sc, rep_level)
                continue
            try:
                candidate = evaluate_tipsy_candidate(
                    sc=sc,
                    vdyp_curve_df=df,
                    result_si=result_si,
                    exclusion=exclusion,
                    min_operable_years=min_operable_years,
                    si_iqrlo_quantile=si_iqrlo_quantile,
                    siteprod_si_fallback_by_species=siteprod_si_fallback_by_species,
                )
            except _tipsy_candidate_exception_types():
                message_fn(sc, si_level)
                message_fn(result[si_level]["ss"])
                raise
            if not candidate.eligible:
                if verbose and candidate.reason == "max_vol_too_low":
                    message_fn(
                        "  ",
                        si_level,
                        "max_vol too low",
                        candidate.max_vol,
                        candidate.min_vol,
                    )
                elif verbose and candidate.reason == "operability_window_too_narrow":
                    message_fn(
                        "  ",
                        si_level,
                        "operability window too narrow",
                        candidate.operable_years,
                        min_operable_years,
                    )
                elif verbose and candidate.reason == "si_too_low":
                    message_fn(
                        "  ",
                        si_level,
                        "SI too low (using %0.2f quantile)" % si_iqrlo_quantile,
                        "%2.1f" % candidate.si_vri_iqrlo,
                        "%2.1f" % candidate.si_spr_iqrlo,
                        candidate.min_si,
                    )
                elif verbose and candidate.reason == "excluded_leading_species":
                    message_fn(
                        "  ",
                        si_level,
                        "bad leading species",
                        candidate.leading_species,
                    )
                elif verbose and candidate.reason == "excluded_bec":
                    message_fn("  ", si_level, "bad bec", candidate.bec)
                elif verbose and candidate.reason == "no_species_candidates":
                    message_fn("  ", si_level, "no species candidates after filtering")
                if append_jsonl_fn is not None and vdyp_curve_events_path is not None:
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_tipsy_warning_event(
                            tsa=tsa,
                            stratumi=int(stratumi),
                            sc=sc,
                            si_level=rep_level,
                            au=int(au),
                            reason="no_species_candidates",
                        ),
                    )
                continue

            message_fn("  ", rep_level, au)
            if len(group_levels) > 1:
                message_fn("    merged si levels", "+".join(group_levels))
            message_fn(
                "    median SI (VRI)               ",
                ("%2.1f" % candidate.si_vri_med).rjust(4),
            )
            message_fn(
                "    median SI (siteprod)          ",
                ("%2.1f" % candidate.si_spr_med).rjust(4),
            )
            message_fn(
                "    median SI ratio (VRI/siteprod) ",
                "%0.2f" % (candidate.si_vri_med / candidate.si_spr_med),
            )
            for species, v in candidate.species_map.items():
                message_fn("    species", species.ljust(3), "%3.0f" % v["pct"])
            vdyp_result = vdyp_results_for_tsa.get(stratumi, {}).get(rep_level)
            if not isinstance(vdyp_result, dict):
                if verbose:
                    message_fn("    missing vdyp result table for", sc, rep_level)
                if append_jsonl_fn is not None and vdyp_curve_events_path is not None:
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_tipsy_warning_event(
                            tsa=tsa,
                            stratumi=int(stratumi),
                            sc=sc,
                            si_level=rep_level,
                            au=int(au),
                            reason="missing_vdyp_output",
                        ),
                    )
                continue
            for level in group_levels:
                scsi_au_tsa[(sc, level)] = au
            au_scsi_tsa[au] = (sc, rep_level)
            tipsy_params_tsa[au] = tipsy_param_builder(au, result_si, vdyp_result)
            message_fn()
    return scsi_au_tsa, au_scsi_tsa, tipsy_params_tsa
