# P115.3 carbon config, validation, and TSA24/MKRF fixtures

Date: 2026-10-26
Phase: P115
Task: P115.3
Parent: #361
Issue: #364

## What was added

- `config/carbon/tsa24.yaml` and `config/carbon/mkrf.yaml` are the supported instance
  defaults. They select the four crosswalk CSVs, the CBM boundary, the pinned
  `cbm_defaults` version and SHA-256, the 10-year/300-year yield grid, fallbacks, and the
  draft review state.
- `femic/carbon/config.py` resolves the block, checks the schema version, refuses an
  unknown CBM eco boundary, checks every configured TSA/FMU against the eco-boundary
  crosswalk, and requires the four crosswalks to share one directory.
- `femic carbon export-package --config ...` uses the block and infers the TSA/FMU codes;
  the explicit flag form remains available.
- `femic/carbon/validate.py` and `femic carbon validate` check:
  - manifest keys, units, boundaries, table files, table hashes, and package fingerprint;
  - exactly one boundary row and matching manifest boundaries;
  - track and species classifier coverage;
  - inventory area/age/delay/land class and disturbance declarations;
  - one positive age grid, every track on it, and leading-species agreement;
  - curve-map tracks and shares;
  - optional expected area and track count.
- The public-safe fixture `tests/fixtures/carbon/tsa24_minimal` is a synthetic one-track
  TSA24/Montane Cordillera package (5.0 ha, 31 yield rows). It is not real inventory.
- `tests/test_carbon_config.py` and `tests/test_carbon_validate.py` cover the config
  loader, boundary/TSA failures, the fixture, hash/fingerprint/area/classifier failures,
  and the CLI success/failure paths.

## Evidence

- Real TSA24 package: `validate_carbon_package` succeeds with **108 tracks,
  6,016,466.4 ha, 3,348 yield rows**.
- `femic carbon validate tests/fixtures/carbon/tsa24_minimal`: succeeds with
  `tracks=1 area_ha=5.0 yield_rows=31`.
- `--expect-area-ha 6`: exits 1 with an area mismatch.
- Targeted carbon tests: **25 passed** across the package, config, validation, and domain
  config modules.
- `sphinx-build -b html docs _build/html -W`: **succeeds**.
- `mypy src/femic/carbon/validate.py src/femic/carbon/config.py`: **no issues**.
- Targeted `ruff check` on the new modules and tests: **passes**.
- Roadmap control and instance-boundary contract tests now pass.

## Boundaries

- The crosswalk science review in P115.1 is still open. Both defaults record
  `review.status: draft`; the package manifest records the crosswalk files in `sources`.
- The full repository test run is not green in this worktree: the remaining failures are
  in K3Z/TSR/patchworks/annex environment-data tests, not the carbon modules. The carbon
  tests and docs gates are green.
- The validator requires the producer's `table_files` manifest mapping. A hand-built,
  non-FEMIC package without that mapping is rejected as a manifest mismatch.
