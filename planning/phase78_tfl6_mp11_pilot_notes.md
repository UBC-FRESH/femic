# Phase 78 TFL 6 MP11 Pilot Notes

## Purpose

This note records the first public-safe FEMIC pilot manifest for using
`figrecover` against the TFL 6 Management Plan 11 PDF package. The pilot is a
figure-candidate planning artifact only. It does not recover values, approve
values, or change FEMIC model inputs.

## Source

- Source URL:
  `https://www.westernforest.com/wp-content/uploads/2026/06/TFL6_MP_11_202606_w_Appendices_Web-compressed.pdf`
- Local source copy used for pilot scanning:
  `/home/gep/projects/figrecover/examples/TFL6_MP_11_202606_w_Appendices_Web-compressed.pdf`
- SHA256:
  `44591c1024254e36d8989df45a2b489a624d5669c5ae01a6ebfd961b50a7321b`
- PDF page count from PyMuPDF:
  `475`

## Pilot Manifest

The compact candidate manifest is:

- `planning/phase78_tfl6_mp11_pilot_figure_manifest.csv`

The manifest selects a small set of high-value figures for later recovery
experiments:

- base-case harvest flow;
- growing-stock trajectories;
- harvest by era and seral-stage classes;
- age-class distribution;
- harvest statistics;
- old-seral landscape-unit trajectories;
- harvest-flow sensitivity scenarios; and
- yield-adjustment method examples.

These candidates align with:

- `UBC-FRESH/femic-tfl6-instance#42`: Phase 6 parent;
- `UBC-FRESH/femic-tfl6-instance#43`: MP11 source package and extraction
  manifest; and
- `UBC-FRESH/femic-tfl6-instance#44`: MP11 tables, figures, sections,
  assumptions, and metadata extraction.

## Runtime Trial

The P78.4 `prepare-corpus` wrapper was exercised against selected public MP11
pages:

```bash
PYTHONPATH=src python - <<'PY'
from typer.testing import CliRunner
from femic.cli.main import app

args = [
    "doc", "figures", "prepare-corpus", "tfl6-mp11-pilot",
    "--pdf",
    "/home/gep/projects/figrecover/examples/TFL6_MP_11_202606_w_Appendices_Web-compressed.pdf",
    "--pages", "82-86,91,98-100,103,116,123",
    "--dpi", "150",
    "--output-root", "runtime/document_ingestion/tfl6-mp11-pilot",
    "--overwrite",
]
result = CliRunner().invoke(app, args)
print(result.stdout)
raise SystemExit(result.exit_code)
PY
```

The command rendered `12` page images and wrote:

- `runtime/document_ingestion/tfl6-mp11-pilot/source_manifest.yaml`
- `runtime/document_ingestion/tfl6-mp11-pilot/pages/*.png`

These runtime artifacts are intentionally ignored and should not be committed.

## Private-Data Hygiene

The MP11 source package is public, but rendered pages, future crops, overlays,
prompt logs, recovered raw tables, and review bundles remain generated runtime
artifacts. Only compact public-safe planning manifests and review summaries
should be tracked unless a maintainer explicitly approves a sanitized artifact.

## Next Steps

- Hand off the pilot manifest to the TFL 6 instance Phase 6 issue tree.
- Use `figrecover` directly for manual crop/calibration experiments on the
  selected figures.
- Register any reviewed recovered tables back through
  `femic doc figures register-table`.
- Keep all recovered values out of accepted FEMIC model-input contracts until
  the TFL 6 instance P6.3-P6.6 review lanes explicitly accept them.
