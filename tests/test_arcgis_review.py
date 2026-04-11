from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from femic import arcgis_review
from femic.arcgis_review import (
    DEFAULT_ARCGIS_REVIEW_OUTPUT_DIR,
    ArcgisReviewProjectResult,
    ReviewLayerSpec,
    _stage_review_layer_sources_for_arcgis,
    build_arcgis_review_project,
    default_arcgis_review_output_dir,
    discover_arcgis_review_layers,
)


def test_discover_arcgis_review_layers_finds_instance_vectors(tmp_path: Path) -> None:
    instance_root = tmp_path / "instance"
    stands = instance_root / "data" / "shp" / "tsa29.shp" / "stands.shp"
    fragments = (
        instance_root
        / "output"
        / "patchworks_tsa29_validated"
        / "fragments"
        / "fragments.shp"
    )
    tsa_gpkg = (
        instance_root / "data" / "downloads" / "bcdc" / "FADM_TSA" / "FADM_TSA.gpkg"
    )
    ignored = instance_root / "data" / "downloads" / "bcdc" / "notes.txt"
    for path in (stands, fragments, tsa_gpkg, ignored):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    specs, skipped = discover_arcgis_review_layers(instance_root=instance_root)

    assert skipped == ()
    names = [spec.name for spec in specs]
    assert names == ["stands", "fragments", "FADM_TSA"]
    tsa_spec = specs[-1]
    assert tsa_spec.source_path == tsa_gpkg.resolve()
    assert tsa_spec.source_layer_name is None
    assert tsa_spec.default_visibility is False


def test_discover_arcgis_review_layers_uses_real_gpkg_layer_name_when_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    gpkg = instance_root / "data" / "downloads" / "bcdc" / "PSP" / "PSP.gpkg"
    gpkg.parent.mkdir(parents=True, exist_ok=True)
    gpkg.touch()
    monkeypatch.setitem(
        sys.modules,
        "fiona",
        SimpleNamespace(listlayers=lambda _path: ["SCHEMA.ACTUAL_LAYER"]),
    )

    specs, skipped = discover_arcgis_review_layers(instance_root=instance_root)

    assert skipped == ()
    assert specs[0].source_path == gpkg.resolve()
    assert specs[0].source_layer_name == "SCHEMA.ACTUAL_LAYER"


def test_default_arcgis_review_output_dir_is_instance_relative(tmp_path: Path) -> None:
    instance_root = tmp_path / "instance"
    assert default_arcgis_review_output_dir(instance_root=instance_root) == (
        instance_root / DEFAULT_ARCGIS_REVIEW_OUTPUT_DIR
    )


def test_discover_arcgis_review_layers_skips_smoke_cached_bcdc_artifacts(
    tmp_path: Path,
) -> None:
    instance_root = tmp_path / "instance"
    smoke_gpkg = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "smoke"
        / "cached"
        / "SMOKE_ONLY.gpkg"
    )
    smoke_gpkg.parent.mkdir(parents=True, exist_ok=True)
    smoke_gpkg.touch()

    specs, skipped = discover_arcgis_review_layers(instance_root=instance_root)

    assert specs == []
    assert any("smoke-scoped cached BCDC review layer" in note for note in skipped)


def test_build_arcgis_review_project_shapes_payload_and_returns_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    stands = instance_root / "data" / "shp" / "tsa29.shp" / "stands.shp"
    stands.parent.mkdir(parents=True, exist_ok=True)
    stands.touch()
    output_dir = tmp_path / "review_out"
    blank_aprx = tmp_path / "Blank.aprx"
    blank_aprx.write_text("blank", encoding="utf-8")
    fake_python = tmp_path / "propy.bat"
    fake_python.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(arcgis_review.os, "name", "nt", raising=False)
    monkeypatch.setattr(arcgis_review, "find_arcgis_pro_python", lambda: fake_python)
    monkeypatch.setattr(
        arcgis_review,
        "find_arcgis_blank_project_template",
        lambda _python_path=None: blank_aprx,
    )

    captured: dict[str, object] = {}

    def _fake_runner(*, code: str, args: list[str]) -> subprocess.CompletedProcess[str]:
        _ = code
        payload = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        captured.update(payload)
        project_path = Path(payload["project_path"])
        manifest_path = Path(payload["manifest_path"])
        project_path.parent.mkdir(parents=True, exist_ok=True)
        project_path.write_text("aprx", encoding="utf-8")
        manifest_path.write_text(
            json.dumps({"project_path": str(project_path), "layer_count": 1}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=["fake"], returncode=0, stdout="", stderr=""
        )

    result = build_arcgis_review_project(
        instance_root=instance_root,
        output_dir=output_dir,
        project_name="TSA 29 Review",
        arcgis_runner=_fake_runner,
    )

    assert isinstance(result, ArcgisReviewProjectResult)
    assert result.project_path == output_dir / "TSA_29_Review.aprx"
    assert result.manifest_path == output_dir / "TSA_29_Review_manifest.json"
    assert captured["map_name"] == "instance Review"
    assert len(captured["layers"]) == 1
    first_layer = captured["layers"][0]
    assert first_layer["default_visibility"] is False
    assert first_layer["name"] == "stands"


def test_build_arcgis_review_project_requires_arcgis_pro(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    instance_root = tmp_path / "instance"
    monkeypatch.setattr(arcgis_review.os, "name", "nt", raising=False)
    monkeypatch.setattr(arcgis_review, "find_arcgis_pro_python", lambda: None)

    with pytest.raises(FileNotFoundError, match="ArcGIS Pro Python not found"):
        build_arcgis_review_project(instance_root=instance_root)


def test_stage_review_layer_sources_for_arcgis_rewrites_gpkg_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    gpkg_spec = ReviewLayerSpec(
        name="PSP",
        artifact_path=tmp_path / "PSP.gpkg",
        source_path=tmp_path / "PSP.gpkg",
        source_layer_name="main.PSP",
        geometry_family="polygon",
        transparency=50,
        draw_order=10,
        default_visibility=False,
    )
    staged_shp = tmp_path / "sources" / "PSP" / "PSP.shp"
    monkeypatch.setattr(
        arcgis_review,
        "_stage_gpkg_layer_for_arcgis",
        lambda *, spec, staging_root: staged_shp,
    )

    prepared_specs, notes = _stage_review_layer_sources_for_arcgis(
        specs=[gpkg_spec],
        staging_root=tmp_path / "sources",
    )

    assert prepared_specs[0].source_path == staged_shp
    assert prepared_specs[0].source_layer_name is None
    assert any("GeoPackage review layer" in note for note in notes)
