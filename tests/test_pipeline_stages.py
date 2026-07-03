from __future__ import annotations

from pathlib import Path
import sys

from femic.pipeline.io import build_legacy_execution_plan, build_pipeline_run_config
from femic.pipeline.legacy_runtime import (
    build_legacy_01a_runtime_config,
    build_legacy_01b_runtime_config,
)
from femic.pipeline.stages import (
    ParallelExecutionBackend,
    execute_legacy_tsa_stage,
    initialize_parallel_execution_backend,
    initialize_legacy_tsa_stage_state,
    load_legacy_module,
    prepare_tsa_index,
    run_legacy_subprocess,
    run_legacy_tsa_loop,
    should_skip_if_outputs_exist,
    stream_filtered_subprocess_output,
)
import pandas as pd
import pytest


def test_run_legacy_subprocess_filters_known_noise(capsys, tmp_path: Path) -> None:
    script_path = tmp_path / "00_data-prep.py"
    script_path.write_text(
        "print('hello')\n"
        "print('Error in sys.excepthook:')\n"
        "print('Original exception was:')\n"
        "print('done')\n",
        encoding="utf-8",
    )
    cfg = build_pipeline_run_config(tsa_list=["08"], resume=True)
    plan = build_legacy_execution_plan(
        run_config=cfg,
        script_path=script_path,
        python_executable=sys.executable,
        base_env={},
    )

    result = run_legacy_subprocess(
        execution_plan=plan,
        drop_lines={"Error in sys.excepthook:", "Original exception was:"},
    )

    out = capsys.readouterr().out
    assert result.exit_code == 0
    assert "hello" in out
    assert "done" in out
    assert "Error in sys.excepthook:" not in out
    assert "Original exception was:" not in out


def test_stream_filtered_subprocess_output_keeps_line_format() -> None:
    written: list[str] = []
    stream_filtered_subprocess_output(
        lines=["alpha\n", "Error in sys.excepthook:\n", "beta\n"],
        drop_lines={"Error in sys.excepthook:"},
        write_fn=written.append,
    )
    assert written == ["alpha\n", "beta\n"]


def test_run_legacy_subprocess_raises_when_stdout_pipe_missing(tmp_path: Path) -> None:
    script_path = tmp_path / "00_data-prep.py"
    script_path.write_text("print('hello')\n", encoding="utf-8")
    cfg = build_pipeline_run_config(tsa_list=["08"], resume=True)
    plan = build_legacy_execution_plan(
        run_config=cfg,
        script_path=script_path,
        python_executable=sys.executable,
        base_env={},
    )

    class _Proc:
        stdout = None

        @staticmethod
        def wait() -> int:
            return 0

    class _Subprocess:
        STDOUT = object()
        PIPE = object()

        @staticmethod
        def Popen(*_args: object, **_kwargs: object) -> _Proc:
            return _Proc()

    import femic.pipeline.stages as stages_module

    old_subprocess = stages_module.subprocess
    try:
        stages_module.subprocess = _Subprocess()  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="stdout pipe was not created"):
            run_legacy_subprocess(
                execution_plan=plan,
                drop_lines=set(),
            )
    finally:
        stages_module.subprocess = old_subprocess


def test_load_legacy_module_loads_run_tsa_symbol(tmp_path: Path) -> None:
    script_path = tmp_path / "legacy.py"
    script_path.write_text(
        "def run_tsa(*, tsa):\n    return f'ran {tsa}'\n",
        encoding="utf-8",
    )

    module = load_legacy_module(script_path=script_path, module_name="legacy_test")

    assert hasattr(module, "run_tsa")
    assert module.run_tsa(tsa="08") == "ran 08"


def test_execute_legacy_tsa_stage_loads_and_runs_with_skip(tmp_path: Path) -> None:
    script_path = tmp_path / "legacy_stage.py"
    script_path.write_text(
        "seen = []\ndef run_tsa(*, tsa, marker):\n    seen.append((tsa, marker))\n",
        encoding="utf-8",
    )
    module = execute_legacy_tsa_stage(
        script_path=script_path,
        module_name="legacy_stage_test",
        tsa_list=["08", "16", "24"],
        should_skip_fn=lambda tsa: tsa == "16",
        build_run_kwargs_fn=lambda tsa: {"tsa": tsa, "marker": "x"},
    )
    assert module.seen == [("08", "x"), ("24", "x")]


def test_execute_legacy_tsa_stage_raises_on_missing_run_symbol(tmp_path: Path) -> None:
    script_path = tmp_path / "legacy_stage_missing.py"
    script_path.write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not define callable"):
        execute_legacy_tsa_stage(
            script_path=script_path,
            module_name="legacy_stage_missing_test",
            tsa_list=["08"],
            should_skip_fn=lambda _tsa: False,
            build_run_kwargs_fn=lambda tsa: {"tsa": tsa},
        )


def test_run_legacy_tsa_loop_applies_skip_logic() -> None:
    seen: list[str] = []

    run_legacy_tsa_loop(
        tsa_list=["08", "16", "24"],
        should_skip_fn=lambda tsa: tsa == "16",
        run_one_fn=lambda tsa: seen.append(tsa),
    )

    assert seen == ["08", "24"]


def test_initialize_legacy_tsa_stage_state_returns_empty_maps() -> None:
    state = initialize_legacy_tsa_stage_state()

    assert state.vdyp_curves_smooth == {}
    assert state.vdyp_results == {}
    assert state.tipsy_params == {}
    assert state.tipsy_curves == {}
    assert state.scsi_au == {}
    assert state.au_scsi == {}
    assert state.results == {}


def test_prepare_tsa_index_sets_index_once() -> None:
    frame = pd.DataFrame({"tsa_code": ["08", "16"], "x": [1, 2]})

    indexed = prepare_tsa_index(f_table=frame, tsa_column="tsa_code")
    reindexed = prepare_tsa_index(f_table=indexed, tsa_column="tsa_code")

    assert indexed.index.name == "tsa_code"
    assert reindexed is indexed


def test_should_skip_if_outputs_exist(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    messages: list[str] = []

    should_skip = should_skip_if_outputs_exist(
        resume_effective=True,
        output_paths=[a, b],
        skip_message="skip",
        print_fn=messages.append,
    )

    assert should_skip is True
    assert messages == ["skip"]


def test_initialize_parallel_execution_backend_uses_serial_when_disabled() -> None:
    messages: list[str] = []
    backend = initialize_parallel_execution_backend(
        disable_ipp=True,
        ipp_module=object(),
        print_fn=messages.append,
    )
    assert isinstance(backend, ParallelExecutionBackend)
    assert backend.use_ipp is False
    assert "ipyparallel disabled" in messages[0]


def test_initialize_parallel_execution_backend_falls_back_on_runtime_error() -> None:
    messages: list[str] = []

    class _IPP:
        class Client:
            def __init__(self) -> None:
                raise RuntimeError("no controller")

    backend = initialize_parallel_execution_backend(
        disable_ipp=False,
        ipp_module=_IPP(),
        print_fn=messages.append,
    )
    assert backend.use_ipp is False
    assert "falling back to serial execution" in messages[0]


def test_initialize_parallel_execution_backend_uses_ipp_when_available() -> None:
    class _Client:
        def load_balanced_view(self) -> str:
            return "lbview"

    class _IPP:
        class Client:
            def __new__(cls) -> _Client:
                return _Client()

    backend = initialize_parallel_execution_backend(
        disable_ipp=False,
        ipp_module=_IPP(),
        print_fn=lambda *_args: None,
    )
    assert backend.use_ipp is True
    assert backend.lbview == "lbview"


def test_build_legacy_01a_runtime_config_builds_cache_paths() -> None:
    runtime_cfg = build_legacy_01a_runtime_config(
        tsa_code="08",
        resume_effective=True,
        force_run_vdyp=False,
        kwarg_overrides_for_tsa=None,
        vdyp_results_pickle_path="./data/vdyp_results.pkl",
        vdyp_input_pandl_path="./data/input.gdb",
        vdyp_ply_feather_path="./data/vdyp_ply.feather",
        vdyp_lyr_feather_path="./data/vdyp_lyr.feather",
        tipsy_params_columns=["a", "b"],
        tipsy_params_path_prefix="./data/tipsy_params_tsa",
        vdyp_results_tsa_pickle_path_prefix="./data/vdyp_results-tsa",
        vdyp_curves_smooth_tsa_feather_path_prefix="./data/vdyp_curves_smooth-tsa",
        parallel_worker_count=4,
    )

    assert runtime_cfg.vdyp_cache_paths["vdyp_results_tsa_pickle_path"] == Path(
        "./data/vdyp_results-tsa08.pkl"
    )
    assert runtime_cfg.vdyp_cache_paths["vdyp_curves_smooth_tsa_feather_path"] == Path(
        "./data/vdyp_curves_smooth-tsa08.feather"
    )
    assert runtime_cfg.parallel_worker_count == 4


def test_build_legacy_01b_runtime_config_builds_output_paths() -> None:
    runtime_cfg = build_legacy_01b_runtime_config(
        tipsy_params_path_prefix="./data/tipsy_params_tsa",
        tipsy_output_root="./data",
        tipsy_output_filename_template="04_output-tsa{tsa}.csv",
    )
    assert runtime_cfg.tipsy_params_path_prefix == "./data/tipsy_params_tsa"
    assert runtime_cfg.tipsy_output_root == "./data"
    assert runtime_cfg.tipsy_input_filename_template == "03_input-tsa{tsa}.csv"
    assert runtime_cfg.tipsy_output_filename_template == "04_output-tsa{tsa}.csv"
