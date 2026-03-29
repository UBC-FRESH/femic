# BTC `/TSR` Variant Probe Ledger

This note tracks the structural clues behind FEMIC's depth-first BTC
`/TSR` probe work for Issue `#48`.

## Stock Report Syntax Classes

- `TimberSupply.rpt`
  - explicit transposed CSV report
  - current unattended seam anchor
  - shape:
    - `Type=transposed`
    - `OutputFormat=CSV`
    - lines like `Volume:Auto:Con    MVcon    {yr}`
- `ForestLandscapePlan.rpt`
  - explicit transposed CSV report
  - similar grammar to `TimberSupply.rpt`
  - lines like `VolumeGross    gVol    {yr}`
- Other stock `.rpt` files (`Yield`, `Logs`, `Mortality`, `Biomass`, `Carbon`,
  `CO2e`, `Industrial`, `Lumber`, `Wildlife`, `Stand`, `Stock`, `VolHtMai`,
  `Volume`, `VPT`)
  - custom report tables, usually not explicitly transposed
  - still contain many tokens omitted by unattended `/TSR`
  - common shapes:
    - bare token lines like `Logs_Grade_D`
    - width-bearing lines like `Year    750`
    - width plus label lines like
      `Mortality_Height_Mean    750    Mean Height`

## Working Inference

- Broad canonical probing proved the current harness is valid:
  `log-grades` still reprobes cleanly.
- The remaining families are not all failing for the same reason.
- Current failure buckets:
  - `exception`
    - BTC exits `1`, produces no output, and FEMIC auto-closes the modal dialog
  - `silent omission`
    - BTC run completes and writes output, but requested columns never appear
  - `naming mismatch`
    - canonical `OutputColumns.txt` names omit cleanly, while alternate
      stock-report spellings appear plausible

## Family Ledger

- `log-grades`
  - outcome: `accepted`
  - note: reprobe sanity check remains green under the current harness
- `lumber-2-or-better`
  - outcome: `accepted`
- `lumber-graded`
  - outcome: `accepted`
- `lumber-degraded`
  - outcome: `accepted`
- `industrial-logs`
  - outcome: `accepted`
- `residual-fibre`
  - outcome: `accepted`
- `yield-and-age-core`
  - outcome: `exception`
  - note: whole-bank and one-token fallback probes both triggered the same
    modal-failure signature
- `crop250-stand-quality`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Yield.rpt`
  - next move: try stock exact + stock-transposed line variants
- `mortality-summary`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Mortality.rpt`
  - next move: try width-bearing stock lines and adapted transposed forms
- `crown-and-fire`
  - outcome: `silent omission`
  - stock clue: tokens appear in canonical ledger; report-file evidence still
    needs confirming token by token
- `stand-structure-threshold-raw`
  - outcome: `naming mismatch`
  - clue:
    - canonical names like `BasalArea000`, `MeanDBHg000`, `StemCount000`
      omitted
    - report-token forms like `BasalArea:000`, `DBHg:000`, `SPH:000` already
      work in shipped banks
  - next move: probe alias variants first
- `biomass-live`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Biomass.rpt`
- `biomass-dead`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Biomass.rpt`
- `carbon`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Carbon.rpt`
- `co2e`
  - outcome: `silent omission`
  - stock clue: tokens appear in `CO2e.rpt`
- `genetics-fertilization-and-oaf`
  - outcome: `silent omission`
- `tass-and-site-index-raw`
  - outcome: `silent omission`
- `mortality-size-classes`
  - outcome: `silent omission`
  - stock clue: tokens appear in `Mortality.rpt`
- `diameter-class-stems`
  - outcome: `silent omission`
- `diameter-class-volume`
  - outcome: `silent omission`
- `diameter-class-vpt`
  - outcome: `silent omission`

## Depth-First Probe Order

1. `crop250-stand-quality`
2. `mortality-summary`
3. `crown-and-fire`
4. `stand-structure-threshold-raw`
5. biomass / carbon / CO2e totals
6. `yield-and-age-core` last, one token at a time

## Exact Next Probe Slice

The next live representative depth-first probes should be:

1. `Mortality_Height_Mean`
2. `Mortality_DBHg_Mean`
3. `Mortality_Basal_Area`
4. `BasalArea000`
5. `MeanDBHg000`
6. `StemCount000`

Notes:

- `Mortality_Stems` is not a direct stock-token line in `Mortality.rpt`, so do
  not invent it as the next representative probe. The direct shipped
  width-bearing mortality representatives are:
  - `Mortality_Height_Mean`
  - `Mortality_DBHg_Mean`
  - `Mortality_Basal_Area`
- The threshold-raw trio is intentionally the strongest naming-mismatch test:
  - `BasalArea000` vs `BasalArea:000`
  - `MeanDBHg000` vs `DBHg:000`
  - `StemCount000` vs `SPH:000`

### Variants To Test For The Mortality Representatives

For each of:
- `Mortality_Height_Mean`
- `Mortality_DBHg_Mean`
- `Mortality_Basal_Area`

test, in order:

1. generic transposed
   - shape:
     - `Token<TAB><TAB><shortascii><TAB>{yr}`
   - why:
     - baseline current `/TSR`-safe probe grammar
2. exact stock `Mortality.rpt` line
   - examples:
     - `Mortality_Height_Mean<TAB>750<TAB>Mean Height`
     - `Mortality_DBHg_Mean<TAB>750<TAB>DBHg`
     - `Mortality_Basal_Area<TAB>750<TAB>Basal Area`
   - why:
     - proves whether the raw stock line itself is loadable through the copied
       `/TSR` runtime
3. stock-transposed adapted line
   - shape:
     - `Token<TAB>750<TAB><shortascii><TAB>{yr}`
   - why:
     - preserves the stock width-bearing flavor while adapting it to the
       transposed TSR seam

### Variants To Test For The Threshold-Raw Naming-Mismatch Trio

For:
- `BasalArea000`
- `MeanDBHg000`
- `StemCount000`

test, in order:

1. generic transposed canonical token
   - shape:
     - `CanonicalToken<TAB><TAB><shortascii><TAB>{yr}`
   - why:
     - control case against the current canonical `OutputColumns.txt` name
2. alias-transposed report token
   - shapes:
     - `BasalArea:000<TAB><TAB><shortascii><TAB>{yr}`
     - `DBHg:000<TAB><TAB><shortascii><TAB>{yr}`
     - `SPH:000<TAB><TAB><shortascii><TAB>{yr}`
   - why:
     - strongest naming-layer hypothesis from the already-working
       stand-structure bank
3. exact stock `Yield.rpt` line
   - shapes:
     - `BasalArea:000`
     - `DBHg:000`
     - `SPH:000`
   - why:
     - proves whether the stock report-token spelling itself is accepted
4. stock-transposed adapted line
   - shapes:
     - `BasalArea:000<TAB><TAB><shortascii><TAB>{yr}`
     - `DBHg:000<TAB><TAB><shortascii><TAB>{yr}`
     - `SPH:000<TAB><TAB><shortascii><TAB>{yr}`
   - why:
     - keeps the stock token spelling but forces it into the proven transposed
       TSR grammar

## Latest Live Results (2026-03-29)

The representative depth-first slice above is now run and produced a strong
negative result.

- mortality representatives:
  - `Mortality_Height_Mean`
  - `Mortality_DBHg_Mean`
  - `Mortality_Basal_Area`
  - all three attempted:
    - generic transposed
    - exact stock `Mortality.rpt`
    - stock-transposed adapted
  - all three variants for all three fields failed the same way:
    - `exit_code=1`
    - no output CSV
    - no error CSV
    - modal dialog detected and auto-closed
  - working reading:
    - width-bearing stock syntax does not rescue the mortality family through
      the copied-install `/TSR` seam

- threshold-raw naming-mismatch trio:
  - `BasalArea000`
  - `MeanDBHg000`
  - `StemCount000`
  - attempted:
    - generic transposed canonical token
    - alias-transposed report token
    - exact stock `Yield.rpt` line
  - all attempted variants failed with the same modal signature:
    - `exit_code=1`
    - no output CSV
    - no error CSV
    - modal dialog detected and auto-closed
  - working reading:
    - even the known-good report-token spellings
      (`BasalArea:000`, `DBHg:000`, `SPH:000`) do not survive this copied-install
      stock-matrix probe path, despite working on the live user-overlay seam

- operational note:
  - the new immediate-kill dialog path is working, but these BTC exception
    dialogs typically do not appear until roughly 17-20 seconds into the run,
    so the wall-clock cost is still dominated by BTC's own pre-dialog stall
    rather than FEMIC waiting after detection

## Variant Rules

- Keep `log-grades` as the standing sanity reprobe before and after major
  variant-search rounds.
- For variant exploration, prefer copied-install probing over the live user
  overlay unless the test specifically needs the real overlay seam.
- Do not ship a new optional bank until a representative token succeeds under
  a stable variant pattern and siblings in the same family confirm that same
  pattern.
