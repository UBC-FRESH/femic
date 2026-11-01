# Phase 122: BA-only pilot acceptance

Parent issue: #542

Branch: `feature/p122-ba-pilot-acceptance`

Status: active

## Goal

Verify that the released BA-only pilot is consumer-ready and record an explicit
accept/reject decision with limits.

## Scope

- Read the BA table and raster with the standard Python/rasterio stack.
- Verify schema, CRS, transform, nodata, band description, row/pixel identity,
  value range, and hashes.
- Record coverage and the strict BA validation.
- Record VRI/THLB coverage as unavailable until the instance annex data are
  materialized; do not infer it.
- Write a consumer note and machine-readable acceptance summary.
- Recommend acceptance as an experimental BA layer or rejection with a precise
  next action.

## Out of scope

- Model fitting or refits.
- Height/volume release.
- Operational claims.
- VRI/THLB acquisition or annex repair.
- Tags or GitHub releases.

## Tasks

- [ ] P122.1 Verify consumer readiness and accept or reject (`#543`).
  - [ ] Verify table and raster readability and schema.
  - [ ] Verify row/pixel and value identity.
  - [ ] Write the consumer acceptance note and machine-readable summary.
  - [ ] Update docs, roadmap, changelog, and public instance.
  - [ ] Run gates and open the phase PR.

## Acceptance

- Reader checks pass.
- Consumer note states coverage, error, and exclusions.
- Decision is recorded as accept-experimental or reject.
- Tests and Sphinx pass.
- Phase PR is open.

## Verification

- `PYTHONPATH=src pytest -q tests/test_lidar_inventory.py`
- `sphinx-build -b html docs _build/html -W`
- Python/rasterio checks
- Manifest/default-config hash checks
