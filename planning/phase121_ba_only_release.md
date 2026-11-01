# Phase 121: BA-only TSA 23 pilot release

Parent issue: #539

Branch: `feature/p121-ba-only-release`

Status: active

## Goal

Package the BA-only TSA 23 pilot release from existing artifacts and correct the
P120 closeout record.

## Scope

- Correct `notes/reports/phase120-closeout.md` to record the merged PRs, CI, and
  closed issues.
- Generate a BA-only long table and 25 m raster from the existing full-grid run.
- Record row/pixel counts, coverage, SHA-256, source hashes, and model/config
  hashes.
- Publish the release note and manifest through the parent repository and public
  TSA23 instance.
- Run gates and open the phase pull request.

## Out of scope

- Height or volume release.
- New model fitting.
- Operational claims.
- Forest-level objectives, constraints, growth, or solver changes.
- Tags, GitHub releases, or new acquisition.
- Re-running the full point-cloud pipeline.

## Tasks

- [ ] P121.1 Correct the P120 closeout and package the BA-only release (`#540`).
  - [ ] Correct the P120 closeout.
  - [ ] Generate the BA-only table and raster.
  - [ ] Verify source/BA identities and coverage.
  - [ ] Write the release manifest and validation note.
  - [ ] Update the public instance.
  - [ ] Run gates and open the phase pull request.

## Acceptance

- P120 closeout names `98fe2c6`, instance `3b4f58a`, CI green, and closed issues.
- BA-only products have checksums, row/pixel counts, and 14.9% coverage.
- No out-of-range or extrapolated cells are introduced.
- Tests and Sphinx pass.
- Phase pull request is open for approval.

## Verification

- `PYTHONPATH=src pytest -q tests/test_lidar_inventory.py`
- `sphinx-build -b html docs _build/html -W`
- `rasterio` band/mask checks
- `pandas` row-count checks
- One-row default-config CLI smoke test

## Artifacts

- `notes/reports/phase120-closeout.md`
- `notes/reports/inv01-tsa23-ba-pilot-release.md`
- `metadata/inv01/tsa23_ba_pilot_manifest.json`
