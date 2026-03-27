from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as et

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

from femic.fmg.core import (
    AnalysisUnitDefinition,
    BundleModelContext,
    CurveDefinition,
    CurvePoint,
    QmdSupportDefinition,
)
from femic.fmg.patchworks import (
    _au_base_display_label,
    _build_curve_with_post_thinning_gap,
    _build_qmd_curve_points,
    _build_stems_per_ha_curve_points,
    _estimate_qmd_cm_from_volume,
    _sanitize_id_component,
    build_fragments_geodataframe,
    build_forestmodel_xml_tree_from_context,
    build_patchworks_forestmodel_definition,
    build_forestmodel_xml_tree,
    export_patchworks_package,
    validate_forestmodel_xml_tree,
    validate_fragments_geodataframe,
    write_forestmodel_xml,
)


def _au_label(stratum_code: str, si_level: str, *, tsa: str | None = None) -> str:
    base = _au_base_display_label(stratum_code=stratum_code, si_level=si_level)
    label = f"{tsa}-{base}" if tsa else base
    return _sanitize_id_component(label)


def _au_token(stratum_code: str, si_level: str, *, tsa: str | None = None) -> str:
    return _sanitize_id_component(_au_label(stratum_code, si_level, tsa=tsa))


def _write_bundle_tables(bundle_dir: Path) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "au_id": 985501000,
                "tsa": "k3z",
                "stratum_code": "CWHvm_HW+FDC",
                "si_level": "L",
                "canfi_species": 402,
                "unmanaged_curve_id": 985501000,
                "managed_curve_id": 985521000,
            }
        ]
    ).to_csv(bundle_dir / "au_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {
                "curve_id": 985521000001,
                "curve_type": "managed_species_prop_HW",
            },
            {
                "curve_id": 985501000001,
                "curve_type": "unmanaged_species_prop_HW",
            },
        ]
    ).to_csv(bundle_dir / "curve_table.csv", index=False)
    pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 55.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
            {"curve_id": 985521000001, "x": 1, "y": 0.7},
            {"curve_id": 985501000001, "x": 1, "y": 0.6},
        ]
    ).to_csv(bundle_dir / "curve_points_table.csv", index=False)


def _build_single_au_context(
    *,
    au_id: int,
    stratum_code: str,
    si_level: str,
    unmanaged_points: tuple[CurvePoint, ...],
    managed_points: tuple[CurvePoint, ...],
    managed_species_curve_ids: dict[str, int] | None = None,
    unmanaged_species_curve_ids: dict[str, int] | None = None,
    curve_points_by_id: dict[int, tuple[CurvePoint, ...]] | None = None,
    qmd_support: QmdSupportDefinition | None = None,
) -> BundleModelContext:
    managed_curve_id = au_id + 20000
    managed_species_curve_ids = managed_species_curve_ids or {}
    unmanaged_species_curve_ids = unmanaged_species_curve_ids or {}
    curve_points_by_id = curve_points_by_id or {}
    curves_by_id: dict[int, CurveDefinition] = {
        au_id: CurveDefinition(
            curve_id=au_id,
            curve_type="unmanaged",
            points=unmanaged_points,
        ),
        managed_curve_id: CurveDefinition(
            curve_id=managed_curve_id,
            curve_type="managed",
            points=managed_points,
        ),
    }
    for curve_id, points in curve_points_by_id.items():
        curve_type = "managed_species_prop_CW"
        if curve_id in unmanaged_species_curve_ids.values():
            curve_type = "unmanaged_species_prop_CW"
        curves_by_id[curve_id] = CurveDefinition(
            curve_id=curve_id,
            curve_type=curve_type,
            points=points,
        )
    return BundleModelContext(
        tsa_list=["k3z"],
        analysis_units=(
            AnalysisUnitDefinition(
                au_id=au_id,
                tsa="k3z",
                stratum_code=stratum_code,
                si_level=si_level,
                managed_curve_id=managed_curve_id,
                unmanaged_curve_id=au_id,
            ),
        ),
        curves_by_id=curves_by_id,
        managed_species_curve_ids={managed_curve_id: managed_species_curve_ids},
        unmanaged_species_curve_ids={au_id: unmanaged_species_curve_ids},
        qmd_support_by_au={au_id: qmd_support or QmdSupportDefinition()},
        curve_row_count=len(curves_by_id),
    )


def test_estimate_qmd_cm_from_volume_returns_plausible_positive_value() -> None:
    qmd_cm = _estimate_qmd_cm_from_volume(
        stand_volume_m3_per_ha=300.0,
        height_m=20.0,
        stems_per_ha=500.0,
    )
    assert qmd_cm == pytest.approx(32.284, rel=1e-3)


def test_build_qmd_curve_points_uses_height_and_tph_inputs() -> None:
    points = _build_qmd_curve_points(
        source_curve_points=(
            CurvePoint(x=10.0, y=40.0),
            CurvePoint(x=20.0, y=120.0),
        ),
        si_level="M",
        site_index=20.0,
        height_curve_points=(
            CurvePoint(x=10.0, y=5.0),
            CurvePoint(x=20.0, y=10.0),
        ),
        tph_curve_points=(
            CurvePoint(x=10.0, y=800.0),
            CurvePoint(x=20.0, y=700.0),
        ),
    )
    assert [point.y for point in points] == pytest.approx([18.6, 24.4], rel=1e-3)


def test_build_stems_per_ha_curve_points_uses_tph_inputs() -> None:
    points = _build_stems_per_ha_curve_points(
        source_curve_points=(
            CurvePoint(x=10.0, y=40.0),
            CurvePoint(x=20.0, y=120.0),
        ),
        tph_curve_points=(
            CurvePoint(x=10.0, y=800.0),
            CurvePoint(x=20.0, y=700.0),
        ),
    )
    assert [point.y for point in points] == pytest.approx([800.0, 700.0], rel=1e-3)


def test_build_forestmodel_xml_tree_contains_cc_and_curve_refs() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert "treatment" in xml_text
    assert 'label="CC"' in xml_text
    assert "feature.Yield.managed.Total" in xml_text
    assert "product.Yield.managed.Total" in xml_text
    assert "product.HarvestedVolume.managed.Total.CC" in xml_text
    assert "AU eq 985501000" in xml_text


def test_build_forestmodel_xml_tree_adds_retention_to_managed_selects() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert 'field="RETENTION" column="Number(column(\'RETENTION\'))"' in xml_text
    assert '<retention factor="RETENTION">' in xml_text
    assert '<assign field="IFM" value="\'unmanaged\'"' in xml_text


def test_build_patchworks_forestmodel_definition_contains_treatment() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )
    from femic.fmg.adapters import build_bundle_model_context_from_tables

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
    )
    definition = build_patchworks_forestmodel_definition(context=context)
    assert definition.define_fields[0].field == "AU"
    treatment_selects = [s for s in definition.selects if s.track_treatment is not None]
    assert any(
        s.track_treatment is not None and s.track_treatment.label == "CC"
        for s in treatment_selects
    )
    assert all(
        any(
            a.field == "ORIGIN" and a.value == "'planted'"
            for a in s.track_treatment.transition_assignments
        )
        for s in treatment_selects
        if s.track_treatment is not None
    )


def test_build_forestmodel_xml_tree_disambiguates_duplicate_au_labels_by_tsa() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985501000,
                "tsa": "k3z",
                "stratum_code": "CWHvm_HW+FDC",
                "si_level": "L",
                "managed_curve_id": 985521000,
                "unmanaged_curve_id": 985501000,
            },
            {
                "au_id": 801000,
                "tsa": "08",
                "stratum_code": "CWHvm_HW+FDC",
                "si_level": "L",
                "managed_curve_id": 821000,
                "unmanaged_curve_id": 801000,
            },
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {"curve_id": 801000, "curve_type": "unmanaged"},
            {"curve_id": 821000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 801000, "x": 1, "y": 9.0},
            {"curve_id": 821000, "x": 1, "y": 11.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    xml_text = et.tostring(root, encoding="unicode")

    assert "feature.Area.og1.k3z_CWHvm_HW_FDC_L" in xml_text
    assert "feature.Area.og1.08_CWHvm_HW_FDC_L" in xml_text


def test_build_patchworks_forestmodel_definition_allows_unmanaged_transition_ifm() -> (
    None
):
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )
    from femic.fmg.adapters import build_bundle_model_context_from_tables

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
    )
    definition = build_patchworks_forestmodel_definition(
        context=context,
        cc_transition_ifm="unmanaged",
    )
    treatment_selects = [s for s in definition.selects if s.track_treatment is not None]
    assert any(
        any(
            a.field == "IFM" and a.value == "'unmanaged'"
            for a in s.track_treatment.transition_assignments
        )
        for s in treatment_selects
        if s.track_treatment is not None
    )


def test_build_forestmodel_xml_tree_adds_species_yield_curves() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {"curve_id": 985501000001, "curve_type": "unmanaged_species_prop_HW"},
            {"curve_id": 985521000001, "curve_type": "managed_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 55.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
            {"curve_id": 985501000001, "x": 1, "y": 0.6},
            {"curve_id": 985521000001, "x": 1, "y": 0.7},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    au_token = _au_token("CWHvm_HW+FDC", "L")

    unmanaged_curve = root.find(
        f"./curve[@id='au_{au_token}_unmanaged_natural_yield_HW']"
    )
    managed_curve = root.find(f"./curve[@id='au_{au_token}_managed_planted_yield_HW']")
    assert unmanaged_curve is not None
    assert managed_curve is not None
    unmanaged_points = unmanaged_curve.findall("./point")
    managed_points = managed_curve.findall("./point")
    assert unmanaged_points[0].attrib == {"x": "1", "y": "6.0"}
    assert unmanaged_points[1].attrib == {"x": "10", "y": "33.0"}
    assert managed_points[0].attrib == {"x": "1", "y": "8.4"}
    assert managed_points[1].attrib == {"x": "10", "y": "49.0"}

    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.Yield.unmanaged.HW" in xml_text
    assert "feature.Yield.managed.HW" in xml_text
    assert "product.Yield.managed.HW" in xml_text
    assert "product.HarvestedVolume.managed.HW.CC" in xml_text


def test_build_forestmodel_xml_tree_adds_old_growth_attributes_and_curves() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 5.0},
            {"curve_id": 985501000, "x": 40, "y": 200.0},
            {"curve_id": 985501000, "x": 100, "y": 350.0},
            {"curve_id": 985521000, "x": 1, "y": 8.0},
            {"curve_id": 985521000, "x": 40, "y": 240.0},
            {"curve_id": 985521000, "x": 100, "y": 380.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )

    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.Area.og1.CWHvm_HW_FDC_L" in xml_text
    assert "feature.Area.og1.total" in xml_text
    assert "feature.Area.og2.CWHvm_HW_FDC_L" in xml_text
    assert "feature.Area.og2.total" in xml_text

    og1_curve = root.find("./curve[@id='au_CWHvm_HW_FDC_L_og1']")
    assert og1_curve is not None
    og1_points = [point.attrib for point in og1_curve.findall("./point")]
    assert og1_points == [{"x": "1", "y": "0.0"}, {"x": "100", "y": "1.0"}]

    og2_curve = root.find("./curve[@id='au_CWHvm_HW_FDC_L_og2']")
    assert og2_curve is not None
    og2_points = [point.attrib for point in og2_curve.findall("./point")]
    assert og2_points == [{"x": "249", "y": "0.0"}, {"x": "250", "y": "1.0"}]


def test_build_forestmodel_xml_tree_reuses_unmanaged_species_props_for_managed_fallback() -> (
    None
):
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985501000,
                "tsa": "k3z",
                "stratum_code": "CWHvm_HW+FDC",
                "si_level": "L",
                "managed_curve_id": 985501000,
                "unmanaged_curve_id": 985501000,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985501000001, "curve_type": "unmanaged_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 50.0},
            {"curve_id": 985501000001, "x": 1, "y": 0.6},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    au_token = _au_token("CWHvm_HW+FDC", "L")

    managed_curve = root.find(f"./curve[@id='au_{au_token}_managed_planted_yield_HW']")
    assert managed_curve is not None
    points = managed_curve.findall("./point")
    assert points[0].attrib == {"x": "1", "y": "6.0"}
    assert points[1].attrib == {"x": "10", "y": "30.0"}

    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.Yield.managed.HW" in xml_text
    assert "product.Yield.managed.HW" in xml_text
    assert "product.HarvestedVolume.managed.HW.CC" in xml_text
    assert "feature.SpeciesProp.managed.HW" in xml_text
    assert "product.SpeciesProp.managed.HW" in xml_text


def test_build_forestmodel_xml_tree_reuses_unmanaged_species_when_managed_prop_is_zero() -> (
    None
):
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {"curve_id": 985501000001, "curve_type": "unmanaged_species_prop_HW"},
            {"curve_id": 985521000001, "curve_type": "managed_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 50.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
            {"curve_id": 985501000001, "x": 1, "y": 0.6},
            {"curve_id": 985521000001, "x": 1, "y": 0.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    au_token = _au_token("CWHvm_HW+FDC", "L")

    managed_curve = root.find(f"./curve[@id='au_{au_token}_managed_planted_yield_HW']")
    assert managed_curve is not None
    points = managed_curve.findall("./point")
    assert points[0].attrib == {"x": "1", "y": "7.2"}
    assert points[1].attrib == {"x": "10", "y": "42.0"}

    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.SpeciesProp.managed.HW" in xml_text
    assert "product.SpeciesProp.managed.HW" in xml_text
    assert 'curve idref="unmanaged_prop_HW_CWHvm_HW_FDC_L_985501000001"' in xml_text


def test_build_forestmodel_xml_tree_does_not_mix_managed_and_unmanaged_species_props() -> (
    None
):
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {"curve_id": 985501000001, "curve_type": "unmanaged_species_prop_DR"},
            {"curve_id": 985501000002, "curve_type": "unmanaged_species_prop_HW"},
            {"curve_id": 985521000001, "curve_type": "managed_species_prop_CW"},
            {"curve_id": 985521000002, "curve_type": "managed_species_prop_DR"},
            {"curve_id": 985521000003, "curve_type": "managed_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 50.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
            {"curve_id": 985501000001, "x": 1, "y": 0.8},
            {"curve_id": 985501000002, "x": 1, "y": 0.2},
            {"curve_id": 985521000001, "x": 1, "y": 0.3},
            {"curve_id": 985521000002, "x": 1, "y": 0.0},
            {"curve_id": 985521000003, "x": 1, "y": 0.7},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )

    managed_select = None
    for select in root.findall(".//select"):
        if (
            select.get("statement")
            == "AU eq 985501000 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl'"
        ):
            managed_select = select
            break
    assert managed_select is not None
    managed_xml = et.tostring(managed_select, encoding="unicode")
    assert "feature.Yield.managed.CW" in managed_xml
    assert "feature.Yield.managed.HW" in managed_xml
    assert "feature.Yield.managed.DR" not in managed_xml
    assert "feature.SpeciesProp.managed.DR" not in managed_xml
    assert 'curve idref="unmanaged_prop_DR_985501000001"' not in managed_xml


def test_build_forestmodel_xml_tree_adds_ct_track_and_qmd_when_configured() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "managed_curve_id": 985522001,
                "unmanaged_curve_id": 985502001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "unmanaged"},
            {"curve_id": 985522001, "curve_type": "managed"},
            {"curve_id": 985522001001, "curve_type": "managed_species_prop_CW"},
            {"curve_id": 985522001002, "curve_type": "managed_species_prop_HW"},
            {"curve_id": 985502001001, "curve_type": "unmanaged_species_prop_CW"},
            {"curve_id": 985502001002, "curve_type": "unmanaged_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 1, "y": 8.0},
            {"curve_id": 985502001, "x": 40, "y": 200.0},
            {"curve_id": 985502001, "x": 100, "y": 320.0},
            {"curve_id": 985522001, "x": 1, "y": 10.0},
            {"curve_id": 985522001, "x": 40, "y": 260.0},
            {"curve_id": 985522001, "x": 100, "y": 400.0},
            {"curve_id": 985522001001, "x": 1, "y": 0.25},
            {"curve_id": 985522001002, "x": 1, "y": 0.75},
            {"curve_id": 985502001001, "x": 1, "y": 0.20},
            {"curve_id": 985502001002, "x": 1, "y": 0.80},
        ]
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "ct_age": 40,
            "age_by_au": {"985502001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
        },
        "fertilization": {
            "enabled": True,
            "response_years": 10,
            "growth_speedup_fraction": 0.10,
            "first_application": {
                "from_state": "cc_pl_ct",
                "to_state": "cc_pl_ct_f1",
                "timing_rule": "cai_argmax",
            },
            "second_application": {
                "enabled": True,
                "from_state": "cc_pl_ct_f1",
                "to_state": "cc_pl_ct_f1_f2",
                "years_after_previous": 10,
            },
            "third_application": {
                "enabled": True,
                "from_state": "cc_pl_ct_f1_f2",
                "to_state": "cc_pl_ct_f1_f2_f3",
                "years_after_previous": 10,
            },
        },
        "qmd": {
            "enabled": True,
            "harvested_product_accounts_enabled": True,
        },
        "stems_per_ha": {
            "enabled": True,
        },
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    managed_planted_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl'\"]"
    )
    assert managed_planted_select is not None
    treatment_labels = [
        node.attrib["label"]
        for node in managed_planted_select.findall("./track/treatment")
    ]
    assert treatment_labels == ["CC", "CT"]

    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.QMD.managed.CWHvm_FDC_HW_M" in xml_text
    assert "feature.QMD.unmanaged.CWHvm_FDC_HW_M" in xml_text
    assert "product.QMDNumerator.managed.CWHvm_FDC_HW_M.CC" in xml_text
    assert "product.QMDNumerator.managed.CWHvm_FDC_HW_M.CT" in xml_text
    assert "product.Treated.managed.CWHvm_FDC_HW_M.CC" in xml_text
    assert "product.Treated.managed.CWHvm_FDC_HW_M.CT" in xml_text
    assert "product.HarvestedVolume.managed.Total.CT" in xml_text
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl' and treatment eq 'CT'"
        in xml_text
    )
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct'"
        in xml_text
    )
    ct_state_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct'\"]"
    )
    assert ct_state_select is not None
    ct_treatment_labels = [
        node.attrib["label"] for node in ct_state_select.findall("./track/treatment")
    ]
    assert ct_treatment_labels == ["CC", "F1"]
    assert "product.Treated.managed.F1" in xml_text
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct' and treatment eq 'F1'"
        in xml_text
    )
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct_f1'"
        in xml_text
    )
    f1_state_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct_f1'\"]"
    )
    assert f1_state_select is not None
    f1_treatment_labels = [
        node.attrib["label"] for node in f1_state_select.findall("./track/treatment")
    ]
    assert f1_treatment_labels == ["CC", "F2"]
    assert "product.Treated.managed.F2" in xml_text
    assert "product.Treated.managed.F3" in xml_text
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct_f1_f2'"
        in xml_text
    )
    f2_state_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct_f1_f2'\"]"
    )
    assert f2_state_select is not None
    f2_treatment_labels = [
        node.attrib["label"] for node in f2_state_select.findall("./track/treatment")
    ]
    assert f2_treatment_labels == ["CC", "F3"]
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct_f1_f2_f3'"
        in xml_text
    )


def test_build_forestmodel_xml_tree_adds_pct_then_ct_variant_path() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "managed_curve_id": 985522001,
                "unmanaged_curve_id": 985502001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "unmanaged"},
            {"curve_id": 985522001, "curve_type": "managed"},
            {"curve_id": 985522001001, "curve_type": "managed_species_prop_FD"},
            {"curve_id": 985522001002, "curve_type": "managed_species_prop_HW"},
            {"curve_id": 985502001001, "curve_type": "unmanaged_species_prop_FD"},
            {"curve_id": 985502001002, "curve_type": "unmanaged_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 1, "y": 8.0},
            {"curve_id": 985502001, "x": 40, "y": 200.0},
            {"curve_id": 985502001, "x": 100, "y": 320.0},
            {"curve_id": 985522001, "x": 1, "y": 10.0},
            {"curve_id": 985522001, "x": 40, "y": 260.0},
            {"curve_id": 985522001, "x": 100, "y": 400.0},
            {"curve_id": 985522001001, "x": 1, "y": 0.225},
            {"curve_id": 985522001002, "x": 1, "y": 0.775},
            {"curve_id": 985502001001, "x": 1, "y": 0.20},
            {"curve_id": 985502001002, "x": 1, "y": 0.80},
        ]
    )
    silviculture_config = {
        "pre_commercial_thinning": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "from_state": "cc_pl",
            "to_state": "cc_pl_pct",
            "age_by_au": {"985502001": 10},
            "remove_species": ["HW"],
        },
        "commercial_thinning": {
            "enabled": False,
        },
        "qmd": {
            "enabled": True,
            "harvested_product_accounts_enabled": True,
        },
        "stems_per_ha": {
            "enabled": True,
        },
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    xml_text = et.tostring(root, encoding="unicode")
    base_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl'\"]"
    )
    assert base_select is not None
    assert [
        node.attrib["label"] for node in base_select.findall("./track/treatment")
    ] == ["CC", "PCT"]
    pct_node = base_select.find("./track/treatment[@label='PCT']")
    assert pct_node is not None
    assert pct_node.get("adjust") == "R"

    pct_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_pct'\"]"
    )
    assert pct_select is not None
    assert [
        node.attrib["label"] for node in pct_select.findall("./track/treatment")
    ] == ["CC"]
    assert "product.Treated.managed.PCT" in xml_text
    assert "product.QMDNumerator.managed.CWHvm_FDC_HW_M.PCT" in xml_text
    assert "product.QMDNumerator.managed.CWHvm_FDC_HW_M.CC" in xml_text
    assert (
        "AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl' and treatment eq 'PCT'"
        in xml_text
    )
    assert "product.Treated.managed.CT" not in xml_text
    assert "cc_pl_pct_ct" not in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_yield_HW" not in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_yield_FD" in xml_text
    assert "product.Treated.managed.F1" not in xml_text


def test_build_forestmodel_xml_tree_from_context_adds_stems_per_ha_features() -> None:
    context = _build_single_au_context(
        au_id=985502001,
        stratum_code="CWHvm_FDC+HW",
        si_level="M",
        unmanaged_points=(
            CurvePoint(x=1.0, y=8.0),
            CurvePoint(x=40.0, y=200.0),
            CurvePoint(x=100.0, y=320.0),
        ),
        managed_points=(
            CurvePoint(x=1.0, y=10.0),
            CurvePoint(x=40.0, y=260.0),
            CurvePoint(x=100.0, y=400.0),
        ),
        managed_species_curve_ids={"CW": 985522001001, "HW": 985522001002},
        unmanaged_species_curve_ids={"CW": 985502001001, "HW": 985502001002},
        curve_points_by_id={
            985522001001: (CurvePoint(x=1.0, y=0.25),),
            985522001002: (CurvePoint(x=1.0, y=0.75),),
            985502001001: (CurvePoint(x=1.0, y=0.20),),
            985502001002: (CurvePoint(x=1.0, y=0.80),),
        },
        qmd_support=QmdSupportDefinition(
            unmanaged_stems_per_ha=500.0,
            managed_tph_points=(
                CurvePoint(x=1.0, y=1200.0),
                CurvePoint(x=40.0, y=800.0),
                CurvePoint(x=100.0, y=500.0),
            ),
        ),
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "ct_age": 40,
            "age_by_au": {"985502001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
        },
        "stems_per_ha": {
            "enabled": True,
        },
    }

    root = build_forestmodel_xml_tree_from_context(
        context=context,
        silviculture_config=silviculture_config,
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.StemsPerHa.managed.CWHvm_FDC_HW_M" in xml_text
    assert "feature.StemsPerHa.unmanaged.CWHvm_FDC_HW_M" in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_stems_per_ha" in xml_text
    assert "au_CWHvm_FDC_HW_M_unmanaged_stems_per_ha" in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_ct_stems_per_ha" in xml_text


def test_build_forestmodel_xml_tree_from_context_adds_pct_stems_per_ha_features() -> None:
    context = _build_single_au_context(
        au_id=985502001,
        stratum_code="CWHvm_FDC+HW",
        si_level="M",
        unmanaged_points=(
            CurvePoint(x=1.0, y=8.0),
            CurvePoint(x=40.0, y=200.0),
            CurvePoint(x=100.0, y=320.0),
        ),
        managed_points=(
            CurvePoint(x=1.0, y=10.0),
            CurvePoint(x=10.0, y=120.0),
            CurvePoint(x=40.0, y=260.0),
            CurvePoint(x=100.0, y=400.0),
        ),
        managed_species_curve_ids={"FD": 985522001001, "HW": 985522001002},
        unmanaged_species_curve_ids={"FD": 985502001001, "HW": 985502001002},
        curve_points_by_id={
            985522001001: (CurvePoint(x=1.0, y=0.225),),
            985522001002: (CurvePoint(x=1.0, y=0.775),),
            985502001001: (CurvePoint(x=1.0, y=0.20),),
            985502001002: (CurvePoint(x=1.0, y=0.80),),
        },
        qmd_support=QmdSupportDefinition(
            unmanaged_stems_per_ha=500.0,
            managed_tph_points=(
                CurvePoint(x=1.0, y=4000.0),
                CurvePoint(x=10.0, y=4000.0),
                CurvePoint(x=40.0, y=2200.0),
                CurvePoint(x=100.0, y=800.0),
            ),
        ),
    )
    silviculture_config = {
        "pre_commercial_thinning": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "from_state": "cc_pl",
            "to_state": "cc_pl_pct",
            "age_by_au": {"985502001": 10},
            "source_total_stems_per_ha": 4000,
            "remove_species": ["HW"],
            "remove_stems_per_ha": {"HW": 1000},
        },
        "commercial_thinning": {
            "enabled": False,
        },
        "stems_per_ha": {
            "enabled": True,
        },
    }

    root = build_forestmodel_xml_tree_from_context(
        context=context,
        silviculture_config=silviculture_config,
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.StemsPerHa.managed.CWHvm_FDC_HW_M" in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_stems_per_ha" in xml_text


def test_build_forestmodel_xml_tree_supports_per_au_fert_response_overrides() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985501001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "L",
                "managed_curve_id": 985521001,
                "unmanaged_curve_id": 985501001,
            },
            {
                "au_id": 985503001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "H",
                "managed_curve_id": 985523001,
                "unmanaged_curve_id": 985503001,
            },
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501001, "curve_type": "unmanaged"},
            {"curve_id": 985521001, "curve_type": "managed"},
            {"curve_id": 985503001, "curve_type": "unmanaged"},
            {"curve_id": 985523001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501001, "x": 1, "y": 5.0},
            {"curve_id": 985501001, "x": 40, "y": 200.0},
            {"curve_id": 985501001, "x": 50, "y": 280.0},
            {"curve_id": 985501001, "x": 60, "y": 360.0},
            {"curve_id": 985501001, "x": 70, "y": 430.0},
            {"curve_id": 985521001, "x": 1, "y": 8.0},
            {"curve_id": 985521001, "x": 40, "y": 240.0},
            {"curve_id": 985521001, "x": 50, "y": 340.0},
            {"curve_id": 985521001, "x": 60, "y": 450.0},
            {"curve_id": 985521001, "x": 70, "y": 560.0},
            {"curve_id": 985503001, "x": 1, "y": 5.0},
            {"curve_id": 985503001, "x": 40, "y": 200.0},
            {"curve_id": 985503001, "x": 50, "y": 280.0},
            {"curve_id": 985503001, "x": 60, "y": 360.0},
            {"curve_id": 985503001, "x": 70, "y": 430.0},
            {"curve_id": 985523001, "x": 1, "y": 8.0},
            {"curve_id": 985523001, "x": 40, "y": 240.0},
            {"curve_id": 985523001, "x": 50, "y": 340.0},
            {"curve_id": 985523001, "x": 60, "y": 450.0},
            {"curve_id": 985523001, "x": 70, "y": 560.0},
        ]
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "eligible_au_ids": [985501001, 985503001],
            "age_by_au": {"985501001": 40, "985503001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
        },
        "fertilization": {
            "enabled": True,
            "eligible_au_ids": [985501001, 985503001],
            "response_years": 10,
            "growth_speedup_fraction_by_au": {
                "985501001": 0.15,
                "985503001": 0.05,
            },
            "first_application": {
                "from_state": "cc_pl_ct",
                "to_state": "cc_pl_ct_f1",
                "age_by_au": {"985501001": 50, "985503001": 50},
            },
            "second_application": {"enabled": False},
            "third_application": {"enabled": False},
        },
        "qmd": {"enabled": True},
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    low_curve = root.find("./curve[@id='au_CWHvm_FDC_HW_L_fert1_total']")
    high_curve = root.find("./curve[@id='au_CWHvm_FDC_HW_H_fert1_total']")
    assert low_curve is not None
    assert high_curve is not None

    low_points = {
        point.attrib["x"]: point.attrib["y"] for point in low_curve.findall("./point")
    }
    high_points = {
        point.attrib["x"]: point.attrib["y"] for point in high_curve.findall("./point")
    }
    assert float(low_points["60"]) > float(high_points["60"])
    assert float(low_points["70"]) == float(high_points["70"])


def test_build_curve_with_post_thinning_gap_ramps_to_target_factor() -> None:
    points = _build_curve_with_post_thinning_gap(
        source_curve_points=(
            CurvePoint(x=30.0, y=300.0),
            CurvePoint(x=40.0, y=400.0),
            CurvePoint(x=50.0, y=500.0),
            CurvePoint(x=60.0, y=600.0),
        ),
        transition_age=40,
        gap_at_transition_value=100.0,
        final_gap_factor=0.0,
        ramp_end_age=60,
    )
    point_map = {int(point.x): point.y for point in points}
    assert point_map[30] == 300.0
    assert point_map[40] == 300.0
    assert point_map[50] == 450.0
    assert point_map[60] == 600.0


def test_build_forestmodel_xml_tree_supports_ct_final_felling_gap_factor() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "managed_curve_id": 985522001,
                "unmanaged_curve_id": 985502001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "unmanaged"},
            {"curve_id": 985522001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 1, "y": 5.0},
            {"curve_id": 985502001, "x": 40, "y": 200.0},
            {"curve_id": 985502001, "x": 50, "y": 320.0},
            {"curve_id": 985502001, "x": 60, "y": 420.0},
            {"curve_id": 985502001, "x": 70, "y": 470.0},
            {"curve_id": 985522001, "x": 1, "y": 8.0},
            {"curve_id": 985522001, "x": 40, "y": 240.0},
            {"curve_id": 985522001, "x": 50, "y": 400.0},
            {"curve_id": 985522001, "x": 60, "y": 480.0},
            {"curve_id": 985522001, "x": 70, "y": 490.0},
        ]
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "eligible_au_ids": [985502001],
            "age_by_au": {"985502001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
            "final_felling_gap_factor": 0.0,
        }
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    residual_curve = root.find(
        "./curve[@id='au_CWHvm_FDC_HW_M_cc_pl_ct_residual_total']"
    )
    assert residual_curve is not None
    point_map = {
        int(float(point.attrib["x"])): float(point.attrib["y"])
        for point in residual_curve.findall("./point")
    }
    assert point_map[40] == 168.0
    assert point_map[50] == 400.0
    assert point_map[60] == 480.0


def test_build_forestmodel_xml_tree_marks_ct_and_fert_treatments_as_age_retaining() -> (
    None
):
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "managed_curve_id": 985522001,
                "unmanaged_curve_id": 985502001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "unmanaged"},
            {"curve_id": 985522001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 1, "y": 5.0},
            {"curve_id": 985502001, "x": 40, "y": 200.0},
            {"curve_id": 985502001, "x": 50, "y": 280.0},
            {"curve_id": 985502001, "x": 60, "y": 360.0},
            {"curve_id": 985502001, "x": 70, "y": 430.0},
            {"curve_id": 985522001, "x": 1, "y": 8.0},
            {"curve_id": 985522001, "x": 40, "y": 240.0},
            {"curve_id": 985522001, "x": 50, "y": 340.0},
            {"curve_id": 985522001, "x": 60, "y": 450.0},
            {"curve_id": 985522001, "x": 70, "y": 560.0},
        ]
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "eligible_au_ids": [985502001],
            "age_by_au": {"985502001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
        },
        "fertilization": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "response_years": 10,
            "growth_speedup_fraction": 0.10,
            "first_application": {
                "from_state": "cc_pl_ct",
                "to_state": "cc_pl_ct_f1",
                "age_by_au": {"985502001": 50},
            },
            "second_application": {
                "enabled": True,
                "from_state": "cc_pl_ct_f1",
                "to_state": "cc_pl_ct_f1_f2",
                "years_after_previous": 10,
            },
            "third_application": {
                "enabled": True,
                "from_state": "cc_pl_ct_f1_f2",
                "to_state": "cc_pl_ct_f1_f2_f3",
                "years_after_previous": 10,
            },
        },
        "qmd": {"enabled": True},
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    ct_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq "
        "'planted' and SILV_STATE eq 'cc_pl'\"]"
    )
    assert ct_select is not None
    ct_node = ct_select.find("./track/treatment[@label='CT']")
    assert ct_node is not None
    assert ct_node.get("adjust") == "R"

    fert1_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq "
        "'planted' and SILV_STATE eq 'cc_pl_ct'\"]"
    )
    assert fert1_select is not None
    fert1_node = fert1_select.find("./track/treatment[@label='F1']")
    assert fert1_node is not None
    assert fert1_node.get("adjust") == "R"

    fert2_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq "
        "'planted' and SILV_STATE eq 'cc_pl_ct_f1'\"]"
    )
    assert fert2_select is not None
    fert2_node = fert2_select.find("./track/treatment[@label='F2']")
    assert fert2_node is not None
    assert fert2_node.get("adjust") == "R"

    fert3_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq "
        "'planted' and SILV_STATE eq 'cc_pl_ct_f1_f2'\"]"
    )
    assert fert3_select is not None
    fert3_node = fert3_select.find("./track/treatment[@label='F3']")
    assert fert3_node is not None
    assert fert3_node.get("adjust") == "R"


def test_build_forestmodel_xml_tree_skips_fert_chain_when_au_not_fert_eligible() -> (
    None
):
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985503001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "H",
                "managed_curve_id": 985523001,
                "unmanaged_curve_id": 985503001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985503001, "curve_type": "unmanaged"},
            {"curve_id": 985523001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985503001, "x": 1, "y": 5.0},
            {"curve_id": 985503001, "x": 40, "y": 200.0},
            {"curve_id": 985503001, "x": 50, "y": 280.0},
            {"curve_id": 985503001, "x": 60, "y": 360.0},
            {"curve_id": 985523001, "x": 1, "y": 8.0},
            {"curve_id": 985523001, "x": 40, "y": 240.0},
            {"curve_id": 985523001, "x": 50, "y": 340.0},
            {"curve_id": 985523001, "x": 60, "y": 450.0},
        ]
    )
    silviculture_config = {
        "commercial_thinning": {
            "enabled": True,
            "from_state": "cc_pl",
            "to_state": "cc_pl_ct",
            "eligible_au_ids": [985503001],
            "age_by_au": {"985503001": 40},
            "basal_area_removal_fraction": 0.30,
            "basal_area_to_volume_ratio": 1.0,
        },
        "fertilization": {
            "enabled": True,
            "eligible_au_ids": [985501001, 985502001],
            "response_years": 10,
            "growth_speedup_fraction": 0.10,
            "first_application": {
                "from_state": "cc_pl_ct",
                "to_state": "cc_pl_ct_f1",
                "age_by_au": {"985503001": 50},
            },
            "second_application": {"enabled": True},
            "third_application": {"enabled": True},
        },
        "qmd": {"enabled": True},
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )
    ct_state_select = root.find(
        "./select[@statement=\"AU eq 985503001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl_ct'\"]"
    )
    assert ct_state_select is not None
    ct_treatment_labels = [
        node.attrib["label"] for node in ct_state_select.findall("./track/treatment")
    ]
    assert ct_treatment_labels == ["CC"]

    xml_text = et.tostring(root, encoding="unicode")
    assert "product.Treated.managed.F1" not in xml_text
    assert "cc_pl_ct_f1" not in xml_text


def test_build_forestmodel_xml_tree_supports_multiple_pct_treatments() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 985502001,
                "tsa": "k3z",
                "stratum_code": "CWHvm_FDC+HW",
                "si_level": "M",
                "managed_curve_id": 985522001,
                "unmanaged_curve_id": 985502001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985502001, "curve_type": "unmanaged"},
            {"curve_id": 985522001, "curve_type": "managed"},
            {"curve_id": 985522001001, "curve_type": "managed_species_prop_FD"},
            {"curve_id": 985522001002, "curve_type": "managed_species_prop_HW"},
            {"curve_id": 985502001001, "curve_type": "unmanaged_species_prop_FD"},
            {"curve_id": 985502001002, "curve_type": "unmanaged_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985502001, "x": 1, "y": 8.0},
            {"curve_id": 985502001, "x": 40, "y": 200.0},
            {"curve_id": 985502001, "x": 100, "y": 320.0},
            {"curve_id": 985522001, "x": 1, "y": 10.0},
            {"curve_id": 985522001, "x": 40, "y": 260.0},
            {"curve_id": 985522001, "x": 100, "y": 400.0},
            {"curve_id": 985522001001, "x": 1, "y": 0.20},
            {"curve_id": 985522001002, "x": 1, "y": 0.80},
            {"curve_id": 985502001001, "x": 1, "y": 0.20},
            {"curve_id": 985502001002, "x": 1, "y": 0.80},
        ]
    )
    silviculture_config = {
        "pre_commercial_thinning": {
            "enabled": True,
            "eligible_au_ids": [985502001],
            "source_total_stems_per_ha": 4000,
            "treatments": [
                {
                    "label": "PCT_LIGHT",
                    "from_state": "cc_pl",
                    "to_state": "cc_pl_pct_light",
                    "ct_to_state": "cc_pl_pct_light_ct",
                    "age_by_au": {"985502001": 10},
                    "remove_species": ["HW"],
                    "remove_stems_per_ha": {"HW": 1000},
                },
                {
                    "label": "PCT_MODERATE",
                    "from_state": "cc_pl",
                    "to_state": "cc_pl_pct_moderate",
                    "ct_to_state": "cc_pl_pct_moderate_ct",
                    "age_by_au": {"985502001": 10},
                    "remove_species": ["HW"],
                    "remove_stems_per_ha": {"HW": 2000},
                },
                {
                    "label": "PCT_HEAVY",
                    "from_state": "cc_pl",
                    "to_state": "cc_pl_pct_heavy",
                    "ct_to_state": "cc_pl_pct_heavy_ct",
                    "age_by_au": {"985502001": 10},
                    "remove_species": ["HW"],
                    "remove_stems_per_ha": {"HW": 3000},
                },
            ],
        },
    }

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        silviculture_config=silviculture_config,
    )

    xml_text = et.tostring(root, encoding="unicode")
    base_select = root.find(
        "./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq 'cc_pl'\"]"
    )
    assert base_select is not None
    assert [
        node.attrib["label"] for node in base_select.findall("./track/treatment")
    ] == ["CC", "PCT_LIGHT", "PCT_MODERATE", "PCT_HEAVY"]

    for state in ("cc_pl_pct_light", "cc_pl_pct_moderate", "cc_pl_pct_heavy"):
        pct_select = root.find(
            f"./select[@statement=\"AU eq 985502001 and IFM eq 'managed' and ORIGIN eq 'planted' and SILV_STATE eq '{state}'\"]"
        )
        assert pct_select is not None
        assert [
            node.attrib["label"] for node in pct_select.findall("./track/treatment")
        ] == ["CC"]

    assert "product.Treated.managed.PCT_LIGHT" in xml_text
    assert "product.Treated.managed.PCT_MODERATE" in xml_text
    assert "product.Treated.managed.PCT_HEAVY" in xml_text
    assert "treatment eq 'PCT_LIGHT'" in xml_text
    assert "treatment eq 'PCT_MODERATE'" in xml_text
    assert "treatment eq 'PCT_HEAVY'" in xml_text
    assert "product.Treated.managed.CT" not in xml_text
    assert "cc_pl_pct_light_ct" not in xml_text
    assert "cc_pl_pct_moderate_ct" not in xml_text
    assert "cc_pl_pct_heavy_ct" not in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_light_yield_HW" in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_moderate_yield_HW" in xml_text
    assert "au_CWHvm_FDC_HW_M_managed_cc_pl_pct_heavy_yield_HW" in xml_text


def test_build_forestmodel_xml_tree_omits_zero_signal_species_accounts() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
            {"curve_id": 985501000001, "curve_type": "unmanaged_species_prop_PL"},
            {"curve_id": 985521000001, "curve_type": "managed_species_prop_PL"},
            {"curve_id": 985501000002, "curve_type": "unmanaged_species_prop_PLC"},
            {"curve_id": 985521000002, "curve_type": "managed_species_prop_PLC"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 50.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
            {"curve_id": 985501000001, "x": 1, "y": 0.0},
            {"curve_id": 985501000001, "x": 10, "y": 0.0},
            {"curve_id": 985521000001, "x": 1, "y": 0.0},
            {"curve_id": 985521000001, "x": 10, "y": 0.0},
            {"curve_id": 985501000002, "x": 1, "y": 0.2},
            {"curve_id": 985501000002, "x": 10, "y": 0.2},
            {"curve_id": 985521000002, "x": 1, "y": 0.3},
            {"curve_id": 985521000002, "x": 10, "y": 0.3},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    labels = {
        attr.attrib["label"]
        for attr in root.findall(".//attribute")
        if "label" in attr.attrib
    }

    assert "product.Yield.managed.PLC" in labels
    assert "product.HarvestedVolume.managed.PLC.CC" in labels
    assert "feature.SpeciesProp.managed.PLC" in labels
    assert "product.SpeciesProp.managed.PLC" in labels

    assert "product.Yield.managed.PL" not in labels
    assert "product.HarvestedVolume.managed.PL.CC" not in labels
    assert "feature.SpeciesProp.managed.PL" not in labels
    assert "product.SpeciesProp.managed.PL" not in labels


def test_build_forestmodel_xml_tree_sets_cc_min_age_from_cmai_minus_20() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 0.0},
            {"curve_id": 985521000, "x": 1, "y": 1.0},
            {"curve_id": 985521000, "x": 20, "y": 100.0},
            {"curve_id": 985521000, "x": 40, "y": 300.0},
            {"curve_id": 985521000, "x": 60, "y": 600.0},
            {"curve_id": 985521000, "x": 80, "y": 700.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    treatment = root.find(".//treatment[@label='CC']")
    assert treatment is not None
    assert treatment.get("minage") == "40"


def test_build_forestmodel_xml_tree_cc_min_age_ignores_higher_cli_floor() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 0.0},
            {"curve_id": 985521000, "x": 1, "y": 1.0},
            {"curve_id": 985521000, "x": 20, "y": 100.0},
            {"curve_id": 985521000, "x": 40, "y": 300.0},
            {"curve_id": 985521000, "x": 60, "y": 600.0},
            {"curve_id": 985521000, "x": 80, "y": 700.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        cc_min_age=80,
    )
    treatment = root.find(".//treatment[@label='CC']")
    assert treatment is not None
    assert treatment.get("minage") == "40"


def test_build_forestmodel_xml_tree_adds_seral_curves_and_attributes() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 0.0},
            {"curve_id": 985521000, "x": 1, "y": 1.0},
            {"curve_id": 985521000, "x": 20, "y": 100.0},
            {"curve_id": 985521000, "x": 40, "y": 300.0},
            {"curve_id": 985521000, "x": 60, "y": 600.0},
            {"curve_id": 985521000, "x": 80, "y": 700.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        seral_stage_config={},
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.Seral.regenerating" in xml_text
    assert "feature.Seral.young" in xml_text
    assert "feature.Seral.immature" in xml_text
    assert "feature.Seral.mature" in xml_text
    assert "feature.Seral.overmature" in xml_text
    assert "feature.Seral.CWHvm_HW_FDC_L.regenerating" in xml_text
    assert "feature.Seral.CWHvm_HW_FDC_L.mature" in xml_text
    assert "product.Seral.regenerating" not in xml_text
    assert "product.Seral.area.regenerating.CWHvm_HW_FDC_L.CC" in xml_text

    mature_curve = root.find("./curve[@id='au_CWHvm_HW_FDC_L_seral_mature']")
    assert mature_curve is not None
    mature_points = [point.attrib for point in mature_curve.findall("./point")]
    assert {"x": "60", "y": "0.0"} in mature_points
    assert {"x": "61", "y": "1.0"} in mature_points
    assert {"x": "80", "y": "1.0"} in mature_points
    assert {"x": "81", "y": "0.0"} in mature_points


def test_build_forestmodel_xml_tree_respects_per_au_seral_overrides() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 0.0},
            {"curve_id": 985521000, "x": 1, "y": 1.0},
            {"curve_id": 985521000, "x": 20, "y": 100.0},
            {"curve_id": 985521000, "x": 40, "y": 300.0},
            {"curve_id": 985521000, "x": 60, "y": 600.0},
            {"curve_id": 985521000, "x": 80, "y": 700.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        seral_stage_config={
            "au_overrides": {
                "985501000": {
                    "mature": {"max_age": 70},
                    "overmature": {"min_age": 71},
                }
            }
        },
    )
    mature_curve = root.find("./curve[@id='au_CWHvm_HW_FDC_L_seral_mature']")
    assert mature_curve is not None
    mature_points = [point.attrib for point in mature_curve.findall("./point")]
    assert {"x": "70", "y": "1.0"} in mature_points
    assert {"x": "71", "y": "0.0"} in mature_points


def test_build_forestmodel_xml_tree_clamps_invalid_seral_stage_bounds() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    # Early culmination age so cmai resolves below configured immature min_age.
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 0.0},
            {"curve_id": 985521000, "x": 1, "y": 20.0},
            {"curve_id": 985521000, "x": 5, "y": 30.0},
            {"curve_id": 985521000, "x": 10, "y": 35.0},
            {"curve_id": 985521000, "x": 40, "y": 100.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        seral_stage_config={
            "default": {
                "regenerating": {"min_age": 0, "max_age": 5},
                "young": {"min_age": 6, "max_age": 25},
                "immature": {"min_age": 26, "max_age": "cmai"},
                "mature": {"min_age": "cmai_plus_1", "max_age": "min_peak_or_200"},
                "overmature": {"min_age": "mature_plus_1", "max_age": None},
            }
        },
    )
    xml_text = et.tostring(root, encoding="unicode")
    assert "feature.Seral.immature" in xml_text
    assert "feature.Seral.CWHvm_HW_FDC_L.immature" in xml_text

    immature_curve = root.find("./curve[@id='au_CWHvm_HW_FDC_L_seral_immature']")
    assert immature_curve is not None
    points = [point.attrib for point in immature_curve.findall("./point")]
    assert {"x": "26", "y": "1.0"} in points
    assert {"x": "27", "y": "0.0"} in points


def test_forestmodel_xml_trims_repeated_curve_values_on_both_tails() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "managed_curve_id": 21001,
                "unmanaged_curve_id": 1001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "unmanaged"},
            {"curve_id": 21001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 5.0},
            {"curve_id": 1001, "x": 2, "y": 5.0},
            {"curve_id": 1001, "x": 10, "y": 40.0},
            {"curve_id": 1001, "x": 20, "y": 40.0},
            {"curve_id": 1001, "x": 30, "y": 40.0},
            {"curve_id": 21001, "x": 1, "y": 7.0},
            {"curve_id": 21001, "x": 5, "y": 7.0},
            {"curve_id": 21001, "x": 10, "y": 50.0},
            {"curve_id": 21001, "x": 20, "y": 60.0},
            {"curve_id": 21001, "x": 30, "y": 60.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    unmanaged_points = root.findall(
        "./curve[@id='unmanaged_total_SBPS_PLI_L_1001']/point"
    )
    managed_points = root.findall("./curve[@id='managed_total_SBPS_PLI_L_21001']/point")
    assert [p.attrib for p in unmanaged_points] == [
        {"x": "1", "y": "5.0"},
        {"x": "10", "y": "40.0"},
    ]
    assert [p.attrib for p in managed_points] == [
        {"x": "5", "y": "7.0"},
        {"x": "10", "y": "50.0"},
        {"x": "20", "y": "60.0"},
    ]


def test_forestmodel_xml_all_flat_curve_keeps_earliest_point() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "managed_curve_id": 21001,
                "unmanaged_curve_id": 1001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "unmanaged"},
            {"curve_id": 21001, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 0.0},
            {"curve_id": 1001, "x": 100, "y": 0.0},
            {"curve_id": 1001, "x": 299, "y": 0.0},
            {"curve_id": 21001, "x": 1, "y": 0.0},
            {"curve_id": 21001, "x": 100, "y": 0.0},
            {"curve_id": 21001, "x": 299, "y": 0.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    unmanaged_points = root.findall(
        "./curve[@id='unmanaged_total_SBPS_PLI_L_1001']/point"
    )
    managed_points = root.findall("./curve[@id='managed_total_SBPS_PLI_L_21001']/point")
    assert [p.attrib for p in unmanaged_points] == [{"x": "1", "y": "0.0"}]
    assert [p.attrib for p in managed_points] == [{"x": "1", "y": "0.0"}]


def test_forestmodel_xml_sanitizes_nan_point_values() -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "managed_curve_id": 21001,
                "unmanaged_curve_id": 1001,
            }
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "unmanaged"},
            {"curve_id": 21001, "curve_type": "managed"},
            {"curve_id": 21001001, "curve_type": "managed_species_prop_HW"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 10.0},
            {"curve_id": 21001, "x": 1, "y": 20.0},
            {"curve_id": 21001001, "x": 1, "y": float("nan")},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    species_prop = root.find("./curve[@id='managed_prop_HW_SBPS_PLI_L_21001001']/point")
    assert species_prop is not None
    assert species_prop.attrib == {"x": "1", "y": "0"}


def test_export_patchworks_package_writes_xml_and_fragments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    checkpoint_path = tmp_path / "checkpoint7.feather"
    output_dir = tmp_path / "patchworks_export"

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

    result = export_patchworks_package(
        bundle_dir=bundle_dir,
        checkpoint_path=checkpoint_path,
        output_dir=output_dir,
        tsa_list=["k3z"],
    )

    assert result.forestmodel_xml_path.is_file()
    assert result.fragments_shapefile_path.is_file()
    xml_text = result.forestmodel_xml_path.read_text(encoding="utf-8")
    assert '<?xml-model href="https://www.spatial.ca/ForestModel.xsd"?>' in xml_text
    assert "feature.Yield.unmanaged.Total" in xml_text
    gdf = gpd.read_file(result.fragments_shapefile_path)
    assert set(
        [
            "FRAGMENT_I",
            "BLOCK",
            "AREA_HA",
            "F_AGE",
            "AU",
            "IFM",
            "ORIGIN",
            "SILV_STATE",
            "RETENTION",
        ]
    ).issubset(gdf.columns)
    assert int(gdf.loc[0, "AU"]) == 985501000
    assert gdf.loc[0, "IFM"] == "managed"
    assert gdf.loc[0, "ORIGIN"] == "natural"
    assert gdf.loc[0, "SILV_STATE"] == "baseline"
    assert float(gdf.loc[0, "RETENTION"]) == pytest.approx(0.0)


def test_export_patchworks_package_decodes_wkb_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_bundle_tables(bundle_dir)
    checkpoint_path = tmp_path / "checkpoint7.feather"
    output_dir = tmp_path / "patchworks_export"

    geom = Polygon([(0, 0), (40, 0), (40, 40), (0, 40), (0, 0)])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 61,
                "thlb_raw": 0,
                "geometry": geom.wkb,
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    result = export_patchworks_package(
        bundle_dir=bundle_dir,
        checkpoint_path=checkpoint_path,
        output_dir=output_dir,
        tsa_list=["k3z"],
    )

    gdf = gpd.read_file(result.fragments_shapefile_path)
    assert gdf.shape[0] == 1
    assert gdf.loc[0, "IFM"] == "unmanaged"
    assert gdf.loc[0, "ORIGIN"] == "natural"
    assert gdf.loc[0, "SILV_STATE"] == "baseline"
    assert float(gdf.loc[0, "RETENTION"]) == pytest.approx(0.0)
    assert gdf.geometry.iloc[0].geom_type == "Polygon"


def test_validate_forestmodel_xml_tree_rejects_missing_curve_ref() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    managed_curve_node = root.find(
        "./curve[@id='managed_total_CWHvm_HW_FDC_L_985521000']"
    )
    assert managed_curve_node is not None
    root.remove(managed_curve_node)

    with pytest.raises(ValueError, match="idref"):
        validate_forestmodel_xml_tree(root=root)


def test_validate_fragments_geodataframe_rejects_invalid_ifm() -> None:
    gdf = gpd.GeoDataFrame(
        {
            "BLOCK": [1],
            "AREA_HA": [1.0],
            "F_AGE": [10],
            "AU": [100],
            "FRAGMENT_ID": [1],
            "IFM": ["bogus"],
            "ORIGIN": ["natural"],
            "SILV_STATE": ["baseline"],
            "RETENTION": [0.0],
            "TSA": ["k3z"],
            "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])],
        },
        geometry="geometry",
        crs="EPSG:3005",
    )

    with pytest.raises(ValueError, match="IFM contains invalid values"):
        validate_fragments_geodataframe(fragments_gdf=gdf)


def test_validate_fragments_geodataframe_rejects_invalid_silv_state() -> None:
    gdf = gpd.GeoDataFrame(
        {
            "FRAGMENT_ID": [1],
            "BLOCK": [1],
            "AREA_HA": [1.0],
            "F_AGE": [10],
            "AU": [100],
            "IFM": ["managed"],
            "ORIGIN": ["natural"],
            "SILV_STATE": ["sideways"],
            "RETENTION": [0.0],
            "TSA": ["k3z"],
            "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])],
        },
        geometry="geometry",
        crs="EPSG:3005",
    )

    with pytest.raises(ValueError, match="SILV_STATE contains invalid values"):
        validate_fragments_geodataframe(fragments_gdf=gdf)


def test_validate_fragments_geodataframe_rejects_out_of_range_retention() -> None:
    gdf = gpd.GeoDataFrame(
        {
            "FRAGMENT_ID": [1],
            "BLOCK": [1],
            "AREA_HA": [1.0],
            "F_AGE": [10],
            "AU": [100],
            "IFM": ["managed"],
            "ORIGIN": ["natural"],
            "SILV_STATE": ["baseline"],
            "RETENTION": [1.2],
            "TSA": ["k3z"],
            "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])],
        },
        geometry="geometry",
        crs="EPSG:3005",
    )

    with pytest.raises(ValueError, match="RETENTION must be between 0.0 and 1.0"):
        validate_fragments_geodataframe(fragments_gdf=gdf)


def test_validate_forestmodel_xml_tree_rejects_retention_without_define() -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )

    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    retention_define = root.find('./define[@field="RETENTION"]')
    silv_define = root.find('./define[@field="SILV_STATE"]')
    assert silv_define is not None
    assert retention_define is not None
    root.remove(retention_define)

    with pytest.raises(ValueError, match="RETENTION"):
        validate_forestmodel_xml_tree(root=root)


def test_build_fragments_geodataframe_emits_one_row_per_stand_fragment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 80,
                "FEATURE_AREA_SQM": 100000.0,  # 10 ha
                "thlb_area": 4.0,  # any positive THLB signal => managed fragment
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
    )

    assert gdf.shape[0] == 1
    assert gdf["FRAGMENT_ID"].nunique() == 1
    assert gdf["BLOCK"].nunique() == 1
    assert gdf.loc[0, "IFM"] == "managed"
    assert gdf.loc[0, "ORIGIN"] == "natural"
    assert gdf.loc[0, "SILV_STATE"] == "baseline"
    assert float(gdf.loc[0, "RETENTION"]) == pytest.approx(0.0)
    assert float(gdf.loc[0, "AREA_HA"]) == pytest.approx(10.0)

    validate_fragments_geodataframe(fragments_gdf=gdf)


def test_build_fragments_geodataframe_marks_age_60_as_planted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 60,
                "FEATURE_AREA_SQM": 100000.0,
                "thlb_raw": 1.0,
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
    )

    assert gdf.loc[0, "ORIGIN"] == "planted"
    assert gdf.loc[0, "SILV_STATE"] == "cc_pl"
    assert float(gdf.loc[0, "RETENTION"]) == pytest.approx(0.0)


def test_build_fragments_geodataframe_interprets_thlb_raw_as_binary_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 80,
                "FEATURE_AREA_SQM": 100000.0,  # 10 ha
                "thlb_raw": 0.0,  # no THLB signal => unmanaged fragment
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
    )

    assert gdf.shape[0] == 1
    assert gdf.loc[0, "IFM"] == "unmanaged"
    assert gdf.loc[0, "ORIGIN"] == "natural"
    assert gdf.loc[0, "SILV_STATE"] == "baseline"
    assert float(gdf.loc[0, "RETENTION"]) == pytest.approx(0.0)
    assert float(gdf.loc[0, "AREA_HA"]) == pytest.approx(10.0)


def test_build_fragments_geodataframe_allows_ifm_threshold_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 70,
                "FEATURE_AREA_SQM": 10000.0,
                "thlb_raw": 0.15,
                "geometry": Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
            },
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 70,
                "FEATURE_AREA_SQM": 10000.0,
                "thlb_raw": 0.85,
                "geometry": Polygon([(20, 0), (30, 0), (30, 10), (20, 10), (20, 0)]),
            },
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
        ifm_source_col="thlb_raw",
        ifm_threshold=0.2,
    )

    assert gdf.shape[0] == 2
    assert sorted(gdf["IFM"].tolist()) == ["managed", "unmanaged"]


def test_build_fragments_geodataframe_allows_ifm_target_managed_share(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 70,
                "FEATURE_AREA_SQM": 10000.0,
                "thlb_raw": value,
                "geometry": Polygon(
                    [
                        (idx * 20, 0),
                        (idx * 20 + 10, 0),
                        (idx * 20 + 10, 10),
                        (idx * 20, 10),
                        (idx * 20, 0),
                    ]
                ),
            }
            for idx, value in enumerate([0.1, 0.2, 0.3, 0.4, 0.5])
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
        ifm_source_col="thlb_raw",
        ifm_target_managed_share=0.8,
    )

    assert gdf.shape[0] == 5
    assert (gdf["IFM"] == "managed").sum() == 4
    assert (gdf["IFM"] == "unmanaged").sum() == 1


def test_build_fragments_geodataframe_applies_full_retention_by_stratum_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame(
        [
            {"au_id": 985501006, "stratum_code": "CWHvm_CW+YC"},
            {"au_id": 985501000, "stratum_code": "CWHvm_HW+FDC"},
        ]
    )
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501006,
                "PROJ_AGE_1": 80,
                "FEATURE_AREA_SQM": 100000.0,
                "thlb_area": 4.0,
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            },
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 80,
                "FEATURE_AREA_SQM": 100000.0,
                "thlb_area": 4.0,
                "geometry": Polygon(
                    [(200, 0), (300, 0), (300, 100), (200, 100), (200, 0)]
                ),
            },
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    gdf = build_fragments_geodataframe(
        checkpoint_path=checkpoint_path,
        au_table=au_table,
        tsa_list=["k3z"],
        silviculture_config={
            "retention": {"full_retention_stratum_codes": ["CWHvm_CW+YC"]}
        },
    )

    retained = gdf.loc[gdf["AU"] == 985501006, "RETENTION"].iloc[0]
    baseline = gdf.loc[gdf["AU"] == 985501000, "RETENTION"].iloc[0]
    assert float(retained) == pytest.approx(1.0)
    assert float(baseline) == pytest.approx(0.0)


def test_build_fragments_geodataframe_rejects_conflicting_ifm_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint_path = tmp_path / "checkpoint7.feather"
    au_table = pd.DataFrame([{"au_id": 985501000}])
    checkpoint_df = pd.DataFrame(
        [
            {
                "tsa_code": "k3z",
                "au": 985501000,
                "PROJ_AGE_1": 80,
                "FEATURE_AREA_SQM": 100000.0,
                "thlb_raw": 0.8,
                "geometry": Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]),
            }
        ]
    )
    monkeypatch.setattr(
        "femic.fmg.patchworks.pd.read_feather", lambda _path: checkpoint_df
    )

    with pytest.raises(ValueError, match="mutually exclusive"):
        build_fragments_geodataframe(
            checkpoint_path=checkpoint_path,
            au_table=au_table,
            tsa_list=["k3z"],
            ifm_source_col="thlb_raw",
            ifm_threshold=0.2,
            ifm_target_managed_share=0.8,
        )


def test_write_forestmodel_xml_matches_fixture(tmp_path: Path) -> None:
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985501000, "x": 10, "y": 55.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
            {"curve_id": 985521000, "x": 10, "y": 70.0},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    out_path = tmp_path / "forestmodel.xml"
    write_forestmodel_xml(root=root, path=out_path)

    expected = Path("tests/fixtures/fmg/forestmodel_minimal.xml").read_text(
        encoding="utf-8"
    )
    actual = out_path.read_text(encoding="utf-8")
    assert actual == expected


def test_write_forestmodel_xml_matches_multi_au_fixture(tmp_path: Path) -> None:
    au_table = pd.DataFrame(
        [
            {
                "au_id": 1001,
                "tsa": "29",
                "stratum_code": "SBPS_PLI",
                "si_level": "L",
                "managed_curve_id": 21001,
                "unmanaged_curve_id": 1001,
            },
            {
                "au_id": 1002,
                "tsa": "29",
                "stratum_code": "IDF_FD",
                "si_level": "M",
                "managed_curve_id": 21002,
                "unmanaged_curve_id": 1002,
            },
        ]
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 1001, "curve_type": "unmanaged"},
            {"curve_id": 1002, "curve_type": "unmanaged"},
            {"curve_id": 21001, "curve_type": "managed"},
            {"curve_id": 21002, "curve_type": "managed"},
            {"curve_id": 1001001, "curve_type": "unmanaged_species_prop_PL"},
            {"curve_id": 1001002, "curve_type": "unmanaged_species_prop_FD"},
            {"curve_id": 1002001, "curve_type": "unmanaged_species_prop_SW"},
            {"curve_id": 1002002, "curve_type": "unmanaged_species_prop_AT"},
            {"curve_id": 21001001, "curve_type": "managed_species_prop_PL"},
            {"curve_id": 21001002, "curve_type": "managed_species_prop_FD"},
            {"curve_id": 21002001, "curve_type": "managed_species_prop_SW"},
            {"curve_id": 21002002, "curve_type": "managed_species_prop_AT"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 1001, "x": 1, "y": 5.0},
            {"curve_id": 1001, "x": 10, "y": 40.0},
            {"curve_id": 1002, "x": 1, "y": 6.0},
            {"curve_id": 1002, "x": 10, "y": 50.0},
            {"curve_id": 21001, "x": 1, "y": 8.0},
            {"curve_id": 21001, "x": 10, "y": 65.0},
            {"curve_id": 21002, "x": 1, "y": 9.0},
            {"curve_id": 21002, "x": 10, "y": 72.0},
            {"curve_id": 1001001, "x": 1, "y": 0.70},
            {"curve_id": 1001002, "x": 1, "y": 0.30},
            {"curve_id": 1002001, "x": 1, "y": 0.55},
            {"curve_id": 1002002, "x": 1, "y": 0.45},
            {"curve_id": 21001001, "x": 1, "y": 0.80},
            {"curve_id": 21001002, "x": 1, "y": 0.20},
            {"curve_id": 21002001, "x": 1, "y": 0.60},
            {"curve_id": 21002002, "x": 1, "y": 0.40},
        ]
    )
    root = build_forestmodel_xml_tree(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
    )
    out_path = tmp_path / "forestmodel_multi.xml"
    write_forestmodel_xml(root=root, path=out_path)

    expected = Path("tests/fixtures/fmg/forestmodel_multi_au.xml").read_text(
        encoding="utf-8"
    )
    actual = out_path.read_text(encoding="utf-8")
    assert actual == expected


def test_build_patchworks_forestmodel_definition_rejects_invalid_transition_ifm() -> (
    None
):
    au_table = pd.DataFrame(
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
    )
    curve_table = pd.DataFrame(
        [
            {"curve_id": 985501000, "curve_type": "unmanaged"},
            {"curve_id": 985521000, "curve_type": "managed"},
        ]
    )
    curve_points = pd.DataFrame(
        [
            {"curve_id": 985501000, "x": 1, "y": 10.0},
            {"curve_id": 985521000, "x": 1, "y": 12.0},
        ]
    )
    from femic.fmg.adapters import build_bundle_model_context_from_tables

    context = build_bundle_model_context_from_tables(
        au_table=au_table,
        curve_table=curve_table,
        curve_points_table=curve_points,
        tsa_list=["k3z"],
    )

    with pytest.raises(ValueError, match="cc_transition_ifm"):
        build_patchworks_forestmodel_definition(
            context=context,
            cc_transition_ifm="retained",
        )
