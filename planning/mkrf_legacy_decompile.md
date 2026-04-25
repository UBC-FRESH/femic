# MKRF Legacy Patchworks Decompile Notes

Issue: `#172`

## Summary

This note records the first archaeology pass over the authoritative legacy
MKRF corpus under:

- `MKRF_Cosmin_Model/MKRF/04_Models/PW_MKRF`
- `MKRF_Cosmin_Model/MKRF/03_MappingAnalysisData`
- `MKRF_Cosmin_Model/MKRF/05_Documents`

Milestone one is intentionally **inventory + metadata only**. It does not
attempt to rebuild MKRF as a FEMIC instance yet.

## Corpus boundary

Authoritative first-pass corpus:

- `04_Models/PW_MKRF`
  compiled legacy Patchworks bundle
- `03_MappingAnalysisData`
  upstream mapping, statistics, geodatabases, and VDYP yield-prep lane
- `05_Documents`
  operator/context note lane

Explicitly out of scope for this slice unless later proven necessary:

- sibling folders outside `MKRF_Cosmin_Model/MKRF`
- the large archive `toWalter_May25_2022_noAFRF.7z`

## Legacy model anatomy

### Primary compiled model entrypoints

- `04_Models/PW_MKRF/baseMKRF.pin`
  primary compiled Patchworks entrypoint
- `04_Models/PW_MKRF/ScenarioSet.bsh`
  scenario-set controller loaded by `runME.bsh`
- `04_Models/PW_MKRF/runME.bsh`
  one-line launcher that sources `ScenarioSet.bsh`

The PIN hard-codes the major runtime seams:

- `Tracks/*.csv` as the matrix input surface
- `Spatial/fragments.shp` as the block geometry surface
- `Spatial/topo_frag100.csv` as the topology surface
- `Scripts/RATIO_ACCOUNTS.bsh` as a ratio-account extension seam

### Editable / builder-side source surfaces

- `04_Models/PW_MKRF/XML/baseMKRF.xml`
  generated core ForestModel XML artifact
- `04_Models/PW_MKRF/XML/Curves.xml`
  generated curve-fragment companion included by entity
- `04_Models/PW_MKRF/XML/002_base.xlsm`
  governing workbook-backed parameter store and SPS XML serializer
- `04_Models/PW_MKRF/XML/001_makeCurves_XML.py`
  helper script that writes `Curves.xml` from `XML/CSV/CURVE_TABLE.csv`
- `04_Models/PW_MKRF/XML/003_MakeAccounts.py`
  helper script that writes `Tracks/accounts.csv` from `Tracks/protoaccounts.csv`
- `04_Models/PW_MKRF/XML/CSV/*`
  builder-side CSV feed surface

### Compiled runtime package

- `04_Models/PW_MKRF/Tracks/*.csv`
  compiled tables analogous to a FEMIC checked-in tracks surface
- `04_Models/PW_MKRF/Spatial/fragments.*`
  compiled fragment geometry surface
- `04_Models/PW_MKRF/Spatial/topo_frag100.csv`
  topology sidecar
- `04_Models/PW_MKRF/Targets/*`
  target-builder workbook plus target `.bsh` scripts
- `04_Models/PW_MKRF/Documentation/*.xlsx`
  account/AU/natural-disturbance/road-cost context workbooks

### Reporting / evidence surface

- `04_Models/PW_MKRF/Outputs/001_Base/*`
  baseline report package with forest, harvest, patch, scenario, and target
  report trees
- `04_Models/PW_MKRF/Outputs/z_Comparisons/*`
  comparison chart/report package

### Upstream mapping / yield-prep lane

- `03_MappingAnalysisData/Source.gdb`
  likely raw/source geodatabase lane
- `03_MappingAnalysisData/Resultant.gdb`
  likely processed/resultant geodatabase lane
- `03_MappingAnalysisData/Resultant_info_v1.xlsx`
  resulting dataset interpretation aid
- `03_MappingAnalysisData/00_Stats/*`
  rollups and statistics used for sanity checks or reporting
- `03_MappingAnalysisData/03_Yields/VDYP/*`
  VDYP batch inputs, parameters, yields, and error logs

### Operator / context lane

- `05_Documents/MKRF_Modeling_Notes.pdf`
  current top-level operator/context note discovered in-scope

## First-pass FEMIC crosswalk

Reference shapes:

- `external/femic-k3z-instance`
  plain-git example of full instance layout
- `external/femic-tsa29-instance`
  DataLad-backed example of compiled-runtime plus editable-source split

Recommended recovery interpretation:

- legacy PIN / scenario / target scripts
  future **analysis/runtime wrapper** surface
- legacy track tables
  future **checked-in Patchworks runtime payload** surface
- legacy XML + builder workbooks/scripts
  future **editable model-source / recovery evidence** surface
- legacy fragments + topology
  future **validated fragments/runtime spatial** surface
- mapping-analysis geodatabases / VDYP prep
  future **raw-input + preprocessing lineage** surface
- historical outputs/reports
  future **archival evidence** surface

## Unresolved seams

- whether any `PW_MKRF/Outputs` artifacts are canonical enough to serve as
  baseline evidence for later FEMIC regression checks
- whether road-network inputs under the legacy PIN's `../roads/` expectation
  exist elsewhere in the planning workspace and are required for route-aware
  reconstruction
- whether the `Source.gdb` / `Resultant.gdb` datasets can be mapped cleanly
  onto a future FEMIC stage-00/stage-01 contract without additional external
  missing dependencies

## Editable-source authority review

The governing editable-source seam is now narrow enough to state explicitly:

- `XML/002_base.xlsm`
  governing workbook-backed parameter store and SPS XML serializer for the core
  ForestModel structure
- `XML/baseMKRF.xml`
  generated core ForestModel XML artifact emitted by the spreadsheet tool
- `XML/Curves.xml`
  generated curve-fragment artifact included into `baseMKRF.xml` through the
  `beforeCurves` entity
- `XML/001_makeCurves_XML.py`
  helper generator that writes `Curves.xml` from `XML/CSV/CURVE_TABLE.csv`
- `XML/003_MakeAccounts.py`
  helper post-processor that writes `Tracks/accounts.csv` from
  `Tracks/protoaccounts.csv`

The SPS VBA in `002_base.xlsm` exposes a top-level `DumpXML(filename)` routine
that writes the XML by calling:

- `dumpProlog`
- `dumpCurves`
- `dumpRetention`
- `dumpUnmanaged`
- `dumpStratum`
- `dumpAttributes`

Those routines pull workbook-owned data surfaces such as:

- `Input Variables`
- `Netdown`
- `curveNames`
- `stratumCriteria`, `stratumFeatures`, `stratumSuccession`,
  `stratumProducts`, `stratumTreatments`, `stratumFactors`
- `attributes`
- `constantValues`

For FEMIC recovery, that means the workbook **data surfaces** are the real
source evidence worth preserving, while the VBA itself should be treated as a
serialization reference to replace rather than a long-term runtime dependency.

## Workbook surface map

The governing workbook now breaks down into a clearer set of FEMIC-facing
source families:

- `Input Variables`
  problem description, horizon, input field bindings, constants, unmanaged
  query, and XML include-fragment hooks
- `Codes`
  workbook registry and enum surface for active sheet families and allowed
  option values
- `Curve Library`
  age-by-curve point library used by `dumpCurves`
- `Netdown`
  aspatial netdown rules and retention feature assignments
- `Attrib`
  general attribute assignment surface
- `Treat`
  currently active stratum bundle containing criteria, features, succession,
  products, treatments, and factor logic
- `Post Renewal Succession`
  supporting treatment-response lookup surface
- `Lookups`
  lookup-table / CSV bridge support surface

One useful caution from this pass: the `Codes` registry advertises constants
and lookup families such as `Harv costs`, `Unharvested Vol`, `Roads_Landings`,
`SilvCosts_Lookup`, and `NaturSuccn`, but the reviewed workbook tab list does
not expose those exact names as discrete worksheets. For now those should be
treated as evidence of intended surfaces, not yet as confirmed sheet-level
payloads.

## Workbook value extracts

The governing workbook-owned values are now materialized into tracked review
artifacts under `metadata/mkrf_xlsm_review/`.

Primary sheet-level review extracts now present:

- `metadata/mkrf_xlsm_review/input_variables.review.csv`
- `metadata/mkrf_xlsm_review/netdown.review.csv`
- `metadata/mkrf_xlsm_review/curve_library.review.csv`
- `metadata/mkrf_xlsm_review/attrib.review.csv`
- `metadata/mkrf_xlsm_review/treat.review.csv`
- `metadata/mkrf_xlsm_review/extract_manifest.yaml`

Named-range and supporting review extracts now present:

- `metadata/mkrf_xlsm_review/ranges/input_variables_*.review.yaml`
- `metadata/mkrf_xlsm_review/ranges/input_variables_columns.review.csv`
- `metadata/mkrf_xlsm_review/ranges/input_variables_constants.review.csv`
- `metadata/mkrf_xlsm_review/ranges/netdown_criteria.review.csv`
- `metadata/mkrf_xlsm_review/ranges/netdown_names.review.csv`
- `metadata/mkrf_xlsm_review/ranges/netdown_factors.review.csv`
- `metadata/mkrf_xlsm_review/ranges/curve_names.review.csv`
- `metadata/mkrf_xlsm_review/ranges/attrib_attributes.review.csv`
- `metadata/mkrf_xlsm_review/ranges/treat_stratum_*.review.csv`
- `metadata/mkrf_xlsm_review/ranges/lookups_spp_comp.review.csv`
- `metadata/mkrf_xlsm_review/ranges/post_renewal_treatment_responses.review.csv`

These files preserve workbook values and formulas as review evidence only.
They are not yet treated as live FEMIC config, not a workbook publication
surface, and not a VBA reimplementation.

## First live Input Variables translation

The first MKRF-first FEMIC-native translation of the workbook `Input Variables`
surface now lives in the instance at:

- `external/femic-mkrf-instance/config/legacy_xml_builder/input_variables.mkrf.yaml`
- `external/femic-mkrf-instance/metadata/legacy_input_variables_translation.yaml`
- `external/femic-mkrf-instance/runbooks/LEGACY_INPUT_VARIABLES_TRANSLATION.md`

That translation is intentionally narrow.

Live now in exporter behavior:

- `description`
- `start_year`
- `horizon_years`
- `exclude_expression`
- `unique_record_label_expression`
- `polygon_area_expression`
- `stand_age_expression`

Preserved but still staged only:

- `max_inventory_age`
- additional stratification column bindings
- treatment-eligibility expression
- include-fragment hooks
- matrix-builder constants

The live subset is wired through the existing Patchworks export flow as an
explicit opt-in config path. The exported ForestModel XML now carries the
legacy block/area/age/exclude expressions directly, and the fragments export
now requires and passes through the referenced checkpoint source columns.
The remaining staged fields stay lineage evidence only until the current
checkpoint-first exporter can safely absorb those legacy matrix-builder
semantics.

## Recommended next bounded step

Do exactly one next bounded move:

**operationalize the remaining staged `Input Variables` seam for
`additional_stratification_columns`**, deciding which workbook-owned
column-expression bindings should become live checkpoint/export fields before
we broaden into `Netdown` or `Treat`.

The archival control-layer intake, the archival track-table intake, the
archival spatial-runtime intake, and the editable-source authority review are
now complete. The next bounded move should:

- focus on exactly one seam:
  - turn the remaining staged additional-stratification column bindings into
    an explicit FEMIC contract instead of broadening immediately into
    `Netdown` or `Treat`;
- preserve the evidence/review framing instead of claiming a runnable rebuild
  surface, a finalized rebuild recipe, workbook publication, or a VBA
  reimplementation;
- continue to defer `03_MappingAnalysisData/*` and `Outputs/*`; and
- keep road-network discovery, reporting-surface import, direct workbook
  publication, live activation of include hooks/constants, and broader `Treat`
  stratum refactoring outside that next slice unless the block-layout contract
  work proves they are required.
