# FAN$IER Linkage Investigation

Date: 2026-03-29

Governing tracker

- GitHub issue `#59`

Goal

- Find the most automatable FEMIC seam for preparing and extracting FAN$IER
  economics results from BTC/TIPSY-side AU inputs.

Working standard

- First-class result:
  - unattended or effectively unattended multi-regime FAN$IER extraction for
    any number of AU profiles, with FEMIC preparing the necessary upstream
    BTC/TIPSY inputs and harvesting structured results.
- Next-best result:
  - FEMIC can synthesize valid `.rgm` / `.eco` inputs and clearly document the
    remaining human-in-the-loop boundary if full headless FAN$IER execution is
    not real.

Preferred economic extraction posture

- If FAN$IER extraction becomes viable, prefer exporting raw or effectively
  undiscounted outputs at a null (`0`) discount rate.
- Treat discounting as a downstream FEMIC/post-processing concern unless
  FAN$IER-specific discount-side behavior is itself the subject of analysis.
- Rationale:
  - FEMIC should not depend on FAN$IER's built-in constant-rate discounting
    assumptions when downstream analysis may want:
    - no discounting;
    - alternate discount curves;
    - time-varying discount profiles;
    - or other pedagogical/economic comparison treatments over very long
      planning horizons.

## Confirmed File Types

- `.fns`
  - FAN$IER project file.
  - Plain text container, not opaque binary.
  - Can embed one or more regime/economics sections.
- `.rgm`
  - Regime file used by FAN$IER batch mode.
  - Plain text; loaded with `File.ReadAllLines(..., Encoding.UTF7)`.
  - Contains regime description plus product-based yield and activity data.
- `.eco`
  - Economics file used by FAN$IER batch mode.
  - Can be embedded with regime data or supplied separately.

## Confirmed Runtime Surfaces

Installed runtime roots

- `C:\Program Files\TIPSY 4.7\Fansier\`
- `C:\Program Files\TIPSY 4.7\BTC\`

Sample assets

- `C:\Program Files\TIPSY 4.7\Fansier\Samples\sample.fns`
- `C:\Program Files\TIPSY 4.7\Fansier\Samples\July 22f.fns`

Extracted help surface

- `reference/tipsy/chm_extracted/Fansier/`

Decompiled scratch

- `tmp/ilspy_fansier/`
- regenerated deterministically from the installed binary with:
  - `C:\Users\gep\.dotnet\tools\ilspycmd.exe -p -o tmp\ilspy_fansier --disable-updatecheck "C:\Program Files\TIPSY 4.7\Fansier\Fansier.exe"`
- primary files to cite going forward:
  - `tmp/ilspy_fansier/Fansier/frmFansier.cs`
  - `tmp/ilspy_fansier/Fansier/frmBatch.cs`
  - `tmp/ilspy_fansier/Fansier/modRegime.cs`

Related BTC decompiled scratch

- `tmp/ilspy_btc/`
- regenerated deterministically from the installed binary with:
  - `C:\Users\gep\.dotnet\tools\ilspycmd.exe -p -o tmp\ilspy_btc --disable-updatecheck "C:\Program Files\TIPSY 4.7\BTC\TIPSYbtc.exe"`
- primary files to cite going forward:
  - `tmp/ilspy_btc/TIPSY/frmTIPSY.cs`
  - `tmp/ilspy_btc/TIPSY/modBTCfile.cs`

## Confirmed Code-Backed Findings

### 1. FAN$IER command-line startup is weak

From `Fansier.frmFansier.ProccessCommandLine()`:

- startup loops over `MyProject.Application.CommandLineArgs`
- for any existing file path, it calls `modRegime.LoadProject(text)`
- there is no evidence here of:
  - batch auto-start
  - report auto-export
  - hidden CLI batch execution

Current best read

- startup args appear to be a project-load convenience seam, not a real
  unattended processing contract.

### 2. FAN$IER has a real temp-folder regime intake seam

From `Fansier.frmFansier.SetPaths()`, `timStart_Tick()`, and
`watchTemp_Created()`:

- FAN$IER creates and uses:
  - `%TEMP%\\Fansier\\`
- on startup it sets:
  - `watchTemp.Path = modRegime.pathTemp`
- it can auto-open `.rgm` files already present in that temp folder
- it also reacts to newly created `.rgm` files and imports them into the live
  app via `AddTempFiles(...)`

This is the strongest concrete TIPSY-to-FAN$IER linkage seam found so far.

Current best read

- the practical integration model is likely:
  - external app writes `.rgm` into `%TEMP%\\Fansier\\`
  - FAN$IER notices and imports it
- this matches the product's own TIPSY/TASS integration story better than any
  supposed CLI batch seam found so far.

Live validation

- Confirmed on 2026-03-29 with a live manual-supervised probe:
  - launched one clean FAN$IER GUI session;
  - extracted the first standalone regime block from the shipped sample
    `sample.fns` into:
    - `tipsy_io/logs/fansier_probe/TFL44 u 200.rgm`
  - copied that file into:
    - `%TEMP%\\Fansier\\probe_TFL44_u_200.rgm`
  - FAN$IER immediately loaded the regime into the running session.

Interpretation

- the `%TEMP%\\Fansier\\` watcher seam is not just a decompiled hypothesis; it
  is a live confirmed integration path.
- This means FEMIC can plausibly stage `.rgm` files for a running FAN$IER
  session without navigating the GUI import path manually.

### 3. FAN$IER batch mode is real, but GUI-driven

From `Fansier.frmBatch`:

- batch mode processes:
  - one or more `.rgm`
  - optional `.eco`
  - discount assumptions
  - product groups
  - harvest ages
- the user chooses:
  - output folder
  - run identifier
  - report type (`txt`, `csv`, `pdf`)
  - short/long report options
  - product/activity column options
- `Start Batch` is the action trigger

Current best read

- FAN$IER definitely has a substantial batch report engine
- but the decompiled code inspected so far shows it as a GUI-driven workflow,
  not a clean command-line one

### 4. Batch report filenames are deterministic

From `Fansier.frmBatch.cmdBatch_Click(...)`:

Long report filenames are built as:

- `<txtPath><RunID> - <rgm.filename> - <eco.Header.Name> - <discount> - <product> - <harvest>.{txt|csv|pdf}`

Short report filenames are built as:

- `<txtPath><RunID>.{txt|csv|pdf}`

This is useful for future FEMIC-side harvesting even if the batch click remains
human-triggered.

### 5. `.rgm` writing is concrete enough to target

From `Fansier.modRegime.WriteRGM(...)` and `SaveRegEcoFile(...)`:

Confirmed major sections include:

- `*AppType`
- `*Run`
- `*ShortHeader`
- `*Header`
- `*FansierVars`
- `*FansierData`
- `*Activities`
- repeated `*Product`

Confirmed important `*FansierVars` keys include:

- `GYMODEL`
- `REGIONCODE`
- `DISTRICTCODE`
- `BEC`
- `SLOPE`
- `OAF1`
- `OAF2`
- `MERCHLIMIT`
- `BASEYEAR`
- optional `ESTABLISHED`
- optional `AREA`

Confirmed `*FansierData` row contract starts with:

- `#Link Age Ht gVol mVol gStems mStems gVPT mVPT LRF <species...>`

Current best read

- direct FEMIC-side `.rgm` synthesis is plausible
- and may be a more promising automation seam than hunting for a nonexistent
  FAN$IER batch CLI

Minimum viable `.rgm` load findings so far

- Known-good shipped standalone sample:
  - `C:\Program Files\TIPSY 4.7\BTC\Samples\TIPSY45 Sample.rgm`
- Live reduction tests against the temp-folder watcher seam now show:
  - `*AppType + *Run + *FansierVars + *FansierData + *Product`
    is sufficient for a clean live regime load
  - `*ShortHeader` and `*Header` are not required just to load a regime
  - `*Activities` and trailing `*Data` are not required just to load a regime
  - dropping all `*Product` sections is not safe for UI loading:
    - FAN$IER throws a `SelectedIndex` / `cProductGroups[0]`-style regime UI
      exception after the watcher import
  - one valid `*Product` block is enough for a clean live load:
    - the full shipped product catalog is not required just to import a regime
    - current reduced known-good probe:
      - `tipsy_io/logs/fansier_probe/TIPSY45 Sample_one_product.rgm`
  - `*FansierVars`, `*Run`, and `*AppType` are all load-optional in the
    watcher-import path:
    - probes with only `*FansierData + one valid *Product block` still loaded
      cleanly as long as row alignment was preserved
  - one aligned `*FansierData` row plus one aligned `*Product` data row is
    sufficient for a clean live load:
    - current reduced known-good probe:
      - `tipsy_io/logs/fansier_probe/TIPSY45 Sample_ultramin_clean_1row.rgm`
  - zero-row regimes are not UI-safe even when the section grammar is valid:
    - the corrected zero-row probe reached regime selection, then FAN$IER threw
      an `IndexOutOfRangeException` in `cmbHarvAge_SelectedIndexChanged(...)`
      because no usable harvest-age rows existed

Current best read

- For a FEMIC-generated regime whose first goal is to load cleanly into a live
  FAN$IER session, the current minimum viable contract looks like:
  - `*FansierData`
    - with at least one real data row
  - at least one valid `*Product` block
    - with matching row count and at least one real data row
- Everything else should currently be treated as optional for live watcher
  loadability until proven otherwise.

### 6. BTC-specific linkage clue is real

From `Fansier.modRegime.LoadRegVars(...)` and installed changelog/help:

- `BatchTIPSY Composer` is explicitly recognized as a growth/yield source
- FAN$IER maps that source to:
  - `GYModelName = "TIPSYbtc"`
  - `GYModelPath = pathRoot + "BTC\\TIPSYbtc.exe"`
- installed `Fansier\\changelog.txt` says:
  - FAN$IER v2.3 can receive area and age or establish year from
    BatchTIPSY Composer via the `.rgm` file

Current best read

- the intended BTC-to-FAN$IER contract is likely regime-file-driven, not
  command-line-message-driven.

## What Looks Automatable Right Now

- FEMIC can likely prepare FAN$IER-facing data by:
  - running BTC/TIPSY upstream
  - synthesizing or exporting `.rgm`
  - synthesizing or exporting `.eco` where needed
  - staging those files in deterministic folders
- FEMIC can now be more specific about one confirmed handoff:
  - dropping a valid `.rgm` into `%TEMP%\\Fansier\\` will load it into a live
    FAN$IER session.
- FEMIC can likely harvest batch outputs deterministically once produced,
  because report naming is explicit and machine-friendly.

## Batch Report Minimums (Code-Backed)

From `Fansier.frmBatch.UpdateStatus(...)` and `cmdBatch_Click(...)`:

- Batch mode can run with no `.eco` files if `Use defaults` is selected.
- In that mode, the practical minimum report prerequisites are:
  - at least one loaded regime in `lstRegime`
  - at least one checked discount-assumptions set in `lstSettings`
  - at least one selected product group / product view
  - at least one selected harvest-age option
  - a valid writable report path
  - one selected report type (`txt`, `csv`, or `pdf`)
- The built-in default discount assumptions set is:
  - `Fansier Defaults   (Discount Rate = 2%)`

Interpretation

- A separate `.eco` file is not inherently required for batch reporting.
- That makes regime-only batch experiments plausible once we move from import
  testing to useful output testing.

### Null-discount feasibility

From `Fansier.frmDiscountAssumptions`:

- discount rate is editable and clamped to:
  - minimum `0%`
  - maximum `30%`
- reinvestment rate is editable and clamped to:
  - minimum `0%`
  - maximum `10%`

Interpretation

- FAN$IER explicitly allows a `0%` discount rate and a `0%` reinvestment rate.
- So the preferred FEMIC posture of extracting raw/null-discount outputs is
  compatible with the shipped FAN$IER discount-assumptions editor.

## First Real Batch Extraction Proof

Live validation on 2026-03-29

- Started from the current lowest clean watcher-import probe:
  - `tipsy_io/logs/fansier_probe/TIPSY45 Sample_ultramin_clean_1row.rgm`
- Confirmed that this regime still loads through the live
  `%TEMP%\\Fansier\\` watcher seam.
- Opened FAN$IER batch mode and confirmed an important UI/runtime boundary:
  - batch mode does not inherit the currently loaded main-window regime;
  - the batch form maintains its own `lstRegime` collection and requires
    regimes to be added explicitly through the `+` button / `LoadBatchRgm(...)`
    file-dialog path.
- With that one-row regime loaded into batch mode, `Use defaults` selected,
  `Fansier Defaults   (Discount Rate = 2%)` checked, one product selected,
  one age selected, and output path set to:
  - `tipsy_io/logs/fansier_probe/batch_smoke/`
  the `Start Batch` button enabled and FAN$IER emitted a real CSV report:
  - `tipsy_io/logs/fansier_probe/batch_smoke/Report.csv`
- The output is economically degenerate but structurally real:
  - one result row was written for the minimal regime;
  - values are mostly `0` / `n/c`, which is consistent with a one-row
    ultramin input rather than a richer operational regime.

Interpretation

- The current one-row minimum regime is not merely importable; it is also
  batch-extractable.
- A separate `.eco` file is still not required for that batch report path when
  `Use defaults` is selected.
- The next useful question is no longer "can FAN$IER emit anything from a
  reduced regime?" but rather:
  - what richer regime content is needed before the emitted report becomes
    analytically useful rather than just structurally valid; and
  - whether the same path works cleanly with an explicit `0%` discount
    assumptions set.

## What Is Still Unproven

- any useful command-line seam that:
  - opens batch mode
  - loads `.rgm` / `.eco` directly
  - starts `Start Batch` without clicks
- whether FAN$IER's `0%` discount assumptions can be persisted or loaded
  across fresh sessions without GUI automation
- whether the remaining quoted/comma-formatted activity-cost columns in batch
  CSV output can be normalized purely through existing FAN$IER export options

## Current Best Hypothesis

- the real practical seam is:
  - FEMIC prepares `.rgm` / `.eco`
  - FAN$IER ingests regimes through its temp-folder watcher and/or scripted
    batch-form import/export flows
  - fully unattended execution is achievable through GUI automation even though
    a useful command-line startup seam still has not been found

## New Proof: Fully Unattended Fresh-Session Batch Extraction

- The repo-local smoke `tmp/fansier_batch_fresh_session_smoke.py` now proves a
  fresh FAN$IER session can be driven end to end without user clicks:
  - kill existing FAN$IER processes
  - relaunch FAN$IER
  - open batch mode from the main toolbar
  - load a standalone `.rgm` through the batch form's `+` picker
  - create `FEMIC Raw 0%` on the fly if it is absent
  - select one discount set, one product group, and one harvest age
  - start batch and wait for `Done`
  - harvest the emitted CSV
- The current proof run succeeded with:
  - regime:
    `C:\Users\gep\OneDrive - UBC\Documents\TIPSY\test1\Batchbiomass-10000.rgm`
  - output:
    `tipsy_io/logs/fansier_probe/batch_auto/AutoSmoke.csv`
  - discount assumptions:
    `FEMIC Raw 0%`
- This is now the first real proof that FAN$IER extraction can be run
  unattended in practice, even though the seam is GUI automation rather than a
  native headless CLI contract.
- Remaining CSV caveat:
  - disabling the batch-form `Use comma for thousands separator` checkbox is
    necessary and now automated;
  - even so, some activity-cost columns still arrive as quoted values with
    thousands separators (for example `"4,056.43"`), so downstream FEMIC CSV
    normalization still needs to treat those fields cautiously.

## Current Format Lane

- `txt` is currently the better machine-ingest export format than `csv`.
- Live unattended A/B results:
  - `CompareCSV.csv` preserved the same economics columns, but still required
    CSV quoting around some comma-formatted activity-cost fields.
  - `CompareTXT.txt` emitted the same short-report payload as a tab-delimited
    text file, which avoids the CSV quoting fight entirely.
- Additional format-cleaning result:
  - disabling activity columns (`ShortReportActivityCols = False`) removes the
    remaining comma-heavy activity-detail tail while preserving the core row:
    - regime/economics/discount/product/age identifiers
    - major standing-yield and product metrics
    - total treatment/harvest/road/manufacturing cost summaries
    - discounted benefits/costs, NPV, SV, IRR, and B/C
- Current preferred machine-ingest lane:
  - report type: `txt`
  - short report: `True`
  - product columns: `True`
  - activity columns: `False`

## Long Report Surface

- Unattended `long report` generation is now proven too.
- Proof artifact:
  - `tipsy_io/logs/fansier_probe/long_compare/LongTXTLean - Batchbiomass-10000.rgm - {defaults} - FEMIC Raw 0% - Lumber & Mill Residues (All Grades) - Max MAI (12.5).txt`
- Initial interpretation:
  - long report is much richer and more narrative than the lean short/txt lane;
  - it includes structured sections such as:
    - `Results`
    - `Harvest Summary`
    - `Discount Assumptions`
  - so long report looks like the better "pump FAN$IER for all it has"
    discovery/export surface, while short/txt remains the better current
    FEMIC-ingest lane.

## "All Outputs" Boundary

- Current evidence says "all outputs" is **not** just an `.rgm` construction
  problem.
- The `.rgm` determines which product groups/regime content FAN$IER knows
  about, but the batch form still controls:
  - short vs long
  - selected discount assumptions
  - selected product groups
  - selected harvest ages
  - product/activity column toggles
- Live maximal-selection proof now exists:
  - output directory:
    - `tipsy_io/logs/fansier_probe/diag_allprod_oneage/`
  - proven successful batch state:
    - `1` checked regime
    - `1` checked discount setting
    - `6` checked product groups
    - `28` checked harvest ages
    - `168` generated long-report `txt` files
  - FAN$IER's own bottom-of-form label at success read:
    - `1 Regimes X 1 Assumptions X 6 Products X 28 Ages = 168 calculations`
  - inspected sample output confirms materially populated economics, not empty
    placeholders.
- Reframed interpretation:
  - the earlier automated failures were false negatives caused by driving the
    checked-list controls faster than FAN$IER's internal state-update logic
    could refresh `lblRuns` and `Start Batch`.
  - this means the all-product-group / multi-age fan-out is **possible**.
  - the remaining seam is now clearly UI pacing/synchronization, not missing
    `.rgm` content.
- Immediate automation consequence:
  - unattended automation should treat the calculations label (`lblRuns`) as a
    sync surface.
  - checkbox state alone is not enough; the script should wait for coherent
    calculation-count updates before continuing or clicking `Start Batch`.

## Broad Unattended Proof

- Fresh-session unattended FAN$IER batch extraction is now proven on the broad
  fan-out path too.
- Proof artifact root:
  - `tipsy_io/logs/fansier_probe/batch_auto_native_all/`
- Successful unattended run shape:
  - clean FAN$IER launch with no preloaded main-window regime;
  - open `Batch` directly from the main toolbar;
  - load `Batchbiomass-10000.rgm` into the batch form;
  - load `FEMIC Raw 0%` from `.dis`;
  - force `Use default (1st) product group` off;
  - use the batch checked-list context-menu `Check All` path for:
    - product groups;
    - harvest ages;
  - run long-report `txt` output.
- Confirmed successful unattended batch state:
  - `1 regime`
  - `1 assumptions set`
  - `6 products`
  - `300 ages`
  - `1,800` generated long-report files
- Inspected output confirms materially populated economics, for example:
  - `AutoAllProdAllAges - Batchbiomass-10000.rgm - {defaults} - FEMIC Raw 0% - Lumber & Mill Residues (All Grades) - 170.00.txt`
- Important implementation clues that made this stable:
  - the `Batch` form is reachable from a clean FAN$IER launch without loading a
    bogus `.rgm` into the main window first;
  - the native checked-list context menu (`Check All` / `Uncheck All`) is the
    reliable broad-selection seam because it uses FAN$IER's own
    `SetItemChecked(...)` + `UpdateStatus()` path;
  - UIA checkbox states alone were not reliable enough for broad selections.

## Discount-Assumptions File Seam

- FAN$IER has a native discount-assumptions file contract:
  - extension: `.dis`
  - main-window menu path:
    - `Discount Assumptions -> Load Discount Assumptions...`
    - `Discount Assumptions -> Save Discount Assumptions...`
- Decompiled parser/writer surfaces:
  - `modFANSIER.LoadDiscountAssumptions(...)`
  - `modFANSIER.AddDiscountAssumptions(...)`
- Confirmed file format fields include:
  - `DiscountRate`
  - `RealPriceInc`
  - `RealCostInc`
  - `RealIncDuration`
  - `DeflationRate`
  - `ReinvestmentRate`
  - `IncludeSunkCosts`
  - `FinancialAnalysis`
  - `RegenCostAtHarvest`
  - `OverrideName`
  - `UserOverride`
- A synthesized file now exists at:
  - `tipsy_io/logs/fansier_probe/FEMIC Raw 0%.dis`
- Live proof:
  - loading that `.dis` through FAN$IER's own menu adds `FEMIC Raw 0%` to the
    batch form's discount-assumptions list in a fresh session.
- This means GUI-side profile creation is no longer the only known seam.
- What is still open:
  - the combined unattended path is already stable when it creates
    `FEMIC Raw 0%` via the editor;
  - the `.dis` load seam works, but it is not yet the default unattended path
    because the menu/dialog sequence still needs one more round of hardening.

## Next High-Value Experiments

1. Live-validate the temp-folder watcher seam.
   - Done:
     - Launch FAN$IER normally.
     - Drop a valid `.rgm` into `%TEMP%\\Fansier\\`.
     - Confirmed that the regime auto-imports.
2. Build a minimal FEMIC-readable `.rgm` schema note.
   - In progress:
     - current live watcher floor appears to be:
       - `*FansierData` with at least one row
       - one valid aligned `*Product` block with at least one row
     - `*AppType`, `*Run`, `*FansierVars`, `*ShortHeader`, `*Header`,
       `*Activities`, and trailing `*Data` are currently load-optional.
   - Next:
     - probe whether the single-row floor can be synthesized with different
       species/product labels or whether it depends on shipped product catalog
       names
     - probe whether a minimal `.eco` sidecar or embedded ECO content changes
       anything for batch/report preparation beyond pure regime import
3. Probe whether registry-preseeded batch settings reduce the GUI boundary.
   - Done for the current unattended proof:
     - `RunIdentifier`
     - `BatchPath`
     - report type / short/long toggles
     - `ThousandSeparator = False`
   - Next:
     - determine whether any additional registry state can remove the need to
       create `FEMIC Raw 0%` through GUI automation on each fresh session;
     - harden the new `.dis` load seam enough to replace editor-driven profile
       creation in the unattended batch smoke.
4. Inspect whether any remaining decompiled startup branch can auto-open
    batch mode or consume temp `.rgm` files without manual navigation.
5. If batch extraction becomes reachable, validate whether a null-discount
   configuration is sufficient to treat FAN$IER as a raw economics extractor
   while leaving discounting entirely to downstream FEMIC analysis.
6. Shift the next live probe from importability to report usefulness:
   - Done for the first threshold:
     - the current ultramin one-row regime now emits a real CSV batch report
       under `Use defaults` with the shipped 2% assumptions set.
   - Done:
     - repeat the same smoke with an explicit `0%` discount-assumptions set;
     - run the same path against at least one richer known-good `.rgm`.
   - Current richer unattended proof:
     - `Batchbiomass-10000.rgm` now batch-runs unattended under
       `FEMIC Raw 0%` and emits materially populated economics in
       `tipsy_io/logs/fansier_probe/batch_auto/AutoSmoke.csv`.
   - Next:
     - Done:
       - compared `csv` vs `txt` on the same unattended richer run;
       - confirmed `txt` is tab-delimited and cleaner for machine ingest;
       - confirmed disabling activity columns removes the remaining
         comma-heavy activity-detail tail.
     - Next:
       - validate whether the chosen lean lane
         (`txt` + no activity columns) remains sufficient across additional
         known-good `.rgm` examples.
       - Done:
         - unattended `long report` smoke against the richer known-good regime;
         - confirmed that long report is a richer sectioned export surface than
           the current lean short/txt lane.
       - In progress:
         - unattended "maximal extraction" smoke with all product groups and
           all harvest ages selected.
       - Current read:
         - the blocker is now the batch form's internal checked-list
           event/counter seam, not a missing `.rgm` output family.
         - thinning the ages to sampled numeric-only ages did not resolve it,
           so the product-group side is now the sharper target.
       - Next:
         - harden multi-select event propagation for batch product/age lists so
           the "all outputs" run becomes startable;
         - once that works, compare maximal long-report output against the lean
           short/txt lane and decide whether FEMIC should archive both.
7. Preserve deterministic decompile notes while this issue is active.
   - Treat `tmp/ilspy_fansier/` and `tmp/ilspy_btc/` as the canonical local
     scratch locations for managed-source inspection on this machine.
   - Do not rely on ephemeral decompile output paths or chat memory for source
     file locations again.
