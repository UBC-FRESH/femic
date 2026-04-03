from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

import pandas as pd
import pytest
import numpy as np
import femic.pipeline.vdyp_stage as vdyp_stage

from femic.pipeline.vdyp_stage import (
    CurveSmoothingPlotConfig,
    StratumFitRunConfig,
    SmoothedCurveResult,
    build_bootstrap_vdyp_results_runner,
    build_vdyp_batch_command,
    emit_vdyp_run_event,
    build_vdyp_run_event,
    normalize_vdyp_run_event_counts,
    build_vdyp_run_context,
    build_curve_fit_adapter,
    build_curve_smoothing_plot_config,
    build_stratum_fit_run_config,
    build_fit_stratum_curves_runner,
    build_run_vdyp_for_stratum_runner,
    build_smoothed_curve_table,
    compile_strata_fit_results,
    execute_bootstrap_vdyp_runs,
    execute_curve_smoothing_runs,
    execute_vdyp_batch,
    collect_vdyp_batch_run_metadata,
    ensure_local_vdyp_runtime_assets,
    fit_stratum_curves,
    load_vdyp_input_tables,
    load_or_build_vdyp_results_tsa,
    plot_curve_overlays,
    resolve_vdyp_batch_execution_dependencies,
    resolve_vdyp_batch_temp_artifacts,
    run_vdyp_for_stratum,
    run_vdyp_sampling,
)


@dataclass
class _RunResult:
    stdout: str
    stderr: str
    returncode: int = 0


def _sample_vdyp_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    vdyp_ply = pd.DataFrame({"FEATURE_ID": [1, 2, 3], "A": [10, 20, 30]})
    vdyp_lyr = pd.DataFrame({"FEATURE_ID": [1, 2, 3], "B": [100, 200, 300]})
    return vdyp_ply, vdyp_lyr


def test_build_vdyp_run_context_sets_expected_defaults() -> None:
    context = build_vdyp_run_context(
        base_context={"seed": 1},
        tsa="08",
        run_id="run-1",
        vdyp_stdout_log_path=Path("logs/stdout.log"),
        vdyp_stderr_log_path=Path("logs/stderr.log"),
        vdyp_binpath=Path("VDYP7/VDYP7/VDYP7Console.exe"),
        vdyp_params=Path("vdyp_params-landp"),
    )
    assert context == {
        "seed": 1,
        "tsa": "08",
        "run_id": "run-1",
        "vdyp_stdout_log": "logs/stdout.log",
        "vdyp_stderr_log": "logs/stderr.log",
        "vdyp_binpath": "VDYP7/VDYP7/VDYP7Console.exe",
        "vdyp_params": "vdyp_params-landp",
    }


def test_build_vdyp_run_context_preserves_existing_values() -> None:
    context = build_vdyp_run_context(
        base_context={
            "run_id": "existing",
            "vdyp_stdout_log": "existing-stdout",
            "vdyp_binpath": "existing-bin",
        },
        run_id="run-1",
        vdyp_stdout_log_path=Path("logs/stdout.log"),
        vdyp_binpath=Path("VDYP7/VDYP7/VDYP7Console.exe"),
    )
    assert context["run_id"] == "existing"
    assert context["vdyp_stdout_log"] == "existing-stdout"
    assert context["vdyp_binpath"] == "existing-bin"


def test_build_vdyp_run_event_builds_shared_payload() -> None:
    counts = normalize_vdyp_run_event_counts(
        feature_count=2.0,
        cache_hits=1.0,
        ply_rows=3.0,
        lyr_rows=4.0,
    )
    payload = build_vdyp_run_event(
        status="ok",
        phase="initial",
        counts=counts,
        cmd="wine VDYP7Console.exe",
        context={"tsa": "08"},
        returncode=0,
    )
    assert payload["event"] == "vdyp_run"
    assert payload["status"] == "ok"
    assert payload["phase"] == "initial"
    assert payload["feature_count"] == 2
    assert payload["cache_hits"] == 1
    assert payload["ply_rows"] == 3
    assert payload["lyr_rows"] == 4
    assert payload["cmd"] == "wine VDYP7Console.exe"
    assert payload["returncode"] == 0
    assert payload["context"] == {"tsa": "08"}


def test_emit_vdyp_run_event_appends_payload() -> None:
    counts = normalize_vdyp_run_event_counts(
        feature_count=2,
        cache_hits=1,
        ply_rows=3,
        lyr_rows=4,
    )
    captured: list[tuple[str | Path, object]] = []
    emit_vdyp_run_event(
        append_jsonl_fn=lambda path, payload: captured.append((path, payload)),
        vdyp_log_path="vdyp_runs.jsonl",
        status="ok",
        phase="initial",
        counts=counts,
        cmd="wine VDYP7Console.exe",
        context={"tsa": "08"},
        returncode=0,
    )
    assert len(captured) == 1
    assert captured[0][0] == "vdyp_runs.jsonl"
    payload = captured[0][1]
    assert isinstance(payload, dict)
    assert payload["event"] == "vdyp_run"
    assert payload["status"] == "ok"
    assert payload["feature_count"] == 2


def test_normalize_vdyp_run_event_counts_coerces_to_ints() -> None:
    counts = normalize_vdyp_run_event_counts(
        feature_count=2.9,
        cache_hits=1.2,
        ply_rows=3.0,
        lyr_rows=4.7,
    )
    assert counts.feature_count == 2
    assert counts.cache_hits == 1
    assert counts.ply_rows == 3
    assert counts.lyr_rows == 4


def test_resolve_vdyp_batch_execution_dependencies_keeps_injected_callables() -> None:
    def _write(*_args: object, **_kwargs: object) -> None:
        return None

    def _import(_path: str) -> dict[str, object]:
        return {}

    def _append_jsonl(_path: str | Path, _payload: object) -> None:
        return None

    def _append_text(_path: str | Path, _text: str) -> None:
        return None

    def _header(**_kwargs: object) -> str:
        return "h"

    def _block(**_kwargs: object) -> str:
        return "b"

    def _run(*_args: object, **_kwargs: object) -> _RunResult:
        return _RunResult(stdout="", stderr="")

    deps = resolve_vdyp_batch_execution_dependencies(
        write_vdyp_infiles=_write,
        import_vdyp_tables_fn=_import,
        append_jsonl_fn=_append_jsonl,
        append_text_fn=_append_text,
        build_stream_header_fn=_header,
        build_stream_log_block_fn=_block,
        subprocess_run=_run,
    )

    assert deps.write_vdyp_infiles is _write
    assert deps.import_vdyp_tables is _import
    assert deps.append_jsonl is _append_jsonl
    assert deps.append_text is _append_text
    assert deps.build_stream_header is _header
    assert deps.build_stream_log_block is _block
    assert deps.subprocess_run is _run


def test_build_vdyp_batch_command_preserves_legacy_string_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vdyp_stage.os, "name", "posix", raising=False)
    cmd = build_vdyp_batch_command(
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="vdyp_params-landp",
        vdyp_io_dir=Path("tmp/vdyp_io"),
        vdyp_ply_csv="vdyp_ply_123.csv",
        vdyp_lyr_csv="vdyp_lyr_123.csv",
        vdyp_out_txt="vdyp_out_123.out",
        vdyp_err_txt="vdyp_err_123.err",
    )
    assert cmd == (
        "wine VDYP7/VDYP7/VDYP7Console.exe -p vdyp_params-landp "
        "-ip ./tmp/vdyp_io/vdyp_ply_123.csv "
        "-il ./tmp/vdyp_io/vdyp_lyr_123.csv "
        "-o ./tmp/vdyp_io/vdyp_out_123.out "
        "-e ./tmp/vdyp_io/vdyp_err_123.err"
    )


def test_build_vdyp_batch_command_windows_uses_native_cfg_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vdyp_stage.os, "name", "nt", raising=False)

    cmd = build_vdyp_batch_command(
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="C:\\repo\\vdyp_params-landp",
        vdyp_io_dir=Path("tmp/vdyp_io"),
        vdyp_ply_csv="vdyp_ply_123.csv",
        vdyp_lyr_csv="vdyp_lyr_123.csv",
        vdyp_out_txt="vdyp_out_123.out",
        vdyp_err_txt="vdyp_err_123.err",
        vdyp_cfg_dir="C:\\repo\\vdyp_io\\VDYP_CFG",
    )

    assert not cmd.startswith("wine ")
    assert "VDYP7/VDYP7/VDYP7Console.exe -p C:\\repo\\vdyp_params-landp" in cmd
    assert "-c C:\\repo\\vdyp_io\\VDYP_CFG\\" in cmd
    assert "-ip ./tmp/vdyp_io/vdyp_ply_123.csv" in cmd


def test_build_vdyp_batch_command_windows_uses_env_cfg_dir_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vdyp_stage.os, "name", "nt", raising=False)
    monkeypatch.setenv("FEMIC_VDYP_CFG_DIR", "C:\\repo\\vdyp_io\\VDYP_CFG")

    cmd = build_vdyp_batch_command(
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="vdyp_params-landp",
        vdyp_io_dir=Path("tmp/vdyp_io"),
        vdyp_ply_csv="vdyp_ply_123.csv",
        vdyp_lyr_csv="vdyp_lyr_123.csv",
        vdyp_out_txt="vdyp_out_123.out",
        vdyp_err_txt="vdyp_err_123.err",
    )
    assert "-c C:\\repo\\vdyp_io\\VDYP_CFG\\" in cmd


def test_ensure_local_vdyp_runtime_assets_stages_cfg_and_ini(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    source_cfg = source_root / "vdyp_io" / "VDYP_CFG"
    source_cfg.mkdir(parents=True)
    (source_cfg / "VDYP.CTR").write_text("cfg", encoding="utf-8")
    (source_root / "vdyp_io" / "Vdyp.ini").write_text("ini", encoding="utf-8")

    local_vdyp_io = tmp_path / "instance" / "vdyp_io"
    ensure_local_vdyp_runtime_assets(
        vdyp_io_dir=local_vdyp_io,
        source_root=source_root,
    )

    assert (local_vdyp_io / "VDYP_CFG" / "VDYP.CTR").read_text(
        encoding="utf-8"
    ) == "cfg"
    assert (local_vdyp_io / "VDYP.INI").read_text(encoding="utf-8") == "ini"


def test_build_vdyp_batch_command_posix_uses_cfg_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vdyp_stage.os, "name", "posix", raising=False)
    cmd = build_vdyp_batch_command(
        vdyp_binpath="/repo/VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="/repo/vdyp_params-landp",
        vdyp_io_dir=Path("tmp/vdyp_io"),
        vdyp_ply_csv="vdyp_ply_123.csv",
        vdyp_lyr_csv="vdyp_lyr_123.csv",
        vdyp_out_txt="vdyp_out_123.out",
        vdyp_err_txt="vdyp_err_123.err",
        vdyp_cfg_dir="/repo/VDYP7/VDYP7/VDYP_CFG",
    )
    assert cmd.startswith("wine ")
    assert "-c /repo/VDYP7/VDYP7/VDYP_CFG/" in cmd


def test_collect_vdyp_batch_run_metadata_captures_expected_fields(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "out.out"
    err_path = tmp_path / "err.err"
    out_path.write_text("out-data", encoding="utf-8")
    err_path.write_text("err-data", encoding="utf-8")

    metadata = collect_vdyp_batch_run_metadata(
        result=_RunResult(stdout="stdout-data", stderr="stderr-data", returncode=3),
        out_path=out_path,
        err_path=err_path,
        run_started=10.0,
        time_fn=lambda: 11.2345,
    )

    assert metadata == {
        "returncode": 3,
        "duration_sec": 1.235,
        "out_size": 8,
        "err_size": 8,
        "err_head": "err-data",
        "proc_stdout_head": "stdout-data",
        "proc_stderr_head": "stderr-data",
    }


def test_collect_vdyp_batch_run_metadata_accepts_string_paths(tmp_path: Path) -> None:
    out_path = tmp_path / "out.out"
    err_path = tmp_path / "err.err"
    out_path.write_text("o", encoding="utf-8")
    err_path.write_text("e", encoding="utf-8")
    metadata = collect_vdyp_batch_run_metadata(
        result=_RunResult(stdout="", stderr="", returncode=0),
        out_path=str(out_path),
        err_path=str(err_path),
        run_started=10.0,
        time_fn=lambda: 10.0,
    )
    assert metadata["out_size"] == 1
    assert metadata["err_size"] == 1


def test_resolve_vdyp_batch_temp_artifacts_returns_names_and_paths() -> None:
    artifacts = resolve_vdyp_batch_temp_artifacts(
        vdyp_ply_name="/tmp/vdyp_ply_123.csv",
        vdyp_lyr_name="/tmp/vdyp_lyr_123.csv",
        vdyp_out_name="/tmp/vdyp_out_123.out",
        vdyp_err_name="/tmp/vdyp_err_123.err",
    )
    assert artifacts.vdyp_ply_csv == "vdyp_ply_123.csv"
    assert artifacts.vdyp_lyr_csv == "vdyp_lyr_123.csv"
    assert artifacts.vdyp_out_txt == "vdyp_out_123.out"
    assert artifacts.vdyp_err_txt == "vdyp_err_123.err"
    assert artifacts.out_path == Path("/tmp/vdyp_out_123.out")
    assert artifacts.err_path == Path("/tmp/vdyp_err_123.err")


def test_build_curve_fit_adapter_converts_maxfev_to_max_nfev() -> None:
    captured: dict[str, object] = {}

    def fake_curve_fit(*_args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return "ok"

    class _FakeNumpy:
        @staticmethod
        def any(value: object) -> bool:
            if isinstance(value, (list, tuple)):
                return any(bool(v) for v in value)
            return bool(value)

        @staticmethod
        def isfinite(bounds: object) -> object:
            return bounds

    wrapped = build_curve_fit_adapter(
        curve_fit_impl=fake_curve_fit,
        np_module=_FakeNumpy(),
    )
    result = wrapped(bounds=(0.0, 1.0), maxfev=123)

    assert result == "ok"
    assert captured["max_nfev"] == 123
    assert "maxfev" not in captured


def test_build_curve_fit_adapter_keeps_existing_max_nfev() -> None:
    captured: dict[str, object] = {}

    def fake_curve_fit(*_args: object, **kwargs: object) -> str:
        captured.update(kwargs)
        return "ok"

    class _FakeNumpy:
        @staticmethod
        def any(value: object) -> bool:
            if isinstance(value, (list, tuple)):
                return any(bool(v) for v in value)
            return bool(value)

        @staticmethod
        def isfinite(bounds: object) -> object:
            return bounds

    wrapped = build_curve_fit_adapter(
        curve_fit_impl=fake_curve_fit,
        np_module=_FakeNumpy(),
    )
    wrapped(bounds=(0.0, 1.0), maxfev=111, max_nfev=222)

    assert captured["max_nfev"] == 222
    assert captured["maxfev"] == 111


def test_fit_stratum_curves_returns_species_fit_payload() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["S1", "S1", "S1"],
            "SITE_INDEX": [20.0, 22.0, 24.0],
            "PROJ_AGE_1": [40, 60, 80],
            "LIVE_STAND_VOLUME_125": [100.0, 100.0, 100.0],
            "live_vol_per_ha_125_SW": [50.0, 60.0, 70.0],
            "PROJ_HEIGHT_1": [15.0, 20.0, 25.0],
        }
    ).set_index("stratum")
    stratum_si_stats = f_table.groupby(level="stratum").SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    class _FakeSns:
        @staticmethod
        def color_palette(_name: str, n: int) -> list[str]:
            return ["#111"] * n

        @staticmethod
        def set_palette(_palette: object) -> None:
            return None

        @staticmethod
        def lineplot(*_args: object, **_kwargs: object) -> None:
            return None

    class _FakePlt:
        @staticmethod
        def subplots(*_args: object, **_kwargs: object) -> tuple[None, list[None]]:
            return None, [None, None, None, None]

    def fake_curve_fit(
        *_args: object, **_kwargs: object
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.array([1.0, 2.0, 3.0, 4.0]), np.eye(4)

    out = fit_stratum_curves(
        f_table=f_table,
        fit_func=lambda x, a, b, c, s: s * (a * ((x - c) ** b)) * np.exp(-a * (x - c)),
        fit_func_bounds_func=lambda _x: ([0, 0, 0, 0], [1, 50, 100, 10]),
        strata_df=pd.DataFrame({"totalarea_p": [1.0]}, index=["S1"]),
        stratum_si_stats=stratum_si_stats,
        stratumi=0,
        species_list=["SW"],
        curve_fit_fn=fake_curve_fit,
        np_module=np,
        pd_module=pd,
        sns_module=_FakeSns(),
        plt_module=_FakePlt(),
        si_levelquants={"M": [0, 50, 100]},
        plot=False,
    )

    assert set(out) == {"M"}
    assert out["M"]["species"]["SW"]["pct"] == 100
    assert out["M"]["species"]["SW"]["age"] == 40
    assert out["M"]["species"]["SW"]["height"] == 15.0
    assert out["M"]["species"]["SW"]["si"] == 22.0


def test_fit_stratum_curves_skips_species_on_curve_fit_error() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["S1", "S1"],
            "SITE_INDEX": [20.0, 22.0],
            "PROJ_AGE_1": [40, 60],
            "LIVE_STAND_VOLUME_125": [100.0, 100.0],
            "live_vol_per_ha_125_SW": [50.0, 60.0],
            "PROJ_HEIGHT_1": [15.0, 20.0],
        }
    ).set_index("stratum")
    stratum_si_stats = f_table.groupby(level="stratum").SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    class _FakeSns:
        @staticmethod
        def color_palette(_name: str, n: int) -> list[str]:
            return ["#111"] * n

    class _FakePlt:
        pass

    messages: list[tuple[object, ...]] = []

    out = fit_stratum_curves(
        f_table=f_table,
        fit_func=lambda x, a, b, c, s: s * (a * ((x - c) ** b)) * np.exp(-a * (x - c)),
        fit_func_bounds_func=lambda _x: ([0, 0, 0, 0], [1, 50, 100, 10]),
        strata_df=pd.DataFrame({"totalarea_p": [1.0]}, index=["S1"]),
        stratum_si_stats=stratum_si_stats,
        stratumi=0,
        species_list=["SW"],
        curve_fit_fn=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("fit boom")),
        np_module=np,
        pd_module=pd,
        sns_module=_FakeSns(),
        plt_module=_FakePlt(),
        si_levelquants={"M": [0, 50, 100]},
        plot=False,
        message_fn=lambda *args: messages.append(args),
    )

    assert out["M"]["species"] == {}
    assert any(msg and msg[0] == "fit error" for msg in messages)


def test_fit_stratum_curves_collapses_sparse_si_bins_before_fit() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["S1"] * 7,
            "SITE_INDEX": [10.0, 20.0, 22.0, 24.0, 30.0, 32.0, 34.0],
            "PROJ_AGE_1": [40, 45, 50, 55, 60, 65, 70],
            "LIVE_STAND_VOLUME_125": [100.0] * 7,
            "live_vol_per_ha_125_SW": [40.0, 45.0, 50.0, 55.0, 65.0, 70.0, 75.0],
            "PROJ_HEIGHT_1": [14.0, 15.0, 16.0, 17.0, 19.0, 20.0, 21.0],
        }
    ).set_index("stratum")
    stratum_si_stats = f_table.groupby(level="stratum").SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    class _FakeSns:
        @staticmethod
        def color_palette(_name: str, n: int) -> list[str]:
            return ["#111"] * n

        @staticmethod
        def set_palette(_palette: object) -> None:
            return None

        @staticmethod
        def lineplot(*_args: object, **_kwargs: object) -> None:
            return None

    class _FakePlt:
        @staticmethod
        def subplots(*_args: object, **_kwargs: object) -> tuple[None, list[None]]:
            return None, [None, None, None, None]

    def fake_curve_fit(
        *_args: object, **_kwargs: object
    ) -> tuple[np.ndarray, np.ndarray]:
        return np.array([1.0, 2.0, 3.0, 4.0]), np.eye(4)

    out = fit_stratum_curves(
        f_table=f_table,
        fit_func=lambda x, a, b, c, s: s * (a * ((x - c) ** b)) * np.exp(-a * (x - c)),
        fit_func_bounds_func=lambda _x: ([0, 0, 0, 0], [1, 50, 100, 10]),
        strata_df=pd.DataFrame({"totalarea_p": [1.0]}, index=["S1"]),
        stratum_si_stats=stratum_si_stats,
        stratumi=0,
        species_list=["SW"],
        curve_fit_fn=fake_curve_fit,
        np_module=np,
        pd_module=pd,
        sns_module=_FakeSns(),
        plt_module=_FakePlt(),
        si_levelquants={"L": [5, 20, 35], "M": [35, 50, 65], "H": [65, 80, 95]},
        min_stands_per_si_bin=3,
        plot=False,
    )

    assert out["M"]["collapsed_to"] != "M"
    assert out["H"]["collapsed_to"] != "H"
    assert out["M"]["si_group_stand_count"] >= 3


def test_fit_stratum_curves_skips_empty_aggregates_when_not_fit_rawdata() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["S1", "S1"],
            "SITE_INDEX": [20.0, 22.0],
            "PROJ_AGE_1": [40, 60],
            "LIVE_STAND_VOLUME_125": [100.0, 100.0],
            "live_vol_per_ha_125_SW": [50.0, 60.0],
            "PROJ_HEIGHT_1": [15.0, 20.0],
        }
    ).set_index("stratum")
    stratum_si_stats = f_table.groupby(level="stratum").SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    class _FakeSns:
        @staticmethod
        def color_palette(_name: str, n: int) -> list[str]:
            return ["#111"] * n

    class _FakePlt:
        pass

    out = fit_stratum_curves(
        f_table=f_table,
        fit_func=lambda x, a, b, c, s: s * (a * ((x - c) ** b)) * np.exp(-a * (x - c)),
        fit_func_bounds_func=lambda _x: ([0, 0, 0, 0], [1, 50, 100, 10]),
        strata_df=pd.DataFrame({"totalarea_p": [1.0]}, index=["S1"]),
        stratum_si_stats=stratum_si_stats,
        stratumi=0,
        species_list=["SW"],
        curve_fit_fn=lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("fit boom")),
        np_module=np,
        pd_module=pd,
        sns_module=_FakeSns(),
        plt_module=_FakePlt(),
        si_levelquants={"M": [0, 50, 100]},
        plot=False,
        fit_rawdata=False,
    )

    assert out["M"]["species"] == {}


def test_fit_stratum_curves_unexpected_curve_fit_error_propagates() -> None:
    f_table = pd.DataFrame(
        {
            "stratum": ["S1", "S1", "S1", "S1"],
            "SITE_INDEX": [20.0, 22.0, 24.0, 26.0],
            "PROJ_AGE_1": [40, 50, 60, 70],
            "LIVE_STAND_VOLUME_125": [100.0, 100.0, 100.0, 100.0],
            "live_vol_per_ha_125_SW": [40.0, 60.0, 70.0, 80.0],
            "PROJ_HEIGHT_1": [15.0, 18.0, 20.0, 23.0],
        }
    ).set_index("stratum")
    stratum_si_stats = f_table.groupby(level="stratum").SITE_INDEX.describe(
        percentiles=[0, 0.05, 0.20, 0.35, 0.5, 0.65, 0.80, 0.95, 1]
    )

    class _FakeSns:
        @staticmethod
        def color_palette(_name: str, n: int) -> list[str]:
            return ["#111"] * n

    class _FakePlt:
        pass

    with pytest.raises(ZeroDivisionError):
        fit_stratum_curves(
            f_table=f_table,
            fit_func=lambda x, a, b, c, s: (
                s * (a * ((x - c) ** b)) * np.exp(-a * (x - c))
            ),
            fit_func_bounds_func=lambda _x: ([0, 0, 0, 0], [1, 50, 100, 10]),
            strata_df=pd.DataFrame({"totalarea_p": [1.0]}, index=["S1"]),
            stratum_si_stats=stratum_si_stats,
            stratumi=0,
            species_list=["SW"],
            curve_fit_fn=lambda *_a, **_k: (_ for _ in ()).throw(
                ZeroDivisionError("unexpected")
            ),
            np_module=np,
            pd_module=pd,
            sns_module=_FakeSns(),
            plt_module=_FakePlt(),
            si_levelquants={"M": [0, 50, 100]},
            plot=False,
        )


def test_build_fit_stratum_curves_runner_binds_fit_context() -> None:
    captured: dict[str, object] = {}

    def fake_fit_stratum_curves(**kwargs: object) -> dict[str, str]:
        captured.update(kwargs)
        return {"status": "ok"}

    compile_one = build_fit_stratum_curves_runner(
        f_table="f_table",
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        strata_df="strata_df",
        stratum_si_stats="si_stats",
        species_list=["SW", "FD"],
        curve_fit_fn=lambda *_a, **_k: None,
        np_module="np",
        pd_module="pd",
        sns_module="sns",
        plt_module="plt",
        fit_rawdata=True,
        min_stands_per_si_bin=11,
        min_age=25,
        agg_type="min",
        plot=False,
        figsize=(8, 6),
        verbose=True,
        ylim=[0.0, 600.0],
        xlim=[0.0, 400.0],
        message_fn=lambda *_a, **_k: None,
        fit_stratum_curves_fn=fake_fit_stratum_curves,
    )

    out = compile_one(7, "S7")

    assert out == {"status": "ok"}
    assert captured["stratumi"] == 7
    assert captured["f_table"] == "f_table"
    assert captured["strata_df"] == "strata_df"
    assert captured["stratum_si_stats"] == "si_stats"
    assert captured["species_list"] == ["SW", "FD"]
    assert captured["fit_rawdata"] is True
    assert captured["min_stands_per_si_bin"] == 11
    assert captured["min_age"] == 25
    assert captured["agg_type"] == "min"
    assert captured["plot"] is False
    assert captured["figsize"] == (8, 6)
    assert captured["verbose"] is True
    assert captured["ylim"] == [0.0, 600.0]
    assert captured["xlim"] == [0.0, 400.0]


def test_compile_strata_fit_results_calls_compile_fn_for_each_stratum() -> None:
    strata_df = pd.DataFrame({"totalarea_p": [0.6, 0.4]}, index=["S1", "S2"])
    seen: list[tuple[int, str]] = []
    messages: list[tuple[object, ...]] = []

    def compile_one(stratumi: int, sc: str) -> dict[str, object]:
        seen.append((stratumi, sc))
        return {"sc": sc}

    out = compile_strata_fit_results(
        strata_df=strata_df,
        compile_one_fn=compile_one,
        message_fn=lambda *args: messages.append(args),
    )

    assert seen == [(0, "S1"), (1, "S2")]
    assert out == [[0, "S1", {"sc": "S1"}], [1, "S2", {"sc": "S2"}]]
    assert messages == [("compiling stratum S1",), ("compiling stratum S2",)]


def test_run_vdyp_sampling_auto_small_sample_runs_all_records() -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [101, 102]})
    calls: list[tuple[list[int], dict[str, object]]] = []
    cache: dict[int, dict[str, object]] = {}

    def run_batch_fn(
        feature_ids: object, **kwargs: object
    ) -> dict[int, dict[str, object]]:
        feature_ids_list = [int(fid) for fid in feature_ids]
        calls.append((feature_ids_list, dict(kwargs)))
        return {fid: {"ok": True} for fid in feature_ids_list}

    out = run_vdyp_sampling(
        sample_table=sample_table,
        nsamples="auto",
        min_samples=3,
        max_samples=10,
        nsamples_c1=0.1,
        nsamples_c2=0.1,
        confidence=95,
        half_rel_ci=0.05,
        ipp_mode=None,
        vdyp_timeout=2.0,
        rc_len=1,
        verbose=False,
        vdyp_out_cache=cache,
        random_seed=None,
        run_batch_fn=run_batch_fn,
        nsamples_from_curves_fn=lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("nsamples_from_curves should not be called")
        ),
    )

    assert calls == [([101, 102], {"phase": "auto_small_sample"})]
    assert set(out) == {101, 102}
    assert set(cache) == {101, 102}


def test_run_vdyp_sampling_auto_runs_gap_fill_phase() -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1, 2, 3, 4]})
    phases: list[str] = []

    def run_batch_fn(
        feature_ids: object, **kwargs: object
    ) -> dict[int, dict[str, object]]:
        phases.append(str(kwargs["phase"]))
        return {int(fid): {"ok": True} for fid in feature_ids}

    out = run_vdyp_sampling(
        sample_table=sample_table,
        nsamples="auto",
        min_samples=1,
        max_samples=10,
        nsamples_c1=0.1,
        nsamples_c2=1.0,
        confidence=95,
        half_rel_ci=0.05,
        ipp_mode=None,
        vdyp_timeout=2.0,
        rc_len=1,
        verbose=False,
        vdyp_out_cache=None,
        random_seed=None,
        run_batch_fn=run_batch_fn,
        nsamples_from_curves_fn=lambda _vdyp_out, **_kwargs: (4, None),
    )

    assert "initial" in phases
    assert "gap_fill" in phases
    assert len(out) >= 3


def test_run_vdyp_sampling_rejects_bad_nsamples_value() -> None:
    with pytest.raises(ValueError, match="Unsupported nsamples mode"):
        run_vdyp_sampling(
            sample_table=pd.DataFrame({"FEATURE_ID": [1, 2]}),
            nsamples="bad-mode",
            min_samples=2,
            max_samples=10,
            nsamples_c1=0.1,
            nsamples_c2=0.1,
            confidence=95,
            half_rel_ci=0.05,
            ipp_mode=None,
            vdyp_timeout=2.0,
            rc_len=1,
            verbose=False,
            vdyp_out_cache=None,
            random_seed=None,
            run_batch_fn=lambda *_a, **_k: {},
            nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
        )


def test_run_vdyp_sampling_load_balanced_mode_raises_not_implemented() -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1, 2, 3, 4]})

    with pytest.raises(NotImplementedError, match="load_balanced"):
        run_vdyp_sampling(
            sample_table=sample_table,
            nsamples="auto",
            min_samples=1,
            max_samples=10,
            nsamples_c1=0.1,
            nsamples_c2=1.0,
            confidence=95,
            half_rel_ci=0.05,
            ipp_mode="load_balanced",
            vdyp_timeout=2.0,
            rc_len=1,
            verbose=False,
            vdyp_out_cache=None,
            random_seed=None,
            run_batch_fn=lambda feature_ids, **_kwargs: {
                int(fid): {"ok": True} for fid in feature_ids
            },
            nsamples_from_curves_fn=lambda _vdyp_out, **_kwargs: (4, None),
        )


def test_run_vdyp_sampling_fixed_mode_honors_random_seed() -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": list(range(1, 11))})

    def _run_once() -> list[int]:
        sampled_ids: list[int] = []

        def run_batch_fn(
            feature_ids: object, **_kwargs: object
        ) -> dict[int, dict[str, object]]:
            sampled_ids.extend(int(fid) for fid in feature_ids)
            return {int(fid): {"ok": True} for fid in feature_ids}

        run_vdyp_sampling(
            sample_table=sample_table,
            nsamples=3,
            min_samples=1,
            max_samples=10,
            nsamples_c1=0.1,
            nsamples_c2=0.1,
            confidence=95,
            half_rel_ci=0.05,
            ipp_mode=None,
            vdyp_timeout=2.0,
            rc_len=1,
            verbose=False,
            vdyp_out_cache=None,
            random_seed=7,
            run_batch_fn=run_batch_fn,
            nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
        )
        return sampled_ids

    assert _run_once() == _run_once()


def test_run_vdyp_for_stratum_requires_wine_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vdyp_stage.os, "name", "posix", raising=False)
    sample_table = pd.DataFrame({"FEATURE_ID": [1]})
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    with pytest.raises(RuntimeError, match="wine not found"):
        run_vdyp_for_stratum(
            sample_table=sample_table,
            tsa="08",
            run_id="run-1",
            vdyp_ply=pd.DataFrame({"FEATURE_ID": [1]}),
            vdyp_lyr=pd.DataFrame({"FEATURE_ID": [1]}),
            rc_len=1,
            curve_fit_fn=lambda *_a, **_k: None,
            fit_func=lambda *_a, **_k: None,
            fit_func_bounds_func=lambda *_a, **_k: None,
            vdyp_binpath=str(vdyp_bin),
            vdyp_params_infile=str(vdyp_params),
            which_fn=lambda _name: None,
            execute_vdyp_batch_fn=lambda **_kwargs: {},
        )


def test_run_vdyp_for_stratum_uses_default_log_paths_and_runs_batch(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1, 2]})
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")
    events: list[dict[str, object]] = []

    def fake_append_jsonl(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_log_paths(**_kwargs: object) -> dict[str, Path]:
        return {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        }

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="08",
        run_id="run-1",
        vdyp_ply=pd.DataFrame({"FEATURE_ID": [1, 2]}),
        vdyp_lyr=pd.DataFrame({"FEATURE_ID": [1, 2]}),
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=fake_log_paths,
        append_jsonl_fn=fake_append_jsonl,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=lambda **kwargs: {
            int(fid): {"phase": kwargs["phase"]} for fid in kwargs["feature_ids"]
        },
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert set(out) == {1, 2}
    assert events and events[0]["status"] == "start"


def test_run_vdyp_for_stratum_default_nsamples_wrapper_handles_infinite_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1, 2, 3]})
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")
    phases: list[str] = []

    monkeypatch.setattr(
        "femic.pipeline.vdyp_sampling.nsamples_from_curves",
        lambda *_args, **_kwargs: (np.inf, None),
    )

    def fake_execute_vdyp_batch_fn(**kwargs: object) -> dict[int, dict[str, object]]:
        phases.append(str(kwargs["phase"]))
        feature_ids = kwargs["feature_ids"]
        assert isinstance(feature_ids, list)
        return {int(fid): {"phase": kwargs["phase"]} for fid in feature_ids}

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="08",
        run_id="run-inf-target",
        vdyp_ply=pd.DataFrame({"FEATURE_ID": [1, 2, 3]}),
        vdyp_lyr=pd.DataFrame({"FEATURE_ID": [1, 2, 3]}),
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=fake_execute_vdyp_batch_fn,
        min_samples=1,
        max_samples=10,
        nsamples_c2=1.0,
    )

    assert phases[0] == "initial"
    assert "gap_fill" in phases[1:]
    assert set(out) == {1, 2, 3}


def test_run_vdyp_for_stratum_resolves_relative_binpath_from_source_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1]})
    source_root = tmp_path / "source"
    bin_rel = Path("source_only/VDYP7/VDYP7Console.exe")
    vdyp_bin = source_root / bin_rel
    vdyp_bin.parent.mkdir(parents=True, exist_ok=True)
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_params.write_text("x", encoding="utf-8")
    monkeypatch.setenv("FEMIC_SOURCE_ROOT", str(source_root))

    captured_binpaths: list[str] = []

    def _capture_execute(**kwargs: object) -> dict[int, dict[str, object]]:
        captured_binpaths.append(str(kwargs["vdyp_binpath"]))
        feature_ids = kwargs["feature_ids"]
        assert isinstance(feature_ids, list)
        return {int(fid): {"phase": kwargs["phase"]} for fid in feature_ids}

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="08",
        run_id="run-1",
        vdyp_ply=pd.DataFrame({"FEATURE_ID": [1]}),
        vdyp_lyr=pd.DataFrame({"FEATURE_ID": [1]}),
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        vdyp_binpath=str(bin_rel),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=_capture_execute,
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert set(out) == {1}
    assert captured_binpaths == [str(vdyp_bin.resolve())]


def test_run_vdyp_for_stratum_maps_source_feature_ids_via_map_id(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_ply = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_lyr = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    captured_feature_ids: list[int] = []

    def fake_execute_vdyp_batch_fn(**kwargs: object) -> dict[int, dict[str, int]]:
        feature_ids = [int(fid) for fid in kwargs["feature_ids"]]
        captured_feature_ids.extend(feature_ids)
        return {fid: {"curve_id": fid} for fid in feature_ids}

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="k3z",
        run_id="run-map-join",
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        nsamples="all",
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=fake_execute_vdyp_batch_fn,
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert captured_feature_ids == [11, 12]
    assert set(out.keys()) == {1001, 1002}
    assert out[1001] == {"curve_id": 11}
    assert out[1002] == {"curve_id": 12}


def test_run_vdyp_for_stratum_remaps_nonmatching_output_keys_by_batch_order(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame({"FEATURE_ID": [1001, 1002]})
    vdyp_ply = pd.DataFrame({"FEATURE_ID": [1001, 1002]})
    vdyp_lyr = pd.DataFrame({"FEATURE_ID": [1001, 1002]})
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    captured_feature_ids: list[int] = []

    def fake_execute_vdyp_batch_fn(**kwargs: object) -> dict[int, dict[str, int]]:
        feature_ids = [int(fid) for fid in kwargs["feature_ids"]]
        captured_feature_ids.extend(feature_ids)
        return {
            79: {"curve_id": feature_ids[0]},
            51: {"curve_id": feature_ids[1]},
        }

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="k3z",
        run_id="run-order-remap",
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        nsamples="all",
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=fake_execute_vdyp_batch_fn,
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert captured_feature_ids == [1001, 1002]
    assert set(out.keys()) == {1001, 1002}
    assert out[1001] == {"curve_id": 1001}
    assert out[1002] == {"curve_id": 1002}


def test_run_vdyp_for_stratum_order_remap_still_maps_back_to_source_feature_ids(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_ply = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_lyr = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
        }
    )
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="k3z",
        run_id="run-map-join-order-remap",
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        nsamples="all",
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=lambda **kwargs: {
            79: {"curve_id": int(kwargs["feature_ids"][0])},
            51: {"curve_id": int(kwargs["feature_ids"][1])},
        },
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert set(out.keys()) == {1001, 1002}
    assert out[1001] == {"curve_id": 11}
    assert out[1002] == {"curve_id": 12}


def test_run_vdyp_for_stratum_prefers_map_polygon_join_when_available(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_ID": [5001, 5002],
        }
    )
    vdyp_ply = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_NUMBER": [5001, 5002],
        }
    )
    vdyp_lyr = pd.DataFrame(
        {
            "FEATURE_ID": [11, 12],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_NUMBER": [5001, 5002],
        }
    )
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    captured_feature_ids: list[int] = []

    def fake_execute_vdyp_batch_fn(**kwargs: object) -> dict[int, dict[str, int]]:
        feature_ids = [int(fid) for fid in kwargs["feature_ids"]]
        captured_feature_ids.extend(feature_ids)
        return {fid: {"curve_id": fid} for fid in feature_ids}

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="k3z",
        run_id="run-map-polygon-join",
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        nsamples="all",
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=fake_execute_vdyp_batch_fn,
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert captured_feature_ids == [11, 12]
    assert set(out.keys()) == {1001, 1002}
    assert out[1001] == {"curve_id": 11}
    assert out[1002] == {"curve_id": 12}


def test_run_vdyp_for_stratum_maps_table_number_outputs_via_table_attrs(
    tmp_path: Path,
) -> None:
    sample_table = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_ID": [5001, 5002],
        }
    )
    vdyp_ply = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_NUMBER": [5001, 5002],
        }
    )
    vdyp_lyr = pd.DataFrame(
        {
            "FEATURE_ID": [1001, 1002],
            "MAP_ID": ["092L043", "092L043"],
            "POLYGON_NUMBER": [5001, 5002],
        }
    )
    vdyp_bin = tmp_path / "vdyp.exe"
    vdyp_params = tmp_path / "vdyp_params-landp"
    vdyp_bin.write_text("x", encoding="utf-8")
    vdyp_params.write_text("x", encoding="utf-8")

    def _table(curve_id: int, map_name: str, polygon_id: int) -> pd.DataFrame:
        table = pd.DataFrame({"curve_id": [curve_id]})
        table.attrs["vdyp_map_name"] = map_name
        table.attrs["vdyp_polygon_id"] = polygon_id
        return table

    out = run_vdyp_for_stratum(
        sample_table=sample_table,
        tsa="k3z",
        run_id="run-table-attrs-remap",
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        rc_len=1,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        nsamples="all",
        vdyp_binpath=str(vdyp_bin),
        vdyp_params_infile=str(vdyp_params),
        which_fn=lambda _name: "/usr/bin/wine",
        build_tsa_vdyp_log_paths_fn=lambda **_kwargs: {
            "run": tmp_path / "run.jsonl",
            "curve": tmp_path / "curve.jsonl",
            "stdout": tmp_path / "stdout.log",
            "stderr": tmp_path / "stderr.log",
        },
        append_jsonl_fn=lambda *_args: None,
        append_text_fn=lambda *_args: None,
        execute_vdyp_batch_fn=lambda **_kwargs: {
            1: _table(1001, "092L043", 5001),
            2: _table(1002, "092L043", 5002),
            3: _table(9999, "092L999", 9999),
        },
        nsamples_from_curves_fn=lambda *_a, **_k: (0, None),
    )

    assert set(out.keys()) == {1001, 1002}
    assert int(out[1001]["curve_id"].iloc[0]) == 1001
    assert int(out[1002]["curve_id"].iloc[0]) == 1002


def test_build_run_vdyp_for_stratum_runner_binds_runtime_context() -> None:
    sample_table = object()
    captured: dict[str, object] = {}

    def fake_run_vdyp_for_stratum(**kwargs: object) -> dict[int, str]:
        captured.update(kwargs)
        return {1: "ok"}

    runner = build_run_vdyp_for_stratum_runner(
        tsa="08",
        run_id="run-1",
        vdyp_ply="ply",
        vdyp_lyr="lyr",
        rc_len=42,
        curve_fit_fn=lambda *_a, **_k: None,
        fit_func=lambda *_a, **_k: None,
        fit_func_bounds_func=lambda *_a, **_k: None,
        append_jsonl_fn=lambda *_a, **_k: None,
        vdyp_log_path="run.jsonl",
        vdyp_stdout_log_path="stdout.log",
        vdyp_stderr_log_path="stderr.log",
        sampling_seed_base=1234,
        run_vdyp_for_stratum_fn=fake_run_vdyp_for_stratum,
    )
    out = runner(sample_table, verbose=True, nsamples="all")

    assert out == {1: "ok"}
    assert captured["sample_table"] is sample_table
    assert captured["tsa"] == "08"
    assert captured["run_id"] == "run-1"
    assert captured["vdyp_ply"] == "ply"
    assert captured["vdyp_lyr"] == "lyr"
    assert captured["rc_len"] == 42
    assert captured["vdyp_log_path"] == "run.jsonl"
    assert captured["vdyp_stdout_log_path"] == "stdout.log"
    assert captured["vdyp_stderr_log_path"] == "stderr.log"
    assert captured["verbose"] is True
    assert captured["nsamples"] == "all"
    assert captured["sampling_seed"] == 1234

    runner(sample_table, sampling_seed=777)
    assert captured["sampling_seed"] == 777


def test_execute_vdyp_batch_logs_ok_and_returns_output(tmp_path: Path) -> None:
    (tmp_path / "vdyp_io").mkdir(parents=True)
    vdyp_ply, vdyp_lyr = _sample_vdyp_tables()
    events: list[dict[str, object]] = []
    text_logs: list[tuple[str, str]] = []

    def fake_write(*args: object) -> None:
        assert len(args) == 6

    def fake_import(path: str) -> dict[int, object]:
        assert Path(path).name.endswith(".out")
        return {1: {"curve": "ok"}}

    def fake_append_jsonl(path: str | Path, payload: object) -> None:
        assert path == tmp_path / "vdyp_io" / "vdyp_runs.jsonl"
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_append_text(path: str | Path, text: str) -> None:
        text_logs.append((str(path), text))

    def fake_run(*_args: object, **_kwargs: object) -> _RunResult:
        return _RunResult(stdout="vdyp stdout", stderr="")

    out = execute_vdyp_batch(
        feature_ids=[1, 2],
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="vdyp_params-landp",
        vdyp_io_dirname=str(tmp_path / "vdyp_io"),
        vdyp_log_path=tmp_path / "vdyp_io" / "vdyp_runs.jsonl",
        vdyp_stdout_log_path=tmp_path / "vdyp_io" / "vdyp_stdout.log",
        vdyp_stderr_log_path=tmp_path / "vdyp_io" / "vdyp_stderr.log",
        phase="initial",
        cache_hits=1,
        timeout=10,
        run_id="run-abc",
        base_context={"tsa": "08"},
        write_vdyp_infiles=fake_write,
        import_vdyp_tables_fn=fake_import,
        append_jsonl_fn=fake_append_jsonl,
        append_text_fn=fake_append_text,
        subprocess_run=fake_run,
    )

    assert out == {1: {"curve": "ok"}}
    assert len(events) == 1
    assert events[0]["status"] == "ok"
    assert events[0]["phase"] == "initial"
    assert events[0]["context"] == {"tsa": "08", "run_id": "run-abc"}
    assert len(text_logs) == 1
    assert "phase=initial" in text_logs[0][1]


def test_execute_vdyp_batch_logs_parse_error(tmp_path: Path) -> None:
    (tmp_path / "vdyp_io").mkdir(parents=True)
    vdyp_ply, vdyp_lyr = _sample_vdyp_tables()
    events: list[dict[str, object]] = []

    def fake_append_jsonl(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    out = execute_vdyp_batch(
        feature_ids=[1],
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="vdyp_params-landp",
        vdyp_io_dirname=str(tmp_path / "vdyp_io"),
        vdyp_log_path=tmp_path / "vdyp_io" / "vdyp_runs.jsonl",
        vdyp_stdout_log_path=tmp_path / "vdyp_io" / "vdyp_stdout.log",
        vdyp_stderr_log_path=tmp_path / "vdyp_io" / "vdyp_stderr.log",
        phase="initial",
        write_vdyp_infiles=lambda *_args: None,
        import_vdyp_tables_fn=lambda _path: (_ for _ in ()).throw(
            ValueError("bad parse")
        ),
        append_jsonl_fn=fake_append_jsonl,
        append_text_fn=lambda *_args: None,
        subprocess_run=lambda *_args, **_kwargs: _RunResult(stdout="", stderr=""),
    )

    assert out == {}
    assert len(events) == 1
    assert events[0]["status"] == "parse_error"


def test_execute_vdyp_batch_logs_timeout(tmp_path: Path) -> None:
    (tmp_path / "vdyp_io").mkdir(parents=True)
    vdyp_ply, vdyp_lyr = _sample_vdyp_tables()
    events: list[dict[str, object]] = []

    def fake_append_jsonl(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def timeout_run(*_args: object, **_kwargs: object) -> _RunResult:
        raise subprocess.TimeoutExpired(cmd="vdyp", timeout=5)

    out = execute_vdyp_batch(
        feature_ids=[1],
        vdyp_ply=vdyp_ply,
        vdyp_lyr=vdyp_lyr,
        vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
        vdyp_params_infile="vdyp_params-landp",
        vdyp_io_dirname=str(tmp_path / "vdyp_io"),
        vdyp_log_path=tmp_path / "vdyp_io" / "vdyp_runs.jsonl",
        vdyp_stdout_log_path=tmp_path / "vdyp_io" / "vdyp_stdout.log",
        vdyp_stderr_log_path=tmp_path / "vdyp_io" / "vdyp_stderr.log",
        phase="initial",
        write_vdyp_infiles=lambda *_args: None,
        import_vdyp_tables_fn=lambda _path: {},
        append_jsonl_fn=fake_append_jsonl,
        append_text_fn=lambda *_args: None,
        subprocess_run=timeout_run,
    )

    assert out == {}
    assert len(events) == 1
    assert events[0]["status"] == "timeout"


def test_execute_vdyp_batch_unexpected_subprocess_error_propagates(
    tmp_path: Path,
) -> None:
    (tmp_path / "vdyp_io").mkdir(parents=True)
    vdyp_ply, vdyp_lyr = _sample_vdyp_tables()

    with pytest.raises(ZeroDivisionError):
        execute_vdyp_batch(
            feature_ids=[1],
            vdyp_ply=vdyp_ply,
            vdyp_lyr=vdyp_lyr,
            vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
            vdyp_params_infile="vdyp_params-landp",
            vdyp_io_dirname=str(tmp_path / "vdyp_io"),
            vdyp_log_path=tmp_path / "vdyp_io" / "vdyp_runs.jsonl",
            vdyp_stdout_log_path=tmp_path / "vdyp_io" / "vdyp_stdout.log",
            vdyp_stderr_log_path=tmp_path / "vdyp_io" / "vdyp_stderr.log",
            phase="initial",
            write_vdyp_infiles=lambda *_args: None,
            import_vdyp_tables_fn=lambda _path: {},
            append_jsonl_fn=lambda *_args: None,
            append_text_fn=lambda *_args: None,
            subprocess_run=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                ZeroDivisionError("unexpected")
            ),
        )


def test_execute_vdyp_batch_unexpected_parse_error_propagates(tmp_path: Path) -> None:
    (tmp_path / "vdyp_io").mkdir(parents=True)
    vdyp_ply, vdyp_lyr = _sample_vdyp_tables()

    with pytest.raises(ZeroDivisionError):
        execute_vdyp_batch(
            feature_ids=[1],
            vdyp_ply=vdyp_ply,
            vdyp_lyr=vdyp_lyr,
            vdyp_binpath="VDYP7/VDYP7/VDYP7Console.exe",
            vdyp_params_infile="vdyp_params-landp",
            vdyp_io_dirname=str(tmp_path / "vdyp_io"),
            vdyp_log_path=tmp_path / "vdyp_io" / "vdyp_runs.jsonl",
            vdyp_stdout_log_path=tmp_path / "vdyp_io" / "vdyp_stdout.log",
            vdyp_stderr_log_path=tmp_path / "vdyp_io" / "vdyp_stderr.log",
            phase="initial",
            write_vdyp_infiles=lambda *_args: None,
            import_vdyp_tables_fn=lambda _path: (_ for _ in ()).throw(
                ZeroDivisionError("unexpected")
            ),
            append_jsonl_fn=lambda *_args: None,
            append_text_fn=lambda *_args: None,
            subprocess_run=lambda *_args, **_kwargs: _RunResult(stdout="", stderr=""),
        )


def test_execute_bootstrap_vdyp_runs_success() -> None:
    events: list[dict[str, object]] = []
    seen_nsamples: list[object] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_run_vdyp(sample: object, **_kwargs: object) -> dict[int, dict[str, str]]:
        assert sample == "sample-ss"
        seen_nsamples.append(_kwargs.get("nsamples"))
        return {1: {"curve": "ok"}}

    results = execute_bootstrap_vdyp_runs(
        tsa="08",
        run_id="run-1",
        results_for_tsa=[(3, "S1", {"L": {"ss": "sample-ss"}})],
        si_levels=["L"],
        vdyp_run_events_path="dummy.jsonl",
        append_jsonl_fn=append_event,
        run_vdyp_fn=fake_run_vdyp,
        verbose=False,
    )

    assert results == {3: {"L": {1: {"curve": "ok"}}}}
    assert len(events) == 1
    assert events[0]["status"] == "dispatch"
    assert events[0]["phase"] == "bootstrap"
    assert seen_nsamples == ["auto"]


def test_execute_bootstrap_vdyp_runs_derives_sampling_seed_per_stratum_and_si() -> None:
    seen_seeds: list[int | None] = []
    seen_nsamples: list[object] = []

    def append_event(_path: str | Path, _payload: object) -> None:
        return None

    def fake_run_vdyp(_sample: object, **kwargs: object) -> dict[int, dict[str, str]]:
        seen_seeds.append(kwargs.get("sampling_seed"))
        seen_nsamples.append(kwargs.get("nsamples"))
        return {1: {"curve": "ok"}}

    execute_bootstrap_vdyp_runs(
        tsa="08",
        run_id="run-1",
        results_for_tsa=[(3, "S1", {"L": {"ss": "sample-l"}, "M": {"ss": "sample-m"}})],
        si_levels=["L", "M"],
        vdyp_run_events_path="dummy.jsonl",
        append_jsonl_fn=append_event,
        run_vdyp_fn=fake_run_vdyp,
        verbose=False,
        sampling_seed_base=100,
    )

    assert seen_seeds == [400, 401]
    assert seen_nsamples == ["auto", "auto"]


def test_execute_bootstrap_vdyp_runs_passes_custom_nsamples_mode() -> None:
    seen_nsamples: list[object] = []

    def append_event(_path: str | Path, _payload: object) -> None:
        return None

    def fake_run_vdyp(_sample: object, **kwargs: object) -> dict[int, dict[str, str]]:
        seen_nsamples.append(kwargs.get("nsamples"))
        return {1: {"curve": "ok"}}

    execute_bootstrap_vdyp_runs(
        tsa="08",
        run_id="run-1",
        results_for_tsa=[(3, "S1", {"L": {"ss": "sample-l"}})],
        si_levels=["L"],
        vdyp_run_events_path="dummy.jsonl",
        append_jsonl_fn=append_event,
        run_vdyp_fn=fake_run_vdyp,
        verbose=False,
        nsamples_mode="all",
    )

    assert seen_nsamples == ["all"]


def test_build_bootstrap_vdyp_results_runner_binds_dispatch_inputs() -> None:
    captured: dict[str, object] = {}

    def run_vdyp_fn(_sample: object, **_kwargs: object) -> dict[object, object]:
        return {}

    def fake_execute_bootstrap(
        **kwargs: object,
    ) -> dict[int, dict[str, dict[int, str]]]:
        captured.update(kwargs)
        return {9: {"L": {1: "ok"}}}

    run_bootstrap = build_bootstrap_vdyp_results_runner(
        tsa="08",
        run_id="run-1",
        results_for_tsa=[(9, "S9", {"L": {"ss": "sample-9"}})],
        si_levels=["L"],
        vdyp_run_events_path="run.jsonl",
        append_jsonl_fn=lambda *_a, **_k: None,
        run_vdyp_fn=run_vdyp_fn,
        vdyp_out_cache={"cached": "value"},
        nsamples_mode="all",
        execute_bootstrap_vdyp_runs_fn=fake_execute_bootstrap,
    )

    out = run_bootstrap()

    assert out == {9: {"L": {1: "ok"}}}
    assert captured["tsa"] == "08"
    assert captured["run_id"] == "run-1"
    assert captured["vdyp_run_events_path"] == "run.jsonl"
    assert captured["si_levels"] == ["L"]
    assert captured["run_vdyp_fn"] is run_vdyp_fn
    assert captured["vdyp_out_cache"] == {"cached": "value"}
    assert captured["nsamples_mode"] == "all"


def test_execute_bootstrap_vdyp_runs_logs_dispatch_error() -> None:
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def failing_run_vdyp(
        _sample: object, **_kwargs: object
    ) -> dict[int, dict[str, str]]:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        execute_bootstrap_vdyp_runs(
            tsa="08",
            run_id="run-1",
            results_for_tsa=[(5, "S2", {"L": {"ss": "sample-ss"}})],
            si_levels=["L"],
            vdyp_run_events_path="dummy.jsonl",
            append_jsonl_fn=append_event,
            run_vdyp_fn=failing_run_vdyp,
            verbose=False,
        )

    assert len(events) == 2
    assert events[0]["status"] == "dispatch"
    assert events[1]["status"] == "dispatch_error"


def test_execute_bootstrap_vdyp_runs_unexpected_error_propagates() -> None:
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def failing_run_vdyp(
        _sample: object, **_kwargs: object
    ) -> dict[int, dict[str, str]]:
        raise ZeroDivisionError("boom")

    with pytest.raises(ZeroDivisionError, match="boom"):
        execute_bootstrap_vdyp_runs(
            tsa="08",
            run_id="run-1",
            results_for_tsa=[(5, "S2", {"L": {"ss": "sample-ss"}})],
            si_levels=["L"],
            vdyp_run_events_path="dummy.jsonl",
            append_jsonl_fn=append_event,
            run_vdyp_fn=failing_run_vdyp,
            verbose=False,
        )

    assert len(events) == 1
    assert events[0]["status"] == "dispatch"


def test_execute_curve_smoothing_runs_builds_output_and_logs_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        assert isinstance(vdyp_out, dict)
        assert kwargs["curve_context"]["stratum_code"] == "S1"
        assert kwargs["custom_knob"] == 7
        assert float(kwargs["toe_shift_years"]) == pytest.approx(0.0)
        return [1.0, 20.0, 40.0], [1e-6, 120.0, 180.0]

    smoothed_runs = execute_curve_smoothing_runs(
        tsa="08",
        run_id="run-1",
        results_for_tsa=[
            (1, "S1", {}),
            (2, "S2", {}),
        ],
        si_levels=["L"],
        vdyp_results_for_tsa={
            1: {"L": {101: {"dummy": "ok"}}},
        },
        kwarg_overrides_for_tsa={("S1", "L"): {"custom_knob": 7}},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert smoothed_runs[0].stratum_code == "S1"
    assert smoothed_runs[0].si_level == "L"
    assert list(smoothed_runs[0].y) == [1e-6, 120.0, 180.0]
    missing_events = [
        event for event in events if event.get("reason") == "missing_vdyp_output"
    ]
    assert len(missing_events) == 1
    assert missing_events[0]["status"] == "warning"
    fallback_events = [
        event for event in events if event.get("stage") == "fallback_policy"
    ]
    assert len(fallback_events) == 1


def test_execute_curve_smoothing_runs_prefers_tail_blend_for_k3z_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FEMIC_K3Z_FORCE_TAIL_BLEND", "1")
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            return [0.0, 150.0, 300.0], [0.0, 220.0, 260.0]
        return [0.0, 150.0, 300.0], [0.0, 140.0, 180.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="k3z",
        run_id="run-k3z",
        results_for_tsa=[(1, "CWH_HW", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert smoothed_runs[0].stratum_code == "CWH_HW"
    assert smoothed_runs[0].si_level == "L"
    # K3Z output curves should use the tail-blend candidate when available.
    assert list(smoothed_runs[0].y) == [0.0, 220.0, 260.0]
    assert any(
        event.get("stage") == "fit_quality_gate"
        and event.get("reason") == "fit_quality_gate_failed"
        for event in events
    )


def test_execute_curve_smoothing_runs_tail_blend_respects_override_thresholds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    captured_tail_kwargs: dict[str, object] = {}

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            captured_tail_kwargs.update(kwargs)
            return [0.0, 150.0, 300.0], [0.0, 220.0, 260.0]
        return [0.0, 150.0, 300.0], [0.0, 140.0, 180.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-tail-override",
        results_for_tsa=[(1, "CWH_HW", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={
            ("CWH_HW", "L"): {
                "tail_linear_min_r2": 0.61,
                "tail_blend_years": 55.0,
            }
        },
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=lambda *_args, **_kwargs: None,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert captured_tail_kwargs
    assert captured_tail_kwargs["tail_linear_min_r2"] == 0.61
    assert captured_tail_kwargs["tail_blend_years"] == 55.0


def test_execute_curve_smoothing_runs_tail_blend_uses_env_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FEMIC_TAIL_LINEAR_MIN_R2", "0.66")
    monkeypatch.setenv("FEMIC_TAIL_BLEND_YEARS", "44")
    captured_tail_kwargs: dict[str, object] = {}

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            captured_tail_kwargs.update(kwargs)
            return [0.0, 150.0, 300.0], [0.0, 220.0, 260.0]
        return [0.0, 150.0, 300.0], [0.0, 140.0, 180.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-tail-env",
        results_for_tsa=[(1, "CWH_HW", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=lambda *_args, **_kwargs: None,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert captured_tail_kwargs
    assert captured_tail_kwargs["tail_linear_min_r2"] == 0.66
    assert captured_tail_kwargs["tail_blend_years"] == 44.0


def test_execute_curve_smoothing_runs_selects_tail_blend_with_objective_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            # Better late-tail alignment with little overall penalty.
            return [0.0, 150.0, 300.0], [0.0, 85.0, 90.0]
        return [0.0, 150.0, 300.0], [0.0, 150.0, 350.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-tail-selected",
        results_for_tsa=[(1, "CWH_HW", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={
            ("CWH_HW", "L"): {"tail_linear_allow_quantile_fallback": True}
        },
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert list(smoothed_runs[0].y) == [0.0, 85.0, 90.0]
    tail_decisions = [
        event
        for event in events
        if event.get("stage") == "tail_blend_selection"
        and event.get("reason") == "tail_blend_selected"
    ]
    assert tail_decisions
    selected_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert selected_events
    assert selected_events[-1].get("selected_path") == "tail_blend"


def test_execute_curve_smoothing_runs_layers_tail_blend_after_left_toe_censor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []
    tail_kwargs_seen: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            tail_kwargs_seen.append(dict(kwargs))
            if int(kwargs.get("skip1", 0)) > 0:
                return [0.0, 150.0, 300.0], [0.0, 70.0, 80.0]
            return [0.0, 150.0, 300.0], [0.0, 400.0, 500.0]
        if int(kwargs.get("skip1", 0)) > 0:
            return [0.0, 150.0, 300.0], [0.0, 20.0, 35.0]
        return [0.0, 150.0, 300.0], [0.0, 260.0, 320.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 50, 55, 60, 65, 70, 200, 210, 220, 230],
            "Vdwb": [
                120.0,
                10.0,
                12.0,
                14.0,
                16.0,
                18.0,
                20.0,
                22.0,
                24.0,
                80,
                82,
                83,
                84,
            ],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-layer-left-tail",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert tail_kwargs_seen
    assert int(tail_kwargs_seen[-1].get("skip1", 0)) > 0
    selection_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert selection_events
    assert selection_events[-1].get("selected_path") != "primary_nlls"


def test_execute_curve_smoothing_runs_rescues_selected_curve_gate_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            return [0.0, 150.0, 300.0], [0.0, 85.0, 90.0]
        # Non-finite primary fit should fail gate and trigger rescue.
        return [0.0, 150.0, 300.0], [0.0, float("nan"), 350.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-selected-gate-rescue",
        results_for_tsa=[(1, "CWH_HW", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    fallback_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert fallback_events
    assert fallback_events[-1].get("selected_path") == "tail_blend"
    rescue_events = [
        event
        for event in events
        if event.get("stage") == "fit_quality_gate"
        and event.get("reason") == "selected_curve_gate_rescue"
    ]
    assert rescue_events


def test_execute_curve_smoothing_runs_logs_fit_quality_gate_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **_kwargs: object
    ) -> tuple[list[float], list[float]]:
        # Intentionally implausible fit to trigger quality gate.
        return [0.0, 150.0, 300.0], [0.0, 1200.0, 1400.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    warnings = [
        event
        for event in events
        if event.get("stage") == "fit_quality_gate"
        and event.get("reason") == "fit_quality_gate_failed"
    ]
    assert warnings
    failure_reasons = warnings[-1].get("failure_reasons")
    assert isinstance(failure_reasons, list)
    assert "mape_exceeds_gate" in failure_reasons


def test_execute_curve_smoothing_runs_selects_dominant_recovery_tail_blend_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            # Better fit overall, but with much higher early overshoot ratio.
            return [0.0, 50.0, 70.0, 300.0], [0.0, 18.0, 24.0, 24.0]
        # Catastrophic primary baseline.
        return [0.0, 50.0, 70.0, 300.0], [0.0, 0.0, 0.0, 0.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 50, 55, 60, 65, 70],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 16.0, 18.0, 20.0, 22.0, 24.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29-dominant-recovery",
        results_for_tsa=[(1, "MS_PLI", {})],
        si_levels=["H"],
        vdyp_results_for_tsa={1: {"H": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={
            ("MS_PLI", "H"): {"tail_linear_allow_quantile_fallback": True}
        },
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert list(smoothed_runs[0].y) == [0.0, 18.0, 24.0, 24.0]
    tail_events = [
        event
        for event in events
        if event.get("stage") == "tail_blend_selection"
        and event.get("reason") == "tail_blend_selected"
    ]
    assert tail_events
    decision = tail_events[-1].get("decision")
    assert isinstance(decision, dict)
    assert decision.get("decision") == "selected"
    assert decision.get("policy") == "layered_when_detected"
    assert decision.get("tail_detected") is False
    selection_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert selection_events
    assert selection_events[-1].get("selected_path") == "tail_blend"


def test_execute_curve_smoothing_runs_selects_left_toe_censor_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if int(kwargs.get("skip1", 0)) > 0:
            return [0.0, 150.0, 300.0], [0.0, 20.0, 35.0]
        return [0.0, 150.0, 300.0], [0.0, 260.0, 320.0]

    # First point is a clear left-toe outlier relative to following bins.
    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 50, 55, 60, 65, 70],
            "Vdwb": [120.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29-left-toe",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert list(smoothed_runs[0].y) == [0.0, 20.0, 35.0]
    left_toe_events = [
        event
        for event in events
        if event.get("stage") == "left_toe_censor"
        and event.get("reason") == "left_toe_censor_selected"
    ]
    assert left_toe_events


def test_execute_curve_smoothing_runs_censors_early_low_discontinuity_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if int(kwargs.get("skip1", 0)) > 0:
            return [0.0, 150.0, 300.0], [0.0, 20.0, 35.0]
        return [0.0, 150.0, 300.0], [0.0, 260.0, 320.0]

    # First four bins sit on an implausibly low shoulder before a sharp rise.
    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 50, 55, 60, 65, 70],
            "Vdwb": [1.0, 1.5, 2.0, 2.5, 12.0, 18.0, 24.0, 30.0, 36.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29-left-toe-low-discontinuity",
        results_for_tsa=[(1, "MS_PLI", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    left_toe_events = [
        event
        for event in events
        if event.get("stage") == "left_toe_censor"
        and event.get("reason") == "left_toe_censor_selected"
    ]
    assert left_toe_events
    skip1_after = left_toe_events[-1].get("skip1_after")
    assert isinstance(skip1_after, int)
    assert skip1_after >= 4


def test_execute_curve_smoothing_runs_selects_merchantable_floor_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("merchantable_floor_enabled", False)):
            return [0.0, 150.0, 300.0], [0.0, 0.0, 35.0]
        return [0.0, 150.0, 300.0], [0.0, 120.0, 180.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29-floor",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={("SBPS_PL", "L"): {"toe_shift_years": 0.0}},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert list(smoothed_runs[0].y) == [0.0, 120.0, 180.0]
    floor_events = [
        event
        for event in events
        if event.get("stage") == "merchantable_floor"
        and event.get("reason") == "merchantable_floor_selected"
    ]
    assert floor_events
    fallback_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert fallback_events
    assert fallback_events[-1].get("selected_path") == "primary_nlls"
    rescue_events = [
        event
        for event in events
        if event.get("stage") == "fit_quality_gate"
        and event.get("reason") == "selected_curve_gate_rescue"
    ]
    assert rescue_events


def test_execute_curve_smoothing_runs_applies_toe_shift_env_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FEMIC_VDYP_TOE_SHIFT_YEARS", "12.5")
    observed_kwargs: list[dict[str, object]] = []

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        observed_kwargs.append(dict(kwargs))
        return [1.0, 20.0, 40.0], [1e-6, 120.0, 180.0]

    execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-toe-shift-default",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: {"dummy": "ok"}}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=lambda *_args, **_kwargs: None,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert observed_kwargs
    assert float(observed_kwargs[0]["toe_shift_years"]) == pytest.approx(12.5)


def test_execute_curve_smoothing_runs_selects_reparameterized_candidate_in_policy_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    events: list[dict[str, object]] = []

    def append_event(_path: str | Path, payload: object) -> None:
        assert isinstance(payload, dict)
        events.append(payload)

    def fake_process(
        _vdyp_out: object, **kwargs: object
    ) -> tuple[list[float], list[float]]:
        if bool(kwargs.get("tail_blend_enabled", False)):
            raise RuntimeError("disable tail candidate for this policy-order test")
        if int(kwargs.get("skip1", 0)) > 0:
            return [0.0, 150.0, 300.0], [0.0, 30.0, 55.0]
        return [0.0, 150.0, 300.0], [0.0, 260.0, 320.0]

    vdyp_obs = pd.DataFrame(
        {
            "Age": [30, 35, 40, 45, 200, 210, 220, 230],
            "Vdwb": [10.0, 12.0, 14.0, 16.0, 80.0, 82.0, 83.0, 84.0],
        }
    )
    smoothed_runs = execute_curve_smoothing_runs(
        tsa="29",
        run_id="run-29-policy-order",
        results_for_tsa=[(1, "SBPS_PL", {})],
        si_levels=["L"],
        vdyp_results_for_tsa={1: {"L": {101: vdyp_obs}}},
        kwarg_overrides_for_tsa={},
        process_vdyp_out_fn=fake_process,
        append_jsonl_fn=append_event,
        vdyp_curve_events_path="curve.jsonl",
        curve_fit_fn=lambda *_a, **_k: None,
        body_fit_func=lambda *_a, **_k: None,
        body_fit_func_bounds_func=lambda *_a, **_k: None,
        toe_fit_func=lambda *_a, **_k: None,
        toe_fit_func_bounds_func=lambda *_a, **_k: None,
        message_fn=lambda *_args, **_kwargs: None,
    )

    assert len(smoothed_runs) == 1
    assert list(smoothed_runs[0].y) == [0.0, 30.0, 55.0]
    selection_events = [
        event
        for event in events
        if event.get("stage") == "fallback_policy"
        and event.get("reason") == "curve_selected"
    ]
    assert selection_events
    assert selection_events[-1].get("selected_path") == "reparameterized_nlls"


def test_build_curve_smoothing_plot_config_applies_defaults() -> None:
    class _FakeSns:
        def __init__(self) -> None:
            self.palette_calls: list[tuple[str, int]] = []
            self.set_palette_calls: list[tuple[object, ...]] = []

        def color_palette(self, name: str, n: int) -> list[str]:
            self.palette_calls.append((name, n))
            return [f"{name}-{i}" for i in range(n)]

        def set_palette(self, palette: tuple[object, ...]) -> None:
            self.set_palette_calls.append(tuple(palette))

    fake_sns = _FakeSns()
    cfg = build_curve_smoothing_plot_config(sns_module=fake_sns)

    assert isinstance(cfg, CurveSmoothingPlotConfig)
    assert cfg.plot is True
    assert cfg.figsize == (8, 6)
    assert cfg.palette == ("Greens-0", "Greens-1", "Greens-2")
    assert cfg.palette_flavours == ("RdPu", "Blues", "Greens", "Greys")
    assert cfg.alphas == (1.0, 0.5, 0.1)
    assert cfg.xlim == (0, 300)
    assert cfg.ylim == (0, 600)
    assert fake_sns.palette_calls == [("Greens", 3)]
    assert fake_sns.set_palette_calls == [cfg.palette]


def test_build_stratum_fit_run_config_applies_defaults() -> None:
    cfg = build_stratum_fit_run_config()

    assert isinstance(cfg, StratumFitRunConfig)
    assert cfg.fit_rawdata is True
    assert cfg.min_stands_per_si_bin == 25
    assert cfg.min_age == 30
    assert cfg.agg_type == "median"
    assert cfg.plot is False
    assert cfg.verbose is False
    assert cfg.figsize == (8, 16)
    assert cfg.ylim == (0, 600)
    assert cfg.xlim == (0, 400)


def test_plot_curve_overlays_renders_expected_series() -> None:
    class _FakePlt:
        def __init__(self) -> None:
            self.plot_calls: list[tuple[object, object, dict[str, object]]] = []
            self.xlim_calls: list[tuple[float, float]] = []
            self.ylim_calls: list[tuple[float, float]] = []
            self.legend_calls = 0
            self.tight_layout_calls = 0

        def subplots(self, *_args: object, **_kwargs: object) -> tuple[None, None]:
            return None, None

        def plot(self, x: object, y: object, **kwargs: object) -> None:
            self.plot_calls.append((x, y, kwargs))

        def legend(self) -> None:
            self.legend_calls += 1

        def xlim(self, v: tuple[float, float]) -> None:
            self.xlim_calls.append(v)

        def ylim(self, v: tuple[float, float]) -> None:
            self.ylim_calls.append(v)

        def tight_layout(self) -> None:
            self.tight_layout_calls += 1

    fake_plt = _FakePlt()
    vdyp_df = pd.DataFrame(
        {"Vdwb": [100.0, 150.0]}, index=pd.Index([30, 60], name="Age")
    )
    smoothed_runs = [
        SmoothedCurveResult(
            stratumi=1,
            stratum_code="S1",
            si_level="L",
            x=[1.0, 40.0],
            y=[1e-6, 120.0],
            vdyp_out={101: vdyp_df},
        )
    ]
    plot_curve_overlays(
        results_for_tsa=[(1, "S1", {})],
        si_levels=["L"],
        smoothed_runs=smoothed_runs,
        plot=True,
        figsize=(8, 6),
        palette=["green"],
        pd_module=pd,
        plt_module=fake_plt,
        dataframe_type=pd.DataFrame,
        xlim=(0, 300),
        ylim=(0, 600),
        message_fn=lambda *_a, **_k: None,
    )

    assert len(fake_plt.plot_calls) == 2
    assert fake_plt.legend_calls == 1
    assert fake_plt.xlim_calls == [(0, 300)]
    assert fake_plt.ylim_calls == [(0, 600)]
    assert fake_plt.tight_layout_calls == 1


def test_build_smoothed_curve_table_builds_rows_and_writes_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written_paths: list[Path] = []

    def fake_to_feather(self: pd.DataFrame, path: str | Path) -> None:
        written_paths.append(Path(path))

    monkeypatch.setattr(pd.DataFrame, "to_feather", fake_to_feather)
    runs = [
        SmoothedCurveResult(
            stratumi=1,
            stratum_code="S1",
            si_level="L",
            x=[1.0, 20.0, 40.0],
            y=[1e-6, 120.0, 180.0],
            vdyp_out={},
        ),
        SmoothedCurveResult(
            stratumi=2,
            stratum_code="S2",
            si_level="M",
            x=[1.0, 50.0],
            y=[1e-6, 210.0],
            vdyp_out={},
        ),
    ]
    output_path = tmp_path / "curves.feather"
    table = build_smoothed_curve_table(
        smoothed_runs=runs,
        pd_module=pd,
        output_path=output_path,
    )

    assert set(table["stratum_code"]) == {"S1", "S2"}
    assert set(table["si_level"]) == {"L", "M"}
    assert written_paths == [output_path]


def test_build_smoothed_curve_table_handles_empty_runs() -> None:
    table = build_smoothed_curve_table(
        smoothed_runs=[],
        pd_module=pd,
        output_path=None,
    )

    assert table.empty
    assert list(table.columns) == ["index", "age", "volume", "stratum_code", "si_level"]


def test_load_or_build_vdyp_results_tsa_force_run_builds_and_writes(
    tmp_path: Path,
) -> None:
    tsa_path = tmp_path / "vdyp_results-tsa08.pkl"
    combined_path = tmp_path / "vdyp_results.pkl"
    expected = {1: {"L": {101: {"ok": True}}}}

    out = load_or_build_vdyp_results_tsa(
        tsa="08",
        force_run_vdyp=True,
        vdyp_results_tsa_pickle_path=tsa_path,
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: expected,
        print_fn=lambda *_a, **_k: None,
    )

    assert out == expected
    assert tsa_path.exists()


def test_load_or_build_vdyp_results_tsa_reads_combined_cache_with_int_key(
    tmp_path: Path,
) -> None:
    tsa_path = tmp_path / "vdyp_results-tsa08.pkl"
    combined_path = tmp_path / "vdyp_results.pkl"
    with combined_path.open("wb") as handle:
        import pickle

        pickle.dump({8: {2: {"M": {202: {"ok": True}}}}}, handle)

    out = load_or_build_vdyp_results_tsa(
        tsa="08",
        force_run_vdyp=False,
        vdyp_results_tsa_pickle_path=tsa_path,
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: {},
        print_fn=lambda *_a, **_k: None,
    )

    assert out == {2: {"M": {202: {"ok": True}}}}


def test_load_or_build_vdyp_results_tsa_bootstraps_when_combined_cache_missing_tsa(
    tmp_path: Path,
) -> None:
    tsa_path = tmp_path / "vdyp_results-tsa29.pkl"
    combined_path = tmp_path / "vdyp_results.pkl"
    with combined_path.open("wb") as handle:
        import pickle

        pickle.dump({8: {2: {"M": {202: {"ok": True}}}}}, handle)

    expected = {1: {"L": {101: {"ok": True}}}}
    out = load_or_build_vdyp_results_tsa(
        tsa="29",
        force_run_vdyp=False,
        vdyp_results_tsa_pickle_path=tsa_path,
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: expected,
        print_fn=lambda *_a, **_k: None,
    )

    assert out == expected
    assert tsa_path.exists()


def test_load_or_build_vdyp_results_tsa_bootstraps_when_combined_cache_schema_invalid(
    tmp_path: Path,
) -> None:
    tsa_path = tmp_path / "vdyp_results-tsa29.pkl"
    combined_path = tmp_path / "vdyp_results.pkl"
    with combined_path.open("wb") as handle:
        import pickle

        # Invalid per-TSA payload shape (SI-level keys at top level).
        pickle.dump({29: {"L": {"bad": True}, "M": {}, "H": {}}}, handle)

    expected = {1: {"L": {101: {"ok": True}}}}
    out = load_or_build_vdyp_results_tsa(
        tsa="29",
        force_run_vdyp=False,
        vdyp_results_tsa_pickle_path=tsa_path,
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: expected,
        print_fn=lambda *_a, **_k: None,
    )

    assert out == expected
    assert tsa_path.exists()


def test_load_or_build_vdyp_results_tsa_uses_tsa_cache_when_present(
    tmp_path: Path,
) -> None:
    tsa_path = tmp_path / "vdyp_results-tsa08.pkl"
    combined_path = tmp_path / "vdyp_results.pkl"
    expected = {9: {"H": {909: {"ok": True}}}}
    with tsa_path.open("wb") as handle:
        import pickle

        pickle.dump(expected, handle)

    out = load_or_build_vdyp_results_tsa(
        tsa="08",
        force_run_vdyp=False,
        vdyp_results_tsa_pickle_path=tsa_path,
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: {},
        print_fn=lambda *_a, **_k: None,
    )

    assert out == expected


def test_load_or_build_vdyp_results_tsa_compat_loader_fallback(tmp_path: Path) -> None:
    expected = {4: {"L": {404: {"ok": True}}}}
    combined_path = tmp_path / "combined.pkl"
    combined_path.write_bytes(b"placeholder")

    out = load_or_build_vdyp_results_tsa(
        tsa="08",
        force_run_vdyp=False,
        vdyp_results_tsa_pickle_path=tmp_path / "missing-tsa.pkl",
        vdyp_results_pickle_path=combined_path,
        run_bootstrap_fn=lambda: {},
        print_fn=lambda *_a, **_k: None,
        load_pickle_fn=lambda _path: (_ for _ in ()).throw(
            ModuleNotFoundError("legacy")
        ),
        load_compat_pickle_fn=lambda _path: {"08": expected},
        dump_pickle_fn=lambda _v, _p: None,
    )

    assert out == expected


def test_load_vdyp_input_tables_reads_feather_by_default() -> None:
    class _FakeTable:
        def __init__(self, name: str, feature_ids: list[int] | None = None) -> None:
            self.name = name
            self.writes: list[Path] = []
            self._df = pd.DataFrame({"FEATURE_ID": feature_ids or []})

        def to_feather(self, path: str | Path) -> None:
            self.writes.append(Path(path))

        @property
        def FEATURE_ID(self) -> pd.Series:
            return self._df["FEATURE_ID"]

        def __getitem__(self, key: object) -> object:
            return self._df.__getitem__(key)

        def copy(self) -> "_FakeTable":
            table = _FakeTable(self.name, self._df["FEATURE_ID"].tolist())
            table.writes = self.writes.copy()
            return table

    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[
                tuple[object, object, object, object, object]
            ] = []
            self.read_feather_calls: list[object] = []

        def read_file(
            self,
            path: object,
            *,
            layer: object,
            where: object | None = None,
            mask: object | None = None,
            ignore_geometry: bool | None = None,
            **kwargs: object,
        ) -> _FakeTable:
            self.read_file_calls.append(
                (path, kwargs.get("driver"), layer, where, mask)
            )
            return _FakeTable(f"file-{layer}", [1, 2])

        def read_feather(self, path: object) -> _FakeTable:
            self.read_feather_calls.append(path)
            return _FakeTable(f"feather-{path}", [1, 2])

    fake_gpd = _FakeGpd()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=False,
        gpd_module=fake_gpd,
    )

    assert ply.name == "feather-ply.feather"
    assert lyr.name == "feather-lyr.feather"
    assert fake_gpd.read_feather_calls == ["ply.feather", "lyr.feather"]
    assert fake_gpd.read_file_calls == []


def test_load_vdyp_input_tables_reads_source_and_writes_feather() -> None:
    class _FakeTable:
        def __init__(self, name: str, feature_ids: list[int] | None = None) -> None:
            self.name = name
            self.writes: list[Path] = []
            self._df = pd.DataFrame({"FEATURE_ID": feature_ids or []})

        def to_feather(self, path: str | Path) -> None:
            self.writes.append(Path(path))

        @property
        def FEATURE_ID(self) -> pd.Series:
            return self._df["FEATURE_ID"]

        def __getitem__(self, key: object) -> object:
            return self._df.__getitem__(key)

        def copy(self) -> "_FakeTable":
            table = _FakeTable(self.name, self._df["FEATURE_ID"].tolist())
            table.writes = self.writes.copy()
            return table

    class _FakeGpd:
        def __init__(self) -> None:
            self.tables: dict[int, _FakeTable] = {}
            self.read_file_calls: list[
                tuple[object, object, object, object, object]
            ] = []
            self.read_feather_calls: list[object] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            mask: object | None = None,
            ignore_geometry: bool | None = None,
            **kwargs: object,
        ) -> _FakeTable:
            self.read_file_calls.append(
                (path, kwargs.get("driver"), layer, where, mask)
            )
            table = _FakeTable(f"file-{layer}", [1, 2] if layer == 0 else [2, 3])
            self.tables[layer] = table
            return table

        def read_feather(self, path: object) -> _FakeTable:
            self.read_feather_calls.append(path)
            return _FakeTable(f"feather-{path}", [1, 2])

    fake_gpd = _FakeGpd()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        gpd_module=fake_gpd,
    )

    assert ply.name == "file-0"
    assert lyr.name == "file-1"
    assert fake_gpd.read_file_calls == [
        ("input.gdb", None, 0, None, None),
        ("input.gdb", None, 1, None, None),
    ]
    assert fake_gpd.read_feather_calls == []
    assert fake_gpd.tables[0].writes == [Path("ply.feather")]


def test_load_vdyp_input_tables_passes_source_where_filter() -> None:
    class _FakeTable:
        def __init__(self, name: str, feature_ids: list[int] | None = None) -> None:
            self.name = name
            self.writes: list[Path] = []
            self._df = pd.DataFrame({"FEATURE_ID": feature_ids or []})

        def to_feather(self, path: str | Path) -> None:
            self.writes.append(Path(path))

        @property
        def FEATURE_ID(self) -> pd.Series:
            return self._df["FEATURE_ID"]

        def __getitem__(self, key: object) -> object:
            return self._df.__getitem__(key)

        def copy(self) -> "_FakeTable":
            table = _FakeTable(self.name, self._df["FEATURE_ID"].tolist())
            table.writes = self.writes.copy()
            return table

    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[
                tuple[object, object, object, object, object]
            ] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            mask: object | None = None,
            ignore_geometry: bool | None = None,
            **kwargs: object,
        ) -> _FakeTable:
            self.read_file_calls.append(
                (path, kwargs.get("driver"), layer, where, mask)
            )
            return _FakeTable(f"file-{layer}", [1, 2] if layer == 0 else [2, 3])

    fake_gpd = _FakeGpd()
    load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        source_where="TSA_NUMBER = 29",
        gpd_module=fake_gpd,
    )

    assert fake_gpd.read_file_calls == [
        ("input.gdb", None, 0, "TSA_NUMBER = 29", None),
        ("input.gdb", None, 1, "TSA_NUMBER = 29", None),
    ]


def test_load_vdyp_input_tables_applies_source_mask_and_filters_layer_rows() -> None:
    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[
                tuple[object, object, object, object, object]
            ] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            mask: object | None = None,
            ignore_geometry: bool | None = None,
            **kwargs: object,
        ) -> pd.DataFrame:
            self.read_file_calls.append(
                (path, kwargs.get("driver"), layer, where, mask)
            )
            if layer == 0:
                return pd.DataFrame({"FEATURE_ID": [1, 2]})
            if where is None:
                return pd.DataFrame({"FEATURE_ID": [1, 2]})
            return pd.DataFrame({"FEATURE_ID": [2, 3]})

    fake_gpd = _FakeGpd()
    mask = object()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        source_mask=mask,
        gpd_module=fake_gpd,
    )

    assert fake_gpd.read_file_calls == [
        ("input.gdb", None, 0, None, mask),
        ("input.gdb", None, 1, None, None),
    ]
    assert ply["FEATURE_ID"].tolist() == [1, 2]
    assert lyr["FEATURE_ID"].tolist() == [1, 2]


def test_load_vdyp_input_tables_reads_source_by_explicit_feature_ids() -> None:
    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[
                tuple[object, object, object, object, object]
            ] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            mask: object | None = None,
            ignore_geometry: bool | None = None,
            **kwargs: object,
        ) -> pd.DataFrame:
            self.read_file_calls.append(
                (path, kwargs.get("driver"), layer, where, mask)
            )
            if where == "FEATURE_ID IN (1,2)":
                return pd.DataFrame({"FEATURE_ID": [1, 2], "layer": [layer, layer]})
            if where == "FEATURE_ID IN (3)":
                return pd.DataFrame({"FEATURE_ID": [3], "layer": [layer]})
            return pd.DataFrame({"FEATURE_ID": [], "layer": []})

    fake_gpd = _FakeGpd()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        source_feature_ids=[1, 2, 3],
        source_feature_id_chunk_size=2,
        gpd_module=fake_gpd,
    )

    assert fake_gpd.read_file_calls == [
        ("input.gdb", None, 0, "FEATURE_ID IN (1,2)", None),
        ("input.gdb", None, 0, "FEATURE_ID IN (3)", None),
        ("input.gdb", None, 1, "FEATURE_ID IN (1,2)", None),
        ("input.gdb", None, 1, "FEATURE_ID IN (3)", None),
    ]
    assert ply["FEATURE_ID"].tolist() == [1, 2, 3]
    assert lyr["FEATURE_ID"].tolist() == [1, 2, 3]


def test_load_vdyp_input_tables_reads_source_by_explicit_map_ids() -> None:
    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[tuple[object, object, object]] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            ignore_geometry: bool | None = None,
            **_kwargs: object,
        ) -> pd.DataFrame:
            self.read_file_calls.append((path, layer, where))
            if where == "MAP_ID IN ('092N010','092N019')":
                return pd.DataFrame(
                    {"MAP_ID": ["092N010", "092N019"], "FEATURE_ID": [1, 2]}
                )
            if where == "MAP_ID IN ('092N040')":
                return pd.DataFrame({"MAP_ID": ["092N040"], "FEATURE_ID": [3]})
            return pd.DataFrame({"MAP_ID": [], "FEATURE_ID": []})

    fake_gpd = _FakeGpd()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        source_map_ids=["092N010", "092N019", "092N040"],
        source_map_id_chunk_size=2,
        gpd_module=fake_gpd,
        message_fn=lambda *_args: None,
    )

    assert fake_gpd.read_file_calls == [
        ("input.gdb", 0, "MAP_ID IN ('092N010','092N019')"),
        ("input.gdb", 0, "MAP_ID IN ('092N040')"),
        ("input.gdb", 1, "MAP_ID IN ('092N010','092N019')"),
        ("input.gdb", 1, "MAP_ID IN ('092N040')"),
    ]
    assert ply["FEATURE_ID"].tolist() == [1, 2, 3]
    assert lyr["FEATURE_ID"].tolist() == [1, 2, 3]


def test_load_vdyp_input_tables_prefers_feature_ids_when_both_inputs_provided() -> None:
    class _FakeGpd:
        def __init__(self) -> None:
            self.read_file_calls: list[tuple[object, int, object | None]] = []

        def read_file(
            self,
            path: object,
            *,
            layer: int,
            where: object | None = None,
            ignore_geometry: bool | None = None,
            **_kwargs: object,
        ) -> pd.DataFrame:
            self.read_file_calls.append((path, layer, where))
            if where == "FEATURE_ID IN (101,102)":
                return pd.DataFrame(
                    {"FEATURE_ID": [101, 102], "MAP_ID": ["092N010", "092N010"]}
                )
            return pd.DataFrame({"FEATURE_ID": [], "MAP_ID": []})

    fake_gpd = _FakeGpd()
    ply, lyr = load_vdyp_input_tables(
        vdyp_input_pandl_path="input.gdb",
        vdyp_ply_feather_path="ply.feather",
        vdyp_lyr_feather_path="lyr.feather",
        read_from_source=True,
        source_feature_ids=[101, 102],
        source_map_ids=["092N010"],
        source_feature_id_chunk_size=10,
        source_map_id_chunk_size=10,
        gpd_module=fake_gpd,
        message_fn=lambda *_args: None,
    )

    assert fake_gpd.read_file_calls == [
        ("input.gdb", 0, "FEATURE_ID IN (101,102)"),
        ("input.gdb", 1, "FEATURE_ID IN (101,102)"),
    ]
    assert ply["FEATURE_ID"].tolist() == [101, 102]
    assert lyr["FEATURE_ID"].tolist() == [101, 102]
