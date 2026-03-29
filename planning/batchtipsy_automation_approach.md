# BatchTIPSY Automation Approach

## Current Direction

Phase 48 is no longer a vague feasibility investigation. The current direction
is to replace the old fixed-width DAT / raw `.out` BatchTIPSY seam with the
newer BTC `MSYT.csv` command-line seam.

The intended target workflow is:

1. Stage 01a writes a canonical BTC-compatible `MSYT.csv` input.
2. FEMIC launches unattended BTC CLI report runs on Windows.
3. BTC returns CSV output and CSV error files.
4. Stage 01b / post-TIPSY consumes the returned CSV directly.

The installed BTC user guide (`userguide1.4.pdf`) now confirms these additional
CLI details:

- BTC command line can start from either:
  - a `.btc` BatchTIPSY Composer project file, or
  - `/TSR`, which uses `TimberSupply.rpt`, or
  - `/FLP`, which uses `ForestLandscapePlan.rpt`
- additional command-line arguments are interpreted as:
  1. input filename
  2. optional output filename
  3. optional error filename
- documented standard exit codes include:
  - `0` success
  - `2` file not found
  - `5` access denied
- the guide explicitly says the batch process obeys normal BTC configuration
  files such as `settings.txt`

Another packaged clue now in scope:

- `C:\Program Files\TIPSY 4.7\CBM\TIPSY-CBM.pdf`
  - page 1 explicitly mentions a BatchTIPSY command-line switch `-RGM`
  - described behavior: create one regime file per processed line for later
    loading into the TIPSY-to-CBM workflow

Current planning implication:

- the wider `C:\Program Files\TIPSY 4.7\` tree should now be treated as an
  active reverse-engineering surface, not just the `BTC\` subdirectory
- the phase plan should include a full installation audit / "easter egg hunt"
  for additional CLI/runtime seams, not just the already proven `/TSR` and
  `/FLP` paths
- the `-RGM` clue should be treated as strategically important beyond carbon
  linkage alone:
  - regime-file export may be the missing seam needed to unlock batch FANSIER
    workflows as well, because FANSIER appears to rely on regime files in
    addition to the ordinary TIPSY inputs
- future FEMIC planning should therefore consider two follow-on linkage paths
  once the core BTC seam is stable:
  - FEMIC -> BTC/BatchTIPSY -> regime files -> TIPSY-CBM
  - FEMIC -> BTC/BatchTIPSY -> regime files -> FANSIER

## Installed-Tree Audit Update (2026-03-29)

The broader installed-tree audit under `P48.3d` is now complete enough to
change planning posture from "possible easter eggs" to "documented adjacent
seams."

High-signal audit findings:

- `BTC\OutputColumns.txt` is confirmed as the canonical BTC output ledger, and
  it explicitly encodes the repeated `{000,125,175}` utilization-threshold
  triplets that FEMIC is now treating as atomic bank units.
- `BTC\userguide1.4.pdf` confirms command-line start modes for:
  - saved `.btc` projects;
  - `/TSR` via `TimberSupply.rpt`;
  - `/FLP` via `ForestLandscapePlan.rpt`.
- `BTC\userguide1.4.pdf` also confirms the positional command-line filename
  contract and says command-line BTC still obeys normal config files such as
  `settings.txt`.
- `CBM\TIPSY-CBM.pdf` explicitly documents the `-RGM` regime-file export seam
  for BatchTIPSY.
- `BTC\oafs.txt`, `BTC\utiliz.txt`, `BTC\gw.txt`, `BTC\FertRespMOF.txt`, and
  `BTC\vriSpecies.txt` remain first-class reverse-engineering surfaces for
  future follow-on work around OAF logic, utilization thresholds, genetics,
  fertilization, and species mapping.

The `.chm` help audit produced a narrower but still useful result:

- local `hh.exe -decompile` did not yield full HTML extraction in this
  environment;
- however, machine-readable topic inventories were recovered directly from the
  compiled help binaries and saved under:
  - `tipsy_io/logs/p48_3_install_audit/chm/`

Those topic inventories surfaced help coverage for:

- TIPSY Batch/custom-table/timber-supply/OAF/mortality topics;
- Fansier regime, pricing, economics, biomass/carbon/CO2e topics;
- SiteTools batch output-column and site-index topics.

The full audit summary now lives in:

- `planning/tipsy_install_tree_audit_20260329.md`

## Evidence Already Collected

- Local Windows host has BTC installed at:
  - `C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe`
- Local BTC changelog confirms command-line support for:
  - `/TSR`
  - `/No_GUI`
- A live local smoke against the installed sample worked with:
  - `TIPSYbtc.exe /TSR <input.csv> <output.csv> <error.csv>`
  - exit code `0`
  - CSV output written as expected
  - CSV error file written as expected
- The simpler invocation:
  - `TIPSYbtc.exe /TSR <input.csv>`
  also works and auto-generates standard output/error file names beside the
  input file.
- The user guide also confirms that BTC can load a `.btc` project directly from
  the command line, which may matter if the richer output path ultimately
  requires a saved project/report configuration rather than plain `/TSR`.

## Important Input / Output Notes

- The installed sample input schema reference is:
  - `C:\Program Files\TIPSY 4.7\BTC\Samples\MSYT.csv`
- The proven `/TSR` CSV output currently gives:
  - merchantable volume by age
  - height by age
- The proven `/FLP` CSV output currently gives:
  - gross volume by age
  - crown closure by age
- Together, `/TSR` and `/FLP` provide a credible first unattended indicator set:
  - merchantable volume
  - height
  - gross volume
  - crown closure
- The richer BTC metadata and Tcl files show BTC knows about additional
  indicators such as:
  - `MeanDBHg000`
  - `MeanDBHg125`
  - `StemCount000`
  - `StemCount125`
  - DBH-class stock and mortality outputs
- However, the currently proven `/TSR` sample run has not yet demonstrated a
  non-GUI path that emits all of those richer indicators directly.

## Default Unattended Mode Decision

The current default implementation target is now a fully unattended BTC mode
that uses a single supervised `/TSR` run with a vetted transposed
`TimberSupply.rpt` mashup.

The canonical unattended indicator set is:

- merchantable volume:
  - `MVcon_*`
  - `MVdec_*`
- height:
  - `HTcon_*`
  - `HTdec_*`
- gross volume:
  - `gVol_*`
- crown closure:
  - `CC_*`

Current planning implication:

- FEMIC should no longer treat separate `/TSR + /FLP` invocations as the
  preferred unattended path
- the supported unattended seam is:
  - writable scratch directory
  - copied BTC install
  - patched stock `TimberSupply.rpt`
  - supervised `/TSR`
  - returned CSV output/error files
- richer BTC outputs should be treated as an optional enhancement tier, not as
  a blocker for landing the first automated BTC pipeline slice

## Current Closeout Scope

The bird currently being landed is the **core unattended BTC cutover**, not
the entire universe of richer BTC indicators.

What is in scope for closeout:

- canonical Stage 01a `03_input-tsaXX.csv` generation
- unattended `TIPSYbtc.exe /TSR` execution under FEMIC
- returned `04_output-tsaXX.csv` / `04_error-tsaXX.csv`
- Stage 01b/post-TIPSY resume from the returned BTC CSV
- real K3Z downstream proof
- user/operator/contract docs that now describe BTC CSV as the default seam

What is explicitly out of scope for this closeout:

- richer optional indicator banks tracked separately on:
  - issue `#47`
  - issue `#48`
  - issue `#49`
- the full `C:\Program Files\TIPSY 4.7\` installation audit / CHM extraction
- regime-file / TIPSY-CBM / FANSIER linkage work

So the intended closure shape is:

- close issue `#46` for the core unattended BTC seam
- keep the richer-bank and deeper reverse-engineering work on their own
  follow-on trackers

## Immediate Regression Follow-Up

The core unattended BTC cutover is now landed, but the next active task is a
post-cutover regression on the shipped K3Z Patchworks surfaces:

- `feature.QMD.*` and `product.QMD.*` accounts appear empty at launch time on
  at least the shipped `base` and `ctfert_l15h5` surfaces
- Patchworks launches cleanly, which suggests the account names and XML syntax
  still exist, but that the underlying QMD attribute values may now be null,
  empty, or otherwise disconnected from their intended curves

The immediate debugging order should therefore be:

1. confirm the symptom on the shipped K3Z `base` and `ctfert_l15h5` launch
   surfaces
2. inspect the generated `tracks/*/accounts.csv`, `protoaccounts.csv`, and
   `features.csv` surfaces for the QMD families
3. inspect the active K3Z ForestModel XML for the matching QMD attributes and
   curve references
4. trace further upstream into the BTC-driven managed-curve rebuild path only
   if the XML/track layer suggests the curves themselves are empty or broken

This regression should be treated as a focused bug-fix task, not as part of
the optional richer BTC indicator-bank expansion.

## Report-Coupled `/TSR` Breakthrough

The recent copied-install probes strongly suggest that `/TSR` is not a fixed
opaque mode. It appears to run whatever compatible report definition is loaded
from `TimberSupply.rpt`.

Live evidence gathered so far:

- baseline copied BTC install with the stock `TimberSupply.rpt`:
  - `/TSR` runs cleanly
  - returns the usual merchantable volume + height CSV surface
- copied BTC install with `ForestLandscapePlan.rpt` renamed to
  `TimberSupply.rpt`:
  - `/TSR` runs cleanly
  - returns FLP-style `gVol_*` and `CC_*` output
- copied BTC install with a small transposed TSR+FLP mashup report replacing
  `TimberSupply.rpt`:
  - `/TSR` runs cleanly
  - returns all four unattended indicator families in one file:
    - `MVcon_*`
    - `MVdec_*`
    - `HTcon_*`
    - `HTdec_*`
    - `gVol_*`
    - `CC_*`

This is now the strongest unattended implementation clue in the whole Phase 48
effort.

Current planning implication:

- FEMIC should target a curated compatible `TimberSupply.rpt` generator rather
  than assuming it must orchestrate separate `/TSR` and `/FLP` runs forever
- the first canonical unattended FEMIC report template should be the safe
  transposed TSR+FLP mashup
- the new FEMIC-side BTC report-template generator should treat that mashup as
  a first-class preset

## First End-to-End Runner Success

The first real end-to-end unattended BTC runner smoke is now proven on the
local Windows host.

Working path:

- copied BTC install staged under writable scratch
- stock `TimberSupply.rpt` patched in place with the vetted transposed mashup
- supervised `/TSR` launch
- returned output/error CSVs kept in writable scratch working directory
- manifest/log capture written by FEMIC

Live proof summary:

- command surface:
  - `femic tipsy run-btc ... --mode TSR`
- result:
  - exit code `0`
  - no lingering `TIPSYbtc.exe` process
  - manifest status `ok`
  - output file emitted successfully
- returned output columns include:
  - `feature_id`
  - `MVcon_*`
  - `MVdec_*`
  - `HTcon_*`
  - `HTdec_*`
  - `gVol_*`
  - `CC_*`

Current planning implication:

- the report-template seam is no longer speculative
- the runner seam is no longer speculative
- the next implementation edge is now:
  - parsing the transposed unattended `/TSR` output into FEMIC downstream
    managed-curve structures

## First Stage 01a `MSYT.csv` Writer Slice

The first conservative BTC input writer slice is now in place in FEMIC.

What it does:

- builds canonical `03_input-tsaXX.csv` from the same current TIPSY `f`-table
  payload already assembled in Stage 01a
- uses AU as the stable stand key for:
  - `feature_id`
  - `opening_id`
- fills the planted treatment unit from the current `f`-table fields:
  - `SPP_n`
  - `PCT_n`
  - `Density`
  - `Regen_Delay`
  - `GW_n`
  - `OAF1`
  - `OAF2`
  - `SI`
- leaves the natural treatment unit empty in this first cut
- maps BTC site-index columns from the same single current `SI` value using a
  conservative species-code projection

Current implementation choice:

- this first slice is intentionally planted-path only
- it does not yet attempt to reconstruct a richer natural treatment unit from
  legacy DAT assumptions
- the goal is to make the unattended BTC seam usable first, then widen the
  fidelity of the input payload after the runner + parser path is proven end to
  end

## First Post-TIPSY BTC CSV Parser Slice

The first conservative unattended BTC output parser slice is now in place in
FEMIC.

What it does:

- parses the vetted transposed `/TSR` output returned by the unattended BTC
  runner
- requires explicit `feature_id` in the returned CSV
- reads the safe proven age-series families:
  - `MVcon_*`
  - `MVdec_*`
  - `HTcon_*`
  - `HTdec_*`
  - `gVol_*`
  - `CC_*`
- converts those wide transposed rows into FEMIC's long-form managed-curve
  table structure
- maps stand identity back onto FEMIC managed-curve ids using:
  - preserve `feature_id` as-is when it is already in managed-curve-id space
    (`>= 20000`)
  - otherwise map legacy/raw stand ids with `managed_curve_id = 20000 + feature_id`

Current first-cut field decisions:

- `Yield = MVcon + MVdec`
- `Height = max(HTcon, HTdec)`
- `GrossYield = gVol`
- `CrownCover = CC`
- `DBHq = NaN`
- `TPH = NaN`

Why the placeholders remain:

- the unattended `/TSR` mashup currently gives us the proven safe four-indicator
  set plus explicit `feature_id`
- richer unattended DBHg / stems-per-ha output is not yet proven safe through
  the same report template seam
- so the first cut broadens Stage 01b to consume BTC CSV directly while making
  the missing stock-level fields explicit rather than silently inventing them

Current implementation implication:

- legacy `01b_run-tsa.py` should accept either:
  - legacy `.out` files, or
  - new unattended BTC `.csv` files
- the unattended BTC CSV path is now the preferred forward direction
- the legacy `.out` path remains only as a temporary compatibility bridge

K3Z smoke note:

- a real unattended BTC `/TSR` run against generated
  `external/femic-k3z-instance/data/03_input-tsak3z.csv` now succeeds and
  parses cleanly with the preserved `21000..23003` managed ids
- the remaining K3Z blocker is no longer BTC itself; it is the downstream
  legacy post-TIPSY bundle builder, which still requires the unshipped
  `external/femic-k3z-instance/data/vdyp_prep-tsak3z.pkl` checkpoint for full
  `tsa btc-post-tipsy` resume

## First End-to-End Orchestration Slice

The first orchestration slice that ties the new BTC seams together is now in
place.

What it does:

- adds `run_btc_and_post_tipsy_bundle_with_manifest(...)` in
  `src/femic/workflows/legacy.py`
- adds the new CLI surface:
  - `femic tsa btc-post-tipsy`
- for each selected TSA, the new workflow:
  1. reads canonical Stage 01a input from `data/03_input-tsaXX.csv`
  2. runs unattended BTC `/TSR`
  3. writes returned artifacts to:
     - `data/04_output-tsaXX.csv`
     - `data/04_error-tsaXX.csv`
  4. resumes the existing post-TIPSY bundle assembly against the new CSV
     output seam

Important compatibility choice:

- the old `femic tsa post-tipsy` surface remains intact
- it still defaults to the legacy `.out` seam unless explicitly given a
  different output-template path by orchestration code
- the new BTC orchestration path is additive for now, not yet a hard swap of
  the user-facing legacy resume command

Why this is the right intermediate shape:

- it gives FEMIC one real unattended Stage 01a -> BTC -> post-TIPSY resume path
  without destabilizing the long-lived manual `.out` resume surface
- it creates a clean place to do instance-level smoke testing before the repo
  docs and operator guidance are rewritten around BTC CSV as the default seam

## Incompatible Report-Type Constraint

Not every report template is a safe drop-in replacement for `TimberSupply.rpt`.

Observed failure modes:

- replacing `TimberSupply.rpt` with `TimberSupply SQL.rpt`:
  - loads successfully
  - then crashes during `BatchProcess()`
- replacing `TimberSupply.rpt` with an oversized `AllFieldsSQL.rpt`:
  - can crash even earlier during report load / startup

Current planning implication:

- BTC custom reports are real and powerful, but fragile
- FEMIC should not target arbitrary “all fields” generation as the first
  unattended design
- instead FEMIC should ship:
  - one or more vetted compatible transposed templates for unattended use
  - optional richer SQL/database templates only as supervised/manual mode

## Richer Yield-Report Fallback Decision

A manual BTC GUI run using the `Yield` report produced a much richer CSV output
surface including:

- `Year`
- `Height`
- `Volume Gross`
- `Volume`
- `Volume Conifer`
- `Volume Deciduous`
- `MAI`
- `Basal Area 0.0+`
- `DBHg 0.0+`
- `Stems Per Ha 0.0+`
- `Crown Cover`
- `Crop Trees Volume 12.5`
- `Crop Trees DBHg Mean`
- `Crop Trees Live Crown`

Current planning implication:

- this `Yield` report is the strongest current candidate for the optional
  richer-output BTC mode if FEMIC cannot unlock the same output set in a fully
  unattended CLI seam
- the richer-output path can remain human-assisted while the default
  `/TSR + /FLP` path becomes unattended

## Stand-Block Parsing Rule For Richer Yield Output

The richer `Yield` report CSV does not currently appear to carry an explicit
stand identifier column in each output row. Instead, the output appears as one
block of age rows per input stand.

Current parser rule:

- preserve the original input stand order from the canonical `MSYT.csv`
- parse the output as ordered stand blocks
- start a new stand block whenever age decreases relative to the previous row
  (for example `120 -> 0`, but the rule should be age-drop based rather than
  hard-coded to a specific maximum age)
- assign output block `n` to input stand `n`

Required safeguards:

- fail fast if output stand-block count does not equal input stand count
- fail fast if a stand block does not have strictly increasing ages after its
  first row
- do not silently tolerate dropped, reordered, or partial stand blocks

## SQL Report Breakthrough

A manual BTC GUI run using the `Timber Supply SQL` report produced a much more
useful rich-output artifact than the plain `Yield` CSV:

- output file:
  - `MSYT_output.sql`
- error file:
  - `MSYT_error.sql`
- explicit schema:
  - `CREATE TABLE BTC_STAND(...)`
  - `CREATE TABLE BTC_ERROR(...)`
- explicit stand identity fields:
  - `StandID`
  - `RowID`
  - `feature_id`

The tested `BTC_STAND` rows included:

- `feature_id`
- `Year`
- `VolumeCon`
- `VolumeDec`
- `HeightCon`
- `HeightDec`

Current planning implication:

- this is the strongest rich-output clue found so far because it removes the
  row-order-only stand-mapping problem
- even if richer GUI mode remains human-assisted, SQL-style output with
  explicit `feature_id` is much easier for FEMIC to parse safely than the plain
  `Yield` CSV block format
- if BTC can emit other custom reports in SQL mode with the same explicit
  stand identifiers, that may become the preferred optional rich-output path
- the older stand-block parsing rule should now be treated as a fallback for
  plain CSV reports that do not include explicit stand IDs, not as the
  preferred rich-output contract

## Output Field Map Clue

The installed file:

- `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt`

looks useful as the field map if FEMIC manages to unlock a richer BTC
non-GUI output mode beyond the simple TSR volume/height CSV.

What it appears to provide:

- stable BTC output keys for many stand-level and stock-level indicators
- direct naming clues for outputs such as:
  - `Volume000`, `Volume125`, `Volume175`
  - `BasalArea000`, `BasalArea125`, `BasalArea175`
  - `MeanDBHg000`, `MeanDBHg125`, `MeanDBHg175`
  - `StemCount000`, `StemCount125`, `StemCount175`
  - diameter-class stem / volume / VPT outputs
  - mortality, snag, and CWD outputs

Current planning implication:

- if FEMIC can identify a supported BTC CLI or project mode that emits richer
  outputs than the default TSR CSV, `OutputColumns.txt` should be treated as the
  first candidate mapping layer between BTC output fields and FEMIC downstream
  tables
- until that richer mode is proven, `OutputColumns.txt` is a valuable clue but
  not yet a live parser contract

## Genetic Gain Default Clue

The installed file:

- `C:\Program Files\TIPSY 4.7\BTC\gw.txt`

looks useful as a first-pass source of default FEMIC genetic gain settings for
the BTC cutover.

What it appears to provide:

- species-level default genetic-worth values
- default selection ages
- default index ages
- an explicit note that these defaults are for exploratory / educational use
  and that species without established values default to `0`

Current planning implication:

- when FEMIC moves from the old DAT seam to the BTC `MSYT.csv` seam, the Stage
  01a writer should have an explicit genetic-gain default policy
- `gw.txt` is the strongest current candidate for the initial default table
- this should be treated as a documented default set for educational workflows,
  not as an operational endorsement

## OAF Default Clue

The installed file:

- `C:\Program Files\TIPSY 4.7\BTC\oafs.txt`

also looks useful as a first-pass source for default FEMIC OAF settings during
the BTC cutover.

What it appears to provide:

- default behavior notes for OAF vector shapes and extrapolation
- built-in defaults for:
  - `OAF1`
  - `OAF2`
  - `DR`
  - `AT`
  - `ArmV`
  - `ArmM`
  - `DSG`
  - `DSC`
- explicit metadata about:
  - `ApplyAt`
  - `Type`
  - `Levels`
  - `Extrapolate`
  - optional filters like species, volume curve, BEC, coast/interior, and PNC

Current planning implication:

- the BTC cutover should define a clear default FEMIC OAF policy instead of
  relying on legacy DAT-era assumptions
- `oafs.txt` is the strongest current candidate source for initial default OAF
  definitions when generating BTC-compatible input
- this should be documented as a packaged BTC defaults source, not silently
  treated as an unquestioned operational standard

## Fertilizer Response Default Clue

The local BTC install also includes:

- `C:\Program Files\TIPSY 4.7\BTC\FertRespMOF.txt`

Current planning implication:

- this looks like the best current candidate source for initial FEMIC default
  fertilizer-response settings during the BTC cutover
- if FEMIC replaces legacy/manual BatchTIPSY assumptions with BTC-native CSV
  input generation, fertilizer-response defaults should come from this packaged
  BTC source instead of being silently improvised
- as with `gw.txt` and `oafs.txt`, these values should be treated as packaged
  BTC defaults that need to be documented explicitly rather than assumed to be
  universally authoritative

## VRI Species Mapping Clue

The local BTC install also includes:

- `C:\Program Files\TIPSY 4.7\BTC\vriSpecies.txt`

Current planning implication:

- this looks like the strongest current candidate packaged source for mapping
  VRI species codes into BTC / TIPSY species handling during the cutover
- if FEMIC moves to BTC-native CSV input generation, species translation should
  reuse this packaged BTC mapping clue instead of silently preserving older
  hard-coded or ad hoc species mappings
- this should be documented as an explicit BTC species-mapping dependency if it
  becomes part of the new Stage 01a input-generation contract

## Table / Range Output Clue

The local BTC install also includes:

- `C:\Program Files\TIPSY 4.7\BTC\TableRange.txt`

This does not currently look like a stand-growth parameter source in the same
sense as `gw.txt` or `oafs.txt`. Instead, it appears to define packaged table /
range presets for BTC reporting or chart output behavior, including:

- common age ranges such as `0-120`, `0-200`, `40-100`
- increment settings like `INC=1`
- maximums such as `MAX=200`
- named presets / labels such as `SGOG`, `Old Growth`, and `CULM`

Current planning implication:

- `TableRange.txt` is probably most useful as a clue about how BTC controls
  report/table output extents or preset output views
- if FEMIC eventually needs to drive a richer BTC output mode or mimic BTC's
  native reporting defaults, this file may help explain age-range and increment
  expectations
- for now it should be treated as an output/reporting clue, not as a primary
  source for stand parameter defaults

## Full Installation Deep-Dive Requirement

The current reverse-engineering effort should no longer be limited to the most
obvious BTC files.

Required deep-dive scope:

- all packaged PDFs under `C:\Program Files\TIPSY 4.7\`
- BTC report/template/config/default files
- Tcl scripts and helper metadata
- CHM help files, extracted into a platform-independent human-readable and
  machine-scannable format for later mining

Why this is now explicit:

- the `TIPSY-CBM.pdf` clue about `-RGM` shows there may still be meaningful
  undocumented or under-documented command-line seams outside the main BTC
  user guide
- the current implementation work has already benefited from clues spread
  across many packaged files (`OutputColumns.txt`, `gw.txt`, `oafs.txt`,
  `FertRespMOF.txt`, `vriSpecies.txt`, report templates, Tcl files)
- continuing this as an explicit tracked audit is better than relying on
  opportunistic discoveries in chat

## First Stand-Table Bank Probe Result

The first richer unattended stand-table bank probes were not successful through
the current `/TSR` seam.

What was tested:

- starting from the proven safe transposed unattended `/TSR` mashup that emits:
  - `MVcon_*`
  - `MVdec_*`
  - `HTcon_*`
  - `HTdec_*`
  - `gVol_*`
  - `CC_*`
- then adding one richer stand-table style column at a time, including:
  - `DBHg`
  - `SPH`
  - `StemCount000`
  - `StemCount125`
  - `StemCount175`
  - `Crop250VolUtil125`
  - `Crop250DBHgMean`
  - `Crop250LiveCrown`

Observed result:

- these probes did not complete cleanly
- on-screen BTC behavior was stacked `.NET` modal crash dialogs
- representative failure mode was:
  - `System.NullReferenceException`
  - in `TIPSY.frmTIPSY.BatchProcess()`

Current planning implication:

- the unattended `/TSR` seam is only proven safe for the current conservative
  default bank
- richer stand-table outputs should be treated as exploratory seam-finding work
  until a compatible template family or alternate BTC mode is proven
- FEMIC should not assume that simply appending richer stand-table fields to the
  current unattended `TimberSupply.rpt` mashup will work

Current working method for issue `#47`:

- keep unattended `/TSR` as the priority path
- start from the current known-good unattended transposed template
- add one new stand-table indicator column at a time
- if a probe passes, keep that column in the candidate bank
- if a probe crashes, immediately revert that one column and record the failure
  as a seam-detection clue
- build the first bank with two outputs in parallel:
  - the largest proven-safe unattended template subset
  - an evidence map explaining what seems to separate `/TSR`-compatible columns
    from `/TSR`-incompatible ones
- use FEMIC-managed BTC modal cleanup as part of the normal probe loop so
  failed probes do not leave a human blocked behind stacked `.NET` dialogs
- write a machine-readable compatibility ledger after every probe so the seam
  evidence survives beyond console output

That second output is important. Every failing column should now trigger a
high-priority parallel clue-collection step, including:

- exact report token syntax
- whether the token appears in stock `Yield.rpt`, `Stand.rpt`, or SQL-style
  templates
- whether the token is utilization-qualified (`:000`, `:125`, `:Auto`)
- whether it looks like a stand-table, crop-tree, or aggregated stand metric
- whether a similar field is available through a different report family
- whether the failure pattern suggests a structural rule that could later
  support a workaround or hack

## First Unattended Ratchet Batch with Auto-Close

The first full seven-column unattended stand-table batch now completed under
FEMIC control with no human dialog-clicking required.

Candidate batch:

- `MAI`
- `BasalArea:000`
- `DBHg:000`
- `SPH:000`
- `StemCount000`
- `StemCount125`
- `StemCount175`

Observed result:

- every candidate failed in the current transposed unattended `/TSR` seam
- every failure was normalized into the same machine-readable pattern:
  - BTC exit code `1`
  - no output CSV produced
  - BTC/.NET modal dialog auto-closed by FEMIC
  - failure classified as `missing_output_exit_1`
- the compatibility ledger was written to:
  - `tmp/btc_probe_sweep/first_batch/compatibility.json`

Current evidence pattern:

- `MAI`, `BasalArea:000`, `DBHg:000`, and `SPH:000` all appear in stock
  `Yield.rpt`, but still fail in the unattended transposed `/TSR` seam
- `StemCount000/125/175` appear in `OutputColumns.txt` and BTC Tcl metadata,
  but do not appear in stock `Yield.rpt`, and they also fail in the same seam

Current planning implication:

- the incompatibility boundary is likely not just about token spelling; it is
  probably tied to the report family/shape of the transposed unattended `/TSR`
  template itself
- the next probes should continue one column at a time, but with higher
  attention to structural families and adjacent variants rather than assuming
  any stock `Yield.rpt` token is safe in unattended `/TSR`

## Critical `/TSR` Overlay Precedence Breakthrough

One of the most important Phase 48 reverse-engineering results is that plain
installed ``TIPSYbtc.exe /TSR`` does **not** behave as if it were bound only to
the stock report under ``C:\Program Files\TIPSY 4.7\BTC``.

Live behavior proved the following:

- installed ``/TSR`` consults the per-user overlay report under the current
  user's Windows Documents folder:
  - ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``
  before falling back to the stock installed ``TimberSupply.rpt``
- with the user overlay present and broken, plain installed ``/TSR`` fails
- when the user overlay is moved out of the way, plain installed stock
  ``/TSR`` succeeds again
- when the user overlay is replaced with a **stock-based safe enhanced TSR
  template**, plain installed ``/TSR`` also succeeds

This means the true unattended seam is:

- preserve the hidden stock ``TimberSupply.rpt`` structure
- extend that structure conservatively through the live overlay path
- test plain installed ``/TSR`` against that overlay
- force the live TSR overlay horizon to:
  - ``TableRange=0-350:10|# MAX=350 INC=10``
- resolve the overlay path generically from the current user's Windows
  Documents directory rather than assuming a machine-specific OneDrive path
  so unattended BTC output lines up with FEMIC's longer VDYP curve timeline
  instead of stopping at the stock 120-year range

It also means the earlier copied-install/generated-template probes were too
pessimistic as a general seam detector. They were useful clues, but they were
not testing the most faithful `/TSR` contract.

Current rule going forward:

- when probing new unattended `/TSR` columns, prefer the **real overlay seam**
  over a clean-room generated replacement template
- preserve the stock report shape whenever possible
- treat failures from stand-alone replacement templates as seam clues, not as
  proof that a token is impossible through `/TSR`

## Overlay-Seam Ratchet Correction

After restoring a stock-based safe enhanced overlay and probing the same first
stand-table batch against the real overlay seam, the earlier “all seven fail”
conclusion was overturned.

The following columns all passed cleanly through plain installed ``/TSR``:

- ``MAI``
- ``BasalArea:000``
- ``DBHg:000``
- ``SPH:000``
- ``StemCount000``
- ``StemCount125``
- ``StemCount175``

This is the strongest current evidence that:

- the key compatibility boundary is structural to the stock TSR report
  contract, not merely the output tokens themselves
- preserving and extending the stock/user-overlay ``TimberSupply.rpt`` path is
  the correct ratchet for issue ``#47``
- future optional indicator-bank work should continue to use the overlay seam
  as the primary reverse-engineering surface unless new evidence proves a
  better boundary

## First Optional Unattended Indicator Bank

The first FEMIC-level optional BTC indicator-bank switch is now wired through
the real unattended `/TSR` overlay seam.

Current switch:

- ``--indicator-bank stand-structure-basic``

Current bank contents:

- ``MAI``
- ``BasalArea:000``
- ``DBHg:000``
- ``SPH:000``
- ``StemCount000``
- ``StemCount125``
- ``StemCount175``

Critical runtime implementation detail:

- the runtime must patch the real per-user overlay report path
  ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt`` with backup/restore;
- relying only on a copied-install-local ``TimberSupply.rpt`` is not
  sufficient, because the live user overlay can silently shadow that local
  file and make a run appear successful while dropping the bank columns from
  the returned output.

Real smoke proof:

- ``femic tipsy run-btc <MSYT.csv> --indicator-bank stand-structure-basic``
  now returns, in one unattended output CSV:
  - the base conservative families:
    - ``MVcon_*``
    - ``MVdec_*``
    - ``HTcon_*``
    - ``HTdec_*``
    - ``gVol_*``
    - ``CC_*``
  - plus the first stand-structure bank:
    - ``MAI_*``
    - ``BasalArea000_*``
    - ``DBHg000_*``
    - ``SPH000_*``
    - ``StemCount000_*``
    - ``StemCount125_*``
    - ``StemCount175_*``
- the 350-year TSR horizon remains intact at the same time.

Immediate next step:

- pilot this first bank only on a dedicated K3Z ``intensive_*`` proving-ground
  subvariant before touching any student-facing variants.
- keep the bank-enabled BTC/TIPSY managed-curve bundle at the shared K3Z data
  layer if needed, but surface the new Patchworks feature/account bindings only
  on that proving-ground surface during the first rollout.

That first proving-ground rollout is now live:

- runtime config:
  - ``config/patchworks.runtime.intensive_light_standstructure.windows.yaml``
- launch entrypoint:
  - ``models/k3z_patchworks_model/analysis/intensive_light_standstructure.pin``
- tracks surface:
  - ``models/k3z_patchworks_model/tracks_intensive_light_standstructure/``

What was smoke-verified after the rollout:

- the rebuilt proving-ground ``forestmodel.xml`` contains the new managed
  feature bindings:
  - ``feature.MAI.managed.*``
  - ``feature.BasalArea000.managed.*``
  - ``feature.DBHg000.managed.*``
  - ``feature.SPH000.managed.*``
  - ``feature.StemCount000.managed.*``
  - ``feature.StemCount125.managed.*``
  - ``feature.StemCount175.managed.*``
- the rebuilt proving-ground ``tracks_intensive_light_standstructure`` surface
  contains 84 managed stand-structure feature-account rows with area-normalized
  ``SUM`` multipliers in ``accounts.csv``;
- the ordinary ``base`` and ``ctfert_l15h5`` tracks remain at zero rows for
  this bank, confirming that the first Patchworks rollout stayed quarantined to
  the dedicated proving-ground surface.

Quick manual developer validation checkpoint:

- the developer manually launched the proving-ground Patchworks surface and
  reported that it "looks pretty good";
- treat that as positive end-to-end confirmation that the first unattended BTC
  stand-structure bank is broadly working in the intended proving-ground
  runtime;
- however, slower indicator-by-indicator interpretation, validation, and
  possible pruning of the bank contents is still expected later and should be
  treated as follow-on refinement work rather than a blocker to this first
  rollout.

## Post-Cutover K3Z QMD Regression and Repair

The first core unattended BTC cutover landed with a real K3Z regression:

- launched K3Z Patchworks surfaces still contained the expected QMD account
  names and XML attributes;
- but both standing `feature.QMD.*` and harvested `product.QMD.*` surfaces were
  effectively empty at runtime.

Confirmed root cause:

- the unattended BTC seam now returns a conservative managed-curve bundle that
  does not include live managed `TPH`;
- `tipsy_curves_tsak3z.csv` therefore carried blank `TPH` for the managed side;
- managed QMD generation in the Patchworks exporter was still assuming that a
  managed `TPH` curve existed, so the managed QMD path collapsed even though
  the accounts/features/attributes still existed syntactically.

Repair that is now in place:

- FEMIC now falls back to Stage 01a / BTC-input stand density for:
  - managed standing stems-per-ha curves when managed `TPH` is absent;
  - managed QMD generation when managed `TPH` is absent.
- This restored non-empty QMD surfaces across the rebuilt K3Z family:
  - `base`
  - `ctfert_*`
  - `pct_*`
  - `intensive_*`
  - overlays

Important boundary learned during the same bugfix:

- first attempts to restore a true BTC-native managed stand-structure signal in
  the unattended `/TSR` seam still fail at runtime;
- this includes probes using the exact stock `Yield.rpt` token forms:
  - `SPH:000`
  - `DBHg:000`
  - `BasalArea:000`
- these probes still crash BTC in `BatchProcess()`

Current planning implication:

- the K3Z QMD regression is repairable and can be closed on the managed-density
  fallback path;
- restoring richer live BTC-native stand-structure signals remains separate
  seam-finding work under the optional indicator-bank tasks, especially issue
  `#47`.

## First Implementation Slice

1. Lock the new BTC seam into repo planning and contracts.
2. Add a deterministic `MSYT.csv` writer from the Stage 01a payload.
3. Add Windows BTC executable discovery and a supervised `/TSR` runner.
4. Add Stage 01b / post-TIPSY parsing for returned BTC CSV output.
5. Make downstream replacement for old `.out`-era support fields explicit,
   especially where later QMD / stems logic currently depends on fields like
   `TPH` or `DBHq`.
6. Define and document the initial FEMIC genetic-gain default policy using
   `gw.txt` as the first candidate source.
7. Define and document the initial FEMIC OAF default policy using `oafs.txt` as
   the first candidate source.
8. Use `OutputColumns.txt` as the first candidate output-field map if a richer
   supported BTC output mode is identified.
