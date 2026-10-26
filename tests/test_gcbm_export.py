"""Tests for the FEMIC GCBM walltowall exporter."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyarrow as pa
import pytest
from pyarrow import feather
from shapely import wkb
from shapely.geometry import Polygon
from typer.testing import CliRunner

from femic.cli.main import app
from femic.gcbm import (
    GcbmExportConfig,
    GcbmExportError,
    export_gcbm_project,
    validate_gcbm_project,
)

FIXTURE = Path(__file__).parent / "fixtures" / "carbon" / "tsa24_minimal"


def _checkpoint(path: Path) -> Path:
    """Write a small checkpoint with two managed TSA24 polygons."""
    polygons = [
        Polygon(
            [(1000000, 500000), (1001000, 500000), (1001000, 501000), (1000000, 501000)]
        ),
        Polygon(
            [(1002000, 500000), (1003000, 500000), (1003000, 501000), (1002000, 501000)]
        ),
    ]
    frame = pd.DataFrame(
        {
            "au": [2401000, 2401000],
            "PROJ_AGE_1": [10, 40],
            "FEATURE_AREA_SQM": [1_000_000.0, 2_000_000.0],
            "IFM_FLAG": [1, 1],
            "geometry": [wkb.dumps(polygon) for polygon in polygons],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    feather.write_feather(pa.Table.from_pandas(frame), path)
    return path


def _aidb(path: Path) -> Path:
    """Write a minimal SQLite AIDB stand-in."""
    connection = sqlite3.connect(path)
    connection.execute("create table species (id integer primary key)")
    connection.execute("insert into species values (1)")
    connection.commit()
    connection.close()
    return path


def _disturbance(path: Path) -> Path:
    """Write a vector disturbance layer."""
    frame = gpd.GeoDataFrame(
        {
            "year": [2021, 2025, 2040],
            "disturbance_type": ["Wildfire", "Wildfire", "Wildfire"],
        },
        geometry=[
            Polygon([(1000500, 500100), (1000600, 500100), (1000600, 500200)]),
            Polygon([(1002000, 500100), (1002100, 500100), (1002100, 500200)]),
            Polygon([(1002500, 500100), (1002600, 500100), (1002600, 500200)]),
        ],
        crs="EPSG:3005",
    )
    frame.to_file(path, layer="disturbances", driver="GPKG", index=False)
    return path


def _config(tmp_path: Path, **overrides: object) -> GcbmExportConfig:
    """Return a test export config."""
    values = {
        "carbon_package_dir": FIXTURE,
        "output_dir": tmp_path / "gcbm",
        "aidb_path": _aidb(tmp_path / "cbm_defaults_vtest.db"),
        "start_year": 2020,
        "end_year": 2030,
        "resolution": 0.001,
        "allow_aidb_mismatch": True,
    }
    values.update(overrides)
    if "checkpoint_path" not in values:
        values["checkpoint_path"] = _checkpoint(tmp_path / "checkpoint.feather")
    return GcbmExportConfig(**values)


def test_export_writes_walltowall_project(tmp_path: Path) -> None:
    """The exporter writes a valid config, inventory, yield table, and manifest."""
    result = export_gcbm_project(_config(tmp_path))
    assert result.fragments == 2
    assert result.tracks == 1
    assert result.area_ha == pytest.approx(300.0)
    assert result.config_path.is_file()
    assert result.inventory_path.is_file()
    assert result.yield_path.is_file()
    assert result.manifest_path.is_file()
    assert not result.aidb_matches_package
    config = json.loads(result.config_path.read_text(encoding="utf-8"))
    assert config["project_name"].startswith("femic-carbon-")
    assert config["start_year"] == 2020
    assert config["end_year"] == 2030
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["model"]["classifier_map"]["1"] == {
        "au": 2401000,
        "ifm": "managed",
    }
    assert config["classifiers"]["Classifier1"]["attribute"] == "Classifier1"
    assert config["layers"]["initial_age"]["attribute"] == "initial_age"
    assert config["aidb"].startswith("input_database/")
    assert (result.project_dir / config["aidb"]).is_file()
    inventory = gpd.read_file(result.inventory_path)
    assert len(inventory) == 2
    assert list(inventory["Classifier1"]) == [1, 1]
    assert list(inventory["Classifier2"]) == [1, 1]
    assert list(inventory["initial_age"]) == [10, 40]
    assert list(inventory["mean_annual_temperature"]) == [3.0, 3.0]
    yields = pd.read_csv(result.yield_path)
    assert list(yields.columns[:3]) == ["Classifier1", "Classifier2", "AIDBSPP"]
    assert yields.loc[0, "Classifier1"] == 1
    assert yields.loc[0, "AIDBSPP"] == "White spruce"
    assert len([column for column in yields.columns if str(column).isdigit()]) == 31
    assert validate_gcbm_project(result.project_dir) == ()


def test_export_accepts_disturbances(tmp_path: Path) -> None:
    """A disturbance vector is clipped to the window and emitted once."""
    result = export_gcbm_project(
        _config(tmp_path, disturbance_path=_disturbance(tmp_path / "disturbances.gpkg"))
    )
    assert result.disturbance_path is not None
    config = json.loads(result.config_path.read_text(encoding="utf-8"))
    assert "disturbances.gpkg" in config["disturbances"]
    assert config["disturbances"]["disturbances.gpkg"]["year"] == "year"
    assert result.warnings
    frame = gpd.read_file(result.disturbance_path)
    assert len(frame) == 2
    assert validate_gcbm_project(result.project_dir) == ()


def test_aidb_mismatch_requires_override(tmp_path: Path) -> None:
    """An AIDB hash mismatch fails unless the caller allows it."""
    config = _config(tmp_path, allow_aidb_mismatch=False)
    with pytest.raises(GcbmExportError, match="AIDB hash"):
        export_gcbm_project(config)


def test_checkpoint_without_matching_track_fails(tmp_path: Path) -> None:
    """A checkpoint AU/IFM with no package track is rejected."""
    checkpoint = _checkpoint(tmp_path / "checkpoint.feather")
    frame = pd.read_feather(checkpoint)
    frame["au"] = 999999
    feather.write_feather(pa.Table.from_pandas(frame), checkpoint)
    with pytest.raises(GcbmExportError, match="no package track"):
        export_gcbm_project(_config(tmp_path, checkpoint_path=checkpoint))


def test_missing_carbon_package_fails(tmp_path: Path) -> None:
    """A missing carbon package is reported clearly."""
    with pytest.raises(FileNotFoundError, match="carbon package"):
        export_gcbm_project(_config(tmp_path, carbon_package_dir=tmp_path / "missing"))


def test_cli_exports_project(tmp_path: Path) -> None:
    """The CLI maps the exporter onto `femic export gcbm`."""
    checkpoint = _checkpoint(tmp_path / "checkpoint.feather")
    aidb = _aidb(tmp_path / "cbm_defaults_vtest.db")
    output = tmp_path / "cli-gcbm"
    result = CliRunner().invoke(
        app,
        [
            "export",
            "gcbm",
            "--checkpoint",
            str(checkpoint),
            "--carbon-package",
            str(FIXTURE),
            "--output-dir",
            str(output),
            "--aidb",
            str(aidb),
            "--allow-aidb-mismatch",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "GCBM export prepared" in result.output
    assert (output / "walltowall_config.json").is_file()
    assert "fragments=2" in result.output
