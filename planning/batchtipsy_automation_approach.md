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
