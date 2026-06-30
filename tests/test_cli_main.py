from __future__ import annotations

import builtins
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
import yaml
from typer.testing import CliRunner

from femic.arcgis_review import ArcgisReviewProjectResult
from femic.glb import GlbBuildResult, GlbStashResult
from femic import bcdc_catalog
from femic import tsr_catalog
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


def test_doc_figures_help_renders() -> None:
    runner = CliRunner()

    doc_result = runner.invoke(cli_main.app, ["doc", "--help"])
    figures_result = runner.invoke(cli_main.app, ["doc", "figures", "--help"])
    preflight_result = runner.invoke(
        cli_main.app, ["doc", "figures", "preflight", "--help"]
    )

    assert doc_result.exit_code == 0, doc_result.output
    assert figures_result.exit_code == 0, figures_result.output
    assert preflight_result.exit_code == 0, preflight_result.output
    assert "figures" in doc_result.stdout
    assert "preflight" in figures_result.stdout
    assert "prepare-corpus" in figures_result.stdout
    assert "register-table" in figures_result.stdout
    assert "Check optional figrecover dependencies" in preflight_result.stdout


def test_doc_figures_preflight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli_main,
        "_module_import_status",
        lambda _module_name: (True, None),
    )
    monkeypatch.setattr(cli_main, "_package_version", lambda _package_name: "0.1.0a1")

    result = CliRunner().invoke(cli_main.app, ["doc", "figures", "preflight"])

    assert result.exit_code == 0, result.output
    assert "figrecover: ok version=0.1.0a1" in result.stdout
    assert "pymupdf: ok" in result.stdout
    assert "pypdf: ok" in result.stdout
    assert "opencv: ok" in result.stdout
    assert "scikit-image: ok" in result.stdout
    assert "httpx: ok" in result.stdout
    assert "Figure-recovery preflight passed" in result.stdout


def test_doc_figures_preflight_fails_when_figrecover_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_import_status(module_name: str) -> tuple[bool, str | None]:
        if module_name == "figrecover":
            return False, "figrecover"
        return True, None

    monkeypatch.setattr(cli_main, "_module_import_status", _fake_import_status)

    result = CliRunner().invoke(cli_main.app, ["doc", "figures", "preflight"])

    assert result.exit_code == 1
    assert "figrecover: missing (figrecover)" in result.stdout
    assert f"install_hint: {cli_main.FIGRECOVER_INSTALL_HINT}" in result.stdout


def test_doc_figures_preflight_reports_missing_optional_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_import_status(module_name: str) -> tuple[bool, str | None]:
        if module_name == "cv2":
            return False, "cv2"
        return True, None

    monkeypatch.setattr(cli_main, "_module_import_status", _fake_import_status)
    monkeypatch.setattr(cli_main, "_package_version", lambda _package_name: "0.1.0a1")

    result = CliRunner().invoke(cli_main.app, ["doc", "figures", "preflight"])

    assert result.exit_code == 1
    assert "figrecover: ok version=0.1.0a1" in result.stdout
    assert "opencv: missing (cv2)" in result.stdout
    assert f"install_hint: {cli_main.FIGRECOVER_INSTALL_HINT}" in result.stdout


def test_doc_figures_prepare_corpus_writes_source_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF synthetic placeholder")

    def _fake_render_pdf_pages(**kwargs: object) -> list[dict[str, object]]:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        page_path = output_dir / "source-p0001.png"
        page_path.write_text("page", encoding="utf-8")
        return [
            {
                "document_id": kwargs["document_id"],
                "page_number": 1,
                "image_path": str(page_path),
                "source_pdf": str(kwargs["pdf_path"]),
                "width_px": 100,
                "height_px": 100,
                "dpi": kwargs["dpi"],
                "renderer": "test-renderer",
                "metadata": {},
            }
        ]

    monkeypatch.setattr(
        cli_main,
        "_render_document_figure_pdf_pages",
        _fake_render_pdf_pages,
    )
    monkeypatch.setattr(cli_main, "_package_version", lambda _package_name: "0.1.0a1")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "prepare-corpus",
            "test-corpus",
            "--pdf",
            str(pdf_path),
            "--output-root",
            str(tmp_path / "corpus"),
            "--dpi",
            "72",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"corpus_id": "test-corpus"' in result.stdout
    source_manifest = tmp_path / "corpus" / "source_manifest.yaml"
    payload = yaml.safe_load(source_manifest.read_text(encoding="utf-8"))
    assert payload["corpus_id"] == "test-corpus"
    assert payload["figrecover_version"] == "0.1.0a1"
    assert payload["sources"][0]["rendered_page_count"] == 1
    assert (tmp_path / "corpus" / "pages" / "source-p0001.png").exists()


def test_doc_figures_prepare_corpus_requires_input(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "prepare-corpus",
            "test-corpus",
            "--output-root",
            str(tmp_path / "corpus"),
        ],
    )

    assert result.exit_code == 1
    assert "provide at least one --pdf" in result.stdout


def test_doc_figures_register_table_writes_review_manifest(tmp_path: Path) -> None:
    table_path = tmp_path / "recovered.csv"
    table_path.write_text("x,y\n1,2\n", encoding="utf-8")
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text(
        '{"x_axis": "linear", "y_axis": "linear"}\n', encoding="utf-8"
    )
    extraction_parameters_path = tmp_path / "params.json"
    extraction_parameters_path.write_text('{"mask": "blue"}\n', encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "register-table",
            "test-corpus",
            str(table_path),
            "--document-title",
            "Synthetic Management Plan",
            "--page",
            "12",
            "--figure-id",
            "Figure 1",
            "--series-name",
            "base case",
            "--visual-selection-rule",
            "blue line mask",
            "--calibration-spec",
            str(calibration_path),
            "--extraction-method",
            "deterministic_line_mask",
            "--extraction-parameters",
            str(extraction_parameters_path),
            "--source-url",
            "https://example.test/source.pdf",
            "--review-status",
            "accepted_for_comparison",
            "--downstream-use",
            "comparison_evidence",
            "--reviewer",
            "tester",
            "--figrecover-version",
            "0.1.0a1",
            "--output-root",
            str(tmp_path / "corpus"),
        ],
    )

    assert result.exit_code == 0, result.output
    review_manifest = tmp_path / "corpus" / "review_manifest.jsonl"
    sidecar = tmp_path / "corpus" / "recovered" / "Figure-1-provenance.json"
    manifest_payload = json.loads(review_manifest.read_text(encoding="utf-8"))
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert manifest_payload["review_status"] == "accepted_for_comparison"
    assert manifest_payload["reviewer"] == "tester"
    assert manifest_payload["output_checksum"] == sidecar_payload["output_checksum"]
    assert '"downstream_use_classification": "comparison_evidence"' in result.stdout


def test_doc_figures_register_table_rejects_unreviewed_model_input(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "recovered.csv"
    table_path.write_text("x,y\n1,2\n", encoding="utf-8")
    calibration_path = tmp_path / "calibration.json"
    calibration_path.write_text('{"x_axis": "linear"}\n', encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "register-table",
            "test-corpus",
            str(table_path),
            "--document-title",
            "Synthetic Management Plan",
            "--page",
            "12",
            "--figure-id",
            "Figure 1",
            "--series-name",
            "base case",
            "--visual-selection-rule",
            "blue line mask",
            "--calibration-spec",
            str(calibration_path),
            "--extraction-method",
            "deterministic_line_mask",
            "--source-url",
            "https://example.test/source.pdf",
            "--review-status",
            "accepted_for_model_input",
            "--downstream-use",
            "model_input",
            "--output-root",
            str(tmp_path / "corpus"),
        ],
    )

    assert result.exit_code == 1
    assert "reviewer is required" in result.stdout


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


def test_prep_arcgis_review_project_prints_emitted_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    project_path = instance_root / "workbench" / "arcgis_review" / "tsa29_review.aprx"
    manifest_path = (
        instance_root / "workbench" / "arcgis_review" / "tsa29_review_manifest.json"
    )
    monkeypatch.setattr(
        cli_main,
        "build_arcgis_review_project",
        lambda *, instance_root, output_dir, project_name: ArcgisReviewProjectResult(
            project_path=project_path,
            manifest_path=manifest_path,
            layer_count=3,
            skipped_notes=(),
        ),
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "arcgis-review-project",
            "--instance-root",
            str(instance_root),
        ],
    )

    assert result.exit_code == 0
    normalized_stdout = result.stdout.replace("\n", "")
    assert "ArcGIS review project emitted" in result.stdout
    assert "project_path=" in normalized_stdout
    assert str(project_path.name) in normalized_stdout
    assert "manifest_path=" in normalized_stdout
    assert str(manifest_path.name) in normalized_stdout
    assert "layer_count=3" in normalized_stdout


def test_prep_arcgis_review_project_surfaces_missing_arcgis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        cli_main,
        "build_arcgis_review_project",
        lambda *, instance_root, output_dir, project_name: (_ for _ in ()).throw(
            FileNotFoundError("ArcGIS Pro Python not found.")
        ),
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "arcgis-review-project",
            "--instance-root",
            str(instance_root),
        ],
    )

    assert result.exit_code == 1
    assert "ArcGIS review-project emit failed" in result.stdout
    assert "ArcGIS Pro Python not found." in result.stdout


def test_prep_glb_build_prints_emitted_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    output_dir = instance_root / "runtime" / "logs" / "glb_build" / "tsa29"
    clipped_glb_gdb_path = output_dir / "clipped_glb.gdb"
    summary_json_path = output_dir / "glb_summary.json"
    summary_markdown_path = output_dir / "glb_summary.md"
    monkeypatch.setattr(
        cli_main,
        "build_tsa_raw_glb",
        lambda **_: GlbBuildResult(
            glb_source_mode="raw_build",
            tsa_selector="29",
            tsa_number="29",
            tsa_name="Williams Lake TSA",
            source_zip_path=tmp_path / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip",
            boundary_source_path=tmp_path / "tsa.gpkg",
            output_dir=output_dir,
            clipped_glb_gdb_path=clipped_glb_gdb_path,
            clipped_glb_feature_class="tsa_glb_vri_2024",
            summary_json_path=summary_json_path,
            summary_markdown_path=summary_markdown_path,
            feature_count=317735,
            clipped_area_ha=4933664.212,
            boundary_area_ha=4933664.215,
            area_delta_ha=-0.003,
            stash_result=GlbStashResult(
                attempted=True,
                status="stashed",
                archive_path=output_dir / "tsa29_glb_vri_2024.gdb.zip",
                summary_path=output_dir / "tsa29_glb_vri_2024.summary.json",
            ),
        ),
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "glb-build",
            "--instance-root",
            str(instance_root),
            "--tsa",
            "29",
        ],
    )

    assert result.exit_code == 0
    normalized_stdout = result.stdout.replace("\n", "")
    assert "Raw-source GLB emitted" in result.stdout
    assert "glb_source_mode=raw_build" in normalized_stdout
    assert "tsa_number=29" in normalized_stdout
    assert "clipped_glb_gdb_path=" in normalized_stdout
    assert "summary_json_path=" in normalized_stdout
    assert "feature_count=317735" in normalized_stdout
    assert "public_data_glb_stash_status=stashed" in normalized_stdout


def test_prep_glb_build_surfaces_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        cli_main,
        "build_tsa_raw_glb",
        lambda **_: (_ for _ in ()).throw(
            FileNotFoundError("Raw 2024 VRI zip not found.")
        ),
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "glb-build",
            "--instance-root",
            str(instance_root),
            "--tsa",
            "29",
        ],
    )

    assert result.exit_code == 1
    assert "GLB build failed" in result.stdout
    assert "Raw 2024 VRI zip not found." in result.stdout


def test_prep_glb_build_resolves_explicit_output_dir_from_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    repo_relative_output = Path(
        "external/femic-tsa29-instance/runtime/logs/glb_build/test"
    )
    captured: dict[str, Path | None] = {}

    def _fake_build(**kwargs: object) -> GlbBuildResult:
        captured["output_dir"] = kwargs.get("output_dir")  # type: ignore[assignment]
        return GlbBuildResult(
            glb_source_mode="raw_build",
            tsa_selector="29",
            tsa_number="29",
            tsa_name="Williams Lake TSA",
            source_zip_path=tmp_path / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip",
            boundary_source_path=tmp_path / "tsa.gpkg",
            output_dir=Path(kwargs["output_dir"]),  # type: ignore[index]
            clipped_glb_gdb_path=Path(kwargs["output_dir"]) / "clipped_glb.gdb",  # type: ignore[index]
            clipped_glb_feature_class="tsa_glb_vri_2024",
            summary_json_path=Path(kwargs["output_dir"]) / "glb_summary.json",  # type: ignore[index]
            summary_markdown_path=Path(kwargs["output_dir"]) / "glb_summary.md",  # type: ignore[index]
            feature_count=1,
            clipped_area_ha=1.0,
            boundary_area_ha=1.0,
            area_delta_ha=0.0,
            stash_result=GlbStashResult(False, "disabled", None, None),
        )

    monkeypatch.setattr(cli_main, "build_tsa_raw_glb", _fake_build)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "glb-build",
            "--instance-root",
            str(instance_root),
            "--tsa",
            "29",
            "--output-dir",
            str(repo_relative_output),
        ],
    )

    assert result.exit_code == 0
    assert captured["output_dir"] == repo_relative_output.resolve()


def test_prep_glb_build_wires_stash_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    instance_root.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def _fake_build(**kwargs: object) -> GlbBuildResult:
        captured.update(kwargs)
        output_dir = tmp_path / "out"
        return GlbBuildResult(
            glb_source_mode="raw_build",
            tsa_selector="29",
            tsa_number="29",
            tsa_name="Williams Lake TSA",
            source_zip_path=tmp_path / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip",
            boundary_source_path=tmp_path / "tsa.gpkg",
            output_dir=output_dir,
            clipped_glb_gdb_path=output_dir / "clipped_glb.gdb",
            clipped_glb_feature_class="tsa_glb_vri_2024",
            summary_json_path=output_dir / "glb_summary.json",
            summary_markdown_path=output_dir / "glb_summary.md",
            feature_count=1,
            clipped_area_ha=1.0,
            boundary_area_ha=1.0,
            area_delta_ha=0.0,
            stash_result=GlbStashResult(False, "disabled", None, None),
        )

    monkeypatch.setattr(cli_main, "build_tsa_raw_glb", _fake_build)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "prep",
            "glb-build",
            "--instance-root",
            str(instance_root),
            "--tsa",
            "29",
            "--force-rebuild-glb",
            "--no-stash-public-data-glb",
            "--force-update-public-data-glb",
        ],
    )

    assert result.exit_code == 0
    assert captured["force_rebuild_glb"] is True
    assert captured["stash_public_data_glb"] is False
    assert captured["force_update_public_data_glb"] is True


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
    monkeypatch.setattr(
        cli_main, "_resolve_windows_user_local_path", lambda _path: None
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {key: "" for key in cli_main.WINDOWS_ARBUTUS_REQUIRED_ENV_KEYS},
    )
    monkeypatch.setattr(
        cli_main,
        "_validate_windows_public_data_tsa_boundary",
        lambda tsa_boundaries_path: [],
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
    monkeypatch.setattr(
        cli_main, "_resolve_windows_user_local_path", lambda _path: None
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {key: "" for key in cli_main.WINDOWS_ARBUTUS_REQUIRED_ENV_KEYS},
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert warnings == []
    assert any("DataLad status check failed" in msg for msg in errors)
    assert len(calls) == 2


def test_validate_windows_arbutus_env_file_reports_quoted_credentials(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "arbutus.env"
    env_file.write_text(
        "\n".join(
            [
                "AWS_ACCESS_KEY_ID='quoted-key'",
                "AWS_SECRET_ACCESS_KEY='quoted-secret'",
                "AWS_DEFAULT_REGION=ca-west-1",
                "S3_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca",
            ]
        ),
        encoding="utf-8",
    )

    errors = cli_main._validate_windows_arbutus_env_file(env_file)

    assert any(
        "AWS_ACCESS_KEY_ID" in msg and "no surrounding quotes" in msg for msg in errors
    )
    assert any(
        "AWS_SECRET_ACCESS_KEY" in msg and "no surrounding quotes" in msg
        for msg in errors
    )


def test_validate_windows_annex_runtime_reports_missing_arbutus_env_vars(
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

    env_file = tmp_path / "user" / ".config" / "femic" / "arbutus.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("AWS_ACCESS_KEY_ID=abc123\n", encoding="utf-8")
    loader_path = env_file.parent / "load-arbutus-env.ps1"
    loader_path.write_text("# loader\n", encoding="utf-8")

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
    monkeypatch.setattr(
        cli_main,
        "_resolve_windows_user_local_path",
        lambda rel: (
            env_file
            if rel == cli_main.WINDOWS_ARBUTUS_ENV_FILE_RELATIVE
            else loader_path
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {
            "AWS_ACCESS_KEY_ID": "",
            "AWS_SECRET_ACCESS_KEY": "",
            "AWS_DEFAULT_REGION": "",
            "S3_ENDPOINT_URL": "",
        },
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert warnings == []
    assert any(
        "Set-ExecutionPolicy -Scope Process Bypass -Force" in msg for msg in errors
    )
    assert any("AWS_SECRET_ACCESS_KEY" in msg for msg in errors)


def test_validate_windows_annex_runtime_reports_bucket_visibility_failure(
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

    env_file = tmp_path / "user" / ".config" / "femic" / "arbutus.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("AWS_ACCESS_KEY_ID=abc123\n", encoding="utf-8")
    loader_path = env_file.parent / "load-arbutus-env.ps1"
    loader_path.write_text("# loader\n", encoding="utf-8")

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
    monkeypatch.setattr(
        cli_main,
        "_resolve_windows_user_local_path",
        lambda rel: (
            env_file
            if rel == cli_main.WINDOWS_ARBUTUS_ENV_FILE_RELATIVE
            else loader_path
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "_validate_windows_arbutus_env_file",
        lambda _path: [],
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {
            "AWS_ACCESS_KEY_ID": "abc123",
            "AWS_SECRET_ACCESS_KEY": "secret123",
            "AWS_DEFAULT_REGION": "ca-west-1",
            "S3_ENDPOINT_URL": "https://object-arbutus.cloud.computecanada.ca",
        },
    )
    monkeypatch.setattr(
        cli_main,
        "_probe_windows_arbutus_bucket",
        lambda bucket_name, env_values: (
            False,
            f"bucket={bucket_name} error_code=404. This usually means invalid loaded credentials.",
        ),
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert warnings == []
    assert any("bucket visibility probe failed" in msg for msg in errors)
    assert any("Stop before `git annex initremote`" in msg for msg in errors)


def test_validate_windows_annex_runtime_passes_with_visible_public_bucket(
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

    env_file = tmp_path / "user" / ".config" / "femic" / "arbutus.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("AWS_ACCESS_KEY_ID=abc123\n", encoding="utf-8")
    loader_path = env_file.parent / "load-arbutus-env.ps1"
    loader_path.write_text("# loader\n", encoding="utf-8")

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
    monkeypatch.setattr(
        cli_main,
        "_resolve_windows_user_local_path",
        lambda rel: (
            env_file
            if rel == cli_main.WINDOWS_ARBUTUS_ENV_FILE_RELATIVE
            else loader_path
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "_validate_windows_arbutus_env_file",
        lambda _path: [],
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {
            "AWS_ACCESS_KEY_ID": "abc123",
            "AWS_SECRET_ACCESS_KEY": "secret123",
            "AWS_DEFAULT_REGION": "ca-west-1",
            "S3_ENDPOINT_URL": "https://object-arbutus.cloud.computecanada.ca",
        },
    )
    monkeypatch.setattr(
        cli_main,
        "_probe_windows_arbutus_bucket",
        lambda bucket_name, env_values: (True, ""),
    )
    monkeypatch.setattr(
        cli_main,
        "_validate_windows_public_data_tsa_boundary",
        lambda tsa_boundaries_path: [],
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert errors == []
    assert warnings == []


def test_arbutus_auth_status_reports_missing_scaffolding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    userprofile = tmp_path / "user"
    userprofile.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setenv("USERPROFILE", str(userprofile))

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["prep", "arbutus-auth-status"])

    assert result.exit_code == 1
    assert "Missing shared Arbutus env file" in result.stdout
    assert "Missing Arbutus profile registry" in result.stdout


def test_arbutus_auth_init_scaffolds_files_then_fails_noninteractive_when_values_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    userprofile = tmp_path / "user"
    userprofile.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    monkeypatch.setattr(cli_main.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli_main.sys.stdout, "isatty", lambda: False)

    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        ["prep", "arbutus-auth-init", "--profile", "public-data"],
    )

    env_file = userprofile / ".config" / "femic" / "arbutus.env"
    profiles_file = userprofile / ".config" / "femic" / "arbutus-profiles.yaml"
    loader_ps1 = userprofile / ".config" / "femic" / "load-arbutus-env.ps1"
    loader_sh = userprofile / ".config" / "femic" / "load-arbutus-env.sh"

    assert result.exit_code == 1
    assert env_file.exists()
    assert profiles_file.exists()
    assert loader_ps1.exists()
    assert loader_sh.exists()
    assert "Missing Arbutus bootstrap values in non-interactive mode" in result.stdout


def test_arbutus_auth_status_reports_current_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    userprofile = tmp_path / "user"
    config_root = userprofile / ".config" / "femic"
    config_root.mkdir(parents=True, exist_ok=True)
    env_file = config_root / "arbutus.env"
    profiles_file = config_root / "arbutus-profiles.yaml"
    status_file = config_root / "arbutus-status.yaml"
    env_values = {
        "AWS_ACCESS_KEY_ID": "abc123456",
        "AWS_SECRET_ACCESS_KEY": "secret123456",
        "AWS_DEFAULT_REGION": "ca-west-1",
        "S3_ENDPOINT_URL": "https://object-arbutus.cloud.computecanada.ca",
    }
    env_file.write_text(
        cli_main._windows_arbutus_env_template(env_values), encoding="utf-8"
    )
    profiles_file.write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "public-data": {
                        "bucket_name": cli_main.WINDOWS_ARBUTUS_PUBLIC_DATA_BUCKET,
                        "remote_name": cli_main.WINDOWS_ARBUTUS_DEFAULT_REMOTE_NAME,
                        "dataset_path_hint": "external/femic-public-data",
                        "note": "",
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    loader_ps1 = config_root / "load-arbutus-env.ps1"
    loader_ps1.write_text("# loader\n", encoding="utf-8")
    loader_sh = config_root / "load-arbutus-env.sh"
    loader_sh.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        cli_main,
        "_probe_windows_arbutus_bucket",
        lambda bucket_name, env_values: (True, ""),
    )

    record = cli_main._build_windows_arbutus_status_record(
        profile_name="public-data",
        profile={
            "bucket_name": cli_main.WINDOWS_ARBUTUS_PUBLIC_DATA_BUCKET,
            "remote_name": cli_main.WINDOWS_ARBUTUS_DEFAULT_REMOTE_NAME,
            "dataset_path_hint": "external/femic-public-data",
            "note": "",
        },
        env_file=env_file,
        loader_paths=[loader_ps1, loader_sh],
        dataset_path=None,
        env_values=env_values,
        validation_checks={
            "env_file_parse": True,
            "shell_env_loaded": True,
            "head_bucket": True,
            "git_annex_enableremote": False,
        },
    )
    status_file.write_text(
        yaml.safe_dump(
            {
                "schema_version": cli_main.WINDOWS_ARBUTUS_STATUS_SCHEMA_VERSION,
                "profiles": {"public-data": record},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        ["prep", "arbutus-auth-status", "--profile", "public-data"],
    )

    assert result.exit_code == 0
    assert "Windows Arbutus auth status is current" in result.stdout


def test_arbutus_auth_status_reports_stale_marker_when_env_file_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    userprofile = tmp_path / "user"
    config_root = userprofile / ".config" / "femic"
    config_root.mkdir(parents=True, exist_ok=True)
    env_file = config_root / "arbutus.env"
    profiles_file = config_root / "arbutus-profiles.yaml"
    status_file = config_root / "arbutus-status.yaml"
    loader_ps1 = config_root / "load-arbutus-env.ps1"
    loader_ps1.write_text("# loader\n", encoding="utf-8")
    env_values = {
        "AWS_ACCESS_KEY_ID": "abc123456",
        "AWS_SECRET_ACCESS_KEY": "secret123456",
        "AWS_DEFAULT_REGION": "ca-west-1",
        "S3_ENDPOINT_URL": "https://object-arbutus.cloud.computecanada.ca",
    }
    env_file.write_text(
        cli_main._windows_arbutus_env_template(env_values), encoding="utf-8"
    )
    profiles_file.write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "public-data": {
                        "bucket_name": cli_main.WINDOWS_ARBUTUS_PUBLIC_DATA_BUCKET,
                        "remote_name": cli_main.WINDOWS_ARBUTUS_DEFAULT_REMOTE_NAME,
                    }
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    for key, value in env_values.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        cli_main,
        "_probe_windows_arbutus_bucket",
        lambda bucket_name, env_values: (True, ""),
    )
    record = cli_main._build_windows_arbutus_status_record(
        profile_name="public-data",
        profile={
            "bucket_name": cli_main.WINDOWS_ARBUTUS_PUBLIC_DATA_BUCKET,
            "remote_name": cli_main.WINDOWS_ARBUTUS_DEFAULT_REMOTE_NAME,
            "dataset_path_hint": "",
            "note": "",
        },
        env_file=env_file,
        loader_paths=[loader_ps1],
        dataset_path=None,
        env_values=env_values,
        validation_checks={
            "env_file_parse": True,
            "shell_env_loaded": True,
            "head_bucket": True,
            "git_annex_enableremote": False,
        },
    )
    status_file.write_text(
        yaml.safe_dump(
            {
                "schema_version": cli_main.WINDOWS_ARBUTUS_STATUS_SCHEMA_VERSION,
                "profiles": {"public-data": record},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    env_file.write_text(
        cli_main._windows_arbutus_env_template(
            env_values | {"AWS_DEFAULT_REGION": "ca-west-2"}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-west-2")

    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        ["prep", "arbutus-auth-status", "--profile", "public-data"],
    )

    assert result.exit_code == 1
    assert "Saved known-working marker is stale" in result.stdout
    assert (
        "mtime differs" in result.stdout or "shared Arbutus env file" in result.stdout
    )


def test_arbutus_auth_status_uses_legacy_single_bucket_compatibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    userprofile = tmp_path / "user"
    config_root = userprofile / ".config" / "femic"
    config_root.mkdir(parents=True, exist_ok=True)
    env_file = config_root / "arbutus.env"
    env_file.write_text(
        "\n".join(
            [
                "AWS_ACCESS_KEY_ID=abc123456",
                "AWS_SECRET_ACCESS_KEY=secret123456",
                "AWS_DEFAULT_REGION=ca-west-1",
                "S3_ENDPOINT_URL=https://object-arbutus.cloud.computecanada.ca",
                "S3_BUCKET_NAME=legacy-bucket",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli_main.os, "name", "nt", raising=False)
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "abc123456")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123456")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ca-west-1")
    monkeypatch.setenv(
        "S3_ENDPOINT_URL",
        "https://object-arbutus.cloud.computecanada.ca",
    )
    monkeypatch.setattr(
        cli_main,
        "_probe_windows_arbutus_bucket",
        lambda bucket_name, env_values: (True, ""),
    )

    runner = CliRunner()
    result = runner.invoke(cli_main.app, ["prep", "arbutus-auth-status"])

    assert result.exit_code == 1
    assert "selected_profile=legacy-default bucket=legacy-bucket" in result.stdout


def test_validate_windows_public_data_tsa_boundary_reports_missing_geospatial_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    public_data_root = tmp_path / "repo" / "external" / "femic-public-data"
    tsa_path = public_data_root / "data" / "bc" / "tsa" / "FADM_TSA.gdb"
    tsa_path.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        cli_main,
        "_probe_windows_filegdb_layers",
        lambda _path: (
            None,
            "Neither `pyogrio` nor `fiona` is importable in the active FEMIC environment.",
        ),
    )

    errors = cli_main._validate_windows_public_data_tsa_boundary(
        tsa_boundaries_path=tsa_path,
    )

    assert any("geospatial runtime is incomplete" in msg for msg in errors)
    assert any(
        "repair the standard FEMIC geospatial environment first" in msg
        for msg in errors
    )


def test_validate_windows_public_data_tsa_boundary_reports_pointer_like_members(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    public_data_root = tmp_path / "repo" / "external" / "femic-public-data"
    tsa_path = public_data_root / "data" / "bc" / "tsa" / "FADM_TSA.gdb"
    tsa_path.mkdir(parents=True, exist_ok=True)
    gitdir = public_data_root.parent / "gitdir"
    payload = (
        gitdir
        / "annex"
        / "objects"
        / "aa1"
        / "bb2"
        / "MD5E-s10--tsa-boundary.gdbtable"
        / "MD5E-s10--tsa-boundary.gdbtable"
    )
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(b"payload")
    (public_data_root / ".git").write_text("gitdir: ../gitdir\n", encoding="utf-8")
    (tsa_path / "a00000001.gdbtable").write_text(
        "../../../.git/annex/objects/aa1/bb2/MD5E-s10--tsa-boundary.gdbtable/"
        "MD5E-s10--tsa-boundary.gdbtable",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli_main,
        "_probe_windows_filegdb_layers",
        lambda _path: (False, "pyogrio DataSourceError: failed to open dataset"),
    )

    errors = cli_main._validate_windows_public_data_tsa_boundary(
        tsa_boundaries_path=tsa_path,
    )

    assert any("pointer-style worktree stubs" in msg for msg in errors)
    assert any("annex unlock data/bc/tsa/FADM_TSA.gdb" in msg for msg in errors)


def test_validate_windows_public_data_tsa_boundary_reports_generic_read_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    public_data_root = tmp_path / "repo" / "external" / "femic-public-data"
    tsa_path = public_data_root / "data" / "bc" / "tsa" / "FADM_TSA.gdb"
    tsa_path.mkdir(parents=True, exist_ok=True)
    (tsa_path / "a00000001.gdbtable").write_bytes(b"real-ish-bytes")

    monkeypatch.setattr(
        cli_main,
        "_probe_windows_filegdb_layers",
        lambda _path: (False, "pyogrio DataSourceError: failed to open dataset"),
    )

    errors = cli_main._validate_windows_public_data_tsa_boundary(
        tsa_boundaries_path=tsa_path,
    )

    assert any(
        "first rule out annex-backed materialization/unlock problems" in msg
        for msg in errors
    )
    assert any("annex enableremote arbutus-s3" in msg for msg in errors)


def test_validate_windows_annex_runtime_surfaces_canonical_tsa_boundary_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data"
    public_data_root.mkdir(parents=True, exist_ok=True)
    external_paths = SimpleNamespace(
        vri_vclr1p_path=public_data_root / "data" / "bc" / "vri.gdb",
        vdyp_input_pandl_path=public_data_root / "data" / "bc" / "vdyp.gdb",
        tsa_boundaries_path=public_data_root / "data" / "bc" / "tsa" / "FADM_TSA.gdb",
        site_prod_bc_gdb_path=public_data_root / "data" / "bc" / "siteprod.gdb",
    )
    for path_obj in (
        external_paths.vri_vclr1p_path,
        external_paths.vdyp_input_pandl_path,
        external_paths.site_prod_bc_gdb_path,
    ):
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.touch()
    external_paths.tsa_boundaries_path.mkdir(parents=True, exist_ok=True)

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
    monkeypatch.setattr(
        cli_main, "_resolve_windows_user_local_path", lambda _path: None
    )
    monkeypatch.setattr(
        cli_main,
        "_current_arbutus_env_values",
        lambda: {key: "" for key in cli_main.WINDOWS_ARBUTUS_REQUIRED_ENV_KEYS},
    )
    monkeypatch.setattr(
        cli_main,
        "_validate_windows_public_data_tsa_boundary",
        lambda tsa_boundaries_path: ["annex unlock data/bc/tsa/FADM_TSA.gdb"],
    )

    errors, warnings = cli_main._validate_windows_annex_runtime(
        source_root=source_root,
        external_paths=external_paths,
    )

    assert warnings == []
    assert "annex unlock data/bc/tsa/FADM_TSA.gdb" in errors


def test_preflight_checks_fails_for_specific_missing_required_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    _create_preflight_required_layout(repo_root)
    missing_required = repo_root / "data" / "ria_vri_vclr1p_checkpoint1.feather"
    missing_required.unlink()

    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main.shutil, "which", lambda _: "/usr/bin/wine")

    with pytest.raises(typer.Exit) as exc_info:
        cli_main._preflight_checks(
            resume=True,
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
    assert any("Provide at least one FMU/code" in msg for msg in messages)


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
        yield_assumptions_path,
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
        called["yield_assumptions_path"] = yield_assumptions_path
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
    assert called["yield_assumptions_path"] is None
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
                "  yield_assumptions_path: config/tsr/yield_assumptions.yaml",
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
    assert called["yield_assumptions_path"] == (
        Path.cwd() / "config" / "tsr" / "yield_assumptions.yaml"
    )


def test_export_patchworks_requires_tsa(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.export_patchworks(tsa=None)

    assert exc_info.value.exit_code == 1
    assert any("Provide at least one FMU/code" in msg for msg in messages)


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
        ifm_mode,
        ifm_source_col,
        ifm_threshold,
        ifm_target_managed_share,
        seral_stage_config_path,
        silviculture_config_path,
        legacy_input_variables_config_path,
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
                "ifm_mode": ifm_mode,
                "ifm_source_col": ifm_source_col,
                "ifm_threshold": ifm_threshold,
                "ifm_target_managed_share": ifm_target_managed_share,
                "seral_stage_config_path": seral_stage_config_path,
                "silviculture_config_path": silviculture_config_path,
                "legacy_input_variables_config_path": (
                    legacy_input_variables_config_path
                ),
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
        ifm_mode="legacy_binary",
        ifm_source_col="thlb_raw",
        ifm_threshold=0.2,
        ifm_target_managed_share=None,
        seral_stage_config=Path("config/seral.k3z.yaml"),
        silviculture_config=Path("config/silviculture.k3z.yaml"),
        legacy_input_variables_config=Path(
            "config/legacy_xml_builder/input_variables.mkrf.yaml"
        ),
    )

    assert called["tsa_list"] == ["k3z"]
    assert called["cc_max_age"] == 500
    assert called["cc_transition_ifm"] == "managed"
    assert called["ifm_mode"] == "legacy_binary"
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
    assert (
        Path(called["legacy_input_variables_config_path"])
        .as_posix()
        .endswith("config/legacy_xml_builder/input_variables.mkrf.yaml")
    )
    assert any("patchworks export completed" in msg for msg in messages)


def test_export_woodstock_requires_tsa(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.export_woodstock(tsa=None)

    assert exc_info.value.exit_code == 1
    assert any("Provide at least one FMU/code" in msg for msg in messages)


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


def test_instance_rebuild_uses_btc_post_tipsy_step_when_declared_in_spec(
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
            "steps": [
                {"step_id": "validate_case"},
                {"step_id": "compile_upstream"},
                {
                    "step_id": "btc_post_tipsy_bundle",
                    "command": "femic tsa btc-post-tipsy --run-config config/run.yaml --tsa 29",
                },
            ],
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
    assert "btc_post_tipsy_bundle" in step_ids
    assert "post_tipsy_bundle" not in step_ids
    patchworks_preflight = next(
        step for step in calls["steps"] if step.step_id == "patchworks_preflight"
    )
    assert patchworks_preflight.depends_on == ("btc_post_tipsy_bundle",)


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
    assert captured["log_dir"] == Path("runtime/logs")
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
        ifm_mode="proportional",
        ifm_source_col=None,
        ifm_threshold=None,
        ifm_target_managed_share=None,
        seral_stage_config=None,
        legacy_input_variables_config=None,
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


def test_data_bcdc_resolve_prints_summary_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "resolve_bcdc_candidates",
        lambda query, limit: cli_main.BcdcResolveResult(
            query=query,
            limit=limit,
            generated_utc="2026-04-04T00:00:00+00:00",
            api_urls=("https://example.invalid/package_search",),
            matches=(
                bcdc_catalog.BcdcPackageMatch(
                    package_id="pkg-f-own",
                    package_name="generalized-forest-cover-ownership",
                    title="Generalized Forest Cover Ownership",
                    dataset_page_url=(
                        "https://catalogue.data.gov.bc.ca/dataset/"
                        "generalized-forest-cover-ownership"
                    ),
                    organization_name="forest-analysis-and-inventory",
                    organization_title="Forest Analysis and Inventory Branch",
                    license_title="Access Only",
                    download_audience="Public",
                    matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                    match_score=400,
                    suggested_fetch_strategy="wfs_getfeature_bbox",
                    resources=(
                        bcdc_catalog.BcdcResourceMatch(
                            resource_id="wms-id",
                            name="WMS getCapabilities request",
                            classification="service",
                            url=(
                                "https://openmaps.gov.bc.ca/geo/pub/"
                                "WHSE_FOREST_VEGETATION.F_OWN/ows"
                            ),
                            format="wms",
                            bcdc_type="webservice",
                            object_name="WHSE_FOREST_VEGETATION.F_OWN",
                            object_short_name="F_OWN",
                            resource_access_method="service",
                            resource_type="data",
                            resource_storage_location="bc geographic warehouse",
                            service_type="openmaps_ows",
                            wfs_queryable=True,
                            wfs_capabilities_url=(
                                "https://openmaps.gov.bc.ca/geo/pub/"
                                "WHSE_FOREST_VEGETATION.F_OWN/ows"
                                "?service=WFS&request=GetCapabilities&version=2.0.0"
                            ),
                            wfs_typename="pub:WHSE_FOREST_VEGETATION.F_OWN",
                            suggested_fetch_strategy="wfs_getfeature_bbox",
                            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                            match_score=400,
                            notes=("WFS-capable OpenMaps service.",),
                        ),
                        bcdc_catalog.BcdcResourceMatch(
                            resource_id="custom-id",
                            name="BC Geographic Warehouse Custom Download",
                            classification="indirect_custom_download",
                            url=None,
                            format="multiple",
                            bcdc_type="geographic",
                            object_name="WHSE_FOREST_VEGETATION.F_OWN",
                            object_short_name="F_OWN",
                            resource_access_method="indirect access",
                            resource_type="data",
                            resource_storage_location="bc geographic warehouse",
                            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                            match_score=400,
                            notes=("Needs manual custom-download follow-up.",),
                        ),
                    ),
                    manual_follow_up=("Use the dataset page for manual access.",),
                ),
            ),
        ),
    )

    cli_main.data_bcdc_resolve(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        manifest_path=tmp_path / "manifest.json",
        download_direct=False,
        download_root=None,
        limit=5,
        instance_root=None,
    )

    assert any("query: WHSE_FOREST_VEGETATION.F_OWN" in msg for msg in messages)
    assert any(
        "top_match: Generalized Forest Cover Ownership" in msg for msg in messages
    )
    assert any(
        "manual_follow_up: Use the dataset page for manual access." in msg
        for msg in messages
    )
    assert any(
        "suggested_fetch_strategy: wfs_getfeature_bbox" in msg for msg in messages
    )
    assert any(
        "resource_hint:" in msg
        and "wfs_typename=pub:WHSE_FOREST_VEGETATION.F_OWN" in msg
        for msg in messages
    )
    assert any("manifest:" in msg for msg in messages)
    assert (tmp_path / "manifest.json").is_file()


def test_data_bcdc_resolve_writes_summary_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "resolve_bcdc_candidates",
        lambda query, limit: cli_main.BcdcResolveResult(
            query=query,
            limit=limit,
            generated_utc="2026-04-04T00:00:00+00:00",
            api_urls=("https://example.invalid/package_search",),
            matches=(
                bcdc_catalog.BcdcPackageMatch(
                    package_id="pkg-cutblocks",
                    package_name="harvested-areas-of-bc-consolidated-cutblocks",
                    title="Harvested Areas of BC (Consolidated Cutblocks)",
                    dataset_page_url=(
                        "https://catalogue.data.gov.bc.ca/dataset/"
                        "harvested-areas-of-bc-consolidated-cutblocks"
                    ),
                    organization_name="forest-analysis-and-inventory",
                    organization_title="Forest Analysis and Inventory Branch",
                    license_title="Open Government Licence",
                    download_audience="Public",
                    matched_by="none",
                    match_score=100,
                    resources=(
                        bcdc_catalog.BcdcResourceMatch(
                            resource_id="zip-id",
                            name="Consolidated Cutblocks Complete Download",
                            classification="direct_data_download",
                            url="https://example.invalid/cutblocks.zip",
                            format="zip",
                            bcdc_type="geographic",
                            object_name=None,
                            object_short_name=None,
                            resource_access_method="direct access",
                            resource_type="data",
                            resource_storage_location="web or ftp site",
                            matched_by="none",
                            match_score=100,
                            notes=("Stable direct download.",),
                        ),
                        bcdc_catalog.BcdcResourceMatch(
                            resource_id="doc-id",
                            name="Documentation",
                            classification="supporting_document",
                            url="https://example.invalid/doc.pdf",
                            format="pdf",
                            bcdc_type="document",
                            object_name=None,
                            object_short_name=None,
                            resource_access_method="direct access",
                            resource_type="abstraction",
                            resource_storage_location="web or ftp site",
                            matched_by="none",
                            match_score=0,
                            notes=("Supporting documentation.",),
                        ),
                    ),
                    manual_follow_up=("Supporting docs available.",),
                ),
            ),
            notes=(
                "Used alias/query variant `CONSOLIDATED_CUTBLOCKS` to surface the current top match.",
            ),
        ),
    )

    summary_path = tmp_path / "summary.csv"
    cli_main.data_bcdc_resolve(
        queries=["CONSOLIDATED_CUTBLOCKS_2011"],
        query_file=None,
        summary_csv=summary_path,
        manifest_path=None,
        download_direct=False,
        download_root=None,
        limit=5,
        instance_root=None,
    )

    assert any("summary_csv:" in msg for msg in messages)
    assert summary_path.is_file()
    text = summary_path.read_text(encoding="utf-8")
    assert "CONSOLIDATED_CUTBLOCKS_2011" in text
    assert "alias_hit" in text
    assert "CONSOLIDATED_CUTBLOCKS" in text
    assert "suggested_fetch_strategy" in text
    assert "has_wfs_queryable_service" in text


def test_bcdc_summary_status_treats_object_name_stem_as_exact_hit() -> None:
    result = cli_main.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.BEC",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog.BcdcPackageMatch(
                package_id="pkg-bec",
                package_name="bec-map",
                title="BEC Map",
                dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/bec-map",
                organization_name="forest-analysis-and-inventory",
                organization_title="Forest Analysis and Inventory Branch",
                license_title="Access Only",
                download_audience="Public",
                matched_by=(
                    "object_name_stem:WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY"
                ),
                match_score=250,
                resources=(),
            ),
        ),
    )

    assert cli_main._bcdc_summary_status(result) == "exact_hit"


def test_data_bcdc_resolve_downloads_direct_resources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    resolve_result = cli_main.BcdcResolveResult(
        query="WHSE_FOREST_VEGETATION.F_OWN",
        limit=5,
        generated_utc="2026-04-04T00:00:00+00:00",
        api_urls=("https://example.invalid/package_search",),
        matches=(
            bcdc_catalog.BcdcPackageMatch(
                package_id="pkg-f-own",
                package_name="generalized-forest-cover-ownership",
                title="Generalized Forest Cover Ownership",
                dataset_page_url=(
                    "https://catalogue.data.gov.bc.ca/dataset/"
                    "generalized-forest-cover-ownership"
                ),
                organization_name="forest-analysis-and-inventory",
                organization_title="Forest Analysis and Inventory Branch",
                license_title="Access Only",
                download_audience="Public",
                matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                match_score=400,
                resources=(
                    bcdc_catalog.BcdcResourceMatch(
                        resource_id="zip-id",
                        name="Download FGDB zip",
                        classification="direct_data_download",
                        url="https://pub.data.gov.bc.ca/datasets/F_OWN.gdb.zip",
                        format="zip",
                        bcdc_type="geographic",
                        object_name="WHSE_FOREST_VEGETATION.F_OWN",
                        object_short_name="F_OWN",
                        resource_access_method="direct access",
                        resource_type="data",
                        resource_storage_location="web or ftp site",
                        matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
                        match_score=400,
                        notes=("Stable direct download.",),
                    ),
                ),
                manual_follow_up=(),
            ),
        ),
    )
    monkeypatch.setattr(
        cli_main, "resolve_bcdc_candidates", lambda query, limit: resolve_result
    )

    def _fake_download(result, destination_root):
        download_result = bcdc_catalog.BcdcDownloadResult(
            destination_root=destination_root,
            downloaded=(
                bcdc_catalog.BcdcDownloadedResource(
                    resource_name="Download FGDB zip",
                    resource_url="https://pub.data.gov.bc.ca/datasets/F_OWN.gdb.zip",
                    saved_path=destination_root
                    / "WHSE_FOREST_VEGETATION_F_OWN"
                    / "F_OWN.gdb.zip",
                ),
            ),
            skipped_resources=("WMS getCapabilities request: service",),
            failures=(),
        )
        result.download_result = download_result
        return download_result

    monkeypatch.setattr(cli_main, "download_direct_bcdc_resources", _fake_download)

    cli_main.data_bcdc_resolve(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        manifest_path=None,
        download_direct=True,
        download_root=tmp_path / "downloads",
        limit=5,
        instance_root=None,
    )

    assert any("downloads: downloaded=1" in msg for msg in messages)


def test_data_bcdc_resolve_plan_only_skips_direct_download_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "resolve_bcdc_candidates",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("resolve_bcdc_candidates should not be called")
        ),
    )
    monkeypatch.setattr(
        cli_main,
        "download_direct_bcdc_resources",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("download_direct_bcdc_resources should not be called")
        ),
    )

    query_file = tmp_path / "queries.txt"
    query_file.write_text(
        "SITE_PROD_BC\nSITE_PROD_BC\nWHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY\n",
        encoding="utf-8",
    )

    cli_main.data_bcdc_resolve(
        queries=None,
        query_file=query_file,
        summary_csv=None,
        manifest_path=None,
        download_direct=True,
        download_root=tmp_path / "downloads",
        limit=5,
        instance_root=None,
        plan_only=True,
        allow_bulk=False,
    )

    assert any("plan_operation: direct-download" in msg for msg in messages)
    assert any("requested_query_count: 3" in msg for msg in messages)
    assert any("deduplicated_query_count: 2" in msg for msg in messages)
    assert any("plan_only:" in msg for msg in messages)


def test_data_bcdc_resolve_query_file_ignores_blank_lines_and_comments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    resolved_queries: list[str] = []

    def _fake_resolve(query: str, limit: int):
        resolved_queries.append(query)
        return cli_main.BcdcResolveResult(
            query=query,
            limit=limit,
            generated_utc="2026-04-04T00:00:00+00:00",
            api_urls=("https://example.invalid/package_search",),
            matches=(),
            notes=("No catalogue matches found for the supplied query.",),
        )

    monkeypatch.setattr(cli_main, "resolve_bcdc_candidates", _fake_resolve)

    query_file = tmp_path / "queries.txt"
    query_file.write_text(
        "# comment\nWHSE_FOREST_VEGETATION.F_OWN\n\nCONSOLIDATED_CUTBLOCKS_2011\n",
        encoding="utf-8",
    )

    cli_main.data_bcdc_resolve(
        queries=None,
        query_file=query_file,
        manifest_path=None,
        download_direct=False,
        download_root=None,
        limit=5,
        instance_root=None,
    )

    assert resolved_queries == [
        "WHSE_FOREST_VEGETATION.F_OWN",
        "CONSOLIDATED_CUTBLOCKS_2011",
    ]


def test_data_bcdc_resolve_query_file_strips_utf8_bom(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resolved_queries: list[str] = []

    def _fake_resolve(query: str, limit: int):
        resolved_queries.append(query)
        return cli_main.BcdcResolveResult(
            query=query,
            limit=limit,
            generated_utc="2026-04-04T00:00:00+00:00",
            api_urls=("https://example.invalid/package_search",),
            matches=(),
            notes=("No catalogue matches found for the supplied query.",),
        )

    monkeypatch.setattr(cli_main, "resolve_bcdc_candidates", _fake_resolve)
    monkeypatch.setattr(cli_main.console, "print", lambda *_args, **_kwargs: None)

    query_file = tmp_path / "queries.txt"
    query_file.write_text("\ufeffWHSE_FOREST_VEGETATION.F_OWN\n", encoding="utf-8")

    cli_main.data_bcdc_resolve(
        queries=None,
        query_file=query_file,
        manifest_path=None,
        download_direct=False,
        download_root=None,
        limit=5,
        instance_root=None,
    )

    assert resolved_queries == ["WHSE_FOREST_VEGETATION.F_OWN"]


def test_data_bcdc_resolve_requires_query_or_query_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_resolve(
            queries=None,
            query_file=None,
            manifest_path=None,
            download_direct=False,
            download_root=None,
            limit=5,
            instance_root=None,
        )

    assert exc_info.value.exit_code == 1
    assert any(
        "provide at least one query or use `--query-file`" in msg for msg in messages
    )


def test_data_bcdc_fetch_prints_summary_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "fetch_bcdc_wfs_data",
        lambda query, **_kwargs: cli_main.BcdcFetchResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url=(
                "https://catalogue.data.gov.bc.ca/dataset/"
                "generalized-forest-cover-ownership"
            ),
            resource_id="wms-id",
            resource_name="WMS getCapabilities request",
            resource_url=(
                "https://openmaps.gov.bc.ca/geo/pub/WHSE_FOREST_VEGETATION.F_OWN/ows"
            ),
            wfs_typename="pub:WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            suggested_fetch_strategy="wfs_getfeature_bbox",
            aoi_source="bbox",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id=None,
            geomark_url=None,
            request_url="https://openmaps.gov.bc.ca/example/GetFeature",
            saved_path=tmp_path / "downloads" / "WHSE_FOREST_VEGETATION_F_OWN.gpkg",
            output_format="gpkg",
            feature_count=2,
            warnings=(),
        ),
    )

    cli_main.data_bcdc_fetch(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        query_file=None,
        manifest_path=tmp_path / "manifest.json",
        download_root=tmp_path / "downloads",
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="gpkg",
    )

    assert any("query: WHSE_FOREST_VEGETATION.F_OWN" in msg for msg in messages)
    assert any("aoi_source: bbox" in msg for msg in messages)
    assert any("feature_count: 2" in msg for msg in messages)
    assert any("saved_path:" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert (tmp_path / "manifest.json").is_file()


def test_data_bcdc_fetch_query_file_with_geomark(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "resolve_geomark_bbox_3005",
        lambda _value: SimpleNamespace(
            geomark_id="gm-demo",
            geomark_url="https://apps.gov.bc.ca/pub/geomark/geomarks/gm-demo",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        ),
    )
    captured_queries: list[str] = []

    def _fake_fetch(query: str, **kwargs):
        captured_queries.append(query)
        assert kwargs["geomark"] is not None
        return cli_main.BcdcFetchResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
            resource_id="wms-id",
            resource_name="WMS getCapabilities request",
            resource_url="https://openmaps.gov.bc.ca/geo/pub/WHSE_FOREST_VEGETATION.F_OWN/ows",
            wfs_typename="pub:WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            suggested_fetch_strategy="wfs_getfeature_bbox",
            aoi_source="geomark",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id="gm-demo",
            geomark_url="https://apps.gov.bc.ca/pub/geomark/geomarks/gm-demo",
            request_url="https://openmaps.gov.bc.ca/example/GetFeature",
            saved_path=tmp_path / "downloads" / "WHSE_FOREST_VEGETATION_F_OWN.gpkg",
            output_format="gpkg",
            feature_count=2,
            warnings=(),
        )

    monkeypatch.setattr(cli_main, "fetch_bcdc_wfs_data", _fake_fetch)

    query_file = tmp_path / "queries.txt"
    query_file.write_text("WHSE_FOREST_VEGETATION.F_OWN\n", encoding="utf-8")

    cli_main.data_bcdc_fetch(
        queries=None,
        query_file=query_file,
        manifest_path=None,
        download_root=tmp_path / "downloads",
        limit=5,
        instance_root=None,
        bbox=None,
        geomark="gm-demo",
        output_format="gpkg",
    )

    assert captured_queries == ["WHSE_FOREST_VEGETATION.F_OWN"]
    assert any("geomark: gm-demo" in msg for msg in messages)


def test_data_bcdc_fetch_requires_exactly_one_aoi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_fetch(
            queries=["WHSE_FOREST_VEGETATION.F_OWN"],
            query_file=None,
            manifest_path=None,
            download_root=None,
            limit=5,
            instance_root=None,
            bbox=None,
            geomark=None,
            output_format="gpkg",
        )

    assert exc_info.value.exit_code == 1
    assert any("supply exactly one AOI input" in msg for msg in messages)


def test_data_bcdc_fetch_reports_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "fetch_bcdc_wfs_data",
        lambda query, **_kwargs: (_ for _ in ()).throw(
            cli_main.BcdcFetchError(
                "use `femic data bcdc-resolve --download-direct` instead"
            )
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_fetch(
            queries=["SITE_PROD_BC"],
            query_file=None,
            manifest_path=None,
            download_root=None,
            limit=5,
            instance_root=None,
            bbox="1170000,450000,1180000,460000",
            geomark=None,
            output_format="gpkg",
        )

    assert exc_info.value.exit_code == 1
    assert any("download-direct" in msg for msg in messages)


def test_data_bcdc_fetch_plan_only_deduplicates_without_fetching(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    called: list[str] = []
    monkeypatch.setattr(
        cli_main,
        "fetch_bcdc_wfs_data",
        lambda query, **_kwargs: called.append(query),
    )

    query_file = tmp_path / "queries.txt"
    query_file.write_text(
        "WHSE_FOREST_VEGETATION.F_OWN\nwhse_forest_vegetation.f_own\n",
        encoding="utf-8",
    )

    cli_main.data_bcdc_fetch(
        queries=None,
        query_file=query_file,
        manifest_path=None,
        download_root=None,
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="gpkg",
        plan_only=True,
        allow_bulk=False,
    )

    assert called == []
    assert any("plan_operation: WFS fetch" in msg for msg in messages)
    assert any("requested_query_count: 2" in msg for msg in messages)
    assert any("deduplicated_query_count: 1" in msg for msg in messages)
    assert any("plan_only:" in msg for msg in messages)


def test_data_bcdc_order_prints_summary_and_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "submit_bcdc_dwds_order",
        lambda query, **_kwargs: cli_main.BcdcDwdsOrderResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url=(
                "https://catalogue.data.gov.bc.ca/dataset/"
                "generalized-forest-cover-ownership"
            ),
            resource_id="dwds-id",
            resource_name="BC Geographic Warehouse Custom Download",
            resource_url=None,
            feature_type="WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            aoi_source="bbox",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id=None,
            geomark_url=None,
            output_format="fgdb",
            email_address=None,
            clipping_method="clip_to_aoi",
            ordering_application="FEMIC-BCDC-DWDS",
            request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
            request_payload={"featureItems": []},
            order_id="2551000",
            order_guid="guid-123",
            submission_status="SUCCESS",
            submission_description="submitted",
            submission_value="2551000",
            status_probe=cli_main.BcdcDwdsStatusProbe(
                order_id="2551000",
                raw_payload={
                    "Status": "FAILURE",
                    "Description": "missing",
                    "Value": "6",
                },
                status="FAILURE",
                description="missing",
                value="6",
                download_url=None,
            ),
            warnings=(
                "DWDS accepted the order submission, but the public `/order/{id}` status seam still reported the order as missing in live probes.",
            ),
        ),
    )

    cli_main.data_bcdc_order(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        query_file=None,
        manifest_path=tmp_path / "manifest.json",
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="fgdb",
        email=None,
        clip=True,
    )

    assert any("feature_type: WHSE_FOREST_VEGETATION.F_OWN" in msg for msg in messages)
    assert any("order_id: 2551000" in msg for msg in messages)
    assert any("status_probe:" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert (tmp_path / "manifest.json").is_file()


def test_data_bcdc_order_uses_git_email_when_flag_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main, "_source_tree_root", lambda: tmp_path)

    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0, stdout="git-email@example.com\n", stderr=""
        )

    monkeypatch.setattr(cli_main.subprocess, "run", _fake_run)

    captured_email: list[str | None] = []

    def _fake_order(query: str, **kwargs):
        captured_email.append(kwargs["email_address"])
        return cli_main.BcdcDwdsOrderResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
            resource_id="dwds-id",
            resource_name="BC Geographic Warehouse Custom Download",
            resource_url=None,
            feature_type="WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            aoi_source="bbox",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id=None,
            geomark_url=None,
            output_format="fgdb",
            email_address=kwargs["email_address"],
            clipping_method="clip_to_aoi",
            ordering_application="FEMIC-BCDC-DWDS",
            request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
            request_payload={"featureItems": []},
            order_id="2551000",
            order_guid="guid-123",
            submission_status="SUCCESS",
            submission_description="submitted",
            submission_value="2551000",
            status_probe=None,
            warnings=(),
        )

    monkeypatch.setattr(cli_main, "submit_bcdc_dwds_order", _fake_order)

    cli_main.data_bcdc_order(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        query_file=None,
        manifest_path=None,
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="fgdb",
        email=None,
        clip=True,
    )

    assert captured_email == ["git-email@example.com"]
    assert any("email: git-email@example.com" in msg for msg in messages)


def test_data_bcdc_order_prefers_env_email_over_git(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli_main, "_source_tree_root", lambda: tmp_path)
    monkeypatch.setenv(cli_main.BCDC_DWDS_EMAIL_ENV, "env-email@example.com")

    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(
            returncode=0, stdout="git-email@example.com\n", stderr=""
        )

    monkeypatch.setattr(cli_main.subprocess, "run", _fake_run)
    captured_email: list[str | None] = []

    def _fake_order(query: str, **kwargs):
        captured_email.append(kwargs["email_address"])
        return cli_main.BcdcDwdsOrderResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
            resource_id="dwds-id",
            resource_name="BC Geographic Warehouse Custom Download",
            resource_url=None,
            feature_type="WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            aoi_source="bbox",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id=None,
            geomark_url=None,
            output_format="fgdb",
            email_address=kwargs["email_address"],
            clipping_method="clip_to_aoi",
            ordering_application="FEMIC-BCDC-DWDS",
            request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
            request_payload={"featureItems": []},
            order_id="2551000",
            order_guid="guid-123",
            submission_status="SUCCESS",
            submission_description="submitted",
            submission_value="2551000",
            status_probe=None,
            warnings=(),
        )

    monkeypatch.setattr(cli_main, "submit_bcdc_dwds_order", _fake_order)
    monkeypatch.setattr(cli_main.console, "print", lambda *_args, **_kwargs: None)

    cli_main.data_bcdc_order(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        query_file=None,
        manifest_path=None,
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="fgdb",
        email=None,
        clip=True,
    )

    assert captured_email == ["env-email@example.com"]


def test_data_bcdc_order_requires_resolvable_email(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(cli_main, "_source_tree_root", lambda: tmp_path)
    monkeypatch.delenv(cli_main.BCDC_DWDS_EMAIL_ENV, raising=False)

    def _fake_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(cli_main.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        cli_main,
        "submit_bcdc_dwds_order",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("submit_bcdc_dwds_order should not be called")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_order(
            queries=["WHSE_FOREST_VEGETATION.F_OWN"],
            query_file=None,
            manifest_path=None,
            limit=5,
            instance_root=None,
            bbox="1170000,450000,1180000,460000",
            geomark=None,
            output_format="fgdb",
            email=None,
            clip=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("DWDS orders need a notification email" in msg for msg in messages)


def test_data_bcdc_order_requires_allow_bulk_for_large_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "submit_bcdc_dwds_order",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("submit_bcdc_dwds_order should not be called")
        ),
    )

    query_file = tmp_path / "queries.txt"
    query_file.write_text(
        "\n".join(
            [
                "WHSE_FOREST_VEGETATION.F_OWN",
                "WHSE_ADMIN_BOUNDARIES.FADM_TSA",
                "WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_order(
            queries=None,
            query_file=query_file,
            manifest_path=None,
            limit=5,
            instance_root=None,
            bbox="1170000,450000,1180000,460000",
            geomark=None,
            output_format="fgdb",
            email=None,
            clip=True,
            plan_only=False,
            allow_bulk=False,
        )

    assert exc_info.value.exit_code == 1
    assert any("plan_operation: DWDS order" in msg for msg in messages)
    assert any("requested_query_count: 3" in msg for msg in messages)
    assert any("good-citizen warning:" in msg for msg in messages)
    assert any("--allow-bulk" in msg for msg in messages)


def test_data_bcdc_order_plan_only_skips_submission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "submit_bcdc_dwds_order",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("submit_bcdc_dwds_order should not be called")
        ),
    )

    cli_main.data_bcdc_order(
        queries=["WHSE_FOREST_VEGETATION.F_OWN"],
        query_file=None,
        manifest_path=None,
        limit=5,
        instance_root=None,
        bbox="1170000,450000,1180000,460000",
        geomark=None,
        output_format="fgdb",
        email=None,
        clip=True,
        plan_only=True,
        allow_bulk=False,
    )

    assert any("plan_operation: DWDS order" in msg for msg in messages)
    assert any("plan_only:" in msg for msg in messages)


def test_data_bcdc_order_query_file_with_geomark(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "resolve_geomark_bbox_3005",
        lambda _value: SimpleNamespace(
            geomark_id="gm-demo",
            geomark_url="https://apps.gov.bc.ca/pub/geomark/geomarks/gm-demo",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
        ),
    )
    captured_queries: list[str] = []

    def _fake_order(query: str, **kwargs):
        captured_queries.append(query)
        assert kwargs["geomark"] is not None
        return cli_main.BcdcDwdsOrderResult(
            query=query,
            limit=5,
            generated_utc="2026-04-04T00:00:00+00:00",
            package_id="pkg-f-own",
            package_name="generalized-forest-cover-ownership",
            package_title="Generalized Forest Cover Ownership",
            dataset_page_url="https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
            resource_id="dwds-id",
            resource_name="BC Geographic Warehouse Custom Download",
            resource_url=None,
            feature_type="WHSE_FOREST_VEGETATION.F_OWN",
            matched_by="object_name:WHSE_FOREST_VEGETATION.F_OWN",
            aoi_source="geomark",
            bbox_epsg3005=(1170000.0, 450000.0, 1180000.0, 460000.0),
            geomark_id="gm-demo",
            geomark_url="https://apps.gov.bc.ca/pub/geomark/geomarks/gm-demo",
            output_format="fgdb",
            email_address="user@example.com",
            clipping_method="clip_to_aoi",
            ordering_application="FEMIC-BCDC-DWDS",
            request_url="https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
            request_payload={"featureItems": []},
            order_id="2551001",
            order_guid="guid-124",
            submission_status="SUCCESS",
            submission_description="submitted",
            submission_value="2551001",
            status_probe=None,
            warnings=(),
        )

    monkeypatch.setattr(cli_main, "submit_bcdc_dwds_order", _fake_order)

    query_file = tmp_path / "queries.txt"
    query_file.write_text("WHSE_FOREST_VEGETATION.F_OWN\n", encoding="utf-8")

    cli_main.data_bcdc_order(
        queries=None,
        query_file=query_file,
        manifest_path=None,
        limit=5,
        instance_root=None,
        bbox=None,
        geomark="gm-demo",
        output_format="fgdb",
        email="user@example.com",
        clip=True,
    )

    assert captured_queries == ["WHSE_FOREST_VEGETATION.F_OWN"]
    assert any("geomark: gm-demo" in msg for msg in messages)


def test_data_bcdc_order_requires_exactly_one_aoi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_order(
            queries=["WHSE_FOREST_VEGETATION.F_OWN"],
            query_file=None,
            manifest_path=None,
            limit=5,
            instance_root=None,
            bbox=None,
            geomark=None,
            output_format="fgdb",
            email=None,
            clip=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("supply exactly one AOI input" in msg for msg in messages)


def test_data_bcdc_order_reports_order_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "submit_bcdc_dwds_order",
        lambda query, **_kwargs: (_ for _ in ()).throw(
            cli_main.BcdcDwdsError("DWDS does not report public download permission")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_order(
            queries=["WHSE_FOREST_VEGETATION.F_OWN"],
            query_file=None,
            manifest_path=None,
            limit=5,
            instance_root=None,
            bbox="1170000,450000,1180000,460000",
            geomark=None,
            output_format="fgdb",
            email=None,
            clip=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("BCDC order error:" in msg for msg in messages)


def test_data_bcdc_order_followup_prints_materialization_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    manifest_path = tmp_path / "order_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "query": "WHSE_FOREST_VEGETATION.F_OWN",
                "limit": 5,
                "generated_utc": "2026-04-04T00:00:00+00:00",
                "package_id": "pkg-f-own",
                "package_name": "generalized-forest-cover-ownership",
                "package_title": "Generalized Forest Cover Ownership",
                "dataset_page_url": "https://catalogue.data.gov.bc.ca/dataset/generalized-forest-cover-ownership",
                "resource_id": "dwds-id",
                "resource_name": "BC Geographic Warehouse Custom Download",
                "resource_url": None,
                "feature_type": "WHSE_FOREST_VEGETATION.F_OWN",
                "matched_by": "object_name:WHSE_FOREST_VEGETATION.F_OWN",
                "aoi_source": "bbox",
                "bbox_epsg3005": [1170000.0, 450000.0, 1180000.0, 460000.0],
                "geomark_id": None,
                "geomark_url": None,
                "output_format": "fgdb",
                "email_address": None,
                "clipping_method": "clip_to_aoi",
                "ordering_application": "FEMIC-BCDC-DWDS",
                "request_url": "https://apps.gov.bc.ca/pub/dwds-ofi/order/createOrderFiltered",
                "request_payload": {"featureItems": []},
                "order_id": "2551000",
                "order_guid": "guid-123",
                "submission_status": "SUCCESS",
                "submission_description": "submitted",
                "submission_value": "2551000",
                "status_probe": None,
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli_main,
        "follow_up_bcdc_dwds_order",
        lambda order, **_kwargs: cli_main.BcdcDwdsOrderResult(
            **{
                **order.__dict__,
                "latest_followup_utc": "2026-04-06T00:00:00+00:00",
                "latest_followup_status_probe": cli_main.BcdcDwdsStatusProbe(
                    order_id=order.order_id,
                    raw_payload={"Status": "SUCCESS"},
                    status="SUCCESS",
                    description="ready",
                    value=order.order_id,
                    download_url="https://example.invalid/order_2551000.zip",
                ),
                "status_probe": cli_main.BcdcDwdsStatusProbe(
                    order_id=order.order_id,
                    raw_payload={"Status": "SUCCESS"},
                    status="SUCCESS",
                    description="ready",
                    value=order.order_id,
                    download_url="https://example.invalid/order_2551000.zip",
                ),
                "materialized_artifact_path": str(tmp_path / "order_2551000.zip"),
                "materialized_download_url": "https://example.invalid/order_2551000.zip",
                "materialized_content_type": "application/zip",
                "materialized_bytes": 1234,
                "followup_warnings": (),
            }
        ),
    )

    cli_main.data_bcdc_order_followup(
        order_manifest=manifest_path,
        manifest_path=tmp_path / "followup_manifest.json",
        download_root=tmp_path / "downloads",
        instance_root=None,
        download=True,
        poll_status=True,
    )

    assert any("materialized_artifact_path:" in msg for msg in messages)
    assert any("latest_followup_utc:" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert (tmp_path / "followup_manifest.json").is_file()


def test_data_bcdc_order_followup_reports_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    manifest_path = tmp_path / "missing_status_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        cli_main,
        "load_bcdc_dwds_manifest",
        lambda _path: (_ for _ in ()).throw(cli_main.BcdcDwdsError("bad manifest")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.data_bcdc_order_followup(
            order_manifest=manifest_path,
            manifest_path=None,
            download_root=None,
            instance_root=None,
            download=True,
            poll_status=True,
        )

    assert exc_info.value.exit_code == 1
    assert any("BCDC order follow-up error:" in msg for msg in messages)


def test_tsr_index_writes_canonical_registry_under_repo_metadata_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    result = cli_main.TsrIndexResult(
        generated_utc="2026-04-04T00:00:00+00:00",
        landing_url=tsr_catalog.DEFAULT_TSR_LANDING_URL,
        publish_root_url=tsr_catalog.DEFAULT_TSR_PUBLISH_ROOT_URL,
        tsa_root_url=tsr_catalog.DEFAULT_TSR_TSA_ROOT_URL,
        landing_resources=(),
        registry=(),
        documents=(),
    )
    written = cli_main.TsrWrittenIndex(
        output_root=repo_root / "metadata" / "tsr",
        registry_path=repo_root / "metadata" / "tsr" / "tsa_registry.json",
        documents_path=repo_root / "metadata" / "tsr" / "tsa_documents.json",
        tsa_count=0,
        document_count=0,
    )
    monkeypatch.setattr(cli_main, "index_tsr_tsa_surfaces", lambda: result)
    captured_roots: list[Path] = []

    def _fake_write(index_result, output_root):
        assert index_result is result
        captured_roots.append(output_root)
        return written

    monkeypatch.setattr(cli_main, "write_tsr_index", _fake_write)

    cli_main.tsr_index(output_root=None)

    assert captured_roots == [repo_root / "metadata" / "tsr"]
    assert any("tsa_count: 0" in msg for msg in messages)
    assert any(str(written.registry_path) in msg for msg in messages)


def test_tsr_index_supports_relative_output_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    monkeypatch.setattr(cli_main.console, "print", lambda *_args, **_kwargs: None)

    result = cli_main.TsrIndexResult(
        generated_utc="2026-04-04T00:00:00+00:00",
        landing_url=tsr_catalog.DEFAULT_TSR_LANDING_URL,
        publish_root_url=tsr_catalog.DEFAULT_TSR_PUBLISH_ROOT_URL,
        tsa_root_url=tsr_catalog.DEFAULT_TSR_TSA_ROOT_URL,
        landing_resources=(),
        registry=(),
        documents=(),
    )
    written = cli_main.TsrWrittenIndex(
        output_root=repo_root / "runtime" / "tsr-smoke",
        registry_path=repo_root / "runtime" / "tsr-smoke" / "tsa_registry.json",
        documents_path=repo_root / "runtime" / "tsr-smoke" / "tsa_documents.json",
        tsa_count=0,
        document_count=0,
    )
    monkeypatch.setattr(cli_main, "index_tsr_tsa_surfaces", lambda: result)
    captured_roots: list[Path] = []

    def _fake_write(index_result, output_root):
        assert index_result is result
        captured_roots.append(output_root)
        return written

    monkeypatch.setattr(cli_main, "write_tsr_index", _fake_write)

    cli_main.tsr_index(output_root=Path("runtime/tsr-smoke"))

    assert captured_roots == [repo_root / "runtime" / "tsr-smoke"]


def test_tsr_index_reports_catalog_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "index_tsr_tsa_surfaces",
        lambda: (_ for _ in ()).throw(cli_main.TsrCatalogError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_index(output_root=None)

    assert exc_info.value.exit_code == 1
    assert any("TSR index error:" in msg for msg in messages)


def test_tsr_fetch_uses_repo_relative_defaults_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    user_corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    user_manifest_path = tmp_path / ".femic" / "tsr" / "tsa_pdf_cache_manifest.json"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main, "default_femic_tsr_corpus_root", lambda: user_corpus_root
    )
    monkeypatch.setattr(
        cli_main,
        "default_femic_tsr_cache_manifest_path",
        lambda: user_manifest_path,
    )

    result = cli_main.TsrFetchResult(
        generated_utc="2026-04-04T00:00:00+00:00",
        documents_path=repo_root / "metadata" / "tsr" / "tsa_documents.json",
        corpus_root=user_corpus_root,
        manifest_path=user_manifest_path,
        selected_tsa_filters=("29",),
        selected_document_count=3,
        cached_documents=(),
        failures=(),
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_fetch(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(cli_main, "fetch_tsr_pdfs", _fake_fetch)

    cli_main.tsr_fetch(
        documents_path=None,
        corpus_root=None,
        manifest_path=None,
        tsa=["29"],
        max_documents=3,
    )

    assert (
        captured_kwargs["documents_path"]
        == repo_root / "metadata" / "tsr" / "tsa_documents.json"
    )
    assert captured_kwargs["corpus_root"] == user_corpus_root
    assert captured_kwargs["manifest_path"] == user_manifest_path
    assert captured_kwargs["tsa_filters"] == ("29",)
    assert captured_kwargs["max_documents"] == 3
    assert captured_kwargs["source_root"] == repo_root
    assert any("selected_document_count: 3" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)


def test_tsr_fetch_reports_cache_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "default_femic_tsr_corpus_root",
        lambda: Path("C:/tmp/.femic/tsr/corpus"),
    )
    monkeypatch.setattr(
        cli_main,
        "default_femic_tsr_cache_manifest_path",
        lambda: Path("C:/tmp/.femic/tsr/tsa_pdf_cache_manifest.json"),
    )
    monkeypatch.setattr(
        cli_main,
        "fetch_tsr_pdfs",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.TsrCacheError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_fetch(
            documents_path=None,
            corpus_root=None,
            manifest_path=None,
            tsa=None,
            max_documents=None,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR fetch error:" in msg for msg in messages)


def test_tsr_extract_writes_candidate_facts_under_repo_metadata_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    user_corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main, "default_femic_tsr_corpus_root", lambda: user_corpus_root
    )

    result = cli_main.TsrExtractResult(
        generated_utc="2026-04-04T00:00:00+00:00",
        documents_path=repo_root / "metadata" / "tsr" / "tsa_documents.json",
        corpus_root=user_corpus_root,
        output_path=repo_root / "metadata" / "tsr" / "tsa_candidate_facts.json",
        selected_tsa_filters=("29",),
        selected_document_count=3,
        extracted_documents_count=2,
        facts=(),
        failures=(),
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_extract(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(cli_main, "extract_tsr_candidate_facts", _fake_extract)

    cli_main.tsr_extract(
        documents_path=None,
        corpus_root=None,
        output_path=None,
        tsa=["29"],
        max_documents=3,
    )

    assert (
        captured_kwargs["documents_path"]
        == repo_root / "metadata" / "tsr" / "tsa_documents.json"
    )
    assert captured_kwargs["corpus_root"] == user_corpus_root
    assert (
        captured_kwargs["output_path"]
        == repo_root / "metadata" / "tsr" / "tsa_candidate_facts.json"
    )
    assert captured_kwargs["tsa_filters"] == ("29",)
    assert captured_kwargs["max_documents"] == 3
    assert captured_kwargs["source_root"] == repo_root
    assert any("fact_count: 0" in msg for msg in messages)
    assert any("output_path:" in msg for msg in messages)


def test_tsr_extract_reports_extract_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "default_femic_tsr_corpus_root",
        lambda: Path("C:/tmp/.femic/tsr/corpus"),
    )
    monkeypatch.setattr(
        cli_main,
        "extract_tsr_candidate_facts",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.TsrExtractError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_extract(
            documents_path=None,
            corpus_root=None,
            output_path=None,
            tsa=None,
            max_documents=None,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR extract error:" in msg for msg in messages)


def test_tsr_overlay_init_writes_instance_local_overlay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    result = cli_main.TsrOverlayInitResult(
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        canonical_summary=tsr_catalog.TsrOverlayCanonicalSummary(
            candidate_fact_count=4,
            document_count=2,
            fact_family_counts={"source_layer_candidate": 2},
            candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
            documents_path="metadata/tsr/tsa_documents.json",
            registry_path="metadata/tsr/tsa_registry.json",
        ),
        created=True,
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_init(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(cli_main, "init_tsr_overlay", _fake_init)

    cli_main.tsr_overlay_init(
        tsa="29",
        instance_root=instance_root,
        registry_path=None,
        documents_path=None,
        candidate_facts_path=None,
        overlay_path=None,
        overwrite=False,
    )

    assert captured_kwargs["instance_root"] == instance_root.resolve()
    assert captured_kwargs["tsa"] == "29"
    assert (
        captured_kwargs["registry_path"]
        == repo_root / "metadata" / "tsr" / "tsa_registry.json"
    )
    assert (
        captured_kwargs["candidate_facts_path"]
        == repo_root / "metadata" / "tsr" / "tsa_candidate_facts.json"
    )
    assert any("overlay_path:" in msg for msg in messages)
    assert any("tsa_id: tsa_29" in msg for msg in messages)


def test_tsr_overlay_init_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "init_tsr_overlay",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.TsrOverlayError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_overlay_init(
            tsa="29",
            instance_root=Path("instance"),
            registry_path=None,
            documents_path=None,
            candidate_facts_path=None,
            overlay_path=None,
            overwrite=False,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR overlay init error:" in msg for msg in messages)


def test_tsr_recipe_init_writes_instance_local_recipe_scaffolds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    result = cli_main.TsrRecipeInitResult(
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        source_layers_recipe_path=instance_root
        / "config"
        / "tsr"
        / "source_layers.recipe.yaml",
        thlb_netdown_recipe_path=instance_root
        / "config"
        / "tsr"
        / "thlb_netdown.recipe.yaml",
        created_source_layers_recipe=True,
        created_thlb_netdown_recipe=True,
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_init(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(cli_main, "init_tsr_recipe_scaffolds", _fake_init)

    cli_main.tsr_recipe_init(
        tsa="29",
        instance_root=instance_root,
        registry_path=None,
        documents_path=None,
        candidate_facts_path=None,
        overlay_path=None,
        overrides_path=None,
        source_layers_recipe_path=None,
        thlb_netdown_recipe_path=None,
        overwrite=False,
    )

    assert captured_kwargs["instance_root"] == instance_root.resolve()
    assert captured_kwargs["tsa"] == "29"
    assert (
        captured_kwargs["registry_path"]
        == repo_root / "metadata" / "tsr" / "tsa_registry.json"
    )
    assert (
        captured_kwargs["source_layers_recipe_path"]
        == (instance_root / "config" / "tsr" / "source_layers.recipe.yaml").resolve()
    )
    assert (
        captured_kwargs["thlb_netdown_recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert any("source_layers_recipe_path:" in msg for msg in messages)
    assert any("thlb_netdown_recipe_path:" in msg for msg in messages)


def test_tsr_recipe_init_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "init_tsr_recipe_scaffolds",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.TsrRecipeError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_recipe_init(
            tsa="29",
            instance_root=Path("instance"),
            registry_path=None,
            documents_path=None,
            candidate_facts_path=None,
            overlay_path=None,
            overrides_path=None,
            source_layers_recipe_path=None,
            thlb_netdown_recipe_path=None,
            overwrite=False,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR recipe init error:" in msg for msg in messages)


def test_tsr_source_layers_build_uses_default_recipe_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrSourceLayersRecipeBuildResult(
            recipe_path=instance_root / "config" / "tsr" / "source_layers.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            entry_count=3,
            status_counts={"exact_hit": 2, "alias_hit": 1},
        )

    monkeypatch.setattr(cli_main, "build_tsr_source_layers_recipe", _fake_build)

    cli_main.tsr_source_layers_build(
        instance_root=instance_root,
        source_layers_recipe_path=None,
        limit=5,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "source_layers.recipe.yaml").resolve()
    )
    assert captured_kwargs["source_root"] == repo_root
    assert any("entry_count: 3" in msg for msg in messages)


def test_tsr_source_layers_run_requires_exactly_one_aoi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_source_layers_run(
            instance_root=Path("instance"),
            source_layers_recipe_path=None,
            bbox=None,
            geomark=None,
            limit=5,
            allow_order=False,
        )

    assert exc_info.value.exit_code == 1
    assert any(
        "Supply exactly one of `--bbox` or `--geomark`." in msg for msg in messages
    )


def test_tsr_thlb_netdown_build_uses_default_recipe_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbNetdownRecipeBuildResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            step_count=4,
            step_kind_counts={"netdown_rule": 3, "reference_target": 1},
            status_counts={"ready": 3, "needs_review": 1},
            selected_document_paths=("TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",),
        )

    monkeypatch.setattr(cli_main, "build_tsr_thlb_netdown_recipe", _fake_build)

    cli_main.tsr_thlb_netdown_build(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert captured_kwargs["source_root"] == repo_root
    assert any("step_count: 4" in msg for msg in messages)
    assert any(
        "selected_document_path: TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf" in msg
        for msg in messages
    )


def test_tsr_thlb_workbench_build_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbWorkbenchBuildResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            notebook_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.workbench.ipynb",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            parent_step_count=5,
            compiled_logic_count=9,
            stage_counts={"glb_to_aflb": 2, "lhlb_to_thlb": 3},
        )

    monkeypatch.setattr(cli_main, "build_tsr_thlb_workbench", _fake_build)

    cli_main.tsr_thlb_netdown_workbench_build(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        workbench_path=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert (
        captured_kwargs["notebook_path"]
        == (
            instance_root / "workbench" / "tsr" / "thlb_netdown.workbench.ipynb"
        ).resolve()
    )
    assert any("parent_step_count: 5" in msg for msg in messages)
    assert any("compiled_logic_count: 9" in msg for msg in messages)


def test_tsr_thlb_warmstart_build_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbWarmstartBuildResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            markdown_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.warmstart.md",
            yaml_path=instance_root / "config" / "tsr" / "thlb_warmstart.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            milestone_count=4,
            parent_step_count=12,
            warmstart_status_counts={
                "compiled_ready": 6,
                "review_pattern_match": 3,
                "blocked_missing_source": 2,
                "manual_or_aspatial": 1,
            },
        )

    monkeypatch.setattr(cli_main, "build_tsr_thlb_warmstart", _fake_build)

    cli_main.tsr_thlb_netdown_warmstart_build(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        output_markdown=None,
        output_yaml=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert (
        captured_kwargs["markdown_path"]
        == (instance_root / "workbench" / "tsr" / "thlb_netdown.warmstart.md").resolve()
    )
    assert (
        captured_kwargs["yaml_path"]
        == (instance_root / "config" / "tsr" / "thlb_warmstart.yaml").resolve()
    )
    assert any("markdown_path:" in msg for msg in messages)
    assert any("yaml_path:" in msg for msg in messages)
    assert any("warmstart_status_compiled_ready: 6" in msg for msg in messages)


def test_tsr_thlb_reconstruction_compare_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = tmp_path / "repo" / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbReconstructionComparisonBuildResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            markdown_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstruction_comparison.md",
            json_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstruction_comparison.json",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            parent_step_count=20,
            comparison_bucket_counts={
                "close_match": 4,
                "strict_overcut_candidate": 3,
                "reviewed_bridge_only": 2,
            },
        )

    monkeypatch.setattr(
        cli_main, "build_tsr_thlb_reconstruction_comparison", _fake_build
    )

    cli_main.tsr_thlb_reconstruction_compare(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        reconstructed_audit_path=None,
        reviewed_status_path=None,
        output_markdown=None,
        output_json=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert (
        captured_kwargs["reconstructed_audit_path"]
        == (
            instance_root / "config" / "tsr" / "thlb_reconstructed.audit.json"
        ).resolve()
    )
    assert (
        captured_kwargs["reviewed_status_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.status.md").resolve()
    )
    assert (
        captured_kwargs["output_markdown_path"]
        == (
            instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.md"
        ).resolve()
    )
    assert (
        captured_kwargs["output_json_path"]
        == (
            instance_root / "config" / "tsr" / "thlb_reconstruction_comparison.json"
        ).resolve()
    )
    assert any("comparison_bucket_close_match: 4" in msg for msg in messages)
    assert any("markdown_path:" in msg for msg in messages)
    assert any("json_path:" in msg for msg in messages)


def test_tsr_thlb_workbench_lock_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_lock(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbWorkbenchLockResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            notebook_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.workbench.ipynb",
            locked_script_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.py",
            locked_recipe_path=instance_root
            / "workbench"
            / "tsr"
            / "thlb_netdown.locked.recipe.yaml",
            frozen_status_report_path=instance_root
            / "workbench"
            / "tsr"
            / "frozen"
            / "thlb_netdown.status.locked-20260405T000000Z.md",
            frozen_audit_path=instance_root
            / "workbench"
            / "tsr"
            / "frozen"
            / "thlb_netdown.audit.locked-20260405T000000Z.json",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            lock_scope="all",
        )

    monkeypatch.setattr(cli_main, "lock_tsr_thlb_workbench", _fake_lock)

    cli_main.tsr_thlb_netdown_workbench_lock(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        workbench_path=None,
        lock_scope="all",
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert (
        captured_kwargs["notebook_path"]
        == (
            instance_root / "workbench" / "tsr" / "thlb_netdown.workbench.ipynb"
        ).resolve()
    )
    assert captured_kwargs["lock_scope"] == "all"
    assert any("locked_script_path:" in msg for msg in messages)
    assert any("lock_scope: all" in msg for msg in messages)


def test_tsr_thlb_netdown_step_run_uses_default_recipe_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbParentStepRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
            parent_label="Land not administered by the Province",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "ria_vri_vclr1p_checkpoint1.feather",
            selected_map_ids=("092O071",),
            selected_landscape_units=(),
            output_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "notebook_runs"
            / "thlb_parent_002.feather",
            result_json_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "notebook_runs"
            / "thlb_parent_002.json",
            status="applied",
            executed_parent_step_ids=(
                "thlb_parent_002_land_not_administered_by_the_province",
            ),
            input_area_ha=2.0,
            removed_area_ha=1.0,
            remaining_area_ha=1.0,
            benchmark_marginal_area_ha=1.0,
            benchmark_cumulative_area_ha=1.0,
            benchmark_marginal_delta_ha=0.0,
            benchmark_cumulative_delta_ha=0.0,
            smoke_benchmark_scale_factor=None,
            scaled_benchmark_marginal_area_ha=None,
            scaled_benchmark_cumulative_area_ha=None,
            scaled_benchmark_marginal_delta_ha=None,
            scaled_benchmark_cumulative_delta_ha=None,
            notes=("Used smoke subset 092O071",),
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_parent_step", _fake_run)

    cli_main.tsr_thlb_netdown_step_run(
        instance_root=instance_root,
        parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
        thlb_netdown_recipe_path=None,
        checkpoint_path=None,
        map_id=None,
        landscape_unit=None,
        auto_map_id_smoke_subset=True,
        execution_mode=cli_main.TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
        max_workers=None,
        lu_bundle_count=None,
        progress_root=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert captured_kwargs["checkpoint_path"] is None
    assert captured_kwargs["map_ids"] == ()
    assert captured_kwargs["landscape_units"] == ()
    assert captured_kwargs["auto_map_id_smoke_subset"] is True
    assert captured_kwargs["lu_bundle_count"] is None
    assert captured_kwargs["progress_root"] is None
    assert any("parent_step_id:" in msg for msg in messages)


def test_instance_mkrf_init_runtime_package_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-mkrf-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_init(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            package_root=instance_root / "models" / "mkrf_patchworks_model",
            readme_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "README.md",
            manifest_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "runtime_package_init_manifest.json",
            curve_status_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "runtime_curve_status.csv",
            analysis_au_runtime_status_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "au_runtime_status.csv",
            analysis_au_curve_refs_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "au_curve_refs.csv",
            species_share_audit_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "runtime_species_share_audit.csv",
            analysis_pin_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "base.pin",
            headless_runtime_common_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "analysis"
            / "headless_runtime_common.bsh",
            flow_targets_script_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "scripts"
            / "targets"
            / "flowtargets.bsh",
            xml_contract_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "xml"
            / "runtime_curve_contract.xml",
            xml_curve_bank_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "xml"
            / "runtime_curve_bank.xml",
            forestmodel_xml_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "xml"
            / "forestmodel.xml",
            selected_au_count=31,
            first_growth_curve_au_count=20,
            first_growth_missing_au_count=11,
            managed_curve_au_count=31,
        )

    monkeypatch.setattr(cli_main, "initialize_mkrf_runtime_package", _fake_init)

    cli_main.instance_mkrf_init_runtime_package(
        package_root=Path("models/mkrf_patchworks_model"),
        selected_au_csv=Path("data/model_input_bundle/selected_au_table.csv"),
        stand_origin_assignment_csv=Path(
            "data/model_input_bundle/stand_origin_assignment.csv"
        ),
        stand_au_assignment_csv=Path("data/model_input_bundle/stand_au_assignment.csv"),
        managed_bootstrap_csv=Path(
            "data/model_input_bundle/managed_au_bootstrap_table.csv"
        ),
        first_growth_curves_csv=Path(
            "data/model_input_bundle/first_growth_au_curves.csv"
        ),
        first_growth_diagnostics_csv=Path(
            "data/model_input_bundle/first_growth_au_fit_diagnostics.csv"
        ),
        managed_curves_csv=Path("data/model_input_bundle/managed_au_curves.csv"),
        managed_run_manifest_json=Path(
            "data/model_input_bundle/managed_au_run_manifest.json"
        ),
        bad_curve_audit_summary_csv=Path(
            "data/model_input_bundle/bad_curve_audit_summary.csv"
        ),
        instance_root=instance_root,
    )

    assert (
        captured_kwargs["package_root"]
        == (instance_root / "models" / "mkrf_patchworks_model").resolve()
    )
    assert (
        captured_kwargs["selected_au_csv"]
        == (
            instance_root / "data" / "model_input_bundle" / "selected_au_table.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["stand_origin_assignment_csv"]
        == (
            instance_root
            / "data"
            / "model_input_bundle"
            / "stand_origin_assignment.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["stand_au_assignment_csv"]
        == (
            instance_root / "data" / "model_input_bundle" / "stand_au_assignment.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["managed_bootstrap_csv"]
        == (
            instance_root
            / "data"
            / "model_input_bundle"
            / "managed_au_bootstrap_table.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["first_growth_curves_csv"]
        == (
            instance_root / "data" / "model_input_bundle" / "first_growth_au_curves.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["first_growth_diagnostics_csv"]
        == (
            instance_root
            / "data"
            / "model_input_bundle"
            / "first_growth_au_fit_diagnostics.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["managed_curves_csv"]
        == (
            instance_root / "data" / "model_input_bundle" / "managed_au_curves.csv"
        ).resolve()
    )
    assert (
        captured_kwargs["managed_run_manifest_json"]
        == (
            instance_root
            / "data"
            / "model_input_bundle"
            / "managed_au_run_manifest.json"
        ).resolve()
    )
    assert (
        captured_kwargs["bad_curve_audit_summary_csv"]
        == (
            instance_root
            / "data"
            / "model_input_bundle"
            / "bad_curve_audit_summary.csv"
        ).resolve()
    )
    assert any("mkrf runtime package initialized" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)
    assert any("curve_status_csv:" in msg for msg in messages)
    assert any("analysis_au_runtime_status_csv:" in msg for msg in messages)
    assert any("analysis_au_curve_refs_csv:" in msg for msg in messages)
    assert any("runtime_species_share_audit_csv:" in msg for msg in messages)
    assert any("xml_contract:" in msg for msg in messages)
    assert any("xml_curve_bank:" in msg for msg in messages)
    assert any("forestmodel_xml:" in msg for msg in messages)


def test_instance_mkrf_audit_runtime_sanity_uses_resolved_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-mkrf-instance"
    stage_dir = repo_root / "runtime" / "logs" / "headless_stage" / "demo"
    stage_dir.mkdir(parents=True)
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_audit(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            package_root=(instance_root / "models" / "mkrf_patchworks_model").resolve(),
            stage_dir=stage_dir.resolve(),
            audit_csv_path=(
                stage_dir / "sanity" / "mkrf_runtime_sanity_audit.csv"
            ).resolve(),
            summary_json_path=(
                stage_dir / "sanity" / "mkrf_runtime_sanity_summary.json"
            ).resolve(),
            row_count=24,
            failure_count=1,
        )

    monkeypatch.setattr(cli_main, "audit_mkrf_runtime_sanity", _fake_audit)

    cli_main.instance_mkrf_audit_runtime_sanity(
        package_root=Path("models/mkrf_patchworks_model"),
        stage_dir=stage_dir,
        instance_root=instance_root,
    )

    assert (
        captured_kwargs["package_root"]
        == (instance_root / "models" / "mkrf_patchworks_model").resolve()
    )
    assert captured_kwargs["stage_dir"] == stage_dir.resolve()
    assert any("mkrf runtime sanity audit complete" in msg for msg in messages)
    assert any("audit_csv:" in msg for msg in messages)
    assert any("summary_json:" in msg for msg in messages)


def test_instance_mkrf_publish_runtime_spatial_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-mkrf-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_publish(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            package_root=instance_root / "models" / "mkrf_patchworks_model",
            spatial_dir=instance_root / "models" / "mkrf_patchworks_model" / "spatial",
            fragments_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "spatial"
            / "fragments.shp",
            manifest_path=instance_root
            / "models"
            / "mkrf_patchworks_model"
            / "spatial"
            / "runtime_spatial_manifest.json",
            source_feature_count=1873,
            published_feature_count=1763,
            excluded_feature_count=110,
        )

    monkeypatch.setattr(cli_main, "publish_mkrf_runtime_spatial_handoff", _fake_publish)

    cli_main.instance_mkrf_publish_runtime_spatial(
        resultant_gdb=instance_root / "data" / "source" / "Resultant.gdb",
        package_root=Path("models/mkrf_patchworks_model"),
        instance_root=instance_root,
    )

    assert (
        captured_kwargs["resultant_gdb"]
        == (instance_root / "data" / "source" / "Resultant.gdb").resolve()
    )
    assert (
        captured_kwargs["package_root"]
        == (instance_root / "models" / "mkrf_patchworks_model").resolve()
    )
    assert any("mkrf runtime spatial published" in msg for msg in messages)
    assert any("fragments:" in msg for msg in messages)
    assert any("manifest:" in msg for msg in messages)


def test_tsr_thlb_netdown_step_run_accepts_explicit_aflb_yield_ready_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbParentStepRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            parent_step_id="thlb_parent_014_sites_with_low_growing_timber_potential",
            parent_label="Sites with low growing timber potential",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "aflb_yield_ready_checkpoint.feather",
            selected_map_ids=("092O071",),
            selected_landscape_units=(),
            output_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "notebook_runs"
            / "thlb_parent_014.feather",
            result_json_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "notebook_runs"
            / "thlb_parent_014.json",
            status="applied",
            executed_parent_step_ids=(
                "thlb_parent_014_sites_with_low_growing_timber_potential",
            ),
            input_area_ha=2.0,
            removed_area_ha=1.0,
            remaining_area_ha=1.0,
            benchmark_marginal_area_ha=1.0,
            benchmark_cumulative_area_ha=1.0,
            benchmark_marginal_delta_ha=0.0,
            benchmark_cumulative_delta_ha=0.0,
            smoke_benchmark_scale_factor=None,
            scaled_benchmark_marginal_area_ha=None,
            scaled_benchmark_cumulative_area_ha=None,
            scaled_benchmark_marginal_delta_ha=None,
            scaled_benchmark_cumulative_delta_ha=None,
            notes=("Explicit yield-ready checkpoint restart",),
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_parent_step", _fake_run)

    cli_main.tsr_thlb_netdown_step_run(
        instance_root=instance_root,
        parent_step_id="thlb_parent_014_sites_with_low_growing_timber_potential",
        thlb_netdown_recipe_path=None,
        checkpoint_path=Path("data/tsr/aflb_yield_ready_checkpoint.feather"),
        map_id=["092O071"],
        landscape_unit=None,
        auto_map_id_smoke_subset=False,
        execution_mode=cli_main.TSR_THLB_PARENT_STEP_EXECUTION_MODE_SERIAL,
        max_workers=None,
        lu_bundle_count=None,
        progress_root=None,
    )

    assert (
        captured_kwargs["checkpoint_path"]
        == (
            instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
        ).resolve()
    )
    assert captured_kwargs["map_ids"] == ("092O071",)
    assert captured_kwargs["auto_map_id_smoke_subset"] is False


def test_tsr_thlb_netdown_parallel_benchmark_uses_default_recipe_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbParallelBenchmarkResult(
            summary_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "parallel_benchmarks"
            / "summary.md",
            parent_step_ids=("thlb_parent_007_old_growth_management_areas",),
            landscape_units=("Williams Lake",),
            run_results=(
                tsr_catalog.TsrThlbParallelBenchmarkRunResult(
                    parent_step_id="thlb_parent_007_old_growth_management_areas",
                    parent_label="Old growth management areas",
                    execution_mode="serial",
                    worker_count=1,
                    lu_count=1,
                    wall_time_seconds=1.0,
                    peak_memory_mb=None,
                    status="applied",
                    input_area_ha=2.0,
                    removed_area_ha=0.5,
                    remaining_area_ha=1.5,
                    output_row_count=2,
                    result_json_path=instance_root / "runtime" / "logs" / "serial.json",
                    output_path=instance_root / "runtime" / "logs" / "serial.feather",
                    parity_with_serial=True,
                    parity_removed_area_delta_ha=0.0,
                    parity_remaining_area_delta_ha=0.0,
                    notes=(),
                ),
            ),
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_parallel_benchmark", _fake_run)

    cli_main.tsr_thlb_netdown_parallel_benchmark(
        instance_root=instance_root,
        parent_step_id=["thlb_parent_007_old_growth_management_areas"],
        thlb_netdown_recipe_path=None,
        checkpoint_path=None,
        landscape_unit=["Williams Lake"],
        worker_count=[1, 2],
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert captured_kwargs["checkpoint_path"] is None
    assert captured_kwargs["landscape_units"] == ("Williams Lake",)
    assert captured_kwargs["worker_counts"] == (1, 2)
    assert any("summary_path:" in msg for msg in messages)
    assert any("benchmark_run:" in msg for msg in messages)


def test_tsr_thlb_netdown_run_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbNetdownRecipeRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "ria_vri_vclr1p_checkpoint8.feather",
            output_path=instance_root
            / "data"
            / "tsr"
            / "thlb_netdown_checkpoint.feather",
            audit_path=instance_root / "config" / "tsr" / "thlb_netdown.audit.json",
            status_report_path=instance_root
            / "config"
            / "tsr"
            / "thlb_netdown.status.md",
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_netdown_status_report-20260405T000000Z.md",
            aflb_checkpoint_path=None,
            aflb_gpkg_path=None,
            aflb_lu_cache_warmed=False,
            lhlb_checkpoint_path=None,
            lhlb_gpkg_path=None,
            lhlb_lu_cache_warmed=False,
            lhlb_curve_ready_checkpoint_path=None,
            lhlb_curve_ready_gpkg_path=None,
            lhlb_curve_ready_lu_cache_warmed=False,
            execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_HYBRID,
            baseline_signal="thlb_raw",
            selected_map_ids=(),
            step_count=3,
            outcome_counts={"applied": 1, "unsupported": 2},
            input_area_ha=1682843.0,
            baseline_managed_area_ha=1682843.0,
            final_managed_area_ha=1513233.574,
            legacy_reference_managed_area_ha=None,
            tsr_reported_aflb_area_ha=3098168.0,
            tsr_reported_thlb_area_ha=1660053.0,
            aflb_checkpoint_area_ha=None,
            lhlb_checkpoint_area_ha=None,
            lhlb_curve_ready_checkpoint_area_ha=None,
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_netdown_recipe", _fake_run)

    cli_main.tsr_thlb_netdown_run(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        checkpoint_path=None,
        output_path=None,
        audit_path=None,
        execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_HYBRID,
        map_id=[],
        auto_map_id_smoke_subset=False,
        no_aflb_gpkg=False,
        no_lhlb_gpkg=False,
        no_lhlb_curve_ready_gpkg=False,
        parallel_mode="auto",
        max_workers=None,
        lu_bundle_count=None,
    )

    assert (
        captured_kwargs["recipe_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml").resolve()
    )
    assert captured_kwargs["checkpoint_path"] is None
    assert (
        captured_kwargs["output_path"]
        == (
            instance_root / "data" / "tsr" / "thlb_netdown_checkpoint.feather"
        ).resolve()
    )
    assert (
        captured_kwargs["audit_path"]
        == (instance_root / "config" / "tsr" / "thlb_netdown.audit.json").resolve()
    )
    assert (
        captured_kwargs["execution_mode"] == tsr_catalog.TSR_THLB_EXECUTION_MODE_HYBRID
    )
    assert captured_kwargs["map_ids"] == ()
    assert captured_kwargs["auto_map_id_smoke_subset"] is False
    assert captured_kwargs["parallel_mode"] == "auto"
    assert captured_kwargs["max_workers"] is None
    assert captured_kwargs["lu_bundle_count"] is None
    assert any("step_count: 3" in msg for msg in messages)
    assert any("execution_mode: hybrid" in msg for msg in messages)
    assert any("outcome_applied: 1" in msg for msg in messages)
    assert any("status_report_path:" in msg for msg in messages)
    assert any("tsr_reported_aflb_area_ha:" in msg for msg in messages)


def test_tsr_build_yield_bridge_resolves_instance_run_config_and_tsa(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_build(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrAflbYieldBridgeBuildResult(
            instance_root=instance_root.resolve(),
            tsa="29",
            aflb_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_checkpoint.feather"
            ).resolve(),
            strata_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_strata_checkpoint.feather"
            ).resolve(),
            au_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_au_checkpoint.feather"
            ).resolve(),
            yield_ready_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
            ).resolve(),
            manifest_path=(
                instance_root / "data" / "tsr" / "aflb_yield_bridge_manifest.json"
            ).resolve(),
            run_config_path=(
                instance_root / "config" / "run_profile.test.yaml"
            ).resolve(),
            run_config_sha256="deadbeef",
            au_table_path=(
                instance_root / "data" / "model_input_bundle" / "au_table.csv"
            ).resolve(),
            top_area_coverage=0.8,
            top_area_coverage_source="default_0_80",
            selected_strata_count=1,
            realized_coverage=0.9,
            aflb_input_row_count=4,
            au_assigned_row_count=4,
            cache_sufficiency_verdict="sufficient",
            cache_sufficiency_reasons=(),
            prior_manifest_found=True,
            yield_ready_status="ready_from_local_cache",
            execution_path="local_cache",
        )

    monkeypatch.setattr(cli_main, "build_tsr_aflb_yield_bridge", _fake_build)

    cli_main.tsr_build_yield_bridge(
        tsa=["29"],
        run_config=Path("config/run_profile.test.yaml"),
        instance_root=instance_root,
    )

    assert captured_kwargs["instance_root"] == instance_root.resolve()
    assert captured_kwargs["tsa"] == "29"
    assert (
        captured_kwargs["run_config_path"]
        == (instance_root / "config" / "run_profile.test.yaml").resolve()
    )
    assert any("aflb_yield_bridge_manifest_path:" in msg for msg in messages)
    assert any("aflb_yield_ready_checkpoint_path:" in msg for msg in messages)
    assert any("top_area_coverage_source: default_0_80" in msg for msg in messages)
    assert any("cache_sufficiency_verdict: sufficient" in msg for msg in messages)
    assert any("prior_manifest_found: True" in msg for msg in messages)
    assert any("yield_bridge_execution_path: local_cache" in msg for msg in messages)
    assert any("yield_ready_status: ready_from_local_cache" in msg for msg in messages)


def test_tsr_build_yield_bridge_does_not_exit_when_execution_recovers_insufficient_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fake_build(**kwargs):
        del kwargs
        return cli_main.TsrAflbYieldBridgeBuildResult(
            instance_root=instance_root.resolve(),
            tsa="29",
            aflb_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_checkpoint.feather"
            ).resolve(),
            strata_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_strata_checkpoint.feather"
            ).resolve(),
            au_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_au_checkpoint.feather"
            ).resolve(),
            yield_ready_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
            ).resolve(),
            manifest_path=(
                instance_root / "data" / "tsr" / "aflb_yield_bridge_manifest.json"
            ).resolve(),
            run_config_path=(
                instance_root / "config" / "run_profile.test.yaml"
            ).resolve(),
            run_config_sha256="deadbeef",
            au_table_path=(
                instance_root / "data" / "model_input_bundle" / "au_table.csv"
            ).resolve(),
            top_area_coverage=0.8,
            top_area_coverage_source="default_0_80",
            selected_strata_count=1,
            realized_coverage=0.9,
            aflb_input_row_count=4,
            au_assigned_row_count=4,
            cache_sufficiency_verdict="insufficient",
            cache_sufficiency_reasons=("No prior yield-bridge manifest found.",),
            prior_manifest_found=False,
            yield_ready_status="ready_from_bridge_execution",
            execution_path="btc_post_tipsy",
        )

    monkeypatch.setattr(cli_main, "build_tsr_aflb_yield_bridge", _fake_build)

    cli_main.tsr_build_yield_bridge(
        tsa=["29"],
        run_config=Path("config/run_profile.test.yaml"),
        instance_root=instance_root,
    )

    assert any("cache_sufficiency_verdict: insufficient" in msg for msg in messages)
    assert any("yield_bridge_execution_path: btc_post_tipsy" in msg for msg in messages)
    assert any(
        "yield_ready_status: ready_from_bridge_execution" in msg for msg in messages
    )


def test_tsr_build_yield_bridge_exits_when_yield_ready_not_written(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fake_build(**kwargs):
        del kwargs
        return cli_main.TsrAflbYieldBridgeBuildResult(
            instance_root=instance_root.resolve(),
            tsa="29",
            aflb_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_checkpoint.feather"
            ).resolve(),
            strata_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_strata_checkpoint.feather"
            ).resolve(),
            au_checkpoint_path=(
                instance_root / "data" / "tsr" / "aflb_au_checkpoint.feather"
            ).resolve(),
            yield_ready_checkpoint_path=None,
            manifest_path=(
                instance_root / "data" / "tsr" / "aflb_yield_bridge_manifest.json"
            ).resolve(),
            run_config_path=(
                instance_root / "config" / "run_profile.test.yaml"
            ).resolve(),
            run_config_sha256="deadbeef",
            au_table_path=(
                instance_root / "data" / "model_input_bundle" / "au_table.csv"
            ).resolve(),
            top_area_coverage=0.8,
            top_area_coverage_source="default_0_80",
            selected_strata_count=1,
            realized_coverage=0.9,
            aflb_input_row_count=4,
            au_assigned_row_count=4,
            cache_sufficiency_verdict="insufficient",
            cache_sufficiency_reasons=("Missing VDYP results cache.",),
            prior_manifest_found=True,
            yield_ready_status="not_ready_cache_insufficient",
            yield_ready_reason="Missing VDYP results cache.",
        )

    monkeypatch.setattr(cli_main, "build_tsr_aflb_yield_bridge", _fake_build)

    with pytest.raises(typer.Exit) as excinfo:
        cli_main.tsr_build_yield_bridge(
            tsa=["29"],
            run_config=Path("config/run_profile.test.yaml"),
            instance_root=instance_root,
        )

    assert excinfo.value.exit_code == 1
    assert any(
        "yield_ready_status: not_ready_cache_insufficient" in msg for msg in messages
    )
    assert any("TSR yield-ready promotion incomplete:" in msg for msg in messages)


def test_tsr_thlb_netdown_run_passes_map_id_smoke_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbNetdownRecipeRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "ria_vri_vclr1p_checkpoint1.feather",
            output_path=instance_root
            / "data"
            / "tsr"
            / "thlb_reconstructed_checkpoint.feather",
            audit_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.audit.json",
            status_report_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.status.md",
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260405T000000Z.md",
            aflb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "aflb_checkpoint.feather",
            aflb_gpkg_path=instance_root / "data" / "tsr" / "aflb_checkpoint.gpkg",
            aflb_lu_cache_warmed=True,
            lhlb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_checkpoint.feather",
            lhlb_gpkg_path=instance_root / "data" / "tsr" / "lhlb_checkpoint.gpkg",
            lhlb_lu_cache_warmed=True,
            lhlb_curve_ready_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_curve_ready_checkpoint.feather",
            lhlb_curve_ready_gpkg_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_curve_ready_checkpoint.gpkg",
            lhlb_curve_ready_lu_cache_warmed=True,
            execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
            baseline_signal="checkpoint1_raw_glb_initialization",
            selected_map_ids=("093J034", "093J044"),
            step_count=2,
            outcome_counts={"applied": 1, "needs_review": 1},
            input_area_ha=100000.0,
            baseline_managed_area_ha=92345.0,
            final_managed_area_ha=80123.0,
            legacy_reference_managed_area_ha=65000.0,
            tsr_reported_aflb_area_ha=3098168.0,
            tsr_reported_thlb_area_ha=66053.0,
            aflb_checkpoint_area_ha=3098168.0,
            lhlb_checkpoint_area_ha=2284357.0,
            lhlb_curve_ready_checkpoint_area_ha=2284357.0,
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_netdown_recipe", _fake_run)

    cli_main.tsr_thlb_netdown_run(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        checkpoint_path=None,
        output_path=None,
        audit_path=None,
        execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        map_id=["093J034", "093J044"],
        auto_map_id_smoke_subset=False,
        allow_stand_binary_fallback=True,
        no_aflb_gpkg=False,
        no_lhlb_gpkg=False,
        no_lhlb_curve_ready_gpkg=False,
        parallel_mode="auto",
        max_workers=None,
        lu_bundle_count=None,
    )

    assert captured_kwargs["map_ids"] == ("093J034", "093J044")
    assert captured_kwargs["auto_map_id_smoke_subset"] is False
    assert captured_kwargs["allow_stand_binary_fallback"] is True
    assert captured_kwargs["write_aflb_gpkg"] is True
    assert captured_kwargs["write_lhlb_gpkg"] is True
    assert captured_kwargs["write_lhlb_curve_ready_gpkg"] is True
    assert captured_kwargs["parallel_mode"] == "auto"
    assert captured_kwargs["max_workers"] is None
    assert captured_kwargs["lu_bundle_count"] is None
    assert any("selected_map_ids: 093J034, 093J044" in msg for msg in messages)


def test_tsr_thlb_netdown_run_can_disable_aflb_gpkg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbNetdownRecipeRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "ria_vri_vclr1p_checkpoint1.feather",
            output_path=instance_root
            / "data"
            / "tsr"
            / "thlb_reconstructed_checkpoint.feather",
            audit_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.audit.json",
            status_report_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.status.md",
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260405T000000Z.md",
            aflb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "aflb_checkpoint.feather",
            aflb_gpkg_path=None,
            aflb_lu_cache_warmed=True,
            lhlb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_checkpoint.feather",
            lhlb_gpkg_path=None,
            lhlb_lu_cache_warmed=True,
            lhlb_curve_ready_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_curve_ready_checkpoint.feather",
            lhlb_curve_ready_gpkg_path=None,
            lhlb_curve_ready_lu_cache_warmed=True,
            execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
            baseline_signal="checkpoint1_raw_glb_initialization",
            selected_map_ids=(),
            step_count=1,
            outcome_counts={"applied": 1},
            input_area_ha=1.0,
            baseline_managed_area_ha=1.0,
            final_managed_area_ha=1.0,
            legacy_reference_managed_area_ha=None,
            tsr_reported_aflb_area_ha=None,
            tsr_reported_thlb_area_ha=None,
            aflb_checkpoint_area_ha=1.0,
            lhlb_checkpoint_area_ha=0.75,
            lhlb_curve_ready_checkpoint_area_ha=0.75,
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_netdown_recipe", _fake_run)

    cli_main.tsr_thlb_netdown_run(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        checkpoint_path=None,
        output_path=None,
        audit_path=None,
        execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        map_id=[],
        auto_map_id_smoke_subset=False,
        allow_stand_binary_fallback=False,
        no_aflb_gpkg=True,
        no_lhlb_gpkg=True,
        no_lhlb_curve_ready_gpkg=True,
        parallel_mode="serial",
        max_workers=3,
        lu_bundle_count=2,
    )

    assert captured_kwargs["write_aflb_gpkg"] is False
    assert captured_kwargs["write_lhlb_gpkg"] is False
    assert captured_kwargs["write_lhlb_curve_ready_gpkg"] is False
    assert captured_kwargs["parallel_mode"] == "serial"
    assert captured_kwargs["max_workers"] == 3
    assert captured_kwargs["lu_bundle_count"] == 2


def test_tsr_thlb_netdown_run_accepts_explicit_aflb_yield_ready_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)
        return cli_main.TsrThlbNetdownRecipeRunResult(
            recipe_path=instance_root / "config" / "tsr" / "thlb_netdown.recipe.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "aflb_yield_ready_checkpoint.feather",
            output_path=instance_root
            / "data"
            / "tsr"
            / "thlb_reconstructed_checkpoint.feather",
            audit_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.audit.json",
            status_report_path=instance_root
            / "config"
            / "tsr"
            / "thlb_reconstructed.status.md",
            runtime_status_report_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "thlb_reconstructed_status_report-20260405T000000Z.md",
            aflb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "aflb_checkpoint.feather",
            aflb_gpkg_path=None,
            aflb_lu_cache_warmed=False,
            lhlb_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_checkpoint.feather",
            lhlb_gpkg_path=None,
            lhlb_lu_cache_warmed=False,
            lhlb_curve_ready_checkpoint_path=instance_root
            / "data"
            / "tsr"
            / "lhlb_curve_ready_checkpoint.feather",
            lhlb_curve_ready_gpkg_path=None,
            lhlb_curve_ready_lu_cache_warmed=False,
            execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
            baseline_signal="aflb_yield_ready_checkpoint_restart",
            selected_map_ids=(),
            step_count=2,
            outcome_counts={"applied": 2},
            input_area_ha=1.0,
            baseline_managed_area_ha=1.0,
            final_managed_area_ha=0.75,
            legacy_reference_managed_area_ha=None,
            tsr_reported_aflb_area_ha=None,
            tsr_reported_thlb_area_ha=None,
            aflb_checkpoint_area_ha=1.0,
            lhlb_checkpoint_area_ha=0.9,
            lhlb_curve_ready_checkpoint_area_ha=0.9,
        )

    monkeypatch.setattr(cli_main, "run_tsr_thlb_netdown_recipe", _fake_run)

    cli_main.tsr_thlb_netdown_run(
        instance_root=instance_root,
        thlb_netdown_recipe_path=None,
        checkpoint_path=Path("data/tsr/aflb_yield_ready_checkpoint.feather"),
        output_path=None,
        audit_path=None,
        execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
        map_id=[],
        auto_map_id_smoke_subset=False,
        allow_stand_binary_fallback=False,
        no_aflb_gpkg=True,
        no_lhlb_gpkg=True,
        no_lhlb_curve_ready_gpkg=True,
        parallel_mode="serial",
        max_workers=None,
        lu_bundle_count=None,
    )

    assert (
        captured_kwargs["checkpoint_path"]
        == (
            instance_root / "data" / "tsr" / "aflb_yield_ready_checkpoint.feather"
        ).resolve()
    )
    assert any(
        "baseline_signal: aflb_yield_ready_checkpoint_restart" in msg
        for msg in messages
    )


def test_pipelines_run_executes_named_pipeline_runbook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    runbook_path = instance_root / "runbooks" / "pipelines" / "tsa29.yaml"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    captured_kwargs: dict[str, object] = {}

    def _fake_run_named_pipeline_runbook(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                "event_kind=pipeline_run_started pipeline_id=tsr.thlb_strict"
            )
            runtime_event_sink(
                "event_kind=compiled_step_finished compiled_step_id=thlb_step_001_total_tsa_area run_status=applied_noop remaining_area_ha=1.000"
            )
        return SimpleNamespace(
            plan=SimpleNamespace(
                pipeline_id="tsr.thlb_strict",
                pipeline_label="TSR strict THLB product lane",
                runbook_path=runbook_path,
                instance_root=instance_root,
                seam_id="aflb_yield_ready",
                execution_mode="reconstructed",
                user_registry_path=None,
                instance_registry_path=None,
                explicit_registry_paths=(),
                run_profile_path=instance_root / "config" / "run_profile.tsa29.yaml",
                overlay_paths=(instance_root / "config" / "tsr" / "overlay.yaml",),
                parameter_files=(),
                validation_contract=SimpleNamespace(
                    contract_kind="tsa29_locked_chain_strict",
                    locked_chain_ledger_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_locked_chain_ledger.json",
                    comparison_report_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_reconstruction_comparison.md",
                    required_recipe_path=instance_root
                    / "workbench"
                    / "tsr"
                    / "thlb_netdown.locked.recipe.yaml",
                ),
                thlb_netdown_recipe_path=instance_root
                / "workbench"
                / "tsr"
                / "thlb_netdown.locked.recipe.yaml",
                source_layers_recipe_path=instance_root
                / "config"
                / "tsr"
                / "source_layers.recipe.yaml",
                checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "aflb_yield_ready_checkpoint.feather",
            ),
            runtime_event_log_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "named_pipeline_events-tsr_thlb_strict-20260419T000000Z.log",
            validation_result=SimpleNamespace(
                validated_parent_step_count=23,
                latest_locked_row_order=23,
                latest_locked_parent_step_id="thlb_parent_023_future_roads",
                expected_final_managed_area_ha=1648497.622,
                actual_final_managed_area_ha=1648497.622,
                max_abs_marginal_delta_ha=0.0,
                max_abs_cumulative_delta_ha=0.0,
            ),
            tsr_thlb_result=cli_main.TsrThlbNetdownRecipeRunResult(
                recipe_path=instance_root
                / "config"
                / "tsr"
                / "thlb_netdown.recipe.yaml",
                tsa=tsr_catalog.TsrOverlayTsaRecord(
                    tsa_id="tsa_29",
                    tsa_code="29",
                    tsa_name="Williams Lake",
                ),
                checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "aflb_yield_ready_checkpoint.feather",
                output_path=instance_root
                / "data"
                / "tsr"
                / "thlb_reconstructed_checkpoint.feather",
                audit_path=instance_root
                / "config"
                / "tsr"
                / "thlb_reconstructed.audit.json",
                status_report_path=instance_root
                / "config"
                / "tsr"
                / "thlb_reconstructed.status.md",
                runtime_status_report_path=instance_root
                / "runtime"
                / "logs"
                / "tsr"
                / "thlb_reconstructed_status_report-20260405T000000Z.md",
                aflb_checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "aflb_checkpoint.feather",
                aflb_gpkg_path=None,
                aflb_lu_cache_warmed=False,
                lhlb_checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "lhlb_checkpoint.feather",
                lhlb_gpkg_path=None,
                lhlb_lu_cache_warmed=False,
                lhlb_curve_ready_checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "lhlb_curve_ready_checkpoint.feather",
                lhlb_curve_ready_gpkg_path=None,
                lhlb_curve_ready_lu_cache_warmed=False,
                execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
                baseline_signal="aflb_yield_ready_checkpoint_restart",
                selected_map_ids=(),
                step_count=2,
                outcome_counts={"applied": 2},
                input_area_ha=1.0,
                baseline_managed_area_ha=1.0,
                final_managed_area_ha=0.75,
                legacy_reference_managed_area_ha=None,
                tsr_reported_aflb_area_ha=None,
                tsr_reported_thlb_area_ha=None,
                aflb_checkpoint_area_ha=1.0,
                lhlb_checkpoint_area_ha=0.9,
                lhlb_curve_ready_checkpoint_area_ha=0.9,
            ),
        )

    monkeypatch.setattr(
        cli_main, "run_named_pipeline_runbook", _fake_run_named_pipeline_runbook
    )

    cli_main.pipelines_run(
        runbook=Path("runbooks/pipelines/tsa29.yaml"),
        instance_root=instance_root,
    )

    assert captured_kwargs["runbook_path"] == runbook_path.resolve()
    assert captured_kwargs["instance_root"] == instance_root.resolve()
    assert any("pipeline_id: tsr.thlb_strict" in msg for msg in messages)
    assert any("event_kind=pipeline_run_started" in msg for msg in messages)
    assert any("event_kind=compiled_step_finished" in msg for msg in messages)
    assert any("seam_id: aflb_yield_ready" in msg for msg in messages)
    assert any("runtime_event_log_path:" in msg for msg in messages)
    assert any("validation_contract_required_recipe_path:" in msg for msg in messages)
    assert any("validation_parent_step_count: 23" in msg for msg in messages)
    assert any(
        "baseline_signal: aflb_yield_ready_checkpoint_restart" in msg
        for msg in messages
    )


def test_pipelines_run_accepts_checked_in_proof_runbook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    runbook = Path("runbooks/pipelines/tsa29.tsr.thlb_strict.aflb_yield_ready.yaml")
    captured_kwargs: dict[str, object] = {}

    monkeypatch.setattr(cli_main.console, "print", lambda _message: None)

    def _fake_run_named_pipeline_runbook(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                "event_kind=pipeline_run_started pipeline_id=tsr.thlb_strict"
            )
        return SimpleNamespace(
            plan=SimpleNamespace(
                pipeline_id="tsr.thlb_strict",
                pipeline_label="TSR strict THLB product lane",
                runbook_path=runbook.resolve(),
                instance_root=instance_root,
                seam_id="aflb_yield_ready",
                execution_mode="reconstructed",
                user_registry_path=None,
                instance_registry_path=None,
                explicit_registry_paths=(),
                run_profile_path=instance_root / "config" / "run_profile.tsa29.yaml",
                overlay_paths=(instance_root / "config" / "tsr" / "overlay.yaml",),
                parameter_files=(),
                validation_contract=SimpleNamespace(
                    contract_kind="tsa29_locked_chain_strict",
                    locked_chain_ledger_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_locked_chain_ledger.json",
                    comparison_report_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_reconstruction_comparison.md",
                    required_recipe_path=instance_root
                    / "workbench"
                    / "tsr"
                    / "thlb_netdown.locked.recipe.yaml",
                ),
                thlb_netdown_recipe_path=instance_root
                / "workbench"
                / "tsr"
                / "thlb_netdown.locked.recipe.yaml",
                source_layers_recipe_path=instance_root
                / "config"
                / "tsr"
                / "source_layers.recipe.yaml",
                checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "aflb_yield_ready_checkpoint.feather",
            ),
            runtime_event_log_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "named_pipeline_events-tsr_thlb_strict-20260419T000000Z.log",
            validation_result=None,
            tsr_thlb_result=SimpleNamespace(
                recipe_path=instance_root
                / "config"
                / "tsr"
                / "thlb_netdown.recipe.yaml",
                checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "aflb_yield_ready_checkpoint.feather",
                output_path=instance_root
                / "data"
                / "tsr"
                / "thlb_reconstructed_checkpoint.feather",
                audit_path=instance_root
                / "config"
                / "tsr"
                / "thlb_reconstructed.audit.json",
                status_report_path=instance_root
                / "config"
                / "tsr"
                / "thlb_reconstructed.status.md",
                runtime_status_report_path=instance_root
                / "runtime"
                / "logs"
                / "tsr"
                / "thlb_reconstructed_status_report-20260405T000000Z.md",
                aflb_checkpoint_path=None,
                aflb_gpkg_path=None,
                aflb_lu_cache_warmed=False,
                lhlb_checkpoint_path=None,
                lhlb_gpkg_path=None,
                lhlb_lu_cache_warmed=False,
                lhlb_curve_ready_checkpoint_path=None,
                lhlb_curve_ready_gpkg_path=None,
                lhlb_curve_ready_lu_cache_warmed=False,
                execution_mode=tsr_catalog.TSR_THLB_EXECUTION_MODE_RECONSTRUCTED,
                baseline_signal="aflb_yield_ready_checkpoint_restart",
                selected_map_ids=(),
                tsa=tsr_catalog.TsrOverlayTsaRecord(
                    tsa_id="tsa_29",
                    tsa_code="29",
                    tsa_name="Williams Lake",
                ),
                step_count=1,
                outcome_counts={"applied": 1},
                input_area_ha=1.0,
                baseline_managed_area_ha=1.0,
                final_managed_area_ha=1.0,
                legacy_reference_managed_area_ha=None,
                tsr_reported_aflb_area_ha=None,
                tsr_reported_thlb_area_ha=None,
                aflb_checkpoint_area_ha=None,
                lhlb_checkpoint_area_ha=None,
                lhlb_curve_ready_checkpoint_area_ha=None,
            ),
        )

    monkeypatch.setattr(
        cli_main, "run_named_pipeline_runbook", _fake_run_named_pipeline_runbook
    )

    cli_main.pipelines_run(runbook=runbook, instance_root=instance_root)

    assert captured_kwargs["runbook_path"] == runbook.resolve()
    assert captured_kwargs["instance_root"] == instance_root.resolve()


def test_pipelines_run_handles_scratch_preflight_only_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    runbook = Path("runbooks/pipelines/tsa29.tsr.thlb_strict.scratch.yaml")
    messages: list[str] = []

    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fake_run_named_pipeline_runbook(**kwargs: object) -> object:
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                "event_kind=pipeline_validation_preflight_finished "
                "locked_row_order=1 actual_start_area_ha=4933664.212"
            )
        return SimpleNamespace(
            plan=SimpleNamespace(
                pipeline_id="tsr.thlb_strict",
                pipeline_label="TSR strict THLB product lane",
                runbook_path=runbook.resolve(),
                instance_root=instance_root,
                seam_id="scratch",
                execution_mode="reconstructed",
                user_registry_path=None,
                instance_registry_path=None,
                explicit_registry_paths=(),
                run_profile_path=instance_root / "config" / "run_profile.tsa29.yaml",
                overlay_paths=(instance_root / "config" / "tsr" / "overlay.yaml",),
                parameter_files=(),
                validation_contract=SimpleNamespace(
                    contract_kind="tsa29_locked_chain_strict",
                    locked_chain_ledger_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_locked_chain_ledger.json",
                    comparison_report_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_reconstruction_comparison.md",
                    required_recipe_path=instance_root
                    / "workbench"
                    / "tsr"
                    / "thlb_netdown.locked.recipe.yaml",
                ),
                thlb_netdown_recipe_path=instance_root
                / "workbench"
                / "tsr"
                / "thlb_netdown.locked.recipe.yaml",
                source_layers_recipe_path=instance_root
                / "config"
                / "tsr"
                / "source_layers.recipe.yaml",
                checkpoint_path=None,
            ),
            runtime_event_log_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "named_pipeline_events-tsr_thlb_strict-20260419T000000Z.log",
            validation_result=SimpleNamespace(
                validated_parent_step_count=1,
                latest_locked_row_order=1,
                latest_locked_parent_step_id="thlb_parent_001_total_tsa_area",
                expected_final_managed_area_ha=4933664.212,
                actual_final_managed_area_ha=4933664.212,
                max_abs_marginal_delta_ha=0.0,
                max_abs_cumulative_delta_ha=0.0,
            ),
            tsr_thlb_result=None,
        )

    monkeypatch.setattr(
        cli_main, "run_named_pipeline_runbook", _fake_run_named_pipeline_runbook
    )

    cli_main.pipelines_run(runbook=runbook, instance_root=instance_root)

    assert any("checkpoint_path: <scratch>" in msg for msg in messages)
    assert any("validation_parent_step_count: 1" in msg for msg in messages)
    assert any(
        "event_kind=pipeline_validation_preflight_finished" in msg for msg in messages
    )


def test_pipelines_run_handles_scratch_parent_step_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    runbook = Path("runbooks/pipelines/tsa29.tsr.thlb_strict.scratch_to_step2.yaml")
    messages: list[str] = []

    monkeypatch.setattr(cli_main.console, "print", messages.append)

    def _fake_run_named_pipeline_runbook(**kwargs: object) -> object:
        runtime_event_sink = kwargs.get("runtime_event_sink")
        if callable(runtime_event_sink):
            runtime_event_sink(
                "event_kind=parent_step_finished "
                "parent_step_id=thlb_parent_002_land_not_administered_by_the_province "
                "run_status=applied remaining_area_ha=4236882.888"
            )
        return SimpleNamespace(
            plan=SimpleNamespace(
                pipeline_id="tsr.thlb_strict",
                pipeline_label="TSR strict THLB product lane",
                runbook_path=runbook.resolve(),
                instance_root=instance_root,
                seam_id="scratch",
                execution_mode="reconstructed",
                user_registry_path=None,
                instance_registry_path=None,
                explicit_registry_paths=(),
                run_profile_path=instance_root / "config" / "run_profile.tsa29.yaml",
                overlay_paths=(instance_root / "config" / "tsr" / "overlay.yaml",),
                parameter_files=(),
                validation_contract=SimpleNamespace(
                    contract_kind="tsa29_locked_chain_strict",
                    locked_chain_ledger_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_locked_chain_ledger.json",
                    comparison_report_path=instance_root
                    / "config"
                    / "tsr"
                    / "thlb_reconstruction_comparison.md",
                    required_recipe_path=instance_root
                    / "workbench"
                    / "tsr"
                    / "thlb_netdown.locked.recipe.yaml",
                ),
                target_parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
                thlb_netdown_recipe_path=instance_root
                / "workbench"
                / "tsr"
                / "thlb_netdown.locked.recipe.yaml",
                source_layers_recipe_path=instance_root
                / "config"
                / "tsr"
                / "source_layers.recipe.yaml",
                checkpoint_path=None,
            ),
            runtime_event_log_path=instance_root
            / "runtime"
            / "logs"
            / "tsr"
            / "named_pipeline_events-tsr_thlb_strict-20260420T000000Z.log",
            validation_result=SimpleNamespace(
                validated_parent_step_count=2,
                latest_locked_row_order=2,
                latest_locked_parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
                expected_final_managed_area_ha=4236882.888,
                actual_final_managed_area_ha=4236882.888,
                max_abs_marginal_delta_ha=0.0,
                max_abs_cumulative_delta_ha=0.0,
            ),
            tsr_thlb_result=None,
            tsr_parent_step_result=SimpleNamespace(
                recipe_path=instance_root
                / "workbench"
                / "tsr"
                / "thlb_netdown.locked.recipe.yaml",
                parent_step_id="thlb_parent_002_land_not_administered_by_the_province",
                parent_label="Land not administered by the Province",
                tsa=SimpleNamespace(
                    tsa_id="tsa_29", tsa_code="29", tsa_name="Williams Lake"
                ),
                checkpoint_path=instance_root
                / "data"
                / "tsr"
                / "glb_checkpoint.feather",
                selected_map_ids=(),
                selected_landscape_units=(),
                execution_mode="serial",
                worker_count=None,
                lu_chunk_count=None,
                output_path=instance_root
                / "data"
                / "tsr"
                / "glb_to_aflb_step2.feather",
                result_json_path=instance_root
                / "runtime"
                / "logs"
                / "tsr"
                / "step2.json",
                status="applied",
                input_area_ha=4933664.212,
                removed_area_ha=696781.324,
                remaining_area_ha=4236882.888,
                benchmark_marginal_area_ha=697033.0,
                benchmark_cumulative_area_ha=4236602.0,
                benchmark_marginal_delta_ha=-251.676,
                benchmark_cumulative_delta_ha=280.888,
                notes=(),
            ),
        )

    monkeypatch.setattr(
        cli_main, "run_named_pipeline_runbook", _fake_run_named_pipeline_runbook
    )

    cli_main.pipelines_run(runbook=runbook, instance_root=instance_root)

    assert any("target_parent_step_id:" in msg for msg in messages)
    assert any(
        "parent_step_id: thlb_parent_002_land_not_administered_by_the_province" in msg
        for msg in messages
    )
    assert any("remaining_area_ha: 4236882.888" in msg for msg in messages)


def test_tsr_facts_report_writes_review_csv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    result = cli_main.TsrFactReportResult(
        candidate_facts_path=repo_root
        / "metadata"
        / "tsr"
        / "tsa_candidate_facts.json",
        tsa_id="tsa_29",
        tsa_code="29",
        tsa_name="Williams Lake",
        selected_fact_families=("source_layer_candidate",),
        rows=(
            tsr_catalog.TsrFactReviewRow(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
                fact_family="source_layer_candidate",
                extracted_value="WHSE_FOREST_VEGETATION.F_OWN",
                recommended_query="WHSE_FOREST_VEGETATION.F_OWN",
                quality="likely_useful",
                quality_reason="BCGW object-name style token",
                snippet="BCGW source layer used for ownership netdown.",
                page_number=12,
                title="Williams Lake TSA Data Package",
                cycle_label="2024 TSR",
                cycle_year=2024,
                provenance_id="tsa29-doc-12-source-1",
                source_url="https://example.invalid/tsa29-data-package.pdf",
            ),
        ),
    )
    captured_kwargs: dict[str, object] = {}
    written_paths: list[Path] = []

    def _fake_report(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    def _fake_write(report_result, *, path):
        assert report_result == result
        written_paths.append(path)
        return path

    monkeypatch.setattr(cli_main, "report_tsr_candidate_facts", _fake_report)
    monkeypatch.setattr(cli_main, "write_tsr_fact_report_csv", _fake_write)

    cli_main.tsr_facts_report(
        tsa="29",
        fact_family=["source_layer_candidate"],
        candidate_facts_path=None,
        output_csv=Path("runtime/logs/tsa29_source_review.csv"),
        limit=25,
    )

    assert (
        captured_kwargs["candidate_facts_path"]
        == repo_root / "metadata" / "tsr" / "tsa_candidate_facts.json"
    )
    assert captured_kwargs["tsa"] == "29"
    assert captured_kwargs["fact_families"] == ("source_layer_candidate",)
    assert captured_kwargs["limit"] == 25
    assert written_paths == [repo_root / "runtime" / "logs" / "tsa29_source_review.csv"]
    assert any("row_count: 1" in msg for msg in messages)
    assert any("output_csv:" in msg for msg in messages)


def test_tsr_facts_report_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "report_tsr_candidate_facts",
        lambda **_kwargs: (_ for _ in ()).throw(cli_main.TsrFactReportError("boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_facts_report(
            tsa="29",
            fact_family=["source_layer_candidate"],
            candidate_facts_path=None,
            output_csv=None,
            limit=None,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR fact-report error:" in msg for msg in messages)


def test_tsr_overlay_report_summarizes_adopted_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "build_tsr_overlay_report",
        lambda **_kwargs: cli_main.TsrOverlayReport(
            overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            canonical_summary=tsr_catalog.TsrOverlayCanonicalSummary(
                candidate_fact_count=4,
                document_count=2,
                fact_family_counts={"source_layer_candidate": 2},
                candidate_facts_path="metadata/tsr/tsa_candidate_facts.json",
                documents_path="metadata/tsr/tsa_documents.json",
                registry_path="metadata/tsr/tsa_registry.json",
            ),
            adopted_counts={
                "source_layers": 1,
                "au_definitions": 0,
                "thlb_references": 0,
                "tipsy_inputs": 0,
                "notes": 0,
            },
        ),
    )

    cli_main.tsr_overlay_report(instance_root=instance_root, overlay_path=None)

    assert any("adopted_source_layers_count: 1" in msg for msg in messages)
    assert any("tsa_name: Williams Lake" in msg for msg in messages)


def test_tsr_override_init_writes_instance_local_override_template(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = _set_cli_repo_root(monkeypatch, tmp_path)
    instance_root = repo_root / "external" / "femic-tsa29-instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)

    result = cli_main.TsrSourceLayerOverridesInitResult(
        overrides_path=instance_root / "config" / "tsr" / "source_layer_overrides.yaml",
        overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
        tsa=tsr_catalog.TsrOverlayTsaRecord(
            tsa_id="tsa_29",
            tsa_code="29",
            tsa_name="Williams Lake",
        ),
        entry_count=5,
        created=True,
    )
    captured_kwargs: dict[str, object] = {}

    def _fake_init(**kwargs):
        captured_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(cli_main, "init_tsr_source_layer_overrides", _fake_init)

    cli_main.tsr_override_init(
        instance_root=instance_root,
        overlay_path=None,
        overrides_path=None,
        overwrite=False,
    )

    assert captured_kwargs["instance_root"] == instance_root.resolve()
    assert (
        captured_kwargs["overlay_path"]
        == (instance_root / "config" / "tsr" / "overlay.yaml").resolve()
    )
    assert (
        captured_kwargs["overrides_path"]
        == (instance_root / "config" / "tsr" / "source_layer_overrides.yaml").resolve()
    )
    assert any("overrides_path:" in msg for msg in messages)
    assert any("entry_count: 5" in msg for msg in messages)


def test_tsr_override_init_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "init_tsr_source_layer_overrides",
        lambda **_kwargs: (_ for _ in ()).throw(
            cli_main.TsrSourceLayerOverridesError("boom")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_override_init(
            instance_root=Path("instance"),
            overlay_path=None,
            overrides_path=None,
            overwrite=False,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR override init error:" in msg for msg in messages)


def test_tsr_override_report_summarizes_override_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "build_tsr_source_layer_override_report",
        lambda **_kwargs: cli_main.TsrSourceLayerOverridesReport(
            overrides_path=instance_root
            / "config"
            / "tsr"
            / "source_layer_overrides.yaml",
            overlay_path=instance_root / "config" / "tsr" / "overlay.yaml",
            tsa=tsr_catalog.TsrOverlayTsaRecord(
                tsa_id="tsa_29",
                tsa_code="29",
                tsa_name="Williams Lake",
            ),
            total_entries=5,
            resolved_entries=2,
            pending_entries=3,
            entries_with_suggestions=2,
            total_suggestion_candidates=4,
            unresolved_overlay_queries=("WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS",),
            override_kind_counts={"replacement_layer": 1, "local_path": 1},
        ),
    )

    cli_main.tsr_override_report(
        instance_root=instance_root, overlay_path=None, overrides_path=None
    )

    assert any("resolved_entries: 2" in msg for msg in messages)
    assert any("pending_entries: 3" in msg for msg in messages)
    assert any("entries_with_suggestions: 2" in msg for msg in messages)
    assert any("total_suggestion_candidates: 4" in msg for msg in messages)
    assert any("replacement_layer_count: 1" in msg for msg in messages)


def test_tsr_override_report_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    monkeypatch.setattr(cli_main.console, "print", messages.append)
    monkeypatch.setattr(
        cli_main,
        "build_tsr_source_layer_override_report",
        lambda **_kwargs: (_ for _ in ()).throw(
            cli_main.TsrSourceLayerOverridesError("boom")
        ),
    )

    with pytest.raises(typer.Exit) as exc_info:
        cli_main.tsr_override_report(
            instance_root=Path("instance"),
            overlay_path=None,
            overrides_path=None,
        )

    assert exc_info.value.exit_code == 1
    assert any("TSR override report error:" in msg for msg in messages)
