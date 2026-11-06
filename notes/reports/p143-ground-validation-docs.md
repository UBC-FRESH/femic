# P143 close-out: ground-validation documentation

Phase: P143 Ground-validation documentation close-out
Parent issue: #601
Branch: `docs/p143-ground-validation`
Pull request: the P143 PR
Date: 2026-11-06
Status: complete

## What changed

- Added `docs/reference/lidar-ground-validation.rst`.
- Added it to the root Reference toctree.
- Linked it from the ground-bundle guide and contract.
- Summarized P135-P142, strict-vs-near-surface semantics, limits, public sources, and
  reproduction commands.

## Evidence included

- P135 TFL6 end-to-end run.
- P137 Squamish public control: precision 0.9970, recall 0.9872.
- P138 parameter sensitivity and the non-adopted candidate.
- P139 TFL6/Golden candidate test and rejection.
- P140 CI guard thresholds.
- P141 SOR/final-mask audit.
- P142 opt-in near-surface pass.

## Limits stated

- No field labels.
- No ground under closed canopy.
- Squamish is not TFL6-specific.
- Class-2 reference is incomplete.
- The CI guard protects one public control, not general accuracy.

## Verification

- `sphinx-build -E -b html docs _build/html -W` passed.
- The new page is reachable from the root toctree and linked from the guide/contract.
- No machine-specific absolute paths are published.

## Next

P117.1 ALS site-index / potential-height layer is the next active FEMIC priority.
