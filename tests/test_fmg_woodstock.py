from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from shapely.geometry import Polygon

from femic.fmg.woodstock import export_woodstock_package


def _write_bundle_tables(bundle_dir: Path) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "au_id": 985501000,
                "tsa": "k3z",
                "stratum_code": "CWHvm_HW+FDC",
                "si_level": "L",
                "managed_curve_id": 985521000,
                "unmanaged_curve_id": 985501000,
            }
        ]
    ).to_csv(bundle_dir / "au_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    ).to_csv(bundle_dir / "curve_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 2, "y": 15.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 2, "y": 20.0},
        ]
    ).to_csv(bundle_dir / "curve_points_table.csv", index=False)


def test_export_woodstock_package_writes_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    checkpoint_path = tmp_path / "checkpoint7.feather"
    output_dir = tmp_path / "woodstock_export"

    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 74,
                "FEATURE_AREA_SQM": 12000.0,
                "thlb_raw": 1,
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    result = export_woodstock_package(
        bundle_dir=bundle_dir,
        checkpoint_path=checkpoint_path,
        output_dir=output_dir,
        tsa_list=["k3z"],
    )

    assert result.yields_csv_path.is_file()
    assert result.areas_csv_path.is_file()
    assert result.actions_csv_path.is_file()
    assert result.transitions_csv_path.is_file()
    yields = pd.read_csv(result.yields_csv_path)
    areas = pd.read_csv(result.areas_csv_path)
    actions = pd.read_csv(result.actions_csv_path)
    transitions = pd.read_csv(result.transitions_csv_path)
    assert set(["tsa", "au_id", "ifm", "age", "volume"]).issubset(yields.columns)
    assert set(yields["ifm"].unique()) == {"managed", "unmanaged"}
    assert set(["stand_id", "tsa", "au_id", "ifm", "age", "area_ha"]).issubset(
        areas.columns
    )
    assert set(
        [
            "tsa",
            "au_id",
            "action_id",
            "from_ifm",
            "to_ifm",
            "min_age",
            "max_age",
            "managed_curve_id",
        ]
    ).issubset(actions.columns)
    assert set(
        ["tsa", "au_id", "action_id", "from_ifm", "to_ifm", "next_au_id"]
    ).issubset(transitions.columns)
    assert actions.loc[0, "action_id"] == "CC"
    assert transitions.loc[0, "to_ifm"] == "managed"


def test_export_woodstock_package_requires_tsa(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    with pytest.raises(ValueError, match="at least one TSA"):
        export_woodstock_package(
            bundle_dir=bundle_dir,
            checkpoint_path=tmp_path / "checkpoint7.feather",
            output_dir=tmp_path / "woodstock_export",
            tsa_list=[],
        )


def test_export_woodstock_package_emits_species_split_products(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    checkpoint_path = tmp_path / "checkpoint7.feather"
    species_checkpoint_path = tmp_path / "ria_vri_vclr1p_checkpoint4.feather"
    output_dir = tmp_path / "woodstock_export"
    checkpoint_path.touch()
    species_checkpoint_path.touch()

    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 74,
                "FEATURE_AREA_SQM": 12000.0,
                "thlb_raw": 1,
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    species_df = pd.DataFrame(
        [
            {
                "FEATURE_ID": 1,
                "FEATURE_AREA_SQM": 100.0,
                "live_vol_per_ha_125_SW": 30.0,
                "live_vol_per_ha_125_AT": 10.0,
            }
        ]
    )
    au_df = pd.DataFrame([{"FEATURE_ID": 1, "au": 985501000}])

    def _fake_read_feather(path, *args, **kwargs):
        if str(path).endswith("checkpoint4.feather"):
            return species_df
        if "columns" in kwargs:
            wanted = set(kwargs["columns"])
            return au_df[[c for c in au_df.columns if c in wanted]]
        return checkpoint_df

    monkeypatch.setattr("femic.fmg.patchworks.pd.read_feather", _fake_read_feather)

    result = export_woodstock_package(
        bundle_dir=bundle_dir,
        checkpoint_path=checkpoint_path,
        output_dir=output_dir,
        tsa_list=["k3z"],
    )

    yields = pd.read_csv(result.yields_csv_path)
    assert "product" in yields.columns
    products = set(yields["product"].unique())
    assert products == {"totvol", "swdvol", "hwdvol"}
    unmanaged_sw = yields[
        (yields["ifm"] == "unmanaged")
        & (yields["product"] == "swdvol")
        & (yields["age"] == 1)
    ]
    unmanaged_hw = yields[
        (yields["ifm"] == "unmanaged")
        & (yields["product"] == "hwdvol")
        & (yields["age"] == 1)
    ]
    # 30/(30+10) = 0.75 softwood, 0.25 hardwood of totvol=10.0
    assert abs(float(unmanaged_sw["volume"].iloc[0]) - 7.5) < 1e-9
    assert abs(float(unmanaged_hw["volume"].iloc[0]) - 2.5) < 1e-9
