# P134 close-out: local LAZ bbox crop and large-tile policy

Phase: P134 Local LAZ Bbox Crop and Large-Tile Policy
Parent issue: #578
Pull request: the P134 PR, `feature/p134-laz-crop` into `main`
Evidence head: the P134.1 commit
Report commit: the commit that adds this report
Date: 2026-11-04
Status: implemented; opt-in local preprocessing

## Summary

Large LidarBC tiles can be cropped locally to a block AOI before the ground adapter or
summary runs:

- `femic.lidar.crop.crop_laz_by_bbox`;
- `femic lidar crop --laz BIG --bbox ... --out SMALL`;
- `femic.laz_crop.v1` manifest.

The crop reads the source in chunks and writes only in-bbox points. It preserves the source
header/CRS and records input/output hashes, counts, bbox, CRS, and warnings.

## Large-tile policy

The TFL6 covering tile is 1.53 GB. LidarBC LAZ is not COPC, so an HTTP range read does not
avoid the full download. The supported path is:

1. materialize the tile once into a managed data root;
2. crop locally to the block AOI;
3. run the ground adapter and summary on the small crop.

Use a COPC source and a bounds-aware reader when one is available. The crop is not a
range-read client.

## Evidence

- Synthetic-LAZ tests: 5 passed.
- Header/CRS preservation checked by reading the cropped LAZ.
- Empty crops and existing outputs fail clearly.
- Docs build with warnings as errors.

## Limits

- The crop still reads the full local input; it does not reduce the one-time download.
- It is not a COPC/range-read client.
- It does not change any default FEMIC product.

## Verification

- `PYTHONPATH=src python -m pytest tests/test_lidar_crop.py -q`
- `ruff check --select E,F src/femic/lidar/crop.py tests/test_lidar_crop.py`
- `mypy src/femic/lidar/crop.py`
- `sphinx-build -b html docs _build/html -W`
