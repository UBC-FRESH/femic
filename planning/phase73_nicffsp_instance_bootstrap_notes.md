# Phase 73 NICF FSP Instance Bootstrap Notes

## Governing Issues

- Parent FEMIC coordination: `UBC-FRESH/femic#199`
- Instance Phase 1 parent issue:
  - `UBC-FRESH/femic-nicffsp-instance#4`: Phase 1 bootstrap repository and
    build plan
- Instance Phase 1 child task issues:
  - `UBC-FRESH/femic-nicffsp-instance#1`: `P1.2` source-payload inspection
    and normalization
  - `UBC-FRESH/femic-nicffsp-instance#3`: `P1.3` K3Z-to-NICF adaptation
    contract
  - `UBC-FRESH/femic-nicffsp-instance#2`: `P1.4` cedar, expansion, and
    runtime-package follow-on issue split

## Bootstrap Result

The standalone instance repository has been created as
`UBC-FRESH/femic-nicffsp-instance` and linked under the parent checkout at
`external/femic-nicffsp-instance`.

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

Next bounded move: continue `P1.2` / `#1` by deciding whether the full
27-feature BCGW LU layer is also canonical reference context. Runtime config
wiring should wait until that source-path decision is recorded. Do not start
`P1.3` or `P1.4` implementation until the accepted source paths are recorded.
