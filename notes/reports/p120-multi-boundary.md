# P120 multi-boundary carbon packages

Date: 2026-10-27
Status: delivered and merged
Cross-repo: FEMIC #417/#421/#422; WS4 #455/#460

## Producer result

The carbon exporter now writes every observed eco boundary and keeps per-row
inventory boundary shares. WS4 compiles the admin/eco SIT classifiers and splits a
track's dataset area by those shares.

| TSA | Package id | Tracks | Area (ha) | Yield rows |
| --- | --- | ---: | ---: | ---: |
| TSA08 | `femic-carbon-08-6c14f038985f` | 33 | 4,341,402.9 | 1,023 |
| TSA16 | `femic-carbon-16-c92d20527b46` | 49 | 2,807,096.4 | 1,519 |
| TSA40 | `femic-carbon-40-d49e9e05b9b9` | 30 | 2,497,704.2 | 930 |
| TSA41 | `femic-carbon-41-5ee703516c93` | 38 | 1,954,327.1 | 1,178 |

All four validate with CBM defaults `1.2.9300.391` and SHA-256
`4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155`.

## Consumer evidence

The WS4 compiled-matrix and full-landscape evidence, including the exact area
splits and 50-year results, is recorded in the WS4 report
`notes/reports/p120-multi-boundary.md`. This note is the producer-side summary; the
WS4 report is the authoritative consumer record.

## Caveats

- The boundary split depends on the source checkpoint carrying the public VRI
  `CFS_ECOZONE` field. A checkpoint without it still gets a dominant-boundary
  package and records that fallback.
- The package uses one CBM species per track. Species-resolved curves remain a
  later refinement.
- The GCBM walltowall lane is a bridge, not a libcbm parity target.
