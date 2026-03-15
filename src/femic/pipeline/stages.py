"""Pipeline stage executors used by workflow wrappers."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence

from femic.pipeline.io import LegacyExecutionPlan
from femic.pipeline.tsa import normalize_tsa_code


@dataclass(frozen=True)
class StageResult:
    """Result returned by a stage executor."""

    exit_code: int


@dataclass
class LegacyTSAStageState:
    """Mutable state maps shared across legacy TSA stages."""

    vdyp_curves_smooth: dict[str, Any]
    vdyp_results: dict[str, Any]
    tipsy_params: dict[str, Any]
    tipsy_curves: dict[str, Any]
    scsi_au: dict[str, Any]
    au_scsi: dict[str, Any]
    results: dict[str, Any]


@dataclass(frozen=True)
class ParallelExecutionBackend:
    """Parallel execution backend selection for legacy notebook-style loops."""

    use_ipp: bool
    rc: Any
    lbview: Any


class _SerialView:
    def map_async(
        self, func: Callable[..., Any], *iterables: Sequence[Any], ordered: bool = True
    ) -> list[Any]:
        return [func(*args) for args in zip(*iterables)]


class _SerialClient:
    def wait_interactive(self) -> None:
        return None

    def __len__(self) -> int:
        return 1


def initialize_legacy_tsa_stage_state() -> LegacyTSAStageState:
    """Create empty state payload used by legacy 01a/01b TSA stages."""
    return LegacyTSAStageState(
        vdyp_curves_smooth={},
        vdyp_results={},
        tipsy_params={},
        tipsy_curves={},
        scsi_au={},
        au_scsi={},
        results={},
    )


def _ipp_fallback_exception_types(ipp_module: Any) -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        OSError,
        RuntimeError,
        TimeoutError,
        ConnectionError,
    ]
    error_module = getattr(ipp_module, "error", None)
    timeout_type = getattr(error_module, "TimeoutError", None)
    if isinstance(timeout_type, type) and issubclass(timeout_type, BaseException):
        types.append(timeout_type)
    return tuple(types)


def initialize_parallel_execution_backend(
    *,
    disable_ipp: bool,
    ipp_module: Any,
    print_fn: Callable[..., Any] = print,
) -> ParallelExecutionBackend:
    """Initialize ipyparallel backend or fall back to serial execution."""
    if disable_ipp:
        print_fn("ipyparallel disabled (FEMIC_DISABLE_IPP=1); using serial execution")
        return ParallelExecutionBackend(
            use_ipp=False,
            rc=_SerialClient(),
            lbview=_SerialView(),
        )

    try:
        rc = ipp_module.Client()
        lbview = rc.load_balanced_view()
        return ParallelExecutionBackend(use_ipp=True, rc=rc, lbview=lbview)
    except _ipp_fallback_exception_types(ipp_module) as exc:
        print_fn(f"ipyparallel not available, falling back to serial execution: {exc}")
        return ParallelExecutionBackend(
            use_ipp=False,
            rc=_SerialClient(),
            lbview=_SerialView(),
        )


def prepare_tsa_index(
    *,
    f_table: Any,
    tsa_column: str = "tsa_code",
) -> Any:
    """Ensure legacy table uses TSA code as index for downstream stage lookups."""
    index = getattr(f_table, "index", None)
    if index is not None and index.name == tsa_column:
        normalized_index = index.map(normalize_tsa_code)
        if list(normalized_index) == list(index):
            return f_table
        table = f_table.copy()
        table.index = normalized_index
        return table
    table = f_table.copy()
    if tsa_column in getattr(table, "columns", []):
        table[tsa_column] = table[tsa_column].map(normalize_tsa_code)
    table = table.set_index(tsa_column)
    table.index = table.index.map(normalize_tsa_code)
    return table


def should_skip_if_outputs_exist(
    *,
    resume_effective: bool,
    output_paths: Sequence[str | Path],
    skip_message: str,
    print_fn: Callable[[str], Any] = print,
) -> bool:
    """Return True when resume mode is on and all required outputs already exist."""
    if not resume_effective:
        return False
    if not all(Path(path).is_file() for path in output_paths):
        return False
    print_fn(skip_message)
    return True


def load_legacy_module(
    *,
    script_path: str | Path,
    module_name: str,
) -> ModuleType:
    """Load a Python module from a legacy script path."""
    resolved_path = Path(script_path)
    spec = importlib.util.spec_from_file_location(module_name, resolved_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {resolved_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_legacy_tsa_loop(
    *,
    tsa_list: Sequence[str],
    should_skip_fn: Callable[[str], bool],
    run_one_fn: Callable[[str], Any],
) -> None:
    """Run one legacy stage per TSA with caller-provided skip logic."""
    for tsa in tsa_list:
        if should_skip_fn(tsa):
            continue
        run_one_fn(tsa)


def execute_legacy_tsa_stage(
    *,
    script_path: str | Path,
    module_name: str,
    tsa_list: Sequence[str],
    should_skip_fn: Callable[[str], bool],
    build_run_kwargs_fn: Callable[[str], Mapping[str, Any]],
    run_symbol: str = "run_tsa",
    load_module_fn: Callable[..., ModuleType] = load_legacy_module,
    run_loop_fn: Callable[..., None] = run_legacy_tsa_loop,
) -> ModuleType:
    """Load one legacy TSA stage module and execute its `run_tsa` loop."""
    module = load_module_fn(script_path=script_path, module_name=module_name)
    run_callable = getattr(module, run_symbol, None)
    if not callable(run_callable):
        raise RuntimeError(
            f"Legacy module {module_name!r} does not define callable {run_symbol!r}"
        )

    def _run_one(tsa: str) -> None:
        run_callable(**dict(build_run_kwargs_fn(tsa)))

    run_loop_fn(
        tsa_list=tsa_list,
        should_skip_fn=should_skip_fn,
        run_one_fn=_run_one,
    )
    return module


def run_legacy_subprocess(
    *,
    execution_plan: LegacyExecutionPlan,
    drop_lines: set[str],
) -> StageResult:
    """Execute legacy script and stream output while filtering known noisy lines."""
    env = dict(execution_plan.env)
    env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        execution_plan.cmd,
        cwd=str(execution_plan.working_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout is None:
        raise RuntimeError("Legacy subprocess stdout pipe was not created")
    stream_filtered_subprocess_output(
        lines=process.stdout,
        drop_lines=drop_lines,
        write_fn=sys.stdout.write,
    )
    return StageResult(exit_code=process.wait())


def stream_filtered_subprocess_output(
    *,
    lines: Iterable[str],
    drop_lines: set[str],
    write_fn: Callable[[str], Any],
) -> None:
    """Forward subprocess output lines, omitting exact known-noise line matches."""
    for line in lines:
        if line.strip() in drop_lines:
            continue
        write_fn(line)
