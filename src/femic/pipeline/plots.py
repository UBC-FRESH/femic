"""Plot artifact naming helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import pandas as pd


def strata_plot_paths(tsa_code: str, root: Path = Path("plots")) -> tuple[Path, Path]:
    """Return PDF/PNG output paths for strata diagnostics for one TSA/case code."""
    tsa = str(tsa_code).zfill(2)
    return root / f"strata-tsa{tsa}.pdf", root / f"strata-tsa{tsa}.png"


def tipsy_vdyp_plot_path(au: int, tsa_code: str, root: Path = Path("plots")) -> Path:
    """Return the canonical TIPSY-vs-VDYP overlay plot path for an AU."""
    tsa = str(tsa_code).zfill(2)
    return root / f"tipsy_vdyp_tsa{tsa}-{au}.png"


def tipsy_vdyp_ylim_for_tsa(
    tsa_code: str,
    default: tuple[float, float] = (0.0, 600.0),
    configured: tuple[float, float] | None = None,
) -> tuple[float, float]:
    """Return legacy TIPSY-vs-VDYP plot y-limits for a TSA/custom unit."""
    _ = tsa_code
    if configured is not None:
        return configured
    return default


@dataclass(frozen=True)
class StrataDistributionPlotConfig:
    """Defaults for the 01a stratum-distribution diagnostic plot."""

    figsize: tuple[float, float]
    alpha: float
    linewidth: float
    inner: str
    width: float
    bw: str
    cut: float
    site_index_xlim: tuple[float, float]
    site_index_focus_quantiles: tuple[float, float]
    site_index_focus_padding: float
    stripplot_alpha: float
    stripplot_size: float
    stripplot_max_points: int
    stripplot_min_points_per_stratum: int
    stripplot_random_seed: int
    write_pdf: bool


@dataclass(frozen=True)
class StrataDistributionPlotMetadata:
    """Runtime metadata for one rendered stratum SI diagnostic plot."""

    site_index_xlim: tuple[float, float]
    total_points: int
    window_points: int
    strip_points_plotted: int
    clipped_low_count: int
    clipped_high_count: int

    @property
    def clipped_total_count(self) -> int:
        """Return total number of SITE_INDEX points clipped from view window."""
        return int(self.clipped_low_count + self.clipped_high_count)


def build_strata_distribution_plot_config(
    *,
    figsize: tuple[float, float] = (8, 12),
    alpha: float = 0.2,
    linewidth: float = 1.0,
    inner: str = "box",
    width: float = 0.8,
    bw: str = "scott",
    cut: float = 0.0,
    site_index_xlim: tuple[float, float] = (0, 30),
    site_index_focus_quantiles: tuple[float, float] = (0.02, 0.98),
    site_index_focus_padding: float = 0.75,
    stripplot_alpha: float = 0.15,
    stripplot_size: float = 1.4,
    stripplot_max_points: int = 3000,
    stripplot_min_points_per_stratum: int = 1,
    stripplot_random_seed: int = 19,
    write_pdf: bool = False,
) -> StrataDistributionPlotConfig:
    """Build defaults for 01a stratum abundance/SI violin diagnostics."""
    return StrataDistributionPlotConfig(
        figsize=figsize,
        alpha=alpha,
        linewidth=linewidth,
        inner=inner,
        width=width,
        bw=bw,
        cut=cut,
        site_index_xlim=site_index_xlim,
        site_index_focus_quantiles=site_index_focus_quantiles,
        site_index_focus_padding=site_index_focus_padding,
        stripplot_alpha=stripplot_alpha,
        stripplot_size=stripplot_size,
        stripplot_max_points=stripplot_max_points,
        stripplot_min_points_per_stratum=stripplot_min_points_per_stratum,
        stripplot_random_seed=stripplot_random_seed,
        write_pdf=write_pdf,
    )


def _resolve_site_index_window(
    *,
    site_index: pd.Series,
    cap_xlim: tuple[float, float],
    focus_quantiles: tuple[float, float],
    focus_padding: float,
) -> tuple[tuple[float, float], int, int]:
    """Resolve SI view window with a fixed floor and quantile-based upper focus."""
    values = pd.to_numeric(site_index, errors="coerce").dropna()
    if values.empty:
        return (float(cap_xlim[0]), float(cap_xlim[1])), 0, 0

    cap_lo = float(cap_xlim[0])
    cap_hi = float(cap_xlim[1])
    if not math.isfinite(cap_lo) or not math.isfinite(cap_hi) or cap_lo >= cap_hi:
        cap_lo, cap_hi = 0.0, 30.0

    q_lo, q_hi = focus_quantiles
    if not (0.0 <= q_lo < q_hi <= 1.0):
        q_lo, q_hi = 0.02, 0.98

    pad = max(float(focus_padding), 0.0)
    core_lo = float(values.quantile(q_lo))
    core_hi = float(values.quantile(q_hi))
    if not math.isfinite(core_lo) or not math.isfinite(core_hi):
        core_lo, core_hi = cap_lo, cap_hi

    # Keep the lower axis bound fixed so left-side violin tails remain visible.
    window_lo = cap_lo
    window_hi = min(cap_hi, math.ceil(core_hi + pad))
    if window_hi <= window_lo:
        window_lo, window_hi = cap_lo, cap_hi

    clipped_low = int((values < window_lo).sum())
    clipped_high = int((values > window_hi).sum())
    return (float(window_lo), float(window_hi)), clipped_low, clipped_high


def _thin_stripplot_points(
    *,
    plot_frame: pd.DataFrame,
    stratum_col: str,
    max_points: int,
    min_points_per_stratum: int,
    random_seed: int,
) -> pd.DataFrame:
    """Downsample stripplot points while retaining at least a small per-stratum sample."""
    if max_points <= 0 or len(plot_frame) <= max_points:
        return plot_frame

    work = plot_frame.reset_index(drop=False).copy()
    work["_femic_plot_row"] = range(len(work))
    min_per = max(int(min_points_per_stratum), 0)

    if min_per > 0:
        keepers = work.groupby(stratum_col, sort=False, group_keys=False).head(min_per)
    else:
        keepers = work.iloc[0:0]

    if len(keepers) >= max_points:
        sampled = keepers.sample(n=max_points, random_state=random_seed)
    else:
        budget = max_points - len(keepers)
        if budget > 0:
            remaining = work.loc[
                ~work["_femic_plot_row"].isin(keepers["_femic_plot_row"])
            ]
            sampled_rest = remaining.sample(
                n=min(budget, len(remaining)),
                random_state=random_seed,
            )
            sampled = pd.concat([keepers, sampled_rest], axis=0, ignore_index=False)
        else:
            sampled = keepers

    sampled = sampled.drop(columns=["_femic_plot_row"])
    return sampled


def resolve_strata_plot_ordering(
    *,
    strata_df: Any,
    sort_lex: bool = False,
) -> tuple[list[float], list[str]]:
    """Resolve stratum bar/violin ordering inputs for 01a diagnostics plots."""
    if sort_lex:
        ordered = strata_df.sort_index()
    else:
        ordered = strata_df
    if "totalarea_p" in ordered.columns and not ordered["totalarea_p"].isna().all():
        abundance = ordered["totalarea_p"]
    elif "coverage" in ordered.columns:
        abundance = ordered["coverage"]
    else:
        abundance = ordered.iloc[:, 0]
    abundance = abundance.fillna(0.0).astype(float)
    stratum_props = [float(v) for v in abundance.values]
    labels = [str(v) for v in ordered.index.values]
    return stratum_props, labels


def plot_strata_site_index_diagnostics(
    *,
    strata_df: Any,
    np_module: Any,
    plt_module: Any,
    hist_xlim: tuple[float, float] = (0, 25),
    hist_bin_stop: float = 25,
    hist_bin_step: float = 1,
) -> None:
    """Render early 01a strata diagnostics (SI histogram + abundance scatter)."""
    ax = strata_df.site_index_median.hist(
        bins=np_module.arange(hist_bin_stop, step=hist_bin_step)
    )
    x_lo = float(hist_xlim[0])
    x_hi = float(hist_xlim[1])
    try:
        observed_max = float(getattr(strata_df.site_index_median, "max")())
    except (AttributeError, TypeError, ValueError):
        observed_max = x_hi
    if math.isfinite(observed_max):
        x_hi = max(x_hi, observed_max + 1.0)
    ax.set_xlim([x_lo, x_hi])
    plt_module.scatter(strata_df.totalarea_p, strata_df.median_si)


def render_strata_distribution_plot(
    *,
    tsa_code: str,
    f_table: Any,
    stratum_col: str,
    labels: list[str],
    stratum_props: list[float],
    plot_config: StrataDistributionPlotConfig,
    sns_module: Any,
    plt_module: Any,
    strata_plot_paths_fn: Any = strata_plot_paths,
) -> StrataDistributionPlotMetadata:
    """Render and save the 01a stratum distribution bar+violin diagnostic plot."""
    plot_frame = f_table.reset_index().copy()
    plot_frame["SITE_INDEX"] = pd.to_numeric(plot_frame["SITE_INDEX"], errors="coerce")
    plot_frame = plot_frame.dropna(subset=["SITE_INDEX"])

    window_xlim, clipped_low, clipped_high = _resolve_site_index_window(
        site_index=plot_frame["SITE_INDEX"],
        cap_xlim=plot_config.site_index_xlim,
        focus_quantiles=plot_config.site_index_focus_quantiles,
        focus_padding=plot_config.site_index_focus_padding,
    )

    window_mask = (plot_frame["SITE_INDEX"] >= window_xlim[0]) & (
        plot_frame["SITE_INDEX"] <= window_xlim[1]
    )
    window_frame = plot_frame.loc[window_mask].copy()
    if window_frame.empty:
        window_frame = plot_frame.copy()
        clipped_low = 0
        clipped_high = 0

    strip_frame = _thin_stripplot_points(
        plot_frame=window_frame,
        stratum_col=stratum_col,
        max_points=plot_config.stripplot_max_points,
        min_points_per_stratum=plot_config.stripplot_min_points_per_stratum,
        random_seed=plot_config.stripplot_random_seed,
    )

    _fig, ax = plt_module.subplots(figsize=plot_config.figsize)
    ax2 = ax.twiny()
    sns_module.barplot(
        y=labels,
        x=stratum_props,
        ax=ax,
        alpha=plot_config.alpha,
        label="Relative abundance of stratum (proportion of total area)",
    )
    sns_module.violinplot(
        y=stratum_col,
        x="SITE_INDEX",
        data=window_frame,
        ax=ax2,
        bw_method=plot_config.bw,
        order=labels,
        linewidth=plot_config.linewidth,
        inner=plot_config.inner,
        width=plot_config.width,
        cut=plot_config.cut,
    )
    # Keep sparse strata visible when violin KDE is underdetermined.
    sns_module.stripplot(
        y=stratum_col,
        x="SITE_INDEX",
        data=strip_frame,
        ax=ax2,
        order=labels,
        color="black",
        alpha=plot_config.stripplot_alpha,
        size=plot_config.stripplot_size,
    )
    ax.set_xlabel("Relative abundance of stratum (proportion of total area)")
    ax2.set_xlim(window_xlim)
    strata_pdf_path, strata_png_path = strata_plot_paths_fn(tsa_code)
    if plot_config.write_pdf:
        plt_module.savefig(strata_pdf_path, bbox_inches="tight")
    plt_module.savefig(strata_png_path, facecolor="white", bbox_inches="tight")
    return StrataDistributionPlotMetadata(
        site_index_xlim=window_xlim,
        total_points=int(len(plot_frame)),
        window_points=int(len(window_frame)),
        strip_points_plotted=int(len(strip_frame)),
        clipped_low_count=int(clipped_low),
        clipped_high_count=int(clipped_high),
    )
