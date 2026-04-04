# TSA29 Section 5.1 BCDC Manual Resolution Notes

Purpose

This note preserves one manual exploration pass of the new
`femic data bcdc-resolve` workflow against layer names scraped from a TSR
source-data list. Per later clarification from the developer, this pass was
actually based on the older Williams Lake TSA package
`reference/williams_lake_tsa_data_package-2.pdf`, specifically Table 2, not
the 2024 TSA29 package.

Treat this as a planning/provenance note, not as a canonical dataset contract.
It is useful for:

- future refinement of TSA29 THLB/netdown logic;
- follow-on work for issue `#98`;
- identifying which TSR source-list entries map cleanly to BC Data Catalogue
  object names;
- identifying alias/name-drift cases where FEMIC should probably learn
  curated fallback rules later.

## High-signal findings

### Source-system pattern

The manual pass suggests a useful first-order rule:

- rows in Table 2 whose source was listed as `BCGW` generally produced useful
  catalogue hits; and
- rows not listed with source `BCGW` generally did not.

That pattern makes sense and should probably inform later resolver heuristics:
the first slice is naturally strongest when the TSR source list is already
pointing at BC Data Catalogue / BCGW-facing layer names.

### Clean exact object-name hits

These queries resolved cleanly to a likely intended BC Data Catalogue package:

- `WHSE_FOREST_VEGETATION.F_OWN`
- `WHSE_ADMIN_BOUNDARIES.FADM_TSA`
- `WHSE_LAND_USE_PLANNING.RMP_LANDSCAPE_UNIT_SVW`
- `WHSE_TANTALIS.TA_PARK_ECORES_PA_SVW`
- `WHSE_ADMIN_BOUNDARIES.CLAB_INDIAN_RESERVES`
- `WHSE_ADMIN_BOUNDARIES.FADM_BCTS_AREA_SP`
- `WHSE_FOREST_VEGETATION.BEC_BIOGEOCLIMATIC_POLY`
- `WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY`
- `WHSE_LAND_USE_PLANNING.RMP_PLAN_NON_LEGAL_POLY_SVW`
- `WHSE_WILDLIFE_MANAGEMENT.WCP_UNGULATE_WINTER_RANGE_SP`
- `WHSE_FOREST_VEGETATION.REC_VISUAL_LANDSCAPE_INVENTORY`
- `WHSE_TANTALIS.TA_WILDLIFE_MGMT_AREAS_SVW`
- `WHSE_WILDLIFE_MANAGEMENT.WCP_WILDLIFE_HABITAT_AREA_POLY`
- `WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_POLYS_SP`
- `WHSE_LAND_USE_PLANNING.RMP_OGMA_LEGAL_CURRENT_SVW`
- `WHSE_LAND_USE_PLANNING.RMP_PLAN_LEGAL_POLY_SVW`
- `WHSE_LAND_USE_PLANNING.RMP_STRGC_LAND_RSRCE_PLAN_SVW`
- `WHSE_BASEMAPPING.TRIM_CONTOUR_POINTS`

### Useful fuzzy/text hits

These did not resolve by clean exact object-name matching, but the current
resolver still surfaced something plausibly useful:

- `SITE_PROD_BC`
  - top match: `Provincial Site Productivity Layer`
- `CONSOLIDATED_CUTBLOCKS`
  - top match: `Harvested Areas of BC (Consolidated Cutblocks)`
- `WHSE_WATER_MANAGEMENT.BC_COMMUNITY_WATERSHEDS`
  - top match looked correct, but matching was weaker than the clean
    object-name hits and is worth revisiting if we add curated rules.

### Direct-download candidates surfaced by v1

These are especially valuable because the first slice can do more than just
classify them; it can potentially download them directly:

- `SITE_PROD_BC`
  - `Site Productivity (Version 8.0) Data Locator`
  - `Provincial Site Productivity Layer (Version 8.0) - Site Index by Tree Species Rasters`
- `WHSE_FOREST_VEGETATION.VEG_COMP_LYR_R1_POLY`
  - `veg_comp_lyr_r1_poly_2024.gdb.zip`
- `CONSOLIDATED_CUTBLOCKS`
  - `Consolidated Cutblocks Complete Download`
- `WHSE_LAND_AND_NATURAL_RESOURCE.PROT_CURRENT_FIRE_POLYS_SP`
  - `Download Zipped Shapefile of Current Fire Perimeters`

These are strong candidates for later promotion into:

- curated resolver rules;
- `metadata/required_datasets.yaml` entries;
- or `external/femic-public-data` archival workflows.

## Gaps / unresolved aliases

These source-list entries did not resolve cleanly in the first manual pass and
are good candidates for future alias/curation work:

- `WHSE_FOREST_TENURE.FTEN_MANAGED_LIC_POLY_SVW`
- `WHSE_HUMAN_CULTURAL_ECONOMIC.FNIRS_AGREEMENT_BOUNDARY_SVW`
- `CONSOLIDATED_CUTBLOCKS_2011`
- `REG_LAND_AND_NATURAL_RESOURCE.TERRAIN_STABILITY_CAR_POLY`
- `REG_LAND_AND_NATURAL_RESOURCE.WLD_WHA_PROPOSED_SP`
- `BCMPB.V9.CUMKILL.PROJECTED`
- `WL_PROP_COMM_FOREST`
- `CARIBOO_OPERATING_AREAS`
- `CYCLE_TIME_WL_TSA_CONTOUR`
- `REG_LAND_AND_NATURAL_RESOURCE_WETLAND_MGMT_CAR_POLY`
- `REG_LAND_AND_NATURAL_RESOURCE_STREAM_MANAGEMENT_CAR_POLY`

Likely explanations include:

- historical layer names that no longer exist verbatim in BCDC;
- internal FAIB shorthand rather than BCDC-facing object names;
- year/version suffixes that should be stripped before querying;
- source-list rows that actually refer to local project layers rather than
  public BC Data Catalogue layers;
- or cases where the useful search key is the package title rather than the
  object name.

## Resolver limitations surfaced by this pass

### Multi-word free-text queries are brittle in PowerShell

Examples like:

- `Silviculture Activities History`

were interpreted as three separate positional queries:

- `Silviculture`
- `Activities`
- `History`

That is technically expected CLI behavior, but it means the Windows examples
should emphasize quoting multi-word queries, for example:

```powershell
& .\.venv\Scripts\python.exe -m femic data bcdc-resolve "Silviculture Activities History"
```

### Hard line wraps plus pasted continuation text can break PowerShell badly

Several manual runs showed two distinct Windows shell hazards:

- pasted object names split across lines caused PowerShell to treat the suffix
  as a second command;
- very large pasted multiline blocks triggered noisy `PSReadLine` rendering
  exceptions unrelated to FEMIC itself.

This suggests the next docs/helpfulness pass should encourage either:

- one query per line/command; or
- quoted arguments in a script file rather than large interactive pastes.

### Some exact-looking queries still only matched by weak text heuristics

`WHSE_WATER_MANAGEMENT.BC_COMMUNITY_WATERSHEDS` appeared to return the right
dataset, but not with the same confidence as the cleaner exact object-name
cases. This is a good clue that future ranking/curation work should include a
small hand-maintained alias map for known forestry/TSR layer names.

## Suggested follow-on work for issue #98

- add a small curated alias map for known forestry/TSR source-list names that
  do not round-trip cleanly through BCDC object-name search;
- add CLI/docs examples for quoted multi-word PowerShell queries;
- consider a batch-input mode that reads one query per line from a text file,
  which would avoid PSReadLine paste chaos;
- consider a later promotion workflow that turns reviewed resolver manifests
  into `metadata/required_datasets.yaml` candidates;
- revisit the high-value direct-download hits first:
  `SITE_PROD_BC`, VRI R1, Consolidated Cutblocks, and current fire perimeters.
