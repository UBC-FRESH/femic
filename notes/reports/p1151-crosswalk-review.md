# P115.1 carbon crosswalk review packet

Date: 2026-10-26
Phase: P115
Task: P115.1
Parent: #361
Issue: #362
Status: **mechanical checks pass; CBM/CFS science review pending**

## 1. What was checked

`scripts/check_carbon_crosswalks.py` checks every crosswalk value against the pinned
CBM defaults database `1.2.9300.391` (SHA-256
`4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155`).

```bash
python scripts/check_carbon_crosswalks.py \
  --aidb /path/to/cbm_defaults_v1.2.9300.391.db \
  --config-dir config/carbon \
  --out notes/reports/p1151-crosswalk-review.json
```

Result:

- 29 species rows: all CBM species names exist.
- 10 TSA/MKRF rows: all admin and eco boundary names exist.
- 12 disturbance rows: all CBM disturbance type names exist.
- 3 land-class rows: all land-class ids exist.
- `ok = true`.

The machine-readable packet is `notes/reports/p1151-crosswalk-review.json`. It also
records the CBM id and description for every disturbance mapping.

This is an **existence check only**. It does not decide whether the mapping is
scientifically right.

## 2. Species review

File: `config/carbon/species_map.bc.csv` (29 rows).

High confidence, direct names: AC, AT, BA, BG, CW, FD/FDC/FDI (one shared CBM name),
HM, HW, LW, MB, OA, PL/PLI, PY, RA, SE, SS, SW, WB, YB, YC.

Rows that need a science decision:

| BC code | Current CBM species | Confidence | Question |
| --- | --- | --- | --- |
| `S` | `Spruce` | medium | Is the generic spruce default acceptable when the leading species is only identified as spruce? |
| `SX` | `Spruce` | medium | Should hybrid spruce use a species-resolved curve instead of the generic spruce default? |
| `SB` | `Subalpine fir (or alpine fir)` | medium | Is the CBM subalpine/alpine fir default the right one for BC subalpine fir? |
| `BL` | `White birch` | medium | Is white birch the correct conservative default for paper birch? |
| `FD`/`FDC`/`FDI` | `Douglas-fir and Rocky Mountain Douglas-fir` | high | Is merging coastal and interior Douglas-fir acceptable, or should the package carry separate species-resolved curves? |
| `YC` | `Yellow-cypress` | high | Confirm the CBM default name is the intended yellow cedar parameterization. |
| `UNK_SW`/`UNK_HW` | unspecified softwood/hardwood | low | Are the explicit fallbacks acceptable, and are they visible enough in the package manifest? |

No mapped CBM species name is missing from the AIDB. The unresolved issue is the
**parameterization and curve resolution**, not string validity.

## 3. Eco-boundary review

File: `config/carbon/eco_boundary.bc.csv` (10 rows).

| TSA/FMU | CBM boundary | Confidence | Question |
| --- | --- | --- | --- |
| 08, 16, 24, 29, 40, 41 | British Columbia / Montane Cordillera | high-medium | Confirm each TSA does not straddle a CBM eco-boundary; TSA 24 and 29 are high, others medium. |
| 46, 47, 48 | British Columbia / Pacific Maritime | high-medium | Confirm the coastal boundary assignments, especially 46 and 47 (medium). |
| `mkrf` | British Columbia / Pacific Maritime | medium | Confirm the MKRF BEC/eco boundary from instance metadata; this row is explicitly marked as needing confirmation. |

All names exist in the AIDB. The unresolved issue is **spatial provenance and
single-boundary packages**: the current contract allows one admin/eco boundary per
package. A TSA or MKRF that spans boundaries must be split or handled by a later
extension.

## 4. Disturbance review

File: `config/carbon/disturbance_map.bc.csv` (12 rows).

The AIDB descriptions make the assumptions explicit:

| WS4 label | CBM type | CBM semantics from 1.2.9300.391 | Question |
| --- | --- | --- | --- |
| `cc` | Clearcut harvesting without salvage | Snags go to the Medium pool | Confirm this is the intended clearcut default. |
| `ct` | Partial cutting | Removes **50% of merchantable biomass** | Is 50% the right assumption, or must intensity be supplied? |
| `pct` | 85% precommercial thinning | Sylva 85% PCT | Confirm the removal assumption for precommercial thinning. |
| `f1`/`f2`/`f3` | Natural succession | **No stock changes** | Confirm fertilization should be a no-op event and not a growth effect. |
| `fire`/`wildfire` | Wildfire | Stand mortality | Confirm duplicate aliases are intentional. |
| `mpb` | Mountain pine beetle — Moderate impact | **10% softwood mortality** | Is 10% acceptable, or must severity come from the instance? |
| `salvage` | Salvage logging after fire | Salvage after fire | Confirm when this is used and whether it should be paired with a fire event. |
| `null` | Natural succession | No stock change | Confirm no-op semantics. |
| `default` | Natural succession | No stock change | Confirm a silent fallback is acceptable; the package must record it. |

Everything exists in the AIDB. The unresolved issue is **removal fraction, severity,
reset age, regen delay, and fallback policy**, not string validity.

## 5. Land-class review

File: `config/carbon/land_class.bc.csv`.

| IFM | Land class | CBM description | Confidence | Question |
| --- | --- | --- | --- | --- |
| managed | 0 | Forest Land remaining Forest Land | high | Matches WS3; confirm. |
| unmanaged | 0 | Forest Land remaining Forest Land | medium | Keep 0 for WS3 parity, or use 16 (Unmanaged Forest Land) for reporting? |
| nonforest | 1 | Cropland remaining | low | Only for an explicit nonforest package; confirm the land-use assumption. |

## 6. Review sign-off block

The reviewer should record decisions here or in the issue, then update the CSVs and
instance config. The review is not complete until this block is filled.

```text
Reviewer:
Affiliation / CBM-CFS expertise:
Review date:

Species decisions:
Eco-boundary decisions:
Disturbance decisions:
Land-class decisions:
Fallback policy:
One-species/one-boundary package policy:

Accepted as-is: [ ] yes [ ] no
Changes required:
```

After changes:

1. Update `confidence`, `source`, and `notes` in the affected CSVs.
2. Set `review.status`, `review.reviewer`, and `review.reviewed_utc` in
   `config/carbon/tsa24.yaml` and/or `mkrf.yaml`.
3. Re-run `scripts/check_carbon_crosswalks.py`.
4. Re-export the package; the crosswalk hashes in `sources` change, so the package
   fingerprint and handoff hashes change.
5. Re-run the WS3/WS4 parity and TSA24 package validation.

## 7. Current conclusion

The crosswalks are **mechanically valid against the pinned CBM defaults** and are
safe to use only as documented draft defaults. P115.1 remains open because the
CBM/CFS science review has not been completed. The WS4 runtime, WS3 parity mechanics,
GCBM export, and production package runs are not blocked by this review; only the
claim that these are reviewed scientific defaults is blocked.
