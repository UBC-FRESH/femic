from __future__ import annotations

import csv
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
    active_columns = [(index, value) for index, value in enumerate(header) if value.strip()]

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
    assert (
        contract["validation_contract"]["required_curve_ids"]
        == list(expected_points.keys())
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
    factors_rows = list(
        csv.reader(factors_path.open(newline="", encoding="utf-8-sig"))
    )

    assert [(index, value) for index, value in enumerate(criteria_rows[0]) if value] == [
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

    contract_rows = {
        row["row_offset"]: row for row in contract["attribute_rows"]
    }
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
