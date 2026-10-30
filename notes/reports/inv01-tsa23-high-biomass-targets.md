# INV-01 TSA 23 high-biomass target set

## Why

The four TSA 23 PSP plots outside the current BA/volume card range are all
high-biomass IDF stands.  The cards stop at `Lhmean` 14.1882 m, so the current
map leaves those stands unmapped.  The next data task is to add high-biomass IDF
plots with actual LidarBC support, not to wait for more validation.

## Source

The target table was built from the complete FAIB PSP archive fetched through
Nemora:

- 7,341 PSP sites province-wide
- 200 in TSA 23, 162 in IDF
- 455 TSA 23 visits
- nearby IDF sites in TSA 22 (Okanagan; 89 with attributes) and TSA 29
  (Williams Lake; 175 with attributes).  TSA 22 is **not** adjacent to TSA 23
  and is excluded from training; it can only be an external transfer test.

High-biomass candidates were restricted to:

- IDF
- latest measurement year >= 2017
- observed live-tree volume >= 150 m3/ha
- a LidarBC point-cloud tile containing the plot

The result is 17 candidates: 14 in TSA 29 and 3 in TSA 22.  TSA 29 candidates
are the exploratory training increment; TSA 22 is excluded from training because
it is the Okanagan TSA, not an adjacent 100 Mile House IDF population.  TSA 22
could be used only as a separate transfer test, not as model training.

## TSA 29 increment

Ten TSA 29 IDF plots with volume >= 150 m3/ha and a point-cloud tile were the
first increment.  Eight are usable; 4024194 has a corrupt LAZ payload and
4024290 has a 113 KB tile with no first returns in the plot support.  The eight
usable plots cover observed volumes from 177 to 383 m3/ha, above the current
training maximum of 217.9 m3/ha.

| Site | Year | Height m | BA m2/ha | Volume m3/ha | Point cloud |
| --- | ---: | ---: | ---: | ---: | --- |
| 4024191 | 2022 | 23.93 | 44.25 | 383.03 | `bc_093b030_1_2_2_xyes_8_utm10_20240509_20240509.laz` |
| 4024194 | 2022 | 24.27 | 28.74 | 269.04 | `bc_093b030_1_2_4_xyes_8_utm10_20240509_20240509.laz` |
| 4024279 | 2022 | 23.28 | 43.37 | 349.97 | `bc_093b019_4_4_1_xyes_8_utm10_2019.laz` |
| 4024285 | 2022 | 19.67 | 36.55 | 248.02 | `bc_093b020_3_1_3_xyes_8_utm10_2019.laz` |
| 4024290 | 2022 | 28.37 | 43.46 | 421.87 | `bc_093b019_2_2_4_xyes_8_utm10_2019.laz` |
| 4024299 | 2022 | 22.62 | 32.23 | 256.78 | `bc_093b030_1_2_2_xyes_8_utm10_20240509_20240509.laz` |
| 4024429 | 2018 | 19.39 | 36.96 | 254.15 | `bc_092p091_4_2_1_xyes_8_utm10_2019.laz` |
| 4024835 | 2022 | 26.99 | 24.47 | 208.62 | `bc_092p081_3_3_2_xyes_8_utm10_2019.laz` |
| 4024836 | 2022 | 26.22 | 20.11 | 177.15 | `bc_092p081_3_3_2_xyes_8_utm10_2019.laz` |
| 4026687 | 2022 | 21.75 | 36.45 | 293.02 | `bc_093b029_4_3_1_xyes_8_utm10_20231008_20231008.laz` |

The point-cloud and DEM files are being staged under
`/srv/shared-data/gep/ws4/tmp/inv01-data`, not under `/tmp`.

## Evaluation rule

- Fit the candidate cards on 14 TSA 23 training plots plus the TSA 29 high-biomass
  increment.
- Keep the four TSA 23 high-biomass plots as the external test.
- Report both current-card and candidate-card predictions on the external test.
- Do not replace the published cards unless the candidate covers the high-biomass
  range and does not degrade the tile-level TSA 23 CV.

This is a domain-extension experiment; TSA 29 is not a TSA 23 validation sample.
The resulting experimental metrics are in
``notes/reports/inv01-tsa23-high-biomass-refit.md``.
