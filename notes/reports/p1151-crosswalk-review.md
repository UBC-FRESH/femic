# P115.1 carbon crosswalk review

Date: 2026-10-26
Phase: P115
Task: P115.1
Parent: #361
Issue: #362
Status: **reviewed against public VRI/CBM/GIS sources; residual modelling gaps deferred**

## 1. Review basis

The review used public deterministic sources rather than an expert opinion:

- **Species:** BC VRI data dictionary (`A User's Guide to the Vegetation Resources
  Inventory`, Table D-1, `https://www.for.gov.bc.ca/hfd/library/documents/bib106996.pdf`)
  cross-checked against the CBM defaults `species_tr` table.
- **Eco boundaries:** BCGW `WHSE_ADMIN_BOUNDARIES.FADM_TSA` polygons intersected with
  the AAFC Terrestrial Ecozones (2026-10-26).
- **Disturbances and land classes:** CBM-CFS3 v1.2 User's Guide, Appendix 6 and Table 3-2,
  plus the `cbm_defaults 1.2.9300.391` disturbance/land-class tables.
- **Fertilization:** Jinming Ke MSc thesis, `Master_s_Thesis___Jimmy.docx`, especially
  §1.2.2 and Experiment Two.

## 2. Automated checks

`scripts/check_carbon_crosswalks.py` checks every mapped value against the pinned CBM
defaults `1.2.9300.391` and the checked-in VRI code table:

```bash
python scripts/check_carbon_crosswalks.py \
  --aidb /path/to/cbm_defaults_v1.2.9300.391.db \
  --config-dir config/carbon \
  --out notes/reports/p1151-crosswalk-review.json
```

Result: **ok = true**

- 41 species rows, 36 VRI codes, 0 missing CBM species names, 0 missing VRI codes.
- 10 TSA/MKRF rows, 0 missing admin/eco boundary names.
- 8 disturbance rows, 0 missing CBM disturbance types.
- 2 land-class rows, 0 missing CBM land classes.

The machine-readable packet is `notes/reports/p1151-crosswalk-review.json`.

## 3. Species corrections

Species keys now follow the public VRI data dictionary. The important corrections:

| VRI code | VRI name | Old/incorrect mapping | Now |
| --- | --- | --- | --- |
| `Bl` | subalpine fir | `BL` was paper birch | `BL` -> `Subalpine fir (or alpine fir)` |
| `Sb` | black spruce | `SB` was subalpine fir | `SB` -> `Black spruce` |
| `Ep` | paper birch | `BL` | `EP` -> `White birch` |
| `Dr` | red alder | `RA` | `DR` -> `Red alder`; `RA` legacy alias |
| `Pa` | whitebark pine | `WB` | `PA` -> `Whitebark pine`; `WB` legacy alias |
| `Qg` | Garry oak | `OA` | `QG` -> `Garry oak`; `OA` legacy alias |
| `Ey` | yellow birch | `YB` | `EY` -> `Yellow birch`; `YB` was not VRI |
| `Act`/`Acb` | black cottonwood / balsam poplar | `AC` black cottonwood | `ACT`, `ACB`; `AC` is generic poplar |

The map now also covers `Pj`, `Pw`, `Plc`, `Sxw`, `Sxl`, and `Sxs`.

Residual species gap: `S`/`Sx` still use the generic Spruce default, and
`Fd`/`Fdc`/`Fdi` share the CBM Douglas-fir default. Species-resolved curves remain a
later extension; the crosswalk records the coarseness.

## 4. Eco-boundary review

Current TSA names and the dominant eco boundary were corrected from the BCGW TSA layer.
The polygon intersection gives:

| TSA | Name | Dominant CBM ecozone | Share | Other ecozones | Result |
| --- | --- | --- | --- | --- | --- |
| 08 | Fort Nelson | Taiga Plains | 54.9% | Boreal Cordillera 45.1% | split required |
| 16 | MacKenzie | Boreal Cordillera | 55.6% | Montane Cordillera 44.4% | split required |
| 24 | Prince George | Montane Cordillera | 98.33% | Boreal Cordillera 1.67% | dominant, small overlap |
| 29 | Williams Lake | Montane Cordillera | 96.84% | Pacific Maritime 3.16% | dominant, small overlap |
| 40 | Fort St. John | Boreal Plains | 53.5% | Taiga Plains 29.1%, Boreal Cordillera 10.0%, Montane 7.3% | split required |
| 41 | Dawson Creek | Montane Cordillera | 52.0% | Boreal Plains 48.0% | split required |
| 46 | GBR North | Pacific Maritime | 93.0% | Montane Cordillera 7.0% | dominant |
| 47 | GBR South | Pacific Maritime | 98.2% | Montane Cordillera 1.8% | dominant |
| 48 | North Island | Pacific Maritime | 100% | none | single boundary |
| `mkrf` | Malcolm Knapp Research Forest | Pacific Maritime | custom | none | non-TSA research forest |

The package contract still carries one boundary per package. TSAs marked “split
required” need a multi-boundary package (or separate packages) before their carbon
results can be interpreted as eco-boundary-correct. TSA24 is 98.33% Montane Cordillera;
the 1.67% Boreal Cordillera overlap is recorded as a limitation, not silently ignored.

The old table had wrong names/codes: e.g. 24 was labelled Quesnel, 08 Okanagan, 16
Kamloops, 40 Kootenay Lake, 41 Boundary, 46 Sunshine Coast, 47 Arrowsmith. Those are
corrected.

## 5. Disturbance review

| WS4 label | CBM type | Decision |
| --- | --- | --- |
| `cc` | Clearcut harvesting without salvage | Keep; default clearcut. |
| `ct` | 40% commercial thinning | Replaces `Partial cutting` (50%). 40% basal-area removal from below is expected to remove less than 40% merchantable volume; the CBM 40% commercial-thinning matrix is therefore an upper-bound proxy. A custom matrix is the next refinement. |
| `pct` | 85% precommercial thinning | Keep; at age 10–20 merchantable volume is near zero, so stock effect is small. |
| `fire`/`wildfire` | Wildfire | Keep as aliases. |
| `mpb` | Mountain pine beetle — Moderate impact | Keep 10% softwood mortality as an evergreen placeholder; real impact depends on pine fraction and beetle intensity. Severity-specific types are available in the AIDB. |
| `salvage` | Salvage logging after fire | Keep, low confidence; usually paired with a preceding fire event. |
| `null` | Natural succession | Explicit no-op only. |
| `f1`–`f3` | **not a plain CBM disturbance** | Do not map to a no-op. The public TIPSY growth response and the thesis emissions audit are implemented in the carbon lane. WS4 now accepts `f1`–`f3` only with `--fertilization-config`, using materialized curve transitions or the scalar fallback, and adds the audited emissions accounts (WS4 #441). |

The CBM AIDB has no fertilization disturbance type. The public TIPSY
``FertRespMOF.txt`` table provides the growth response by species/site index/age,
and the thesis code (``UBC-FRESH/msc_jimmy_ke``) provides the 200 kg N/ha dose and
per-hectare factors: ~17.14 kg CO2, 0.0557 kg CH4, 20.00 kg N2O for one application
(40.00/60.00 for two/three). FEMIC exposes the curve transform and a reproducible
emissions audit; the CBM pool/optimizer wiring is a separate runtime step.

## 6. Land-class review

CBM-CFS3 v1.2 User's Guide, Table 3-2 defines:

- `0` — Forest Land remaining Forest Land
- `16` — Unmanaged Forest Land
- `1` — Cropland remaining; `2` grassland, `3` wetland, `4` settlement, `5` other

The mapping now uses:

- managed IFM -> `0`
- unmanaged IFM -> `16`
- nonforest -> **no default**; the instance must supply cropland/grassland/wetland/
  settlement/other explicitly.

The package builder now raises on an unmapped IFM instead of silently assigning `0`.
This deliberately diverges from the old WS3 parity fixture, which used `0` for both
managed and unmanaged; the parity adapter keeps its own fixture mapping.

## 7. Residual work

- Multi-boundary package support for TSA 08, 16, 40, 41 (and the small overlaps in
  24, 29, 46, 47).
- Wire the public TIPSY fertilization curves and emissions audit into the compiled dataset, optimizer ledger, and report.
- Intensity-specific `ct` matrix and MPB severity input.
- Species-resolved curves for S/Sx, SB, and the Douglas-fir group.
- Re-export the TSA24 package after these crosswalk changes; package hashes change.

## 8. Closeout

The crosswalk review is complete for the current package contract. Residual items above
are model extensions, not unresolved string/GIS crosswalk questions. The original
`review.status: draft` in the instance configs should be changed to `reviewed` and the
package re-exported before the P115 phase closeout.
