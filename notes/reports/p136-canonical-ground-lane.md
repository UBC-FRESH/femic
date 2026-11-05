# P136 close-out: canonical ground lane in FEMIC

Phase: P136 Canonical Ground Lane in FEMIC
Parent issue: #584
Pull requests: #586 (FEMIC port), UBC-FRESH/fresh-urban-forest-lab#145 (legacy writer removal)
Evidence head: `7d64201` (FEMIC main after P136.1)
Report date: 2026-11-05
Status: complete; synthetic and real-tile validation

## Summary

FEMIC is now the canonical owner of the ground-classification lane.

- The PTD-inspired classifier, low-point mask, SOR mask, bundle writer, and CLI live in
  `femic.lidar`.
- `femic lidar ground-bundle-build` writes the existing `femic.ground-bundle.v1` and
  `femic.ground-qa.v1` contract without changing any default LidarBC product.
- `fresh-urban-forest-lab` no longer ships the bundle writer or `ground-adapter` CLI. It keeps
  `classify_ground_ptd` only as a point-cloud prototype for urban ALS experiments.

There was never a runtime import between the repositories. The confusing part was ownership:
the writer lived in the urban-forest app while the schema and consumers were FEMIC/FHOPS.

## Evidence

- FEMIC port: 33 classifier and writer tests pass.
- Golden tile: 113,775 points -> 82,530 ground, 78,965 low flags, no warnings.
- The FEMIC reader reads the FEMIC-written bundle and sees `is_ground`, `hag`, `is_low`, and
  `ref_class`.
- Sphinx docs build with warnings as errors.
- The `fresh-urban-forest-lab` dashboard is green after the writer removal.
- The upstream cross-repo contract was already proven on the TFL6 tile in P135.

## Limits

- No field or manual ground labels; the classifier output is not an accuracy estimate.
- The writer is opt-in and workstation-capable; large tiles remain local.
- No default FEMIC product, tag, release, or setting changed.
- The urban-lab classifier prototype remains until a later cleanup decides whether to delete
  it or keep it as a generic utility.

## Verification

- `PYTHONPATH=src python -m pytest tests/test_lidar_ground_classification.py tests/test_lidar_ground_adapter.py -q`
- `mypy src/femic/lidar/ground_classification.py src/femic/lidar/ground_adapter.py`
- `sphinx-build -b html docs _build/html -W`
- `python scripts/dashboard.py` in `fresh-urban-forest-lab`

## Next

- Manual ground-label validation remains the evidence gap.
- Any future ALS conditioning or ground work belongs in FEMIC first.
