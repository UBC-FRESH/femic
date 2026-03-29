# BTC `/TSR` Variant Probe Ledger

This note tracks the structural clues behind FEMIC's depth-first BTC
`/TSR` probe work for Issue `#48`.

## Active Rule

- Treat the live user-overlay
  `Documents\BatchTIPSY Composer\TimberSupply.rpt` seam as the only active
  decision-making probe path for BTC field eligibility.
- Do not keep using copied-install stock-matrix experiments to decide whether
  a field is shippable. That path has already proven too misleading.
- Use copied-install/template-structure experiments only if we later need a
  narrow reverse-engineering side test, not as the main eligibility workflow.

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

## Next Active Overlay-Only Differential Probe Set

Retire copied-install stock-matrix probing as the main path. The next live
decision-making slice should use only the real user-overlay TSR seam, run
sequentially, with stock-TSR-style overlay lines and direct header inspection.

Control first:

1. `Logs_Grade_D`

Representative omitted-family tokens next:

2. `Mortality_Height_Mean`
3. `Crop250VolUtil125`
4. `CrownCover`

Overlay line shape to use:

- `Token<TAB><TAB><shortascii><TAB>{yr}`

Why this slice:

- `Logs_Grade_D` is a known-good control on the actual seam.
- `Mortality_Height_Mean`, `Crop250VolUtil125`, and `CrownCover` each
  represent a different omitted family without depending on the threshold-raw
  alias confusion.
- The real question now is not copied-install syntax; it is whether these
  exact tokens are honored, silently omitted, or exception-triggering through
  the actual live overlay seam.

## Overlay-Only Differential Result (2026-03-29)

The real live overlay seam answered the question much more cleanly than the
copied-install experiments.

- known-good control:
  - `Logs_Grade_D`
  - passed cleanly with returned `LGD_*` age-series headers
- first representative omitted-family tokens:
  - `Mortality_Height_Mean`
  - `Crop250VolUtil125`
  - `CrownCover`
  - all three passed cleanly with returned age-series headers
- sibling follow-up tokens:
  - mortality:
    - `Mortality_Stems`
    - `Mortality_DBHg_Mean`
    - `Mortality_Basal_Area`
    - `Mortality_Volume_Total`
  - crop250:
    - `Crop250DBHgMean`
    - `Crop250LiveCrown`
  - crown/fire:
    - `Crown_Bulk_Density`
  - all of these also passed cleanly on the live overlay seam

Current practical reading:

- the earlier "silent omission" families were not fundamentally impossible
  through unattended `/TSR`
- the live user-overlay seam is the correct place to prove eligibility
- `mortality-summary`, `crop250-stand-quality`, and `crown-and-fire` are now
  strong shipped-bank candidates and should be validated at whole-bank level
  and then rolled forward as real FEMIC optional banks

## Next Active Overlay-Only Slice

The next live-overlay-only candidate set should be:

Control:

1. `Logs_Grade_D`

Representative biomass / carbon / CO2e totals:

2. `Biomass_Live_Total`
3. `Biomass_Dead_Total`
4. `Carbon_Live_Total`
5. `Carbon_Dead_Total`
6. `CO2e_Live_Total`
7. `CO2e_Dead_Total`

Remaining crown/fire support metrics:

8. `mean_height_to_crown_base`
9. `mean_crown_length`

Overlay line shape:

- `Token<TAB><TAB><shortascii><TAB>{yr}`

Why this slice:

- it extends the now-proven overlay-only workflow to the next compact,
  interpretable ecological families before taking on the bulky diameter/mortality
  class histograms;
- the totals-first biomass/carbon/CO2e probes give a cheap high-signal answer
  before trying every component field;
- the two remaining crown/fire support metrics clarify whether the current
  `crown-and-fire` bank should stay as-is or expand to include the supporting
  height/length columns.

## Biomass / Carbon / CO2e Overlay Result (2026-03-29)

The next overlay-only totals slice also came back clean.

- control:
  - `Logs_Grade_D`
  - passed again on the live overlay seam
- representative totals passed with real returned age-series headers:
  - `Biomass_Live_Total`
  - `Biomass_Dead_Total`
  - `Carbon_Live_Total`
  - `Carbon_Dead_Total`
  - `CO2e_Live_Total`
  - `CO2e_Dead_Total`
- remaining crown/fire support metrics also passed:
  - `mean_height_to_crown_base`
  - `mean_crown_length`

That was strong enough to justify whole-bank live overlay smokes, and those
also passed cleanly for:

- `biomass-live`
- `biomass-dead`
- `carbon`
- `co2e`
- expanded `crown-and-fire`

Direct header inspection confirmed returned columns including:

- `Biomass_Live_Wood_*`, `Biomass_Live_Total_*`
- `Biomass_Dead_Wood_*`, `Biomass_Dead_Total_*`
- `Carbon_Live_Total_*`, `Carbon_Dead_Total_*`
- `CO2e_Live_Total_*`, `CO2e_Dead_Total_*`
- `CrownCover_*`, `mean_height_to_crown_base_*`,
  `mean_crown_length_*`, `Crown_Bulk_Density_*`

Current practical reading:

- the live overlay seam continues to unlock coherent whole-bank families well
  beyond the first product and summary slices
- the next major remaining bank cluster is the class/histogram surface:
  `mortality-size-classes`, `diameter-class-stems`,
  `diameter-class-volume`, and `diameter-class-vpt`

## Next Active Histogram / Class Overlay Slice

Retire copied-install probing from the decision path entirely. The only seam
that matters for shipping eligibility is the real user overlay
`Documents\BatchTIPSY Composer\TimberSupply.rpt` seam under unattended `/TSR`,
run sequentially with direct returned-header inspection.

Control first:

1. `Logs_Grade_D`

Representative histogram/class tokens next:

2. `Mortality_Stems_Size_Class_5`
3. `Mortality_Volume_Size_Class_5`
4. `Mortality_VPT_Size_Class_5`
5. `Stems_Diameter_Class_0`
6. `Volume_Diameter_Class_0`
7. `VPT_Diameter_Class_0`

Overlay line shape:

- `Token<TAB><TAB><shortascii><TAB>{yr}`

Why this slice:

- it stays on the only proven seam for unattended BTC field discovery;
- it tests one mortality histogram representative from each major size-class
  family before trying every sibling field; and
- it tests one diameter-class representative from each major class family
  before shipping the four bulky remaining banks.

Decision rule:

- if the representatives pass with real returned age-series headers, expand to
  whole-bank live overlay smokes for:
  - `mortality-size-classes`
  - `diameter-class-stems`
  - `diameter-class-volume`
  - `diameter-class-vpt`
- if they fail, record the exact failure class (`exception` vs `omitted`) and
  stop broadening that family until the live seam yields a stronger clue.

## Histogram / Class Overlay Result (2026-03-29)

The live overlay seam also unlocked the remaining class/histogram families.

- representative control and reps all passed with real returned age-series
  headers:
  - `Logs_Grade_D`
  - `Mortality_Stems_Size_Class_5`
  - `Mortality_Volume_Size_Class_5`
  - `Mortality_VPT_Size_Class_5`
  - `Stems_Diameter_Class_0`
  - `Volume_Diameter_Class_0`
  - `VPT_Diameter_Class_0`
- while tightening that slice, the probe harness also got one important fix:
  - default one-token probes now force short ASCII header aliases; and
  - returned-header detection no longer assumes alnum-only prefixes, so stock
    BTC headers like `Logs (Grade)_10` are no longer misclassified as missing.
- based on those representative passes, whole-bank live overlay smokes also
  passed cleanly for:
  - `mortality-size-classes`
  - `diameter-class-stems`
  - `diameter-class-volume`
  - `diameter-class-vpt`
- direct header inspection confirmed returned columns such as:
  - `Mortality_Stems_Size_Class_5_*`
  - `Mortality_Volume_Size_Class_5_*`
  - `Mortality_VPT_Size_Class_5_*`
  - `Stems_Diameter_Class_0_*`
  - `Volume_Diameter_Class_0_*`
  - `VPT_Diameter_Class_0_*`

Current practical reading:

- the live overlay seam is now proven for the bulky histogram/class families
  too, not just the compact summary/product/ecological banks; and
- the remaining unresolved canonical families are now the smaller
  `genetics-fertilization-and-oaf`, `tass-and-site-index-raw`,
  `stand-structure-threshold-raw`, and the exception-prone `yield-and-age-core`
  cluster.

## Next Remaining Live-Overlay Slice

The next candidate family should be the compact scalar status banks again, not
another large class family.

Recommended order:

1. `genetics-fertilization-and-oaf`
2. `tass-and-site-index-raw`
3. `stand-structure-threshold-raw`
4. `yield-and-age-core` last, one token at a time

Representative next tokens to run first:

1. `GWgain`
2. `FertGain`
3. `OAF`
4. `YearTASS_Base`
5. `HeightSindex_Base`
6. `BasalArea000` / `DBHg:000` only if the threshold-raw alias question is
   reopened deliberately

## Scalar Status Overlay Result (2026-03-29)

The remaining compact scalar/status families also passed on the live overlay
seam.

- representative live overlay probes passed with real returned age-series
  headers for:
  - `GWgain`
  - `FertGain`
  - `OAFremoval`
  - `OAFmortality`
  - `OAFimpact`
  - `OAF`
  - `YearTASS_Base`
  - `HeightSindex_Base`
  - `YearTASS_Full`
  - `HeightSindex_Full`
- based on that signal, whole-bank live overlay smokes also passed cleanly for:
  - `genetics-fertilization-and-oaf`
  - `tass-and-site-index-raw`
- direct header inspection confirmed returned columns such as:
  - `GWgain_*`
  - `FertGain_*`
  - `OAF_*`
  - `YearTASS_Base_*`
  - `HeightSindex_Base_*`
  - `YearTASS_Full_*`
  - `HeightSindex_Full_*`

Current practical reading:

- all compact canonical scalar/status banks are now shipped through the live
  overlay seam; and
- the live overlay seam also unlocked the full `stand-structure-threshold-raw`
  family on the simple generic transposed probe line:
  - `Volume000/125/175`
  - `BasalArea000/125/175`
  - `MeanDBHg000/125/175`
  - `MAI000/125/175`
  - `VPT000/125/175`
  - `Juvenille_Volume000/125/175`
  - `Juvenille_Percent000/125/175`
- all twenty-one threshold-raw tokens were accepted in live overlay probing with
  `runtime_layout=live-overlay`, `variant_strategy=stock-matrix`, and the
  generic transposed line winning immediately before any alias/stock fallback
  was needed.
- the live overlay seam also unlocked a coherent reduced `yield-and-age-core`
  bank on the simple generic transposed line:
  - accepted and now shippable:
    - `Year`
    - `TotalAge`
    - `BHAge`
    - `StandAge`
    - `HeightSindex`
    - `Height`
    - `Volume`
    - `VPT`
    - `HeightTassTop`
    - `HeightTassMean`
    - `HeightTassPredom`
  - already present in the unattended TSR base preset rather than needing the
    optional bank:
    - `CC`
    - `VolumeGross`
  - still live-overlay blocked with modal BTC exceptions:
    - `Juvenille_Volume`
    - `Juvenille_Percent`
- there are no remaining unresolved optional-bank families under Issue `#48`;
  only the two blocked non-threshold juvenile totals remain as documented
  live-overlay exceptions.

## Remaining Unresolved Families

Recommended order:

1. No remaining unshipped logical banks

Why this order:

- the remaining work is no longer bank expansion; it is closeout hygiene around
  the two blocked non-threshold juvenile totals and final Issue `#48`
  reconciliation.

Threshold-triplet design rule:

- when BTC exposes the same metric at `{000,125,175}` top-diameter merchantable
  cutoffs, FEMIC should treat that triplet as one atomic bank-design unit;
- do not ship only one member of that triplet as the long-term mapped-bank
  result unless a specific live-overlay blockage is proven and documented; and
- for `stand-structure-threshold-raw`, that intended landing shape is now
  proven and landed as the full three-threshold family for each metric
  (`Volume`, `BasalArea`, `MeanDBHg`, `MAI`, `VPT`, `Juvenille_Volume`,
  `Juvenille_Percent`), not just the `000` member.

## Variant Rules

- Keep `log-grades` as the standing sanity reprobe before and after major
  live-overlay probe rounds.
- Do not ship a new optional bank until a representative token succeeds under
  the real live overlay seam and siblings in the same family confirm that same
  pattern.
