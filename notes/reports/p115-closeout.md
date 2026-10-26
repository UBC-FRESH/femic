# P115 closeout: forest carbon domain, CBM packages, and GCBM export

Date: 2026-10-26
Phase: P115
Parent: #361
Branch: `feature/p115-forest-carbon`

## 1. Delivered

- **P115.1** — reviewed carbon domain contract and crosswalks, corrected against the
  public BC VRI dictionary, CBM-CFS3 v1.2 User's Guide, and TSA/ecozone GIS
  intersections. Review packet: `notes/reports/p1151-crosswalk-review.md`.
- **P115.2** — static CBM carbon package exporter from FEMIC bundles/checkpoints.
- **P115.3** — TSA24/MKRF `carbon:` configs, `femic carbon validate`, public-safe
  fixture, CI coverage, and docs.
- **P115.4** — `femic export gcbm`, walltowall JSON/layers/AIDB/manifest, real TSA24
  prepare and GCBM smoke.
- **P115.5** — TSA24 package handoff, WS3 reference trajectory, exact WS3/WS4 parity,
  production TSA24 baseline, and cross-repo handoff to WS4 #357.
- **P115.6** — CBM4 status, engine-adapter boundary, version-pin policy, and platform
  watchlist.

## 2. Evidence

- Crosswalk checker: 41 species rows / 36 VRI codes, 10 TSA/MKRF rows, 8 disturbance
  rows, 2 land classes; all names and VRI codes valid.
- TSA24 v2 package: `femic-carbon-24-d7a5dc27910f`, 108 tracks, 6,016,466.4 ha,
  3,348 yield rows; WS4 fingerprint `153f0060...`; archive SHA-256 `111feaeb...`.
- WS3 `tsa24_clipped`: 264,504.7 -> 274,479.4 tC over 20 steps; WS3/WS4 pools and flux
  exact (`max_abs = 0.0`, `max_rel = 0.0` at 1e-6).
- WS4 TSA24 AU 2401005 baseline: 21,774,124.4 -> 21,949,881.3 tC over five years.
- GCBM smoke: 500 fragments, 4,789.8 ha, 2020-2030, 1,489,453.2 -> 1,504,436.7 tC;
  walltowall prepare produced `gcbm_input.db` and `gcbm_project`.
- Verification: carbon/GCBM targeted tests pass; carbon modules clean under `mypy` and
  targeted `ruff`; Sphinx `-W` passes; dashboard carbon lane green.

## 3. Deferred

- Multi-boundary carbon packages for TSA 08, 16, 40, 41 and the small overlaps in
  TSA 24, 29, 46, 47.
- Fertilization growth response plus fertilizer life-cycle/N2O accounting.
- Species-resolved curves for S/Sx, SB, and the Douglas-fir group.
- Intensity-specific `ct` matrix and MPB severity input.
- Full 536k-fragment TSA24 carbon-aware search (baseline runtime limit).
- Same-landscape GCBM comparison beyond the 500-fragment smoke.

## 4. Closeout

All P115 child tasks are complete. The branch is pushed and the phase PR is queued.
Merge, branch deletion, and parent #361 closure wait for maintainer approval.
