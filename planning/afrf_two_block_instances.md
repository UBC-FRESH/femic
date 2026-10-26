# AFRF Block Instance Bootstrap Notes

## Governing Issues

Gavin Lake:

- `UBC-FRESH/femic-afrf-gavinlake-instance#1`: Phase 0, bootstrap and
  structural parity (complete)
- `UBC-FRESH/femic-afrf-gavinlake-instance#7`: Phase 1, scenario translation
  and baseline benchmark (planned)

Knife Creek:

- `UBC-FRESH/femic-afrf-knifecreek-instance#1`: Phase 0, bootstrap and
  growth-engine contract (complete)
- `UBC-FRESH/femic-afrf-knifecreek-instance#7`: Phase 1, data acquisition and
  stem lists (planned)

Parent FEMIC registration note: this planning note and the two submodule
entries. There is no FEMIC roadmap phase for the block models yet; the block
repos own their phases.

## Repositories

- `UBC-FRESH/femic-afrf-gavinlake-instance`
  - linked at `external/femic-afrf-gavinlake-instance`
- `UBC-FRESH/femic-afrf-knifecreek-instance`
  - linked at `external/femic-afrf-knifecreek-instance`

Both are public. Both follow the UBC-FRESH dev workflow seed: phase/task
roadmap, GitHub parent and child issues, changelog, ADRs, green dashboard.

The future merged model is reserved as `UBC-FRESH/femic-afrf-instance`. It
does not exist yet.

## Why two instances

The blocks are geographically disconnected and differ in ecology, management
objective, and growth engine. A single model built now would force one growth
engine and one policy surface onto both blocks.

Gavin Lake:

- legacy Patchworks age-class matrix from Cosmin Man;
- complete H variant with 2,907 blocks and 5,663.66 ha;
- ws4 ingest path because the archive has no ForestModelXML;
- structural parity is recorded: initial growing stock 1,418,962.31 m3 vs the
  legacy implied 1,418,963.33 m3.

Knife Creek:

- predominantly IDF, shade-tolerant Douglas-fir, and almost the whole block
  under mule-deer winter-range constraints;
- even-aged clearcutting is largely unavailable;
- growth engine is FVS-BC through `UBC-FRESH/fresh-fvsbc`, pinned at
  `ca33d0e26a079a72add5108f1b182b798b0c4e3e` (0.11.0);
- ws4 receives a state-transition library, not an age-class yield table;
- no field data or run exists yet.

## Merge contract

The merge is a separate project. The block instances keep native identifiers:

- Gavin Lake block IDs stay `1..999,999`.
- Knife Creek block IDs are offset by `1,000,000` in the merged model.
- The merged topology is block-diagonal; no cross-block edges.
- Shared account names stay global; block-specific groups are prefixed
  `gl.` or `kc.`.

The full contract is in each instance's merge ADR.

## Submodule registration

Add or refresh the submodules:

```bash
git submodule update --init external/femic-afrf-gavinlake-instance
git submodule update --init external/femic-afrf-knifecreek-instance
git submodule update --remote external/femic-afrf-gavinlake-instance
git submodule update --remote external/femic-afrf-knifecreek-instance
```

The submodule branch is `main` in both repositories.

## Current state

Both Phase 0 bootstraps are complete and merged. Both Phase 1 efforts are
planned and not active. No Gavin Lake scenario result and no Knife Creek model
result is claimed.

## Next bounded moves

1. Approve and activate Gavin Lake P1 (#7): translate the remaining scenarios
   and build a reviewed baseline schedule.
2. Approve and activate Knife Creek P1 (#7): acquire the boundary, inventory,
   BEC, site index, disturbance, mule-deer constraints, and stem-list basis.
3. Do not create the merged repository until both block models have a stable
   ws4 dataset and a release.
