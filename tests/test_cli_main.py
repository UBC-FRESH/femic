from __future__ import annotations

import builtins
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
import yaml

from femic.cli import main as cli_main


def _set_cli_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    fake_module_path = repo_root / "src" / "femic" / "cli" / "main.py"
    fake_module_path.parent.mkdir(parents=True, exist_ok=True)
    fake_module_path.write_text("# fake module path for preflight tests\n")
    monkeypatch.setattr(cli_main, "__file__", str(fake_module_path))
    return repo_root


def _create_preflight_required_layout(repo_root: Path) -> None:
    data_root = repo_root / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "tsa_boundaries.feather").touch()
    (data_root / "ria_vri_vclr1p_checkpoint1.feather").touch()
    (data_root / "tipsy_params_columns").touch()
    (data_root / "vdyp_ply.feather").touch()
    (data_root / "vdyp_lyr.feather").touch()
    (data_root / "vdyp_results.pkl").touch()

    (repo_root / "ria_maptiles.csv").touch()

    vdyp_cfg = repo_root / "vdyp_io" / "VDYP_CFG"
    vdyp_cfg.mkdir(parents=True, exist_ok=True)

    vdyp_exe = repo_root / "VDYP7" / "VDYP7" / "VDYP7Console.exe"
    vdyp_exe.parent.mkdir(parents=True, exist_ok=True)
    vdyp_exe.touch()


def test_enable_rich_tracebacks_ignores_missing_rich(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _patched_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> object:
        if name == "rich.traceback":
            raise ModuleNotFoundError("rich not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _patched_import)
    cli_main._enable_rich_tracebacks()


def test_enable_rich_tracebacks_unexpected_import_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def _patched_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> object:
        if name == "rich.traceback":
            raise ZeroDivisionError("unexpected")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _patched_import)
    with pytest.raises(ZeroDivisionError, match="unexpected"):
        cli_main._enable_rich_tracebacks()


def test_preflight_checks_exit_when_data_root_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_cli_repo_root(monkeypatch, tmp_path)
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.shutil, "which", lambda _: "/usr/bin/wine")

    with pytest.raises(typer.Exit) as exc_info:
        cli_main._preflight_checks(
            resume=False,
            instance_context=SimpleNamespace(root=tmp_path / "repo"),
        )

    assert exc_info.value.exit_code == 1
    assert any("Missing data directory" in msg for msg in messages)


def test_preflight_checks_resume_warns_when_wine_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    _create_preflight_required_layout(repo_root)

    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.os, "name", "posix", raising=False)
    monkeypatch.setattr(cli_main, "_source_tree_root", lambda: repo_root)
    monkeypatch.setattr(cli_main.shutil, "which", lambda _: None)

    cli_main._preflight_checks(
        resume=True,
        instance_context=SimpleNamespace(root=repo_root),
    )

    assert any("wine not found on PATH" in msg for msg in messages)
    assert not any("[red]Error:" in msg for msg in messages)


def test_preflight_checks_uses_source_root_fallback_for_shared_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = _set_cli_repo_root(monkeypatch, tmp_path)
    _create_preflight_required_layout(source_root)
    instance_root = source_root / "external" / "femic-k3z-instance"
    (instance_root / "data").mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        cli_main.shutil,
        "which",
        lambda name: (
            "tool.exe"
            if name in {"git", "git-annex", "git-annex.exe", "git-annex.cmd"}
            else None
        ),
    )

    cli_main._preflight_checks(
        resume=False,
        instance_context=SimpleNamespace(root=instance_root),
    )

    assert not any("Missing required file" in msg for msg in messages)
    assert not any("Missing VDYP configuration directory" in msg for msg in messages)
    assert not any("Missing VDYP executable" in msg for msg in messages)


def test_preflight_checks_windows_requires_git_annex(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    _create_preflight_required_layout(repo_root)

    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)

    def _which(name: str) -> str | None:
        if name == "git":
            return "C:/Program Files/Git/cmd/git.exe"
        return None

    monkeypatch.setattr(cli_main.shutil, "which", _which)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main._preflight_checks(
            resume=False,
            instance_context=SimpleNamespace(root=repo_root),
        )

    assert exc_info.value.exit_code == 1
    assert any("git-annex not found on PATH" in msg for msg in messages)


def test_validate_windows_annex_runtime_passes_when_tools_and_repo_are_healthy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data"
    public_data_root.mkdir(parents=True, exist_ok=True)
    external_paths = SimpleNamespace(
        vri_vclr1p_path=public_data_root / "data" / "bc" / "vri.gdb",
        vdyp_input_pandl_path=public_data_root / "data" / "bc" / "vdyp.gdb",
        tsa_boundaries_path=public_data_root / "data" / "bc" / "tsa.gdb",
        site_prod_bc_gdb_path=public_data_root / "data" / "bc" / "siteprod.gdb",
    )
    for path_obj in (
        external_paths.vri_vclr1p_path,
        external_paths.vdyp_input_pandl_path,
        external_paths.tsa_boundaries_path,
        external_paths.site_prod_bc_gdb_path,
    ):
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.touch()

    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        cli_main.shutil,
        "which",
        lambda name: "tool.exe" if name in {"git", "datalad"} else None,
    )
    monkeypatch.setattr(
        cli_main,
        "_run_preflight_command",
        lambda command, cwd, timeout_s=15: (True, ""),
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert errors == []
    assert warnings == []


def test_validate_windows_annex_runtime_reports_datalad_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data"
    public_data_root.mkdir(parents=True, exist_ok=True)
    external_paths = SimpleNamespace(
        vri_vclr1p_path=public_data_root / "data" / "bc" / "vri.gdb",
        vdyp_input_pandl_path=public_data_root / "data" / "bc" / "vdyp.gdb",
        tsa_boundaries_path=public_data_root / "data" / "bc" / "tsa.gdb",
        site_prod_bc_gdb_path=public_data_root / "data" / "bc" / "siteprod.gdb",
    )
    for path_obj in (
        external_paths.vri_vclr1p_path,
        external_paths.vdyp_input_pandl_path,
        external_paths.tsa_boundaries_path,
        external_paths.site_prod_bc_gdb_path,
    ):
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.touch()

    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setattr(
        cli_main.shutil,
        "which",
        lambda name: "tool.exe" if name in {"git", "datalad"} else None,
    )

    calls: list[list[str]] = []

    def _fake_run(
        command: list[str], cwd: Path, timeout_s: int = 15
    ) -> tuple[bool, str]:
        calls.append(command)
        if command[:4] == ["git", "-C", str(public_data_root), "annex"]:
            return True, ""
        return False, "status failed"

    monkeypatch.setattr(cli_main, "_run_preflight_command", _fake_run)

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert warnings == []
    assert any("DataLad status check failed" in msg for msg in errors)
    assert len(calls) == 2


def test_preflight_checks_fails_for_specific_missing_required_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    _create_preflight_required_layout(repo_root)
    missing_required = repo_root / "data" / "tipsy_params_columns"
    missing_required.unlink()

    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.shutil, "which", lambda _: "/usr/bin/wine")

    with pytest.raises(typer.Exit) as exc_info:
        cli_main._preflight_checks(
            resume=False,
            instance_context=SimpleNamespace(root=repo_root),
        )

    assert exc_info.value.exit_code == 1
    error_messages = [msg for msg in messages if "[red]Error:" in msg]
    assert len(error_messages) == 1
    assert "Missing required file" in error_messages[0]
    assert str(missing_required) in error_messages[0]


def test_run_all_exits_on_invalid_run_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_path = tmp_path / "bad.json"
    cfg_path.write_text("[]", encoding="utf-8")
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.run_all(
            data_root=Path("data"),
            output_root=Path("outputs"),
            tsa=None,
            resume=False,
            dry_run=False,
            verbose=False,
            skip_checks=False,
            debug_rows=None,
            run_id=None,
            log_dir=Path("vdyp_io/logs"),
            run_config=cfg_path,
        )

    assert exc_info.value.exit_code == 1
    assert any("Invalid run config" in msg for msg in messages)


def test_run_all_uses_profile_dry_run_and_profile_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_path = tmp_path / "run_profile.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "selection:",
                "  tsa: ['16']",
                "modes:",
                "  resume: true",
                "  dry_run: true",
                "  debug_rows: 12",
                "run:",
                "  run_id: cfg-run",
                "  log_dir: vdyp_io/custom_logs",
                "",
            ]
        ),
        encoding="utf-8",
    )
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.run_all(
            data_root=Path("data"),
            output_root=Path("outputs"),
            tsa=None,
            resume=False,
            dry_run=False,
            verbose=False,
            skip_checks=False,
            debug_rows=None,
            run_id=None,
            log_dir=Path("vdyp_io/logs"),
            run_config=cfg_path,
        )

    assert exc_info.value.exit_code == 0
    assert any("Dry run" in msg for msg in messages)
    assert any("tsa=['16']" in msg for msg in messages)
    assert any("resume=True" in msg for msg in messages)
    assert any("debug_rows=12" in msg for msg in messages)
    assert any("run_id=cfg-run" in msg for msg in messages)


def test_tsa_post_tipsy_requires_tsa(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsa_post_tipsy(
            tsa=None,
            verbose=False,
            run_id=None,
            log_dir=Path("vdyp_io/logs"),
            run_config=None,
        )

    assert exc_info.value.exit_code == 1
    assert any("Provide at least one TSA" in msg for msg in messages)


def test_tsa_post_tipsy_calls_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    def _fake_run_post_tipsy_bundle_with_manifest(
        *,
        tsa_list,
        run_id,
        log_dir,
        repo_root,
        data_root,
        message_fn,
        managed_curve_mode,
        managed_curve_x_scale,
        managed_curve_y_scale,
        managed_curve_truncate_at_culm,
        managed_curve_max_age,
    ):
        called["tsa_list"] = tsa_list
        called["run_id"] = run_id
        called["log_dir"] = log_dir
        called["repo_root"] = repo_root
        called["data_root"] = data_root
        called["managed_curve_mode"] = managed_curve_mode
        called["managed_curve_x_scale"] = managed_curve_x_scale
        called["managed_curve_y_scale"] = managed_curve_y_scale
        called["managed_curve_truncate_at_culm"] = managed_curve_truncate_at_culm
        called["managed_curve_max_age"] = managed_curve_max_age
        message_fn("fake-progress")
        return SimpleNamespace(
            manifest_path=Path("vdyp_io/logs/run_manifest-post_tipsy_test.json"),
            result=SimpleNamespace(
                tsa_list=tsa_list,
                au_rows=30,
                curve_rows=60,
                curve_points_rows=9000,
                au_table_path=Path("data/model_input_bundle/au_table.csv"),
                curve_table_path=Path("data/model_input_bundle/curve_table.csv"),
                curve_points_table_path=Path(
                    "data/model_input_bundle/curve_points_table.csv"
                ),
            ),
        )

    monkeypatch.setattr(
        cli_main,
        "run_post_tipsy_bundle_with_manifest",
        _fake_run_post_tipsy_bundle_with_manifest,
    )

    cli_main.tsa_post_tipsy(
        tsa=["29"],
        verbose=True,
        run_id="post_tipsy_test",
        log_dir=Path("vdyp_io/logs"),
        run_config=None,
    )

    assert called["tsa_list"] == ["29"]
    assert called["run_id"] == "post_tipsy_test"
    assert Path(called["log_dir"]).as_posix().endswith("vdyp_io/logs")
    assert isinstance(called["repo_root"], Path)
    assert isinstance(called["data_root"], Path)
    assert called["managed_curve_mode"] is None
    assert called["managed_curve_x_scale"] is None
    assert called["managed_curve_y_scale"] is None
    assert called["managed_curve_truncate_at_culm"] is None
    assert called["managed_curve_max_age"] is None
    assert any("post-tipsy completed" in msg for msg in messages)
    assert any("Run manifest:" in msg for msg in messages)
    assert any("fake-progress" in msg for msg in messages)


def test_tsa_post_tipsy_uses_run_config_managed_curve_options(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    cfg_path = tmp_path / "run_profile.k3z.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "selection:",
                "  tsa: ['k3z']",
                "modes:",
                "  managed_curve_mode: vdyp_transform",
                "  managed_curve_x_scale: 0.8",
                "  managed_curve_y_scale: 1.2",
                "  managed_curve_truncate_at_culm: true",
                "  managed_curve_max_age: 300",
                "run:",
                "  run_id: cfg_post_tipsy",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_run_post_tipsy_bundle_with_manifest(**kwargs):
        called.update(kwargs)
        return SimpleNamespace(
            manifest_path=Path("vdyp_io/logs/run_manifest-cfg_post_tipsy.json"),
            result=SimpleNamespace(
                tsa_list=kwargs["tsa_list"],
                au_rows=30,
                curve_rows=60,
                curve_points_rows=9000,
                au_table_path=Path("data/model_input_bundle/au_table.csv"),
                curve_table_path=Path("data/model_input_bundle/curve_table.csv"),
                curve_points_table_path=Path(
                    "data/model_input_bundle/curve_points_table.csv"
                ),
            ),
        )

    monkeypatch.setattr(
        cli_main,
        "run_post_tipsy_bundle_with_manifest",
        _fake_run_post_tipsy_bundle_with_manifest,
    )

    cli_main.tsa_post_tipsy(
        tsa=None,
        verbose=False,
        run_id=None,
        log_dir=Path("vdyp_io/logs"),
        run_config=cfg_path,
    )

    assert called["tsa_list"] == ["k3z"]
    assert called["run_id"] == "cfg_post_tipsy"
    assert called["managed_curve_mode"] == "vdyp_transform"
    assert called["managed_curve_x_scale"] == 0.8
    assert called["managed_curve_y_scale"] == 1.2
    assert called["managed_curve_truncate_at_culm"] is True
    assert called["managed_curve_max_age"] == 300


def test_export_patchworks_requires_tsa(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.export_patchworks(tsa=None)

    assert exc_info.value.exit_code == 1
    assert any("Provide at least one TSA" in msg for msg in messages)


def test_export_patchworks_calls_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    def _fake_export_patchworks_package(
        *,
        bundle_dir,
        checkpoint_path,
        output_dir,
        tsa_list,
        start_year,
        horizon_years,
        cc_min_age,
        cc_max_age,
        cc_transition_ifm,
        fragments_crs,
        ifm_source_col,
        ifm_threshold,
        ifm_target_managed_share,
        seral_stage_config_path,
        silviculture_config_path,
    ):
        called.update(
            {
                "bundle_dir": bundle_dir,
                "checkpoint_path": checkpoint_path,
                "output_dir": output_dir,
                "tsa_list": tsa_list,
                "start_year": start_year,
                "horizon_years": horizon_years,
                "cc_min_age": cc_min_age,
                "cc_max_age": cc_max_age,
                "cc_transition_ifm": cc_transition_ifm,
                "fragments_crs": fragments_crs,
                "ifm_source_col": ifm_source_col,
                "ifm_threshold": ifm_threshold,
                "ifm_target_managed_share": ifm_target_managed_share,
                "seral_stage_config_path": seral_stage_config_path,
                "silviculture_config_path": silviculture_config_path,
            }
        )
        return SimpleNamespace(
            forestmodel_xml_path=Path("output/patchworks/forestmodel.xml"),
            fragments_shapefile_path=Path("output/patchworks/fragments/fragments.shp"),
            tsa_list=tsa_list,
            au_count=12,
            fragment_count=218,
            curve_count=48,
        )

    monkeypatch.setattr(
        cli_main, "export_patchworks_package", _fake_export_patchworks_package
    )

    cli_main.export_patchworks(
        tsa=["k3z"],
        bundle_dir=Path("data/model_input_bundle"),
        checkpoint=Path("data/ria_vri_vclr1p_checkpoint7.feather"),
        output_dir=Path("output/patchworks"),
        start_year=2026,
        horizon_years=300,
        cc_min_age=0,
        cc_max_age=500,
        cc_transition_ifm="managed",
        fragments_crs="EPSG:3005",
        ifm_source_col="thlb_raw",
        ifm_threshold=0.2,
        ifm_target_managed_share=None,
        seral_stage_config=Path("config/seral.k3z.yaml"),
        silviculture_config=Path("config/silviculture.k3z.yaml"),
    )

    assert called["tsa_list"] == ["k3z"]
    assert called["cc_max_age"] == 500
    assert called["cc_transition_ifm"] == "managed"
    assert called["ifm_source_col"] == "thlb_raw"
    assert called["ifm_threshold"] == pytest.approx(0.2)
    assert (
        Path(called["seral_stage_config_path"])
        .as_posix()
        .endswith("config/seral.k3z.yaml")
    )
    assert (
        Path(called["silviculture_config_path"])
        .as_posix()
        .endswith("config/silviculture.k3z.yaml")
    )
    assert any("patchworks export completed" in msg for msg in messages)


def test_export_woodstock_requires_tsa(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.export_woodstock(tsa=None)

    assert exc_info.value.exit_code == 1
    assert any("Provide at least one TSA" in msg for msg in messages)


def test_export_woodstock_calls_exporter(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    def _fake_export_woodstock_package(
        *,
        bundle_dir,
        checkpoint_path,
        output_dir,
        tsa_list,
        cc_min_age,
        cc_max_age,
        fragments_crs,
    ):
        called.update(
            {
                "bundle_dir": bundle_dir,
                "checkpoint_path": checkpoint_path,
                "output_dir": output_dir,
                "tsa_list": tsa_list,
                "cc_min_age": cc_min_age,
                "cc_max_age": cc_max_age,
                "fragments_crs": fragments_crs,
            }
        )
        return SimpleNamespace(
            yields_csv_path=Path("output/woodstock/woodstock_yields.csv"),
            areas_csv_path=Path("output/woodstock/woodstock_areas.csv"),
            actions_csv_path=Path("output/woodstock/woodstock_actions.csv"),
            transitions_csv_path=Path("output/woodstock/woodstock_transitions.csv"),
            tsa_list=tsa_list,
            yield_rows=1234,
            area_rows=567,
            action_rows=12,
            transition_rows=12,
        )

    monkeypatch.setattr(
        cli_main, "export_woodstock_package", _fake_export_woodstock_package
    )

    cli_main.export_woodstock(
        tsa=["k3z"],
        bundle_dir=Path("data/model_input_bundle"),
        checkpoint=Path("data/ria_vri_vclr1p_checkpoint7.feather"),
        output_dir=Path("output/woodstock"),
        cc_min_age=0,
        cc_max_age=500,
        fragments_crs="EPSG:3005",
    )

    assert called["tsa_list"] == ["k3z"]
    assert called["cc_max_age"] == 500
    assert called["fragments_crs"] == "EPSG:3005"
    assert any("woodstock export completed" in msg for msg in messages)


def test_export_release_calls_packager(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    def _fake_build_release_package(
        *,
        case_id,
        output_root,
        model_input_bundle_dir,
        patchworks_output_dir,
        woodstock_output_dir,
        logs_dir,
        run_id,
        strict,
    ):
        called.update(
            {
                "case_id": case_id,
                "output_root": output_root,
                "model_input_bundle_dir": model_input_bundle_dir,
                "patchworks_output_dir": patchworks_output_dir,
                "woodstock_output_dir": woodstock_output_dir,
                "logs_dir": logs_dir,
                "run_id": run_id,
                "strict": strict,
            }
        )
        return SimpleNamespace(
            release_id="k3z_test",
            release_dir=Path("releases/k3z_test"),
            manifest_path=Path("releases/k3z_test/release_manifest.json"),
            handoff_notes_path=Path("releases/k3z_test/HANDOFF.md"),
        )

    monkeypatch.setattr(cli_main, "build_release_package", _fake_build_release_package)

    cli_main.export_release(
        case_id="k3z",
        output_root=Path("releases"),
        bundle_dir=Path("data/model_input_bundle"),
        patchworks_dir=Path("output/patchworks_k3z_validated"),
        woodstock_dir=Path("output/woodstock_k3z_validated"),
        logs_dir=Path("vdyp_io/logs"),
        run_id="test",
        strict=True,
    )

    assert called["case_id"] == "k3z"
    assert called["strict"] is True
    assert any("release package built" in msg for msg in messages)


def test_patchworks_preflight_reports_config_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fail_load(_path: Path) -> None:
        raise FileNotFoundError("missing config")

    monkeypatch.setattr(cli_main, "load_patchworks_runtime_config", _fail_load)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.patchworks_preflight(config=Path("missing.yaml"))

    assert exc_info.value.exit_code == 1
    assert any("Patchworks config error" in msg for msg in messages)


def test_patchworks_preflight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    runtime_cfg = SimpleNamespace(
        jar_path=Path("reference/Patchworks/patchworks.jar"),
        license_env="SPS_LICENSE_SERVER",
        license_value="sps_user@auth.spatial.ca",
        spshome="Z:\\Patchworks",
    )
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: runtime_cfg
    )
    monkeypatch.setattr(
        cli_main,
        "run_patchworks_preflight",
        lambda **_kwargs: SimpleNamespace(
            warnings=(),
            errors=(),
            launcher_executable="/usr/bin/wine64",
            host_mode="wine",
            license_host="auth.spatial.ca",
        ),
    )

    cli_main.patchworks_preflight(config=Path("config/patchworks.runtime.yaml"))

    assert any("Patchworks preflight passed" in msg for msg in messages)
    assert any("license_host=auth.spatial.ca" in msg for msg in messages)


def test_patchworks_matrix_build_emits_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    runtime_cfg = SimpleNamespace()
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: runtime_cfg
    )
    monkeypatch.setattr(
        cli_main,
        "run_patchworks_command",
        lambda **_kwargs: SimpleNamespace(
            run_id="pwtest",
            returncode=0,
            command=("wine64", "cmd", "/c", "java -jar patchworks.jar"),
            stdout_log_path=Path(
                "vdyp_io/logs/patchworks_matrixbuilder_stdout-pwtest.log"
            ),
            stderr_log_path=Path(
                "vdyp_io/logs/patchworks_matrixbuilder_stderr-pwtest.log"
            ),
            manifest_path=Path(
                "vdyp_io/logs/patchworks_matrixbuilder_manifest-pwtest.json"
            ),
            failures=(),
        ),
    )

    cli_main.patchworks_matrix_build(
        config=Path("config/patchworks.runtime.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="pwtest",
        interactive=False,
    )

    assert any("Patchworks matrix-builder run complete" in msg for msg in messages)
    assert any("stdout_log:" in msg for msg in messages)


def test_patchworks_build_blocks_emits_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    runtime_cfg = SimpleNamespace()
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: runtime_cfg
    )
    called: dict[str, object] = {}

    def _fake_build_patchworks_blocks_dataset(**kwargs):
        called.update(kwargs)
        return SimpleNamespace(
            model_dir=Path("C:/model"),
            blocks_shapefile_path=Path("C:/model/blocks/blocks.shp"),
            topology_csv_path=Path("C:/model/blocks/topology_blocks_200r.csv"),
            block_count=218,
            stand_id_field="FEATURE_ID",
            topology_edge_count=1024,
            topology_radius_m=200.0,
        )

    monkeypatch.setattr(
        cli_main,
        "build_patchworks_blocks_dataset",
        _fake_build_patchworks_blocks_dataset,
    )

    cli_main.patchworks_build_blocks(
        config=Path("config/patchworks.runtime.yaml"),
        model_dir=None,
        fragments_shp=None,
        topology_radius=200.0,
        topology_backend="patchworks-raster",
        with_topology=True,
    )

    assert called["topology_backend"] == "patchworks-raster"
    assert any("Patchworks blocks build complete" in msg for msg in messages)
    assert any("blocks_shapefile:" in msg for msg in messages)
    assert any("backend=patchworks-raster" in msg for msg in messages)


def test_patchworks_build_blocks_reports_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fail_load(_path: Path) -> None:
        raise FileNotFoundError("missing config")

    monkeypatch.setattr(cli_main, "load_patchworks_runtime_config", _fail_load)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.patchworks_build_blocks(
            config=Path("missing.yaml"),
            model_dir=None,
            fragments_shp=None,
            topology_radius=200.0,
            topology_backend="python",
            with_topology=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("Patchworks block build failed" in msg for msg in messages)


def test_patchworks_instances_list_emits_registry_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            builtin_registry_loaded=True,
            user_registry_path=Path("C:/Users/test/.femic/variants.yaml"),
            instances=(
                SimpleNamespace(
                    instance_id="k3z",
                    label="K3Z example instance",
                    variant_ids=("k3z.base", "k3z.intensive_light"),
                    default_variant_id="k3z.base",
                    default_scenario_set_id="k3z.proving_ground",
                ),
            ),
        ),
    )

    cli_main.patchworks_instances_list(registry=Path("variants.yaml"))

    assert any("Patchworks instances" in msg for msg in messages)
    assert any("builtins_loaded: True" in msg for msg in messages)
    assert any("k3z: K3Z example instance" in msg for msg in messages)


def test_patchworks_variants_show_emits_registry_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_variant=lambda _variant_id: SimpleNamespace(
                variant_id="k3z.base",
                label="K3Z base",
                instance_id="k3z",
                instance_label="K3Z example instance",
                variant_family="baseline",
                kind="patchworks",
                default=True,
                default_scenario_id="even_flow_smoke",
                instance_root=Path("external/femic-k3z-instance"),
                analysis_pin=Path("external/femic-k3z-instance/models/.../base.pin"),
                runtime_config=Path(
                    "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
                ),
                source="builtin",
                registry_path=None,
                runtime=None,
                notes=("note one",),
                materialization=(
                    SimpleNamespace(
                        kind="datalad-get",
                        dataset_root="external/femic-public-data",
                        relpaths=("data",),
                        estimated_bytes=1024,
                    ),
                ),
            )
        ),
    )

    cli_main.patchworks_variants_show(
        "k3z.base",
        registry=Path("variants.yaml"),
        materialization_threshold_mib=100,
    )

    assert any("Patchworks variant" in msg for msg in messages)
    assert any("variant_id: k3z.base" in msg for msg in messages)
    assert any("analysis_pin:" in msg for msg in messages)
    assert any("note: note one" in msg for msg in messages)
    assert any("materialization_summary:" in msg for msg in messages)
    assert any("materialization_dataset:" in msg for msg in messages)
    assert any("estimated=1.0 KiB" in msg for msg in messages)


def test_patchworks_variants_show_reports_no_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_variant=lambda _variant_id: SimpleNamespace(
                variant_id="k3z.base",
                label="K3Z base",
                instance_id="k3z",
                instance_label="K3Z example instance",
                variant_family="baseline",
                kind="patchworks",
                default=True,
                default_scenario_id="even_flow_smoke",
                instance_root=Path("external/femic-k3z-instance"),
                analysis_pin=Path("external/femic-k3z-instance/models/.../base.pin"),
                runtime_config=Path(
                    "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
                ),
                source="builtin",
                registry_path=None,
                runtime=None,
                notes=(),
                materialization=(),
            )
        ),
    )

    cli_main.patchworks_variants_show(
        "k3z.base",
        registry=Path("variants.yaml"),
        materialization_threshold_mib=100,
    )

    assert any("materialization_summary: none" in msg for msg in messages)


def test_patchworks_variants_materialization_plan_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_variant=lambda _variant_id: SimpleNamespace(
                variant_id="k3z.base",
                label="K3Z base",
                registry_path=None,
                materialization=(
                    SimpleNamespace(
                        kind="datalad-get",
                        dataset_root="external/femic-public-data",
                        relpaths=("data", "k3z"),
                        estimated_bytes=150 * 1024 * 1024,
                    ),
                    SimpleNamespace(
                        kind="datalad-get",
                        dataset_root="external/femic-public-data",
                        relpaths=("cache",),
                        estimated_bytes=None,
                    ),
                ),
            )
        ),
    )

    cli_main.patchworks_variants_materialization_plan(
        "k3z.base",
        registry=Path("variants.yaml"),
        materialization_threshold_mib=100,
    )

    assert any("Patchworks variant materialization plan" in msg for msg in messages)
    assert any("materialization_summary:" in msg for msg in messages)
    assert any("datasets=1" in msg for msg in messages)
    assert any("actions=2" in msg for msg in messages)
    assert any("requires_confirmation=True" in msg for msg in messages)
    assert any("has_unknown_sizes=True" in msg for msg in messages)
    assert any("materialization_dataset:" in msg for msg in messages)
    assert any("relpaths=['data', 'k3z']" in msg for msg in messages)


def test_patchworks_run_variant_reports_dataset_summary_for_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        instance_root=Path("external/femic-k3z-instance"),
        analysis_pin=Path(
            "external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin"
        ),
        runtime_config=Path(
            "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
        ),
        materialization=(
            SimpleNamespace(
                kind="datalad-get",
                dataset_root="external/femic-public-data",
                relpaths=("data",),
                estimated_bytes=150 * 1024 * 1024,
            ),
            SimpleNamespace(
                kind="datalad-get",
                dataset_root="external/femic-public-data",
                relpaths=("cache",),
                estimated_bytes=None,
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: variant),
    )
    confirmed: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        cli_main.typer,
        "confirm",
        lambda message, default=False: confirmed.append((message, default)) or True,
    )
    materialized: list[str] = []
    monkeypatch.setattr(
        cli_main,
        "materialize_patchworks_variant",
        lambda item: materialized.append(item.variant_id),
    )
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: SimpleNamespace()
    )
    monkeypatch.setattr(
        cli_main,
        "run_patchworks_headless_pin",
        lambda **_kwargs: SimpleNamespace(
            run_id="demo",
            returncode=0,
            pin_path=variant.analysis_pin,
            stage_dir=Path("vdyp_io/logs/headless_stage/demo"),
            scenario_mode="none",
            execution=SimpleNamespace(
                stdout_log_path=Path("tipsy_io/logs/stdout.log"),
                stderr_log_path=Path("tipsy_io/logs/stderr.log"),
            ),
            manifest_path=Path("tipsy_io/logs/manifest.json"),
            failures=(),
        ),
    )

    cli_main.patchworks_run_variant(
        "k3z.base",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo",
        stage_label=None,
        iterations=1,
        improvement=0.0,
        scenario_mode="none",
        scenario_target=None,
        scenario_min_annual=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert confirmed
    assert materialized == ["k3z.base"]
    rendered = "\n".join(str(msg) for msg in messages)
    assert "datasets=1" in rendered
    assert "actions=2" in rendered
    assert "materialization_dataset:" in rendered


def test_patchworks_run_variant_delegates_to_headless_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        instance_root=Path("external/femic-k3z-instance"),
        analysis_pin=Path(
            "external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin"
        ),
        runtime_config=Path(
            "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: variant),
    )
    monkeypatch.setattr(
        cli_main,
        "build_patchworks_variant_materialization_plan",
        lambda *_args, **_kwargs: SimpleNamespace(
            action_count=0,
            known_estimated_bytes=0,
            has_unknown_sizes=False,
            requires_confirmation=False,
        ),
    )
    monkeypatch.setattr(
        cli_main, "materialize_patchworks_variant", lambda *_args, **_kwargs: None
    )
    runtime_cfg = SimpleNamespace()
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: runtime_cfg
    )
    called: dict[str, object] = {}

    def _fake_run_patchworks_headless_pin(**kwargs):
        called.update(kwargs)
        return SimpleNamespace(
            run_id="demo",
            returncode=0,
            pin_path=variant.analysis_pin,
            stage_dir=Path("tipsy_io/logs/headless_stage/demo"),
            scenario_mode="none",
            execution=SimpleNamespace(
                stdout_log_path=Path("tipsy_io/logs/stdout.log"),
                stderr_log_path=Path("tipsy_io/logs/stderr.log"),
            ),
            manifest_path=Path("tipsy_io/logs/manifest.json"),
            failures=(),
        )

    monkeypatch.setattr(
        cli_main, "run_patchworks_headless_pin", _fake_run_patchworks_headless_pin
    )

    cli_main.patchworks_run_variant(
        "k3z.base",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo",
        stage_label=None,
        iterations=1,
        improvement=0.0,
        scenario_mode="none",
        scenario_target=None,
        scenario_min_annual=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert called["config"] is runtime_cfg
    assert called["pin_path"] == variant.analysis_pin
    assert Path(called["log_dir"]) == Path("vdyp_io/logs").resolve()
    assert any("Patchworks variant run complete" in msg for msg in messages)
    assert any("runtime_config:" in msg for msg in messages)


def test_patchworks_run_variant_reports_registry_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: (_ for _ in ()).throw(
            cli_main.PatchworksVariantRegistryError("boom")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.patchworks_run_variant(
            "k3z.base",
            registry=Path("variants.yaml"),
            log_dir=Path("vdyp_io/logs"),
            run_id="demo",
            stage_label=None,
            iterations=1,
            improvement=0.0,
            scenario_mode="none",
            scenario_target=None,
            scenario_min_annual=None,
            allow_large_download=False,
            materialization_threshold_mib=100,
        )

    assert exc_info.value.exit_code == 1
    assert any("Patchworks variant run failed" in msg for msg in messages)


def test_patchworks_run_variant_prompts_for_large_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        instance_root=Path("external/femic-k3z-instance"),
        analysis_pin=Path(
            "external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin"
        ),
        runtime_config=Path(
            "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
        ),
        materialization=(
            SimpleNamespace(
                kind="datalad-get",
                dataset_root="external/femic-public-data",
                relpaths=("data",),
                estimated_bytes=150 * 1024 * 1024,
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: variant),
    )
    monkeypatch.setattr(
        cli_main,
        "build_patchworks_variant_materialization_plan",
        lambda *_args, **_kwargs: SimpleNamespace(
            action_count=1,
            known_estimated_bytes=150 * 1024 * 1024,
            has_unknown_sizes=False,
            requires_confirmation=True,
        ),
    )
    confirmed: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        cli_main.typer,
        "confirm",
        lambda message, default=False: confirmed.append((message, default)) or True,
    )
    materialized: list[str] = []
    monkeypatch.setattr(
        cli_main,
        "materialize_patchworks_variant",
        lambda item: materialized.append(item.variant_id),
    )
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: SimpleNamespace()
    )
    monkeypatch.setattr(
        cli_main,
        "run_patchworks_headless_pin",
        lambda **_kwargs: SimpleNamespace(
            run_id="demo",
            returncode=0,
            pin_path=variant.analysis_pin,
            stage_dir=Path("vdyp_io/logs/headless_stage/demo"),
            scenario_mode="none",
            execution=SimpleNamespace(
                stdout_log_path=Path("tipsy_io/logs/stdout.log"),
                stderr_log_path=Path("tipsy_io/logs/stderr.log"),
            ),
            manifest_path=Path("tipsy_io/logs/manifest.json"),
            failures=(),
        ),
    )

    cli_main.patchworks_run_variant(
        "k3z.base",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo",
        stage_label=None,
        iterations=1,
        improvement=0.0,
        scenario_mode="none",
        scenario_target=None,
        scenario_min_annual=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert confirmed
    assert materialized == ["k3z.base"]
    assert any("materialization required" in msg for msg in messages)


def test_patchworks_run_variant_stops_when_large_materialization_declined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        materialization=(
            SimpleNamespace(
                kind="datalad-get",
                dataset_root="external/femic-public-data",
                relpaths=("data",),
                estimated_bytes=150 * 1024 * 1024,
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: variant),
    )
    monkeypatch.setattr(
        cli_main,
        "build_patchworks_variant_materialization_plan",
        lambda *_args, **_kwargs: SimpleNamespace(
            action_count=1,
            known_estimated_bytes=150 * 1024 * 1024,
            has_unknown_sizes=False,
            requires_confirmation=True,
        ),
    )
    monkeypatch.setattr(cli_main.typer, "confirm", lambda *_args, **_kwargs: False)
    materialize_called = False

    def _fake_materialize(*_args, **_kwargs):
        nonlocal materialize_called
        materialize_called = True

    monkeypatch.setattr(cli_main, "materialize_patchworks_variant", _fake_materialize)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.patchworks_run_variant(
            "k3z.base",
            registry=Path("variants.yaml"),
            log_dir=Path("vdyp_io/logs"),
            run_id="demo",
            stage_label=None,
            iterations=1,
            improvement=0.0,
            scenario_mode="none",
            scenario_target=None,
            scenario_min_annual=None,
            allow_large_download=False,
            materialization_threshold_mib=100,
        )

    assert exc_info.value.exit_code == 1
    assert materialize_called is False
    assert any("large materialization was not approved" in msg for msg in messages)


def test_patchworks_variants_register_writes_user_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_variant=lambda _variant_id: (_ for _ in ()).throw(
                cli_main.PatchworksVariantRegistryError("missing")
            )
        ),
    )
    registry_path = tmp_path / "variants.yaml"

    cli_main.patchworks_variants_register(
        "demo.base",
        label="Demo base",
        instance_id="demo",
        instance_root=Path("external/demo-instance"),
        analysis_pin=Path("external/demo-instance/models/demo/analysis/base.pin"),
        runtime_config=Path("external/demo-instance/config/runtime.yaml"),
        variant_family="baseline",
        kind="patchworks",
        default=False,
        instance_label="Demo instance",
        registry=registry_path,
    )

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert payload["variants"][0]["variant_id"] == "demo.base"
    assert payload["instances"][0]["label"] == "Demo instance"
    assert any("Patchworks variant registered" in msg for msg in messages)


def test_patchworks_variants_update_overlays_builtin_variant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    registry_path = tmp_path / "variants.yaml"

    builtin_variant = SimpleNamespace(
        variant_id="k3z.base",
        label="K3Z base",
        instance_id="k3z",
        instance_label="K3Z example instance",
        variant_family="baseline",
        kind="patchworks",
        instance_root=Path("external/femic-k3z-instance"),
        analysis_pin=Path(
            "external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin"
        ),
        runtime_config=Path(
            "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
        ),
        default=True,
        default_scenario_id=None,
        notes=(),
        materialization=(),
        scenarios=(),
        runtime=None,
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_variant=lambda _variant_id: builtin_variant
        ),
    )

    cli_main.patchworks_variants_update(
        "k3z.base",
        label="Overlaid K3Z base",
        instance_id=None,
        instance_root=None,
        analysis_pin=None,
        runtime_config=None,
        variant_family=None,
        kind=None,
        default=False,
        instance_label=None,
        registry=registry_path,
    )

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert payload["variants"][0]["variant_id"] == "k3z.base"
    assert payload["variants"][0]["label"] == "Overlaid K3Z base"
    assert "default" not in payload["variants"][0]
    assert any("Patchworks variant updated" in msg for msg in messages)


def test_patchworks_variants_remove_deletes_user_overlay_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    registry_path = tmp_path / "variants.yaml"
    registry_path.write_text(
        "\n".join(
            [
                "variants:",
                "  - variant_id: demo.base",
                '    label: "Demo base"',
                "    instance_id: demo",
                "    variant_family: baseline",
                "    kind: patchworks",
                "    instance_root: external/demo-instance",
                "    analysis_pin: external/demo-instance/models/demo/analysis/base.pin",
                "    runtime_config: external/demo-instance/config/runtime.yaml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    cli_main.patchworks_variants_remove("demo.base", registry=registry_path)

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    assert payload["variants"] == []
    assert any("Patchworks variant removed" in msg for msg in messages)


def test_patchworks_scenarios_list_prints_variant_scenarios(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        scenarios=(
            SimpleNamespace(
                scenario_id="even_flow_smoke",
                label="K3Z base even-flow smoke",
                mode="max-even-flow-smoke",
                target="product.Yield.managed.Total",
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: variant),
    )

    cli_main.patchworks_scenarios_list("k3z.base", registry=Path("variants.yaml"))

    assert any("Patchworks scenarios" in msg for msg in messages)
    assert any("even_flow_smoke" in msg for msg in messages)


def test_patchworks_run_scenario_delegates_to_headless_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        runtime_config=Path(
            "external/femic-k3z-instance/config/patchworks.runtime.windows.yaml"
        ),
        analysis_pin=Path(
            "external/femic-k3z-instance/models/k3z_patchworks_model/analysis/base.pin"
        ),
        materialization=(),
    )
    scenario = SimpleNamespace(
        scenario_id="even_flow_smoke",
        label="K3Z base even-flow smoke",
        mode="max-even-flow-smoke",
        target="product.Yield.managed.Total",
        min_annual=None,
        iterations=100000,
        improvement=0.0,
        stage_label=None,
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_scenario=lambda _variant_id, _scenario_id: (variant, scenario)
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "build_patchworks_variant_materialization_plan",
        lambda *_args, **_kwargs: SimpleNamespace(
            action_count=0,
            known_estimated_bytes=0,
            has_unknown_sizes=False,
            requires_confirmation=False,
        ),
    )
    monkeypatch.setattr(
        cli_main, "materialize_patchworks_variant", lambda *_args, **_kwargs: None
    )
    runtime_cfg = SimpleNamespace()
    monkeypatch.setattr(
        cli_main, "load_patchworks_runtime_config", lambda _path: runtime_cfg
    )
    called: dict[str, object] = {}

    def _fake_run_patchworks_headless_pin(**kwargs):
        called.update(kwargs)
        return SimpleNamespace(
            run_id="demo",
            returncode=0,
            pin_path=variant.analysis_pin,
            stage_dir=Path("vdyp_io/logs/headless_stage/demo"),
            scenario_mode=scenario.mode,
            execution=SimpleNamespace(
                stdout_log_path=Path("tipsy_io/logs/stdout.log"),
                stderr_log_path=Path("tipsy_io/logs/stderr.log"),
            ),
            manifest_path=Path("tipsy_io/logs/manifest.json"),
            failures=(),
        )

    monkeypatch.setattr(
        cli_main, "run_patchworks_headless_pin", _fake_run_patchworks_headless_pin
    )

    cli_main.patchworks_run_scenario(
        "k3z.base",
        "even_flow_smoke",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo",
        stage_label=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert called["config"] is runtime_cfg
    assert called["pin_path"] == variant.analysis_pin
    assert called["scenario_mode"] == "max-even-flow-smoke"
    assert called["scenario_target"] == "product.Yield.managed.Total"
    assert called["iterations"] == 100000
    assert any("Patchworks scenario run complete" in msg for msg in messages)


def test_patchworks_run_default_scenario_delegates_to_headless_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    variant = SimpleNamespace(
        variant_id="k3z.base",
        runtime_config=Path("external/femic-k3z-instance/config/runtime.yaml"),
    )
    scenario = SimpleNamespace(
        scenario_id="even_flow_smoke",
        label="Even-flow smoke",
        mode="max-even-flow-smoke",
        target="product.Yield.managed.Total",
        min_annual=None,
        iterations=100000,
        improvement=0.0,
        stage_label=None,
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_default_scenario=lambda _variant_id: (variant, scenario)
        ),
    )

    calls: list[dict[str, object]] = []

    def _fake_run_registered_scenario(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            run_id="demo_default",
            returncode=0,
            pin_path=Path("external/femic-k3z-instance/models/base.pin"),
            stage_dir=Path("vdyp_io/logs/headless_stage/demo_default"),
            manifest_path=Path("vdyp_io/logs/demo_default.json"),
            execution=SimpleNamespace(
                stdout_log_path=Path("stdout.log"),
                stderr_log_path=Path("stderr.log"),
            ),
            scenario_mode="max-even-flow-smoke",
            failures=(),
        )

    monkeypatch.setattr(
        cli_main, "_run_patchworks_registered_scenario", _fake_run_registered_scenario
    )

    cli_main.patchworks_run_default_scenario(
        "k3z.base",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo_default",
        stage_label=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert calls
    assert calls[0]["variant"] is variant
    assert calls[0]["scenario"] is scenario
    assert any("Patchworks default-scenario run complete" in msg for msg in messages)


def test_patchworks_run_default_scenario_set_delegates_to_named_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_default_scenario_set=lambda _instance_id: SimpleNamespace(
                scenario_set_id="k3z.proving_ground"
            )
        ),
    )
    calls: list[dict[str, object]] = []

    def _fake_run_scenario_set(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(cli_main, "patchworks_run_scenario_set", _fake_run_scenario_set)

    cli_main.patchworks_run_default_scenario_set(
        "k3z",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo_default_set",
        stage_label=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert calls == [
        {
            "args": ("k3z.proving_ground",),
            "kwargs": {
                "registry": Path("variants.yaml"),
                "log_dir": Path("vdyp_io/logs"),
                "run_id": "demo_default_set",
                "stage_label": None,
                "allow_large_download": False,
                "materialization_threshold_mib": 100,
            },
        }
    ]


def test_patchworks_scenario_sets_list_prints_registry_sets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    scenario_set = SimpleNamespace(
        scenario_set_id="k3z.proving_ground",
        label="K3Z proving-ground scenario smoke set",
        mode="sequential",
        instance_id="k3z",
        scenario_set_family="proving_ground",
        default=True,
        scenarios=(SimpleNamespace(), SimpleNamespace()),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            iter_scenario_sets=lambda **_kwargs: (scenario_set,)
        ),
    )

    cli_main.patchworks_scenario_sets_list(
        registry=Path("variants.yaml"),
        instance_id="k3z",
    )

    assert any("Patchworks scenario sets" in msg for msg in messages)
    assert any("k3z.proving_ground" in msg for msg in messages)
    assert any("instance=k3z" in msg for msg in messages)
    assert any("family=proving_ground" in msg for msg in messages)
    assert any("default" in msg for msg in messages)


def test_patchworks_scenario_sets_show_prints_registry_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    scenario_set = SimpleNamespace(
        scenario_set_id="k3z.proving_ground",
        label="K3Z proving-ground scenario smoke set",
        mode="sequential",
        instance_id="k3z",
        scenario_set_family="proving_ground",
        default=True,
        notes=("Demo note",),
        scenarios=(
            SimpleNamespace(variant_id="k3z.base", scenario_id="even_flow_smoke"),
            SimpleNamespace(
                variant_id="k3z.intensive_light_standstructure",
                scenario_id="even_flow_smoke",
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_scenario_set=lambda _scenario_set_id: scenario_set
        ),
    )

    cli_main.patchworks_scenario_sets_show(
        "k3z.proving_ground",
        registry=Path("variants.yaml"),
    )

    assert any("Patchworks scenario set" in msg for msg in messages)
    assert any("scenario_set_id: k3z.proving_ground" in msg for msg in messages)
    assert any("instance_id: k3z" in msg for msg in messages)
    assert any("scenario_set_family: proving_ground" in msg for msg in messages)
    assert any("note: Demo note" in msg for msg in messages)


def test_patchworks_run_scenario_set_runs_members_sequentially(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    scenario_set = SimpleNamespace(
        scenario_set_id="k3z.proving_ground",
        label="K3Z proving-ground scenario smoke set",
        mode="sequential",
        scenarios=(
            SimpleNamespace(variant_id="k3z.base", scenario_id="even_flow_smoke"),
            SimpleNamespace(
                variant_id="k3z.intensive_light_standstructure",
                scenario_id="even_flow_smoke",
            ),
        ),
    )
    variant_a = SimpleNamespace(variant_id="k3z.base")
    variant_b = SimpleNamespace(variant_id="k3z.intensive_light_standstructure")
    scenario = SimpleNamespace(
        scenario_id="even_flow_smoke",
        label="Even-flow smoke",
        mode="max-even-flow-smoke",
        target="product.Yield.managed.Total",
        min_annual=None,
        iterations=100000,
        improvement=0.0,
        stage_label=None,
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(
            get_scenario_set=lambda _id: scenario_set,
            get_scenario=lambda variant_id, _scenario_id: (
                variant_a if variant_id == "k3z.base" else variant_b,
                scenario,
            ),
        ),
    )
    calls: list[tuple[str, str]] = []

    def _fake_run_registered_scenario(**kwargs):
        calls.append((kwargs["variant"].variant_id, kwargs["run_id"]))
        return SimpleNamespace(
            run_id=kwargs["run_id"],
            returncode=0,
            stage_dir=Path(f"vdyp_io/logs/headless_stage/{kwargs['run_id']}"),
            manifest_path=Path(f"vdyp_io/logs/{kwargs['run_id']}.json"),
            failures=(),
        )

    monkeypatch.setattr(
        cli_main, "_run_patchworks_registered_scenario", _fake_run_registered_scenario
    )

    cli_main.patchworks_run_scenario_set(
        "k3z.proving_ground",
        registry=Path("variants.yaml"),
        log_dir=Path("vdyp_io/logs"),
        run_id="demo_set",
        stage_label=None,
        allow_large_download=False,
        materialization_threshold_mib=100,
    )

    assert calls == [
        ("k3z.base", "demo_set_01"),
        ("k3z.intensive_light_standstructure", "demo_set_02"),
    ]
    assert any("Patchworks scenario-set run complete" in msg for msg in messages)


def test_fansier_run_batch_emits_manifest_and_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    monkeypatch.setattr(
        cli_main,
        "run_fansier_batch",
        lambda **_kwargs: SimpleNamespace(
            manifest_path=Path("tipsy_io/logs/fansier_batch_manifest-demo.json"),
            first_output_path=Path("tipsy_io/logs/fansier_batch/demo.txt"),
            product_count=6,
            age_count=300,
            calculations=1800,
            output_files=(Path("tipsy_io/logs/fansier_batch/demo.txt"),),
        ),
    )

    cli_main.fansier_run_batch(
        rgm_path=Path("demo.rgm"),
        out_dir=Path("tipsy_io/logs/fansier_batch"),
        log_dir=Path("tipsy_io/logs"),
        run_id="demo",
        fansier_exe=Path("Fansier.exe"),
        discount_name="FEMIC Raw 0%",
        discount_dis_path=None,
        report_type="txt",
        long_report=True,
        product_cols=True,
        activity_cols=False,
        select_all_products=True,
        select_all_ages=True,
        product_name="Logs (1)",
        age_name="10.00 (1)",
    )

    assert any("FAN$IER batch run complete" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert any("calculations=1800" in msg for msg in messages)


def test_fansier_run_batch_reports_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_fansier_batch",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.FansierRuntimeError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.fansier_run_batch(
            rgm_path=Path("demo.rgm"),
            out_dir=Path("tipsy_io/logs/fansier_batch"),
            log_dir=Path("tipsy_io/logs"),
            run_id="demo",
            fansier_exe=Path("Fansier.exe"),
            discount_name="FEMIC Raw 0%",
            discount_dis_path=None,
            report_type="txt",
            long_report=False,
            product_cols=True,
            activity_cols=False,
            select_all_products=False,
            select_all_ages=False,
            product_name="Logs (1)",
            age_name="10.00 (1)",
        )

    assert exc_info.value.exit_code == 1
    assert any("FAN$IER batch run failed" in msg for msg in messages)


def test_fansier_parse_batch_output_emits_manifest_and_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "parse_fansier_batch_output_dir",
        lambda **_kwargs: SimpleNamespace(
            manifest_path=Path("tipsy_io/logs/fansier_batch_parse_manifest-demo.json"),
            report_count=1800,
            calculation_summary_rows=1800,
            harvest_summary_rows=1800,
            cost_line_rows=7200,
            product_price_factor_rows=10800,
            benefit_line_rows=54000,
        ),
    )

    cli_main.fansier_parse_batch_output(
        report_dir=Path("tipsy_io/logs/fansier_cli_smoke"),
        out_dir=Path("tipsy_io/logs/fansier_parsed"),
        report_glob="*.txt",
    )

    assert any("FAN$IER batch parse complete" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert any("benefit_rows=54000" in msg for msg in messages)


def test_fansier_parse_batch_output_reports_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "parse_fansier_batch_output_dir",
        lambda **_kwargs: (_ for _ in ()).throw(
            cli_main.FansierReportParseError("boom")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.fansier_parse_batch_output(
            report_dir=Path("tipsy_io/logs/fansier_cli_smoke"),
            out_dir=Path("tipsy_io/logs/fansier_parsed"),
            report_glob="*.txt",
        )

    assert exc_info.value.exit_code == 1
    assert any("FAN$IER batch parse failed" in msg for msg in messages)


def test_fansier_run_and_parse_emits_both_manifest_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_fansier_batch_and_parse",
        lambda **_kwargs: SimpleNamespace(
            batch_result=SimpleNamespace(
                manifest_path=Path("tipsy_io/logs/fansier_batch_manifest-demo.json"),
                output_files=(Path("tipsy_io/logs/fansier_batch/demo.txt"),),
                calculations=1800,
            ),
            parse_result=SimpleNamespace(
                manifest_path=Path(
                    "tipsy_io/logs/fansier_batch_parse_manifest-demo.json"
                ),
                benefit_line_rows=54000,
            ),
        ),
    )

    cli_main.fansier_run_and_parse(
        rgm_path=Path("demo.rgm"),
        out_dir=Path("tipsy_io/logs/fansier_batch"),
        parsed_out_dir=Path("tipsy_io/logs/fansier_parsed"),
        log_dir=Path("tipsy_io/logs"),
        run_id="demo",
        fansier_exe=Path("Fansier.exe"),
        discount_name="FEMIC Raw 0%",
        discount_dis_path=None,
        report_type="txt",
        long_report=True,
        product_cols=True,
        activity_cols=False,
        select_all_products=True,
        select_all_ages=True,
        product_name="Logs (1)",
        age_name="10.00 (1)",
    )

    assert any("FAN$IER run-and-parse complete" in msg for msg in messages)
    assert any("batch_manifest:" in msg for msg in messages)
    assert any("parse_manifest:" in msg for msg in messages)
    assert any("benefit_rows=54000" in msg for msg in messages)


def test_fansier_run_and_parse_reports_workflow_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_fansier_batch_and_parse",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.FansierWorkflowError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.fansier_run_and_parse(
            rgm_path=Path("demo.rgm"),
            out_dir=Path("tipsy_io/logs/fansier_batch"),
            parsed_out_dir=Path("tipsy_io/logs/fansier_parsed"),
            log_dir=Path("tipsy_io/logs"),
            run_id="demo",
            fansier_exe=Path("Fansier.exe"),
            discount_name="FEMIC Raw 0%",
            discount_dis_path=None,
            report_type="txt",
            long_report=True,
            product_cols=True,
            activity_cols=False,
            select_all_products=True,
            select_all_ages=True,
            product_name="Logs (1)",
            age_name="10.00 (1)",
        )

    assert exc_info.value.exit_code == 1
    assert any("FAN$IER run-and-parse failed" in msg for msg in messages)


def test_instance_init_calls_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    def _fake_bootstrap_instance_workspace(
        *,
        instance_root,
        overwrite,
        include_bc_vri_download,
        message_fn,
    ):
        called["instance_root"] = instance_root
        called["overwrite"] = overwrite
        called["include_bc_vri_download"] = include_bc_vri_download
        message_fn("download simulation")
        return SimpleNamespace(
            instance_root=instance_root,
            created_dirs=(),
            written_files=(instance_root / "QUICKSTART.md",),
            skipped_files=(),
            downloaded_archives=(),
            extracted_dirs=(),
        )

    monkeypatch.setattr(
        cli_main,
        "bootstrap_instance_workspace",
        _fake_bootstrap_instance_workspace,
    )
    monkeypatch.setattr(
        cli_main,
        "run_geospatial_preflight",
        lambda **_kwargs: SimpleNamespace(
            os_family="windows",
            install_hint="windows hint",
            gdal_version=None,
            warnings=(),
            errors=(),
            ok=True,
        ),
    )

    cli_main.instance_init(
        instance_root=Path("instance"),
        overwrite=True,
        download_bc_vri=False,
        yes=True,
    )

    assert called["instance_root"].name == "instance"
    assert called["overwrite"] is True
    assert called["include_bc_vri_download"] is False
    assert any("instance init completed" in msg for msg in messages)


def test_instance_init_with_instance_name_uses_configured_user_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: dict[str, object] = {}

    monkeypatch.setattr(
        cli_main,
        "load_femic_user_config",
        lambda: SimpleNamespace(
            config_path=Path("user.yaml"),
            exists=True,
            paths=SimpleNamespace(
                managed_external_root=Path("managed"),
                user_instance_root=Path("userspace") / "instances",
            ),
        ),
    )

    def _fake_bootstrap_instance_workspace(
        *,
        instance_root,
        overwrite,
        include_bc_vri_download,
        message_fn,
    ):
        called["instance_root"] = instance_root
        called["overwrite"] = overwrite
        called["include_bc_vri_download"] = include_bc_vri_download
        message_fn("download simulation")
        return SimpleNamespace(
            instance_root=instance_root,
            created_dirs=(),
            written_files=(instance_root / "QUICKSTART.md",),
            skipped_files=(),
            downloaded_archives=(),
            extracted_dirs=(),
        )

    monkeypatch.setattr(
        cli_main,
        "bootstrap_instance_workspace",
        _fake_bootstrap_instance_workspace,
    )
    monkeypatch.setattr(
        cli_main,
        "run_geospatial_preflight",
        lambda **_kwargs: SimpleNamespace(
            os_family="windows",
            install_hint="windows hint",
            gdal_version=None,
            warnings=(),
            errors=(),
            ok=True,
        ),
    )

    cli_main.instance_init(
        instance_root=None,
        instance_name="demo-case",
        overwrite=False,
        download_bc_vri=False,
        yes=True,
    )

    assert (
        called["instance_root"]
        == (Path("userspace") / "instances" / "demo-case").resolve()
    )
    assert any("instance init completed" in msg for msg in messages)


def test_instance_init_rejects_instance_root_and_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.instance_init(
            instance_root=Path("instance"),
            instance_name="demo-case",
            overwrite=False,
            download_bc_vri=False,
            yes=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("mutually exclusive" in msg for msg in messages)


def test_instance_config_show_prints_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "load_femic_user_config",
        lambda: SimpleNamespace(
            config_path=Path("user.yaml"),
            exists=False,
            paths=SimpleNamespace(
                managed_external_root=Path("managed"),
                user_instance_root=Path("instances"),
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "default_femic_user_paths",
        lambda: SimpleNamespace(
            managed_external_root=Path("default-managed"),
            user_instance_root=Path("default-instances"),
        ),
    )

    cli_main.instance_config_show()

    assert any("config_path: user.yaml" in msg for msg in messages)
    assert any("managed_external_root: managed" in msg for msg in messages)
    assert any(
        "default_user_instance_root: default-instances" in msg for msg in messages
    )


def test_patchworks_run_variant_surfaces_builtin_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    fake_variant = SimpleNamespace(variant_id="k3z.base")
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_variant_registry",
        lambda **_kwargs: SimpleNamespace(get_variant=lambda _variant_id: fake_variant),
    )
    monkeypatch.setattr(
        cli_main,
        "builtins_install_hint_for_variant",
        lambda _variant: "Built-in instance k3z is not available locally.",
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.patchworks_run_variant(
            variant_id="k3z.base",
            registry=Path("variants.yaml"),
            log_dir=Path("vdyp_io/logs"),
            run_id=None,
            stage_label=None,
            iterations=1,
            improvement=0.0,
            scenario_mode="none",
            scenario_target=None,
            scenario_min_annual=None,
            allow_large_download=False,
            materialization_threshold_mib=100,
        )

    assert exc_info.value.exit_code == 1
    assert any(
        "Built-in instance k3z is not available locally." in msg for msg in messages
    )


def test_instance_rebuild_runs_runner_and_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=Path("instance-root"),
            resolve_path=lambda value: Path("instance-root") / value,
        ),
    )

    calls: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, *, steps, report_sink):
            calls["steps"] = steps
            calls["report_sink"] = report_sink

        def run(self, *, run_id, context):
            calls["run_id"] = run_id
            calls["context"] = context
            return SimpleNamespace(
                failed=False,
                outcomes=(
                    SimpleNamespace(
                        step_id="validate_case",
                        status="ok",
                        duration_seconds=0.1,
                        error=None,
                    ),
                    SimpleNamespace(
                        step_id="post_tipsy_bundle",
                        status="ok",
                        duration_seconds=0.2,
                        error=None,
                    ),
                ),
            )

    monkeypatch.setattr(cli_main, "RebuildRunner", FakeRunner)
    monkeypatch.setattr(
        cli_main,
        "load_rebuild_spec",
        lambda _path: {
            "schema_version": "1.0",
            "instance": {"case_id": "x"},
            "runtime": {},
            "steps": [{}],
            "invariants": [{}],
        },
    )
    monkeypatch.setattr(cli_main, "validate_rebuild_spec_payload", lambda _payload: [])

    cli_main.instance_rebuild(
        spec=Path("config/rebuild.spec.yaml"),
        run_config=Path("config/run_profile.case_template.yaml"),
        tipsy_config_dir=Path("config/tipsy"),
        log_dir=Path("vdyp_io/logs"),
        run_id="rebuild_test",
        with_patchworks=False,
        dry_run=False,
        patchworks_config=Path("config/patchworks.runtime.yaml"),
        baseline=Path("config/rebuild.baseline.json"),
        write_baseline=False,
        allowlist=Path("config/rebuild.allowlist.yaml"),
        instance_root=Path("instance-root"),
    )

    assert calls["run_id"] == "rebuild_test"
    assert calls["context"] == {"instance_root": "instance-root"}
    step_ids = [step.step_id for step in calls["steps"]]
    assert step_ids == [
        "validate_case",
        "geospatial_preflight",
        "compile_upstream",
        "post_tipsy_bundle",
    ]
    assert any("instance rebuild" in msg for msg in messages)


def test_instance_rebuild_includes_patchworks_steps_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=Path("instance-root"),
            resolve_path=lambda value: Path("instance-root") / value,
        ),
    )

    calls: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, *, steps, report_sink):
            calls["steps"] = steps
            calls["report_sink"] = report_sink

        def run(self, *, run_id, context):
            _ = (run_id, context)
            return SimpleNamespace(failed=False, outcomes=())

    monkeypatch.setattr(cli_main, "RebuildRunner", FakeRunner)
    monkeypatch.setattr(
        cli_main,
        "load_rebuild_spec",
        lambda _path: {
            "schema_version": "1.0",
            "instance": {"case_id": "x"},
            "runtime": {},
            "steps": [{}],
            "invariants": [{}],
        },
    )
    monkeypatch.setattr(cli_main, "validate_rebuild_spec_payload", lambda _payload: [])
    monkeypatch.setattr(cli_main.console, "print", lambda _msg: None)

    cli_main.instance_rebuild(
        spec=Path("config/rebuild.spec.yaml"),
        run_config=Path("config/run_profile.case_template.yaml"),
        tipsy_config_dir=Path("config/tipsy"),
        log_dir=Path("vdyp_io/logs"),
        run_id="rebuild_test",
        with_patchworks=True,
        dry_run=False,
        patchworks_config=Path("config/patchworks.runtime.yaml"),
        baseline=Path("config/rebuild.baseline.json"),
        write_baseline=False,
        allowlist=Path("config/rebuild.allowlist.yaml"),
        instance_root=Path("instance-root"),
    )

    step_ids = [step.step_id for step in calls["steps"]]
    assert "patchworks_preflight" in step_ids
    assert "patchworks_matrix_build" in step_ids


def test_instance_rebuild_dry_run_prints_plan_without_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=Path("instance-root"),
            resolve_path=lambda value: Path("instance-root") / value,
        ),
    )

    class FailRunner:
        def __init__(self, **_kwargs):
            raise AssertionError("runner should not be constructed in dry-run mode")

    monkeypatch.setattr(cli_main, "RebuildRunner", FailRunner)
    monkeypatch.setattr(
        cli_main,
        "load_rebuild_spec",
        lambda _path: {
            "schema_version": "1.0",
            "instance": {"case_id": "x"},
            "runtime": {},
            "steps": [{}],
            "invariants": [{}],
        },
    )
    monkeypatch.setattr(cli_main, "validate_rebuild_spec_payload", lambda _payload: [])

    cli_main.instance_rebuild(
        spec=Path("config/rebuild.spec.yaml"),
        run_config=Path("config/run_profile.case_template.yaml"),
        tipsy_config_dir=Path("config/tipsy"),
        log_dir=Path("vdyp_io/logs"),
        run_id="rebuild_test",
        with_patchworks=True,
        dry_run=True,
        patchworks_config=Path("config/patchworks.runtime.yaml"),
        baseline=Path("config/rebuild.baseline.json"),
        write_baseline=False,
        allowlist=Path("config/rebuild.allowlist.yaml"),
        instance_root=Path("instance-root"),
    )

    assert any("instance rebuild dry-run" in msg for msg in messages)
    assert any("1. validate_case" in msg for msg in messages)
    assert any("patchworks_matrix_build" in msg for msg in messages)


def test_instance_rebuild_fails_when_unexpected_diffs_exceed_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    instance_root = tmp_path / "instance-root"
    (instance_root / "config").mkdir(parents=True, exist_ok=True)
    (instance_root / "config/patchworks.runtime.yaml").write_text(
        "patchworks:\n  jar_path: C:/patchworks/patchworks.jar\n"
        "  license_env: SPS_LICENSE_SERVER\n"
        "  license_value: user@server\n"
        "  spshome: C:/patchworks\n"
        "matrix_builder:\n"
        "  fragments_path: C:/tmp/fragments.dbf\n"
        "  output_dir: C:/tmp/tracks\n"
        "  forestmodel_xml_path: C:/tmp/ForestModel.xml\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda value: instance_root / value,
        ),
    )

    class FakeRunner:
        def __init__(self, *, steps, report_sink):
            _ = (steps, report_sink)

        def run(self, *, run_id, context):
            _ = (run_id, context)
            return SimpleNamespace(failed=False, outcomes=())

    monkeypatch.setattr(cli_main, "RebuildRunner", FakeRunner)
    monkeypatch.setattr(
        cli_main,
        "load_rebuild_spec",
        lambda _path: {
            "schema_version": "1.0",
            "instance": {"case_id": "x"},
            "runtime": {"baseline_unexpected_diff_threshold": 0},
            "steps": [{}],
            "invariants": [],
        },
    )
    monkeypatch.setattr(cli_main, "validate_rebuild_spec_payload", lambda _payload: [])
    monkeypatch.setattr(cli_main, "collect_rebuild_metrics", lambda **_kwargs: {})
    monkeypatch.setattr(
        cli_main,
        "build_current_snapshot",
        lambda **_kwargs: {"track_tables": {}, "forestmodel_xml": {}},
    )
    monkeypatch.setattr(cli_main, "load_snapshot", lambda _path: {})
    monkeypatch.setattr(
        cli_main,
        "diff_snapshots",
        lambda **_kwargs: {
            "table_diffs": [],
            "xml_diff": {"status": "unchanged", "changed_keys": []},
            "diff_count": 1,
            "baseline_match": False,
        },
    )
    monkeypatch.setattr(
        cli_main,
        "load_diff_allowlist",
        lambda _path: {"allowed_table_diffs": [], "allowed_xml_keys": []},
    )
    monkeypatch.setattr(
        cli_main,
        "apply_diff_allowlist",
        lambda **_kwargs: {
            "unexpected_table_diffs": [{"table": "accounts.csv"}],
            "unexpected_xml_keys": [],
            "unexpected_diff_count": 1,
            "allowlist_match": False,
        },
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.instance_rebuild(
            spec=Path("config/rebuild.spec.yaml"),
            run_config=Path("config/run_profile.case_template.yaml"),
            tipsy_config_dir=Path("config/tipsy"),
            log_dir=Path("vdyp_io/logs"),
            run_id="rebuild_test",
            with_patchworks=False,
            dry_run=False,
            patchworks_config=Path("config/patchworks.runtime.yaml"),
            baseline=Path("config/rebuild.baseline.json"),
            write_baseline=False,
            allowlist=Path("config/rebuild.allowlist.yaml"),
            instance_root=instance_root,
        )

    assert exc_info.value.exit_code == 1
    assert any("unexpected baseline diffs exceed threshold" in msg for msg in messages)


def test_instance_rebuild_fails_on_fatal_invariant_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=Path("instance-root"),
            resolve_path=lambda value: Path("instance-root") / value,
        ),
    )

    class FakeRunner:
        def __init__(self, *, steps, report_sink):
            _ = (steps, report_sink)

        def run(self, *, run_id, context):
            _ = (run_id, context)
            return SimpleNamespace(failed=False, outcomes=())

    monkeypatch.setattr(cli_main, "RebuildRunner", FakeRunner)
    monkeypatch.setattr(
        cli_main,
        "load_rebuild_spec",
        lambda _path: {
            "schema_version": "1.0",
            "instance": {"case_id": "x"},
            "runtime": {},
            "steps": [{}],
            "invariants": [],
        },
    )
    monkeypatch.setattr(cli_main, "validate_rebuild_spec_payload", lambda _payload: [])
    monkeypatch.setattr(
        cli_main,
        "collect_rebuild_metrics",
        lambda **_kwargs: {"products.nonzero_labels": []},
    )
    monkeypatch.setattr(
        cli_main,
        "evaluate_invariants",
        lambda **_kwargs: [
            SimpleNamespace(
                invariant_id="species_policy_nonzero_product_yield_managed_plc",
                status="fail",
                severity="fatal",
                message="missing nonzero PLC signal",
                remediation="rebuild tracks and inspect products/curves",
            )
        ],
    )
    monkeypatch.setattr(cli_main, "has_fatal_invariant_failures", lambda _results: True)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.instance_rebuild(
            spec=Path("config/rebuild.spec.yaml"),
            run_config=Path("config/run_profile.case_template.yaml"),
            tipsy_config_dir=Path("config/tipsy"),
            log_dir=Path("vdyp_io/logs"),
            run_id="rebuild_test",
            with_patchworks=False,
            dry_run=False,
            patchworks_config=Path("config/patchworks.runtime.yaml"),
            baseline=Path("config/rebuild.baseline.json"),
            write_baseline=False,
            allowlist=Path("config/rebuild.allowlist.yaml"),
            instance_root=Path("instance-root"),
        )

    assert exc_info.value.exit_code == 1
    assert any("Fatal rebuild invariant regression detected" in msg for msg in messages)


def test_instance_validate_spec_reports_schema_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=Path("instance-root"),
            resolve_path=lambda value: Path("instance-root") / value,
        ),
    )
    monkeypatch.setattr(cli_main, "load_rebuild_spec", lambda _path: {})
    monkeypatch.setattr(
        cli_main,
        "validate_rebuild_spec_payload",
        lambda _payload: ["Missing required root key: steps"],
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.instance_validate_spec(
            spec=Path("config/rebuild.spec.yaml"),
            instance_root=Path("instance-root"),
        )

    assert exc_info.value.exit_code == 1
    assert any("Rebuild spec validation failed" in msg for msg in messages)
    assert any("Missing required root key: steps" in msg for msg in messages)


def test_instance_promote_evidence_writes_normalized_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    instance_root = tmp_path / "instance-root"
    log_dir = instance_root / "vdyp_io" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = log_dir / "instance_rebuild_report-r1.json"
    report_path.write_text(
        json.dumps(
            {
                "run_id": "r1",
                "failed": False,
                "invariant_results": [{"status": "pass"}, {"status": "warn"}],
                "metrics": {"baseline_diff_count": 0},
                "regression_gate": {
                    "step_failure": False,
                    "fatal_invariant_failure": False,
                    "unexpected_diff_regression": False,
                    "baseline_unexpected_diff_threshold": 0,
                    "baseline_unexpected_diff_count": 0,
                },
                "diagnostics": {
                    "account_surface": {
                        "species_count": 10,
                        "diagnosis": {"total_ok_species_empty_signature": False},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda value: instance_root / value,
        ),
    )

    cli_main.instance_promote_evidence(
        report=Path("vdyp_io/logs/instance_rebuild_report-r1.json"),
        output=Path("evidence/reference_rebuild_report.latest.json"),
        log_dir=Path("vdyp_io/logs"),
        max_warn_increase=None,
        max_baseline_diff_increase=None,
        instance_root=instance_root,
    )

    output_path = instance_root / "evidence/reference_rebuild_report.latest.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "r1"
    assert payload["status"] == "ok"
    assert payload["summary"]["invariant_pass_count"] == 1
    assert payload["summary"]["invariant_warn_count"] == 1
    assert (
        payload["summary"]["account_surface_total_ok_species_empty_signature"] is False
    )
    assert payload["summary"]["account_surface_species_count"] == 10
    assert any("Promoted rebuild evidence" in msg for msg in messages)


def test_instance_promote_evidence_emits_trend_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    instance_root = tmp_path / "instance-root"
    log_dir = instance_root / "vdyp_io" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_path = instance_root / "evidence/reference_rebuild_report.latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "summary": {
                    "invariant_warn_count": 0,
                    "baseline_diff_count": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    report_path = log_dir / "instance_rebuild_report-r2.json"
    report_path.write_text(
        json.dumps(
            {
                "run_id": "r2",
                "failed": False,
                "invariant_results": [{"status": "warn"}, {"status": "warn"}],
                "metrics": {"baseline_diff_count": 2},
                "regression_gate": {
                    "step_failure": False,
                    "fatal_invariant_failure": False,
                    "unexpected_diff_regression": False,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda value: instance_root / value,
        ),
    )

    cli_main.instance_promote_evidence(
        report=Path("vdyp_io/logs/instance_rebuild_report-r2.json"),
        output=Path("evidence/reference_rebuild_report.latest.json"),
        log_dir=Path("vdyp_io/logs"),
        max_warn_increase=0,
        max_baseline_diff_increase=0,
        instance_root=instance_root,
    )

    promoted = json.loads(output_path.read_text(encoding="utf-8"))
    assert promoted["trend_drift"]["warn_increase"] == 2
    assert promoted["trend_drift"]["baseline_diff_increase"] == 2
    assert len(promoted["trend_drift"]["warnings"]) == 2
    assert any("trend drift warning:" in msg for msg in messages)


def test_instance_refresh_reference_evidence_uses_reference_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_promote(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli_main, "instance_promote_evidence", _fake_promote)

    cli_main.instance_refresh_reference_evidence(
        report=None,
        reference_root=Path("r"),
        max_warn_increase=1,
        max_baseline_diff_increase=2,
    )

    assert captured["report"] is None
    assert captured["instance_root"] == Path("r")
    assert captured["output"] == Path("evidence/reference_rebuild_report.latest.json")
    assert captured["log_dir"] == Path("vdyp_io/logs")
    assert captured["max_warn_increase"] == 1
    assert captured["max_baseline_diff_increase"] == 2


def test_instance_account_surface_writes_summary_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    instance_root = tmp_path / "instance-root"
    tracks_dir = instance_root / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n"
        "_MANAGED_,x,product.Yield.managed.CW,1\n"
        "_MANAGED_,x,product.HarvestedVolume.managed.CW.CC,1\n"
        "_MANAGED_,x,feature.Seral.CWHvm_HW_FDC_L.mature,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda value: instance_root / value,
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_runtime_config",
        lambda _path: SimpleNamespace(matrix_output_dir=tracks_dir),
    )

    cli_main.instance_account_surface(
        config=Path("config/patchworks.runtime.windows.yaml"),
        output=Path("vdyp_io/logs/account_surface.json"),
        instance_root=instance_root,
    )

    payload = json.loads(
        (instance_root / "vdyp_io/logs/account_surface.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["species_count"] == 1
    assert payload["species_complete_count"] == 1
    assert payload["au_count"] == 1
    assert any("account surface summary" in msg for msg in messages)


def test_instance_account_surface_emits_total_ok_species_empty_diagnosis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n_MANAGED_,x,product.Yield.managed.Total,1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=tmp_path,
            resolve_path=lambda value: tmp_path / value,
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "load_patchworks_runtime_config",
        lambda _path: SimpleNamespace(matrix_output_dir=tracks_dir),
    )
    monkeypatch.setattr(
        cli_main,
        "summarize_account_surface",
        lambda **_kwargs: {
            "total_accounts": 2,
            "species_count": 0,
            "species_complete_count": 0,
            "au_count": 0,
            "species_missing_yield": [],
            "species_missing_harvest_cc": [],
            "diagnosis": {
                "total_ok_species_empty_signature": True,
                "recommended_next_checks": ["check-one", "check-two"],
            },
        },
    )

    cli_main.instance_account_surface(
        config=Path("config/patchworks.runtime.windows.yaml"),
        output=None,
        instance_root=tmp_path,
    )

    assert any("total OK, species-wise empty" in msg for msg in messages)
    assert any("check-one" in msg for msg in messages)


def test_collect_rebuild_artifact_references_filters_missing(
    tmp_path: Path,
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = "rtest"
    (log_dir / f"run_manifest-{run_id}.json").write_text("{}", encoding="utf-8")
    (log_dir / f"instance_rebuild_report-{run_id}.json").write_text(
        "{}",
        encoding="utf-8",
    )

    refs = cli_main._collect_rebuild_artifact_references(log_dir=log_dir, run_id=run_id)

    assert len(refs["run_manifests"]) == 1
    assert refs["patchworks_manifests"] == []
    assert refs["patchworks_logs"] == []
    assert len(refs["rebuild_reports"]) == 1


def test_prep_geospatial_preflight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_geospatial_preflight",
        lambda **_kwargs: SimpleNamespace(
            os_family="linux",
            install_hint="linux hint",
            gdal_version="3.8.5",
            warnings=(),
            errors=(),
            ok=True,
        ),
    )

    cli_main.prep_geospatial_preflight(
        strict_warnings=False, skip_shapefile_smoke=False
    )

    assert any("Geospatial preflight passed" in msg for msg in messages)
    assert any("gdal_version=3.8.5" in msg for msg in messages)


def test_prep_geospatial_preflight_fails_on_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_geospatial_preflight",
        lambda **_kwargs: SimpleNamespace(
            os_family="windows",
            install_hint="windows hint",
            gdal_version=None,
            warnings=(),
            errors=("missing fiona",),
            ok=False,
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.prep_geospatial_preflight(
            strict_warnings=False,
            skip_shapefile_smoke=False,
        )

    assert exc_info.value.exit_code == 1
    assert any("missing fiona" in msg for msg in messages)


def test_prep_geospatial_preflight_strict_warnings_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "run_geospatial_preflight",
        lambda **_kwargs: SimpleNamespace(
            os_family="linux",
            install_hint="linux hint",
            gdal_version="3.8.5",
            warnings=("gdal visibility warning",),
            errors=(),
            ok=True,
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.prep_geospatial_preflight(
            strict_warnings=True,
            skip_shapefile_smoke=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("gdal visibility warning" in msg for msg in messages)


def test_export_dual_runs_patchworks_and_woodstock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir()
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda p: instance_root / p,
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "export_patchworks_package",
        lambda **_kwargs: SimpleNamespace(
            tsa_list=["29"],
            curve_count=10,
            forestmodel_xml_path=instance_root / "output/patchworks/forestmodel.xml",
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "export_woodstock_package",
        lambda **_kwargs: SimpleNamespace(
            tsa_list=["29"],
            yield_rows=20,
            yields_csv_path=instance_root / "output/woodstock/woodstock_yields.csv",
        ),
    )
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    cli_main.export_dual(
        tsa=["29"],
        bundle_dir=Path("data/model_input_bundle"),
        checkpoint=Path("data/ria_vri_vclr1p_checkpoint7.feather"),
        patchworks_output_dir=Path("output/patchworks"),
        woodstock_output_dir=Path("output/woodstock"),
        start_year=2026,
        horizon_years=300,
        cc_min_age=0,
        cc_max_age=1000,
        cc_transition_ifm=None,
        fragments_crs="EPSG:3005",
        ifm_source_col=None,
        ifm_threshold=None,
        ifm_target_managed_share=None,
        seral_stage_config=None,
        with_ws3_smoke=False,
        ws3_command=None,
        ws3_workdir=None,
        ws3_report=Path("evidence/ws3_smoke_report.latest.json"),
        ws3_require_command=False,
        ws3_timeout_seconds=600,
        ws3_repo_path=None,
        ws3_builtin_smoke=False,
        ws3_bridge_dir=None,
        instance_root=instance_root,
    )

    assert any("dual export completed" in msg for msg in messages)


def test_instance_ws3_smoke_fails_on_failed_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir()
    monkeypatch.setattr(
        cli_main,
        "_resolve_cli_instance_context",
        lambda **_kwargs: SimpleNamespace(
            root=instance_root,
            resolve_path=lambda p: instance_root / p,
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "run_ws3_smoke",
        lambda **_kwargs: SimpleNamespace(
            status="failed",
            yields_rows=0,
            areas_rows=0,
            actions_rows=0,
            transitions_rows=0,
            message="failed smoke",
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.instance_ws3_smoke(
            woodstock_dir=Path("output/woodstock"),
            output=Path("evidence/ws3_smoke_report.latest.json"),
            ws3_command=None,
            ws3_workdir=None,
            require_command=False,
            timeout_seconds=600,
            ws3_repo_path=None,
            builtin_model_smoke=True,
            ws3_bridge_dir=None,
            instance_root=instance_root,
        )
    assert exc_info.value.exit_code == 1
