from __future__ import annotations

import csv
import json
from pathlib import Path

from femic.tsr_catalog.report import report_tsr_candidate_facts
from femic.tsr_catalog.report import write_tsr_fact_report_csv


def _write_candidate_facts(path: Path) -> None:
    payload = {
        "facts": [
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "fact_family": "source_layer_candidate",
                "value": "WHSE_FOREST_VEGETATION.F_OWN",
                "snippet": "BCGW source layer used for ownership netdown.",
                "page_number": 12,
                "title": "Williams Lake TSA Data Package",
                "cycle_label": "2024 TSR",
                "cycle_year": 2024,
                "provenance_id": "tsa29-doc-12-source-1",
                "source_url": "https://example.invalid/tsa29-data-package.pdf",
            },
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "fact_family": "source_layer_candidate",
                "value": "SD438.B7W54",
                "snippet": "Library call number from the document front matter.",
                "page_number": 1,
                "title": "Williams Lake TSA Data Package",
                "cycle_label": "2024 TSR",
                "cycle_year": 2024,
                "provenance_id": "tsa29-doc-1-source-2",
                "source_url": "https://example.invalid/tsa29-data-package.pdf",
            },
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "fact_family": "thlb_reference",
                "value": "1,682,843 ha",
                "snippet": (
                    "The timber harvesting land base (THLB) for the Williams Lake TSA "
                    "is estimated at 1,682,843 ha."
                ),
                "page_number": 44,
                "title": "Williams Lake TSA Data Package",
                "cycle_label": "2024 TSR",
                "cycle_year": 2024,
                "provenance_id": "tsa29-doc-44-thlb-1",
                "source_url": "https://example.invalid/tsa29-data-package.pdf",
            },
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "fact_family": "thlb_reference",
                "value": "5.1",
                "snippet": ".......... 5.1 Timber harvesting land base",
                "page_number": 3,
                "title": "Williams Lake TSA Data Package",
                "cycle_label": "2024 TSR",
                "cycle_year": 2024,
                "provenance_id": "tsa29-doc-3-thlb-2",
                "source_url": "https://example.invalid/tsa29-data-package.pdf",
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_report_tsr_candidate_facts_ranks_useful_rows_ahead_of_noise(
    tmp_path: Path,
) -> None:
    candidate_facts_path = tmp_path / "tsa_candidate_facts.json"
    _write_candidate_facts(candidate_facts_path)

    result = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa="29",
        fact_families=("source_layer_candidate", "thlb_reference"),
    )

    assert result.tsa_id == "tsa_29"
    assert result.selected_fact_families == (
        "source_layer_candidate",
        "thlb_reference",
    )
    assert len(result.rows) == 4

    first_source = next(
        row for row in result.rows if row.fact_family == "source_layer_candidate"
    )
    assert first_source.extracted_value == "WHSE_FOREST_VEGETATION.F_OWN"
    assert first_source.quality == "likely_useful"
    assert first_source.recommended_query == "WHSE_FOREST_VEGETATION.F_OWN"

    noisy_source = next(
        row for row in result.rows if row.extracted_value == "SD438.B7W54"
    )
    assert noisy_source.quality == "likely_noise"
    assert noisy_source.recommended_query == ""

    useful_thlb = next(
        row for row in result.rows if row.extracted_value == "1,682,843 ha"
    )
    assert useful_thlb.quality == "likely_useful"

    noisy_thlb = next(row for row in result.rows if row.extracted_value == "5.1")
    assert noisy_thlb.quality == "likely_noise"

    counts = result.quality_counts()
    assert counts["likely_useful"] == 2
    assert counts["likely_noise"] == 2


def test_write_tsr_fact_report_csv_writes_review_columns(tmp_path: Path) -> None:
    candidate_facts_path = tmp_path / "tsa_candidate_facts.json"
    _write_candidate_facts(candidate_facts_path)
    result = report_tsr_candidate_facts(
        candidate_facts_path=candidate_facts_path,
        tsa="29",
        fact_families=("source_layer_candidate",),
        limit=1,
    )

    output_csv = tmp_path / "review.csv"
    written = write_tsr_fact_report_csv(result, path=output_csv)

    assert written == output_csv.resolve()
    rows = list(csv.DictReader(output_csv.open(encoding="utf-8", newline="")))
    assert len(rows) == 1
    assert rows[0]["quality"] == "likely_useful"
    assert rows[0]["recommended_query"] == "WHSE_FOREST_VEGETATION.F_OWN"
    assert rows[0]["provenance_id"] == "tsa29-doc-12-source-1"
