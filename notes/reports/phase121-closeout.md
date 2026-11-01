# P121 BA-only TSA 23 pilot release — close-out package

## Header

Phase: P121
Parent issue: #539
Pull request: https://github.com/UBC-FRESH/femic/pull/541
Evidence head: `728f69a` on `feature/p121-ba-only-release`
Report date: 2026-11-01
Status: pr-open; CI pending

## Recommendation

1. Approve the BA-only product release as a non-operational pilot.
2. Approve the corrected P120 closeout record.
3. Do not create a tag or GitHub release without separate approval.
4. Keep height and volume research-only.

## Objectives and acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| P120 closeout corrected | merged PR `98fe2c6`, instance `3b4f58a`, issues closed | met |
| BA-only table generated | 2,942,755 rows | met |
| BA-only raster generated | 2,942,755 valid pixels; 25 m, EPSG:3157 | met |
| Coverage documented | 14.9% TSA area; 9.35% of full raster | met |
| Hashes recorded | source, table, raster, model card, default config | met |
| Tests and docs pass | 21 tests; Sphinx `-W` | met |
| Phase PR queued | #541; instance #47 | met |

## Workflow compliance

- Phase issue #539 and task issue #540 exist and are linked.
- Branch is `feature/p121-ba-only-release`.
- P121.1 commits use the task ID.
- Roadmap, changelog, plan, ADR, and release note are in the change set.
- No tag or release is created.

The P120 closeout record was corrected in this phase because it still said
draft/awaiting after the merge. This is recorded as a documentation defect, not
a rewrite of the P120 history.

## Gate evidence

- `PYTHONPATH=src pytest -q tests/test_lidar_inventory.py` -> 21 passed.
- `sphinx-build -b html docs _build/html -W` -> build succeeded.
- BA table rows and raster valid pixels both 2,942,755.
- BA table and raster means both 23.87 m2/ha.
- Local `ruff` and `mypy` baseline failures remain documented from P120.

## CI evidence

Parent PR #541 and instance PR #47 are open; check CI on the final head.

## Deviations and risks

- Local baseline lint/type gates remain red; CI must be checked.
- The release is a 14.9% BA-only pilot, not an operational inventory.
- Height and volume remain unsupported as default products.
- No out-of-range cells were introduced.

## Next phase

No next phase is proposed until this release is approved. A future phase should
separate local gate cleanup from scientific work.

## Decision

Approve the corrected closeout and the BA-only pilot release. Merge only after
CI is green on the PR head; do not tag or publish a GitHub release without
separate approval.
