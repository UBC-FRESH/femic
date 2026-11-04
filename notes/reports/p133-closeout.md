# P133 close-out: ground-bundle block summary

Phase: P133 Ground-Bundle Block Summary
Parent issue: #575
Pull request: the P133 PR, `feature/p133-ground-summary` into `main`
Evidence head: the P133.1 commit
Report commit: the commit that adds this report
Date: 2026-11-04
Status: implemented; optional read-only summary consumer

## Summary

FEMIC can now summarize a validated ground bundle over planning polygons:

- `femic.lidar.ground_summary.summarize_ground_bundle`;
- `femic lidar ground-summary BUNDLE --polygons PATH --out CSV`;
- per-polygon point count, ground/low fractions, and HAG mean/p50/p95/max;
- CSV plus `femic.ground-summary.v1` manifest.

The command is opt-in and does not change any default FEMIC product.

## Evidence

- Synthetic-bundle tests: 6 passed.
- Real coastal bundle summary over a single AOI polygon:
  - 415,068 points;
  - 374,711 predicted ground (90.277%);
  - 374,787 low-point flags (90.295%);
  - HAG mean 2.0045 m, p50 0.0 m, p95 24.185 m, max 59.4299 m;
  - no warnings.
- Compound CRS handling: point CRS `EPSG:3157+5703` compares against polygon CRS
  `EPSG:3157` after dropping the vertical component.
- Docs build with warnings as errors.

## Limits

- The summary describes the predicted surface, not field-validated ground accuracy.
- It requires matching horizontal CRS; there is no silent reprojection.
- It requires `laspy` for point reading; the reader-only path still works without it.
- The real coastal summary is local, not a CI network job.

## Verification

- `PYTHONPATH=src python -m pytest tests/test_lidar_ground_summary.py -q`
- `ruff check --select E,F src/femic/lidar/ground_summary.py tests/test_lidar_ground_summary.py`
- `mypy src/femic/lidar/ground_summary.py`
- `sphinx-build -b html docs _build/html -W`
