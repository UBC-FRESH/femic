from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from femic.patchworks_runtime import (
    PatchworksConfigError,
    build_patchworks_blocks_dataset,
    build_appchooser_command_string,
    build_matrix_builder_command_string,
    infer_patchworks_model_dir,
    load_patchworks_runtime_config,
    parse_license_server,
    run_patchworks_command,
    run_patchworks_preflight,
    to_wine_windows_path,
)


def _write_runtime_config(tmp_path: Path) -> Path:
    cfg = tmp_path / "patchworks.runtime.yaml"
    cfg.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: patchworks/patchworks.jar",
                "  wine_prefix: null",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "  spshome: Z:\\Patchworks",
                "matrix_builder:",
                "  fragments_path: data/fragments.dbf",
                "  output_dir: output/tracks",
                "  forestmodel_xml_path: output/forestmodel.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return cfg


def test_load_patchworks_runtime_config_resolves_relative_paths(tmp_path: Path) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    assert cfg.jar_path == (tmp_path / "patchworks/patchworks.jar").resolve()
    assert cfg.fragments_path == (tmp_path / "data/fragments.dbf").resolve()
    assert cfg.matrix_output_dir == (tmp_path / "output/tracks").resolve()
    assert cfg.forestmodel_xml_path == (tmp_path / "output/forestmodel.xml").resolve()
    assert cfg.accounts_exclude_regex == ()


def test_load_patchworks_runtime_config_handles_parent_relative_paths(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    cfg_dir = repo_root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "reference/Patchworks").mkdir(parents=True, exist_ok=True)
    (repo_root / "reference/Patchworks/patchworks.jar").touch()
    (repo_root / "output/patchworks_k3z_validated/fragments").mkdir(
        parents=True, exist_ok=True
    )
    (repo_root / "output/patchworks_k3z_validated/fragments/fragments.dbf").touch()
    (repo_root / "output/patchworks_k3z_validated/forestmodel.xml").touch()

    cfg_path = cfg_dir / "patchworks.runtime.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: ../reference/Patchworks/patchworks.jar",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "  spshome: Z:\\Patchworks",
                "matrix_builder:",
                "  fragments_path: ../output/patchworks_k3z_validated/fragments/fragments.dbf",
                "  output_dir: ../output/patchworks_k3z_validated/tracks",
                "  forestmodel_xml_path: ../output/patchworks_k3z_validated/forestmodel.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_patchworks_runtime_config(cfg_path)
    assert cfg.jar_path == (repo_root / "reference/Patchworks/patchworks.jar").resolve()
    assert (
        cfg.fragments_path
        == (
            repo_root / "output/patchworks_k3z_validated/fragments/fragments.dbf"
        ).resolve()
    )
    assert cfg.accounts_exclude_regex == ()


def test_load_patchworks_runtime_config_parses_accounts_exclude_regex(
    tmp_path: Path,
) -> None:
    cfg_path = tmp_path / "patchworks.runtime.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: patchworks/patchworks.jar",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "  spshome: Z:\\Patchworks",
                "matrix_builder:",
                "  fragments_path: data/fragments.dbf",
                "  output_dir: output/tracks",
                "  forestmodel_xml_path: output/forestmodel.xml",
                "  accounts_exclude_regex:",
                '    - "\\\\.PL(\\\\.|$)"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_patchworks_runtime_config(cfg_path)
    assert cfg.accounts_exclude_regex == ("\\.PL(\\.|$)",)


def test_parse_license_server_requires_user_host_format() -> None:
    assert parse_license_server("sps_user@auth.spatial.ca") == (
        "sps_user",
        "auth.spatial.ca",
    )
    with pytest.raises(PatchworksConfigError):
        parse_license_server("auth.spatial.ca")


def test_load_patchworks_runtime_config_uses_env_when_license_value_null(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = tmp_path / "patchworks.runtime.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: patchworks/patchworks.jar",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: null",
                "  spshome: Z:\\Patchworks",
                "matrix_builder:",
                "  fragments_path: data/fragments.dbf",
                "  output_dir: output/tracks",
                "  forestmodel_xml_path: output/forestmodel.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPS_LICENSE_SERVER", "envuser@auth.spatial.ca")
    cfg = load_patchworks_runtime_config(cfg_path)
    assert cfg.license_value == "envuser@auth.spatial.ca"


def test_to_wine_windows_path_maps_posix(tmp_path: Path) -> None:
    path = (tmp_path / "a b/c.txt").resolve()
    path.parent.mkdir(parents=True)
    path.touch()
    mapped = to_wine_windows_path(path)
    if path.drive:
        assert mapped.startswith(path.drive)
    else:
        assert mapped.startswith("Z:\\")
    assert "a b" in mapped


def test_build_matrix_builder_command_string_contains_expected_args(
    tmp_path: Path,
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cmd = build_matrix_builder_command_string(cfg)
    assert "ca.spatial.tracks.builder.Process" in cmd
    assert "fragments.dbf" in cmd
    assert "forestmodel.xml" in cmd


def test_build_appchooser_command_string_points_to_patchworks_jar(
    tmp_path: Path,
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cmd = build_appchooser_command_string(cfg)
    assert 'java "-Djava.library.path=' in cmd
    assert "-jar patchworks.jar" in cmd


def test_run_patchworks_preflight_reports_missing_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)
    monkeypatch.setattr("femic.patchworks_runtime.find_wine_executable", lambda: None)

    result = run_patchworks_preflight(config=cfg)
    assert not result.ok
    assert any("wine64/wine not found" in msg for msg in result.errors)
    assert any("Patchworks jar not found" in msg for msg in result.errors)


def test_load_patchworks_runtime_config_requires_spshome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SPSHOME", raising=False)
    cfg = tmp_path / "patchworks.runtime.yaml"
    cfg.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: patchworks/patchworks.jar",
                "  wine_prefix: null",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "matrix_builder:",
                "  fragments_path: data/fragments.dbf",
                "  output_dir: output/tracks",
                "  forestmodel_xml_path: output/forestmodel.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(PatchworksConfigError, match="Missing Patchworks install home"):
        load_patchworks_runtime_config(cfg)


def test_load_patchworks_runtime_config_uses_env_spshome_when_field_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPSHOME", "Z:\\PatchworksEnv")
    cfg = tmp_path / "patchworks.runtime.yaml"
    cfg.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: patchworks/patchworks.jar",
                "  wine_prefix: null",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "matrix_builder:",
                "  fragments_path: data/fragments.dbf",
                "  output_dir: output/tracks",
                "  forestmodel_xml_path: output/forestmodel.xml",
                "",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_patchworks_runtime_config(cfg)
    assert loaded.spshome == "Z:\\PatchworksEnv"
    command = build_matrix_builder_command_string(loaded)
    assert 'set "SPSHOME=Z:\\PatchworksEnv"' in command


def test_run_patchworks_command_writes_logs_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.matrix_output_dir / "tracks.bin").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)

    observed_env: dict[str, str] = {}

    def _fake_subprocess_run(*_args, **_kwargs):
        nonlocal observed_env
        observed_env = dict(_kwargs.get("env", {}))
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("femic.patchworks_runtime.subprocess.run", _fake_subprocess_run)

    result = run_patchworks_command(
        config=cfg,
        interactive=False,
        log_dir=tmp_path / "logs",
        run_id="pwtest",
    )

    assert result.returncode == 0
    assert result.stdout_log_path.exists()
    assert result.stderr_log_path.exists()
    assert result.manifest_path.exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "pwtest"
    assert manifest["returncode"] == 0
    assert "ca.spatial.tracks.builder.Process" in manifest["command_string"]
    assert manifest["runtime"]["spshome"] == "Z:\\Patchworks"
    assert manifest["runtime"]["host_mode"] == "wine"
    assert manifest["runtime"]["launcher_executable"] == "/usr/bin/wine64"
    assert observed_env["SPS_LICENSE_SERVER"] == "sps_user@auth.spatial.ca"
    assert observed_env["SPSHOME"] == "Z:\\Patchworks"
    assert not result.failures


def test_run_patchworks_command_promotes_protoaccounts_and_backs_up_accounts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.matrix_output_dir / "protoaccounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n_ALL_,a,a,1\n",
        encoding="utf-8",
    )
    (cfg.matrix_output_dir / "accounts.csv").write_text(
        "GROUP,ATTRIBUTE,ACCOUNT,SUM\n_ALL_,legacy,legacy,1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)
    monkeypatch.setattr(
        "femic.patchworks_runtime.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    result = run_patchworks_command(
        config=cfg,
        interactive=False,
        log_dir=tmp_path / "logs",
        run_id="pwsync",
    )

    assert result.returncode == 0
    accounts_path = cfg.matrix_output_dir / "accounts.csv"
    assert accounts_path.read_text(encoding="utf-8").endswith("_ALL_,a,a,1\n")
    backups = sorted(cfg.matrix_output_dir.glob("accounts_backup_*.csv"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8").endswith("_ALL_,legacy,legacy,1\n")

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["accounts_sync"]["status"] == "synced"
    assert manifest["accounts_sync"]["backup_path"] == str(backups[0])
    assert manifest["accounts_sync"]["excluded_row_count"] == 0


def test_run_patchworks_command_reports_missing_protoaccounts_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.matrix_output_dir / "tracks.csv").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)
    monkeypatch.setattr(
        "femic.patchworks_runtime.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    result = run_patchworks_command(
        config=cfg,
        interactive=False,
        log_dir=tmp_path / "logs",
        run_id="pwnoproto",
    )
    assert result.returncode == 0
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["accounts_sync"]["status"] == "skipped_missing_protoaccounts"
    assert manifest["accounts_sync"]["accounts_path"] is None
    assert manifest["accounts_sync"]["excluded_row_count"] == 0


def test_run_patchworks_command_excludes_accounts_by_regex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8")
        + '\n  accounts_exclude_regex:\n    - "\\\\.PL(\\\\.|$)"\n',
        encoding="utf-8",
    )
    cfg = load_patchworks_runtime_config(cfg_path)

    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.matrix_output_dir / "protoaccounts.csv").write_text(
        (
            "GROUP,ATTRIBUTE,ACCOUNT,SUM\n"
            "_MANAGED_,product.Yield.managed.PL,product.Yield.managed.PL,1\n"
            "_MANAGED_,product.Yield.managed.PLC,product.Yield.managed.PLC,1\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)
    monkeypatch.setattr(
        "femic.patchworks_runtime.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="ok", stderr=""),
    )

    result = run_patchworks_command(
        config=cfg,
        interactive=False,
        log_dir=tmp_path / "logs",
        run_id="pwfilter",
    )

    assert result.returncode == 0
    accounts_text = (cfg.matrix_output_dir / "accounts.csv").read_text(encoding="utf-8")
    assert "product.Yield.managed.PL,product.Yield.managed.PL" not in accounts_text
    assert "product.Yield.managed.PLC,product.Yield.managed.PLC" in accounts_text

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["accounts_sync"]["excluded_patterns"] == ["\\.PL(\\.|$)"]
    assert manifest["accounts_sync"]["excluded_row_count"] == 1


def test_run_patchworks_command_fails_on_fatal_stderr_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)

    def _fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="Not licensed or no connection to license server",
        )

    monkeypatch.setattr("femic.patchworks_runtime.subprocess.run", _fake_subprocess_run)

    result = run_patchworks_command(
        config=cfg, interactive=False, log_dir=tmp_path / "logs", run_id="pwfatal"
    )
    assert result.returncode == 1
    assert any("fatal stderr signatures detected" in x for x in result.failures)


def test_run_patchworks_command_treats_artifact_complete_as_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    (cfg.matrix_output_dir / "tracks.csv").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(
        "femic.patchworks_runtime.find_wine_executable", lambda: "/usr/bin/wine64"
    )
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: False)

    def _fake_subprocess_run(args, **_kwargs):
        if list(args)[:4] == ["/usr/bin/wine64", "cmd", "/c", "java -version"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=123, stdout="", stderr="")

    monkeypatch.setattr("femic.patchworks_runtime.subprocess.run", _fake_subprocess_run)

    result = run_patchworks_command(
        config=cfg, interactive=False, log_dir=tmp_path / "logs", run_id="pwdone"
    )
    assert result.returncode == 0


def test_run_patchworks_preflight_windows_uses_cmd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()

    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: True)
    monkeypatch.setattr(
        "femic.patchworks_runtime.shutil_which", lambda name: "java.exe"
    )

    observed_args: list[str] = []

    def _fake_subprocess_run(args, **_kwargs):
        nonlocal observed_args
        observed_args = list(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("femic.patchworks_runtime.subprocess.run", _fake_subprocess_run)

    result = run_patchworks_preflight(config=cfg)
    assert result.ok
    assert result.host_mode == "windows"
    assert result.launcher_executable == "java.exe"
    assert observed_args[:2] == ["java.exe", "-version"]


def test_run_patchworks_preflight_warns_when_env_spshome_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    cfg.jar_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.jar_path.touch()
    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()

    monkeypatch.delenv("SPSHOME", raising=False)
    monkeypatch.setattr("femic.patchworks_runtime.is_windows_host", lambda: True)
    monkeypatch.setattr(
        "femic.patchworks_runtime.shutil_which", lambda name: "java.exe"
    )
    monkeypatch.setattr(
        "femic.patchworks_runtime.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    result = run_patchworks_preflight(config=cfg)
    assert result.ok
    assert any(
        "SPSHOME environment variable is not set" in msg for msg in result.warnings
    )


def test_infer_patchworks_model_dir_uses_runtime_layout(tmp_path: Path) -> None:
    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)
    expected_root = tmp_path.resolve()
    assert infer_patchworks_model_dir(cfg) == expected_root


def test_infer_patchworks_model_dir_prefers_tracks_yield_pair(tmp_path: Path) -> None:
    cfg_path = tmp_path / "runtime.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "patchworks:",
                "  jar_path: C:/Patchworks/patchworks.jar",
                "  license_env: SPS_LICENSE_SERVER",
                "  license_value: sps_user@auth.spatial.ca",
                "  spshome: C:/Patchworks",
                "matrix_builder:",
                "  fragments_path: output/fragments/fragments.dbf",
                "  output_dir: models/k3z_patchworks_model/tracks",
                "  forestmodel_xml_path: models/k3z_patchworks_model/yield/forestmodel.xml",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_patchworks_runtime_config(cfg_path)
    expected_root = (tmp_path / "models" / "k3z_patchworks_model").resolve()
    assert infer_patchworks_model_dir(cfg) == expected_root


def test_build_patchworks_blocks_dataset_dispatches_patchworks_raster_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gpd = pytest.importorskip("geopandas")
    shapely_geometry = pytest.importorskip("shapely.geometry")

    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()

    fragments = gpd.GeoDataFrame(
        {
            "FRAGMENT_I": [5001],
            "FEATURE_ID": [101],
            "BLOCK": [1],
            "AREA_HA": [1.0],
            "F_AGE": [60],
            "AU": [1],
            "IFM": ["managed"],
            "TSA": ["k3z"],
        },
        geometry=[shapely_geometry.box(0.0, 0.0, 10.0, 10.0)],
        crs="EPSG:3005",
    )
    fragments_path = cfg.fragments_path.with_suffix(".shp")
    fragments.to_file(fragments_path, index=False)

    called: dict[str, object] = {}

    def _fake_raster_topology(**kwargs):
        called.update(kwargs)
        topology_path = kwargs["topology_csv_path"]
        topology_path.write_text(
            "BLOCK1,BLOCK2,DISTANCE,LENGTH\n-9999,1,0.0,10.0\n",
            encoding="utf-8",
        )
        return 1

    monkeypatch.setattr(
        "femic.patchworks_runtime._run_patchworks_raster_topology",
        _fake_raster_topology,
    )

    result = build_patchworks_blocks_dataset(
        config=cfg,
        topology_radius_m=200.0,
        build_topology=True,
        topology_backend="patchworks-raster",
    )

    assert result.topology_csv_path is not None
    assert result.topology_csv_path.exists()
    assert result.topology_edge_count == 1
    assert called["config"] == cfg
    assert called["fragments_shapefile_path"] == fragments_path.resolve()
    assert called["topology_id_field"] == "FRAGMENT_I"
    assert called["topology_radius_m"] == 200.0


def test_build_patchworks_blocks_dataset_writes_blocks_and_topology(
    tmp_path: Path,
) -> None:
    gpd = pytest.importorskip("geopandas")
    shapely_geometry = pytest.importorskip("shapely.geometry")

    cfg_path = _write_runtime_config(tmp_path)
    cfg = load_patchworks_runtime_config(cfg_path)

    cfg.fragments_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.fragments_path.touch()
    cfg.matrix_output_dir.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.parent.mkdir(parents=True, exist_ok=True)
    cfg.forestmodel_xml_path.touch()

    polygons = [
        shapely_geometry.box(0.0, 0.0, 10.0, 10.0),
        shapely_geometry.box(10.0, 0.0, 20.0, 10.0),
    ]
    fragments = gpd.GeoDataFrame(
        {
            "FEATURE_ID": [101, 102],
            "BLOCK": [1, 2],
            "AREA_HA": [1.0, 1.0],
            "F_AGE": [60, 70],
            "AU": [1, 1],
            "IFM": ["managed", "unmanaged"],
            "TSA": ["k3z", "k3z"],
        },
        geometry=polygons,
        crs="EPSG:3005",
    )
    fragments_path = cfg.fragments_path.with_suffix(".shp")
    fragments.to_file(fragments_path, index=False)

    result = build_patchworks_blocks_dataset(
        config=cfg,
        topology_radius_m=200.0,
        build_topology=True,
    )

    assert result.blocks_shapefile_path.exists()
    assert result.topology_csv_path is not None
    assert result.topology_csv_path.exists()
    assert result.stand_id_field == "BLOCK"
    assert result.block_count == 2

    blocks_gdf = gpd.read_file(result.blocks_shapefile_path)
    assert set(blocks_gdf["BLOCK"].astype(int).tolist()) == {1, 2}

    topology_text = result.topology_csv_path.read_text(encoding="utf-8")
    assert "BLOCK1,BLOCK2,DISTANCE,LENGTH" in topology_text
    assert "-9999,1" in topology_text
    assert "-9999,2" in topology_text
    assert "1,2,0.000" in topology_text
