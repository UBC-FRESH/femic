# TSA24 minimal carbon fixture

A tiny, public-safe package generated from synthetic stand data with the TSA24
code and the Montane Cordillera boundary. It is not a sample of the real TSA24
inventory; it exercises the package contract in tests and CI.

- 1 track, 2 inventory rows, 5.0 ha
- 31 yield rows on the 10-year grid to age 300
- draft crosswalks and the pinned CBM defaults hash

Regenerate only through the FEMIC exporter/tests; do not hand-edit the CSVs or
manifest.
