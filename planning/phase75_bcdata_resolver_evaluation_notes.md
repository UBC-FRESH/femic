# Phase 75: `bcdata` Resolver Evaluation Notes

## Objective

Evaluate whether the R package `bcdata` should inform or extend FEMIC's BC Data
Catalogue discovery workflow. This is a parent FEMIC data-discovery lane, not a
TFL 6 instance source-materialization task.

The governing issue is `UBC-FRESH/femic#201`.

## Current FEMIC Surfaces to Compare

- `src/femic/bcdc_catalog.py`
- `src/femic/bcdc_fetch.py`
- `src/femic/bcdc_dwds.py`
- `femic data bcdc-resolve`
- `femic data bcdc-fetch`
- `femic data bcdc-order`
- `femic data bcdc-order-followup`

## Candidate Comparison Corpus

Use fixed queries that represent real modelling discovery pressure:

- TFL 6 / Tree Farm Licence 6 administrative boundary.
- FADM administrative boundaries.
- Old growth management area / OGMA polygons.
- Riparian management zone / RMZ candidates.
- Shoreline, coastline, ocean adjacency, or NTS coastline candidates.
- DEM and terrain products suitable for slope-derived operability proxies.
- VRI L1R1 polygon and special VDYP source products.
- Digital road atlas / DRA roads.
- Freshwater atlas / FWA hydrography.
- BEC and landscape unit layers used by THLB retention logic.

## Comparison Metrics

For each query, record:

- candidate records returned by FEMIC and `bcdata`;
- first-page ranking and whether the authoritative candidate is obvious;
- resource types and direct-download classification;
- WFS/geodata query availability;
- zipped-resource handling;
- authenticated-record behaviour when applicable;
- runtime and failure modes;
- whether the result is reproducible without hidden local state; and
- whether the output shape is easy to consume from FEMIC.

## Integration Options

Evaluate these in order:

1. Keep FEMIC's resolver as-is and use the comparison only to improve query
   guidance.
2. Use `bcdata` as an optional reference/oracle tool for resolver QA.
3. Add an optional `Rscript` bridge invoked by FEMIC for discovery comparisons.
4. Add a deeper Python-to-R runtime bridge only if it clearly improves
   reliability and is maintainable on Windows and CI.

`reticulate` should not be assumed to be the right bridge. It is primarily an
R-to-Python integration path, while FEMIC would need to call R from Python.
Treat a shell-level `Rscript` helper, `rpy2`, or no integration as candidates
until the comparison shows that a dependency is worth carrying.

## Non-Goals

- Do not replace FEMIC's existing BCDC resolver before the comparison is done.
- Do not add R as an unconditional core FEMIC dependency without an explicit
  decision.
- Do not start TFL 6 source-layer extraction from this phase.
- Do not promote `bcdata` results into model-instance contracts without normal
  instance review.
