from __future__ import annotations

import pandas as pd

from femic.pipeline.vri import (
    assign_stratum_codes_with_lexmatch,
    assign_forest_type_from_species_pct,
    classify_stand_cdm,
    classify_stand_forest_type,
    derive_species_list_from_slots,
    filter_post_thlb_stands,
    initialize_aflb_land_base_records,
    is_conifer_species_code,
    is_deciduous_species_code,
    normalize_and_filter_checkpoint2_records,
    pconif,
    pdecid,
    stratify_stand,
)


def _base_row() -> dict[str, object]:
    return {
        "SPECIES_CD_1": None,
        "SPECIES_CD_2": None,
        "SPECIES_CD_3": None,
        "SPECIES_CD_4": None,
        "SPECIES_CD_5": None,
        "SPECIES_CD_6": None,
        "SPECIES_PCT_1": None,
        "SPECIES_PCT_2": None,
        "SPECIES_PCT_3": None,
        "SPECIES_PCT_4": None,
        "SPECIES_PCT_5": None,
        "SPECIES_PCT_6": None,
        "SOIL_NUTRIENT_REGIME": None,
        "SOIL_MOISTURE_REGIME_1": None,
        "SITE_POSITION_MESO": None,
        "BCLCS_LEVEL_2": "T",
        "BCLCS_LEVEL_3": None,
        "BCLCS_LEVEL_4": None,
        "BCLCS_LEVEL_5": None,
        "BEC_VARIANT": None,
        "NON_PRODUCTIVE_CD": None,
        "FOR_MGMT_LAND_BASE_IND": "Y",
        "BEC_ZONE_CODE": "SBS",
        "PROJ_AGE_1": 60,
        "BASAL_AREA": 20,
        "LIVE_STAND_VOLUME_125": None,
        "LIVE_VOL_PER_HA_SPP1_125": None,
        "LIVE_VOL_PER_HA_SPP2_125": None,
        "LIVE_VOL_PER_HA_SPP3_125": None,
        "LIVE_VOL_PER_HA_SPP4_125": None,
        "LIVE_VOL_PER_HA_SPP5_125": None,
        "LIVE_VOL_PER_HA_SPP6_125": None,
    }


def test_normalize_and_filter_checkpoint2_records_applies_fill_defaults() -> None:
    frame = pd.DataFrame([_base_row()]).assign(LIVE_STAND_VOLUME_125=10)
    out = normalize_and_filter_checkpoint2_records(f_table=frame)
    row = out.iloc[0]
    assert row["SPECIES_CD_1"] == "X"
    assert row["SPECIES_PCT_1"] == 0
    assert row["SOIL_NUTRIENT_REGIME"] == "X"
    assert row["LIVE_VOL_PER_HA_SPP1_125"] == 0


def test_normalize_and_filter_checkpoint2_records_filters_excluded_rows() -> None:
    keep = _base_row()
    drop_bec = _base_row() | {"BEC_ZONE_CODE": "BAFA"}
    drop_live_vol = _base_row() | {"LIVE_STAND_VOLUME_125": 0}
    drop_nonproductive = _base_row() | {"NON_PRODUCTIVE_CD": "35"}
    frame = pd.DataFrame([keep, drop_bec, drop_live_vol, drop_nonproductive]).assign(
        LIVE_STAND_VOLUME_125=[10, 10, 0, 10]
    )
    out = normalize_and_filter_checkpoint2_records(f_table=frame)
    assert len(out) == 1
    assert out.iloc[0]["BEC_ZONE_CODE"] == "SBS"


def test_initialize_aflb_land_base_records_keeps_young_and_low_volume_productive_stands() -> (
    None
):
    young_regrowing = _base_row() | {
        "PROJ_AGE_1": 5,
        "LIVE_STAND_VOLUME_125": 0,
        "BASAL_AREA": 1,
    }
    productive_mature = _base_row() | {
        "PROJ_AGE_1": 80,
        "LIVE_STAND_VOLUME_125": 200,
        "BASAL_AREA": 25,
    }
    nonproductive = _base_row() | {
        "NON_PRODUCTIVE_CD": "35",
        "LIVE_STAND_VOLUME_125": 10,
    }
    not_managed = _base_row() | {
        "FOR_MGMT_LAND_BASE_IND": "N",
        "LIVE_STAND_VOLUME_125": 10,
    }
    non_treed = _base_row() | {
        "BCLCS_LEVEL_2": "N",
        "LIVE_STAND_VOLUME_125": 10,
    }
    frame = pd.DataFrame(
        [young_regrowing, productive_mature, nonproductive, not_managed, non_treed]
    )

    out = initialize_aflb_land_base_records(f_table=frame)

    assert len(out) == 2
    assert set(out["PROJ_AGE_1"]) == {5, 80}
    assert set(out["FOR_MGMT_LAND_BASE_IND"]) == {"Y"}


def test_initialize_aflb_land_base_records_can_exclude_bec_zones_when_requested() -> (
    None
):
    keep = _base_row() | {"BEC_ZONE_CODE": "SBS", "LIVE_STAND_VOLUME_125": 10}
    drop = _base_row() | {"BEC_ZONE_CODE": "BAFA", "LIVE_STAND_VOLUME_125": 10}
    frame = pd.DataFrame([keep, drop])

    out = initialize_aflb_land_base_records(
        f_table=frame,
        excluded_bec_zones=("BAFA",),
    )

    assert len(out) == 1
    assert out.iloc[0]["BEC_ZONE_CODE"] == "SBS"


def test_conifer_deciduous_helpers_and_proportions() -> None:
    assert is_conifer_species_code("SW") is True
    assert is_deciduous_species_code("AT") is True
    row = {
        "SPECIES_CD_1": "SW",
        "SPECIES_CD_2": "AT",
        "SPECIES_CD_3": "PL",
        "SPECIES_CD_4": "X",
        "SPECIES_CD_5": "X",
        "SPECIES_CD_6": "X",
        "SPECIES_PCT_1": 50,
        "SPECIES_PCT_2": 30,
        "SPECIES_PCT_3": 20,
        "SPECIES_PCT_4": 0,
        "SPECIES_PCT_5": 0,
        "SPECIES_PCT_6": 0,
    }
    assert pconif(row) == 0.7
    assert pdecid(row) == 0.3


def test_stand_classification_helpers() -> None:
    conif_row = {
        "SPECIES_CD_1": "SW",
        "SPECIES_CD_2": "PL",
        "SPECIES_CD_3": "AT",
        "SPECIES_CD_4": "X",
        "SPECIES_CD_5": "X",
        "SPECIES_CD_6": "X",
        "SPECIES_PCT_1": 60,
        "SPECIES_PCT_2": 25,
        "SPECIES_PCT_3": 15,
        "SPECIES_PCT_4": 0,
        "SPECIES_PCT_5": 0,
        "SPECIES_PCT_6": 0,
    }
    decid_row = conif_row | {
        "SPECIES_CD_1": "AT",
        "SPECIES_CD_2": "EP",
        "SPECIES_PCT_1": 70,
    }
    assert classify_stand_cdm(conif_row) == "c"
    assert classify_stand_cdm(decid_row) == "d"
    assert classify_stand_forest_type(conif_row) == 1


def test_assign_forest_type_from_species_pct_assigns_column() -> None:
    frame = pd.DataFrame(
        [
            {
                "SPECIES_CD_1": "SW",
                "SPECIES_CD_2": "PL",
                "SPECIES_CD_3": "AT",
                "SPECIES_CD_4": "X",
                "SPECIES_CD_5": "X",
                "SPECIES_CD_6": "X",
                "SPECIES_PCT_1": 60,
                "SPECIES_PCT_2": 25,
                "SPECIES_PCT_3": 15,
                "SPECIES_PCT_4": 0,
                "SPECIES_PCT_5": 0,
                "SPECIES_PCT_6": 0,
            },
            {
                "SPECIES_CD_1": "AT",
                "SPECIES_CD_2": "EP",
                "SPECIES_CD_3": "SW",
                "SPECIES_CD_4": "X",
                "SPECIES_CD_5": "X",
                "SPECIES_CD_6": "X",
                "SPECIES_PCT_1": 50,
                "SPECIES_PCT_2": 35,
                "SPECIES_PCT_3": 15,
                "SPECIES_PCT_4": 0,
                "SPECIES_PCT_5": 0,
                "SPECIES_PCT_6": 0,
            },
        ]
    )
    out = assign_forest_type_from_species_pct(f_table=frame)
    assert list(out["forest_type"]) == [1, 4]


def test_stratify_stand_builds_expected_codes() -> None:
    row = {
        "BEC_ZONE_CODE": "SBS",
        "BCLCS_LEVEL_4": "TM",
        "SPECIES_CD_1": "SW",
        "SPECIES_CD_2": "PL",
        "BEC_ZONE_CODE_lexmatch": "SBSx",
        "SPECIES_CD_1_lexmatch": "SSW",
        "SPECIES_CD_2_lexmatch": "PPL",
    }
    assert stratify_stand(row) == "SBS_SW+PL"
    assert stratify_stand(row, lexmatch=True) == "SBSxSBSxSBSx_SSWSSW+PPL"


def test_stratify_stand_supports_bec_subzone_and_species_combos() -> None:
    row = {
        "BEC_ZONE_CODE": "CWH",
        "BEC_SUBZONE": "xm",
        "BEC_VARIANT": "2",
        "BEC_PHASE": "a",
        "BCLCS_LEVEL_4": "XY",
        "SPECIES_CD_1": "HW",
        "SPECIES_PCT_1": 35,
        "SPECIES_CD_2": "CW",
        "SPECIES_PCT_2": 45,
        "SPECIES_CD_3": "FD",
        "SPECIES_PCT_3": 20,
        "BEC_ZONE_CODE_lexmatch": "CWHx",
        "SPECIES_CD_1_lexmatch": "HHW",
        "SPECIES_CD_2_lexmatch": "CCW",
        "SPECIES_CD_3_lexmatch": "FFD",
    }
    assert (
        stratify_stand(row, bec_grouping="subzone", species_combo_count=2)
        == "CWHxm_CW+HW"
    )
    assert (
        stratify_stand(row, bec_grouping="phase", species_combo_count=3)
        == "CWHxm2a_CW+HW+FD"
    )


def test_stratify_stand_supports_attribute_rows() -> None:
    class _Row:
        BEC_ZONE_CODE = "SBS"
        BCLCS_LEVEL_4 = "TM"
        SPECIES_CD_1 = "SW"
        SPECIES_CD_2 = "PL"
        BEC_ZONE_CODE_lexmatch = "SBSx"
        SPECIES_CD_1_lexmatch = "SSW"
        SPECIES_CD_2_lexmatch = "PPL"

        def __getitem__(self, key: str) -> str:
            raise TypeError("attribute-style row only")

    row = _Row()
    assert stratify_stand(row) == "SBS_SW+PL"
    assert stratify_stand(row, lexmatch=True) == "SBSxSBSxSBSx_SSWSSW+PPL"


def test_assign_stratum_codes_with_lexmatch_assigns_both_columns() -> None:
    frame = pd.DataFrame(
        [
            {
                "BEC_ZONE_CODE": "SBS",
                "SPECIES_CD_1": "SW",
                "SPECIES_CD_2": "PL",
                "BCLCS_LEVEL_4": "TM",
            },
            {
                "BEC_ZONE_CODE": "BWBS",
                "SPECIES_CD_1": "AT",
                "SPECIES_CD_2": "X",
                "BCLCS_LEVEL_4": "XY",
            },
        ]
    )

    def _row_apply(table: pd.DataFrame, fn: object, axis: int) -> pd.Series:
        assert axis == 1
        return table.apply(fn, axis=axis)  # type: ignore[arg-type]

    out = assign_stratum_codes_with_lexmatch(
        f_table=frame,
        row_apply_fn=_row_apply,
    )
    assert out.loc[0, "stratum"] == "SBS_SW+PL"
    assert out.loc[1, "stratum"] == "BWBS_AT"
    assert out.loc[0, "stratum_lexmatch"].startswith("SBSxSBSxSBSx_")


def test_assign_stratum_codes_with_lexmatch_supports_species_combo_count() -> None:
    frame = pd.DataFrame(
        [
            {
                "BEC_ZONE_CODE": "CWH",
                "BEC_SUBZONE": "xm",
                "BEC_VARIANT": "2",
                "BEC_PHASE": "a",
                "SPECIES_CD_1": "HW",
                "SPECIES_PCT_1": 40,
                "SPECIES_CD_2": "CW",
                "SPECIES_PCT_2": 35,
                "SPECIES_CD_3": "FD",
                "SPECIES_PCT_3": 25,
                "BCLCS_LEVEL_4": "XY",
            }
        ]
    )

    def _row_apply(table: pd.DataFrame, fn: object, axis: int) -> pd.Series:
        return table.apply(fn, axis=axis)  # type: ignore[arg-type]

    out = assign_stratum_codes_with_lexmatch(
        f_table=frame,
        row_apply_fn=_row_apply,
        bec_grouping="variant",
        species_combo_count=2,
    )
    assert out.loc[0, "stratum"] == "CWHxm2_HW+CW"


def test_filter_post_thlb_stands_filters_expected_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "BCLCS_LEVEL_2": "T",
                "FOR_MGMT_LAND_BASE_IND": "Y",
                "BEC_ZONE_CODE": "SBS",
                "SPECIES_CD_1": "SW",
                "BCLCS_LEVEL_5": "TM",
                "SITE_INDEX": 20.0,
            },
            {
                "BCLCS_LEVEL_2": "N",
                "FOR_MGMT_LAND_BASE_IND": "Y",
                "BEC_ZONE_CODE": "SBS",
                "SPECIES_CD_1": "SW",
                "BCLCS_LEVEL_5": "TM",
                "SITE_INDEX": 20.0,
            },
            {
                "BCLCS_LEVEL_2": "T",
                "FOR_MGMT_LAND_BASE_IND": "Y",
                "BEC_ZONE_CODE": "BAFA",
                "SPECIES_CD_1": "SW",
                "BCLCS_LEVEL_5": "TM",
                "SITE_INDEX": 20.0,
            },
            {
                "BCLCS_LEVEL_2": "T",
                "FOR_MGMT_LAND_BASE_IND": "Y",
                "BEC_ZONE_CODE": "SBS",
                "SPECIES_CD_1": None,
                "BCLCS_LEVEL_5": "TM",
                "SITE_INDEX": 20.0,
            },
        ]
    )
    out = filter_post_thlb_stands(f_table=frame)
    assert len(out) == 1
    assert out.iloc[0]["BEC_ZONE_CODE"] == "SBS"


def test_derive_species_list_from_slots_excludes_none() -> None:
    frame = pd.DataFrame(
        {
            "SPECIES_CD_1": ["SW", None],
            "SPECIES_CD_2": ["PL", "AT"],
            "SPECIES_CD_3": [None, "SW"],
            "SPECIES_CD_4": [None, None],
            "SPECIES_CD_5": [None, None],
            "SPECIES_CD_6": [None, None],
        }
    )
    out = derive_species_list_from_slots(f_table=frame)
    assert set(out) == {"SW", "PL", "AT"}
