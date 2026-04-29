from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as et

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
    assert track_tables["legacy_source_tables"] == {
        "curves.csv": {
            "legacy_path": (
                "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Tracks/curves.csv"
            ),
            "status": "legacy_source_available",
            "size_bytes": 4767897,
            "row_count": 283654,
        },
        "features.csv": {
            "legacy_path": (
                "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Tracks/features.csv"
            ),
            "status": "legacy_source_available",
            "size_bytes": 1177960,
            "row_count": 29364,
        },
        "products.csv": {
            "legacy_path": (
                "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Tracks/products.csv"
            ),
            "status": "legacy_source_available",
            "size_bytes": 1321697,
            "row_count": 28336,
        },
    }
    assert track_tables["instance_pointer_only_tables"] == {
        "curves.csv": {
            "instance_path": "data/legacy_mkrf/compiled_tracks/curves.csv",
            "status": "instance_pointer_only",
            "publication_status": "requires_git_annex_for_instance_publication",
        },
        "features.csv": {
            "instance_path": "data/legacy_mkrf/compiled_tracks/features.csv",
            "status": "instance_pointer_only",
            "publication_status": "requires_git_annex_for_instance_publication",
        },
        "products.csv": {
            "instance_path": "data/legacy_mkrf/compiled_tracks/products.csv",
            "status": "instance_pointer_only",
            "publication_status": "requires_git_annex_for_instance_publication",
        },
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
    assert reconciliation["next_bounded_step"] == {
        "recommendation": "implement_first_builder_activation_gate",
        "roadmap_task": "future_phase",
        "description": (
            "Phase 56 closed with rebuild-readiness criteria published. The next phase "
            "should implement the first selected builder activation gate before any "
            "matrix-build execution or runnable rebuild claim."
        ),
    }


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
        "P56.3 verified existing legacy compiled curves/features/products" in gap
        for gap in remaining_gaps
    )
    assert reconciliation["next_bounded_step"] == {
        "recommendation": "implement_first_builder_activation_gate",
        "roadmap_task": "future_phase",
    }


def test_mkrf_compiled_track_evidence_reconciliation_records_p56_3_boundary() -> None:
    reconciliation_path = Path(
        "external/femic-mkrf-instance/metadata/"
        "legacy_compiled_track_evidence_reconciliation.yaml"
    )

    if not reconciliation_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    reconciliation = yaml.safe_load(reconciliation_path.read_text(encoding="utf-8"))

    assert reconciliation["phase"] == "P56.3"
    assert reconciliation["decision"] == {
        "legacy_compiled_track_evidence": "available_in_planning_corpus",
        "instance_publication": "blocked_pending_git_annex",
        "matrix_build": "not_run",
        "femic_regenerated_outputs": "not_claimed",
        "runnable_rebuild_claim": "no_go",
    }
    assert reconciliation["tooling_boundary"]["git_annex"] == (
        "unavailable_in_active_shell"
    )

    source_tables = reconciliation["source_tables"]
    assert source_tables["curves_csv"]["source_status"] == "legacy_source_available"
    assert source_tables["curves_csv"]["instance_status"] == "instance_pointer_only"
    assert source_tables["curves_csv"]["row_count"] == 283654
    assert source_tables["curves_csv"]["unique_curve_count"] == 10172

    assert source_tables["features_csv"]["row_count"] == 29364
    assert source_tables["features_csv"]["unique_track_count"] == 2116
    assert source_tables["features_csv"]["unique_label_count"] == 38
    assert (
        source_tables["features_csv"]["observed_key_labels"][
            "feature.area.managed.seral.le10"
        ]["row_count"]
        == 1434
    )

    assert source_tables["products_csv"]["row_count"] == 28336
    assert source_tables["products_csv"]["unique_track_count"] == 1434
    assert source_tables["products_csv"]["treatment_row_counts"] == {
        "CC": 20076,
        "CT": 8260,
    }
    assert (
        source_tables["products_csv"]["observed_key_labels"][
            "product.area.managed.treat.CT"
        ]["row_count"]
        == 590
    )

    assert reconciliation["scope_boundary"] == [
        "No ForestModel XML was generated.",
        "No fragments were regenerated.",
        "No Patchworks matrix build was run.",
        "No compiled track payloads were imported into the instance in this slice.",
        "No future FEMIC-regenerated track outputs are claimed.",
        "No runnable FEMIC/Patchworks rebuild claim is introduced.",
    ]
    assert reconciliation["next_bounded_step"] == {
        "recommendation": "implement_first_builder_activation_gate",
        "roadmap_task": "future_phase",
    }


def test_mkrf_builder_activation_plan_records_p56_4_boundary() -> None:
    plan_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_builder_activation_plan.yaml"
    )

    if not plan_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))

    assert plan["phase"] == "P56.4"
    assert plan["decision"] == {
        "builder_activation": "not_started",
        "matrix_build": "not_run",
        "default_exporter_behavior": "unchanged",
        "mkrf_activation": "opt_in_only",
        "runnable_rebuild_claim": "no_go",
    }

    assert [step["surface"] for step in plan["activation_order"]] == [
        "curve_emission",
        "retention_netdown_emission",
        "attribute_emission",
        "stratum_treat_emission",
        "full_forestmodel_xml_emission",
        "patchworks_matrix_build_handoff",
    ]

    matrix_handoff = plan["activation_order"][-1]
    assert matrix_handoff["validation_gate"] == [
        "Run only after source-input publication boundary is resolved.",
        "Never treat archival legacy compiled tracks as FEMIC-generated outputs.",
        (
            "Compare matrix-build outputs to legacy compiled track evidence before "
            "any runnable rebuild claim."
        ),
    ]

    assert plan["legacy_evidence_boundary"]["rule"] == [
        "Archival evidence may be used for comparison and acceptance gates.",
        "Archival evidence must not be relabeled as FEMIC-regenerated output.",
        (
            "Matrix-build success is not sufficient without direct output comparison "
            "against relevant legacy evidence."
        ),
    ]
    assert plan["scope_boundary"] == [
        "No builder was activated by P56.4.",
        "No ForestModel XML was generated by P56.4.",
        "No fragments were regenerated by P56.4.",
        "No Patchworks matrix build was run by P56.4.",
        "No default exporter behavior changed.",
        "No runnable FEMIC/Patchworks rebuild claim is introduced.",
    ]
    assert plan["next_bounded_step"] == {
        "recommendation": "implement_first_builder_activation_gate",
        "roadmap_task": "future_phase",
    }


def test_mkrf_source_input_publication_boundary_records_p56_5_decision() -> None:
    boundary_path = Path(
        "external/femic-mkrf-instance/metadata/"
        "legacy_source_input_publication_boundary.yaml"
    )

    if not boundary_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    boundary = yaml.safe_load(boundary_path.read_text(encoding="utf-8"))

    assert boundary["phase"] == "P56.5"
    assert boundary["last_updated_phase"] == "P58.3b"
    assert boundary["decision"] == {
        "source_input_publication_boundary": "resolved_for_next_readiness_gate",
        "payload_intake": "not_started",
        "matrix_build": "not_run",
        "builder_activation": "not_started",
        "runnable_rebuild_claim": "no_go",
    }

    fragments = boundary["required_for_future_matrix_build_candidate"][
        "compiled_runtime_inputs"
    ]["fragments"]
    assert (
        fragments["publication_status"] == "requires_git_annex_for_instance_publication"
    )
    assert fragments["readable_legacy_source"]["feature_count"] == 1763
    assert fragments["readable_legacy_source"]["geometry_type"] == "Polygon"
    assert fragments["readable_legacy_source"]["crs"] == "EPSG:3005"
    assert fragments["readable_legacy_source"]["required_fields"] == [
        "RES_KEY",
        "CONTCLAS",
        "AGE_2020",
        "AU_EX",
        "AU_FU",
        "Operabilit",
        "CT_eligib",
    ]

    field_contract = boundary["field_contract"]
    assert field_contract["base_mkrf_xml_input"] == {
        "block": "Int(RES_KEY)",
        "area": "area()/10000",
        "age": "Int(AGE_2020)",
        "exclude": "CONTCLAS eq 'X'",
    }
    assert field_contract["additional_stratification"]["ct"] == "CT_eligib"

    lanes = boundary["publication_lanes"]
    assert lanes["archival_runtime_candidate_lane"]["status"] == (
        "blocked_pending_git_annex_for_fragments"
    )
    assert lanes["raw_source_reproducibility_lane"]["status"] == (
        "resultant_boundary_reconstructed_and_substitute_separation_explicit"
    )
    reconstructed = lanes["raw_source_reproducibility_lane"][
        "reconstructed_fragments_publication_boundary"
    ]
    assert reconstructed["source_feature_class"] == {
        "path": (
            "MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData/"
            "Resultant.gdb/Resultant"
        ),
        "feature_count": 1873,
        "geometry_type": "MultiPolygon",
    }
    assert reconstructed["runtime_publication"] == {
        "target_glob": "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Spatial/fragments.*",
        "published_feature_count": 1763,
        "geometry_type": "Polygon",
        "filter": {
            "expression": "CONTCLAS != 'X'",
            "excluded_feature_count": 110,
            "excluded_rollup": "2_Non_Forest",
            "excluded_netdown_counts": {
                "2_11_Non_Forest": 97,
                "2_10_Roads": 13,
            },
        },
    }
    assert reconstructed["field_projection"] == [
        {"source": "Operability", "published": "Operabilit"},
        {"source": "Shape_Length", "published": "Shape_Leng"},
        {"source": "Shape_Area", "published": "Shape_Area"},
        {"source": "CONTCLAS", "published": "CONTCLAS"},
        {"source": "AGE_2020", "published": "AGE_2020"},
        {"source": "AU_EX", "published": "AU_EX"},
        {"source": "AU_FU", "published": "AU_FU"},
        {"source": "RES_KEY", "published": "RES_KEY"},
        {"source": "CT_eligib", "published": "CT_eligib"},
    ]
    assert reconstructed["verification"] == {
        "shared_res_key_count": 1763,
        "core_field_mismatches": 0,
        "true_multipart_shared_features": 0,
        "note": [
            "Resultant rows carried single-part multipolygon geometries only.",
            (
                "No value drift was observed across the published runtime field "
                "subset."
            ),
        ],
    }
    assert lanes["raw_source_reproducibility_lane"]["substitute_boundary"] == {
        "raw_source_rule": {
            "status": "required_for_source_faithful_claim",
            "definition": [
                (
                    "Raw source means the upstream "
                    "`03_MappingAnalysisData/*` surfaces that feed "
                    "`Resultant.gdb/Resultant`, not later published runtime "
                    "artifacts."
                ),
                (
                    "A source-faithful rebuild claim must start from those "
                    "upstream source surfaces or a fully documented "
                    "reproduction of them."
                ),
            ],
        },
        "compiled_runtime_substitutes": {
            "status": "not_acceptable_as_raw_source",
            "rejected_surfaces": [
                "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Spatial/fragments.*",
                "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Spatial/topo_frag100.csv",
                "data/legacy_mkrf/compiled_spatial/fragments.*",
                "data/legacy_mkrf/compiled_spatial/topo_frag100.csv",
            ],
            "rationale": [
                (
                    "These are compiled runtime publications used for "
                    "matrix-build and launch validation, not upstream source "
                    "inputs."
                ),
                (
                    "They may serve as comparison evidence, but not as "
                    "substitutes for source-faithful reconstruction."
                ),
            ],
        },
        "checkpoint_derived_substitutes": {
            "status": "not_acceptable_as_raw_source",
            "rejected_classes": [
                "instance-local restart or resume checkpoints",
                "exported fragments derived from previously compiled runtime lanes",
                (
                    "any derived boundary/checkpoint artifact created for "
                    "debugging or restart convenience"
                ),
            ],
            "rationale": [
                (
                    "Checkpoints are derived intermediates. They can support "
                    "resume or debugging, but they do not answer raw-source "
                    "provenance questions."
                ),
                (
                    "P58.3 explicitly keeps checkpoint-derived artifacts "
                    "separate from the upstream mapping and yield-prep "
                    "source lane."
                ),
            ],
        },
    }
    assert lanes["current_femic_run_profile_lane"]["status"] == (
        "template_not_runnable_source_boundary"
    )

    assert boundary["explicit_non_requirements_for_next_gate"]["roads"]["status"] == (
        "not_required_for_current_legacy_pin"
    )
    assert boundary["explicit_non_requirements_for_next_gate"]["outputs"]["status"] == (
        "not_required_as_source_input"
    )
    assert (
        boundary["explicit_non_requirements_for_next_gate"][
            "direct_workbook_publication"
        ]["status"]
        == "not_required_for_current_femic_contract"
    )

    assert boundary["identity_boundary"] == {
        "generated_xml_literal_description": "Base TFL26",
        "accepted_case_identity": "mkrf_legacy_2016",
        "status": "mismatch_recorded_not_accepted_identity",
        "decision": [
            "Preserve `Base TFL26` as a literal legacy artifact value.",
            "Do not use `Base TFL26` as the MKRF case identity.",
            (
                "Carry the mismatch into rebuild-readiness criteria as a required "
                "caveat or correction before any user-facing runnable claim."
            ),
        ],
    }
    assert boundary["next_bounded_step"] == {
        "recommendation": "publish_reproducibility_boundary_before_source_faithful_claim",
        "roadmap_task": "P58.3c",
    }


def test_mkrf_rebuild_readiness_criteria_close_phase_56() -> None:
    criteria_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_rebuild_readiness_criteria.yaml"
    )

    if not criteria_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    criteria = yaml.safe_load(criteria_path.read_text(encoding="utf-8"))

    assert criteria["phase"] == "P56.6"
    assert criteria["decision"] == {
        "metadata_recovery": "complete_for_phase_56",
        "runnable_rebuild_candidate": "no_go",
        "builder_activation": "not_started",
        "matrix_build": "not_run",
        "runnable_rebuild_claim": "blocked_until_all_criteria_pass",
    }

    assert criteria["claim_levels"]["metadata_recovery_complete"]["status"] == "go"
    assert (
        criteria["claim_levels"]["runnable_rebuild_candidate_ready"]["status"]
        == "no_go"
    )

    gates = {
        gate["gate_id"]: gate["status"] for gate in criteria["required_go_no_go_gates"]
    }
    assert gates == {
        "legacy_evidence_gate": "passed_for_metadata_recovery",
        "source_input_publication_gate": "not_passed",
        "builder_activation_gate": "not_started",
        "generated_xml_gate": "not_started",
        "matrix_build_gate": "not_started",
        "output_comparison_gate": "not_started",
        "identity_gate": "not_passed",
    }

    assert criteria["explicit_scope_boundary"] == [
        "No builder was activated by P56.6.",
        "No ForestModel XML was generated by P56.6.",
        "No fragments were regenerated by P56.6.",
        "No Patchworks matrix build was run by P56.6.",
        "No source payloads, roads, outputs, or direct workbook payloads were ingested by P56.6.",
        "No runnable FEMIC/Patchworks rebuild claim is introduced.",
    ]
    assert criteria["phase_56_closeout"] == {
        "status": "closed_as_readiness_planning_and_evidence_boundary_phase",
        "next_recommended_phase": {
            "focus": "implement_first_builder_activation_gate",
            "starting_boundary": [
                "Start with curve emission or another explicitly selected P56.4 gate.",
                (
                    "Do not run matrix build until source-input publication and "
                    "XML emission gates pass."
                ),
            ],
        },
    }


def test_mkrf_runtime_model_layout_records_p57_2_boundary() -> None:
    layout_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_runtime_model_layout.yaml"
    )

    if not layout_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    layout = yaml.safe_load(layout_path.read_text(encoding="utf-8"))

    assert layout["phase"] == "P57.2"
    assert layout["status"] == "runtime_model_directory_materialized_pre_xml"
    assert layout["decision"] == {
        "runtime_model_directory": "materialized",
        "accepted_runtime_input_lane": "legacy_compiled_spatial_and_controls",
        "spatial_payload_source": "local_planning_corpus_compiled_runtime_copy",
        "archival_annex_remote_materialization": "blocked_in_active_shell",
        "xml_emission": "not_started",
        "matrix_build": "not_run",
        "launch_proof": "not_run",
        "runnable_rebuild_claim": "no_go",
    }

    assert layout["model_layout"] == {
        "model_root": "models/mkrf_patchworks_model",
        "analysis_root": "models/mkrf_patchworks_model/analysis",
        "xml_root": "models/mkrf_patchworks_model/XML",
        "spatial_root": "models/mkrf_patchworks_model/Spatial",
        "tracks_root": "models/mkrf_patchworks_model/Tracks",
        "scripts_root": "models/mkrf_patchworks_model/Scripts",
        "targets_root": "models/mkrf_patchworks_model/Targets",
        "initial_targets_root": "models/mkrf_patchworks_model/InitialTargets",
    }

    spatial_contract = layout["materialized_inputs"]["spatial_runtime"]["contract"]
    assert spatial_contract == {
        "crs": "EPSG:3005",
        "feature_count": 1763,
        "block_key": "RES_KEY",
    }
    assert layout["materialized_inputs"]["scenario_controller"]["known_gap"] == [
        (
            "the legacy target-description file was not recovered in the compiled "
            "control slice and is represented by a fail-fast placeholder"
        )
    ]
    assert layout["future_output_staging"] == {
        "xml_root": {
            "path": "models/mkrf_patchworks_model/XML",
            "producer": "P57.3_femic_opt_in_mkrf_xml_emission",
        },
        "tracks_root": {
            "path": "models/mkrf_patchworks_model/Tracks",
            "producer": "P57.6_patchworks_matrix_build",
        },
    }
    assert layout["scope_boundary"] == [
        "No FEMIC-generated ForestModel XML was written into the runtime model directory.",
        "No legacy compiled track tables were copied into runtime `Tracks/` as generated output.",
        "No Patchworks runtime config was rewired.",
        "No Patchworks matrix build was run.",
        "No Patchworks launch proof was run.",
        "No runnable FEMIC/Patchworks rebuild claim is introduced.",
    ]
    assert layout["next_bounded_step"] == {
        "recommendation": "implement_opt_in_mkrf_xml_emission",
        "roadmap_task": "P57.3",
    }

    runtime_root = Path("external/femic-mkrf-instance/models/mkrf_patchworks_model")
    assert (runtime_root / "analysis" / "base.pin").exists()
    assert (runtime_root / "analysis" / "ScenarioSet.bsh").exists()
    assert (runtime_root / "Spatial" / "fragments.shp").exists()
    assert (runtime_root / "Spatial" / "topo_frag100.csv").exists()
    placeholder = runtime_root / "InitialTargets" / "00_Target_Descriptions.bsh"
    assert placeholder.exists()
    placeholder_text = placeholder.read_text(encoding="utf-8")
    assert "InitialTargets/00_Target_Descriptions.bsh" in placeholder_text
    assert "target-description lane" in placeholder_text


def test_mkrf_source_reproducibility_boundary_records_p58_3c() -> None:
    boundary_path = Path(
        "external/femic-mkrf-instance/metadata/"
        "legacy_source_reproducibility_boundary.yaml"
    )

    if not boundary_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    boundary = yaml.safe_load(boundary_path.read_text(encoding="utf-8"))

    assert boundary["phase"] == "P58.3c"
    assert boundary["status"] == (
        "reproducibility_boundary_published_no_source_faithful_claim"
    )
    assert boundary["decision"] == {
        "raw_source_publication_boundary": "published",
        "source_faithful_rebuild_claim": "not_permitted_yet",
        "compiled_runtime_substitution": "rejected",
        "checkpoint_substitution": "rejected",
        "matrix_build_dependency": "unchanged",
        "runnable_minimal_claim": "unchanged",
    }
    assert boundary["raw_source_lane"]["authoritative_upstream_families"] == [
        "MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData/Source.gdb",
        "MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData/Resultant.gdb",
        "MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData/Resultant_info_v1.xlsx",
        "MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData/03_Yields/VDYP/*",
    ]
    assert boundary["raw_source_lane"]["reconstructed_publication_contract"][
        "published_runtime_target"
    ] == {
        "path_glob": "MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF/Spatial/fragments.*",
        "feature_count": 1763,
        "geometry_type": "Polygon",
        "filter_expression": "CONTCLAS != 'X'",
        "excluded_feature_count": 110,
    }
    assert boundary["rejected_substitutes"]["compiled_runtime"]["status"] == (
        "not_raw_source"
    )
    assert boundary["rejected_substitutes"]["checkpoint_derived"]["status"] == (
        "not_raw_source"
    )
    assert boundary["claim_boundary"]["allowed_now"] == [
        (
            "minimally_runnable_patchworks_instance_from_femic_managed_xml_plus_"
            "accepted_compiled_spatial_inputs"
        ),
        "raw_source_publication_boundary_reconstructed_at_contract_level",
    ]
    assert boundary["claim_boundary"]["not_allowed_yet"] == [
        "source_faithful_mkrf_rebuild",
        (
            "claim_that_runtime_fragments_or_topology_were_regenerated_from_"
            "upstream_mapping_inputs"
        ),
        (
            "claim_that_checkpoint_or_compiled_runtime_surfaces_are_equivalent_"
            "to_raw_source"
        ),
    ]
    assert boundary["next_bounded_step"] == {
        "recommendation": "broaden_runtime_and_scenario_validation_beyond_minimal_launch",
        "roadmap_task": "P58.4",
    }


def test_mkrf_runtime_xml_emission_records_p58_2_boundary() -> None:
    emission_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_runtime_xml_emission.yaml"
    )

    if not emission_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    emission = yaml.safe_load(emission_path.read_text(encoding="utf-8"))

    assert emission["phase"] == "P58.2"
    assert emission["status"] == "runtime_xml_emitted_with_native_attribute_builder"
    assert emission["decision"] == {
        "runtime_xml_emission": "materialized",
        "emission_mode": "opt_in_mkrf_contract_builder",
        "generated_yield_curves": "inlined_from_curve_table_csv",
        "native_attribute_builder": "materialized",
        "matrix_build": "passed",
        "launch_proof": "passed",
        "runnable_rebuild_claim": "minimal_runnable",
    }
    assert emission["emitted_artifact"]["path"] == (
        "models/mkrf_patchworks_model/XML/baseMKRF.xml"
    )
    assert emission["emitted_artifact"]["sha256"] == (
        "18b22086c44faa9dcd61ddfcf71156d15efee7b7bdcf09b9c7a27cf6bc1cb6e7"
    )
    assert emission["emitted_artifact"]["forest_model"] == {
        "description": "Base TFL26",
        "horizon_years": 300,
        "start_year": 2020,
        "max_age": 350,
        "match": "multi",
    }
    assert emission["emitted_artifact"]["structure_counts"] == {
        "defines": 12,
        "curves": 1057,
        "selects": 11,
        "retentions": 2,
        "treatments": 2,
    }
    assert emission["emitted_contract"]["define_fields"] == [
        "status",
        "au",
        "auf",
        "oper",
        "ct",
        "aux",
        "treatment",
        "managed",
        "unmanaged",
        "operable",
        "lowoper",
        "frd",
    ]
    assert emission["emitted_contract"]["input"] == {
        "block": "Int(RES_KEY)",
        "area": "Shape_Area/10000",
        "age": "Int(AGE_2020)",
        "exclude": "CONTCLAS eq 'X'",
    }
    assert emission["emitted_contract"]["inlined_generated_curve_source"] == {
        "curve_count": 1049,
        "producer": "data/legacy_mkrf/generated_xml/CSV/CURVE_TABLE.csv",
    }
    assert emission["phase"] == "P58.2"
    assert emission["status"] == "runtime_xml_emitted_with_native_attribute_builder"
    assert emission["decision"] == {
        "runtime_xml_emission": "materialized",
        "emission_mode": "opt_in_mkrf_contract_builder",
        "generated_yield_curves": "inlined_from_curve_table_csv",
        "native_attribute_builder": "materialized",
        "matrix_build": "passed",
        "launch_proof": "passed",
        "runnable_rebuild_claim": "minimal_runnable",
    }
    assert emission["inputs"]["attribute_review_extract"] == (
        "metadata/mkrf_xlsm_review/ranges/attrib_attributes.review.csv"
    )
    assert emission["inputs"]["species_lookup_review_extract"] == (
        "metadata/mkrf_xlsm_review/ranges/lookups_spp_comp.review.csv"
    )
    assert emission["next_bounded_step"] == {
        "recommendation": "reconstruct_raw_source_input_lane",
        "roadmap_task": "P58.3",
    }

    runtime_xml = Path(
        "external/femic-mkrf-instance/models/mkrf_patchworks_model/XML/baseMKRF.xml"
    )
    assert runtime_xml.exists()
    root = et.parse(runtime_xml).getroot()
    assert root.attrib == {
        "description": "Base TFL26",
        "horizon": "300",
        "year": "2020",
        "maxage": "350",
        "match": "multi",
    }
    assert root.find("./curve[@id='Yield_1']") is not None
    assert len(root.findall("./select")) == 11
    assert root.find("./define[@field='frd']") is not None
    assert (
        root.find(".//features/attribute[@label='%f.area.%m.seral.le10']") is not None
    )
    assert root.find(".//features/attribute[@label='%f.yield.%m.indsp.Ba']") is not None


def test_mkrf_attribute_passthrough_records_p57_4_boundary() -> None:
    passthrough_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_attribute_passthrough.yaml"
    )

    if not passthrough_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    passthrough = yaml.safe_load(passthrough_path.read_text(encoding="utf-8"))

    assert passthrough["phase"] == "P57.4"
    assert passthrough["status"] == "attribute_passthrough_materialized_for_runtime_xml"
    assert passthrough["decision"] == {
        "passthrough_mode": "extracted_legacy_select_blocks",
        "source_of_truth": "data/legacy_mkrf/generated_xml/baseMKRF.xml",
        "native_attribute_builder": "not_implemented",
        "compatibility_constant_dependencies": "materialized",
        "matrix_build": "not_run",
        "launch_proof": "not_run",
        "runnable_rebuild_claim": "no_go",
    }
    assert passthrough["compatibility_contract"]["extracted_select_block_count"] == 5
    assert passthrough["compatibility_contract"]["validated_dependencies"] == {
        "define_fields": ["status", "au", "aux", "treatment", "managed", "frd"],
        "curve_ids": ["one", "le10"],
        "generated_curve_family": "Yield_*",
        "required_attribute_labels": [
            "%f.area.%m.total",
            "%f.yield.%m.total",
            "%f.yield.%m.merch.total",
            "%f.yield.%m.indsp.Ba",
            "%f.yield.%m.indsp.Cw",
            "%f.yield.%m.indsp.Dec",
            "%f.yield.%m.indsp.Fd",
            "%f.yield.%m.indsp.Hw",
            "%f.yield.%m.indsp.Oth",
            "%f.yield.%m.indsp.Dr",
            "%f.yield.%m.indsp.Yc",
            "%f.area.%m.seral.le10",
        ],
    }
    assert [
        block["block_id"]
        for block in passthrough["compatibility_contract"]["extracted_blocks"]
    ] == [
        "feature_area_and_total_yield",
        "merchantable_total_yield",
        "individual_species_yield",
        "seral_le10_area",
        "product_area_and_yield_family",
    ]
    assert passthrough["next_bounded_step"] == {
        "recommendation": "wire_runtime_config_to_generated_model_directory",
        "roadmap_task": "P57.5",
    }


def test_mkrf_runtime_config_points_to_generated_runtime_model() -> None:
    config_path = Path(
        "external/femic-mkrf-instance/config/patchworks.runtime.windows.yaml"
    )

    if not config_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["matrix_builder"] == {
        "fragments_path": "../models/mkrf_patchworks_model/Spatial/fragments.dbf",
        "output_dir": "../models/mkrf_patchworks_model/Tracks",
        "forestmodel_xml_path": "../models/mkrf_patchworks_model/XML/baseMKRF.xml",
        "auto_close_window_on_success": True,
        "auto_close_settle_seconds": 2.0,
        "auto_close_timeout_seconds": 10.0,
    }


def test_mkrf_runtime_config_wiring_records_p57_5_boundary() -> None:
    wiring_path = Path(
        "external/femic-mkrf-instance/metadata/legacy_runtime_config_wiring.yaml"
    )

    if not wiring_path.exists():
        pytest.skip("MKRF instance submodule is not materialized")

    wiring = yaml.safe_load(wiring_path.read_text(encoding="utf-8"))

    assert wiring["phase"] == "P57.5"
    assert wiring["status"] == "runtime_config_wired_and_preflight_validated"
    assert wiring["decision"] == {
        "runtime_config_wiring": "materialized",
        "variant_registration": "builtin_registry_updated",
        "preflight": "passed",
        "matrix_build": "not_run",
        "launch_proof": "not_run",
        "runnable_rebuild_claim": "no_go",
    }
    assert wiring["runtime_surfaces"] == {
        "runtime_config": "config/patchworks.runtime.windows.yaml",
        "analysis_pin": "models/mkrf_patchworks_model/analysis/base.pin",
        "fragments_path": "models/mkrf_patchworks_model/Spatial/fragments.dbf",
        "forestmodel_xml_path": "models/mkrf_patchworks_model/XML/baseMKRF.xml",
        "tracks_output_dir": "models/mkrf_patchworks_model/Tracks",
        "builtin_variant": {
            "variant_id": "mkrf.base",
            "instance_id": "mkrf",
            "analysis_pin": "external/femic-mkrf-instance/models/mkrf_patchworks_model/analysis/base.pin",
            "runtime_config": "external/femic-mkrf-instance/config/patchworks.runtime.windows.yaml",
        },
    }
    assert wiring["preflight_result"]["status"] == "passed"
    assert wiring["preflight_result"]["license_host"] == "auth.spatial.ca"
    assert wiring["next_bounded_step"] == {
        "recommendation": "run_matrix_build_against_emitted_xml_and_accepted_spatial_inputs",
        "roadmap_task": "P57.6",
    }
