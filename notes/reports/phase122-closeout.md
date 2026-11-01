# P122 BA-only pilot acceptance — close-out package

## Header

Phase: P122
Parent issue: #542
Pull request: https://github.com/UBC-FRESH/femic/pull/544
Instance pull request: https://github.com/UBC-FRESH/femic-tsa23-instance/pull/48
Evidence head: `dfea10c` on `feature/p122-ba-pilot-acceptance`
Report date: 2026-11-01
Status: pr-open; CI pending

## Recommendation

1. Approve the BA-only product as an experimental layer.
2. Reject it for operational use.
3. Do not create a tag or GitHub release.
4. Keep height and volume research-only.

## Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Table and raster readable | pandas/rasterio checks pass | met |
| Row/pixel identity | 2,942,755 both | met |
| Mean identity | 23.87 m2/ha both | met |
| Coverage recorded | 14.9% TSA; 9.35% full raster | met |
| Strict BA error recorded | 36 in-range, 8.86 m2/ha | met |
| VRI/THLB not inferred | marked not computed; annex not materialized | met |
| Tests and docs | 21 tests; Sphinx `-W` | met |
| Phase PR queued | #544; instance #48 | met |

## Workflow compliance

- Parent issue #542 and child #543 exist and are linked.
- Branch `feature/p122-ba-pilot-acceptance`.
- Commits use the P122.1 task ID.
- Roadmap, changelog, plan, consumer note, and manifest are in the change set.
- No tag or release was created.

## Gate evidence

- `PYTHONPATH=src pytest -q tests/test_lidar_inventory.py` -> 21 passed.
- `sphinx-build -b html docs _build/html -W` -> build succeeded.
- BA table/raster rows and means match; manifest hashes match.
- Local `ruff`/`mypy` baseline deviations remain documented.

## CI evidence

To be recorded after the final PR head is checked.

## Deviations and risks

- VRI/THLB coverage was not computed because the instance annex geometry is not
  materialized. This is recorded, not filled with inferred numbers.
- No WS4/FHOPS end-to-end consumer run was executed.
- The product is a 14.9% BA-only experimental layer; it is not operational.

## Next phase

No next phase until acceptance is approved. Separate local gate cleanup from
scientific work.

## Decision

Approve experimental acceptance and operational rejection. Merge after CI is
green on the PR head. Do not tag or release.
