from __future__ import annotations

import pandas as pd

from femic.workflows.mkrf import (
    _build_tipsy_legacy_au_table,
    _classify_site_index_levels,
    _filter_assignment_to_selected_aus,
)


def test_classify_site_index_levels_splits_into_lmh_bins() -> None:
    levels = _classify_site_index_levels(pd.Series([10.0, 12.0, 20.0, 25.0, 35.0, 40.0]))
    assert list(levels.astype(str)) == ["L", "L", "M", "M", "H", "H"]


def test_build_tipsy_legacy_au_table_derives_bec_and_species_pair() -> None:
    man_si_by_au = pd.DataFrame(
        [
            {"AU": 101, "BEC": "CWHvm2", "SI": 28.5},
            {"AU": 102, "BEC": "MHmm1", "SI": 18.0},
        ]
    )
    tipsy_spp_comp = pd.DataFrame(
        [
            {"AU": 101, "BA": 10.0, "CW": 45.0, "DR": 0.0, "FD": 0.0, "HW": 45.0, "YC": 0.0},
            {"AU": 102, "BA": 0.0, "CW": 0.0, "DR": 20.0, "FD": 60.0, "HW": 20.0, "YC": 0.0},
        ]
    )

    legacy = _build_tipsy_legacy_au_table(
        man_si_by_au=man_si_by_au,
        tipsy_spp_comp=tipsy_spp_comp,
    ).sort_values("AU", kind="stable")

    assert list(legacy["bec_zone"]) == ["cwh", "mhm"]
    assert list(legacy["bec_subzone"]) == ["vm", "m"]
    assert list(legacy["bec_variant"]) == ["2", "1"]
    assert list(legacy["leading_species_1"]) == ["cw", "fdc"]
    assert list(legacy["leading_species_2"]) == ["hw", "dr"]
    assert list(legacy["legacy_candidate_au_id"]) == [
        "cwh_vm_2_cw_hw",
        "mhm_m_1_fdc_dr",
    ]


def test_filter_assignment_to_selected_aus_keeps_only_selected_rows() -> None:
    assignment = pd.DataFrame(
        [
            {"res_key": 1, "au_id": "a"},
            {"res_key": 2, "au_id": "b"},
            {"res_key": 3, "au_id": "c"},
        ]
    )
    selected = pd.DataFrame(
        [
            {"au_id": "b", "selected_rank": 1},
            {"au_id": "c", "selected_rank": 2},
        ]
    )

    filtered = _filter_assignment_to_selected_aus(assignment, selected)

    assert list(filtered["res_key"]) == [2, 3]
    assert list(filtered["au_id"]) == ["b", "c"]
