from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from femic.fmg.adapters import (
    BundleAuxiliaryData,
    BundleAuxiliaryRequest,
    discover_bundle_auxiliary_providers,
    build_bundle_model_context,
    build_bundle_model_context_from_tables,
    normalize_tsa_code,
)
from femic.fmg.core import CurvePoint, QmdSupportDefinition


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


def test_build_bundle_model_context_accepts_auxiliary_qmd_support(
    tmp_path: Path,
) -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 2001,
                "tsa": "demo",
                "stratum_code": "CWH_HW",
                "si_level": "M",
                "treated_curve_id": 22001,
                "untreated_curve_id": 2001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 2001, "curve_type": "untreated"},
            {"curve_id": 22001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 2001, "x": 0, "y": 0.0},
            {"curve_id": 2001, "x": 10, "y": 30.0},
            {"curve_id": 22001, "x": 0, "y": 0.0},
            {"curve_id": 22001, "x": 10, "y": 36.0},
        ]
    )

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["demo"],
        bundle_dir=tmp_path,
        auxiliary_data=BundleAuxiliaryData(
            qmd_support_by_au={
                2001: QmdSupportDefinition(
                    site_index=27.5,
                    unmanaged_stems_per_ha=450.0,
                    managed_stems_per_ha=900.0,
                    managed_height_points=(),
                    managed_tph_points=(),
                )
            }
        ),
    )

    support = context.qmd_support_by_au[2001]
    assert support.site_index == pytest.approx(27.5)
    assert support.unmanaged_stems_per_ha == pytest.approx(450.0)
    assert support.managed_stems_per_ha == pytest.approx(900.0)


def test_build_bundle_model_context_uses_auxiliary_provider(
    tmp_path: Path,
) -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 2001,
                "tsa": "demo",
                "stratum_code": "CWH_HW",
                "si_level": "M",
                "treated_curve_id": 22001,
                "untreated_curve_id": 2001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 2001, "curve_type": "untreated"},
            {"curve_id": 22001, "curve_type": "treated"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 2001, "x": 0, "y": 0.0},
            {"curve_id": 2001, "x": 10, "y": 30.0},
            {"curve_id": 22001, "x": 0, "y": 0.0},
            {"curve_id": 22001, "x": 10, "y": 36.0},
        ]
    )

    class DemoProvider:
        provider_id = "demo"

        def build_bundle_auxiliary(
            self, request: BundleAuxiliaryRequest
        ) -> BundleAuxiliaryData:
            assert request.tsa_list == ("demo",)
            return BundleAuxiliaryData(
                managed_indicator_curves_by_au={
                    2001: {
                        "demo_curve": (
                            CurvePoint(x=0.0, y=0.0),
                            CurvePoint(x=10.0, y=12.0),
                        )
                    }
                }
            )

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["demo"],
        bundle_dir=tmp_path,
        auxiliary_providers=[DemoProvider()],
    )

    assert context.managed_indicator_curves_by_au[2001]["demo_curve"] == (
        CurvePoint(x=0.0, y=0.0),
        CurvePoint(x=10.0, y=12.0),
    )


def test_discover_bundle_auxiliary_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    class DemoProvider:
        provider_id = "demo"

        def build_bundle_auxiliary(
            self, request: BundleAuxiliaryRequest
        ) -> BundleAuxiliaryData:
            _ = request
            return BundleAuxiliaryData()

    class DemoEntryPoint:
        name = "demo"

        def load(self) -> object:
            return DemoProvider

    class DemoEntryPoints:
        def select(self, *, group: str) -> tuple[DemoEntryPoint, ...]:
            assert group == "femic.fmg_bundle_auxiliary"
            return (DemoEntryPoint(),)

    monkeypatch.setattr(
        "femic.fmg.adapters.metadata.entry_points",
        lambda: DemoEntryPoints(),
    )

    providers = discover_bundle_auxiliary_providers()

    assert [provider.provider_id for provider in providers] == ["demo"]


def test_build_bundle_model_context_requires_tsa(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    with pytest.raises(ValueError, match="at least one TSA"):
        build_bundle_model_context(bundle_dir=bundle_dir, tsa_list=[])
