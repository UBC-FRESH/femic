"""Typed runtime payloads for legacy 00/01a/01b orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from femic.pipeline.vdyp import build_vdyp_cache_paths


@dataclass(frozen=True)
class Legacy01ARuntimeConfig:
    """Runtime payload passed from `00_data-prep.py` into `01a_run-tsa.py`."""

    resume_effective: bool
    force_run_vdyp: bool
    kwarg_overrides_for_tsa: dict[str, dict[str, Any]] | None
    vdyp_results_pickle_path: str | Path
    vdyp_input_pandl_path: str | Path
    vdyp_ply_feather_path: str | Path
    vdyp_lyr_feather_path: str | Path
    tipsy_params_columns: Sequence[str]
    tipsy_params_path_prefix: str | Path
    vdyp_cache_paths: Mapping[str, Path]
    parallel_worker_count: int = 1
    vdyp_out_cache: dict[str, Any] | None = None
    curve_fit_impl: Any = None
    target_area_coverage: float | None = None
    target_nstrata: int | None = None
    vdyp_sampling_mode: str | int = "auto"
    vdyp_two_pass_rebin: bool = False
    min_stands_per_si_bin: int = 25
    force_tail_blend_candidate: bool = False
    enable_late_gate_rescue: bool = True


@dataclass(frozen=True)
class Legacy01BRuntimeConfig:
    """Runtime payload passed from `00_data-prep.py` into `01b_run-tsa.py`."""

    tipsy_params_path_prefix: str | Path
    tipsy_output_root: str | Path
    tipsy_input_filename_template: str = "03_input-tsa{tsa}.csv"
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.csv"


def build_legacy_01a_runtime_config(
    *,
    tsa_code: str,
    resume_effective: bool,
    force_run_vdyp: bool,
    kwarg_overrides_for_tsa: dict[str, dict[str, Any]] | None,
    vdyp_results_pickle_path: str | Path,
    vdyp_input_pandl_path: str | Path,
    vdyp_ply_feather_path: str | Path,
    vdyp_lyr_feather_path: str | Path,
    tipsy_params_columns: Sequence[str],
    tipsy_params_path_prefix: str | Path,
    vdyp_results_tsa_pickle_path_prefix: str | Path,
    vdyp_curves_smooth_tsa_feather_path_prefix: str | Path,
    parallel_worker_count: int = 1,
    vdyp_out_cache: dict[str, Any] | None = None,
    curve_fit_impl: Any = None,
    target_area_coverage: float | None = None,
    target_nstrata: int | None = None,
    vdyp_sampling_mode: str | int = "auto",
    vdyp_two_pass_rebin: bool = False,
    min_stands_per_si_bin: int = 25,
    force_tail_blend_candidate: bool = False,
    enable_late_gate_rescue: bool = True,
) -> Legacy01ARuntimeConfig:
    """Build typed runtime config payload for a single 01a TSA run."""
    vdyp_cache_paths = build_vdyp_cache_paths(
        tsa_code=str(tsa_code),
        vdyp_results_tsa_pickle_path_prefix=vdyp_results_tsa_pickle_path_prefix,
        vdyp_curves_smooth_tsa_feather_path_prefix=vdyp_curves_smooth_tsa_feather_path_prefix,
    )
    return Legacy01ARuntimeConfig(
        resume_effective=bool(resume_effective),
        force_run_vdyp=bool(force_run_vdyp),
        kwarg_overrides_for_tsa=kwarg_overrides_for_tsa,
        vdyp_results_pickle_path=vdyp_results_pickle_path,
        vdyp_input_pandl_path=vdyp_input_pandl_path,
        vdyp_ply_feather_path=vdyp_ply_feather_path,
        vdyp_lyr_feather_path=vdyp_lyr_feather_path,
        tipsy_params_columns=tipsy_params_columns,
        tipsy_params_path_prefix=tipsy_params_path_prefix,
        vdyp_cache_paths=vdyp_cache_paths,
        parallel_worker_count=max(int(parallel_worker_count), 1),
        vdyp_out_cache=vdyp_out_cache,
        curve_fit_impl=curve_fit_impl,
        target_area_coverage=target_area_coverage,
        target_nstrata=target_nstrata,
        vdyp_sampling_mode=vdyp_sampling_mode,
        vdyp_two_pass_rebin=bool(vdyp_two_pass_rebin),
        min_stands_per_si_bin=max(int(min_stands_per_si_bin), 1),
        force_tail_blend_candidate=bool(force_tail_blend_candidate),
        enable_late_gate_rescue=bool(enable_late_gate_rescue),
    )


def build_legacy_01b_runtime_config(
    *,
    tipsy_params_path_prefix: str | Path,
    tipsy_output_root: str | Path = "data",
    tipsy_input_filename_template: str = "03_input-tsa{tsa}.csv",
    tipsy_output_filename_template: str = "04_output-tsa{tsa}.csv",
) -> Legacy01BRuntimeConfig:
    """Build typed runtime config payload for a single 01b TSA run."""
    return Legacy01BRuntimeConfig(
        tipsy_params_path_prefix=tipsy_params_path_prefix,
        tipsy_output_root=tipsy_output_root,
        tipsy_input_filename_template=tipsy_input_filename_template,
        tipsy_output_filename_template=tipsy_output_filename_template,
    )
