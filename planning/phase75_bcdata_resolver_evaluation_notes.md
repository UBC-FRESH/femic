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

## P75.2a FEMIC Baseline Resolver Run

Baseline artifacts were generated under `runtime/phase75/`:

- `p75_femic_baseline_queries.txt`
- `p75_femic_bcdc_resolve_manifest.json`
- `p75_femic_bcdc_resolve_summary.csv`

These are runtime artifacts, not tracked deliverables. The run used
`femic data bcdc-resolve --plan-only`, which still performs catalogue
resolution and writes resolver manifests, but does not execute downloads,
WFS fetches, or DWDS orders.

Summary from the FEMIC resolver baseline:

| Metric | Count |
| --- | ---: |
| Query rows | 51 |
| Exact hits | 11 |
| Alias hits | 4 |
| Weak text hits | 33 |
| No hits | 3 |
| Rows with WFS-queryable service flag | 29 |
| Rows with direct-download candidates | 12 |
| Rows with BCGW/custom-download candidates | 39 |

No-hit queries:

- `ocean shoreline`
- `special VDYP`
- `Silviculture Activities History`

Clear FEMIC strengths from this baseline:

- exact BCGW object-name queries work well for TFL/FADM/OGMA/VRI/DRA/BEC/LU
  layers;
- curated/generated aliases help important short names, including `BEC`,
  `SITE_PROD_BC`, `CONSOLIDATED_CUTBLOCKS_2011`, and `FTEN_MANAGED_LIC`;
- `Tree Farm Licence 6` surfaces the current FADM TFL view as the top match;
- `WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY` surfaces the 2025 VRI R1 layer;
  and
- the resolver identifies WFS-queryable OpenMaps services for many BCGW
  polygon/line layers.

TFL 6 data-layer challenge findings that should be used as benchmark pressure
against `bcdata`:

- `TFL 6` as a short free-text query is noisy and returns `Moose Management
  Areas - TFL38` as the top match, while `Tree Farm Licence 6` works better.
- RMZ remains unresolved as a reusable TFL 6 source. `riparian management zone`
  and `riparian` find a North Coast/Skeena RMZ buffer source, while `RMZ`
  returns an Old Growth TAP protected-area record.
- Shoreline discovery is only partly successful: `coastline`, `BC coastline`,
  and `NTS coastline` surface the NTS coastline polygon candidate, but
  `shoreline` is noisy and `ocean shoreline` has no hit.
- DEM/terrain discovery is broad rather than operationally precise: `digital
  elevation model`, `DEM`, and `BC DEM` surface LiDAR/LidarBC records, while
  `slope` returns an unrelated Spotted Owl slope-class source.
- VRI discovery is mixed: the exact R1 object-name query finds the 2025 VRI R1
  layer, but `VRI L1R1` and `vegetation resources inventory` surface the
  historical VRI package, and `special VDYP` has no hit.
- FWA free-text discovery is noisy: `Freshwater Atlas`, `FWA streams`, and
  `FWA lakes` all rank wetlands first, and `FWA wetlands` returns a high
  precipitation layer.
- `designated lands` is promising: it returns the province-wide land
  designations spatial data with direct shapefile and GeoPackage download
  candidates.

P75.2b should now run the same query corpus through `bcdata` and compare
whether it improves the real TFL 6 source-layer resolution problems above,
especially RMZ, shoreline/ocean, DEM/slope, VRI/special VDYP, FWA stream/lake
specificity, and short-query TFL 6 ranking.

## P75.2b `bcdata` Baseline Search Run

The `bcdata` side of the comparison was run with:

- `C:\Program Files\R\R-4.5.1\bin\Rscript.exe`
- local runtime R library: `runtime/phase75/r-lib`
- tracked harness: `scripts/phase75_bcdata_resolve_baseline.r`
- query input: `runtime/phase75/p75_femic_baseline_queries.txt`
- runtime outputs:
  - `runtime/phase75/p75_bcdata_search_summary.csv`
  - `runtime/phase75/p75_bcdata_search_manifest.json`

`Rscript` was not on `PATH`, so the run used the explicit R 4.5.1 executable.
The `bcdata` package was installed into the runtime-only library rather than a
user/global R library. The installed `bcdata` version was `0.5.2`.

Summary from the `bcdata` search baseline:

| Metric | Count |
| --- | ---: |
| Query rows | 51 |
| Exact hits | 7 |
| Strong hits | 18 |
| Weak hits | 20 |
| No hits | 6 |
| Rows with WFS-like service flag | 28 |
| Rows with direct-download candidates | 24 |
| Rows with BCGW/DWDS-style candidates | 36 |

No-hit queries:

- `ocean shoreline`
- `special VDYP`
- `SITE_PROD_BC`
- `Silviculture Activities History`
- `CONSOLIDATED_CUTBLOCKS_2011`
- `FTEN_MANAGED_LIC`

Early comparison observations to carry into P75.2c:

- `bcdata` did not improve the noisy short query `TFL 6`; both tools ranked
  `Moose Management Areas - TFL38` first.
- `bcdata` ranked FADM TFL deletion/addition records above the current-view
  TFL layer for `Tree Farm Licence 6`, while FEMIC ranked the current FADM TFL
  view first.
- `bcdata` improved some free-text resource-family discovery:
  - `coastline` ranked `Freshwater Atlas Coastlines`;
  - `digital elevation model` ranked the CDED DEM record;
  - `Freshwater Atlas` ranked rivers;
  - `FWA lakes` ranked lakes; and
  - `FWA wetlands` ranked wetlands.
- `bcdata` did not solve the unresolved TFL 6 RMZ problem. It returned Morice
  FD/Skeena RMZ for `riparian management zone`, and a Lillooet LRMP record for
  `RMZ`.
- `bcdata` did not solve `ocean shoreline` or `special VDYP`; both remained
  no-hit cases.
- `bcdata` performed worse on FEMIC's curated alias/regression cases:
  `SITE_PROD_BC`, `CONSOLIDATED_CUTBLOCKS_2011`, and `FTEN_MANAGED_LIC` were
  no-hit in `bcdata`, while FEMIC resolved them through alias logic.
- `bcdata` ranked approved WHA/UWR records for the corresponding free-text
  queries, while FEMIC ranked proposed records.

P75.2c should turn these run outputs into the formal side-by-side summary and
decide which differences are real adoption signals versus query-tuning or
normalization issues.

## P75.2c Side-by-Side Interpretation

The formal comparison focused on the 42 benchmark rows that directly exercise
the TFL 6 data-layer resolution challenge and the existing FEMIC regression
cases. Outcome counts:

| Outcome | Count | Meaning |
| --- | ---: | --- |
| `bcdata_wins` | 13 | `bcdata` ranked a more obviously relevant top match or gave a stronger match class. |
| `femic_wins` | 7 | FEMIC exact-object-name or alias logic clearly outperformed `bcdata`. |
| `complementary_or_ranking_diff` | 8 | Both found something plausible, but ranked materially different candidates. |
| `similar` | 11 | Both tools produced effectively comparable outcomes. |
| `both_fail` | 3 | Neither tool found a useful candidate. |

High-signal FEMIC wins:

- exact object-name queries remain a FEMIC strength;
- FEMIC ranked the current FADM TFL view first for `Tree Farm Licence 6`, while
  `bcdata` ranked deletion/addition records first;
- FEMIC's curated aliases resolved modelling-specific tokens that `bcdata`
  missed entirely: `SITE_PROD_BC`, `CONSOLIDATED_CUTBLOCKS_2011`, and
  `FTEN_MANAGED_LIC`;
- FEMIC handled `WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY` as the BEC
  Map exact object-name candidate, while `bcdata` ranked the generalized
  1:2M BEC zone layer first; and
- FEMIC preserved the exact DRA master-partially-attributed road layer when the
  exact BCGW object name was supplied.

High-signal `bcdata` wins:

- free-text hydrography discovery was materially better: `Freshwater Atlas`,
  `FWA lakes`, and `FWA wetlands` ranked more relevant FWA family records than
  FEMIC;
- `coastline` ranked `Freshwater Atlas Coastlines`, which may be more useful
  for reproducible shoreline/ocean proxy work than FEMIC's NTS coastline top
  match, depending on scale and intended overlay operation;
- `digital elevation model` ranked the CDED DEM record instead of broad LiDAR
  catalogue records;
- `slope` ranked `RESULTS Openings Slope Aspect and Elevation`, which is more
  semantically relevant than FEMIC's Spotted Owl slope-class record, although
  it is not a stand-alone DEM-to-slope solution;
- `landscape unit` ranked `Landscape Units of British Columbia - Current`,
  while FEMIC ranked a region-specific water-management plan; and
- WHA/UWR free-text queries ranked approved records, while FEMIC ranked
  proposed records.

Cases where neither tool solved the modelling need:

- `ocean shoreline` remained a no-hit in both tools;
- `special VDYP` remained a no-hit in both tools;
- `Silviculture Activities History` remained a no-hit in both tools; and
- neither tool resolved a TFL 6-specific RMZ layer. `bcdata` found Morice/Skeena
  or Lillooet-region RMZ-like records, while FEMIC found North Coast/Skeena or
  Old Growth TAP candidates.

P75.2c interpretation:

- Do not replace FEMIC's resolver with `bcdata`.
- Keep FEMIC's object-name search, alias expansion, and modelling-specific
  replacement-family logic as the core resolver behaviour.
- Treat `bcdata` as evidence for improving FEMIC free-text ranking, especially
  for FWA, DEM/coastline, landscape-unit, WHA, and UWR queries.
- Treat `bcdata` as a useful optional QA oracle or comparison harness candidate,
  not a mandatory runtime dependency.
- The most promising integration work is to port specific ranking/normalization
  lessons into FEMIC, then keep the R harness as optional evidence tooling for
  future resolver audits.
- `designatedlands` still needs separate source-manifest review before any
  claim about designated/protected-land source completeness.

## P75.3 Native Integration Decision

The accepted `bcdata` integration boundary is native Python adoption of useful
discovery/ranking ideas, not an R runtime bridge:

- no mandatory R dependency;
- no `reticulate`;
- no embedded Python-to-R dependency such as `rpy2`;
- no `bcdata` import or shell-out in normal FEMIC resolver paths;
- keep `scripts/phase75_bcdata_resolve_baseline.r` as optional QA/comparison
  evidence only; and
- port high-signal ranking outcomes into `src/femic/bcdc_catalog.py` as curated
  aliases and native scoring behaviour.

The first native resolver improvements are:

- `coastline` -> `WHSE_BASEMAPPING.FWA_COASTLINES_SP`;
- `FWA streams` -> `WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP`;
- `FWA lakes` -> `WHSE_BASEMAPPING.FWA_LAKES_POLY`;
- `FWA wetlands` -> `WHSE_BASEMAPPING.FWA_WETLANDS_POLY`;
- `landscape unit` -> `WHSE_LAND_USE_PLANNING.RMP_LANDSCAPE_UNIT_SVW`;
- `wildlife habitat area` ->
  `WHSE_WILDLIFE_MANAGEMENT.WCP_WILDLIFE_HABITAT_AREA_POLY`;
- `ungulate winter range` ->
  `WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RANGE_SP`; and
- `digital elevation model` / `DEM` -> the CDED DEM title search preference.

Attribution decision:

- credit the BC Government `bcdata` package and the Teucher, Albers, and
  Hazlitt JOSS paper in user-facing Sphinx docs;
- mention in the Python resolver comments that Phase 75 free-text aliases were
  informed by observed `bcdata` search outcomes; and
- do not copy `bcdata` source code into FEMIC.

`designatedlands` remains outside this slice. It should be reviewed as a
source-manifest/workflow-pattern input under P75.3c before any adoption claim.

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
