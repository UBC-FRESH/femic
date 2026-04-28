from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest
import yaml


def test_mkrf_curve_library_contract_matches_review_extract() -> None:
    extract_path = Path("metadata/mkrf_xlsm_review/curve_library.review.csv")
    contract_path = Path(
        "external/femic-mkrf-instance/config/legacy_xml_builder/curve_library.mkrf.yaml"
    )

    if not contract_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    rows = list(csv.reader(extract_path.open(newline="", encoding="utf-8-sig")))
    header = rows[5]
    active_columns = [
        (index, value) for index, value in enumerate(header) if value.strip()
    ]

    assert active_columns == [
        (0, "Age"),
        (1, "zero"),
        (2, "age"),
        (3, "le10"),
        (4, "lt20"),
        (5, "gt60"),
        (6, "lt80"),
        (7, "gt250"),
    ]

    expected_points = {
        curve_id: [
            {"age": int(row[0]), "value": int(row[column_index])}
            for row in rows[6:]
            if column_index < len(row) and row[column_index].strip()
        ]
        for column_index, curve_id in active_columns[1:]
    }
    expected_axis = [int(row[0]) for row in rows[6:] if row and row[0].strip()]

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert contract["build_boundary"]["live_exporter_input"] is False
    assert (
        contract["build_boundary"]["before_curves_hook_status"]
        == "blocked_pending_generated_fragment_acceptance"
    )
    assert contract["age_axis"]["observed_values"] == expected_axis
    assert {
        curve["curve_id"]: curve["points"] for curve in contract["curves"]
    } == expected_points
    assert contract["validation_contract"]["required_curve_ids"] == list(
        expected_points.keys()
    )


def test_mkrf_netdown_contract_matches_complete_review_rows() -> None:
    criteria_path = Path("metadata/mkrf_xlsm_review/ranges/netdown_criteria.review.csv")
    names_path = Path("metadata/mkrf_xlsm_review/ranges/netdown_names.review.csv")
    factors_path = Path("metadata/mkrf_xlsm_review/ranges/netdown_factors.review.csv")
    contract_path = Path(
        "external/femic-mkrf-instance/config/legacy_xml_builder/netdown.mkrf.yaml"
    )

    if not contract_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    criteria_rows = list(
        csv.reader(criteria_path.open(newline="", encoding="utf-8-sig"))
    )
    names_rows = list(csv.reader(names_path.open(newline="", encoding="utf-8-sig")))
    factors_rows = list(csv.reader(factors_path.open(newline="", encoding="utf-8-sig")))

    assert [
        (index, value) for index, value in enumerate(criteria_rows[0]) if value
    ] == [
        (4, "status"),
        (8, "Netdown"),
    ]
    assert names_rows[0][0] == "feature.area.retention.total"

    complete_rows = [
        row
        for row in criteria_rows[1:]
        if row[0].strip() and row[4].strip() and row[8].strip()
    ]
    assert complete_rows == [
        [
            "status in managed and oper in operable",
            "",
            "",
            "",
            "unmanaged",
            "",
            "",
            "",
            "0.1",
        ],
        [
            "status in managed and oper in lowoper",
            "",
            "",
            "",
            "unmanaged",
            "",
            "",
            "",
            "0.2",
        ],
    ]

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert contract["build_boundary"]["live_exporter_input"] is False
    assert (
        contract["build_boundary"]["dump_retention_status"]
        == "blocked_pending_retention_builder_acceptance"
    )
    assert [
        {
            "selection_expression": rule["selection_expression"],
            "reassignment": rule["reassignment"],
            "netdown_proportion": rule["netdown_proportion"],
            "feature_assignments": rule["feature_assignments"],
        }
        for rule in contract["rules"]
    ] == [
        {
            "selection_expression": "status in managed and oper in operable",
            "reassignment": {"field": "status", "value": "unmanaged"},
            "netdown_proportion": 0.1,
            "feature_assignments": [
                {"feature": "feature.area.retention.total", "value": 1}
            ],
        },
        {
            "selection_expression": "status in managed and oper in lowoper",
            "reassignment": {"field": "status", "value": "unmanaged"},
            "netdown_proportion": 0.2,
            "feature_assignments": [
                {"feature": "feature.area.retention.total", "value": 1}
            ],
        },
    ]
    nonblank_factors = [
        row[0]
        for row in factors_rows
        if row and row[0].strip() and all(not cell.strip() for cell in row[1:])
    ]
    assert nonblank_factors == ["1", "1", "1"]
    assert contract["review_only"]["incomplete_feature_factor_rows"] == [
        {
            "source_range": "netdownFactors",
            "row_offset": 3,
            "value": 1,
            "reason": "No matching nonblank netdownCriteria selection row is present.",
        }
    ]
    assert contract["review_only"]["incomplete_netdown_factor_tail"] == {
        "source_range": "netdownCriteria",
        "value": 0.07,
        "count": 85,
        "reason": (
            "Values appear in the Netdown column without matching selection, "
            "reassignment, or feature-factor rows."
        ),
    }


def test_mkrf_attributes_contract_classifies_review_rows() -> None:
    extract_path = Path("metadata/mkrf_xlsm_review/ranges/attrib_attributes.review.csv")
    contract_path = Path(
        "external/femic-mkrf-instance/config/legacy_xml_builder/attributes.mkrf.yaml"
    )

    if not contract_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    rows = list(csv.reader(extract_path.open(newline="", encoding="utf-8-sig")))

    assert rows[0][:9] == [
        "Applies to",
        "Curve or Expression",
        "Attribute Name",
        "Factor",
        "Future",
        "Cycle",
        "Ignore",
        "Output",
        "Scale",
    ]

    complete_rows = {
        row_offset: row
        for row_offset, row in enumerate(rows[1:], start=1)
        if len(row) > 2 and row[2].strip()
    }
    incomplete_rows = [
        row_offset
        for row_offset, row in enumerate(rows[1:], start=1)
        if any(cell.strip() for cell in row) and not (len(row) > 2 and row[2].strip())
    ]

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert contract["build_boundary"]["live_exporter_input"] is False
    assert (
        contract["build_boundary"]["dump_attributes_status"]
        == "blocked_pending_attribute_builder_acceptance"
    )
    assert contract["row_summary"] == {
        "complete_attribute_rows": 16,
        "incomplete_template_rows": 143,
        "rows_with_frd_dependency": 14,
        "rows_with_yield_curve_dependency": 11,
        "rows_with_lookup_table_dependency": 8,
        "rows_with_attribute_reference_dependency": 1,
        "rows_with_curve_library_dependency": 1,
    }
    assert len(complete_rows) == contract["row_summary"]["complete_attribute_rows"]
    assert len(incomplete_rows) == contract["row_summary"]["incomplete_template_rows"]

    contract_rows = {row["row_offset"]: row for row in contract["attribute_rows"]}
    assert sorted(contract_rows) == sorted(complete_rows)
    assert contract_rows[9]["attribute_name"] == "%f.yield.%m.merch.total"
    assert (
        contract_rows[9]["status"]
        == "review_to_build_candidate_blocked_by_attribute_dependency"
    )
    assert contract_rows[21] == {
        "row_offset": 21,
        "family_id": "seral_area_le10",
        "applies_to": "feature",
        "curve_or_expression": "le10",
        "attribute_name": "%f.area.%m.seral.le10",
        "factor_expression": "1",
        "selection_expression": "status ne 'X'",
        "status": "review_to_build_candidate",
    }

    workbook_attribute_names = {
        row[2].strip().strip("'") for row in complete_rows.values()
    }
    assert set(contract["validation_contract"]["required_attribute_names"]).issubset(
        workbook_attribute_names
    )
    assert contract["review_only"]["incomplete_template_rows"]["count"] == len(
        incomplete_rows
    )


def test_mkrf_treat_contract_preserves_treatments_and_review_only_rows() -> None:
    ranges_root = Path("metadata/mkrf_xlsm_review/ranges")
    contract_path = Path(
        "external/femic-mkrf-instance/config/legacy_xml_builder/strata/treat.mkrf.yaml"
    )
    treatments_path = Path(
        "external/femic-mkrf-instance/data/legacy_mkrf/compiled_tracks/treatments.csv"
    )

    if not contract_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    criteria_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_criteria.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    succession_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_succession.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    features_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_features.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    products_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_products.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    factors_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_factors.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )
    treatment_rows = list(
        csv.reader(
            (ranges_root / "treat_stratum_treatments.review.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    )

    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    assert contract["build_boundary"]["live_exporter_input"] is False
    assert (
        contract["build_boundary"]["dump_stratum_status"]
        == "blocked_pending_stratum_builder_acceptance"
    )
    assert not any(any(cell.strip() for cell in row) for row in criteria_rows)
    assert contract["stratum"]["selection_criteria"]["status"] == "empty"
    assert succession_rows[0][2] == "Breakup at"
    assert succession_rows[0][9] == "Renewal age"
    assert succession_rows[1][2] == "999"
    assert succession_rows[1][9] == "0"
    assert contract["stratum"]["succession"] == {
        "status": "review_to_build_candidate_default_rule",
        "breakup_at": 999,
        "renewal_age": 0,
    }

    named_feature_rows = [row for row in features_rows[1:] if row[4].strip()]
    named_product_rows = [
        row for row in products_rows if len(row) > 2 and row[2].strip()
    ]
    assert named_feature_rows == []
    assert named_product_rows == []
    assert contract["stratum"]["feature_rows"]["named_feature_count"] == 0
    assert contract["stratum"]["product_rows"]["named_product_count"] == 0
    assert contract["stratum"]["feature_rows"]["row_count"] == len(features_rows) - 1
    assert contract["stratum"]["product_rows"]["row_count"] == len(products_rows)

    assert treatment_rows[0][2:4] == ["CC", "CT"]
    assert treatment_rows[1][2:4] == ["managed", "managed"]
    assert treatment_rows[5][2] == "if(oper in operable, 60, 150)"
    assert treatment_rows[5][3] == "40"
    assert treatment_rows[6][3] == "150"
    assert treatment_rows[8][2] == "auf"
    assert treatment_rows[8][3] == " 'thn_'+au"
    assert treatment_rows[17][2:4] == ["0", "20"]
    assert factors_rows[1][2:4] == ["1", "1"]

    assert {treatment["treatment_id"] for treatment in contract["treatments"]} == {
        "CC",
        "CT",
    }
    ct_contract = next(
        treatment
        for treatment in contract["treatments"]
        if treatment["treatment_id"] == "CT"
    )
    assert ct_contract["selection"]["additional_expressions"] == [
        "oper in operable",
        "ct eq 'Y'",
        "not startswith(au,'t')",
    ]
    assert ct_contract["maximum_operable_age"] == 150
    assert ct_contract["retention"] == 20

    compiled_rows = list(
        csv.DictReader(treatments_path.open(newline="", encoding="utf-8-sig"))
    )
    compiled_counts = Counter(row["TREATMENT"] for row in compiled_rows)
    assert dict(compiled_counts) == {"CC": 1434, "CT": 590}
    assert contract["compiled_track_crosscheck"]["treatments_csv"]["row_count"] == len(
        compiled_rows
    )
    assert contract["compiled_track_crosscheck"]["treatments_csv"][
        "treatment_counts"
    ] == dict(compiled_counts)


def test_mkrf_rebuild_readiness_records_no_go_contract_gaps() -> None:
    reconciliation_path = Path(
        "external/femic-mkrf-instance/metadata/"
        "legacy_workbook_compiled_reconciliation.yaml"
    )

    if not reconciliation_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    reconciliation = yaml.safe_load(reconciliation_path.read_text(encoding="utf-8"))

    assert reconciliation["decision"] == "no_go_for_runnable_rebuild"
    assert reconciliation["go_no_go"] == {
        "rebuild_claim": "no_go",
        "metadata_recovery_claim": "go",
        "rationale": [
            (
                "Phase 55 recovered the workbook-owned source contract into "
                "FEMIC-ready metadata surfaces."
            ),
            (
                "The current instance is not a runnable legacy Patchworks rebuild "
                "because generated XML fragments, builder activation, and several "
                "compiled matrix tables remain unreconciled."
            ),
            (
                "Compiled archival outputs are sufficient as review evidence for "
                "planning the next recovery phase, not as substitute raw/source inputs."
            ),
        ],
    }

    pin_contract = reconciliation["compiled_output_evidence"]["pin_entrypoint"][
        "observed_contract"
    ]
    assert pin_contract["horizon_years"] == 300
    assert pin_contract["block_key"] == "RES_KEY"
    assert pin_contract["use_routes"] is False
    assert pin_contract["use_patches"] is True

    track_tables = reconciliation["compiled_output_evidence"]["track_tables"]
    assert track_tables["materialized_tables"]["accounts.csv"]["rows"] == 60
    assert track_tables["materialized_tables"]["treatments.csv"]["rows"] == 2024
    assert track_tables["materialized_tables"]["strata.csv"]["rows"] == 2116
    assert set(track_tables["pointer_only_tables"]) == {
        "curves.csv",
        "features.csv",
        "products.csv",
    }
    assert track_tables["observed_contract"]["treatments"]["treatment_counts"] == {
        "CC": 1434,
        "CT": 590,
    }

    generated_xml = reconciliation["compiled_output_evidence"][
        "generated_xml_artifacts"
    ]
    assert generated_xml["base_mkrf_xml"]["status"] == (
        "available_generated_review_artifact_after_p56_2"
    )
    assert generated_xml["curves_xml"]["status"] == (
        "located_and_reconciled_from_legacy_path_not_copied_after_p56_2"
    )
    assert generated_xml["curve_table_csv"]["status"] == (
        "available_generated_review_artifact_after_p56_2"
    )
    assert reconciliation["next_bounded_step"]["recommendation"] == (
        "materialize_or_resolve_pointer_only_compiled_track_tables"
    )


def test_mkrf_generated_xml_reconciliation_records_p56_2_boundary() -> None:
    reconciliation_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_generated_xml_reconciliation.yaml"
    )

    if not reconciliation_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    reconciliation = yaml.safe_load(reconciliation_path.read_text(encoding="utf-8"))

    assert reconciliation["phase"] == "P56.2"
    assert reconciliation["decision"] == {
        "generated_xml_review_artifacts": (
            "base_xml_and_curve_table_materialized_for_review"
        ),
        "before_curves_activation": "blocked",
        "xml_builder_activation": "not_started",
        "runnable_rebuild_claim": "no_go",
    }

    source_artifacts = reconciliation["source_artifacts"]
    assert source_artifacts["base_mkrf_xml"]["instance_path"] == (
        "data/legacy_mkrf/generated_xml/baseMKRF.xml"
    )
    assert source_artifacts["curves_xml"]["instance_path"] is None
    assert source_artifacts["curves_xml"]["status"] == (
        "located_and_reconciled_from_legacy_path_not_copied"
    )
    assert source_artifacts["curve_table_csv"]["instance_path"] == (
        "data/legacy_mkrf/generated_xml/CSV/CURVE_TABLE.csv"
    )

    base_contract = reconciliation["base_mkrf_xml_contract"]
    assert base_contract["forest_model"] == {
        "generated_literal_description": "Base TFL26",
        "horizon_years": 300,
        "start_year": 2020,
        "max_inventory_age": 350,
        "match": "multi",
    }
    assert base_contract["identity_check"]["status"] == (
        "legacy_description_mismatch_recorded"
    )
    assert base_contract["input"] == {
        "block": "Int(RES_KEY)",
        "area": "area()/10000",
        "age": "Int(AGE_2020)",
        "exclude": "CONTCLAS eq 'X'",
    }
    assert base_contract["base_curve_ids"] == [
        "one",
        "zero",
        "age",
        "le10",
        "lt20",
        "gt60",
        "lt80",
        "gt250",
    ]

    curves = reconciliation["curves_xml_reconciliation"]
    assert curves["curve_count"] == 1049
    assert curves["point_count"] == 37764
    assert curves["points_per_curve"] == 36
    assert curves["equivalence"]["status"] == "matched_by_curve_age_value_sets"

    remaining_gaps = set(reconciliation["remaining_gaps"])
    assert any("beforeCurves remains inactive" in gap for gap in remaining_gaps)
    assert any(
        "P56.2 does not materialize pointer-only" in gap for gap in remaining_gaps
    )
    assert reconciliation["next_bounded_step"] == {
        "recommendation": "materialize_or_resolve_pointer_only_compiled_track_tables",
        "roadmap_task": "P56.3",
    }
