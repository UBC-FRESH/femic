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

## What Is Still Unproven

- fully unattended headless FAN$IER batch execution
- any useful command-line seam that:
  - opens batch mode
  - loads `.rgm` / `.eco` directly
  - starts `Start Batch` without clicks

## Current Best Hypothesis

- the real practical seam is:
  - FEMIC prepares `.rgm` / `.eco`
  - FAN$IER ingests regimes through its temp-folder watcher and/or interactive
    import/export flows
  - FAN$IER batch reporting may remain GUI-triggered unless a hidden startup
    branch is found later

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
   - `RunIdentifier`
   - `BatchPath`
   - report type / short/long toggles
4. Inspect whether any remaining decompiled startup branch can auto-open
    batch mode or consume temp `.rgm` files without manual navigation.
5. If batch extraction becomes reachable, validate whether a null-discount
   configuration is sufficient to treat FAN$IER as a raw economics extractor
   while leaving discounting entirely to downstream FEMIC analysis.
6. Shift the next live probe from importability to report usefulness:
   - load the current ultramin one-row regime
   - open batch mode with `Use defaults`
   - add or edit a `0%` discount-assumptions set
   - see whether FAN$IER can emit short/long reports from that minimal regime
     without requiring a separate `.eco`
