"""VDYP execution stage helpers for legacy notebook migration."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import functools
import importlib
import math
import os
import pickle
import shlex
import subprocess
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, cast

import numpy as np

from femic.pipeline.diagnostics import (
    build_contextual_error_message,
    build_timestamped_event,
)
from femic.pipeline.tsa import resolve_si_level_quantiles_for_stratum
from femic.pipeline.vdyp_curves import detect_linear_tail_segment


@dataclass(frozen=True)
class SmoothedCurveResult:
    """One smoothed curve result for a stratum/SI combination."""

    stratumi: int
    stratum_code: str
    si_level: str
    x: Sequence[float]
    y: Sequence[float]
    vdyp_out: dict[Any, Any]


@dataclass(frozen=True)
class CurveSmoothingPlotConfig:
    """Plot defaults for legacy VDYP curve-smoothing overlays."""

    plot: bool
    figsize: tuple[float, float]
    palette: tuple[Any, ...]
    palette_flavours: tuple[str, ...]
    alphas: tuple[float, ...]
    xlim: tuple[float, float]
    ylim: tuple[float, float]


@dataclass(frozen=True)
class StratumFitRunConfig:
    """Defaults for pre-VDYP stratum curve-fit compilation runs."""

    fit_rawdata: bool
    min_stands_per_si_bin: int
    min_age: int
    agg_type: str
    plot: bool
    verbose: bool
    figsize: tuple[float, float]
    ylim: tuple[float, float]
    xlim: tuple[float, float]


@dataclass(frozen=True)
class VdypBatchTempArtifacts:
    """Resolved temp-file names and absolute paths for one VDYP batch run."""

    vdyp_ply_csv: str
    vdyp_lyr_csv: str
    vdyp_out_txt: str
    vdyp_err_txt: str
    out_path: Path
    err_path: Path


@dataclass(frozen=True)
class VdypRunEventCounts:
    """Normalized integer count fields shared by VDYP run events/headers."""

    feature_count: int
    cache_hits: int
    ply_rows: int
    lyr_rows: int


@dataclass(frozen=True)
class VdypBatchExecutionDependencies:
    """Resolved callable dependencies used by `execute_vdyp_batch(...)`."""

    write_vdyp_infiles: Callable[..., None]
    import_vdyp_tables: Callable[[str], dict[Any, Any]]
    append_jsonl: Callable[[str | Path, Any], None]
    append_text: Callable[[str | Path, str], None]
    build_stream_header: Callable[..., str]
    build_stream_log_block: Callable[..., str]
    subprocess_run: Callable[..., Any]


def _curve_fit_skip_exception_types() -> tuple[type[Exception], ...]:
    """Curve-fit failures that should skip one species and continue."""
    return (
        RuntimeError,
        ValueError,
        TypeError,
        OverflowError,
        FloatingPointError,
    )


def _subprocess_run_exception_types() -> tuple[type[Exception], ...]:
    """Subprocess launch/exec failures that should emit VDYP run error records."""
    return (OSError, ValueError, subprocess.SubprocessError)


def _vdyp_parse_exception_types() -> tuple[type[Exception], ...]:
    """VDYP output parse/import failures that should emit parse_error records."""
    return (OSError, ValueError, TypeError, KeyError, UnicodeError)


def _bootstrap_dispatch_exception_types() -> tuple[type[Exception], ...]:
    """VDYP dispatch failures that should emit bootstrap dispatch_error events."""
    return (
        RuntimeError,
        ValueError,
        TypeError,
        OSError,
        KeyError,
        subprocess.SubprocessError,
    )


def _as_path(path: str | Path) -> Path:
    """Normalize path-like inputs to `Path`."""
    return path if isinstance(path, Path) else Path(path)


def _sampling_seed_from_env(env_key: str = "FEMIC_SAMPLING_SEED") -> int | None:
    """Resolve optional sampling seed from env for deterministic bootstrap sampling."""
    raw = os.environ.get(env_key)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(
            build_contextual_error_message(
                prefix="Invalid FEMIC sampling seed",
                context={env_key: raw, "expected": "integer"},
            )
        ) from exc


def resolve_vdyp_batch_execution_dependencies(
    *,
    write_vdyp_infiles: Callable[..., None] | None,
    import_vdyp_tables_fn: Callable[[str], dict[Any, Any]] | None,
    append_jsonl_fn: Callable[[str | Path, Any], None] | None,
    append_text_fn: Callable[[str | Path, str], None] | None,
    build_stream_header_fn: Callable[..., str] | None,
    build_stream_log_block_fn: Callable[..., str] | None,
    subprocess_run: Callable[..., Any] | None,
) -> VdypBatchExecutionDependencies:
    """Resolve injected/default callable dependencies for VDYP batch execution."""
    resolved_write = write_vdyp_infiles
    if resolved_write is None:
        from femic.pipeline.vdyp_io import (
            write_vdyp_infiles_plylyr as resolved_write,
        )
    resolved_import = import_vdyp_tables_fn
    if resolved_import is None:
        from femic.pipeline.vdyp_io import import_vdyp_tables as resolved_import
    resolved_append_jsonl = append_jsonl_fn
    if resolved_append_jsonl is None:
        from femic.pipeline.vdyp_logging import append_jsonl as resolved_append_jsonl
    resolved_append_text = append_text_fn
    if resolved_append_text is None:
        from femic.pipeline.vdyp_logging import append_text as resolved_append_text
    resolved_build_header = build_stream_header_fn
    if resolved_build_header is None:
        from femic.pipeline.vdyp_logging import (
            build_vdyp_stream_header as resolved_build_header,
        )
    resolved_build_block = build_stream_log_block_fn
    if resolved_build_block is None:
        from femic.pipeline.vdyp_logging import (
            build_vdyp_stream_log_block as resolved_build_block,
        )
    resolved_subprocess_run = subprocess_run or subprocess.run
    return VdypBatchExecutionDependencies(
        write_vdyp_infiles=cast(Callable[..., None], resolved_write),
        import_vdyp_tables=cast(
            Callable[[str], dict[Any, Any]],
            resolved_import,
        ),
        append_jsonl=cast(Callable[[str | Path, Any], None], resolved_append_jsonl),
        append_text=cast(Callable[[str | Path, str], None], resolved_append_text),
        build_stream_header=cast(Callable[..., str], resolved_build_header),
        build_stream_log_block=cast(Callable[..., str], resolved_build_block),
        subprocess_run=cast(Callable[..., Any], resolved_subprocess_run),
    )


def build_vdyp_batch_command(
    *,
    vdyp_binpath: str,
    vdyp_params_infile: str,
    vdyp_io_dir: str | Path,
    vdyp_ply_csv: str,
    vdyp_lyr_csv: str,
    vdyp_out_txt: str,
    vdyp_err_txt: str,
    vdyp_cfg_dir: str | Path | None = None,
) -> str:
    """Build legacy VDYP command text used for execution and logging metadata."""
    vdyp_io_dir_str = _as_path(vdyp_io_dir).as_posix()

    def _rel_io_path(filename: str) -> str:
        return f"./{vdyp_io_dir_str}/{filename}"

    parts: list[str] = []
    if os.name != "nt":
        parts.append("wine")
    parts.extend([vdyp_binpath, "-p", vdyp_params_infile])
    if os.name == "nt":
        resolved_cfg = None
        if vdyp_cfg_dir is not None:
            resolved_cfg = str(_as_path(vdyp_cfg_dir))
        elif os.environ.get("FEMIC_VDYP_CFG_DIR"):
            resolved_cfg = str(_as_path(os.environ["FEMIC_VDYP_CFG_DIR"]))
        if resolved_cfg:
            if not resolved_cfg.endswith(("\\", "/")):
                resolved_cfg = resolved_cfg + "\\"
            parts.extend(["-c", resolved_cfg])
    parts.extend(
        [
            "-ip",
            _rel_io_path(vdyp_ply_csv),
            "-il",
            _rel_io_path(vdyp_lyr_csv),
            "-o",
            _rel_io_path(vdyp_out_txt),
            "-e",
            _rel_io_path(vdyp_err_txt),
        ]
    )
    return subprocess.list2cmdline(parts)


def collect_vdyp_batch_run_metadata(
    *,
    result: Any,
    out_path: str | Path,
    err_path: str | Path,
    run_started: float,
    time_fn: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Collect subprocess/file metadata shared by parse-error and success events."""
    out_path_ = _as_path(out_path)
    err_path_ = _as_path(err_path)
    err_size = err_path_.stat().st_size if err_path_.exists() else 0
    err_head = ""
    if err_size:
        err_head = err_path_.read_text(encoding="utf-8", errors="ignore")[:500]
    out_size = out_path_.stat().st_size if out_path_.exists() else 0
    return {
        "returncode": getattr(result, "returncode", None),
        "duration_sec": round(time_fn() - run_started, 3),
        "out_size": int(out_size),
        "err_size": int(err_size),
        "err_head": err_head,
        "proc_stdout_head": (result.stdout or "")[:500],
        "proc_stderr_head": (result.stderr or "")[:500],
    }


def build_vdyp_run_context(
    *,
    base_context: Mapping[str, Any] | None = None,
    tsa: str | None = None,
    run_id: str | None = None,
    vdyp_stdout_log_path: str | Path | None = None,
    vdyp_stderr_log_path: str | Path | None = None,
    vdyp_binpath: str | Path | None = None,
    vdyp_params: str | Path | None = None,
) -> dict[str, Any]:
    """Build VDYP run context payload while preserving caller-provided values."""

    def _normalize_context_path(value: str | Path) -> str:
        if isinstance(value, Path):
            return value.as_posix()
        return str(value)

    context = dict(base_context or {})
    if tsa is not None:
        context.setdefault("tsa", tsa)
    if run_id is not None:
        context.setdefault("run_id", run_id)
    if vdyp_stdout_log_path is not None:
        context.setdefault(
            "vdyp_stdout_log", _normalize_context_path(vdyp_stdout_log_path)
        )
    if vdyp_stderr_log_path is not None:
        context.setdefault(
            "vdyp_stderr_log", _normalize_context_path(vdyp_stderr_log_path)
        )
    if vdyp_binpath is not None:
        context.setdefault("vdyp_binpath", _normalize_context_path(vdyp_binpath))
    if vdyp_params is not None:
        context.setdefault("vdyp_params", _normalize_context_path(vdyp_params))
    return context


def build_vdyp_run_event(
    *,
    status: str,
    phase: str,
    counts: VdypRunEventCounts,
    cmd: str,
    context: Mapping[str, Any],
    **extra_fields: Any,
) -> dict[str, Any]:
    """Build one VDYP run event payload with shared base fields."""
    return build_timestamped_event(
        event="vdyp_run",
        status=status,
        phase=phase,
        feature_count=counts.feature_count,
        cache_hits=counts.cache_hits,
        ply_rows=counts.ply_rows,
        lyr_rows=counts.lyr_rows,
        cmd=cmd,
        context=dict(context),
        **extra_fields,
    )


def emit_vdyp_run_event(
    *,
    append_jsonl_fn: Callable[[str | Path, Any], None],
    vdyp_log_path: str | Path,
    status: str,
    phase: str,
    counts: VdypRunEventCounts,
    cmd: str,
    context: Mapping[str, Any],
    **extra_fields: Any,
) -> None:
    """Emit one VDYP run event record through the provided append sink."""
    append_jsonl_fn(
        vdyp_log_path,
        build_vdyp_run_event(
            status=status,
            phase=phase,
            counts=counts,
            cmd=cmd,
            context=context,
            **extra_fields,
        ),
    )


def normalize_vdyp_run_event_counts(
    *,
    feature_count: Any,
    cache_hits: Any,
    ply_rows: Any,
    lyr_rows: Any,
) -> VdypRunEventCounts:
    """Normalize run-event count fields to integers in one shared seam."""
    return VdypRunEventCounts(
        feature_count=int(feature_count),
        cache_hits=int(cache_hits),
        ply_rows=int(ply_rows),
        lyr_rows=int(lyr_rows),
    )


def resolve_vdyp_batch_temp_artifacts(
    *,
    vdyp_ply_name: str,
    vdyp_lyr_name: str,
    vdyp_out_name: str,
    vdyp_err_name: str,
) -> VdypBatchTempArtifacts:
    """Resolve temp-file basenames and full paths for VDYP batch processing."""
    vdyp_ply_path = _as_path(vdyp_ply_name)
    vdyp_lyr_path = _as_path(vdyp_lyr_name)
    out_path = _as_path(vdyp_out_name)
    err_path = _as_path(vdyp_err_name)
    return VdypBatchTempArtifacts(
        vdyp_ply_csv=vdyp_ply_path.name,
        vdyp_lyr_csv=vdyp_lyr_path.name,
        vdyp_out_txt=out_path.name,
        vdyp_err_txt=err_path.name,
        out_path=out_path,
        err_path=err_path,
    )


def build_stratum_fit_run_config(
    *,
    fit_rawdata: bool = True,
    min_stands_per_si_bin: int = 25,
    min_age: int = 30,
    agg_type: str = "median",
    plot: bool = False,
    verbose: bool = False,
    figsize: tuple[float, float] = (8, 16),
    ylim: tuple[float, float] = (0, 600),
    xlim: tuple[float, float] = (0, 400),
) -> StratumFitRunConfig:
    """Build defaults for pre-VDYP stratum fit stage settings."""
    return StratumFitRunConfig(
        fit_rawdata=bool(fit_rawdata),
        min_stands_per_si_bin=int(min_stands_per_si_bin),
        min_age=int(min_age),
        agg_type=str(agg_type),
        plot=bool(plot),
        verbose=bool(verbose),
        figsize=figsize,
        ylim=ylim,
        xlim=xlim,
    )


def build_curve_smoothing_plot_config(
    *,
    sns_module: Any,
    plot: bool = True,
    figsize: tuple[float, float] = (8, 6),
    palette_name: str = "Greens",
    palette_size: int = 3,
    palette_flavours: Sequence[str] = ("RdPu", "Blues", "Greens", "Greys"),
    alphas: Sequence[float] = (1.0, 0.5, 0.1),
    xlim: tuple[float, float] = (0, 300),
    ylim: tuple[float, float] = (0, 600),
) -> CurveSmoothingPlotConfig:
    """Build and apply legacy curve-smoothing plot defaults."""
    palette = tuple(sns_module.color_palette(palette_name, palette_size))
    sns_module.set_palette(palette)
    return CurveSmoothingPlotConfig(
        plot=bool(plot),
        figsize=figsize,
        palette=palette,
        palette_flavours=tuple(str(v) for v in palette_flavours),
        alphas=tuple(float(v) for v in alphas),
        xlim=xlim,
        ylim=ylim,
    )


def build_curve_fit_adapter(
    *,
    curve_fit_impl: Callable[..., Any] | None = None,
    np_module: Any | None = None,
) -> Callable[..., Any]:
    """Build legacy-compatible curve_fit wrapper handling maxfev/max_nfev."""
    curve_fit_fn = curve_fit_impl
    if curve_fit_fn is None:
        scipy_optimize = importlib.import_module("scipy.optimize")
        curve_fit_fn = scipy_optimize.curve_fit
    np_mod = np_module or importlib.import_module("numpy")

    @functools.wraps(curve_fit_fn)
    def curve_fit(*args: Any, **kwargs: Any) -> Any:
        bounds = kwargs.get("bounds")
        if bounds is not None and np_mod.any(np_mod.isfinite(bounds)):
            if "max_nfev" not in kwargs:
                kwargs["max_nfev"] = kwargs.pop("maxfev", None)
        return curve_fit_fn(*args, **kwargs)

    return curve_fit


def load_vdyp_input_tables(
    *,
    vdyp_input_pandl_path: str | Path,
    vdyp_ply_feather_path: str | Path,
    vdyp_lyr_feather_path: str | Path,
    read_from_source: bool = False,
    source_where: str | None = None,
    source_mask: Any | None = None,
    source_map_ids: Sequence[str] | None = None,
    source_feature_ids: Sequence[Any] | None = None,
    source_map_id_chunk_size: int | None = 5,
    source_feature_id_chunk_size: int | None = None,
    gpd_module: Any | None = None,
    message_fn: Callable[..., Any] = print,
) -> tuple[Any, Any]:
    """Load VDYP polygon/layer tables from feather cache or source geodatabase."""
    gpd_mod = gpd_module or importlib.import_module("geopandas")
    if read_from_source:

        def _normalize_feature_ids(values: Sequence[Any]) -> list[int]:
            normalized: list[int] = []
            for value in values:
                if value is None:
                    continue
                value_str = str(value).strip()
                if value_str == "":
                    continue
                normalized.append(int(value))
            return sorted(set(normalized))

        def _normalize_map_ids(values: Sequence[str]) -> list[str]:
            normalized = [str(v).strip() for v in values if str(v).strip() != ""]
            return sorted(set(normalized))

        def _read_layer_by_feature_ids(*, layer: int, feature_ids: list[int]) -> Any:
            if not feature_ids:
                message_fn(f"VDYP layer {layer}: no feature_ids; returning empty table")
                return gpd_mod.read_file(
                    vdyp_input_pandl_path,
                    layer=layer,
                    where="1=0",
                )
            pd_mod = importlib.import_module("pandas")
            if source_feature_id_chunk_size and int(source_feature_id_chunk_size) > 0:
                chunks: list[Any] = []
                chunk_size = max(int(source_feature_id_chunk_size), 1)
                total_chunks = (len(feature_ids) + chunk_size - 1) // chunk_size
                message_fn(
                    f"VDYP layer {layer}: loading {len(feature_ids)} feature_ids "
                    f"in {total_chunks} chunks (chunk_size={chunk_size})"
                )
                for start in range(0, len(feature_ids), chunk_size):
                    chunk_ids = feature_ids[start : start + chunk_size]
                    chunk_where = "FEATURE_ID IN (%s)" % ",".join(
                        str(fid) for fid in chunk_ids
                    )
                    chunk_i = (start // chunk_size) + 1
                    if chunk_i == 1 or chunk_i % 25 == 0 or chunk_i == total_chunks:
                        message_fn(
                            f"VDYP layer {layer}: chunk {chunk_i}/{total_chunks}"
                        )
                    chunks.append(
                        gpd_mod.read_file(
                            vdyp_input_pandl_path,
                            layer=layer,
                            where=chunk_where,
                            ignore_geometry=True,
                        )
                    )
                return pd_mod.concat(chunks, ignore_index=True)

            message_fn(
                f"VDYP layer {layer}: full-layer read with in-memory FEATURE_ID "
                f"filter (n={len(feature_ids)})"
            )
            table = gpd_mod.read_file(
                vdyp_input_pandl_path,
                layer=layer,
                ignore_geometry=True,
            )
            return table[table.FEATURE_ID.isin(feature_ids)].copy()

        def _read_layer_by_map_ids(*, layer: int, map_ids: list[str]) -> Any:
            if not map_ids:
                message_fn(f"VDYP layer {layer}: no map_ids; returning empty table")
                return gpd_mod.read_file(
                    vdyp_input_pandl_path,
                    layer=layer,
                    where="1=0",
                    ignore_geometry=True,
                )
            pd_mod = importlib.import_module("pandas")
            chunks: list[Any] = []
            chunk_size = max(int(source_map_id_chunk_size or 1), 1)
            total_chunks = (len(map_ids) + chunk_size - 1) // chunk_size
            message_fn(
                f"VDYP layer {layer}: loading {len(map_ids)} map_ids "
                f"in {total_chunks} chunks (chunk_size={chunk_size})"
            )
            for start in range(0, len(map_ids), chunk_size):
                chunk_ids = map_ids[start : start + chunk_size]
                quoted = ",".join(
                    "'" + mid.replace("'", "''") + "'" for mid in chunk_ids
                )
                chunk_where = f"MAP_ID IN ({quoted})"
                chunk_i = (start // chunk_size) + 1
                if chunk_i == 1 or chunk_i % 10 == 0 or chunk_i == total_chunks:
                    message_fn(f"VDYP layer {layer}: chunk {chunk_i}/{total_chunks}")
                chunks.append(
                    gpd_mod.read_file(
                        vdyp_input_pandl_path,
                        layer=layer,
                        where=chunk_where,
                        ignore_geometry=True,
                    )
                )
            return pd_mod.concat(chunks, ignore_index=True)

        explicit_feature_ids = (
            _normalize_feature_ids(source_feature_ids) if source_feature_ids else []
        )
        explicit_map_ids = _normalize_map_ids(source_map_ids) if source_map_ids else []
        if explicit_feature_ids:
            message_fn(
                f"VDYP source load: explicit feature-id mode "
                f"(n={len(explicit_feature_ids)})"
            )
            vdyp_ply = _read_layer_by_feature_ids(
                layer=0, feature_ids=explicit_feature_ids
            )
            vdyp_lyr = _read_layer_by_feature_ids(
                layer=1, feature_ids=explicit_feature_ids
            )
            if vdyp_ply.shape[0] == 0 and vdyp_lyr.shape[0] == 0 and explicit_map_ids:
                message_fn(
                    "VDYP source load: feature-id lookup returned empty tables; "
                    f"falling back to map-id mode (n={len(explicit_map_ids)})"
                )
                vdyp_ply = _read_layer_by_map_ids(layer=0, map_ids=explicit_map_ids)
                vdyp_lyr = _read_layer_by_map_ids(layer=1, map_ids=explicit_map_ids)
            vdyp_ply.to_feather(vdyp_ply_feather_path)
            vdyp_lyr.to_feather(vdyp_lyr_feather_path)
            return vdyp_ply, vdyp_lyr

        if explicit_map_ids:
            message_fn(
                f"VDYP source load: explicit map-id mode (n={len(explicit_map_ids)})"
            )
            vdyp_ply = _read_layer_by_map_ids(layer=0, map_ids=explicit_map_ids)
            vdyp_lyr = _read_layer_by_map_ids(layer=1, map_ids=explicit_map_ids)
            vdyp_ply.to_feather(vdyp_ply_feather_path)
            vdyp_lyr.to_feather(vdyp_lyr_feather_path)
            return vdyp_ply, vdyp_lyr

        read_kwargs: dict[str, Any] = {}
        if source_where:
            read_kwargs["where"] = source_where
        if source_mask is not None:
            read_kwargs["mask"] = source_mask
        vdyp_ply = gpd_mod.read_file(vdyp_input_pandl_path, layer=0, **read_kwargs)
        vdyp_ply.to_feather(vdyp_ply_feather_path)
        # Layer 1 has no geometry; when loading by mask, fetch feature-id chunks.
        lyr_kwargs: dict[str, Any] = {}
        if source_where:
            lyr_kwargs["where"] = source_where
            vdyp_lyr = gpd_mod.read_file(vdyp_input_pandl_path, layer=1, **lyr_kwargs)
        elif source_mask is not None:
            feature_ids = _normalize_feature_ids(vdyp_ply.FEATURE_ID.tolist())
            vdyp_lyr = _read_layer_by_feature_ids(layer=1, feature_ids=feature_ids)
        else:
            vdyp_lyr = gpd_mod.read_file(vdyp_input_pandl_path, layer=1, **lyr_kwargs)
        vdyp_lyr.to_feather(vdyp_lyr_feather_path)
        return vdyp_ply, vdyp_lyr
    pd_mod = importlib.import_module("pandas")
    try:
        vdyp_ply = gpd_mod.read_feather(vdyp_ply_feather_path)
    except ValueError as exc:
        # Some historical caches were written as plain Feather tables without
        # GeoPandas metadata; fall back to pandas in that case.
        if "Missing geo metadata" not in str(exc):
            raise
        vdyp_ply = pd_mod.read_feather(vdyp_ply_feather_path)
    try:
        vdyp_lyr = gpd_mod.read_feather(vdyp_lyr_feather_path)
    except ValueError as exc:
        if "Missing geo metadata" not in str(exc):
            raise
        vdyp_lyr = pd_mod.read_feather(vdyp_lyr_feather_path)
    return vdyp_ply, vdyp_lyr


def _default_load_pickle(path: str | Path) -> Any:
    with Path(path).open("rb") as handle:
        return pickle.load(handle)


def _default_dump_pickle(value: Any, path: str | Path) -> None:
    with Path(path).open("wb") as handle:
        pickle.dump(value, handle)


def _default_load_compat_pickle(path: str | Path) -> Any:
    pickle_compat = importlib.import_module("pandas.compat.pickle_compat")
    with Path(path).open("rb") as handle:
        return pickle_compat.load(handle)


def load_or_build_vdyp_results_tsa(
    *,
    tsa: str,
    force_run_vdyp: bool,
    vdyp_results_tsa_pickle_path: str | Path,
    vdyp_results_pickle_path: str | Path,
    run_bootstrap_fn: Callable[[], dict[int, dict[str, dict[Any, Any]]]],
    print_fn: Callable[..., Any] = print,
    load_pickle_fn: Callable[[str | Path], Any] = _default_load_pickle,
    dump_pickle_fn: Callable[[Any, str | Path], None] = _default_dump_pickle,
    load_compat_pickle_fn: Callable[[str | Path], Any] = _default_load_compat_pickle,
) -> dict[int, dict[str, dict[Any, Any]]]:
    """Resolve per-TSA VDYP results from cache, combined cache, or fresh bootstrap."""
    tsa_path = Path(vdyp_results_tsa_pickle_path)
    combined_path = Path(vdyp_results_pickle_path)
    si_levels = {"L", "M", "H"}

    def _looks_like_per_tsa_vdyp_results(value: Any) -> bool:
        if not isinstance(value, dict) or not value:
            return isinstance(value, dict)
        # Reject legacy/invalid shape where first-level keys are SI levels.
        if set(str(k) for k in value.keys()).issubset(si_levels):
            return False
        for k, v in value.items():
            if isinstance(k, bool):
                return False
            if not isinstance(k, int):
                return False
            if not isinstance(v, dict):
                return False
        return True

    def _bootstrap_and_cache() -> dict[int, dict[str, dict[Any, Any]]]:
        print_fn()
        result = run_bootstrap_fn()
        dump_pickle_fn(result, tsa_path)
        return result

    if force_run_vdyp:
        return _bootstrap_and_cache()

    if (not tsa_path.is_file()) and combined_path.is_file():
        try:
            vdyp_results_all = load_pickle_fn(combined_path)
        except ModuleNotFoundError:
            vdyp_results_all = load_compat_pickle_fn(combined_path)
        vdyp_key: Any = tsa
        if vdyp_key not in vdyp_results_all:
            try:
                vdyp_key = int(tsa)
            except (TypeError, ValueError):
                vdyp_key = tsa
        if vdyp_key in vdyp_results_all:
            cached = vdyp_results_all[vdyp_key]
            if _looks_like_per_tsa_vdyp_results(cached):
                return cached
            print_fn(
                "combined VDYP cache has invalid schema for tsa",
                tsa,
                "; rebuilding",
            )
            return _bootstrap_and_cache()
        # Combined cache is optional; if TSA key is missing, run bootstrap.
        return _bootstrap_and_cache()

    if not tsa_path.is_file():
        return _bootstrap_and_cache()

    return load_pickle_fn(tsa_path)


def plot_curve_overlays(
    *,
    results_for_tsa: Sequence[tuple[int, str, Any]],
    si_levels: Sequence[str],
    smoothed_runs: Sequence[SmoothedCurveResult],
    plot: bool,
    figsize: tuple[float, float],
    palette: Sequence[Any],
    pd_module: Any,
    plt_module: Any,
    dataframe_type: type,
    xlim: tuple[float, float] = (0, 300),
    ylim: tuple[float, float] = (0, 600),
    message_fn: Callable[..., Any] = print,
) -> None:
    """Render legacy VDYP overlay plots for smoothed curves."""
    if not plot:
        return
    smoothed_run_map = {(r.stratumi, r.si_level): r for r in smoothed_runs}
    for stratumi, sc, _result in results_for_tsa:
        plt_module.subplots(1, 1, figsize=figsize)
        message_fn("stratum", stratumi, sc)
        for i, si_level in enumerate(si_levels):
            message_fn("processing", sc, si_level)
            run = smoothed_run_map.get((int(stratumi), si_level))
            if run is None:
                continue
            x, y = run.x, run.y
            vdyp_out = run.vdyp_out
            vdyp_out_concat = pd_module.concat(
                [v for v in vdyp_out.values() if isinstance(v, dataframe_type)]
            )
            c = vdyp_out_concat.groupby(level="Age")["Vdwb"].median()
            c = c[c > 0]
            c = c[c.index >= 30]
            x_ = c.index.values
            y_ = c.values
            plt_module.plot(
                x_,
                y_,
                linestyle=":",
                label="VDYP->agg (%s %s)" % (sc, si_level),
                linewidth=2,
                color=palette[i],
            )
            plt_module.plot(x, y, label="%s %s" % (sc, si_level))
        plt_module.legend()
        plt_module.xlim(xlim)
        plt_module.ylim(ylim)
        plt_module.tight_layout()


def build_smoothed_curve_table(
    *,
    smoothed_runs: Sequence[SmoothedCurveResult],
    pd_module: Any,
    output_path: str | Path | None = None,
) -> Any:
    """Build and optionally persist the smoothed VDYP curve table."""
    out_cols = ["index", "age", "volume", "stratum_code", "si_level"]
    frames = []
    for run in smoothed_runs:
        df = pd_module.DataFrame(zip(run.x, run.y), columns=["age", "volume"])
        df = df[df.volume > 0]
        df["stratum_code"] = run.stratum_code
        df["si_level"] = run.si_level
        frames.append(df)
    if frames:
        curve_table = pd_module.concat(frames).reset_index()
    else:
        curve_table = pd_module.DataFrame(columns=out_cols)
    if output_path is not None:
        curve_table.to_feather(output_path)
    return curve_table


def fit_stratum_curves(
    *,
    f_table: Any,
    fit_func: Callable[..., Any],
    fit_func_bounds_func: Callable[[Any], Any],
    strata_df: Any,
    stratum_si_stats: Any,
    stratumi: int,
    species_list: Sequence[str],
    curve_fit_fn: Callable[..., Any],
    np_module: Any,
    pd_module: Any,
    sns_module: Any,
    plt_module: Any,
    plot: bool = True,
    figsize: tuple[float, float] = (6, 12),
    verbose: bool = False,
    xlim: tuple[float, float] = (0, 300),
    ylim: tuple[float, float] = (0, 500),
    si_levelquants: Mapping[str, Sequence[float]] | None = None,
    linestyles: Sequence[str] | None = None,
    markers: Sequence[str] | None = None,
    palette_flavours: Sequence[str] | None = None,
    maxfev: int = 100000,
    min_age: int = 30,
    max_age: int = 300,
    max_records: int = 15000,
    sigma_exponent: float = 1.0,
    window: int = 10,
    min_periods: int | None = None,
    center: bool = False,
    agg_type: str = "median",
    sv_thresh: float = 0.10,
    rawdata_alpha: float = 0.05,
    fitattr_thresh: float = 1.0,
    fit_rawdata: bool = True,
    min_stands_per_si_bin: int = 25,
    debug: bool = False,
    message_fn: Callable[..., Any] = print,
) -> dict[str, Any]:
    """Fit per-SI species curves for one stratum using legacy notebook logic."""
    del max_records, sigma_exponent, window, min_periods, center, debug
    if si_levelquants is None:
        si_levelquants = {
            "L": [5, 20, 35],
            "M": [35, 50, 65],
            "H": [65, 80, 95],
        }
    if linestyles is None:
        linestyles = ["-", "--", ":"]
    if markers is None:
        markers = ["x", "+", "*"]
    if palette_flavours is None:
        palette_flavours = ["RdPu", "Blues", "Greens"]

    _palettes = [sns_module.color_palette(pf, 3) for pf in palette_flavours]
    pd_module.options.mode.chained_assignment = None
    sc = strata_df.iloc[stratumi].name
    if verbose:
        message_fn("processing stratum", sc)
    if plot:
        _fig, ax = plt_module.subplots(4, 1, figsize=figsize, sharex=True, sharey=True)
        palette = sns_module.color_palette("RdPu", 3)
        sns_module.set_palette(palette)
        ax_ = {
            "L": ax[1],
            "M": ax[2],
            "H": ax[3],
        }
        palette_ = {v: palette[i] for i, v in enumerate("LMH")}
    result: dict[str, Any] = {}
    active_si_levelquants = resolve_si_level_quantiles_for_stratum(
        stratum_si_stats=stratum_si_stats,
        stratum_code=sc,
        si_levelquants=si_levelquants,
    )
    level_order = list(active_si_levelquants.keys())
    stratum_rows = f_table.loc[[sc]].copy()
    stratum_rows = stratum_rows[
        (stratum_rows.PROJ_AGE_1 >= min_age) & (stratum_rows.PROJ_AGE_1 < max_age)
    ]
    level_masks: dict[str, Any] = {}
    level_counts: dict[str, int] = {}
    for si_level, q_values in active_si_levelquants.items():
        si_lo = stratum_si_stats.loc[sc].loc["%i%%" % q_values[0]]
        si_hi = stratum_si_stats.loc[sc].loc["%i%%" % q_values[2]]
        mask = (stratum_rows.SITE_INDEX >= si_lo) & (stratum_rows.SITE_INDEX <= si_hi)
        level_masks[si_level] = mask
        level_counts[si_level] = int(mask.sum())

    level_to_rep = {level: level for level in level_order}

    def _rebuild_group_state() -> tuple[
        list[str], dict[str, list[str]], dict[str, int]
    ]:
        rep_order: list[str] = []
        members_by_rep: dict[str, list[str]] = {}
        counts_by_rep: dict[str, int] = {}
        for level in level_order:
            rep = level_to_rep[level]
            if rep not in rep_order:
                rep_order.append(rep)
            members_by_rep.setdefault(rep, []).append(level)
            counts_by_rep[rep] = counts_by_rep.get(rep, 0) + level_counts.get(level, 0)
        return rep_order, members_by_rep, counts_by_rep

    rep_order, rep_members, group_counts = _rebuild_group_state()
    if int(min_stands_per_si_bin) > 0:
        while len(rep_order) > 1:
            sparse_reps = [
                rep
                for rep in rep_order
                if group_counts.get(rep, 0) < int(min_stands_per_si_bin)
            ]
            if not sparse_reps:
                break
            sparse_rep = min(sparse_reps, key=lambda rep: group_counts.get(rep, 0))
            sparse_idx = rep_order.index(sparse_rep)
            neighbor_candidates: list[str] = []
            if sparse_idx > 0:
                neighbor_candidates.append(rep_order[sparse_idx - 1])
            if sparse_idx + 1 < len(rep_order):
                neighbor_candidates.append(rep_order[sparse_idx + 1])
            if not neighbor_candidates:
                break
            merge_target = max(
                neighbor_candidates,
                key=lambda rep: (
                    group_counts.get(rep, 0),
                    -abs(rep_order.index(rep) - sparse_idx),
                ),
            )
            for level, rep in list(level_to_rep.items()):
                if rep == sparse_rep:
                    level_to_rep[level] = merge_target
            rep_order, rep_members, group_counts = _rebuild_group_state()

    if len(set(level_to_rep.values())) < len(level_order):
        collapse_desc = ", ".join(
            f"{level}->{level_to_rep[level]} ({level_counts.get(level, 0)} stands)"
            for level in level_order
            if level_to_rep[level] != level
        )
        message_fn("  pre-fit SI bin collapse", sc, collapse_desc)

    rep_payloads: dict[str, dict[str, Any]] = {}
    for rep_level in rep_order:
        members = rep_members.get(rep_level, [rep_level])
        combined_mask = None
        for member in members:
            member_mask = level_masks.get(member)
            if member_mask is None:
                continue
            combined_mask = (
                member_mask if combined_mask is None else (combined_mask | member_mask)
            )
        if combined_mask is None:
            rep_payloads[rep_level] = {
                "ss": stratum_rows.iloc[0:0].copy(),
                "species": {},
            }
            continue
        ss = stratum_rows[combined_mask]
        ss = ss.sort_values("PROJ_AGE_1")
        stand_volume_total = ss["LIVE_STAND_VOLUME_125"].sum()
        if stand_volume_total <= 0:
            sv = pd_module.Series(dtype=float)
        else:
            sv = pd_module.Series(
                {
                    species: (
                        ss[f"live_vol_per_ha_125_{species}"].sum() / stand_volume_total
                    )
                    for species in species_list
                }
            ).sort_values(ascending=False)
            sv = sv[sv > sv_thresh]
        payload: dict[str, Any] = {"ss": ss, "species": {}}
        si_md = float(ss.SITE_INDEX.median()) if not ss.empty else float("nan")
        if verbose:
            message_fn("sv sum", sv.sum())
        if plot:
            x, y = [], []
            for j, species in enumerate(sv.index.values):
                fitattr = f"live_vol_per_ha_125_{species}"
                sss = ss[ss[fitattr] >= 1]
                x.append(sss.PROJ_AGE_1.values)
                y.append(sss[fitattr].values / sv.sum())
            if x and y:
                x = np_module.concatenate(x)
                y = np_module.concatenate(y)
                ax_[rep_level].scatter(
                    x,
                    y,
                    alpha=rawdata_alpha,
                    label="Raw data (%s SI, all spp)" % (rep_level),
                    color="grey",
                    marker=".",
                )
        for j, species in enumerate(sv.index.values):
            if verbose:
                message_fn(
                    "  fitting SI level %s (%2.1f), species %s"
                    % (rep_level, si_md, species)
                )
            fitattr = f"live_vol_per_ha_125_{species}"
            sss = ss[ss[fitattr] >= fitattr_thresh]
            sv_sum = float(sv.sum())
            if sv_sum <= 0 or sss.empty:
                continue
            if fit_rawdata:
                x = sss.PROJ_AGE_1.values
                y = sss[fitattr].values / sv_sum
                sigma = None
            else:
                agg = sss.groupby("PROJ_AGE_1")[fitattr].agg(
                    ["mean", "median", "std", "count"]
                )
                agg = agg[agg["count"] > 2]
                if agg.empty:
                    continue
                std_mean = float(agg["std"].fillna(0.0).mean())
                agg["sigma"] = (
                    (std_mean + agg["std"].fillna(0.0)) / agg["count"]
                ) ** 0.5
                x = agg.index.values
                y = agg[agg_type].values / sv_sum
                sigma = agg["sigma"].values
            bounds = fit_func_bounds_func(x)
            try:
                popt, pcov = curve_fit_fn(
                    fit_func,
                    x,
                    y,
                    bounds=bounds,
                    maxfev=maxfev,
                    sigma=sigma,
                )
            except _curve_fit_skip_exception_types() as exc:
                message_fn(
                    "fit error",
                    exc,
                    "stratum",
                    sc,
                    "si",
                    rep_level,
                    "species",
                    species,
                    "n",
                    len(x),
                )
                continue

            if verbose:
                message_fn("fitting N raw data points", sss.shape[0])
                message_fn("popt", popt)
            if plot:
                if not fit_rawdata:
                    ax_[rep_level].scatter(
                        x,
                        y,
                        alpha=0.8,
                        label="Smoothed data (%s SI, %s)" % (rep_level, species),
                        color="black",
                        marker=markers[j],
                    )
                x_ = np_module.linspace(popt[2], 300, 30)
                y_ = fit_func(x_, *popt)
                sns_module.lineplot(
                    x_,
                    y_,
                    label="func fit (%s SI, %s)" % (rep_level, species),
                    ax=ax[0],
                    color=palette_[rep_level],
                    linestyle=linestyles[j],
                    linewidth=3,
                )
                sns_module.lineplot(
                    x_,
                    y_,
                    label="func fit (%s SI, %s)" % (rep_level, species),
                    ax=ax_[rep_level],
                    color=palette_[rep_level],
                    linestyle=linestyles[j],
                    linewidth=3,
                )
            payload["species"][species] = {}
            payload["species"][species]["si"] = si_md
            payload["species"][species]["pct"] = int(
                round(100 * sv[species] / sv.sum())
            )
            age = int(round(np_module.min(x) * 1.0))
            payload["species"][species]["age"] = (
                age if not np_module.isnan(age) else None
            )
            jj = min(2, j + 1)
            ssss = sss[
                (sss[f"PROJ_AGE_{jj}"] >= age - 5) & (sss[f"PROJ_AGE_{jj}"] < age + 5)
            ]
            height = ssss[f"PROJ_HEIGHT_{jj}"].median()
            payload["species"][species]["height"] = (
                height if not np_module.isnan(height) else None
            )
            payload["species"][species]["fit_func"] = fit_func
            payload["species"][species]["popt"] = popt
            payload["species"][species]["pcov"] = pcov
        rep_payloads[rep_level] = payload
    for si_level in level_order:
        rep_level = level_to_rep.get(si_level, si_level)
        base_payload = rep_payloads.get(
            rep_level, {"ss": stratum_rows.iloc[0:0], "species": {}}
        )
        payload = dict(base_payload)
        payload["collapsed_to"] = rep_level
        payload["collapsed_members"] = tuple(rep_members.get(rep_level, [rep_level]))
        payload["si_bin_stand_count"] = int(level_counts.get(si_level, 0))
        payload["si_group_stand_count"] = int(group_counts.get(rep_level, 0))
        result[si_level] = payload
    if plot:
        ax[0].set_title("Best-fit yield curves (stratum %s)" % sc)
        plt_module.legend(loc="best")
        plt_module.xlim(xlim)
        plt_module.ylim(ylim)
        plt_module.xlabel("Stand age (years)")
        plt_module.ylabel("Merch. volume (m3/ha)")
        plt_module.tight_layout()
        plt_module.savefig(
            "plots/yieldcurve_fit-%s-%s.png" % (str(stratumi).zfill(2), sc),
            facecolor="white",
        )
        plt_module.savefig(
            "plots/yieldcurve_fit-%s-%s.pdf" % (str(stratumi).zfill(2), sc),
            facecolor="white",
        )
    return result


def build_fit_stratum_curves_runner(
    *,
    f_table: Any,
    fit_func: Callable[..., Any],
    fit_func_bounds_func: Callable[..., Any],
    strata_df: Any,
    stratum_si_stats: Any,
    species_list: Sequence[str],
    curve_fit_fn: Callable[..., Any],
    fit_rawdata: bool,
    min_stands_per_si_bin: int = 25,
    min_age: int,
    agg_type: str,
    plot: bool,
    figsize: tuple[int, int],
    verbose: bool,
    ylim: Sequence[float],
    xlim: Sequence[float],
    np_module: Any,
    pd_module: Any,
    sns_module: Any,
    plt_module: Any,
    message_fn: Callable[..., Any] = print,
    fit_stratum_curves_fn: Callable[..., Any] = fit_stratum_curves,
) -> Callable[[int, str], Any]:
    """Build a compile-one callback that runs `fit_stratum_curves(...)` for one stratum."""

    def _compile_one(stratumi: int, _sc: str) -> Any:
        return fit_stratum_curves_fn(
            f_table=f_table,
            fit_func=fit_func,
            fit_func_bounds_func=fit_func_bounds_func,
            strata_df=strata_df,
            stratum_si_stats=stratum_si_stats,
            stratumi=stratumi,
            species_list=species_list,
            curve_fit_fn=curve_fit_fn,
            np_module=np_module,
            pd_module=pd_module,
            sns_module=sns_module,
            plt_module=plt_module,
            fit_rawdata=fit_rawdata,
            min_stands_per_si_bin=min_stands_per_si_bin,
            min_age=min_age,
            agg_type=agg_type,
            plot=plot,
            figsize=figsize,
            verbose=verbose,
            ylim=ylim,
            xlim=xlim,
            message_fn=message_fn,
        )

    return _compile_one


def compile_strata_fit_results(
    *,
    strata_df: Any,
    compile_one_fn: Callable[[int, str], Any],
    message_fn: Callable[..., Any] = print,
) -> list[list[Any]]:
    """Compile fit payloads for each selected stratum index/code pair."""
    compiled: list[list[Any]] = []
    for stratumi, sc in enumerate(strata_df.index.values[:]):
        message_fn("compiling stratum %s" % sc)
        fit_out = compile_one_fn(stratumi, sc)
        compiled.append([stratumi, sc, fit_out])
    return compiled


def run_vdyp_sampling(
    *,
    sample_table: Any,
    nsamples: str | int,
    min_samples: int,
    max_samples: int,
    nsamples_c1: float,
    nsamples_c2: float,
    confidence: float,
    half_rel_ci: float,
    ipp_mode: str | None,
    vdyp_timeout: float,
    rc_len: int,
    verbose: bool,
    vdyp_out_cache: dict[Any, Any] | None,
    random_seed: int | None,
    run_batch_fn: Callable[..., dict[Any, Any]],
    nsamples_from_curves_fn: Callable[..., tuple[int, Any]],
    message_fn: Callable[..., Any] = print,
) -> dict[Any, Any]:
    """Run legacy VDYP sampling flow (auto/all/fixed) for one stratum sample table."""

    random_draw_index = 0

    def _next_random_state() -> int | None:
        nonlocal random_draw_index
        if random_seed is None:
            return None
        state = int(random_seed) + random_draw_index
        random_draw_index += 1
        return state

    def _take_cached(
        feature_ids: Sequence[Any], vdyp_out: dict[Any, Any]
    ) -> tuple[list[Any], int]:
        if vdyp_out_cache is None:
            return list(feature_ids), 0
        uncached: list[Any] = []
        for fid in feature_ids:
            if fid in vdyp_out_cache:
                vdyp_out[fid] = vdyp_out_cache[fid]
            else:
                uncached.append(fid)
        cache_hits = len(feature_ids) - len(uncached)
        return uncached, cache_hits

    if nsamples == "auto" and sample_table.shape[0] < min_samples:
        if sample_table.shape[0] == 0:
            return {}
        if verbose:
            message_fn(
                "auto mode: stratum has fewer than min_samples; "
                f"running all {sample_table.shape[0]} records"
            )
        vdyp_out = run_batch_fn(
            sample_table.FEATURE_ID.values, phase="auto_small_sample"
        )
        if vdyp_out_cache is not None:
            vdyp_out_cache.update(vdyp_out)
        return vdyp_out

    if nsamples == "auto" and sample_table.shape[0] >= min_samples:
        ss = sample_table.reset_index().set_index("index")
        samples = ss.sample(
            min(min_samples, ss.shape[0]), random_state=_next_random_state()
        )
        vdyp_out = {}
        feature_ids, cache_hits = _take_cached(
            samples.FEATURE_ID.values, vdyp_out=vdyp_out
        )
        vdyp_out_new = run_batch_fn(feature_ids, cache_hits=cache_hits, phase="initial")
        vdyp_out.update(vdyp_out_new)
        if vdyp_out_cache is not None:
            vdyp_out_cache.update(vdyp_out)
        ss.drop(samples.index, inplace=True)
        nsamples_target, _ = nsamples_from_curves_fn(
            vdyp_out,
            confidence=confidence,
            half_rel_ci=half_rel_ci,
        )
        nsamples_target = min(max(nsamples_target, min_samples), ss.shape[0])
        nsamples_gap = nsamples_target - len(vdyp_out)
        nsamples_gap_rel = nsamples_gap / nsamples_target
        while nsamples_gap_rel > nsamples_c1 and ss.shape[0]:
            if nsamples_gap_rel > nsamples_c2:
                nsamples_new = int(nsamples_gap * (1 - nsamples_gap_rel))
            else:
                nsamples_new = nsamples_gap
            nsamples_new = min(nsamples_new, max_samples, ss.shape[0])
            if nsamples_new <= 0:
                break
            if verbose:
                message_fn(
                    "moe loop",
                    nsamples_target,
                    nsamples_new,
                    "%0.2f" % nsamples_gap_rel,
                    len(vdyp_out),
                    ss.shape[0],
                )
            samples = ss.sample(nsamples_new, random_state=_next_random_state())
            feature_ids = samples.FEATURE_ID.values
            timeout = 30 + (vdyp_timeout * feature_ids.shape[0] / rc_len)
            if not ipp_mode or samples.shape[0] < min_samples:
                feature_ids, cache_hits = _take_cached(feature_ids, vdyp_out=vdyp_out)
                vdyp_out_ = run_batch_fn(
                    feature_ids,
                    timeout=timeout,
                    cache_hits=cache_hits,
                    phase="gap_fill",
                )
                vdyp_out.update(vdyp_out_)
                if vdyp_out_cache is not None:
                    vdyp_out_cache.update(vdyp_out)
            elif ipp_mode == "load_balanced":
                raise NotImplementedError(
                    build_contextual_error_message(
                        prefix="Unsupported VDYP sampling mode",
                        context={"ipp_mode": ipp_mode, "nsamples": nsamples},
                    )
                )
            ss.drop(samples.index, inplace=True)
            nsamples_target, _ = nsamples_from_curves_fn(
                vdyp_out,
                confidence=confidence,
                half_rel_ci=half_rel_ci,
            )
            nsamples_target = min(
                max(nsamples_target, min_samples), sample_table.shape[0]
            )
            nsamples_gap = nsamples_target - len(vdyp_out)
            nsamples_gap_rel = nsamples_gap / nsamples_target
        if verbose:
            message_fn("final gap", nsamples_gap_rel)
        return vdyp_out

    if nsamples == "all":
        return run_batch_fn(sample_table.FEATURE_ID.values, phase="all")
    if isinstance(nsamples, int):
        samples = sample_table.sample(nsamples, random_state=_next_random_state())
        return run_batch_fn(samples.FEATURE_ID.values, phase="fixed")
    raise ValueError(
        build_contextual_error_message(
            prefix="Unsupported nsamples mode in run_vdyp_sampling",
            context={
                "nsamples": repr(nsamples),
                "expected": "'auto' | 'all' | int",
            },
            skip_none=False,
        )
    )


def run_vdyp_for_stratum(
    *,
    sample_table: Any,
    tsa: str,
    run_id: str,
    vdyp_ply: Any,
    vdyp_lyr: Any,
    rc_len: int,
    curve_fit_fn: Callable[..., Any],
    fit_func: Callable[..., Any],
    fit_func_bounds_func: Callable[..., Any],
    nsamples: str | int = "auto",
    vdyp_io_dirname: str = "vdyp_io",
    vdyp_params_infile: str = "vdyp_params-landp",
    vdyp_binpath: str = "VDYP7/VDYP7/VDYP7Console.exe",
    nsamples_c1: float = 0.01,
    nsamples_c2: float = 0.1,
    verbose: bool = False,
    confidence: float = 95,
    half_rel_ci: float = 0.05,
    min_samples: int = 100,
    max_samples: int = 640,
    ipp_mode: str | None = None,
    vdyp_timeout: float = 2.0,
    vdyp_out_cache: dict[Any, Any] | None = None,
    sampling_seed: int | None = None,
    vdyp_log_path: str | Path | None = None,
    vdyp_stdout_log_path: str | Path | None = None,
    vdyp_stderr_log_path: str | Path | None = None,
    log_context: Mapping[str, Any] | None = None,
    which_fn: Callable[[str], str | None] | None = None,
    build_tsa_vdyp_log_paths_fn: Callable[..., Mapping[str, str | Path]] | None = None,
    append_jsonl_fn: Callable[[str | Path, Any], None] | None = None,
    append_text_fn: Callable[[str | Path, str], None] | None = None,
    execute_vdyp_batch_fn: Callable[..., dict[Any, Any]] | None = None,
    write_vdyp_infiles_fn: Callable[..., None] | None = None,
    import_vdyp_tables_fn: Callable[[str], dict[Any, Any]] | None = None,
    nsamples_from_curves_fn: Callable[..., tuple[int, Any]] | None = None,
    message_fn: Callable[..., Any] = print,
) -> dict[Any, Any]:
    """Run VDYP for one stratum sample table with logging and sampling orchestration."""
    import shutil

    if which_fn is None:
        which_fn = shutil.which
    if build_tsa_vdyp_log_paths_fn is None:
        from femic.pipeline.vdyp_logging import build_tsa_vdyp_log_paths

        build_tsa_vdyp_log_paths_fn = build_tsa_vdyp_log_paths
    if append_jsonl_fn is None:
        from femic.pipeline.vdyp_logging import append_jsonl

        append_jsonl_fn = append_jsonl
    if append_text_fn is None:
        from femic.pipeline.vdyp_logging import append_text

        append_text_fn = append_text
    if write_vdyp_infiles_fn is None:
        from femic.pipeline.vdyp_io import write_vdyp_infiles_plylyr

        write_vdyp_infiles_fn = write_vdyp_infiles_plylyr
    if import_vdyp_tables_fn is None:
        from femic.pipeline.vdyp_io import import_vdyp_tables

        import_vdyp_tables_fn = import_vdyp_tables
    if nsamples_from_curves_fn is None:
        from femic.pipeline.vdyp_sampling import nsamples_from_curves

        def _default_nsamples_from_curves(
            vdyp_out: dict[Any, Any], **kwargs: Any
        ) -> tuple[int, Any]:
            nsamples_target, fit_out = nsamples_from_curves(vdyp_out, **kwargs)
            return int(nsamples_target), fit_out

        nsamples_from_curves_fn = _default_nsamples_from_curves
    if execute_vdyp_batch_fn is None:
        execute_vdyp_batch_fn = execute_vdyp_batch

    build_tsa_vdyp_log_paths_ = cast(
        Callable[..., Mapping[str, str | Path]], build_tsa_vdyp_log_paths_fn
    )
    append_jsonl_ = cast(Callable[[str | Path, Any], None], append_jsonl_fn)
    append_text_ = cast(Callable[[str | Path, str], None], append_text_fn)
    execute_vdyp_batch_ = cast(Callable[..., dict[Any, Any]], execute_vdyp_batch_fn)
    nsamples_from_curves_ = cast(
        Callable[..., tuple[int, Any]], nsamples_from_curves_fn
    )

    windows_host = os.name == "nt"
    if not windows_host and which_fn("wine") is None:
        raise RuntimeError(
            "wine not found; VDYP7 requires wine to run on non-Windows systems"
        )
    vdyp_binpath_path = Path(vdyp_binpath)
    if not vdyp_binpath_path.exists():
        raise RuntimeError(f"VDYP executable not found: {vdyp_binpath_path.resolve()}")
    vdyp_params_path = Path(vdyp_params_infile)
    if not vdyp_params_path.exists() and not vdyp_params_path.is_absolute():
        source_root = os.environ.get("FEMIC_SOURCE_ROOT")
        if source_root:
            candidate = Path(source_root) / vdyp_params_path
            if candidate.exists():
                vdyp_params_path = candidate
    if not vdyp_params_path.exists():
        raise RuntimeError(f"VDYP params path not found: {vdyp_params_path.resolve()}")
    vdyp_params_infile = str(vdyp_params_path)
    Path(vdyp_io_dirname).mkdir(parents=True, exist_ok=True)

    tsa_paths = build_tsa_vdyp_log_paths_(
        tsa_code=tsa,
        run_id=run_id,
        vdyp_io_dirname=vdyp_io_dirname,
    )
    if vdyp_log_path is None:
        vdyp_log_path = tsa_paths["run"]
    if vdyp_stdout_log_path is None:
        vdyp_stdout_log_path = tsa_paths["stdout"]
    if vdyp_stderr_log_path is None:
        vdyp_stderr_log_path = tsa_paths["stderr"]

    base_context = build_vdyp_run_context(
        base_context=log_context,
        tsa=tsa,
        run_id=run_id,
        vdyp_stdout_log_path=vdyp_stdout_log_path,
        vdyp_stderr_log_path=vdyp_stderr_log_path,
        vdyp_binpath=vdyp_binpath_path,
        vdyp_params=vdyp_params_path,
    )

    resolved_sampling_seed = (
        sampling_seed if sampling_seed is not None else _sampling_seed_from_env()
    )

    pd_mod = importlib.import_module("pandas")

    def _normalize_feature_ids(values: Sequence[Any]) -> list[int]:
        result: list[int] = []
        for value in values:
            try:
                result.append(int(value))
            except (TypeError, ValueError):
                continue
        return result

    def _normalize_polygon_key(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, float) and np.isnan(value):
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return str(int(float(text)))
        except (TypeError, ValueError):
            return text

    sample_feature_to_map_id: dict[int, str] = {}
    sample_feature_to_map_polygon: dict[int, tuple[str, str]] = {}
    sample_polygon_column = next(
        (
            col
            for col in ("POLYGON_ID", "POLYGON_NUMBER")
            if col in sample_table.columns
        ),
        None,
    )
    if "FEATURE_ID" in sample_table.columns and "MAP_ID" in sample_table.columns:
        source_pairs = sample_table[["FEATURE_ID", "MAP_ID"]].dropna()
        for row in source_pairs.itertuples(index=False):
            try:
                source_feature_id = int(row.FEATURE_ID)
            except (TypeError, ValueError):
                continue
            map_id = str(row.MAP_ID).strip()
            if map_id:
                sample_feature_to_map_id[source_feature_id] = map_id
        if sample_polygon_column is not None:
            source_poly_pairs = sample_table[
                ["FEATURE_ID", "MAP_ID", sample_polygon_column]
            ].dropna()
            for row in source_poly_pairs.itertuples(index=False):
                try:
                    source_feature_id = int(row.FEATURE_ID)
                except (TypeError, ValueError):
                    continue
                map_id = str(row.MAP_ID).strip()
                polygon_key = _normalize_polygon_key(
                    getattr(row, sample_polygon_column)
                )
                if map_id and polygon_key:
                    sample_feature_to_map_polygon[source_feature_id] = (
                        map_id,
                        polygon_key,
                    )

    vdyp_feature_id_set: set[int] = set()
    vdyp_map_to_feature_ids: dict[str, list[int]] = {}
    vdyp_map_polygon_to_feature_ids: dict[tuple[str, str], list[int]] = {}
    vdyp_polygon_column = next(
        (col for col in ("POLYGON_NUMBER", "POLYGON_ID") if col in vdyp_ply.columns),
        None,
    )
    if "FEATURE_ID" in vdyp_ply.columns:
        vdyp_feature_series = pd_mod.to_numeric(
            vdyp_ply["FEATURE_ID"], errors="coerce"
        ).dropna()
        vdyp_feature_ids = vdyp_feature_series.astype(int).tolist()
        vdyp_feature_id_set = set(vdyp_feature_ids)
        if "MAP_ID" in vdyp_ply.columns:
            map_series = (
                vdyp_ply.loc[vdyp_feature_series.index, "MAP_ID"]
                .astype(str)
                .str.strip()
                .tolist()
            )
            polygon_series: list[str | None] = []
            if vdyp_polygon_column is not None:
                polygon_series = [
                    _normalize_polygon_key(value)
                    for value in vdyp_ply.loc[
                        vdyp_feature_series.index, vdyp_polygon_column
                    ].tolist()
                ]
            for feature_id, map_id in zip(vdyp_feature_ids, map_series):
                if not map_id:
                    continue
                vdyp_map_to_feature_ids.setdefault(map_id, []).append(feature_id)
            if polygon_series:
                for feature_id, map_id, polygon_key in zip(
                    vdyp_feature_ids, map_series, polygon_series
                ):
                    if not map_id or not polygon_key:
                        continue
                    vdyp_map_polygon_to_feature_ids.setdefault(
                        (map_id, polygon_key), []
                    ).append(feature_id)
            for map_id in list(vdyp_map_to_feature_ids.keys()):
                vdyp_map_to_feature_ids[map_id] = sorted(
                    set(vdyp_map_to_feature_ids[map_id])
                )
            for map_polygon in list(vdyp_map_polygon_to_feature_ids.keys()):
                vdyp_map_polygon_to_feature_ids[map_polygon] = sorted(
                    set(vdyp_map_polygon_to_feature_ids[map_polygon])
                )

    def _resolve_feature_ids_for_vdyp(
        source_feature_ids: Sequence[Any],
    ) -> tuple[list[int], dict[int, list[int]], bool]:
        source_ids = _normalize_feature_ids(source_feature_ids)
        if not source_ids:
            return [], {}, False

        vdyp_to_source: dict[int, list[int]] = {}
        map_id_offsets: dict[str, int] = {}
        map_polygon_offsets: dict[tuple[str, str], int] = {}
        used_map_join = False

        for source_id in source_ids:
            if source_id in vdyp_feature_id_set:
                vdyp_to_source.setdefault(source_id, []).append(source_id)
                continue

            map_polygon = sample_feature_to_map_polygon.get(source_id)
            if map_polygon:
                polygon_candidates = vdyp_map_polygon_to_feature_ids.get(map_polygon)
                if polygon_candidates:
                    offset = map_polygon_offsets.get(map_polygon, 0)
                    selected_feature_id = int(
                        polygon_candidates[offset % len(polygon_candidates)]
                    )
                    map_polygon_offsets[map_polygon] = offset + 1
                    vdyp_to_source.setdefault(selected_feature_id, []).append(source_id)
                    used_map_join = True
                    continue

            map_id = sample_feature_to_map_id.get(source_id)
            if not map_id:
                continue
            candidates = vdyp_map_to_feature_ids.get(map_id)
            if not candidates:
                continue
            offset = map_id_offsets.get(map_id, 0)
            selected_feature_id = int(candidates[offset % len(candidates)])
            map_id_offsets[map_id] = offset + 1
            vdyp_to_source.setdefault(selected_feature_id, []).append(source_id)
            used_map_join = True

        if not vdyp_to_source:
            return source_ids, {fid: [fid] for fid in source_ids}, False
        return sorted(vdyp_to_source.keys()), vdyp_to_source, used_map_join

    def _run_batch(
        feature_ids: Sequence[Any],
        *,
        timeout: int | float | None = None,
        cache_hits: int = 0,
        phase: str | None = None,
    ) -> dict[Any, Any]:
        source_feature_ids = _normalize_feature_ids(feature_ids)
        feature_count = len(source_feature_ids)
        resolved_feature_ids, vdyp_to_source, used_map_join = (
            _resolve_feature_ids_for_vdyp(source_feature_ids)
        )
        if feature_count == 0:
            append_jsonl_(
                vdyp_log_path,
                build_timestamped_event(
                    event="vdyp_run",
                    status="cache_only",
                    phase=phase,
                    feature_count=0,
                    cache_hits=int(cache_hits),
                    context=base_context,
                ),
            )
            return {}
        append_jsonl_(
            vdyp_log_path,
            build_timestamped_event(
                event="vdyp_run",
                status="start",
                phase=phase,
                feature_count=int(feature_count),
                cache_hits=int(cache_hits),
                context=base_context,
            ),
        )
        vdyp_out = execute_vdyp_batch_(
            feature_ids=resolved_feature_ids,
            vdyp_ply=vdyp_ply,
            vdyp_lyr=vdyp_lyr,
            vdyp_binpath=vdyp_binpath,
            vdyp_params_infile=vdyp_params_infile,
            vdyp_io_dirname=vdyp_io_dirname,
            vdyp_log_path=vdyp_log_path,
            vdyp_stdout_log_path=vdyp_stdout_log_path,
            vdyp_stderr_log_path=vdyp_stderr_log_path,
            phase=phase or "unknown",
            cache_hits=cache_hits,
            timeout=int(timeout) if timeout is not None else 30,
            run_id=run_id,
            base_context=base_context,
            write_vdyp_infiles=write_vdyp_infiles_fn,
            import_vdyp_tables_fn=import_vdyp_tables_fn,
            append_jsonl_fn=append_jsonl_,
            append_text_fn=append_text_,
        )
        resolved_feature_id_set = set(resolved_feature_ids)
        resolved_out: dict[int, Any] = {}

        map_polygon_offsets_out: dict[tuple[str, str], int] = {}
        for vdyp_table in vdyp_out.values():
            attrs = getattr(vdyp_table, "attrs", None)
            if not isinstance(attrs, Mapping):
                continue
            map_name_raw = attrs.get("vdyp_map_name")
            polygon_raw = attrs.get("vdyp_polygon_id")
            if map_name_raw is None or polygon_raw is None:
                continue
            map_name = str(map_name_raw).strip()
            polygon_key = _normalize_polygon_key(polygon_raw)
            if not map_name or not polygon_key:
                continue
            candidates = vdyp_map_polygon_to_feature_ids.get((map_name, polygon_key))
            if not candidates:
                continue
            candidates = [fid for fid in candidates if fid in resolved_feature_id_set]
            if not candidates:
                continue
            map_polygon = (map_name, polygon_key)
            offset = map_polygon_offsets_out.get(map_polygon, 0)
            selected_feature_id = int(candidates[offset % len(candidates)])
            map_polygon_offsets_out[map_polygon] = offset + 1
            resolved_out[selected_feature_id] = vdyp_table

        for vdyp_feature_id, vdyp_table in vdyp_out.items():
            try:
                vdyp_id_int = int(vdyp_feature_id)
            except (TypeError, ValueError):
                continue
            if (
                vdyp_id_int in resolved_feature_id_set
                and vdyp_id_int not in resolved_out
            ):
                resolved_out[vdyp_id_int] = vdyp_table

        # Some VDYP builds report Polygon ids in output tables instead of input FEATURE_IDs.
        # When counts line up exactly, preserve table order and remap to requested ids.
        used_order_remap = False
        if len(resolved_out) != len(resolved_feature_ids) and len(vdyp_out) >= len(
            resolved_feature_ids
        ):
            resolved_out = {
                int(feature_id): table
                for feature_id, table in zip(
                    resolved_feature_ids, vdyp_out.values(), strict=False
                )
            }
            used_order_remap = True

        if not resolved_out:
            return vdyp_out

        if used_order_remap and verbose:
            message_fn(
                "VDYP output remap via batch order "
                f"(requested={len(resolved_feature_ids)} tables={len(vdyp_out)})"
            )

        source_out: dict[Any, Any] = {}
        for resolved_id, vdyp_table in resolved_out.items():
            source_ids = vdyp_to_source.get(resolved_id) or [resolved_id]
            for source_id in source_ids:
                source_out[source_id] = vdyp_table

        return source_out or vdyp_out

    return run_vdyp_sampling(
        sample_table=sample_table,
        nsamples=nsamples,
        min_samples=min_samples,
        max_samples=max_samples,
        nsamples_c1=nsamples_c1,
        nsamples_c2=nsamples_c2,
        confidence=confidence,
        half_rel_ci=half_rel_ci,
        ipp_mode=ipp_mode,
        vdyp_timeout=vdyp_timeout,
        rc_len=rc_len,
        verbose=verbose,
        vdyp_out_cache=vdyp_out_cache,
        random_seed=resolved_sampling_seed,
        run_batch_fn=lambda feature_ids, **kwargs: _run_batch(feature_ids, **kwargs),
        nsamples_from_curves_fn=lambda vdyp_out, **kwargs: nsamples_from_curves_(
            vdyp_out,
            curve_fit_fn=curve_fit_fn,
            fit_func=fit_func,
            fit_func_bounds_func=fit_func_bounds_func,
            **kwargs,
        ),
        message_fn=message_fn,
    )


def build_run_vdyp_for_stratum_runner(
    *,
    tsa: str,
    run_id: str,
    vdyp_ply: Any,
    vdyp_lyr: Any,
    rc_len: int,
    curve_fit_fn: Callable[..., Any],
    fit_func: Callable[..., Any],
    fit_func_bounds_func: Callable[..., Any],
    append_jsonl_fn: Callable[[str | Path, Any], None] | None = None,
    vdyp_log_path: str | Path | None = None,
    vdyp_stdout_log_path: str | Path | None = None,
    vdyp_stderr_log_path: str | Path | None = None,
    sampling_seed_base: int | None = None,
    run_vdyp_for_stratum_fn: Callable[..., dict[Any, Any]] = run_vdyp_for_stratum,
) -> Callable[..., dict[Any, Any]]:
    """Build a per-TSA VDYP runner callable for bootstrap dispatch helpers."""

    def _run_vdyp(sample_table: Any, **kwargs: Any) -> dict[Any, Any]:
        if "sampling_seed" not in kwargs:
            kwargs["sampling_seed"] = sampling_seed_base
        return run_vdyp_for_stratum_fn(
            sample_table=sample_table,
            tsa=tsa,
            run_id=run_id,
            vdyp_ply=vdyp_ply,
            vdyp_lyr=vdyp_lyr,
            rc_len=rc_len,
            curve_fit_fn=curve_fit_fn,
            fit_func=fit_func,
            fit_func_bounds_func=fit_func_bounds_func,
            append_jsonl_fn=append_jsonl_fn,
            vdyp_log_path=vdyp_log_path,
            vdyp_stdout_log_path=vdyp_stdout_log_path,
            vdyp_stderr_log_path=vdyp_stderr_log_path,
            **kwargs,
        )

    return _run_vdyp


def execute_bootstrap_vdyp_runs(
    *,
    tsa: str,
    run_id: str,
    results_for_tsa: Sequence[tuple[int, str, Any]],
    si_levels: Sequence[str],
    vdyp_run_events_path: str | Path,
    append_jsonl_fn: Callable[[str | Path, Any], None],
    run_vdyp_fn: Callable[..., dict[Any, Any]],
    vdyp_out_cache: dict[Any, Any] | None = None,
    nsamples_mode: str | int = "auto",
    verbose: bool = True,
    half_rel_ci: float = 0.01,
    ipp_mode: str | None = None,
    nsamples_c1: float = 0.05,
    sampling_seed_base: int | None = None,
) -> dict[int, dict[str, dict[Any, Any]]]:
    """Execute bootstrap VDYP runs across stratum/SI combinations."""
    vdyp_results_tsa: dict[int, dict[str, dict[Any, Any]]] = {}
    resolved_sampling_seed_base = (
        sampling_seed_base
        if sampling_seed_base is not None
        else _sampling_seed_from_env()
    )
    for stratumi, sc, result in results_for_tsa:
        vdyp_results_tsa[stratumi] = {}
        for si_index, si_level in enumerate(si_levels):
            si_payload = result.get(si_level) if isinstance(result, Mapping) else None
            si_sample = (
                si_payload.get("ss") if isinstance(si_payload, Mapping) else None
            )
            if si_sample is None or getattr(si_sample, "empty", False):
                if verbose:
                    print(f"skipping VDYP bootstrap ({sc}, {si_level}) - no samples")
                vdyp_results_tsa[stratumi][si_level] = {}
                append_jsonl_fn(
                    vdyp_run_events_path,
                    build_timestamped_event(
                        event="vdyp_run",
                        status="skipped",
                        phase="bootstrap",
                        reason="missing_or_empty_si_sample",
                        context={
                            "run_id": run_id,
                            "tsa": tsa,
                            "stratum_index": int(stratumi),
                            "stratum_code": sc,
                            "si_level": si_level,
                        },
                    ),
                )
                continue
            if verbose:
                print(f"running VDYP in bootstrap sample mode ({sc}, {si_level})")
            run_context = {
                "run_id": run_id,
                "tsa": tsa,
                "stratum_index": int(stratumi),
                "stratum_code": sc,
                "si_level": si_level,
            }
            append_jsonl_fn(
                vdyp_run_events_path,
                build_timestamped_event(
                    event="vdyp_run",
                    status="dispatch",
                    phase="bootstrap",
                    context=run_context,
                ),
            )
            try:
                sampling_seed = None
                if resolved_sampling_seed_base is not None:
                    sampling_seed = (
                        int(resolved_sampling_seed_base)
                        + int(stratumi) * 100
                        + int(si_index)
                    )
                vdyp_out = run_vdyp_fn(
                    si_sample,
                    nsamples=nsamples_mode,
                    verbose=verbose,
                    half_rel_ci=half_rel_ci,
                    ipp_mode=ipp_mode,
                    nsamples_c1=nsamples_c1,
                    vdyp_out_cache=vdyp_out_cache,
                    sampling_seed=sampling_seed,
                    log_context=run_context,
                )
            except _bootstrap_dispatch_exception_types() as exc:
                append_jsonl_fn(
                    vdyp_run_events_path,
                    build_timestamped_event(
                        event="vdyp_run",
                        status="dispatch_error",
                        phase="bootstrap",
                        error_type=type(exc).__name__,
                        error=str(exc),
                        error_repr=repr(exc),
                        traceback=traceback.format_exc(),
                        context=run_context,
                    ),
                )
                raise
            vdyp_results_tsa[stratumi][si_level] = vdyp_out
            if verbose:
                print()
    return vdyp_results_tsa


def build_bootstrap_vdyp_results_runner(
    *,
    tsa: str,
    run_id: str,
    results_for_tsa: Sequence[tuple[int, str, Any]],
    si_levels: Sequence[str],
    vdyp_run_events_path: str | Path,
    append_jsonl_fn: Callable[[str | Path, Any], None],
    run_vdyp_fn: Callable[..., dict[Any, Any]],
    vdyp_out_cache: dict[Any, Any] | None = None,
    nsamples_mode: str | int = "auto",
    sampling_seed_base: int | None = None,
    execute_bootstrap_vdyp_runs_fn: Callable[
        ..., dict[int, dict[str, dict[Any, Any]]]
    ] = execute_bootstrap_vdyp_runs,
) -> Callable[[], dict[int, dict[str, dict[Any, Any]]]]:
    """Build a zero-arg bootstrap callback for `load_or_build_vdyp_results_tsa(...)`."""

    def _run_bootstrap() -> dict[int, dict[str, dict[Any, Any]]]:
        return execute_bootstrap_vdyp_runs_fn(
            tsa=tsa,
            run_id=run_id,
            results_for_tsa=results_for_tsa,
            si_levels=si_levels,
            vdyp_run_events_path=vdyp_run_events_path,
            append_jsonl_fn=append_jsonl_fn,
            run_vdyp_fn=run_vdyp_fn,
            vdyp_out_cache=vdyp_out_cache,
            nsamples_mode=nsamples_mode,
            sampling_seed_base=sampling_seed_base,
        )

    return _run_bootstrap


def execute_vdyp_batch(
    *,
    feature_ids: Sequence[int],
    vdyp_ply: Any,
    vdyp_lyr: Any,
    vdyp_binpath: str,
    vdyp_params_infile: str,
    vdyp_io_dirname: str,
    vdyp_log_path: str | Path,
    vdyp_stdout_log_path: str | Path,
    vdyp_stderr_log_path: str | Path,
    phase: str,
    cache_hits: int = 0,
    timeout: int = 30,
    run_id: str | None = None,
    base_context: Mapping[str, Any] | None = None,
    write_vdyp_infiles: Callable[..., None] | None = None,
    import_vdyp_tables_fn: Callable[[str], dict[Any, Any]] | None = None,
    append_jsonl_fn: Callable[[str | Path, Any], None] | None = None,
    append_text_fn: Callable[[str | Path, str], None] | None = None,
    build_stream_header_fn: Callable[..., str] | None = None,
    build_stream_log_block_fn: Callable[..., str] | None = None,
    subprocess_run: Callable[..., Any] | None = None,
) -> dict[Any, Any]:
    """Run one VDYP batch and return parsed per-feature output tables."""
    feature_ids_list = list(feature_ids)
    if not feature_ids_list:
        return {}
    deps = resolve_vdyp_batch_execution_dependencies(
        write_vdyp_infiles=write_vdyp_infiles,
        import_vdyp_tables_fn=import_vdyp_tables_fn,
        append_jsonl_fn=append_jsonl_fn,
        append_text_fn=append_text_fn,
        build_stream_header_fn=build_stream_header_fn,
        build_stream_log_block_fn=build_stream_log_block_fn,
        subprocess_run=subprocess_run,
    )

    feature_count = len(feature_ids_list)
    vdyp_ply_ = vdyp_ply[vdyp_ply.FEATURE_ID.isin(feature_ids_list)]
    vdyp_lyr_ = vdyp_lyr[vdyp_lyr.FEATURE_ID.isin(feature_ids_list)]
    ply_rows = vdyp_ply_.shape[0]
    lyr_rows = vdyp_lyr_.shape[0]
    counts = normalize_vdyp_run_event_counts(
        feature_count=feature_count,
        cache_hits=cache_hits,
        ply_rows=ply_rows,
        lyr_rows=lyr_rows,
    )
    context = build_vdyp_run_context(
        base_context=base_context,
        run_id=run_id,
    )

    vdyp_io_dir = Path(vdyp_io_dirname)
    vdyp_io_dir.mkdir(parents=True, exist_ok=True)

    with (
        tempfile.NamedTemporaryFile(
            dir=vdyp_io_dir,
            prefix="vdyp_ply_",
            suffix=".csv",
            delete=False,
        ) as vdyp_ply_csv_,
        tempfile.NamedTemporaryFile(
            dir=vdyp_io_dir,
            prefix="vdyp_lyr_",
            suffix=".csv",
            delete=False,
        ) as vdyp_lyr_csv_,
        tempfile.NamedTemporaryFile(
            dir=vdyp_io_dir,
            prefix="vdyp_out_",
            suffix=".out",
            delete=False,
        ) as vdyp_out_txt_,
        tempfile.NamedTemporaryFile(
            dir=vdyp_io_dir,
            prefix="vdyp_err_",
            suffix=".err",
            delete=False,
        ) as vdyp_err_txt_,
    ):
        temp_artifacts = resolve_vdyp_batch_temp_artifacts(
            vdyp_ply_name=vdyp_ply_csv_.name,
            vdyp_lyr_name=vdyp_lyr_csv_.name,
            vdyp_out_name=vdyp_out_txt_.name,
            vdyp_err_name=vdyp_err_txt_.name,
        )

        deps.write_vdyp_infiles(
            feature_ids_list,
            vdyp_ply,
            vdyp_lyr,
            str(vdyp_io_dir),
            temp_artifacts.vdyp_ply_csv,
            temp_artifacts.vdyp_lyr_csv,
        )

        run_started = time.time()
        args = build_vdyp_batch_command(
            vdyp_binpath=vdyp_binpath,
            vdyp_params_infile=vdyp_params_infile,
            vdyp_io_dir=vdyp_io_dir,
            vdyp_ply_csv=temp_artifacts.vdyp_ply_csv,
            vdyp_lyr_csv=temp_artifacts.vdyp_lyr_csv,
            vdyp_out_txt=temp_artifacts.vdyp_out_txt,
            vdyp_err_txt=temp_artifacts.vdyp_err_txt,
            vdyp_cfg_dir=os.environ.get("FEMIC_VDYP_CFG_DIR"),
        )
        try:
            result = deps.subprocess_run(
                shlex.split(args, posix=os.name != "nt"),
                timeout=timeout,
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired as exc:
            emit_vdyp_run_event(
                append_jsonl_fn=deps.append_jsonl,
                vdyp_log_path=vdyp_log_path,
                status="timeout",
                phase=phase,
                counts=counts,
                cmd=args,
                context=context,
                timeout_sec=timeout,
                error=str(exc),
            )
            return {}
        except _subprocess_run_exception_types() as exc:
            emit_vdyp_run_event(
                append_jsonl_fn=deps.append_jsonl,
                vdyp_log_path=vdyp_log_path,
                status="error",
                phase=phase,
                counts=counts,
                cmd=args,
                context=context,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return {}

        stream_header = deps.build_stream_header(
            phase=phase,
            feature_count=counts.feature_count,
            cache_hits=counts.cache_hits,
            cmd=args,
        )
        if result.stdout:
            deps.append_text(
                vdyp_stdout_log_path,
                deps.build_stream_log_block(
                    stream_header=stream_header,
                    stream_text=result.stdout,
                ),
            )
        if result.stderr:
            deps.append_text(
                vdyp_stderr_log_path,
                deps.build_stream_log_block(
                    stream_header=stream_header,
                    stream_text=result.stderr,
                ),
            )

        run_metadata = collect_vdyp_batch_run_metadata(
            result=result,
            out_path=temp_artifacts.out_path,
            err_path=temp_artifacts.err_path,
            run_started=run_started,
        )
        try:
            vdyp_out = deps.import_vdyp_tables(
                str(vdyp_io_dir / temp_artifacts.vdyp_out_txt)
            )
        except _vdyp_parse_exception_types() as exc:
            emit_vdyp_run_event(
                append_jsonl_fn=deps.append_jsonl,
                vdyp_log_path=vdyp_log_path,
                status="parse_error",
                phase=phase,
                counts=counts,
                cmd=args,
                context=context,
                **run_metadata,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return {}

        emit_vdyp_run_event(
            append_jsonl_fn=deps.append_jsonl,
            vdyp_log_path=vdyp_log_path,
            status="ok" if vdyp_out else "empty_output",
            phase=phase,
            counts=counts,
            cmd=args,
            context=context,
            **run_metadata,
            vdyp_out_tables=int(len(vdyp_out)),
        )
        return vdyp_out


def execute_curve_smoothing_runs(
    *,
    tsa: str,
    run_id: str,
    results_for_tsa: Sequence[tuple[int, str, Any]],
    si_levels: Sequence[str],
    vdyp_results_for_tsa: Mapping[int, Mapping[str, dict[Any, Any]]],
    kwarg_overrides_for_tsa: Mapping[tuple[str, str], Mapping[str, Any]],
    process_vdyp_out_fn: Callable[..., tuple[Sequence[float], Sequence[float]]],
    append_jsonl_fn: Callable[[str | Path, Any], None],
    vdyp_curve_events_path: str | Path,
    curve_fit_fn: Callable[..., Any],
    body_fit_func: Callable[..., Any],
    body_fit_func_bounds_func: Callable[..., Any],
    toe_fit_func: Callable[..., Any],
    toe_fit_func_bounds_func: Callable[..., Any],
    message_fn: Callable[..., Any] = print,
) -> list[SmoothedCurveResult]:
    """Build smoothed VDYP curves for each stratum/SI combination."""

    fit_gate_max_mape = 2.0
    fit_gate_max_early_overshoot = 8.0
    fit_gate_catastrophic_mape = float(
        os.environ.get("FEMIC_FIT_GATE_CATASTROPHIC_MAPE", "0.90")
    )
    fit_gate_max_early_underfit = float(
        os.environ.get("FEMIC_FIT_GATE_MAX_EARLY_UNDERFIT", "100000.0")
    )
    dominant_recovery_max_metric_ratio = float(
        os.environ.get("FEMIC_DOMINANT_RECOVERY_MAX_METRIC_RATIO", "0.40")
    )
    body_c_min_default = float(os.environ.get("FEMIC_BODY_C_MIN", "-20.0"))
    merchantable_floor_age = 20.0
    merchantable_floor_value = 0.0
    toe_shift_default_years = float(
        os.environ.get("FEMIC_VDYP_TOE_SHIFT_YEARS", "0.0")
    )
    tail_default_linear_min_points = int(
        os.environ.get("FEMIC_TAIL_LINEAR_MIN_POINTS", "4")
    )
    tail_default_linear_min_r2 = float(
        os.environ.get("FEMIC_TAIL_LINEAR_MIN_R2", "0.10")
    )
    tail_default_linear_max_nrmse = float(
        os.environ.get("FEMIC_TAIL_LINEAR_MAX_NRMSE", "0.65")
    )
    tail_default_linear_prefer_min_age = float(
        os.environ.get("FEMIC_TAIL_LINEAR_PREFER_MIN_AGE", "70.0")
    )
    tail_default_linear_flat_slope_abs = float(
        os.environ.get("FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS", "0.25")
    )
    tail_default_linear_min_span_years = float(
        os.environ.get("FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS", "10.0")
    )
    tail_default_blend_years = float(os.environ.get("FEMIC_TAIL_BLEND_YEARS", "120.0"))
    tail_select_min_tail_improvement = float(
        os.environ.get("FEMIC_TAIL_SELECT_MIN_TAIL_IMPROVEMENT", "0.96")
    )
    tail_select_max_rmse_ratio = float(
        os.environ.get("FEMIC_TAIL_SELECT_MAX_RMSE_RATIO", "1.12")
    )
    tail_select_max_mape_ratio = float(
        os.environ.get("FEMIC_TAIL_SELECT_MAX_MAPE_RATIO", "1.15")
    )
    tail_select_max_early_overshoot_ratio = float(
        os.environ.get("FEMIC_TAIL_SELECT_MAX_EARLY_OVERSHOOT_RATIO", "1.20")
    )
    tail_select_close_tolerance = float(
        os.environ.get("FEMIC_TAIL_SELECT_CLOSE_TOLERANCE", "0.06")
    )
    left_toe_low_ratio_threshold = float(
        os.environ.get("FEMIC_LEFT_TOE_LOW_RATIO_THRESHOLD", "1.8")
    )
    left_toe_low_abs_excess = float(
        os.environ.get("FEMIC_LEFT_TOE_LOW_ABS_EXCESS", "4.0")
    )
    left_toe_slope_kink_ratio = float(
        os.environ.get("FEMIC_LEFT_TOE_SLOPE_KINK_RATIO", "2.5")
    )
    left_toe_slope_kink_abs = float(
        os.environ.get("FEMIC_LEFT_TOE_SLOPE_KINK_ABS", "4.0")
    )
    left_toe_structural_min_skip = int(
        os.environ.get("FEMIC_LEFT_TOE_STRUCTURAL_MIN_SKIP", "4")
    )
    left_toe_structural_max_rmse_ratio = float(
        os.environ.get("FEMIC_LEFT_TOE_STRUCTURAL_MAX_RMSE_RATIO", "1.02")
    )
    left_toe_structural_max_tail_rmse_ratio = float(
        os.environ.get("FEMIC_LEFT_TOE_STRUCTURAL_MAX_TAIL_RMSE_RATIO", "1.03")
    )
    left_toe_structural_max_mape_ratio = float(
        os.environ.get("FEMIC_LEFT_TOE_STRUCTURAL_MAX_MAPE_RATIO", "1.03")
    )
    auto_skip_head_drop_ratio_threshold = float(
        os.environ.get("FEMIC_AUTO_SKIP_HEAD_DROP_RATIO_THRESHOLD", "1.8")
    )
    auto_skip_head_drop_abs_threshold = float(
        os.environ.get("FEMIC_AUTO_SKIP_HEAD_DROP_ABS_THRESHOLD", "3.0")
    )

    def _with_curve_defaults(params: dict[str, Any]) -> dict[str, Any]:
        params.setdefault("toe_shift_years", toe_shift_default_years)
        params.setdefault("body_c_min", body_c_min_default)
        return params

    def _with_tail_defaults(params: dict[str, Any]) -> dict[str, Any]:
        params.setdefault("tail_linear_min_points", tail_default_linear_min_points)
        params.setdefault("tail_linear_min_r2", tail_default_linear_min_r2)
        params.setdefault("tail_linear_max_nrmse", tail_default_linear_max_nrmse)
        params.setdefault(
            "tail_linear_prefer_min_age", tail_default_linear_prefer_min_age
        )
        params.setdefault(
            "tail_linear_flat_slope_abs", tail_default_linear_flat_slope_abs
        )
        params.setdefault(
            "tail_linear_min_span_years", tail_default_linear_min_span_years
        )
        params.setdefault("tail_linear_allow_quantile_fallback", True)
        params.setdefault("tail_blend_years", tail_default_blend_years)
        return params

    def _toe_shift_years_for_kwargs(params: Mapping[str, Any]) -> float:
        value = params.get("toe_shift_years", 0.0)
        try:
            years = float(value)
        except (TypeError, ValueError):
            years = 0.0
        return max(0.0, years)

    def _toe_shift_active(params: Mapping[str, Any]) -> bool:
        return _toe_shift_years_for_kwargs(params) > 0.0

    def _build_observed_bins(vdyp_out: Mapping[Any, Any]) -> Any | None:
        pd_module = importlib.import_module("pandas")
        vdyp_tables = [
            table
            for table in vdyp_out.values()
            if isinstance(table, pd_module.DataFrame)
        ]
        if not vdyp_tables:
            return None
        observed = pd_module.concat(vdyp_tables).reset_index()
        if "Age" not in observed.columns or "Vdwb" not in observed.columns:
            return None
        observed = observed[["Age", "Vdwb"]].dropna()
        observed = observed[(observed["Age"] >= 30) & (observed["Age"] < 300)]
        if observed.empty:
            return None
        observed["age_bin"] = (observed["Age"] // 5) * 5
        binned = observed.groupby("age_bin", as_index=False).agg(
            median_volume=("Vdwb", "median"),
            p25=("Vdwb", lambda s: float(s.quantile(0.25))),
            p75=("Vdwb", lambda s: float(s.quantile(0.75))),
            n=("Vdwb", "count"),
        )
        return binned if not binned.empty else None

    def _fit_quality(
        *,
        binned: Any,
        x_curve: Sequence[float],
        y_curve: Sequence[float],
    ) -> dict[str, float]:
        obs_age = np.asarray(binned["age_bin"].values, dtype=float)
        obs_vol = np.asarray(binned["median_volume"].values, dtype=float)
        pred = np.interp(
            obs_age, np.asarray(x_curve, dtype=float), np.asarray(y_curve, dtype=float)
        )
        resid = pred - obs_vol
        rmse = float(np.sqrt(np.mean(np.square(resid))))
        denom = np.maximum(obs_vol, 1e-6)
        mape = float(np.mean(np.abs(resid) / denom))
        tail_start = float(np.quantile(obs_age, 0.70))
        tail = obs_age >= tail_start
        tail_rmse = (
            float(np.sqrt(np.mean(np.square(resid[tail])))) if np.any(tail) else rmse
        )
        early = obs_age <= float(np.quantile(obs_age, 0.35))
        early_overshoot = (
            float(np.max(pred[early] / np.maximum(obs_vol[early], 1e-6)))
            if np.any(early)
            else 1.0
        )
        early_underfit = (
            float(np.max(obs_vol[early] / np.maximum(pred[early], 1e-6)))
            if np.any(early)
            else 1.0
        )
        return {
            "rmse": rmse,
            "mape": mape,
            "tail_rmse": tail_rmse,
            "early_overshoot": early_overshoot,
            "early_underfit": early_underfit,
        }

    def _evaluate_fit_quality_gate(
        *,
        y_curve: Sequence[float],
        metrics: Mapping[str, float] | None,
    ) -> list[str]:
        reasons: list[str] = []
        y_vals = np.asarray(y_curve, dtype=float)
        if y_vals.size == 0:
            reasons.append("empty_curve")
            return reasons
        if not np.all(np.isfinite(y_vals)):
            reasons.append("non_finite_curve")
        if float(np.nanmin(y_vals)) < -1e-6:
            reasons.append("negative_volume")
        if metrics is None:
            return reasons
        mape = float(metrics.get("mape", float("nan")))
        early_overshoot = float(metrics.get("early_overshoot", float("nan")))
        early_underfit = float(metrics.get("early_underfit", float("nan")))
        if not math.isfinite(mape):
            reasons.append("non_finite_mape")
        elif mape > fit_gate_max_mape:
            reasons.append("mape_exceeds_gate")
        elif mape >= fit_gate_catastrophic_mape:
            reasons.append("catastrophic_mape")
        if not math.isfinite(early_overshoot):
            reasons.append("non_finite_early_overshoot")
        elif early_overshoot > fit_gate_max_early_overshoot:
            reasons.append("early_overshoot_exceeds_gate")
        if not math.isfinite(early_underfit):
            reasons.append("non_finite_early_underfit")
        elif early_underfit > fit_gate_max_early_underfit:
            reasons.append("early_underfit_exceeds_gate")
        return reasons

    def _dominant_recovery_decision(
        *,
        baseline_metrics: Mapping[str, float],
        candidate_metrics: Mapping[str, float],
    ) -> dict[str, Any]:
        baseline_rmse = float(baseline_metrics.get("rmse", float("nan")))
        baseline_mape = float(baseline_metrics.get("mape", float("nan")))
        baseline_tail_rmse = float(baseline_metrics.get("tail_rmse", float("nan")))
        baseline_early_underfit = float(
            baseline_metrics.get("early_underfit", float("nan"))
        )
        candidate_rmse = float(candidate_metrics.get("rmse", float("nan")))
        candidate_mape = float(candidate_metrics.get("mape", float("nan")))
        candidate_tail_rmse = float(candidate_metrics.get("tail_rmse", float("nan")))
        candidate_early_overshoot = float(
            candidate_metrics.get("early_overshoot", float("nan"))
        )
        finite = all(
            math.isfinite(v)
            for v in (
                baseline_rmse,
                baseline_mape,
                baseline_tail_rmse,
                baseline_early_underfit,
                candidate_rmse,
                candidate_mape,
                candidate_tail_rmse,
                candidate_early_overshoot,
            )
        )
        if not finite:
            return {
                "selected": False,
                "decision": "reject_non_finite_metrics",
                "baseline_catastrophic": False,
            }
        if baseline_rmse <= 0 or baseline_mape <= 0 or baseline_tail_rmse <= 0:
            return {
                "selected": False,
                "decision": "reject_invalid_baseline",
                "baseline_catastrophic": False,
            }

        rmse_ratio = candidate_rmse / baseline_rmse
        mape_ratio = candidate_mape / baseline_mape
        tail_rmse_ratio = candidate_tail_rmse / baseline_tail_rmse
        baseline_catastrophic = (
            baseline_mape >= fit_gate_catastrophic_mape
            or baseline_early_underfit > fit_gate_max_early_underfit
        )
        candidate_safe_overshoot = (
            candidate_early_overshoot <= fit_gate_max_early_overshoot
        )
        dominant_improvement = (
            rmse_ratio <= dominant_recovery_max_metric_ratio
            and mape_ratio <= dominant_recovery_max_metric_ratio
            and tail_rmse_ratio <= dominant_recovery_max_metric_ratio
        )
        selected = bool(
            baseline_catastrophic and dominant_improvement and candidate_safe_overshoot
        )
        return {
            "selected": selected,
            "decision": "selected" if selected else "rejected",
            "baseline_catastrophic": bool(baseline_catastrophic),
            "dominant_improvement": bool(dominant_improvement),
            "candidate_safe_overshoot": bool(candidate_safe_overshoot),
            "rmse_ratio": float(rmse_ratio),
            "mape_ratio": float(mape_ratio),
            "tail_rmse_ratio": float(tail_rmse_ratio),
        }

    def _infer_auto_skip1(
        *,
        binned: Any,
        x_curve: Sequence[float],
        y_curve: Sequence[float],
        current_skip1: int,
    ) -> int:
        obs_age = np.asarray(binned["age_bin"].values, dtype=float)
        obs_vol = np.asarray(binned["median_volume"].values, dtype=float)
        pred = np.interp(
            obs_age, np.asarray(x_curve, dtype=float), np.asarray(y_curve, dtype=float)
        )
        early_limit = float(np.quantile(obs_age, 0.40))
        early = obs_age <= early_limit
        if not np.any(early):
            return int(current_skip1)
        ratio = pred[early] / np.maximum(obs_vol[early], 1e-6)
        bad = ratio > 1.8
        if not np.any(bad):
            suggested_ratio = int(current_skip1)
        else:
            cutoff_age = float(np.max(obs_age[early][bad]))
            suggested_ratio = int(np.count_nonzero(obs_age <= cutoff_age))

        # Prefer minimal leading discontinuity censor when early bins show a
        # clear high shoulder then abrupt drop.
        suggested_head = int(current_skip1)
        if obs_vol.size >= 5:
            head = np.asarray(obs_vol[: min(8, obs_vol.size)], dtype=float)
            if head.size >= 4:
                head_diff = np.diff(head)
                drop_idx = int(np.argmin(head_diff))
                drop_val = float(head_diff[drop_idx])
                if drop_val <= -auto_skip_head_drop_abs_threshold:
                    left_med = float(np.median(head[: drop_idx + 1]))
                    right_end = min(head.size, drop_idx + 3)
                    right_med = float(np.median(head[drop_idx + 1 : right_end]))
                    if (
                        left_med / max(right_med, 1e-6)
                        >= auto_skip_head_drop_ratio_threshold
                    ):
                        suggested_head = int(drop_idx + 1)
        if suggested_head > int(current_skip1):
            return int(suggested_head)
        return int(max(current_skip1, suggested_ratio))

    def _infer_left_toe_censor_skip(
        *,
        binned: Any,
        current_skip1: int,
    ) -> int:
        obs_age = np.asarray(binned["age_bin"].values, dtype=float)
        obs_vol = np.asarray(binned["median_volume"].values, dtype=float)
        if obs_age.size < 6 or obs_vol.size < 6:
            return int(current_skip1)
        early_limit = float(np.quantile(obs_age, 0.40))
        early_idx = np.where(obs_age <= early_limit)[0]
        if early_idx.size < 3:
            return int(current_skip1)
        suggested = int(current_skip1)
        for idx in early_idx:
            if idx < current_skip1:
                continue
            if idx + 2 >= obs_vol.size:
                break
            next_window = obs_vol[idx + 1 : idx + 4]
            if next_window.size == 0:
                break
            next_median = float(np.median(next_window))
            current = float(obs_vol[idx])
            if next_median <= 0:
                continue
            ratio = current / next_median
            abs_excess = current - next_median
            if ratio >= 1.8 and abs_excess >= 5.0:
                suggested = max(suggested, idx + 1)
                continue
            low_ratio = next_median / max(current, 1e-6)
            low_excess = next_median - current
            if (
                low_ratio >= left_toe_low_ratio_threshold
                and low_excess >= left_toe_low_abs_excess
            ):
                suggested = max(suggested, idx + 1)
                continue
            next_val = float(obs_vol[idx + 1])
            if next_val > 0:
                sharp_drop = current / next_val
                if sharp_drop >= 1.6 and abs(current - next_val) >= 5.0:
                    suggested = max(suggested, idx + 1)
            if idx + 3 < obs_vol.size:
                initial_slope = float(obs_vol[idx + 1] - obs_vol[idx])
                follow_slopes = np.diff(obs_vol[idx + 1 : idx + 4])
                if follow_slopes.size > 0:
                    follow_scale = float(np.median(np.abs(follow_slopes)))
                    if abs(initial_slope) >= left_toe_slope_kink_abs and abs(
                        initial_slope
                    ) >= left_toe_slope_kink_ratio * max(follow_scale, 1e-6):
                        suggested = max(suggested, idx + 1)
        return int(suggested)

    def _run_candidate(
        *,
        vdyp_out: Mapping[Any, Any],
        curve_context: Mapping[str, Any],
        kwargs: Mapping[str, Any],
        candidate_name: str,
    ) -> tuple[Sequence[float], Sequence[float]] | None:
        try:
            x_c, y_c = process_vdyp_out_fn(
                vdyp_out,
                curve_fit_fn=curve_fit_fn,
                body_fit_func=body_fit_func,
                body_fit_func_bounds_func=body_fit_func_bounds_func,
                toe_fit_func=toe_fit_func,
                toe_fit_func_bounds_func=toe_fit_func_bounds_func,
                log_event=lambda payload: append_jsonl_fn(
                    vdyp_curve_events_path, payload
                ),
                message=None,
                curve_context=dict(curve_context, candidate=candidate_name),
                **dict(kwargs),
            )
            x_arr = np.asarray(x_c, dtype=float)
            y_arr = np.asarray(y_c, dtype=float)
            if (
                x_arr.size == 0
                or y_arr.size == 0
                or x_arr.size != y_arr.size
                or not np.all(np.isfinite(x_arr))
                or not np.all(np.isfinite(y_arr))
            ):
                append_jsonl_fn(
                    vdyp_curve_events_path,
                    build_timestamped_event(
                        event="vdyp_curve_fit",
                        status="warning",
                        stage="candidate_validation",
                        reason="candidate_rejected_non_finite",
                        context=curve_context,
                        candidate_name=candidate_name,
                        x_size=int(x_arr.size),
                        y_size=int(y_arr.size),
                    ),
                )
                return None
            return x_c, y_c
        except Exception:
            return None

    def _select_tail_blend_candidate(
        *,
        current_metrics: Mapping[str, float],
        tail_metrics: Mapping[str, float],
    ) -> tuple[bool, dict[str, Any]]:
        current_tail = float(current_metrics.get("tail_rmse", float("nan")))
        current_rmse = float(current_metrics.get("rmse", float("nan")))
        current_mape = float(current_metrics.get("mape", float("nan")))
        current_early = float(current_metrics.get("early_overshoot", float("nan")))
        tail_tail = float(tail_metrics.get("tail_rmse", float("nan")))
        tail_rmse = float(tail_metrics.get("rmse", float("nan")))
        tail_mape = float(tail_metrics.get("mape", float("nan")))
        tail_early = float(tail_metrics.get("early_overshoot", float("nan")))

        finite = all(
            math.isfinite(v)
            for v in (
                current_tail,
                current_rmse,
                current_mape,
                current_early,
                tail_tail,
                tail_rmse,
                tail_mape,
                tail_early,
            )
        )
        if not finite:
            return False, {"decision": "reject_non_finite_metrics"}
        if current_tail <= 0 or current_rmse <= 0 or current_mape <= 0:
            return False, {"decision": "reject_invalid_current_baseline"}

        improve_tail = tail_tail <= (tail_select_min_tail_improvement * current_tail)
        non_harm_guard = (
            tail_rmse <= (tail_select_max_rmse_ratio * current_rmse)
            and tail_mape <= (tail_select_max_mape_ratio * current_mape)
            and tail_early <= (tail_select_max_early_overshoot_ratio * current_early)
        )
        close_tail = abs(tail_tail - current_tail) <= (
            tail_select_close_tolerance * current_tail
        )
        improve_global = (
            (tail_rmse < current_rmse)
            and (tail_mape <= (1.05 * current_mape))
            and (tail_early <= (1.10 * current_early))
        )
        tie_break = (
            close_tail and (tail_rmse < current_rmse) and (tail_mape <= current_mape)
        )
        dominant_recovery = _dominant_recovery_decision(
            baseline_metrics=current_metrics,
            candidate_metrics=tail_metrics,
        )
        selected = bool(
            (non_harm_guard and (improve_tail or improve_global or tie_break))
            or bool(dominant_recovery.get("selected", False))
        )
        decision = "selected" if selected else "rejected"
        return selected, {
            "decision": decision,
            "improve_tail": bool(improve_tail),
            "improve_global": bool(improve_global),
            "non_harm_guard": bool(non_harm_guard),
            "tie_break": bool(tie_break),
            "close_tail": bool(close_tail),
            "dominant_recovery": dominant_recovery,
        }

    def _max_pre_merchantable_volume(
        *,
        x_curve: Sequence[float],
        y_curve: Sequence[float],
        floor_age: float,
    ) -> float:
        x_vals = np.asarray(x_curve, dtype=float)
        y_vals = np.asarray(y_curve, dtype=float)
        if x_vals.size == 0 or y_vals.size == 0:
            return 0.0
        max_eval_age = int(max(1, round(float(floor_age))))
        eval_ages = np.arange(1.0, float(max_eval_age) + 1.0, 1.0, dtype=float)
        pred = np.interp(eval_ages, x_vals, y_vals)
        finite_pred = pred[np.isfinite(pred)]
        if finite_pred.size == 0:
            return 0.0
        return float(np.max(finite_pred))

    def _estimate_tail_blend_window(
        *,
        binned: Any | None,
        anchor_quantile: float,
        blend_years: float,
    ) -> dict[str, float] | None:
        if binned is None:
            return None
        ages = np.asarray(binned["age_bin"].values, dtype=float)
        if ages.size == 0:
            return None
        anchor_age = float(
            np.quantile(ages, float(np.clip(anchor_quantile, 0.5, 0.95)))
        )
        tail_end_age = float(
            min(np.max(ages), anchor_age + max(1.0, float(blend_years)))
        )
        return {"anchor_age": anchor_age, "tail_end_age": tail_end_age}

    def _emit_fit_diagnostic_plot(
        *,
        tsa_code: str,
        stratumi: int,
        stratum_code: str,
        si_level: str,
        vdyp_out: Mapping[Any, Any],
        binned: Any | None,
        x_fit: Sequence[float],
        y_fit: Sequence[float],
        selected_x: Sequence[float],
        selected_y: Sequence[float],
        selected_path: str,
        tail_blend_meta: Mapping[str, Any] | None,
        candidate_curves: Mapping[str, tuple[Sequence[float], Sequence[float]]],
        fit_metrics: Mapping[str, Mapping[str, float]],
    ) -> None:
        try:
            plt_module = importlib.import_module("matplotlib.pyplot")
        except ModuleNotFoundError:
            return
        plot_root = Path("plots")
        plot_root.mkdir(parents=True, exist_ok=True)
        plot_path = plot_root / (
            f"vdyp_fitdiag_tsa{str(tsa_code).zfill(2)}-"
            f"{str(stratumi).zfill(2)}-{stratum_code}-{si_level}.png"
        )

        fig, (ax, ax_resid) = plt_module.subplots(
            2, 1, figsize=(8, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
        )
        pd_module = importlib.import_module("pandas")
        raw_label_used = False
        for table in vdyp_out.values():
            if not isinstance(table, pd_module.DataFrame):
                continue
            raw = table.reset_index()
            if "Age" not in raw.columns or "Vdwb" not in raw.columns:
                continue
            raw = raw[["Age", "Vdwb"]].dropna()
            raw = raw[
                (raw["Age"] >= 0)
                & (raw["Age"] <= 300)
                & np.isfinite(raw["Age"])
                & np.isfinite(raw["Vdwb"])
                & (raw["Vdwb"] >= 0)
            ]
            if raw.empty:
                continue
            raw = raw.sort_values("Age")
            ax.plot(
                raw["Age"],
                raw["Vdwb"],
                color="0.5",
                alpha=0.08,
                linewidth=0.4,
                label="Raw VDYP curves" if not raw_label_used else None,
                zorder=1,
            )
            raw_label_used = True
        if binned is not None:
            ax.fill_between(
                binned["age_bin"],
                binned["p25"],
                binned["p75"],
                color="lightblue",
                alpha=0.35,
                label="Observed P25-P75 (5y bins)",
            )
            ax.scatter(
                binned["age_bin"],
                binned["median_volume"],
                s=14,
                color="tab:blue",
                label="Observed median (5y bins)",
            )
        ax.plot(
            list(x_fit), list(y_fit), color="tab:red", linewidth=2, label="Current fit"
        )
        ax.plot(
            list(selected_x),
            list(selected_y),
            color="black",
            linewidth=2.3,
            linestyle="-.",
            label=f"Selected fit ({selected_path})",
        )
        for key, color, label in (
            ("tail_blend", "tab:orange", "Tail-blend fit"),
            ("auto_skip", "tab:purple", "Auto-skip fit"),
            ("left_toe_censor", "tab:brown", "Left-toe censor fit"),
            ("merchantable_floor", "tab:olive", "Merch-floor fit"),
        ):
            curve = candidate_curves.get(key)
            if curve is None:
                continue
            x_c, y_c = curve
            ax.plot(
                list(x_c),
                list(y_c),
                color=color,
                linewidth=1.7,
                linestyle="--",
                label=label,
            )
        ax.set_title(f"VDYP Fit Diagnostic: {stratum_code} {si_level}")
        ax.set_xlabel("Age")
        ax.set_ylabel("Volume")
        ax.set_xlim(0, 300)
        ymax_fit = float(np.nanmax(y_fit)) * 1.05
        ymax_obs = 0.0
        if binned is not None:
            ymax_obs = float(binned["p75"].max()) * 1.15
        ymax = max(ymax_obs, ymax_fit, 1.0)
        ax.set_ylim(0, ymax)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
        stats_lines: list[str] = []
        for name in (
            "current",
            "tail_blend",
            "auto_skip",
            "left_toe_censor",
            "merchantable_floor",
        ):
            metric = fit_metrics.get(name)
            if not metric:
                continue
            stats_lines.append(
                f"{name}: rmse={metric['rmse']:.1f}, tail={metric['tail_rmse']:.1f}, "
                f"early_ratio={metric['early_overshoot']:.2f}"
            )
        if stats_lines:
            ax.text(
                0.01,
                0.99,
                "\n".join(stats_lines),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=7,
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )
        if tail_blend_meta:
            anchor_age = tail_blend_meta.get("anchor_age")
            tail_end_age = tail_blend_meta.get("tail_end_age")
            if anchor_age is not None and tail_end_age is not None:
                ax.axvspan(
                    float(anchor_age),
                    float(tail_end_age),
                    color="orange",
                    alpha=0.08,
                    label="Tail blend window",
                )
                ax.text(
                    0.99,
                    0.01,
                    f"blend [{float(anchor_age):.0f}, {float(tail_end_age):.0f}]",
                    transform=ax.transAxes,
                    ha="right",
                    va="bottom",
                    fontsize=7,
                    bbox={"facecolor": "white", "alpha": 0.65, "edgecolor": "none"},
                )

        if binned is not None:
            obs_age = np.asarray(binned["age_bin"].values, dtype=float)
            obs_vol = np.asarray(binned["median_volume"].values, dtype=float)
            pred_sel = np.interp(
                obs_age,
                np.asarray(selected_x, dtype=float),
                np.asarray(selected_y, dtype=float),
            )
            residual = pred_sel - obs_vol
            ax_resid.axhline(0.0, color="black", linewidth=1.0, alpha=0.6)
            ax_resid.scatter(obs_age, residual, s=14, color="tab:gray", alpha=0.8)
            ax_resid.plot(obs_age, residual, color="tab:gray", linewidth=1.2, alpha=0.7)
            ax_resid.set_ylabel("Residual")
        else:
            ax_resid.set_ylabel("Residual")
        ax_resid.set_xlabel("Age")
        ax_resid.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(plot_path, dpi=150)
        plt_module.close(fig)

    def _emit_lmh_overlay_plot(
        *,
        tsa_code: str,
        runs: Sequence[SmoothedCurveResult],
    ) -> None:
        if not runs:
            return
        try:
            plt_module = importlib.import_module("matplotlib.pyplot")
        except ModuleNotFoundError:
            return
        plot_root = Path("plots")
        plot_root.mkdir(parents=True, exist_ok=True)
        grouped: dict[tuple[int, str], dict[str, SmoothedCurveResult]] = {}
        for run in runs:
            key = (int(run.stratumi), str(run.stratum_code))
            grouped.setdefault(key, {})[str(run.si_level)] = run
        for (stratumi, stratum_code), level_runs in grouped.items():
            if not level_runs:
                continue
            plot_path = plot_root / (
                f"vdyp_lmh_tsa{str(tsa_code).zfill(2)}-"
                f"{str(stratumi).zfill(2)}-{stratum_code}.png"
            )
            fig, ax = plt_module.subplots(1, 1, figsize=(8, 5))
            ymax = 1.0
            for si_level, color in (
                ("L", "tab:blue"),
                ("M", "tab:green"),
                ("H", "tab:red"),
            ):
                level_run = level_runs.get(si_level)
                if level_run is None:
                    continue
                x_vals = np.asarray(level_run.x, dtype=float)
                y_vals = np.asarray(level_run.y, dtype=float)
                if x_vals.size == 0 or y_vals.size == 0:
                    continue
                ax.plot(
                    x_vals,
                    y_vals,
                    linewidth=2.0,
                    color=color,
                    label=f"{si_level} best-fit curve",
                )
                ymax = max(ymax, float(np.nanmax(y_vals)))
            ax.set_title(f"VDYP L/M/H Comparison: {stratum_code}")
            ax.set_xlabel("Age")
            ax.set_ylabel("Volume")
            ax.set_xlim(0, 300)
            ax.set_ylim(0, ymax * 1.05)
            ax.grid(alpha=0.25)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(plot_path, dpi=150)
            plt_module.close(fig)

    smoothed_runs: list[SmoothedCurveResult] = []
    for stratumi, sc, _result in results_for_tsa:
        for si_level in si_levels:
            kwargs = _with_curve_defaults(
                dict(kwarg_overrides_for_tsa.get((sc, si_level), {}))
            )
            curve_context = {
                "run_id": run_id,
                "tsa": tsa,
                "stratum_index": int(stratumi),
                "stratum_code": sc,
                "si_level": si_level,
            }
            vdyp_out = vdyp_results_for_tsa.get(stratumi, {}).get(si_level)
            if not isinstance(vdyp_out, dict) or len(vdyp_out) == 0:
                message_fn("  missing vdyp results for", sc, si_level)
                append_jsonl_fn(
                    vdyp_curve_events_path,
                    build_timestamped_event(
                        event="vdyp_curve_fit",
                        status="warning",
                        stage="curve_input",
                        reason="missing_vdyp_output",
                        context=curve_context,
                    ),
                )
                continue
            x, y = process_vdyp_out_fn(
                vdyp_out,
                curve_fit_fn=curve_fit_fn,
                body_fit_func=body_fit_func,
                body_fit_func_bounds_func=body_fit_func_bounds_func,
                toe_fit_func=toe_fit_func,
                toe_fit_func_bounds_func=toe_fit_func_bounds_func,
                log_event=lambda payload: append_jsonl_fn(
                    vdyp_curve_events_path, payload
                ),
                message=message_fn,
                curve_context=curve_context,
                **kwargs,
            )
            binned_obs = _build_observed_bins(vdyp_out)
            candidate_curves: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
            fit_metrics: dict[str, dict[str, float]] = {}
            tail_blend_meta_for_plot: dict[str, float] | None = None
            if binned_obs is not None:
                fit_metrics["current"] = _fit_quality(
                    binned=binned_obs,
                    x_curve=x,
                    y_curve=y,
                )
                active_kwargs = dict(kwargs)
                initial_skip1 = int(kwargs.get("skip1", 0))
                active_curve: tuple[Sequence[float], Sequence[float]] = (x, y)
                active_metrics = fit_metrics["current"]

                current_skip1 = int(active_kwargs.get("skip1", 0))
                suggested_skip = _infer_auto_skip1(
                    binned=binned_obs,
                    x_curve=x,
                    y_curve=y,
                    current_skip1=current_skip1,
                )
                if suggested_skip > current_skip1:
                    auto_kwargs = dict(kwargs)
                    auto_kwargs["skip1"] = suggested_skip
                    auto_curve = _run_candidate(
                        vdyp_out=vdyp_out,
                        curve_context=dict(curve_context, auto_skip1=suggested_skip),
                        kwargs=auto_kwargs,
                        candidate_name="auto_skip",
                    )
                    if auto_curve is not None:
                        auto_metrics = _fit_quality(
                            binned=binned_obs,
                            x_curve=auto_curve[0],
                            y_curve=auto_curve[1],
                        )
                        baseline = fit_metrics["current"]
                        improved_rmse = auto_metrics["rmse"] <= (
                            0.95 * baseline["rmse"]
                        )
                        improved_tail = (
                            auto_metrics["tail_rmse"] <= baseline["tail_rmse"]
                        )
                        reduced_overshoot = (
                            auto_metrics["early_overshoot"]
                            <= baseline["early_overshoot"]
                        )
                        if improved_rmse and improved_tail and reduced_overshoot:
                            candidate_curves["auto_skip"] = auto_curve
                            fit_metrics["auto_skip"] = auto_metrics
                            active_kwargs["skip1"] = int(suggested_skip)
                            active_curve = auto_curve
                            active_metrics = auto_metrics

                left_toe_base_skip = int(kwargs.get("skip1", 0))
                left_toe_skip = _infer_left_toe_censor_skip(
                    binned=binned_obs,
                    current_skip1=left_toe_base_skip,
                )
                if left_toe_skip > left_toe_base_skip:
                    prior_skip1 = int(active_kwargs.get("skip1", 0))
                    censor_skip = int(max(prior_skip1, left_toe_skip))
                    censor_kwargs = dict(active_kwargs)
                    censor_kwargs["skip1"] = censor_skip
                    censor_curve = _run_candidate(
                        vdyp_out=vdyp_out,
                        curve_context=dict(
                            curve_context,
                            left_toe_censor_skip1=left_toe_skip,
                        ),
                        kwargs=censor_kwargs,
                        candidate_name="left_toe_censor",
                    )
                    if censor_curve is not None:
                        censor_metrics = _fit_quality(
                            binned=binned_obs,
                            x_curve=censor_curve[0],
                            y_curve=censor_curve[1],
                        )
                        fit_metrics["left_toe_censor"] = censor_metrics
                        baseline = active_metrics
                        improved_overshoot = censor_metrics["early_overshoot"] <= (
                            0.80 * baseline["early_overshoot"]
                        )
                        improved_rmse = censor_metrics["rmse"] <= (
                            0.97 * baseline["rmse"]
                        )
                        improved_mape = censor_metrics["mape"] <= baseline["mape"]
                        structural_skip_delta = int(censor_skip - left_toe_base_skip)
                        structural_non_harm = (
                            censor_metrics["rmse"]
                            <= (left_toe_structural_max_rmse_ratio * baseline["rmse"])
                            and censor_metrics["tail_rmse"]
                            <= (
                                left_toe_structural_max_tail_rmse_ratio
                                * baseline["tail_rmse"]
                            )
                            and censor_metrics["mape"]
                            <= (left_toe_structural_max_mape_ratio * baseline["mape"])
                        )
                        structural_discontinuity_accept = (
                            structural_skip_delta >= left_toe_structural_min_skip
                        )
                        dominant_recovery = _dominant_recovery_decision(
                            baseline_metrics=baseline,
                            candidate_metrics=censor_metrics,
                        )
                        additional_after_auto = prior_skip1 > int(initial_skip1)
                        structural_additional_improvement = (
                            improved_rmse or improved_overshoot
                        )
                        structural_accept = bool(
                            structural_discontinuity_accept
                            and structural_non_harm
                            and (
                                (not additional_after_auto)
                                or structural_additional_improvement
                            )
                        )
                        already_applied = prior_skip1 >= int(
                            left_toe_skip
                        ) and prior_skip1 > int(left_toe_base_skip)
                        accepted = (
                            (improved_overshoot and (improved_rmse or improved_mape))
                            or structural_accept
                            or bool(already_applied)
                            or bool(dominant_recovery.get("selected", False))
                        )
                        append_jsonl_fn(
                            vdyp_curve_events_path,
                            build_timestamped_event(
                                event="vdyp_curve_fit",
                                status="info",
                                stage="left_toe_censor",
                                reason=(
                                    "left_toe_censor_selected"
                                    if accepted
                                    else "left_toe_censor_rejected"
                                ),
                                context=curve_context,
                                skip1_before=int(prior_skip1),
                                skip1_after=int(censor_skip),
                                baseline_metrics=dict(baseline),
                                candidate_metrics=dict(censor_metrics),
                                decision={
                                    "already_applied": bool(already_applied),
                                    "improved_overshoot": bool(improved_overshoot),
                                    "improved_rmse": bool(improved_rmse),
                                    "improved_mape": bool(improved_mape),
                                    "structural_skip_delta": int(structural_skip_delta),
                                    "structural_non_harm": bool(structural_non_harm),
                                    "structural_discontinuity_accept": bool(
                                        structural_discontinuity_accept
                                    ),
                                    "structural_accept": bool(structural_accept),
                                    "additional_after_auto": bool(
                                        additional_after_auto
                                    ),
                                    "structural_additional_improvement": bool(
                                        structural_additional_improvement
                                    ),
                                    "dominant_recovery": dominant_recovery,
                                },
                            ),
                        )
                        if accepted:
                            if not already_applied:
                                candidate_curves["left_toe_censor"] = censor_curve
                                active_kwargs["skip1"] = int(censor_skip)
                                active_curve = censor_curve
                                active_metrics = censor_metrics

                tail_kwargs = _with_tail_defaults(dict(active_kwargs))
                tail_kwargs["tail_blend_enabled"] = True
                tail_curve = _run_candidate(
                    vdyp_out=vdyp_out,
                    curve_context=curve_context,
                    kwargs=tail_kwargs,
                    candidate_name="tail_blend",
                )
                tail_selected = False
                if tail_curve is not None:
                    candidate_curves["tail_blend"] = tail_curve
                    fit_metrics["tail_blend"] = _fit_quality(
                        binned=binned_obs,
                        x_curve=tail_curve[0],
                        y_curve=tail_curve[1],
                    )
                    tail_blend_meta_for_plot = _estimate_tail_blend_window(
                        binned=binned_obs,
                        anchor_quantile=float(
                            tail_kwargs.get("tail_anchor_quantile", 0.70)
                        ),
                        blend_years=float(tail_kwargs.get("tail_blend_years", 30.0)),
                    )
                    tail_detected = detect_linear_tail_segment(
                        observed_age=np.asarray(
                            binned_obs["age_bin"].values, dtype=float
                        ),
                        observed_volume=np.asarray(
                            binned_obs["median_volume"].values, dtype=float
                        ),
                        linear_min_points=int(
                            tail_kwargs.get("tail_linear_min_points", 4)
                        ),
                        linear_min_r2=float(
                            tail_kwargs.get("tail_linear_min_r2", 0.75)
                        ),
                        linear_max_nrmse=float(
                            tail_kwargs.get("tail_linear_max_nrmse", 0.18)
                        ),
                        linear_prefer_min_age=float(
                            tail_kwargs.get("tail_linear_prefer_min_age", 180.0)
                        ),
                        linear_flat_slope_abs=float(
                            tail_kwargs.get("tail_linear_flat_slope_abs", 0.04)
                        ),
                        linear_min_span_years=float(
                            tail_kwargs.get("tail_linear_min_span_years", 80.0)
                        ),
                    )
                    tail_detect_gate = bool(tail_detected is not None) or bool(
                        tail_kwargs.get("tail_linear_allow_quantile_fallback", False)
                    )
                    if tail_detect_gate:
                        tail_selected, tail_decision = _select_tail_blend_candidate(
                            current_metrics=active_metrics,
                            tail_metrics=fit_metrics["tail_blend"],
                        )
                    else:
                        tail_selected = False
                        tail_decision = {"decision": "reject_not_detected"}
                    tail_decision = {
                        **tail_decision,
                        "policy": "layered_when_detected",
                        "tail_detected": bool(tail_detected is not None),
                        "tail_detect_gate": bool(tail_detect_gate),
                    }
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_timestamped_event(
                            event="vdyp_curve_fit",
                            status="info",
                            stage="tail_blend_selection",
                            reason=(
                                "tail_blend_selected"
                                if tail_selected
                                else "tail_blend_rejected"
                            ),
                            context=curve_context,
                            baseline_metrics=dict(active_metrics),
                            candidate_metrics=dict(fit_metrics["tail_blend"]),
                            decision=tail_decision,
                        ),
                    )
                    if tail_selected:
                        candidate_curves["tail_blend_selected"] = tail_curve
                        active_curve = tail_curve
                        active_metrics = fit_metrics["tail_blend"]

                floor_base_curve = active_curve
                floor_baseline_metrics = active_metrics
                if tail_selected and tail_curve is not None:
                    floor_base_curve = tail_curve
                    floor_baseline_metrics = fit_metrics.get(
                        "tail_blend", floor_baseline_metrics
                    )
                baseline_pre_merch = _max_pre_merchantable_volume(
                    x_curve=floor_base_curve[0],
                    y_curve=floor_base_curve[1],
                    floor_age=merchantable_floor_age,
                )
                if baseline_pre_merch > 1.0:
                    floor_kwargs = dict(active_kwargs)
                    if tail_selected:
                        floor_kwargs = _with_tail_defaults(floor_kwargs)
                        floor_kwargs["tail_blend_enabled"] = True
                    if not _toe_shift_active(floor_kwargs):
                        floor_kwargs["merchantable_floor_enabled"] = True
                        floor_kwargs["merchantable_floor_age"] = merchantable_floor_age
                        floor_kwargs["merchantable_floor_value"] = (
                            merchantable_floor_value
                        )
                        floor_curve = _run_candidate(
                            vdyp_out=vdyp_out,
                            curve_context=dict(
                                curve_context,
                                merchantable_floor_age=merchantable_floor_age,
                            ),
                            kwargs=floor_kwargs,
                            candidate_name="merchantable_floor",
                        )
                        if floor_curve is not None:
                            floor_metrics = _fit_quality(
                                binned=binned_obs,
                                x_curve=floor_curve[0],
                                y_curve=floor_curve[1],
                            )
                            fit_metrics["merchantable_floor"] = floor_metrics
                            floor_pre_merch = _max_pre_merchantable_volume(
                                x_curve=floor_curve[0],
                                y_curve=floor_curve[1],
                                floor_age=merchantable_floor_age,
                            )
                            baseline = floor_baseline_metrics
                            reduced_pre_merch = floor_pre_merch <= 0.5
                            acceptable_rmse = floor_metrics["rmse"] <= (
                                1.20 * baseline["rmse"]
                            )
                            accepted = reduced_pre_merch and acceptable_rmse
                            append_jsonl_fn(
                                vdyp_curve_events_path,
                                build_timestamped_event(
                                    event="vdyp_curve_fit",
                                    status="info",
                                    stage="merchantable_floor",
                                    reason=(
                                        "merchantable_floor_selected"
                                        if accepted
                                        else "merchantable_floor_rejected"
                                    ),
                                    context=curve_context,
                                    floor_age=float(merchantable_floor_age),
                                    baseline_pre_merch_volume=float(baseline_pre_merch),
                                    candidate_pre_merch_volume=float(floor_pre_merch),
                                    baseline_metrics=dict(baseline),
                                    candidate_metrics=dict(floor_metrics),
                                ),
                            )
                            if accepted:
                                candidate_curves["merchantable_floor"] = floor_curve

            gate_fail_reasons = _evaluate_fit_quality_gate(
                y_curve=y,
                metrics=fit_metrics.get("current"),
            )
            if gate_fail_reasons:
                message_fn(
                    "  fit-quality gate warning",
                    sc,
                    si_level,
                    ",".join(gate_fail_reasons),
                )
                append_jsonl_fn(
                    vdyp_curve_events_path,
                    build_timestamped_event(
                        event="vdyp_curve_fit",
                        status="warning",
                        stage="fit_quality_gate",
                        reason="fit_quality_gate_failed",
                        context=curve_context,
                        failure_reasons=gate_fail_reasons,
                        metrics=dict(fit_metrics.get("current", {})),
                    ),
                )

            output_x, output_y = x, y
            selected_path = "primary_nlls"
            selected_metrics = dict(fit_metrics.get("current", {}))
            auto_curve = candidate_curves.get("auto_skip")
            if auto_curve is not None:
                output_x, output_y = auto_curve
                selected_path = "reparameterized_nlls"
                selected_metrics = dict(fit_metrics.get("auto_skip", selected_metrics))
            left_toe_curve = candidate_curves.get("left_toe_censor")
            if left_toe_curve is not None:
                output_x, output_y = left_toe_curve
                selected_path = "censored_refit"
                selected_metrics = dict(
                    fit_metrics.get("left_toe_censor", selected_metrics)
                )
            tail_selected_curve = candidate_curves.get("tail_blend_selected")
            if tail_selected_curve is not None:
                output_x, output_y = tail_selected_curve
                selected_path = "tail_blend"
                selected_metrics = dict(fit_metrics.get("tail_blend", selected_metrics))
            floor_curve = candidate_curves.get("merchantable_floor")
            if floor_curve is not None:
                output_x, output_y = floor_curve
                selected_path = "merchantable_floor"
                selected_metrics = dict(
                    fit_metrics.get("merchantable_floor", selected_metrics)
                )
            # Preserve an escape hatch for the earlier K3Z tail-blend override,
            # but keep it disabled by default so K3Z follows the same candidate
            # selection policy as other cases unless explicitly requested.
            force_k3z_tail_blend = os.environ.get(
                "FEMIC_K3Z_FORCE_TAIL_BLEND", "0"
            ).strip().lower() in ("1", "true", "yes", "on")
            if force_k3z_tail_blend and str(tsa).strip().lower() == "k3z":
                tail_curve = candidate_curves.get("tail_blend")
                if tail_curve is not None:
                    output_x, output_y = tail_curve
                    selected_path = "tail_blend_override_k3z"
                    selected_metrics = dict(
                        fit_metrics.get("tail_blend", selected_metrics)
                    )

            # Guard against carrying forward obviously failed selected curves.
            selected_gate_fail_reasons = _evaluate_fit_quality_gate(
                y_curve=output_y,
                metrics=selected_metrics,
            )
            path_candidates: dict[
                str, tuple[tuple[Sequence[float], Sequence[float]], dict[str, float]]
            ] = {
                "primary_nlls": ((x, y), dict(fit_metrics.get("current", {}))),
            }
            auto_curve = candidate_curves.get("auto_skip")
            if auto_curve is not None:
                path_candidates["reparameterized_nlls"] = (
                    auto_curve,
                    dict(fit_metrics.get("auto_skip", {})),
                )
            left_toe_curve = candidate_curves.get("left_toe_censor")
            if left_toe_curve is not None:
                path_candidates["censored_refit"] = (
                    left_toe_curve,
                    dict(fit_metrics.get("left_toe_censor", {})),
                )
            tail_curve = candidate_curves.get("tail_blend")
            if tail_curve is not None:
                path_candidates["tail_blend"] = (
                    tail_curve,
                    dict(fit_metrics.get("tail_blend", {})),
                )
            floor_curve = candidate_curves.get("merchantable_floor")
            if floor_curve is not None:
                path_candidates["merchantable_floor"] = (
                    floor_curve,
                    dict(fit_metrics.get("merchantable_floor", {})),
                )

            if str(tsa).strip().lower() != "k3z" and selected_gate_fail_reasons:
                gate_by_path: dict[str, list[str]] = {}
                for path_name, (curve_xy, curve_metrics) in path_candidates.items():
                    gate_by_path[path_name] = _evaluate_fit_quality_gate(
                        y_curve=curve_xy[1],
                        metrics=curve_metrics,
                    )
                rescue_order = (
                    "tail_blend",
                    "merchantable_floor",
                    "reparameterized_nlls",
                    "censored_refit",
                    "primary_nlls",
                )
                rescue_path: str | None = None
                for path_name in rescue_order:
                    reasons = gate_by_path.get(path_name)
                    if reasons is not None and not reasons:
                        rescue_path = path_name
                        break

                if rescue_path is None:
                    rescue_path = min(
                        gate_by_path.keys(),
                        key=lambda path_name: (
                            len(gate_by_path[path_name]),
                            float(
                                path_candidates[path_name][1].get("rmse", float("inf"))
                            ),
                        ),
                    )
                if rescue_path != selected_path:
                    prior_selected_path = str(selected_path)
                    prior_selected_gate_fail_reasons = list(selected_gate_fail_reasons)
                    rescue_curve, rescue_metrics = path_candidates[rescue_path]
                    output_x, output_y = rescue_curve
                    selected_path = rescue_path
                    selected_metrics = dict(rescue_metrics)
                    selected_gate_fail_reasons = list(gate_by_path[rescue_path])
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_timestamped_event(
                            event="vdyp_curve_fit",
                            status="warning",
                            stage="fit_quality_gate",
                            reason="selected_curve_gate_rescue",
                            context=curve_context,
                            prior_selected_path=prior_selected_path,
                            rescue_selected_path=rescue_path,
                            rescue_gate_fail_reasons=selected_gate_fail_reasons,
                            rescue_trigger_gate_reasons=prior_selected_gate_fail_reasons,
                            rescue_order=list(rescue_order),
                            gate_by_path=gate_by_path,
                        ),
                    )
                elif selected_gate_fail_reasons:
                    append_jsonl_fn(
                        vdyp_curve_events_path,
                        build_timestamped_event(
                            event="vdyp_curve_fit",
                            status="warning",
                            stage="fit_quality_gate",
                            reason="selected_curve_gate_unresolved",
                            context=curve_context,
                            selected_path=selected_path,
                            selected_gate_fail_reasons=selected_gate_fail_reasons,
                            gate_by_path=gate_by_path,
                        ),
                    )
            append_jsonl_fn(
                vdyp_curve_events_path,
                build_timestamped_event(
                    event="vdyp_curve_fit",
                    status="info",
                    stage="fallback_policy",
                    reason="curve_selected",
                    context=curve_context,
                    selected_path=selected_path,
                    available_candidates=sorted(candidate_curves.keys()),
                    selected_metrics=selected_metrics,
                    selected_gate_fail_reasons=selected_gate_fail_reasons,
                ),
            )
            _emit_fit_diagnostic_plot(
                tsa_code=tsa,
                stratumi=int(stratumi),
                stratum_code=sc,
                si_level=si_level,
                vdyp_out=vdyp_out,
                binned=binned_obs,
                x_fit=x,
                y_fit=y,
                selected_x=output_x,
                selected_y=output_y,
                selected_path=selected_path,
                tail_blend_meta=tail_blend_meta_for_plot,
                candidate_curves=candidate_curves,
                fit_metrics=fit_metrics,
            )
            smoothed_runs.append(
                SmoothedCurveResult(
                    stratumi=int(stratumi),
                    stratum_code=sc,
                    si_level=si_level,
                    x=output_x,
                    y=output_y,
                    vdyp_out=vdyp_out,
                )
            )
    _emit_lmh_overlay_plot(tsa_code=tsa, runs=smoothed_runs)
    return smoothed_runs

