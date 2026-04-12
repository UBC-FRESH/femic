from __future__ import annotations

import json
from pathlib import Path
import zipfile

import geopandas as gpd
from shapely.geometry import Polygon

from femic.glb import (
    GLB_OUTPUT_FEATURE_CLASS_NAME,
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
        arcgis_runner=_fake_arcgis_runner,
    )

    assert result.tsa_number == "29"
    assert result.tsa_name == "Williams Lake TSA"
    assert result.feature_count == 7
    assert result.clipped_area_ha == 100.0
    assert result.clipped_glb_feature_class == GLB_OUTPUT_FEATURE_CLASS_NAME
    assert result.summary_json_path.exists()
    assert result.summary_markdown_path.exists()
    summary_payload = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
    assert summary_payload["tsa_number"] == "29"
    assert summary_payload["feature_count"] == 7
    markdown_text = result.summary_markdown_path.read_text(encoding="utf-8")
    assert "raw source geometry" in markdown_text
