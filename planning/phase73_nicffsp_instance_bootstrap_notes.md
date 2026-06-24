# Phase 73 NICF FSP Instance Bootstrap Notes

## Governing Issues

- Parent FEMIC coordination: `UBC-FRESH/femic#199`
- Instance Phase 1 parent issue:
  - `UBC-FRESH/femic-tfl6-instance#4`: Phase 1 bootstrap repository and
    build plan
- Instance Phase 1 child task issues:
  - `UBC-FRESH/femic-tfl6-instance#1`: `P1.2` source-payload inspection
    and normalization
  - `UBC-FRESH/femic-tfl6-instance#3`: `P1.3` K3Z-to-NICF adaptation
    contract
  - `UBC-FRESH/femic-tfl6-instance#2`: `P1.4` cedar, expansion, and
    runtime-package follow-on issue split
  - `UBC-FRESH/femic-tfl6-instance#5`: `P1.5` 2025 VRI source-data
    collection for the NICF base inventory

## Bootstrap Result

The standalone instance repository has been created as
`UBC-FRESH/femic-tfl6-instance` and linked under the parent checkout at
`external/femic-tfl6-instance`.

The initial instance payload is a bootstrap/planning snapshot, not a runnable
Patchworks model package. It includes:

- FEMIC instance scaffold files under `config/`, `runbooks/`, and runtime
  folders;
- modelwright-style workflow surfaces: `AGENTS.md`, `ROADMAP.md`,
  `CHANGE_LOG.md`, and `planning/`;
- raw source payloads under `data/source/nicf_fsp/`; and
- provenance notes for the uploaded AOI, LU, and FSP files.

The instance `AGENTS.md` now makes the modelwright-style issue hierarchy a
hard workflow rule for future phase expansions: one GitHub parent issue per
roadmap phase, one linked child issue per phase task, and third-level
implementation issues only when a task is too large to manage as one child.

## Source Payload Boundary

The uploaded source files are now tracked in the instance repository with
lowercase repo-relative paths:

- `data/source/nicf_fsp/nicf_fsp_amendment_3_spatial.zip`
- `data/source/nicf_fsp/bcgw_lu_clip_2026_06.zip`
- `data/source/nicf_fsp/nicf_forest_stewardship_plan_2020.pdf`

The source zips still need layer-level inspection. Do not treat them as direct
runtime inputs until the authoritative AOI and LU layers have been extracted
and recorded in stable paths.

## Current Edge

Completed bounded move: `P1.2a` inspected
`nicf_fsp_amendment_3_spatial.zip` and recorded the layer inventory in the
instance source inventory. The zip contains one `NICF_FDU_2024` shapefile family
with six valid EPSG:3005 polygon features labeled as FDU/LU records and a
measured total area of about `204162.510 ha`.

Completed bounded move: `P1.2` also inspected `bcgw_lu_clip_2026_06.zip` and
recorded the BCGW LU layer inventory. The zip contains one
`RMP_LU_SVW_polygon` shapefile family with `27` valid EPSG:3005 polygon
features. The six `NICF_FDU_2024` features overlap matching full BCGW LUs named
Holberg, Keogh, Marble, Nahwitti, Shushartie, and Tsulquate, but each FDU
candidate is smaller than the full LU.

Completed bounded move: `P1.2` cross-checked the 2020 FSP PDF. The PDF
identifies three proposed FDUs/LUs: Holberg, Keogh, and Marble. The additional
2024 amendment spatial names Nahwitti, Shushartie, and Tsulquate do not appear
in the extracted 2020 FSP text.

Completed bounded move: `P1.2` accepted the 2024 amendment `NICF_FDU_2024`
layer as the bootstrap AOI source because the project request identifies the
amendment spatial payload as the new AOI. The six FDU/LU features are preserved
as canonical source geometry semantics, while a dissolved whole-AOI polygon is
treated as a generated runtime helper only.

Completed bounded move: `P1.2` extracted the accepted `NICF_FDU_2024` shapefile
family into the lowercase tracked source path
`data/source/nicf_fsp/aoi/nicf_fdu_2024.*` and verified it reads as six valid
EPSG:3005 polygon features with the expected bounds and area.

Correction: the canonical FSP AOI is the provided amendment spatial boundary
filtered to FDU 1 Holberg, FDU 2 Keogh, and FDU 3 Marble only. The six-feature
amendment shapefile remains raw provenance, but the tracked canonical AOI source
is now `data/source/nicf_fsp/aoi/nicf_fsp_aoi.*`, verified as three valid
EPSG:3005 polygon features totaling `147798.392 ha`.

Completed bounded move: `P1.2` extracted the canonical LU reference context.
The full 27-feature BCGW LU zip remains raw provenance, and the tracked
canonical LU reference source is
`data/source/nicf_fsp/lu_reference/nicf_lu_reference.*`, verified as three
valid EPSG:3005 polygon features for Holberg, Keogh, and Marble totaling
`165588.857 ha`.

Completed bounded move: `P1.2` wired `config/run_profile.nicffsp.yaml` to the
accepted source paths. `selection.boundary_path` now points to
`data/source/nicf_fsp/aoi/nicf_fsp_aoi.shp`, and
`selection.source_context.lu_reference_path` records
`data/source/nicf_fsp/lu_reference/nicf_lu_reference.shp`.

Next bounded move: start `P1.3` / `#3` by comparing the K3Z config,
model-input bundle, docs, and Patchworks package structure against the accepted
NICF FSP source boundary.

Completed bounded move: `P1.3a` compared the K3Z template surfaces against the
NICF scaffold and recorded the findings in
`external/femic-tfl6-instance/planning/k3z_template_adaptation.md`. K3Z can
carry forward repository shape, rebuild-spec discipline, model-input bundle
contract, and Patchworks package layout, but its generated bundle tables,
Patchworks tracks, treatment variants, TIPSY rules, and runtime paths are not
accepted NICF semantics. NICF still lacks a model-input bundle and Patchworks
package, and `config/patchworks.runtime.windows.yaml` remains a K3Z-shaped
placeholder until the P1.4 runtime-package lane.

Next bounded move: continue `P1.3` / `#3` by defining the first NICF
run-profile boundary beyond source paths, especially stratification, VDYP
sampling/rebinning, and managed-curve defaults.

Completed bounded move: `P1.3b` defined the first NICF run-profile boundary in
`external/femic-tfl6-instance/config/run_profile.nicffsp.yaml`. The profile
now uses subzone BEC grouping, two-species combinations, TM second-species
fallback, `0.90` area coverage, clean first-compile mode (`resume: false`),
complete VDYP sampling, two-pass rebinning, `10` minimum stands per SI bin, and
`managed_curve_mode: tipsy`. The decision is recorded in
`external/femic-tfl6-instance/planning/k3z_template_adaptation.md`.

Next bounded move: continue `P1.3` / `#3` by separating K3Z assumptions into
carry-forward versus FRST 558 review-required lists before any model-input
bundle generation starts.

Completed bounded move: `P1.3c` separated K3Z carry-forward assumptions from
FRST 558 review-required assumptions in
`external/femic-tfl6-instance/planning/k3z_template_adaptation.md`. K3Z
structure, run-profile mechanics, bundle table contracts, and package layout
are accepted as structural carry-forward assumptions. K3Z TIPSY rules,
treatment variants, cedar signals, expansion candidate rules, seral objectives,
product/account targets, and baseline acceptance metrics require FRST 558
review before implementation.

Next bounded move: continue `P1.3` / `#3` by identifying the minimum
source-derived model-input surfaces needed before P1.4 runtime-package issue
bodies can be finalized.

Completed bounded move: `P1.3` accepted the first K3Z-to-NICF adaptation
boundary. `external/femic-tfl6-instance/planning/k3z_template_adaptation.md`
now records the minimum source-derived model-input surfaces needed before
Patchworks runtime-package work: accepted AOI, LU/FDU context, AOI-clipped
inventory checkpoint, AU diagnostics, bundle tables, managed/natural curve
evidence, managed/unmanaged and origin fields, and baseline acceptance summary.
It also records P1.4 handoff terms for cedar-signal, expansion-candidate, and
runtime-package issue bodies.

Queued bounded move: `P1.5` / `#5` now tracks materialization of the latest
2025 provincial VRI source packages before NICF base AOI inventory extraction
depends on them. The required sources are the 2025 VRI layer 1 rank 1 polygon
package and the 2025 VDYP7 input polygon/layer package, targeted under
`external/femic-public-data/data/bc/vri/2025/` following the existing 2019 and
2024 public-data convention.

Next bounded move: start `P1.5` / `#5` by recording official package metadata
and confirming the accepted public-data materialization convention. Resume
`P1.4` / `#2` follow-on issue splitting after the new source-data dependency is
explicit.

Completed bounded move: `P1.5a` recorded the official 2025 VRI source metadata
in `external/femic-tfl6-instance/planning/vri_2025_data_collection.md`. The
metadata snapshot includes BCDC titles, package ids, package UUIDs, resource
ids, resource names, modified timestamps, formats, and direct package URLs for
the 2025 R1 polygon package and the 2025 VDYP7 polygon/layer package. Package
size, checksum, read-smoke, and DataLad/git-annex/publication status remain
open for the materialization step.

Next bounded move: continue `P1.5` / `#5` by materializing the two 2025 source
archives under the accepted `external/femic-public-data/data/bc/vri/2025/`
convention and recording checksum/read-smoke evidence.

Completed bounded move: `P1.5b` materialized the two 2025 VRI source archives
under `external/femic-public-data/data/bc/vri/2025/`. The R1 archive is
`4168172794` bytes and the VDYP7 polygon/layer archive is `403304406` bytes.
Both zip archives passed CRC validation. The public-data commit carrying the
annex pointer files is `348d9b60529e3a0160672048fc33e4083f2128fb`; current
`git annex whereis` reports one local copy for each archive. Arbutus/public
remote publication and full geodatabase read-smoke evidence remain open.

Next bounded move: continue `P1.5` / `#5` by running read smoke on the
materialized 2025 geodatabases and recording layer names, feature-count
evidence, CRS, and the extraction/runtime path decision.

Source lookup: found the requested TFL 6 Management Plan 10 timber supply
analysis information package at the BC TFL management-plan document surface and
stored a local copy at
`external/femic-tfl6-instance/data/source/nicf_fsp/reference/tfl_6_management_plan_10_information_package_2011.pdf`.
The PDF verifies as 126 pages, `2183218` bytes, SHA-256
`302b4ce948a2cb765ec6a451157963422e9b8f102647d6b71864235e3bdb38e7`, with
extracted text confirming TFL 6, Management Plan #10, Timber Supply Analysis
Information Package, and February 2011.

AOI pivot planning update: the active NICF teaching-case AOI is now TFL 6 rather
than the original FDU 1/2/3 bootstrap boundary. Instance issue
`UBC-FRESH/femic-tfl6-instance#6` now tracks fetching the TFL 6 boundary from
`WHSE_ADMIN_BOUNDARIES.FADM_TFL`, clipping the 2025 R1 VRI polygon source, and
filtering the VDYP7 polygon/layer tables to the TFL 6 feature-id set. Instance
issue `UBC-FRESH/femic-tfl6-instance#7` tracks the later 2011 TFL 6
management-plan/information-package review for FEMIC-style source-layer and
THLB netdown recipe planning. Detailed notes live in
`external/femic-tfl6-instance/planning/tfl6_aoi_pivot_and_input_layers.md`
and `external/femic-tfl6-instance/planning/tfl6_thlb_recipe_extraction.md`.

Pivot hygiene update: reconciled the instance README, quickstart,
`config/run_profile.nicffsp.yaml` comments, `planning/source_inventory.md`, and
`planning/k3z_template_adaptation.md` so TFL 6 is consistently described as the
active target AOI. At that checkpoint, the run profile deliberately still
pointed at the existing FDU 1/2/3 bootstrap boundary until `P1.6a` could
materialize `data/source/tfl_6/aoi/tfl_6_boundary.gpkg`.

Completed bounded move: `P1.6a` materialized the active TFL 6 boundary at
`external/femic-tfl6-instance/data/source/tfl_6/aoi/tfl_6_boundary.gpkg`,
layer `tfl_6_boundary`. The boundary was fetched from
`WHSE_ADMIN_BOUNDARIES.FADM_TFL` with `FOREST_FILE_ID='TFL6'`, normalized to
lowercase fields, and verified as 182 EPSG:3005 features with `217042.719 ha`
union area and matching exploratory bounds. One source ring self-intersection
was repaired with no rounded union-area change. The instance run profile now
points to the TFL 6 boundary. The next bounded move at that checkpoint was
`P1.6b`: clip the 2025 VRI R1 polygon source to this boundary and record
geometry QA.

Rename and reference-corpus update: the instance repository is now
`UBC-FRESH/femic-tfl6-instance`, linked in the parent checkout at
`external/femic-tfl6-instance`. The locally copied TFL 6 reference corpus from
the Province of British Columbia TFL 6 page is indexed under
`external/femic-tfl6-instance/reference/tfl6_reference_index.json`, summarized
in `external/femic-tfl6-instance/reference/tfl6_reference_index.md`, and has
searchable extracted PDF text under
`external/femic-tfl6-instance/reference/extracted_text/`. The index covers 18
files: 17 PDFs and one PNG, including AAC rationale, licence maps, instrument,
annual reports, Management Plan 9/10 files, analysis report, and information
package documents. This completes `P1.7a`; `P1.7b` remains the later reviewed
document-mining step.

Completed bounded move: `P1.6b` clipped the 2025 provincial VRI R1 polygon
source to the accepted TFL 6 boundary. The clipped input is
`external/femic-tfl6-instance/data/input/tfl_6/vri_2025_r1_poly_tfl6.gpkg`,
with manifest
`external/femic-tfl6-instance/data/input/tfl_6/vri_2025_r1_poly_tfl6_clip_manifest.json`.
The clip bbox-read `42297` source R1 features, exact-clipped `26959`
intersecting features, and verified `26959` valid EPSG:3005 MultiPolygon
features with `217042.718950 ha` clipped area. `feature_id` is the preferred
VDYP join-key candidate for `P1.6c`. Next bounded move is `P1.6c`: filter the
2025 VDYP7 polygon and layer tables to the clipped TFL 6 `feature_id` set and
verify key integrity.

Completed bounded move: `P1.6c` filtered the 2025 VDYP7 polygon and layer
tables to the clipped TFL 6 `feature_id` set. The instance now carries
`external/femic-tfl6-instance/data/input/tfl_6/vdyp7_input_poly_2025_tfl6.parquet`,
`external/femic-tfl6-instance/data/input/tfl_6/vdyp7_input_layer_2025_tfl6.parquet`,
and
`external/femic-tfl6-instance/data/input/tfl_6/vdyp7_input_2025_tfl6_filter_manifest.json`.
The filter scanned `7104182` VDYP7 polygon rows and retained `26833`, scanned
`7608054` VDYP7 layer rows and retained `25585`, verified zero retained feature
IDs outside the clipped R1 set, and verified zero layer-table feature IDs
outside the retained VDYP7 polygon table. Missing R1-to-VDYP rows are recorded
as diagnostics for downstream inventory and THLB recipe work.

Completed bounded move: `P1.6d` accepted the active TFL 6 input-layer manifest
at
`external/femic-tfl6-instance/data/input/tfl_6/input_layers_manifest.json`.
The manifest records the active TFL 6 boundary, clipped 2025 R1 polygon layer,
filtered 2025 VDYP7 polygon table, filtered 2025 VDYP7 layer table, and
join-contract diagnostics. Instance planning now treats the original FDU 1/2/3
AOI as historical provenance only, not as the active model extraction boundary.
This completes instance issue `UBC-FRESH/femic-tfl6-instance#6`; the next
bounded move is `P1.7b` / `#7`, a reviewed pass over the 2011 TFL 6 management
plan and information package for land-base, source-layer, yield, and THLB
netdown assumptions.

Completed bounded move: `P1.7b` added
`external/femic-tfl6-instance/planning/tfl6_2011_document_review.md` as the
first reviewed document-mining note for the 2011 TFL 6 Management Plan 10
family. The note anchors land-base review to Information Package Section 6 and
Tables 4-17, records Table 4 benchmarks including `171441 ha` total landbase,
`147059 ha` productive forest, `107811 ha` current THLB, and `106319 ha`
long-term landbase, and lists first-pass source-layer, THLB netdown, yield,
visual, old-seral, steep-terrain, and minimum-harvest assumption candidates.
It explicitly separates MP10 historical benchmarks from the current P1.6 2025
TFL 6 input-layer surface and does not create or execute recipe YAML. Next
bounded move is `P1.7c`: separate TSA29 workflow carry-forward patterns from
TFL/general-FMU adaptation gaps.

Completed bounded move: `P1.7b` follow-up added
`external/femic-tfl6-instance/planning/tfl6_thlb_netdown_steps.md` as the
ordered TFL 6 THLB netdown backbone. The note preserves the literal Management
Plan 10 information-package Table 4 order from total landbase through current
THLB and long-term landbase, maps those rows onto tentative FEMIC
`GLB -> AFLB -> LHLB -> THLB` review stages, records the cumulative area
targets (`171441 ha`, `147059 ha`, `134621 ha`, `107811 ha`, and `106319 ha`),
and lists the candidate spatial/aspatial input layers and GIS operations needed
for each deduction. No recipe YAML was created and no netdown execution was
run. Next bounded move remains `P1.7c`: classify each netdown row into TSA29
carry-forward, TFL/general-FMU adaptation, missing-source, aspatial fallback, or
reference-target treatment before drafting recipe skeletons.
