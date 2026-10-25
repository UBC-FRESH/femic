"""Tests for the FEMIC static carbon package exporter."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from femic.carbon import (
    CarbonExportConfig,
    build_carbon_package_tables,
    load_carbon_export_config,
    track_names_from_compiled_dataset,
    write_carbon_package,
)
from femic.carbon.package import DisturbanceMapping, SpeciesMapping
from femic.fmg.core import (
    AnalysisUnitDefinition,
    BundleModelContext,
    CurveDefinition,
    CurvePoint,
)


def _config() -> CarbonExportConfig:
    """Return a compact synthetic export config."""
    return load_carbon_export_config(
        Path("config/carbon"),
        admin_boundary="British Columbia",
        eco_boundary="Montane Cordillera",
        cbm_defaults_version="1.2.9300.391",
        cbm_defaults_sha256="b" * 64,
    )


def _context() -> BundleModelContext:
    """Return a one-AU bundle-like context."""
    return BundleModelContext(
        tsa_list=["24"],
        analysis_units=(
            AnalysisUnitDefinition(
                au_id=1,
                tsa="24",
                stratum_code="2401002_SW",
                si_level="1",
                managed_curve_id=2,
                unmanaged_curve_id=1,
            ),
        ),
        curves_by_id={
            1: CurveDefinition(
                1,
                "unmanaged",
                (CurvePoint(0, 0), CurvePoint(40, 120), CurvePoint(80, 220)),
            ),
            2: CurveDefinition(
                2,
                "managed",
                (CurvePoint(0, 0), CurvePoint(10, 50), CurvePoint(40, 180)),
            ),
        },
        managed_species_curve_ids={},
        unmanaged_species_curve_ids={},
        qmd_support_by_au={},
        curve_row_count=2,
    )


def _inventory() -> pd.DataFrame:
    """Return two managed fragments on the canonical track."""
    return pd.DataFrame(
        {
            "au_id": [1, 1],
            "ifm": ["managed", "managed"],
            "age": [10, 20],
            "area_ha": [3.0, 2.0],
        }
    )


def test_build_tables_has_all_contract_tables() -> None:
    """The builder emits the nine package tables."""
    tables = build_carbon_package_tables(
        context=_context(), inventory=_inventory(), config=_config()
    )
    assert set(tables) == {
        "classifiers",
        "disturbance_types",
        "age_classes",
        "inventory",
        "yield",
        "track_carbon_map",
        "curve_carbon_map",
        "species_map",
        "boundaries",
    }
    assert tables["inventory"]["area_ha"].sum() == 5.0
    assert tables["track_carbon_map"].shape[0] == 1
    assert tables["track_carbon_map"].loc[0, "classifier_set"].endswith(";softwood")
    assert tables["yield"].shape[0] == 31
    assert (
        tables["yield"].loc[tables["yield"]["age"] == 10, "volume_m3_ha"].iloc[0]
        == 50.0
    )
    assert (
        tables["yield"].loc[tables["yield"]["age"] == 40, "volume_m3_ha"].iloc[0]
        == 180.0
    )


def test_write_package_writes_manifest_and_hashes(tmp_path: Path) -> None:
    """The writer produces the manifest, tables, and table hashes."""
    tables = build_carbon_package_tables(
        context=_context(), inventory=_inventory(), config=_config()
    )
    result = write_carbon_package(
        tables=tables,
        output_dir=tmp_path / "package",
        config=_config(),
        source_hashes=[("synthetic", "a" * 64)],
        package_label="24",
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "0.1"
    assert manifest["package_id"] == result.package_id
    assert set(manifest["table_hashes"]) == set(tables)
    assert result.package_dir == tmp_path / "package"
    assert result.track_count == 1
    assert result.yield_rows == 31


def test_track_names_from_compiled_dataset(tmp_path: Path) -> None:
    """Exact track names are read from a compiled dataset when available."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    pd.DataFrame(
        {
            "track_id": [1, 2],
            "name": [
                "AU(1)+IFM(managed)+treatment()",
                "AU(2)+IFM(unmanaged)+treatment()",
            ],
        }
    ).to_parquet(dataset / "tracks.parquet", index=False)
    mapping = track_names_from_compiled_dataset(dataset)
    assert mapping[(1, "managed")] == "AU(1)+IFM(managed)+treatment()"
    assert mapping[(2, "unmanaged")] == "AU(2)+IFM(unmanaged)+treatment()"


def test_config_loads_the_repo_crosswalks() -> None:
    """The draft crosswalk files parse into the export config."""
    config = _config()
    assert isinstance(config.species_map["SW"], SpeciesMapping)
    assert config.species_map["SW"].cbm_species == "White spruce"
    assert isinstance(config.disturbance_map["cc"], DisturbanceMapping)
    assert config.land_class_by_ifm["managed"] == 0
