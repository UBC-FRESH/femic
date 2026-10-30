# INV-01 TSA 23 PSP holdout check

## Correction

The earlier recommendation to wait for more field data was wrong.  The full BC
FAIB PSP archive is available through Nemora/FAIB; the 14-plot pilot was a
selected subset, not the whole PSP universe.  I downloaded the current archive
and used it immediately.

The full archive gives:

- 7,341 PSP sites province-wide
- 200 PSP sites in TSA 23
- 162 of those in IDF
- 455 TSA 23 visits; 451 with reconstructed live-tree attributes
- 22 TSA 23 visits since 2017 with a LidarBC point-cloud tile
- 18 of those 22 in the processed 5,899-tile set; 4 in an omitted tile
- 4 independent IDF plots with usable first returns and exact plot support

This is still a small holdout, but it is **not** a reason to wait: it is enough
to test the current cards now and to design the next refit.

## Data acquisition

The PSP archive was fetched with Nemora's FAIB helpers:

```python
from nemora.ingest.faib import download_faib_csvs
download_faib_csvs(
    "/srv/shared-data/gep/ws4/tmp/inv01-data/psp/raw",
    dataset="psp",
    filenames=[
        "faib_header.csv",
        "faib_plot_header.csv",
        "faib_sample_byvisit.csv",
        "faib_tree_detail.csv",
    ],
)
```

The tree detail extract is 706 MB; the header/visit tables are a few MB.  The
FAIB archive also provides the 2026 data dictionary.  No new PSP field
measurements were collected.

## Ground reconstruction

Ground attributes were reconstructed exactly as in the 14-plot pilot:

- live trees only (`LV_D == "L"`)
- DBH >= 9.1 cm
- per-tree `BA_TREE`, `VOL_WSV`, `HEIGHT`, expanded by `PHF_TREE`
- basal area and volume summed per hectare
- Lorey height = `sum(height * expanded BA) / sum(expanded BA)`

This reproduces the 14 published training rows to the recorded precision.

## Holdout selection

The independent set is the four IDF plots measured in 2018 in tile
`lidarbc:4:117213` (2019 LidarBC), which were omitted from the full run because
the fine 2.5 km 1 m DEM was unavailable:

| Site | Visit | Measured | Lidar | Observed height | Observed BA | Observed volume |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4025090 | 5 | 2018 | 2019 | 23.68 m | 34.33 m2/ha | 302.78 m3/ha |
| 4025091 | 5 | 2018 | 2019 | 19.54 m | 44.61 m2/ha | 305.07 m3/ha |
| 4025094 | 5 | 2018 | 2019 | 20.90 m | 36.23 m2/ha | 273.80 m3/ha |
| 4025095 | 5 | 2018 | 2019 | 15.34 m | 31.28 m2/ha | 173.17 m3/ha |

Features were computed from first returns above a 2019 1 m layer-6 DEM, using
the exact FAIB plot area (`PLOT_AREA_MAIN`, equivalent radius 16.06 m).  This is
the same first-return method as the pilot; the DEM source differs because the
fine layer-5 tile is absent.

The fifth candidate, `4025421`, is in tile `lidarbc:4:117009`; the actual point
cloud begins about 66 m east of the plot, so no first returns fall in the plot
support.  It is excluded rather than silently using an empty sample.


## Applicability: this is an extrapolation test

The four plots are high-biomass IDF stands.  The current cards have narrow
ranges:

- height: `Lhp95` 9.508-24.07 m
- BA/volume: `Lhmean` 5.8017-14.1882 m and `CC2m` 56.3442-86.3423%

Three of the four plots are outside the BA/volume `Lhmean` range, and one is
outside the height range:

| Site | Lhmean | Lhp95 | Height in range | BA/volume in range |
| --- | ---: | ---: | :---: | :---: |
| 4025090 | 21.30 | 28.51 | no | no |
| 4025091 | 16.19 | 20.98 | yes | no |
| 4025094 | 18.15 | 22.61 | yes | no |
| 4025095 | 13.36 | 18.51 | yes | yes |

Therefore the table above is **not an in-domain validation of the cards**.  It
is a stress test of extrapolation.  The current full-run map already drops cells
outside these ranges, so these high-biomass plots would be unmapped rather than
predicted.  The result is still decisive for the programme: the cards do not
cover a large part of the TSA's high-biomass IDF stands.

A simple exploratory refit on all 18 plots did not improve leave-one-tile-out
RMSE (height 0.94 vs 0.86 m; BA 5.26 vs 5.04 m2/ha; volume 57.9 vs 57.6 m3/ha).
The next fit needs more high-biomass plots, not just a different line through the
same 18.

## Current-card results

Applying the published 14-plot cards to the four independent plots:

| Attribute | Observed mean | Predicted mean | Bias | MAE | RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lorey height (m) | 19.87 | 20.87 | +1.00 | 1.07 | 1.46 |
| Basal area (m2/ha) | 36.61 | 37.55 | +0.93 | 6.97 | 8.35 |
| Gross volume (m3/ha) | 263.71 | 352.97 | +89.27 | 97.64 | 118.21 |

Per plot:

| Site | Height obs/pred | BA obs/pred | Volume obs/pred |
| --- | ---: | ---: | ---: |
| 4025090 | 23.68 / 25.76 | 34.33 / 44.54 | 302.78 / 495.02 |
| 4025091 | 19.54 / 19.47 | 44.61 / 32.54 | 305.07 / 288.34 |
| 4025094 | 20.90 / 20.82 | 36.23 / 41.61 | 273.80 / 397.54 |
| 4025095 | 15.34 / 17.40 | 31.28 / 31.50 | 173.17 / 231.00 |

The holdout RMSEs are larger than the pilot LOOCV errors:

- height: 1.46 m vs 0.688 m
- BA: 8.35 m2/ha vs 4.414 m2/ha
- volume: 118.21 m3/ha vs 20.666 m3/ha

The height and BA cards retain signal in the three in-range height plots, but the
BA/volume predictions are extrapolations and volume is badly overpredicted.  Four
plots in one tile are not a spatial validation of the TSA; they show that the
current cards cannot be extended to high-biomass stands.

## What this means

- The current surface is still not operational.
- The full PSP archive is now the evidence base; waiting for “more validation”
  is not the issue.  The issue is **domain coverage**: the cards stop at
  `Lhmean` 14.19 m, while high-biomass IDF stands exceed it.
- Refitting on the same 18 plots is not sufficient.  The next dataset increment
  must add high-biomass IDF plots with LidarBC-supporting point clouds, ideally
  in TSA 23 or adjacent IDF, plus a tile-level spatial holdout.
- The four holdout plots are clustered in one 2019 tile; that is a limitation of
  this check, not a reason to defer the next fit.

## Files

- `notes/reports/inv01-tsa23-psp-holdout.csv`
- `notes/reports/inv01-tsa23-psp-holdout.json`
- `examples/inv01_tsa23_validation/psp_holdout.py`
- `notes/reports/inv01-tsa23-high-biomass-targets.md` — next high-biomass data increment
- FAIB archive cache: `/srv/shared-data/gep/ws4/tmp/inv01-data/psp/raw/` (not tracked)
