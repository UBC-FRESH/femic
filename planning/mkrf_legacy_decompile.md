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
  main editable legacy model XML
- `04_Models/PW_MKRF/XML/Curves.xml`
  curve-heavy XML companion
- `04_Models/PW_MKRF/XML/002_base.xlsm`
  workbook-backed XML builder dependency
- `04_Models/PW_MKRF/XML/001_makeCurves_XML.py`
- `04_Models/PW_MKRF/XML/003_MakeAccounts.py`
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
- whether `XML/baseMKRF.xml` or the workbook/script builder chain should be
  treated as the governing editable source of truth
- whether the `Source.gdb` / `Resultant.gdb` datasets can be mapped cleanly
  onto a future FEMIC stage-00/stage-01 contract without additional external
  missing dependencies

## Recommended next bounded step

Do exactly one next bounded move:

**import the small compiled control surfaces into `external/femic-mkrf-instance`
as inert archival reference files**, not the full runtime package yet.

The metadata-only intake is now complete. The next bounded move should:

- copy only the small compiled control files such as `baseMKRF.pin`,
  `runME.bsh`, `ScenarioSet.bsh`, and selected `.bsh` control scripts into a
  clearly archival/reference lane inside the MKRF instance;
- continue to defer bulky tracks, fragments, topology, outputs, and upstream
  mapping-analysis payloads; and
- leave the actual FEMIC rebuild/export interpretation deferred until the
  archival control surfaces are reviewed in-instance.
