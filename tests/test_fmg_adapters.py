from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from femic.fmg.adapters import (
    build_bundle_model_context,
    build_bundle_model_context_from_tables,
    normalize_tsa_code,
)
from femic.fmg.core import CurvePoint


def _write_bundle_tables(bundle_dir: Path) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "treated_curve_id": 21001,
                "untreated_curve_id": 1001,
            },
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "treated_curve_id": 21001,
                "untreated_curve_id": 1001,
            },
        ]
    ).to_csv(bundle_dir / "au_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "untreated"},
            {"curve_id": 21001, "curve_type": "treated"},
            {"curve_id": 21001001, "curve_type": "treated_species_prop_PL"},
            {"curve_id": 1001001, "curve_type": "untreated_species_prop_PL"},
        ]
    ).to_csv(bundle_dir / "curve_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 10.0},
            {"curve_id": 1001, "x": 2, "y": 20.0},
            {"curve_id": 21001, "x": 1, "y": 12.0},
            {"curve_id": 21001, "x": 2, "y": 25.0},
            {"curve_id": 21001001, "x": 1, "y": 0.70},
            {"curve_id": 1001001, "x": 1, "y": 0.60},
        ]
    ).to_csv(bundle_dir / "curve_points_table.csv", index=False)


def test_normalize_tsa_code() -> None:
    assert normalize_tsa_code("29") == "29"
    assert normalize_tsa_code(8) == "08"
    assert normalize_tsa_code("K3Z") == "k3z"


def test_build_bundle_model_context_from_tables_scopes_and_dedupes() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "treated_curve_id": 21001,
                "untreated_curve_id": 1001,
            },
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "treated_curve_id": 21001,
                "untreated_curve_id": 1001,
            },
            {
                "au_id": 2001,
                "tsa": "k3z",
                "stratum_code": "CWH_HW",
                "si_level": "M",
                "treated_curve_id": 22001,
                "untreated_curve_id": 2001,
            },
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "untreated"},
            {"curve_id": 21001, "curve_type": "treated"},
            {"curve_id": 21001001, "curve_type": "treated_species_prop_PL"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 10.0},
            {"curve_id": 21001, "x": 1, "y": 12.0},
            {"curve_id": 21001001, "x": 1, "y": 0.7},
        ]
    )

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["29"],
    )

    assert context.tsa_list == ["29"]
    assert len(context.analysis_units) == 1
    assert context.analysis_units[0].au_id == 1001
    assert 1001 in context.curves_by_id
    assert context.managed_species_curve_ids[21001]["PL"] == 21001001


def test_build_bundle_model_context_reads_csv(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    context = build_bundle_model_context(bundle_dir=bundle_dir, tsa_list=["29"])
    assert context.tsa_list == ["29"]
    assert len(context.analysis_units) == 1
    assert context.analysis_units[0].managed_curve_id == 21001
    assert len(context.curves_by_id[1001].points) == 2


def test_build_bundle_model_context_thins_unmanaged_curves_to_decadal_knots() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "treated_curve_id": 21001,
                "untreated_curve_id": 1001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "untreated"},
            {"curve_id": 21001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [{"curve_id": 1001, "x": age, "y": float(age)} for age in range(1, 13)]
        + [{"curve_id": 21001, "x": age, "y": float(age * 2)} for age in range(1, 13)]
    )

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["29"],
    )

    assert [point.x for point in context.curves_by_id[1001].points] == [1.0, 10.0, 12.0]
    assert [point.x for point in context.curves_by_id[21001].points] == [
        float(age) for age in range(1, 13)
    ]


def test_build_bundle_model_context_loads_managed_stems_fallback_from_btc_input(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "data" / "model_input_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "treated_curve_id": 985522001,
                "untreated_curve_id": 985502001,
                "source_local_au_id": 2001,
                "source_managed_local_au_id": 22001,
                "source_unmanaged_local_au_id": 2001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "untreated"},
            {"curve_id": 985522001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 0, "y": 0.0},
            {"curve_id": 985502001, "x": 10, "y": 30.0},
            {"curve_id": 985522001, "x": 0, "y": 0.0},
            {"curve_id": 985522001, "x": 10, "y": 36.0},
        ]
    )
    au_table.to_csv(bundle_dir / "au_table.csv", index=False)
    curve_table.to_csv(bundle_dir / "curve_table.csv", index=False)
    curve_points.to_csv(bundle_dir / "curve_points_table.csv", index=False)
    pd.DataFrame(
        [
            {"AU": 22001, "Age": 0, "Yield": 0.0, "Height": 0.0, "TPH": float("nan")},
            {"AU": 22001, "Age": 10, "Yield": 36.0, "Height": 4.0, "TPH": float("nan")},
        ]
    ).to_csv(tmp_path / "data" / "tipsy_curves_tsak3z.csv", index=False)
    pd.DataFrame(
        [
            {
                "feature_id": 22001,
                "planted_density1": 630,
                "planted_density2": 180,
                "planted_density3": 90,
                "natural_density1": 0,
            }
        ]
    ).to_csv(tmp_path / "data" / "03_input-tsak3z.csv", index=False)

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
        bundle_dir=bundle_dir,
    )

    support = context.qmd_support_by_au[985502001]
    assert support.managed_stems_per_ha == pytest.approx(900.0)
    assert support.managed_tph_points == ()


def test_build_bundle_model_context_loads_log_grade_indicator_curves_from_tipsy(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "data" / "model_input_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "treated_curve_id": 985522001,
                "untreated_curve_id": 985502001,
                "source_local_au_id": 2001,
                "source_managed_local_au_id": 22001,
                "source_unmanaged_local_au_id": 2001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "untreated"},
            {"curve_id": 985522001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 0, "y": 0.0},
            {"curve_id": 985502001, "x": 10, "y": 30.0},
            {"curve_id": 985502001, "x": 20, "y": 80.0},
            {"curve_id": 985522001, "x": 0, "y": 0.0},
            {"curve_id": 985522001, "x": 10, "y": 36.0},
            {"curve_id": 985522001, "x": 20, "y": 90.0},
        ]
    )
    au_table.to_csv(bundle_dir / "au_table.csv", index=False)
    curve_table.to_csv(bundle_dir / "curve_table.csv", index=False)
    curve_points.to_csv(bundle_dir / "curve_points_table.csv", index=False)
    pd.DataFrame(
        [
            {
                "AU": 22001,
                "Age": 0,
                "Yield": 0.0,
                "Height": 0.0,
                "TPH": 0.0,
                "Logs_Grade_D": 0.0,
                "Logs_Grade_All": 0.0,
            },
            {
                "AU": 22001,
                "Age": 10,
                "Yield": 36.0,
                "Height": 4.0,
                "TPH": 900.0,
                "Logs_Grade_D": 7.0,
                "Logs_Grade_All": 14.0,
            },
            {
                "AU": 22001,
                "Age": 20,
                "Yield": 90.0,
                "Height": 9.0,
                "TPH": 700.0,
                "Logs_Grade_D": 18.0,
                "Logs_Grade_All": 30.0,
            },
        ]
    ).to_csv(tmp_path / "data" / "tipsy_curves_tsak3z.csv", index=False)

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
        bundle_dir=bundle_dir,
    )

    indicator_curves = context.managed_indicator_curves_by_au[985502001]
    assert indicator_curves["Logs_Grade_D"] == (
        CurvePoint(x=0.0, y=0.0),
        CurvePoint(x=10.0, y=7.0),
        CurvePoint(x=20.0, y=18.0),
    )
    assert indicator_curves["Logs_Grade_All"] == (
        CurvePoint(x=0.0, y=0.0),
        CurvePoint(x=10.0, y=14.0),
        CurvePoint(x=20.0, y=30.0),
    )


def test_build_bundle_model_context_uses_deterministic_managed_local_au_crosswalk(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "data" / "model_input_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "treated_curve_id": 985522001,
                "untreated_curve_id": 985502001,
                "source_local_au_id": 2001,
                "source_managed_local_au_id": 22001,
                "source_unmanaged_local_au_id": 2001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "untreated"},
            {"curve_id": 985522001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 0, "y": 0.0},
            {"curve_id": 985502001, "x": 10, "y": 30.0},
            {"curve_id": 985522001, "x": 0, "y": 0.0},
            {"curve_id": 985522001, "x": 10, "y": 999.0},
        ]
    )
    au_table.to_csv(bundle_dir / "au_table.csv", index=False)
    curve_table.to_csv(bundle_dir / "curve_table.csv", index=False)
    curve_points.to_csv(bundle_dir / "curve_points_table.csv", index=False)
    pd.DataFrame(
        [
            {
                "AU": 22001,
                "Age": 0,
                "Yield": 0.0,
                "Height": 0.0,
                "TPH": 0.0,
                "Logs_Grade_J": 0.0,
            },
            {
                "AU": 22001,
                "Age": 10,
                "Yield": 36.0,
                "Height": 4.0,
                "TPH": 900.0,
                "Logs_Grade_J": 12.0,
            },
        ]
    ).to_csv(tmp_path / "data" / "tipsy_curves_tsak3z.csv", index=False)

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
        bundle_dir=bundle_dir,
    )

    assert context.managed_indicator_curves_by_au[985502001]["Logs_Grade_J"] == (
        CurvePoint(x=0.0, y=0.0),
        CurvePoint(x=10.0, y=12.0),
    )


def test_build_bundle_model_context_requires_tsa(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    with pytest.raises(ValueError, match="at least one TSA"):
        build_bundle_model_context(bundle_dir=bundle_dir, tsa_list=[])
