# P78.7 Single-PDF Metadata Summary Notes

## Purpose

This note captures the P78.7 follow-up to the Phase 78 `figrecover`
integration. The goal is to keep the TSR/TSA29 PDF-discussion-paper lane
deterministic and machine-searchable without forcing every cached TSR
document through a full `prepare-corpus` -> `register-table` build. The
new `femic doc figures summarize-pdf` command emits a single, deterministic
JSON summary so the TSA29 TSR_2026 discussion paper has a trackable
metadata artifact alongside the cached PDF.

## Tool Versions

The summary records versions for the toolchain used during the run:

- `femic`: packaged FEMIC version
- `figrecover`: optional `figrecover` package version (skipped on hosts
  without the optional stack)
- `pymupdf`: optional PyMuPDF version
- `pypdf`: packaged pypdf version

The optional stack was installed into the active FEMIC virtual environment
with `python -m pip install -e ../workspace/figrecover --no-deps` plus
`python -m pip install pymupdf`. This is documented so that future runs
can reproduce the same figure-detection behaviour.

## Command Surface

A new command was added to the `doc figures` CLI to make the summary
workflow match the rest of the `figrecover` integration surface:

```bash
python -m femic doc figures summarize-pdf <pdf-path> \
  --output-path <extracted_metadata.json> \
  --source-url <public-url> \
  --inventory-tsa-id tsa_29 \
  --inventory-tsa-code 29 \
  --inventory-tsa-name "Williams Lake" \
  --inventory-cycle-label TSR_2026 \
  --inventory-cycle-year 2026 \
  --inventory-document-type discussion_paper \
  --inventory-relative-path TSR_2026/Public_Discussion_Paper/29ts_pdp_2026_williams_lake_discussion_paper.pdf \
  --dpi 150
```

## TSA29 TSR_2026 Discussion Paper Run

The first run was executed against:

- local PDF:
  `external/femic-tsa29-instance/reference/tsa/tsa_29/TSR_2026/Public_Discussion_Paper/29ts_pdp_2026_williams_lake_discussion_paper.pdf`
- output JSON:
  `external/femic-tsa29-instance/reference/tsa/tsa_29/TSR_2026/Public_Discussion_Paper/extracted_metadata.json`

The summary reports:

- 29 pages,
- 29 rendered pages,
- 23 figrecover PyMuPDF image-block figure candidates,
- SHA-256:
  `7d114327119ca02c36f8a18f2076c3857672534f2e41a5797c6434b4147e564f`,
- source URL:
  `https://www2.gov.bc.ca/assets/gov/farming-natural-resources-and-industry/forestry/stewardship/forest-analysis-inventory/tsr-annual-allowable-cut/29ts_pdp_2026_williams_lake_discussion_paper.pdf`,
- `figrecover_version`: `0.1.0a1`,
- `pymupdf_version`: `1.28.2`,
- `pypdf_version`: `6.8.0`,
- `femic_version`: `0.2.0a1`.

The rendered pages stay under a temporary `femic-pdf-summary-*` working
directory. The JSON summary itself is small and safe to track alongside the
cached PDF as a public-safe planning artifact.

## Regression Coverage

A new test module, `tests/test_pdf_metadata_summary.py`, validates:

- required top-level keys (`schema_version`, `schema_url`, `generated_utc`,
  `document`, `inventory`, `text_summary`, `figures`, `rendered_pages`,
  `provenance`);
- required document keys including the SHA-256, source URL, fetch timestamp,
  and page count;
- required figure keys when figures are present;
- the canonical default output path layout used for cached TSR PDFs;
- the `summarize-pdf` CLI command via `typer.testing.CliRunner`;
- explicit failure on missing PDF inputs and blank source URLs.

## Acceptance

P78.7 is accepted when:

- the `summarize-pdf` command is exposed under `doc figures`
  (`femic doc figures summarize-pdf --help`);
- a JSON summary is written alongside the TSA29 TSR_2026 discussion paper
  at
  `external/femic-tsa29-instance/reference/tsa/tsa_29/TSR_2026/Public_Discussion_Paper/extracted_metadata.json`;
- the JSON summary parses with `json.loads` and contains all required
  top-level, document, and provenance fields;
- the regression test under `tests/test_pdf_metadata_summary.py` passes;
- `python -m pytest tests/test_pdf_metadata_summary.py` reports all tests
  passing.

## Non-Goals

P78.7 does not:

- rebuild the full TSA29 THLB netdown,
- promote figure candidates into accepted model inputs without review,
- replace the existing `prepare-corpus` + `register-table` review flow,
- touch MASC, WS3, or FHOPS/Nemora repositories.
