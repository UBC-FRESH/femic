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
- `additional_stratification_columns`
- `treatment_eligibility_expression`

Inactive after P55.14 classification:

- `max_inventory_age`
  review metadata only
- `beforeCurves`
  blocked until the Curve Library review-to-build contract is translated
- blank include-fragment hooks
  review metadata only
- formula-like or otherwise unclaimed matrix-builder constants such as `frd`

The live subset is wired through the existing Patchworks export flow as an
explicit opt-in config path. The exported ForestModel XML now carries the
legacy block/area/age/exclude expressions directly, and the fragments export
now requires and passes through the referenced checkpoint source columns.
The live additional-stratification bindings now materialize into fragments
fields `status`, `au_1`, `auf`, `oper`, `ct`, and `aux`, with `au_1`
deliberately renamed from workbook key `au` to avoid colliding with the base
required `AU` fragments field.
The live treatment-eligibility seam now materializes as fragments field
`treat_inel`, which is written as `Y` when the legacy workbook expression
evaluates true and `N` otherwise. In the current MKRF translation that means
`status in unmanaged` is evaluated against the live `status` binding plus the
translated legacy constants contract. That contract now exposes only scalar
legacy expression symbols: `managed`, `unmanaged`, `operable`, and `lowoper`.
Formula-like workbook entries such as `frd` remain preserved but deferred until
a live builder consumer is identified. This remains narrower than a full legacy
unmanaged-track rebuild: the expression currently drives an exported review
field, not a regenerated Patchworks select/track block.
The remaining staged fields stay lineage evidence only until the current
checkpoint-first exporter can safely absorb the rest of those legacy
matrix-builder semantics.

## Planned recovery sequence

Do exactly one next bounded move at a time. The roadmap is now the control
surface for Phase 55/56 sequencing; implementation should not invent the next
slice in chat.

Completed Phase 55 workbook-contract recovery:

- `P55.14`:
  `max_inventory_age` is review metadata only because the current
  checkpoint-first exporter derives curve evaluation spans from
  `horizon_years` and source curve ages. `beforeCurves` is blocked because the
  workbook value points at generated `Curves.xml`; activation requires the
  `P55.15` Curve Library review-to-build contract. The remaining include
  hooks are blank in the workbook and are preserved as review metadata.
- `P55.15`:
  the workbook `Curve Library` / `curveNames` surface is translated into
  `config/legacy_xml_builder/curve_library.mkrf.yaml` in the MKRF instance.
  The contract preserves the legacy curve IDs `zero`, `age`, `le10`, `lt20`,
  `gt60`, `lt80`, and `gt250`; preserves the workbook `Age` axis and nonblank
  curve points; and treats blank cells as absent points, not zeroes. It is a
  review-to-build contract only: `beforeCurves` remains inactive until a later
  generated `Curves.xml` fragment-equivalence pass.
- `P55.16`:
  the workbook `Netdown` / `netdownCriteria`, `netdownNames`, and
  `netdownFactors` surfaces are translated into
  `config/legacy_xml_builder/netdown.mkrf.yaml` in the MKRF instance. The
  contract preserves the two complete proportional reassignment rules, keeps
  their `feature.area.retention.total` factor assignments, and preserves the
  unmatched feature-factor row plus 85 trailing `0.07` values as review-only
  metadata. It does not activate `dumpRetention` or proportional fragment area
  splitting.
- `P55.17`:
  the workbook `Attrib` / `attributes` surface is translated into
  `config/legacy_xml_builder/attributes.mkrf.yaml` in the MKRF instance. The
  contract preserves 16 rows with nonblank `Attribute Name` values, classifies
  143 rows as incomplete template/default rows, and keeps formula dependencies
  such as `frd`, `Yield_*`, `LookupTable`, `treatment`, and attribute
  references blocked. It does not activate `dumpAttributes`.
- `P55.18`:
  the workbook `Treat` stratum bundle is translated into
  `config/legacy_xml_builder/strata/treat.mkrf.yaml` in the MKRF instance. The
  contract preserves the empty/default stratum criteria, the default succession
  rule (`breakup_at = 999`, `renewal_age = 0`), and the `CC`/`CT` treatment
  definitions. Feature and product rows remain review metadata because they
  carry template/default values but no `Feature Name` or `Product Name`.
  Copied compiled track tables are cross-check evidence only. It does not
  activate `dumpStratum`.
- `P55.19`:
  the translated workbook-derived contract is reconciled against the available
  compiled legacy outputs at the contract surface level in
  `metadata/legacy_workbook_compiled_reconciliation.yaml`. The review records
  a metadata-recovery go decision and a runnable-rebuild no-go decision. The
  no-go blockers are generated `baseMKRF.xml` / `Curves.xml` reconciliation,
  pointer-only compiled track tables, inactive curve/retention/attribute/
  stratum builders, unpublished boundary/checkpoint inputs, and unresolved
  upstream mapping / road / output / workbook publication requirements.

Active next bounded move:

`P56.3` is the active next bounded implementation move. Materialize or resolve
the pointer-only compiled track tables (`curves.csv`, `features.csv`, and
`products.csv`) without substituting other compiled artifacts.

Completed `P56.1` planning boundary:

- generated XML reconciliation is scheduled under `P56.2`;
- pointer-only compiled track table resolution is scheduled under `P56.3`;
- curve, retention, attribute, stratum, and full XML builder activation-order
  design is scheduled under `P56.4`;
- real MKRF source-input publication boundaries, including checkpoint and
  boundary requirements, are scheduled under `P56.5`; and
- runnable rebuild-readiness milestone criteria are scheduled under `P56.6`.

Remaining Phase 56 sequence after `P56.1`:

- `P56.2`:
  completed. Generated `baseMKRF.xml` and `CSV/CURVE_TABLE.csv` are now inert
  review artifacts in the MKRF instance under
  `data/legacy_mkrf/generated_xml/`. `baseMKRF.xml` matches the translated
  Input Variables and built-in Curve Library contract surfaces. Located
  `Curves.xml` matches `CSV/CURVE_TABLE.csv` by curve identifier, age, and
  numeric value. `beforeCurves` and XML builders remain inactive.
- `P56.3`:
  materialize or resolve pointer-only compiled track tables (`curves.csv`,
  `features.csv`, and `products.csv`) without substituting other artifacts.
- `P56.4`:
  design the activation order for curve, retention, attribute, stratum, and
  full XML emission builders.
- `P56.5`:
  resolve the real MKRF source-input publication boundary, including
  checkpoint and boundary requirements.
- `P56.6`:
  publish rebuild-readiness milestone criteria before any runnable rebuild
  claim.

Hard boundaries for this sequence:

- no `03_MappingAnalysisData/*` intake;
- no `Outputs/*` intake;
- no road-network discovery;
- no direct workbook publication;
- no generated XML builder activation;
- no compiled-track payload materialization outside `P56.3`;
- no curve, retention, attribute, stratum, or full XML builder activation;
- no VBA runtime dependency;
- no substitution of compiled artifacts for raw source inputs; and
- no claim that the archival legacy payload is a runnable FEMIC/Patchworks
  rebuild surface until a later roadmap task explicitly establishes that
  contract.
