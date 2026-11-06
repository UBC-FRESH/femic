# Arbor method-mining close-out

Date: 2026-11-06
Status: complete
Scope: Arbor-derived methods in FEMIC and the related `fresh-urban-forest-lab` prototype
Issue: #608

## Bottom line

There is **no Arbor integration** in FEMIC.

- No Arbor package, R code, C++ code, model object, or vendored GPL source is imported.
- Arbor was used as a method and design reference only.
- The implementation is a clean-room Python reimplementation with cited provenance.
- The ALS-relevant lane is complete. The remaining Arbor methods are MLS/TLS-oriented and
  are not part of the current FEMIC product.

General FEMIC work after this point — TIPSY configuration, SiteProd, debug rows, biomass
curves, CI, and packaging — is **not Arbor work** and should not be described as such.

## What was actually taken

| Arbor method | Arbor reference | Current location | Used by the ground lane? |
| --- | --- | --- | --- |
| Statistical outlier removal (SOR) | `src/utils/sor.cpp` | `femic.lidar.ground_classification.statistical_outlier_mask` | Yes, optional |
| Progressive TIN densification (PTD) | Book ch. 4; `src/segment/segment_ground_api.cpp`; Axelsson (2000) | `femic.lidar.ground_classification.classify_ground_ptd` | Yes |
| Low-point / near-ground cut | Book ch. 4 | `femic.lidar.ground_classification.low_point_mask` | Yes |
| Barycentric voxel decimation | Book ch. 3 | `femic.lidar.ground_classification.hybrid_homogenize`; also retained in `fresh-urban-forest-lab` | No; generic helper |
| Voxel connected components | `src/utils/Grid3D.cpp` | `femic.lidar.ground_classification.voxel_connected_components`; also retained in `fresh-urban-forest-lab` | No; generic helper |
| Local anisotropy | `src/utils/anisotopy.cpp`; book ch. 5 | `femic.lidar.ground_classification.local_anisotropy`; also retained in `fresh-urban-forest-lab` | No; generic helper |

The **near-surface consistency pass** is a FEMIC extension, not an Arbor method:

- `femic.lidar.ground_classification.near_surface_mask`
- opt-in `include_near_surface` / `near_surface_tolerance_m` in the ground adapter.

## What was not taken

- Arbor semantic/instance segmentation and the pathfinder.
- Arbor seed detection.
- QSM and QSF.
- Arbor tree models, R wrappers, C++ implementations, and bundled libraries.
- Any GPL-3.0 source code or model object.
- Any MLS/TLS-specific workflow.

## Why the lane stops here

- Arbor is GPL-3.0; direct copying would change the licence posture of this MIT-compatible
  project.
- Arbor is primarily an MLS/TLS forest point-cloud pipeline. FEMIC's operational need was
  ALS conditioning and ground classification.
- The ALS ground lane now has:
  - a canonical FEMIC implementation and writer;
  - a public Squamish control patch;
  - parameter-sensitivity evidence;
  - TFL6 and Golden terrain tests;
  - a false-negative audit;
  - an opt-in near-surface pass;
  - a CI guard.
- The remaining Arbor methods need MLS/TLS data, validation, and a separate product need.
  Porting them now would add surface area without evidence.

## Evidence

- `notes/reports/p135-tfl6-ground-e2e.md`
- `notes/reports/p137-squamish-control-patch.md`
- `notes/reports/p138-ptd-sensitivity.md`
- `notes/reports/p139-candidate-settings.md`
- `notes/reports/p140-ground-control-guard.md`
- `notes/reports/p141-tfl6-false-negative-audit.md`
- `notes/reports/p142-near-surface-ground.md`
- `docs/reference/lidar-ground-validation.rst`
- `tests/fixtures/lidar/ground_control/`
- `.github/workflows/ground-classifier-guard.yml`

## If Arbor work resumes

Treat it as a new, separately justified lane. It would need:

1. a specific MLS/TLS product requirement;
2. public or project MLS/TLS data with validation;
3. a GPL-boundary review if any Arbor source is copied rather than reimplemented;
4. a new roadmap phase and CI guard.

Until then, Arbor is a cited method source, not an integration target.
