from __future__ import annotations

import json
from pathlib import Path
import zipfile

import geopandas as gpd
from shapely.geometry import Polygon

from femic.glb import (
    GLB_OUTPUT_FEATURE_CLASS_NAME,
    GlbBuildResult,
    GlbStashResult,
    _resolve_glb_stash_paths,
    _stash_glb_snapshot,
    build_tsa_raw_glb,
    resolve_default_raw_vri_2024_zip,
    resolve_default_tsa_boundary_path,
)


def _write_boundary_layer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    boundary = gpd.GeoDataFrame(
        {
            "TSA_NUMBER": [29],
            "TSA_NAME": ["Williams Lake TSA"],
            "TSB_NUMBER": [None],
            "geometry": [Polygon([(0, 0), (0, 1000), (1000, 1000), (1000, 0)])],
        },
        crs="EPSG:3005",
    )
    boundary.to_file(path)


def test_default_glb_paths_resolve_from_source_and_instance_roots(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    instance_root = tmp_path / "instance"
    zip_path = (
        source_root
        / "external"
        / "femic-public-data"
        / "data"
        / "bc"
        / "vri"
        / "2024"
        / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
    )
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"zip")
    boundary_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA.gpkg"
    )
    _write_boundary_layer(boundary_path)

    assert (
        resolve_default_raw_vri_2024_zip(source_root=source_root) == zip_path.resolve()
    )
    assert resolve_default_tsa_boundary_path(instance_root=instance_root) == (
        boundary_path.resolve()
    )


def test_build_tsa_raw_glb_writes_summary_with_mocked_arcgis(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    instance_root = tmp_path / "instance"
    boundary_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA.gpkg"
    )
    _write_boundary_layer(boundary_path)
    zip_path = (
        source_root
        / "external"
        / "femic-public-data"
        / "data"
        / "bc"
        / "vri"
        / "2024"
        / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
    )
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("VEG_COMP_LYR_R1_POLY_2024.gdb/dummy.txt", "dummy")

    def _fake_arcgis_runner(
        *,
        source_feature_class_path: Path,
        boundary_layer_path: Path,
        output_gdb_path: Path,
        output_feature_class_name: str,
        summary_json_path: Path,
    ) -> None:
        assert source_feature_class_path.name == "VEG_COMP_LYR_R1_POLY"
        assert boundary_layer_path.parent.suffix == ".gdb"
        assert boundary_layer_path.parent.exists()
        assert boundary_layer_path.name == "tsa_29_boundary"
        output_gdb_path.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(
            json.dumps(
                {
                    "feature_count": 7,
                    "clipped_area_ha": 100.0,
                    "output_feature_class": str(
                        output_gdb_path / output_feature_class_name
                    ),
                }
            ),
            encoding="utf-8",
        )

    result = build_tsa_raw_glb(
        source_root=source_root,
        instance_root=instance_root,
        tsa="29",
        stash_public_data_glb=False,
        arcgis_runner=_fake_arcgis_runner,
    )

    assert result.tsa_number == "29"
    assert result.tsa_name == "Williams Lake TSA"
    assert result.glb_source_mode == "raw_build"
    assert result.feature_count == 7
    assert result.clipped_area_ha == 100.0
    assert result.clipped_glb_feature_class == GLB_OUTPUT_FEATURE_CLASS_NAME
    assert result.summary_json_path.exists()
    assert result.summary_markdown_path.exists()
    summary_payload = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert summary_payload["tsa_number"] == "29"
    assert summary_payload["feature_count"] == 7
    assert summary_payload["public_data_glb_stash_status"] == "disabled"
    markdown_text = result.summary_markdown_path.read_text(encoding="utf-8")
    assert "raw source geometry" in markdown_text


def test_resolve_glb_stash_paths_uses_tsa_and_vintage(tmp_path: Path) -> None:
    public_data_root = tmp_path / "data"
    archive_path, summary_path = _resolve_glb_stash_paths(
        public_data_root=public_data_root,
        tsa_number="29",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
    )

    assert archive_path == (
        public_data_root
        / "bc"
        / "tsa"
        / "glb"
        / "2024"
        / "tsa29"
        / "tsa29_glb_vri_2024.gdb.zip"
    )
    assert summary_path == (
        public_data_root
        / "bc"
        / "tsa"
        / "glb"
        / "2024"
        / "tsa29"
        / "tsa29_glb_vri_2024.summary.json"
    )


def test_stash_glb_snapshot_reuses_existing_files(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data" / "data"
    repo_root = public_data_root.parent
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    archive_path, summary_path = _resolve_glb_stash_paths(
        public_data_root=public_data_root,
        tsa_number="29",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(b"zip")
    summary_path.write_text("{}", encoding="utf-8")
    clipped_gdb = tmp_path / "clipped_glb.gdb"
    clipped_gdb.mkdir()
    result = GlbBuildResult(
        glb_source_mode="raw_build",
        tsa_selector="29",
        tsa_number="29",
        tsa_name="Williams Lake TSA",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
        boundary_source_path=tmp_path / "tsa.gpkg",
        output_dir=tmp_path / "out",
        clipped_glb_gdb_path=clipped_gdb,
        clipped_glb_feature_class=GLB_OUTPUT_FEATURE_CLASS_NAME,
        summary_json_path=tmp_path / "glb_summary.json",
        summary_markdown_path=tmp_path / "glb_summary.md",
        feature_count=1,
        clipped_area_ha=1.0,
        boundary_area_ha=1.0,
        area_delta_ha=0.0,
        stash_result=GlbStashResult(False, "disabled", None, None),
    )
    result.summary_json_path.write_text("{}", encoding="utf-8")
    annex_calls: list[tuple[Path, tuple[Path, ...]]] = []

    stash_result = _stash_glb_snapshot(
        result=result,
        source_root=source_root,
        force_update=False,
        annex_runner=lambda **kwargs: annex_calls.append(
            (kwargs["repo_root"], kwargs["paths"])
        ),
    )

    assert stash_result.status == "reused"
    assert stash_result.archive_path == archive_path
    assert stash_result.summary_path == summary_path
    assert annex_calls == []


def test_stash_glb_snapshot_force_updates_existing_files(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data" / "data"
    repo_root = public_data_root.parent
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    archive_path, summary_path = _resolve_glb_stash_paths(
        public_data_root=public_data_root,
        tsa_number="29",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(b"old")
    summary_path.write_text("{}", encoding="utf-8")
    clipped_gdb = tmp_path / "clipped_glb.gdb"
    clipped_gdb.mkdir()
    (clipped_gdb / "dummy.txt").write_text("fresh", encoding="utf-8")
    result = GlbBuildResult(
        glb_source_mode="raw_build",
        tsa_selector="29",
        tsa_number="29",
        tsa_name="Williams Lake TSA",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
        boundary_source_path=tmp_path / "tsa.gpkg",
        output_dir=tmp_path / "out",
        clipped_glb_gdb_path=clipped_gdb,
        clipped_glb_feature_class=GLB_OUTPUT_FEATURE_CLASS_NAME,
        summary_json_path=tmp_path / "glb_summary.json",
        summary_markdown_path=tmp_path / "glb_summary.md",
        feature_count=1,
        clipped_area_ha=1.0,
        boundary_area_ha=1.0,
        area_delta_ha=0.0,
        stash_result=GlbStashResult(False, "disabled", None, None),
    )
    result.summary_json_path.write_text("{}", encoding="utf-8")
    annex_calls: list[tuple[Path, tuple[Path, ...]]] = []

    stash_result = _stash_glb_snapshot(
        result=result,
        source_root=source_root,
        force_update=True,
        annex_runner=lambda **kwargs: annex_calls.append(
            (kwargs["repo_root"], kwargs["paths"])
        ),
    )

    assert stash_result.status == "updated"
    assert archive_path.exists()
    assert summary_path.exists()
    assert annex_calls == [(repo_root, (archive_path, summary_path))]


def test_build_tsa_raw_glb_reuses_existing_stash_before_raw_clip(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data" / "data"
    repo_root = public_data_root.parent
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    instance_root = tmp_path / "instance"
    boundary_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA.gpkg"
    )
    _write_boundary_layer(boundary_path)
    zip_path = (
        source_root
        / "external"
        / "femic-public-data"
        / "data"
        / "bc"
        / "vri"
        / "2024"
        / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
    )
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(b"placeholder")
    archive_path, summary_path = _resolve_glb_stash_paths(
        public_data_root=public_data_root,
        tsa_number="29",
        source_zip_path=Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip"),
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("clipped_glb.gdb/dummy.txt", "dummy")
    summary_path.write_text(
        json.dumps(
            {
                "tsa_selector": "29",
                "tsa_number": "29",
                "tsa_name": "Williams Lake TSA",
                "source_zip_path": str(Path("VEG_COMP_LYR_R1_POLY_2024.gdb.zip")),
                "boundary_source_path": str(boundary_path),
                "clipped_glb_feature_class": GLB_OUTPUT_FEATURE_CLASS_NAME,
                "feature_count": 7,
                "clipped_area_ha": 100.0,
                "boundary_area_ha": 100.0,
                "area_delta_ha": 0.0,
            }
        ),
        encoding="utf-8",
    )

    def _unexpected_arcgis_runner(**_: object) -> None:
        raise AssertionError("raw clip should not run when stash exists")

    result = build_tsa_raw_glb(
        source_root=source_root,
        instance_root=instance_root,
        tsa="29",
        arcgis_runner=_unexpected_arcgis_runner,
    )

    assert result.glb_source_mode == "stashed_snapshot"
    assert result.stash_result.status == "reused"


def test_build_tsa_raw_glb_force_rebuild_ignores_existing_stash(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    public_data_root = source_root / "external" / "femic-public-data" / "data"
    repo_root = public_data_root.parent
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    instance_root = tmp_path / "instance"
    boundary_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA"
        / "WHSE_ADMIN_BOUNDARIES_FADM_TSA.gpkg"
    )
    _write_boundary_layer(boundary_path)
    zip_path = (
        source_root
        / "external"
        / "femic-public-data"
        / "data"
        / "bc"
        / "vri"
        / "2024"
        / "VEG_COMP_LYR_R1_POLY_2024.gdb.zip"
    )
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("VEG_COMP_LYR_R1_POLY_2024.gdb/dummy.txt", "dummy")
    archive_path, summary_path = _resolve_glb_stash_paths(
        public_data_root=public_data_root,
        tsa_number="29",
        source_zip_path=zip_path,
    )
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(b"old")
    summary_path.write_text("{}", encoding="utf-8")

    def _fake_arcgis_runner(
        *,
        source_feature_class_path: Path,
        boundary_layer_path: Path,
        output_gdb_path: Path,
        output_feature_class_name: str,
        summary_json_path: Path,
    ) -> None:
        output_gdb_path.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(
            json.dumps(
                {
                    "feature_count": 7,
                    "clipped_area_ha": 100.0,
                    "output_feature_class": str(
                        output_gdb_path / output_feature_class_name
                    ),
                }
            ),
            encoding="utf-8",
        )

    result = build_tsa_raw_glb(
        source_root=source_root,
        instance_root=instance_root,
        tsa="29",
        force_rebuild_glb=True,
        stash_public_data_glb=False,
        arcgis_runner=_fake_arcgis_runner,
    )

    assert result.glb_source_mode == "raw_build"
