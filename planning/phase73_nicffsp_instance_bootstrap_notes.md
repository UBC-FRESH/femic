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

Next bounded move: work `P1.2` / `#1` by inspecting
`nicf_fsp_amendment_3_spatial.zip`, recording its layer inventory, and
identifying the authoritative AOI boundary candidate. Do not start `P1.3` or
`P1.4` implementation until the accepted source paths are recorded.
