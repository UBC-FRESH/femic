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
