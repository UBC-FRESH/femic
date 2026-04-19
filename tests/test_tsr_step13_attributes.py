from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd  # type: ignore[import-untyped]
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, box
import yaml

from femic.tsr_catalog import step13_attributes


def _write_test_raster(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:3005",
        transform=from_origin(0.0, float(values.shape[0] * 100), 100.0, 100.0),
        nodata=np.nan,
    ) as dataset:
        dataset.write(values.astype(np.float32), 1)


def test_build_slope_percent_raster_uses_percent_rise(tmp_path: Path) -> None:
    raster_path = tmp_path / "dem.tif"
    values = np.array(
        [
            [0.0, 50.0, 100.0],
            [0.0, 50.0, 100.0],
            [0.0, 50.0, 100.0],
        ],
        dtype=np.float32,
    )
    _write_test_raster(raster_path, values)
    checkpoint = gpd.GeoDataFrame(
        {"MAP_ID": ["092O071"]},
        geometry=[box(0, 0, 300, 300)],
        crs="EPSG:3005",
    )

    slope_percent, _ = step13_attributes._build_slope_percent_raster(
        checkpoint=checkpoint,
        dem_paths=(raster_path,),
    )

    assert np.nanmedian(slope_percent) == pytest.approx(50.0, abs=1.0)


def test_summarize_polygon_median_raster_values_ignores_nodata() -> None:
    checkpoint = gpd.GeoDataFrame(
        {"MAP_ID": ["092O071", "092O071"]},
        geometry=[box(0, 0, 200, 200), box(200, 0, 400, 200)],
        crs="EPSG:3005",
    )
    raster_values = np.array(
        [
            [10.0, 20.0, 30.0, 40.0],
            [10.0, np.nan, 30.0, 40.0],
        ],
        dtype=np.float32,
    )

    medians = step13_attributes._summarize_polygon_median_raster_values(
        checkpoint=checkpoint,
        raster_values=raster_values,
        transform=from_origin(0.0, 200.0, 100.0, 100.0),
    )

    assert medians.tolist() == pytest.approx([10.0, 35.0])


def test_classify_checkpoint_side_of_highway_uses_east_west_split() -> None:
    checkpoint = gpd.GeoDataFrame(
        {"MAP_ID": ["092O071", "092O071"]},
        geometry=[box(0, 0, 90, 100), box(110, 0, 200, 100)],
        crs="EPSG:3005",
    )
    highway = LineString([(100.0, -50.0), (100.0, 150.0)])

    side = step13_attributes._classify_checkpoint_side_of_highway(
        checkpoint=checkpoint,
        highway_geometry=highway,
    )

    assert side.tolist() == ["west", "east"]


def test_compile_tsr_thlb_step13_attributes_writes_output_and_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance_root = tmp_path / "instance"
    checkpoint_path = instance_root / "data" / "tsr" / "lhlb_checkpoint.feather"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = gpd.GeoDataFrame(
        {
            "MAP_ID": ["092O071", "092O071"],
            "FEATURE_ID": [1, 2],
            "SITE_INDEX": [18.0, 22.0],
            "PROJ_AGE_1": [40, 80],
            "stratum_matched": ["S1", "S1"],
            "si_level": ["M", "M"],
            "au": [1, 1],
        },
        geometry=[box(0, 0, 90, 100), box(110, 0, 200, 100)],
        crs="EPSG:3005",
    )
    checkpoint.to_feather(checkpoint_path)

    au_table_path = instance_root / "data" / "model_input_bundle" / "au_table.csv"
    au_table_path.parent.mkdir(parents=True, exist_ok=True)
    au_table_path.write_text(
        "\n".join(
            [
                "tsa,stratum_code,si_level,au_id,treated_curve_id,untreated_curve_id",
                "29,S1,M,2900001,101,202",
            ]
        ),
        encoding="utf-8",
    )

    highway_path = (
        instance_root
        / "data"
        / "downloads"
        / "bcdc"
        / "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP"
        / "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP.gpkg"
    )
    highway_path.parent.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(
        {"HIGHWAY_NUMBER": [97]},
        geometry=[LineString([(100.0, -50.0), (100.0, 150.0)])],
        crs="EPSG:3005",
    ).to_file(highway_path, driver="GPKG")

    source_recipe_path = instance_root / "config" / "tsr" / "source_layers.recipe.yaml"
    source_recipe_path.parent.mkdir(parents=True, exist_ok=True)
    source_recipe_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "recipe_kind": "source_layers",
                "tsa": {"tsa_id": "29", "tsa_code": "29", "tsa_name": "TSA 29"},
                "canonical_inputs": {
                    "registry_path": "metadata/tsr/tsa_registry.json",
                    "documents_path": "metadata/tsr/tsa_documents.json",
                    "candidate_facts_path": "metadata/tsr/tsa_candidate_facts.json",
                },
                "instance_inputs": {
                    "overlay_path": "config/tsr/overlay.yaml",
                    "source_layer_overrides_path": "config/tsr/source_layer_overrides.yaml",
                    "download_root": "data/downloads/bcdc",
                },
                "recipe_contract": {"status": "built"},
                "entries": [
                    {
                        "entry_id": (
                            "whse_imagery_and_base_maps_mot_highway_profiles_sp"
                        ),
                        "artifact_path": (
                            "data/downloads/bcdc/"
                            "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP/"
                            "WHSE_IMAGERY_AND_BASE_MAPS_MOT_HIGHWAY_PROFILES_SP.gpkg"
                        ),
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    dem_path = tmp_path / "dem.tif"
    _write_test_raster(
        dem_path,
        np.array(
            [
                [0.0, 50.0, 100.0],
                [0.0, 50.0, 100.0],
            ],
            dtype=np.float32,
        ),
    )

    monkeypatch.setattr(
        step13_attributes,
        "_prepare_dem_tile_paths",
        lambda **kwargs: (
            "https://catalogue.data.gov.bc.ca/dataset/example-dem",
            "https://pub.data.gov.bc.ca/datasets/example/",
            ("092o07",),
            (dem_path,),
        ),
    )

    result = step13_attributes.compile_tsr_thlb_step13_attributes(
        instance_root=instance_root
    )

    written = gpd.read_feather(result.output_path)
    assert "femic_slope_pct_median" in written.columns
    assert "femic_hwy97_side" in written.columns
    assert "femic_step13_steep_slope_flag" in written.columns
    assert written["femic_hwy97_side"].tolist() == ["west", "east"]
    assert written["femic_step13_steep_slope_flag"].tolist() == [True, False]

    audit = json.loads(result.audit_path.read_text(encoding="utf-8"))
    assert audit["dem"]["tile_ids"] == ["092o07"]
    assert audit["highway_97"]["filter_field"] == "HIGHWAY_NUMBER"
    assert audit["checkpoint_summary"]["steep_slope_flag_count"] == 1
