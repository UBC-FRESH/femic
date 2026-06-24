# Phase 75: `bcdata` and `designatedlands` Evaluation Notes

## Objective

Evaluate whether the R package `bcdata` and the BC Gov `designatedlands`
workflow should inform or extend FEMIC's BC Data Catalogue discovery and
source-layer groking workflow. This is a parent FEMIC data-discovery lane, not a
TFL 6 instance source-materialization task.

The governing issue is `UBC-FRESH/femic#201`.

## Current FEMIC Surfaces to Compare

| Lane | Python surface | CLI surface | Output to compare |
| --- | --- | --- | --- |
| Catalogue resolve | `src/femic/bcdc_catalog.py::resolve_bcdc_candidates` | `femic data bcdc-resolve` | `BcdcResolveResult`, top match, ranked matches, resource classifications, WFS hints, direct-download candidates, manual follow-up notes. |
| Direct download | `src/femic/bcdc_catalog.py::download_direct_bcdc_resources` | `femic data bcdc-resolve --download-direct` | `BcdcDownloadResult`, downloaded resources, skipped resources, failures, destination paths. |
| AOI WFS fetch | `src/femic/bcdc_fetch.py::fetch_bcdc_wfs_data` | `femic data bcdc-fetch` | `BcdcFetchResult`, selected WFS resource, typename, request URL, output format, feature count, AOI source, warnings. |
| DWDS order | `src/femic/bcdc_dwds.py::submit_bcdc_dwds_order` | `femic data bcdc-order` | `BcdcDwdsOrderResult`, selected feature type, request payload, order ID/GUID, status probe, warnings. |
| DWDS follow-up | `src/femic/bcdc_dwds.py::follow_up_bcdc_dwds_order` | `femic data bcdc-order-followup` | Updated order manifest, pickup/download URL, materialized artifact path, content type, byte count, follow-up warnings. |

FEMIC already writes JSON manifests for the catalogue, WFS, and DWDS lanes and
CSV summary output for catalogue resolve. P75.2 should reuse those output shapes
as the FEMIC side of the comparison rather than inventing a second FEMIC result
format.

## Candidate Comparison Corpus

Use fixed queries that represent real modelling discovery pressure:

| ID | Theme | Primary query strings | Expected evidence |
| --- | --- | --- | --- |
| `p75_q01_tfl6_boundary` | TFL 6 administrative boundary | `Tree Farm Licence 6`; `TFL 6`; `WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE_POLY_SVW` | Whether each tool finds the current managed licence / TFL boundary candidate and exposes a usable BCGW object or service. |
| `p75_q02_fadm_boundary` | FADM administrative boundaries | `FADM_TSA`; `forest administrative boundaries`; `WHSE_ADMIN_BOUNDARIES.FADM_TSA` | Exact-object-name handling, admin-boundary family suggestions, and direct/WFS/DWDS availability. |
| `p75_q03_ogma` | Old growth management areas | `old growth management area`; `OGMA`; `WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW`; `WHSE_LAND_USE_PLANNING.RMP_OGMA_NON_LEGAL_CURRENT_SVW` | Current legal/non-legal OGMA discoverability and whether designated-lands manifests identify equivalent or better source references. |
| `p75_q04_rmz` | Riparian management zone candidates | `riparian management zone`; `RMZ`; `riparian`; `stream riparian` | Whether a public polygon source exists or whether the tools only surface hydrography/buffer ingredients. |
| `p75_q05_shoreline` | Shoreline/coastline/ocean adjacency | `shoreline`; `coastline`; `BC coastline`; `NTS coastline`; `ocean shoreline` | Whether candidate coastline/shoreline layers are ranked clearly enough for a 40 m ocean-shoreline teaching proxy. |
| `p75_q06_dem_terrain` | DEM and slope-derived operability inputs | `digital elevation model`; `DEM`; `BC DEM`; `terrain resource information management`; `slope` | Whether discovery surfaces DEM or terrain products suitable for AOI-clipped slope raster construction. |
| `p75_q07_vri_inventory` | VRI L1R1 and VDYP source products | `VRI L1R1`; `vegetation resources inventory`; `special VDYP`; `WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY` | Whether current VRI polygon and related VDYP packages are visible, downloadable, or require manual/data mirror handling. |
| `p75_q08_roads` | Road-network inputs | `Digital Road Atlas`; `DRA`; `roads`; `WHSE_BASEMAPPING.DRA_DGTL_ROAD_ATLAS_MPAR_SP` | Whether road-line candidates and service/download forms are correctly classified. |
| `p75_q09_hydrography` | Freshwater atlas inputs | `Freshwater Atlas`; `FWA streams`; `FWA lakes`; `FWA wetlands` | Whether hydrography ingredients for riparian buffers are discoverable and automatable. |
| `p75_q10_bec_lu` | BEC and landscape units | `BEC`; `biogeoclimatic`; `landscape unit`; `WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY`; `WHSE_LAND_USE_PLANNING.RMP_LANDSCAPE_UNIT_SVW` | Whether object-name aliases and keyword search rank the modelling-support layers correctly. |
| `p75_q11_designated_lands` | Protected/designated lands | `designated lands`; `protected areas`; `conservation lands`; `land act reserves`; `wildlife habitat area`; `ungulate winter range` | Whether `bcdata`, FEMIC, and `designatedlands` source CSVs converge on the same designation source families and restriction metadata. |
| `p75_q12_download_edge_cases` | Known resolver edge cases | `SITE_PROD_BC`; `Silviculture Activities History`; `CONSOLIDATED_CUTBLOCKS_2011`; `FTEN_MANAGED_LIC` | Regression coverage for direct download, multi-word quoted query handling, stale object-name aliases, and generated replacement-family aliases. |

P75.2 should use a small TFL 6 / northern Vancouver Island EPSG:3005 bbox for
fetch/order smoke comparisons when an AOI is required. The exact bbox can be
recorded in the comparison manifest; it should not be treated as a model AOI
contract.

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

Minimum comparison columns:

| Column | Meaning |
| --- | --- |
| `query_id` | Stable corpus ID from the table above. |
| `query_text` | Literal search string passed to the tool. |
| `tool` | `femic_resolve`, `femic_fetch`, `femic_dwds`, `bcdata_search`, `bcdata_get_data`, `designatedlands_manifest`, or another reviewed tool label. |
| `command_or_script` | Exact command, Python call, or R expression used to generate the row. |
| `status` | `exact_hit`, `strong_hit`, `weak_hit`, `no_hit`, `manual_only`, `error`, or `not_applicable`. |
| `top_title` | Top-ranked dataset/title returned by the tool. |
| `top_object_name` | BCGW object name or equivalent source identifier, if exposed. |
| `top_url` | Dataset page, metadata URL, service URL, or source-manifest URL. |
| `rank_of_expected` | 1-based rank of the expected authoritative candidate, or blank if not found. |
| `resource_classes` | Normalized resource classes found by the tool. |
| `wfs_queryable` | Whether a WFS/geodata query path is available. |
| `direct_download` | Whether a direct-download path is available. |
| `dwds_candidate` | Whether a BCGW/DWDS fallback path is available. |
| `manual_download` | Whether the tool/source manifest says manual acquisition is required. |
| `runtime_seconds` | Wall-clock time for the query or manifest extraction. |
| `notes` | Short review note, including failure reason or useful adoption clue. |

Artifacts for P75.2 should be written under `runtime/phase75/` and should stay
out of commits unless a later roadmap item explicitly accepts small reviewed
fixtures. The repo-tracked deliverable for P75.2 is the comparison summary, not
raw live-query output.

## P75.1 Contract Status

P75.1 is complete when:

- the FEMIC comparison surfaces are named;
- the query corpus above is treated as the initial fixed corpus;
- the metric columns above are treated as the comparison schema;
- `designatedlands` is scoped as source-manifest/workflow-pattern evidence; and
- P75.2 is the next executable step.

## Integration Options

Evaluate `bcdata` options in order:

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

Evaluate `designatedlands` separately:

1. Mine its source CSV tables as a curated manifest of designation-related
   source layers.
2. Use its overlay/restriction-class logic as a recipe-design reference.
3. Add optional FEMIC helper code only for specific reusable pieces that do not
   force a heavy runtime dependency.
4. Do not vendor or require the full workflow unless a later decision accepts
   its PostGIS, GDAL, and processing footprint.

`designatedlands` is better treated as a source-manifest and workflow-pattern
candidate than as a drop-in resolver. Its full processing stack is materially
heavier than FEMIC's existing BCDC resolver because it expects command-line
GDAL and a PostGIS-enabled PostgreSQL database.

## Non-Goals

- Do not replace FEMIC's existing BCDC resolver before the comparison is done.
- Do not add R as an unconditional core FEMIC dependency without an explicit
  decision.
- Do not add a PostGIS/GDAL designated-lands processing dependency to FEMIC
  without an explicit decision.
- Do not start TFL 6 source-layer extraction from this phase.
- Do not promote `bcdata` results into model-instance contracts without normal
  instance review.
- Do not promote `designatedlands` restriction classes into a model-instance
  THLB contract without normal instance review.
