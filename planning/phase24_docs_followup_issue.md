# Draft GitHub Feature Issue: Phase 24 Docs Follow-up Polish

## Suggested title

Improve native Windows Patchworks runtime docs and SiteProd default-resolution summary

## Suggested labels

- documentation
- developer-experience
- follow-up

## Problem

Phase 24 rebuilt the API docs, added a compact technical-contract layer, and
validated the docs against the core benchmark tasks. The docs are now
functionally sufficient for:

- Patchworks runtime setup
- bundled K3Z rebuild/amend loops
- SiteProd default/fallback orientation
- DataLad/public-data bootstrap

However, two non-blocking friction points remain:

1. Native Windows Patchworks runtime orientation is still spread across:
   - `docs/guides/geospatial-runtime-bootstrap.rst`
   - `docs/guides/cross-platform-runtime-smoke.rst`
   - `docs/reference/api/femic-patchworks-runtime.rst`
2. SiteProd default and fallback behavior is clear, but a maintainer still has
   to synthesize the whole story from:
   - `docs/guides/stage-00-data-prep.rst`
   - `docs/guides/geospatial-runtime-bootstrap.rst`
   - `docs/reference/api/femic-pipeline-siteprod.rst`

## Proposed work

- add a short native Windows Patchworks runtime quickstart/runbook that mirrors
  the current Linux/Wine specificity
- add one compact operator-facing SiteProd resolution-order summary
  (`siteprod.tif` + bandmap -> ArcRasterRescue -> Windows ArcGIS Pro fallback)
- keep both additions in the same main docs tree and wire them into the
  existing contract/guides navigation rather than creating a second docs layer

## Why this is follow-up work, not a Phase 24 blocker

The benchmark validation for `P24.4a` found that current docs are already
sufficient for the target maintenance tasks. These gaps affect speed and
convenience, not successful task completion.
