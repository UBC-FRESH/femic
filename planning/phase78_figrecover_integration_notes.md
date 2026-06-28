# Phase 78 `figrecover` Integration Notes

## Purpose

Phase 78 plans explicit integration of the UBC-FRESH `figrecover` package into
FEMIC document-ingestion workflows. The immediate motivation is the TFL 6 MP11
PDF package, which contains figure evidence that may need auditable
figure-derived tables before the TFL 6 model-overhaul lane can compare MP11
outputs against the Phase 5 prototype.

The integration target is not automatic truth extraction. FEMIC should use
`figrecover` to prepare, recover, review, and register approximate figure data
with enough provenance that maintainers can decide later whether a recovered
value is suitable for planning, comparison, sensitivity analysis, or model
input work.

## Package Boundary

`figrecover` remains a separate UBC-FRESH package. FEMIC should integrate it as
an optional document-ingestion dependency:

- normal FEMIC installation must not require `figrecover`;
- THLB, VDYP, TIPSY, BatchTIPSY, Patchworks, and instance-scaffold workflows
  must continue to run without `figrecover`;
- any FEMIC command that needs `figrecover` must fail clearly when the optional
  dependency is missing; and
- dependency adoption should use a FEMIC optional extra, such as
  `femic[figures]`, only after the package footprint is accepted.

The first attempted local install from the GitHub repository timed out and did
not leave `figrecover` installed in the active FEMIC virtual environment. Treat
dependency installation as open P78.2 work, not as completed setup.

## Planned FEMIC Surfaces

Phase 78 should add a small wrapper layer rather than copying `figrecover`
internals into FEMIC.

Candidate CLI/API surfaces:

- `femic doc figures preflight`
  - report whether `figrecover` and its PDF/image extras are importable;
  - report package version and optional backend availability;
  - avoid downloading or processing documents.
- `femic doc figures prepare-corpus`
  - call the `figrecover` corpus/PDF preparation layer;
  - render public PDF pages or prepare page manifests;
  - write an auditable figure-candidate manifest.
- `femic doc figures register-table`
  - register a reviewed recovered CSV/JSON table with FEMIC provenance;
  - record page, figure, source, calibration, extraction method, and review
    status;
  - keep raw recovered data separate from accepted model contracts.
- `femic doc figures export-reviewed`
  - export only reviewed/accepted recovered tables for downstream planning or
    instance-specific comparison lanes.

The exact command names can change during implementation, but the separation
between preparation, recovery/review, registration, and accepted export should
remain.

## Artifact Convention

Use ignored runtime/local paths for generated document artifacts by default.
Instance repositories can mirror the convention under their own ignored
runtime area.

Proposed generic layout:

```text
runtime/document_ingestion/<corpus_id>/
  source_manifest.yaml
  pages/
  figure_candidates.csv
  crops/
  calibration/
  recovered/
  overlays/
  review_manifest.jsonl
  accepted/
```

Tracked planning files should contain compact manifests, checksums, review
summaries, and accepted crosswalks. They should not contain bulky rendered
pages, crops, overlays, prompt logs, private PDFs, or unreleased recovered
tables unless the data are public-safe and intentionally approved for
publication.

## Required Provenance Fields

Recovered figure data cannot be used as FEMIC evidence unless the registration
record includes:

- corpus ID;
- source URL or source path;
- source checksum where a local copy exists;
- document title or package component;
- page number;
- figure/table identifier where available;
- crop path or crop checksum;
- axis calibration specification;
- series name and visual selection rule;
- `figrecover` version;
- extraction method and parameters;
- output file checksum;
- reviewer and review timestamp when promoted beyond raw extraction;
- review status; and
- downstream use classification.

Suggested review-status vocabulary:

- `raw_extraction`;
- `needs_calibration_review`;
- `needs_value_review`;
- `reviewed_for_planning`;
- `accepted_for_comparison`;
- `accepted_for_model_input`;
- `rejected`;
- `superseded`.

## TFL 6 MP11 Pilot Boundary

The first pilot should align with the TFL 6 instance Phase 6 issue tree:

- `UBC-FRESH/femic-tfl6-instance#42`: Phase 6 parent.
- `UBC-FRESH/femic-tfl6-instance#43`: MP11 source package and extraction
  manifest.
- `UBC-FRESH/femic-tfl6-instance#44`: MP11 tables, figures, sections,
  assumptions, and metadata extraction.

The parent FEMIC pilot should prove that the wrapper can:

- prepare a public PDF corpus manifest for the MP11 package;
- identify a small set of figure candidates with page anchors;
- record deterministic provenance and tool versions;
- keep recovered values out of accepted model contracts until reviewed; and
- hand off compact manifest records to the TFL 6 instance planning lane.

The pilot must not:

- perform the full MP11 extraction;
- rebuild TFL 6 THLB, yield curves, model inputs, or Patchworks runtime
  artifacts;
- claim WFP-model equivalence; or
- treat approximate figure recovery as an approved AAC or operational model
  source without review.

## Implementation Sequence

1. P78.1: finalize this integration boundary and issue/roadmap placement.
2. P78.2: add optional dependency packaging and preflight checks.
3. P78.3: implement artifact-path and provenance-record helpers.
4. P78.4: add wrapper CLI/API commands with synthetic/public-safe tests.
5. P78.5: run a small TFL 6 MP11 pilot manifest and hand off findings to the
   TFL 6 instance Phase 6 lane.
6. P78.6: document the workflow and run focused validation.

## Execution Environment Notes

The local Windows FEMIC environment is sufficient for P78.2 packaging and
import-preflight work. Heavier P78.3 through P78.5 work should preferentially
run on the available Ubuntu server with 72 Xeon cores, 768 GB RAM, and the
96 GB NVIDIA RTX Pro 6000 Blackwell GPU. That server is the better place for
large MP11 page rendering, crop generation, VLM-assisted figure metadata
review, and batch extraction pilots. Any server-side workflow must still write
portable manifests and avoid committing bulky runtime pages, crops, overlays,
prompt logs, or unreleasable recovered tables.

## Validation Expectations

Before any P78 implementation milestone closes:

- run focused unit tests for new code;
- run Sphinx warning-clean if docs change;
- search new docs/planning surfaces for personal local paths;
- verify commands fail clearly when `figrecover` is absent; and
- verify recovered values cannot silently bypass review status into accepted
  model-input surfaces.
