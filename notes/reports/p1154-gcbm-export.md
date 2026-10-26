# P115.4 GCBM walltowall export

Date: 2026-10-26
Phase: P115
Task: P115.4
Parent: #361
Issue: #365

## What was added

- `femic/gcbm/export.py` and `femic export gcbm`.
- The exporter writes `walltowall_config.json`, `inventory.gpkg`, a wide
  `yield.csv`, optional `disturbances.gpkg`, a copied AIDB, and `manifest.json`.
- One baseline package track per AU/IFM, selected deterministically from
  `ORIGIN(natural)`, `SILV_STATE(baseline)`, and `RETENTION(0)`.
- Dense small classifier codes (`Classifier1` 1..N, `Classifier2` 1/0) to avoid
  Float32 formatting of raw AU ids (`2401005` -> `2.401005e+6`), which otherwise
  breaks GCBM growth-curve lookup.
- Checkpoint reprojection from EPSG:3005 to EPSG:4326, initial-age clamping, a
  constant MAT fallback, AIDB hash verification, and disturbance clipping.
- `validate_gcbm_project` structural checks and six exporter tests.
- `docs/guides/gcbm-export.rst`.

## Real TSA24 smoke

Export:

- Checkpoint: `/tmp/opencode/tsa24_checkpoint.feather`.
- Package: `/tmp/opencode/tsa24_carbon_package_ds` (108 tracks, 6,016,466.4 ha).
- Selection: AU **2401005**, first **500** fragments, resolution **0.005 deg**,
  2020-2030.
- Output: **500 fragments, 2 tracks, 4,789.8 ha**.
- AIDB: `cbm_defaults_v1.2.9300.391.db`, SHA-256
  `4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155`, matching
  the package.

Walltowall/GCBM host:

- Windows Python 3.10 and the bundled walltowall/GCBM wheels were installed
  under Wine 9.0.
- `walltowall prepare` was run in the project directory with GDAL/PROJ data on
  the path. It produced `layers/tiled`, `input_database/gcbm_input.db`, and
  `gcbm_project`.
- Wine's multiprocessing limit (63 handles / 64 workers) required a serial-pool
  workaround in the external Python site-packages. This is an environment
  workaround, not exporter code, and is documented in the guide.
- GCBM `moja.cli.exe` ran 2020-2030: **276 processed land units, 196 result
  locations, 0 errors, 107 s**.
- WS4 `ws4 gcbm` read the output: **12 steps, 1,489,453.2 -> 1,504,436.7 tC**.

A full 7,314-fragment export at 0.001 degrees was produced but not tiled; the
bounded 500-fragment smoke is the evidence for the prepare/run bridge.

## Verification

- `tests/test_gcbm_export.py`: **6 passed**.
- `mypy src/femic/gcbm/export.py`: clean.
- `ruff` on the new module and tests: clean.
- `sphinx-build -b html docs _build/html -W`: pending final run.
- Existing carbon/config/validation tests remain green.

## Boundaries

- MAT is a constant 3.0 C placeholder; absolute stocks are not interpretable
  until a reviewed climate layer is supplied.
- One baseline track/species per AU/IFM; species- and state-resolved curves are
  later work.
- No retention/partial-harvest transition beyond the package disturbance map.
- Access `.mdb` AIDBs are rejected; the lane uses the SQLite AIDB.
- The Wine serial-pool workaround is external and not part of the FEMIC CLI.
