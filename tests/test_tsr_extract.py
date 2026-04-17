from __future__ import annotations

import json
from pathlib import Path

from femic import tsr_catalog


def _write_inventory(tmp_path: Path) -> Path:
    payload = {
        "generated_utc": "2026-04-04T00:00:00+00:00",
        "document_count": 2,
        "documents": [
            {
                "tsa_id": "tsa_29",
                "tsa_code": "29",
                "tsa_name": "Williams Lake",
                "cycle_label": "TSR_2024",
                "cycle_year": 2024,
                "title": "29ts_dpkg_2024",
                "document_type": "data_package",
                "file_name": "29ts_dpkg_2024.pdf",
                "file_extension": "pdf",
                "relative_path": "TSR_2024/Data_Package_2024/29ts_dpkg_2024.pdf",
                "url": "https://example.invalid/29ts_dpkg_2024.pdf",
                "listed_modified_raw": "4/3/2026 12:00 PM",
                "size_bytes": 100,
            },
            {
                "tsa_id": "tsa_08",
                "tsa_code": "08",
                "tsa_name": "Kamloops",
                "cycle_label": "TSR_2021",
                "cycle_year": 2021,
                "title": "08ts_ra_2021",
                "document_type": "rationale",
                "file_name": "08ts_ra_2021.pdf",
                "file_extension": "pdf",
                "relative_path": "TSR_2021/08ts_ra_2021.pdf",
                "url": "https://example.invalid/08ts_ra_2021.pdf",
                "listed_modified_raw": "4/3/2026 12:01 PM",
                "size_bytes": 120,
            },
        ],
    }
    inventory_path = tmp_path / "metadata" / "tsr" / "tsa_documents.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(payload), encoding="utf-8")
    return inventory_path


def test_extract_tsr_candidate_facts_writes_reviewable_fact_manifest(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    cached_pdf = (
        corpus_root
        / "tsa"
        / "tsa_29"
        / "TSR_2024"
        / "Data_Package_2024"
        / "29ts_dpkg_2024.pdf"
    )
    cached_pdf.parent.mkdir(parents=True, exist_ok=True)
    cached_pdf.write_bytes(b"fake-pdf")
    output_path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"

    def _fake_extract_pages(path: Path) -> tuple[str, ...]:
        assert path == cached_pdf
        return (
            "\n".join(
                [
                    "Data source list",
                    "BCGW WHSE_FOREST_VEGETATION.F_OWN 2024",
                    "Analysis Unit 23009 defines an SBSdk-leading stand group",
                    "THLB 1,682,843 ha",
                    "TIPSY assumptions: OAF1 15 OAF2 5 regen delay 2",
                ]
            ),
        )

    result = tsr_catalog.extract_tsr_candidate_facts(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        output_path=output_path,
        tsa_filters=("29",),
        source_root=tmp_path,
        extract_pdf_pages_fn=_fake_extract_pages,
    )

    assert result.selected_document_count == 1
    assert result.extracted_documents_count == 1
    assert len(result.failures) == 0
    families = {fact.fact_family for fact in result.facts}
    assert families == {
        "document_metadata",
        "source_layer_candidate",
        "au_definition_candidate",
        "thlb_reference",
        "tipsy_input_candidate",
    }
    values = {fact.value for fact in result.facts}
    assert "WHSE_FOREST_VEGETATION.F_OWN" in values
    assert "1,682,843 ha" in values

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["fact_count"] == 5
    assert payload["fact_family_counts"]["source_layer_candidate"] == 1


def test_extract_tsr_candidate_facts_reports_missing_cached_pdfs(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    output_path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"

    result = tsr_catalog.extract_tsr_candidate_facts(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        output_path=output_path,
        tsa_filters=("29",),
        source_root=tmp_path,
        extract_pdf_pages_fn=lambda _path: ("unused",),
    )

    assert result.selected_document_count == 1
    assert result.extracted_documents_count == 0
    assert len(result.facts) == 0
    assert len(result.failures) == 1
    assert result.failures[0].error == "cached_pdf_missing"


def test_extract_tsr_candidate_facts_repairs_wrapped_source_layer_tokens(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    cached_pdf = (
        corpus_root
        / "tsa"
        / "tsa_29"
        / "TSR_2024"
        / "Data_Package_2024"
        / "29ts_dpkg_2024.pdf"
    )
    cached_pdf.parent.mkdir(parents=True, exist_ok=True)
    cached_pdf.write_bytes(b"fake-pdf")
    output_path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"

    def _fake_extract_pages(path: Path) -> tuple[str, ...]:
        assert path == cached_pdf
        return (
            "\n".join(
                [
                    "Mule Deer winter range BCGW REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER_",
                    "WR_CAR_POLY",
                    "Ungulate winter range BCGW WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RAN",
                    "GE_SP",
                ]
            ),
        )

    result = tsr_catalog.extract_tsr_candidate_facts(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        output_path=output_path,
        tsa_filters=("29",),
        source_root=tmp_path,
        extract_pdf_pages_fn=_fake_extract_pages,
    )

    source_values = {
        fact.value
        for fact in result.facts
        if fact.fact_family == "source_layer_candidate"
    }
    assert "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER_WR_CAR_POLY" in source_values
    assert "WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RANGE_SP" in source_values
    assert "REG_LAND_AND_NATURAL_RESOURCE.L_MULE_DEER_" not in source_values
    assert "WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RAN" not in source_values


def test_extract_tsr_candidate_facts_captures_wildlife_harvest_zone_lines_as_thlb_references(
    tmp_path: Path,
) -> None:
    inventory_path = _write_inventory(tmp_path)
    corpus_root = tmp_path / ".femic" / "tsr" / "corpus"
    cached_pdf = (
        corpus_root
        / "tsa"
        / "tsa_29"
        / "TSR_2024"
        / "Data_Package_2024"
        / "29ts_dpkg_2024.pdf"
    )
    cached_pdf.parent.mkdir(parents=True, exist_ok=True)
    cached_pdf.write_bytes(b"fake-pdf")
    output_path = tmp_path / "metadata" / "tsr" / "tsa_candidate_facts.json"

    def _fake_extract_pages(path: Path) -> tuple[str, ...]:
        assert path == cached_pdf
        return (
            "\n".join(
                [
                    "Areas designated through GWMs as no harvest will be excluded from the LHLB.",
                    "Areas designated as conditional harvest zone will be addressed in Section 7.",
                ]
            ),
        )

    result = tsr_catalog.extract_tsr_candidate_facts(
        documents_path=inventory_path,
        corpus_root=corpus_root,
        output_path=output_path,
        tsa_filters=("29",),
        source_root=tmp_path,
        extract_pdf_pages_fn=_fake_extract_pages,
    )

    thlb_values = {
        fact.value for fact in result.facts if fact.fact_family == "thlb_reference"
    }
    assert (
        "Areas designated through GWMs as no harvest will be excluded from the LHLB."
        in thlb_values
    )
    assert (
        "Areas designated as conditional harvest zone will be addressed in Section 7."
        in thlb_values
    )
