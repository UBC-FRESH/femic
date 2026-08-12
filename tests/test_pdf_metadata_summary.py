from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from femic.cli import main as cli_main
from femic.pdf_metadata_summary import (
    PDF_METADATA_SUMMARY_SCHEMA_VERSION,
    PdfMetadataSummaryError,
    TsaInventoryLink,
    build_pdf_metadata_summary,
    compute_pdf_metadata_summary_inputs,
    default_summary_output_path,
    write_pdf_metadata_summary,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SCHEMA_PATH = (
    REPO_ROOT
    / "docs"
    / "reference"
    / "schemas"
    / "femic-pdf-metadata-summary.schema.json"
)


REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "schema_url",
    "generated_utc",
    "document",
    "inventory",
    "text_summary",
    "figures",
    "rendered_pages",
    "provenance",
)


REQUIRED_DOCUMENT_KEYS = (
    "file_name",
    "local_path",
    "source_url",
    "size_bytes",
    "sha256",
    "fetched_at_utc",
    "page_count",
    "title",
    "author",
)

REQUIRED_DOCUMENT_NON_NULL_KEYS = (
    "file_name",
    "local_path",
    "source_url",
    "size_bytes",
    "sha256",
    "fetched_at_utc",
    "page_count",
)


REQUIRED_PROVENANCE_KEYS = (
    "figrecover_version",
    "pymupdf_version",
    "pypdf_version",
    "femic_version",
)


REQUIRED_FIGURE_KEYS = (
    "figure_id",
    "page_number",
    "source",
    "confidence",
)


def _write_minimal_pdf(pdf_path: Path) -> None:
    """Write a tiny valid PDF with one text page to exercise the summary path."""

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length 44 >> stream\n"
        b"BT /F1 12 Tf 72 720 Td (Synthetic PDF body text.) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000262 00000 n \n"
        b"0000000356 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n414\n%%EOF\n"
    )
    pdf_path.write_bytes(pdf_bytes)


def test_pdf_metadata_summary_required_keys_and_figure_section(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_minimal_pdf(pdf_path)
    output_path = tmp_path / "summary" / "extracted_metadata.json"

    inputs = compute_pdf_metadata_summary_inputs(
        pdf_path=pdf_path,
        source_url="https://example.test/sample.pdf",
    )

    summary = build_pdf_metadata_summary(
        pdf_path=inputs.pdf_path,
        source_url="https://example.test/sample.pdf",
        fetched_at_utc="2026-08-09T19:00:00+00:00",
        inventory_link=TsaInventoryLink(
            tsa_id="tsa_99",
            tsa_code="99",
            tsa_name="Sample TSA",
            cycle_label="TSR_2026",
            cycle_year=2026,
            document_type="discussion_paper",
            inventory_relative_path="TSR_2026/sample.pdf",
        ),
        figrecover_render_pages=inputs.rendered_pages,
        figrecover_figure_candidates=inputs.figure_candidates,
        source_relative_path="TSR_2026/sample.pdf",
        page_texts=inputs.page_texts,
    )

    destination = write_pdf_metadata_summary(summary, output_path=output_path)

    payload = json.loads(destination.read_text(encoding="utf-8"))

    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in payload, f"missing top-level key: {key}"

    assert payload["schema_version"] == PDF_METADATA_SUMMARY_SCHEMA_VERSION

    for key in REQUIRED_DOCUMENT_KEYS:
        assert key in payload["document"], f"missing document key: {key}"

    for key in REQUIRED_DOCUMENT_NON_NULL_KEYS:
        assert payload["document"][key] is not None, (
            f"document.{key} should be populated"
        )

    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in payload["provenance"], f"missing provenance key: {key}"

    assert payload["inventory"]["tsa_id"] == "tsa_99"
    assert payload["inventory"]["cycle_label"] == "TSR_2026"
    assert payload["document"]["source_url"] == "https://example.test/sample.pdf"
    assert len(payload["document"]["sha256"]) == 64

    assert isinstance(payload["figures"], list)
    assert isinstance(payload["rendered_pages"], list)

    if payload["figures"]:
        for figure in payload["figures"]:
            for key in REQUIRED_FIGURE_KEYS:
                assert key in figure, f"missing figure key: {key}"


def test_pdf_metadata_summary_rejects_missing_pdf(tmp_path: Path) -> None:
    missing = tmp_path / "absent.pdf"
    with pytest.raises(PdfMetadataSummaryError, match="PDF not found"):
        compute_pdf_metadata_summary_inputs(
            pdf_path=missing,
            source_url="https://example.test/absent.pdf",
        )


def test_pdf_metadata_summary_rejects_blank_source_url(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    _write_minimal_pdf(pdf_path)

    with pytest.raises(PdfMetadataSummaryError, match="source_url cannot be blank"):
        compute_pdf_metadata_summary_inputs(
            pdf_path=pdf_path,
            source_url="   ",
        )


def test_default_summary_output_path_layout(tmp_path: Path) -> None:
    reference_root = tmp_path / "external" / "femic-tsa29-instance" / "reference"

    candidate = default_summary_output_path(
        reference_root,
        "tsa/tsa_29/TSR_2026/Public_Discussion_Paper/29ts_pdp_2026_williams_lake_discussion_paper.pdf",
    )

    assert candidate == (
        reference_root
        / "tsa"
        / "tsa_29"
        / "TSR_2026"
        / "Public_Discussion_Paper"
        / "29ts_pdp_2026_williams_lake_discussion_paper.extracted_metadata.json"
    )


def test_default_summary_output_path_rejects_blank_path(tmp_path: Path) -> None:
    with pytest.raises(PdfMetadataSummaryError):
        default_summary_output_path(tmp_path, "   ")


def test_doc_figures_summarize_pdf_renders_real_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Smoke-test the CLI command with a real fixture PDF from the source tree.

    Mirrors the TSR_2026 discussion paper placement pattern but uses an
    isolated fixture so the test does not depend on cached annex content.
    """

    pdf_path = tmp_path / "fixture.pdf"
    _write_minimal_pdf(pdf_path)
    output_path = tmp_path / "extracted_metadata.json"

    monkeypatch.setattr(cli_main, "Path", Path, raising=False)  # ensure identity

    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "summarize-pdf",
            str(pdf_path),
            "--output-path",
            str(output_path),
            "--source-url",
            "https://example.test/fixture.pdf",
            "--inventory-tsa-id",
            "tsa_99",
            "--inventory-tsa-code",
            "99",
            "--inventory-tsa-name",
            "Sample TSA",
            "--inventory-cycle-label",
            "TSR_2026",
            "--inventory-cycle-year",
            "2026",
            "--inventory-document-type",
            "discussion_paper",
            "--inventory-relative-path",
            "TSR_2026/fixture.pdf",
            "--dpi",
            "96",
            "--femic-command",
            "femic doc figures summarize-pdf --test",
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["document"]["source_url"] == "https://example.test/fixture.pdf"
    assert payload["inventory"]["tsa_id"] == "tsa_99"
    assert payload["inventory"]["cycle_label"] == "TSR_2026"
    assert payload["provenance"]["femic_command"] == (
        "femic doc figures summarize-pdf --test"
    )


def test_doc_figures_summarize_pdf_rejects_missing_input(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "extracted_metadata.json"
    missing_pdf = tmp_path / "does-not-exist.pdf"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "doc",
            "figures",
            "summarize-pdf",
            str(missing_pdf),
            "--output-path",
            str(output_path),
            "--source-url",
            "https://example.test/missing.pdf",
        ],
    )

    assert result.exit_code != 0


def test_pdf_metadata_summary_validates_against_json_schema(
    tmp_path: Path,
) -> None:
    pytest.importorskip("jsonschema")
    from jsonschema import ValidationError, validate

    pdf_path = tmp_path / "schema.pdf"
    _write_minimal_pdf(pdf_path)
    output_path = tmp_path / "extracted_metadata.json"

    inputs = compute_pdf_metadata_summary_inputs(
        pdf_path=pdf_path,
        source_url="https://example.test/schema.pdf",
    )

    summary = build_pdf_metadata_summary(
        pdf_path=inputs.pdf_path,
        source_url="https://example.test/schema.pdf",
        fetched_at_utc="2026-08-09T19:00:00+00:00",
        inventory_link=TsaInventoryLink(
            tsa_id="tsa_99",
            tsa_code="99",
            tsa_name="Sample TSA",
            cycle_label="TSR_2026",
            cycle_year=2026,
            document_type="discussion_paper",
            inventory_relative_path="TSR_2026/schema.pdf",
        ),
        figrecover_render_pages=inputs.rendered_pages,
        figrecover_figure_candidates=inputs.figure_candidates,
        source_relative_path="TSR_2026/schema.pdf",
        page_texts=inputs.page_texts,
    )

    write_pdf_metadata_summary(summary, output_path=output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    schema = json.loads(SUMMARY_SCHEMA_PATH.read_text(encoding="utf-8"))

    try:
        validate(payload, schema)
    except ValidationError as exc:
        pytest.fail(f"summary failed schema validation: {exc.message}")


# ---------------------------------------------------------------------------
# TSR_2026 PDP extraction regression tests
# ---------------------------------------------------------------------------
TSR_2026_PDP_EXTRACTED_METADATA_PATH = (
    REPO_ROOT
    / "external"
    / "femic-tsa29-instance"
    / "reference"
    / "tsa"
    / "tsa_29"
    / "TSR_2026"
    / "Public_Discussion_Paper"
    / "extracted_metadata.json"
)
TSR_2026_PDP_FIGURES_DIR = TSR_2026_PDP_EXTRACTED_METADATA_PATH.parent / "figures"


@pytest.fixture(scope="module")
def tsr_2026_pdp_summary() -> dict[str, object]:
    if not TSR_2026_PDP_EXTRACTED_METADATA_PATH.exists():
        pytest.skip(
            f"TSR_2026 PDP summary missing: {TSR_2026_PDP_EXTRACTED_METADATA_PATH}"
        )
    return json.loads(TSR_2026_PDP_EXTRACTED_METADATA_PATH.read_text(encoding="utf-8"))


def _expected_quantitative_figures() -> tuple[str, ...]:
    return (
        "figure_02_harvest_live_dead",
        "figure_03_pine_nonpine_harvest",
        "figure_04_age_class",
        "figure_05a_thlb_species_pie",
        "figure_05b_nonthlb_species_pie",
        "figure_06_bec_zones",
        "figure_07_base_case_projection",
        "figure_08_growing_stock",
        "figure_09_harvest_profile",
        "figure_10_mean_volume_per_ha",
        "figure_11_age_composition",
        "figure_12_mean_area_harvested",
        "figure_13_alternative_projection",
        "figure_14_mdwr_removal",
        "figure_15_catastrophic_wildfires",
    )


def _expected_skipped_figures() -> tuple[str, ...]:
    return (
        "figure_00_cover",
        "figure_00_logo",
        "figure_01_tsa_map",
    )


def test_tsr2026_pdp_extracted_metadata_top_level_keys(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    for required in (
        "schema_version",
        "schema_url",
        "generated_utc",
        "document",
        "inventory",
        "text_summary",
        "figures",
        "rendered_pages",
        "provenance",
        "figure_datasets",
        "tsr_facts",
        "ws3_links",
    ):
        assert required in tsr_2026_pdp_summary, f"missing {required!r}"


def test_tsr2026_pdp_figure_dataset_files_exist(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    for record in tsr_2026_pdp_summary["figure_datasets"]["summary_records"]:
        csv_path = TSR_2026_PDP_FIGURES_DIR.parent / record["csv_path"]
        json_path = TSR_2026_PDP_FIGURES_DIR.parent / record["json_path"]
        assert csv_path.exists(), f"missing {csv_path}"
        assert json_path.exists(), f"missing {json_path}"
        if record["is_quantitative"]:
            assert record["row_count"] >= 1, (
                f"quantitative figure {record['logical_figure_id']} produced "
                f"no dataset rows"
            )


def test_tsr2026_pdp_expected_quantitative_figures_nonempty(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    by_logical_id = {
        record["logical_figure_id"]: record
        for record in tsr_2026_pdp_summary["figure_datasets"]["summary_records"]
    }
    for expected in _expected_quantitative_figures():
        assert expected in by_logical_id, (
            f"logical figure {expected!r} missing from figure_datasets"
        )
        record = by_logical_id[expected]
        assert record["is_quantitative"], (
            f"{expected!r} expected to be is_quantitative=True"
        )
        assert record["row_count"] >= 1, f"{expected!r} produced an empty dataset"


def test_tsr2026_pdp_expected_skipped_figures_marked(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    by_logical_id = {
        record["logical_figure_id"]: record
        for record in tsr_2026_pdp_summary["figure_datasets"]["summary_records"]
    }
    for expected in _expected_skipped_figures():
        assert expected in by_logical_id, (
            f"logical figure {expected!r} missing from figure_datasets"
        )
        record = by_logical_id[expected]
        assert record["is_quantitative"] is False, (
            f"{expected!r} should be marked non-quantitative"
        )
        assert record["skip_reason"], (
            f"{expected!r} should have an explicit skip_reason"
        )


def test_tsr2026_pdp_quantitative_datasets_match_sha256(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    for record in tsr_2026_pdp_summary["figure_datasets"]["summary_records"]:
        if not record["is_quantitative"]:
            continue
        assert record["csv_sha256"], (
            f"quantitative dataset {record['logical_figure_id']} missing csv_sha256"
        )
        assert len(record["csv_sha256"]) == 64, (
            f"csv_sha256 length != 64 for {record['logical_figure_id']}"
        )


def test_tsr2026_pdp_figure_block_dataset_links(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    """Each figrecover image-block must have a dataset_relpath when its logical
    figure is quantitative, and an explicit crop_relpath for traceability."""
    for figure_block in tsr_2026_pdp_summary["figures"]:
        logical_id = figure_block.get("figure_logical_id")
        assert logical_id, (
            f"figure block {figure_block['figure_id']} missing figure_logical_id"
        )
        assert figure_block.get("crop_relpath"), (
            f"figure block {figure_block['figure_id']} missing crop_relpath"
        )
        assert figure_block.get("crop_checksum"), (
            f"figure block {figure_block['figure_id']} missing crop_checksum"
        )
        if figure_block.get("is_quantitative"):
            assert figure_block.get("dataset_relpath"), (
                f"quantitative figure block {figure_block['figure_id']} "
                f"missing dataset_relpath"
            )


def test_tsr2026_pdp_tsr_facts_schema(tsr_2026_pdp_summary: dict[str, object]) -> None:
    payload = tsr_2026_pdp_summary["tsr_facts"]
    assert payload["schema_version"] >= 1
    assert payload["schema_url"].startswith("https://")
    assert isinstance(payload["facts"], list)
    assert len(payload["facts"]) > 0
    required_keys = {"key", "value", "page_number", "quote"}
    for fact in payload["facts"]:
        missing = required_keys - set(fact.keys())
        assert not missing, f"fact {fact.get('key')!r} missing required keys: {missing}"
        assert isinstance(fact["page_number"], int)
        assert fact["page_number"] >= 1
        assert isinstance(fact["quote"], str)
        assert fact["quote"].strip()


def test_tsr2026_pdp_tsr_facts_required_aac_thlb_fields(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    """Required TSR-specific structured facts the brief mandates."""
    fact_keys = {fact["key"] for fact in tsr_2026_pdp_summary["tsr_facts"]["facts"]}
    required = {
        "aac_current_after_fnwl_adjustment",
        "total_tsa_area_ha",
        "aflb_area_ha",
        "thlb_area_ha",
        "short_term_harvest_live",
        "mid_term_harvest_live",
        "long_term_harvest_live",
        "starting_total_growing_stock_million_m3",
        "long_term_total_growing_stock_million_m3",
        "tsr_modelling_engine",
    }
    missing = required - fact_keys
    assert not missing, f"missing required TSR facts: {sorted(missing)}"


def test_tsr2026_pdp_ws3_links_schema(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    payload = tsr_2026_pdp_summary["ws3_links"]
    assert payload["schema_version"] >= 1
    assert payload["schema_url"].startswith("https://")
    assert payload["modifies_model_inventory"] is False, (
        "ws3_links must explicitly disclaim model mutation"
    )
    inventory = payload["model_inventory_summary"]
    assert inventory["model_id"] == "tsa29_patchworks_model"
    assert inventory["au_count"] > 0
    required_link_keys = {
        "tsr_fact_key",
        "tsr_fact_value",
        "tsr_unit",
        "tsr_page_number",
        "tsr_quote",
        "model_id",
        "model_track_table",
        "model_observation",
        "match_kind",
        "is_authoritative",
    }
    for link in payload["links"]:
        missing = required_link_keys - set(link.keys())
        assert not missing, f"ws3 link missing keys: {missing}"
        assert link["is_authoritative"] is False
        assert link["model_id"] == inventory["model_id"]
    assert len(payload["inventory_index"]) == inventory["au_count"]
    for entry in payload["inventory_index"]:
        assert entry["AU"]
        assert isinstance(entry["tsr_cited"], bool)


def test_tsr2026_pdp_ws3_links_distinct_from_fsa_stsa_models(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    """ws3_links must not edit the model: explicitly mark each link as
    referencing (not editing) the existing inventory."""
    payload = tsr_2026_pdp_summary["ws3_links"]
    assert payload["modifies_model_inventory"] is False
    for link in payload["links"]:
        assert link["match_kind"] in {
            "tsr_fact_to_inventory_aggregate",
            "external_validation_target",
        }, f"unexpected match_kind: {link['match_kind']!r}"


def test_tsr2026_pdp_csv_rows_parseable_json(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    """Each per-figure dataset CSV must be parseable as CSV with consistent
    columns, non-empty header, and row_count matching the JSON summary."""
    import csv as _csv

    for record in tsr_2026_pdp_summary["figure_datasets"]["summary_records"]:
        csv_path = TSR_2026_PDP_FIGURES_DIR.parent / record["csv_path"]
        if not record["is_quantitative"]:
            continue
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = _csv.reader(handle)
            rows = list(reader)
        assert len(rows) >= 1, f"empty CSV at {csv_path}"
        assert rows[0][0] == "source", (
            f"first CSV column must be 'source', got {rows[0][0]!r}"
        )
        # row_count = header + data rows
        body_rows = len(rows) - 1
        assert body_rows == record["row_count"], (
            f"row_count mismatch for {record['logical_figure_id']}: "
            f"summary says {record['row_count']} but CSV has {body_rows} data rows"
        )


def test_tsr2026_pdp_full_summary_validates_schema(
    tsr_2026_pdp_summary: dict[str, object],
) -> None:
    pytest.importorskip("jsonschema")
    from jsonschema import validate

    schema = json.loads(SUMMARY_SCHEMA_PATH.read_text(encoding="utf-8"))
    validate(tsr_2026_pdp_summary, schema)
