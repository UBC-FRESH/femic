# P132 close-out: optional ground-bundle reader

Phase: P132 Optional Ground-Bundle Reader
Parent issue: #572
Pull request: the P132 PR, `feature/p132-ground-reader` into `main`
Evidence head: the P132.1 commit
Report commit: the commit that adds this report
Date: 2026-11-04
Status: implemented; optional read-only adapter

## Summary

FEMIC can now validate and inspect the sidecar ground bundle produced by
`fresh-urban-forest-lab`:

- `femic.lidar.ground_bundle.read_ground_bundle`;
- `femic lidar ground-bundle PATH`;
- `docs/guides/lidar-ground-bundle.rst`;
- `docs/reference/contracts/lidar-ground-bundle.rst`.

The reader validates `femic.ground-bundle.v1` and `femic.ground-qa.v1`, file hashes,
parameter hash, point counts, required QA fields, and optional LAZ dimensions. It is
read-only and does not change any default FEMIC product.

## Evidence

- Synthetic-bundle tests: 8 passed.
- Cross-repo read: the P21 coastal bundle
  (`415,068` points, `374,711` ground, `374,787` low) validated with no warnings and the
  four extra dimensions.
- `laspy[lazrs]` is optional; without it, the reader validates manifest/QA and records a
  warning that point inspection was skipped.
- The reader does not import `fresh-urban-forest-lab`.

## Limits

- The reader validates a sidecar; it does not create one.
- It does not validate ground-classification accuracy.
- It does not change FEMIC's default LidarBC products.
- The real cross-repo bundle read is local, not a CI network job.

## Verification

- `PYTHONPATH=src python -m pytest tests/test_lidar_ground_bundle.py -q`
- `ruff check --select E,F src/femic/lidar/ground_bundle.py tests/test_lidar_ground_bundle.py`
- `mypy src/femic/lidar/ground_bundle.py tests/test_lidar_ground_bundle.py`
- `sphinx-build -b html docs _build/html -W`
