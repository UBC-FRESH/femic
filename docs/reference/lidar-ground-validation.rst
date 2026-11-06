LiDAR ground-classification validation
======================================

This page summarizes the ground-classifier evidence behind the optional ground bundle. It
is a validation record, not a new product contract. The operational contract is in
:doc:`contracts/lidar-ground-bundle`.

The classifier is opt-in. No default FEMIC LidarBC product depends on it.

Evidence at a glance
--------------------

.. list-table::
   :header-rows: 1
   :widths: 22 40 38

   * - Phase
     - What was tested
     - Result
   * - P135
     - Real TFL6 crop, seven blocks, 137,428,675 points
     - 36,662,162 predicted ground (26.68%); 20.29% low-point flags; HAG p95 21.4207 m;
       30.4 min; no field labels
   * - P137
     - Squamish public control: open mudflat + closed-canopy first returns
     - 5,461 ground and 9,284 non-ground labels; precision 0.9970; recall 0.9872
   * - P138
     - 54-setting sensitivity grid on the Squamish control
     - P135 defaults: recall 0.9742, canopy false ground 0.00141; best 2 m / 30 deg /
       0.3 m: recall 0.9998, false ground 0.00011
   * - P139
     - Candidate settings on two TFL6 blocks and Golden 2021
     - Candidate rejected: Golden class-2 HAG p99 worsened from 0.044 m to 0.340 m
   * - P140
     - Public-control CI guard
     - Ground recall >= 0.95 and canopy false ground <= 0.005; workflow runs on PRs and
       ``main``
   * - P141
     - TFL6 steep-block false-negative audit
     - 53% of class-2 false negatives were SOR-removed; kept-point recall 0.9049; 99.4% of
       kept false negatives had HAG <= 0.15 m
   * - P142
     - Opt-in near-surface pass
     - Default stays strict; enabled mode raises Squamish recall to 0.9903 and TFL6
       SOR-off recall to 0.9990

What the evidence supports
--------------------------

- The strict classifier is usable on real LidarBC ALS tiles.
- The P135 defaults are conservative and robust across TFL6, Golden, and Squamish.
- The public Squamish control shows the strict mask does not systematically call canopy
  first returns ground.
- The P138 candidate parameter change is not safe as a default because it degraded Golden
  class-2 HAG.
- The P141 audit found that the remaining TFL6 recall gap is mostly SOR removal and a
  conservative final mask, not a bad TIN surface.
- The P142 near-surface pass is available as an opt-in terrain-surface mode.

What the evidence does not support
----------------------------------

- It is not a field-validated accuracy estimate.
- It does not validate ground under a closed forest canopy; the Squamish control has open
  mudflat ground and canopy first returns, not hidden forest floor.
- It does not make TFL6-specific claims from the Squamish public control.
- The class-2 reference is incomplete, especially on TFL6.
- Parameter tuning on one small coastal patch is not a general tuning set.

Strict versus terrain-surface ground
------------------------------------

The default bundle is **strict ground**. ``is_ground`` excludes points that the final PTD
surface passes through but the densification mask did not add.

The opt-in ``--include-near-surface`` mode is **terrain-surface ground**. It adds points
within ``--near-surface-tolerance-m`` of the final surface to ``is_ground``. ``hag`` and
``is_low`` are unchanged, so the low-point band remains available. This mode can include
low vegetation and is not mineral-ground-only.

Public control data
-------------------

The Squamish control uses:

- District of Squamish 2024 7.5 cm orthophoto, Open Government Licence - Squamish;
- LidarBC 2019, 8 points/m2, Open Government Licence - British Columbia.

The compact CI fixtures are under ``tests/fixtures/lidar/ground_control/``. Raw orthophoto
and LAZ bytes are not tracked.

Reproduction
------------

Build a bundle with the strict default::

   femic lidar ground-bundle-build data/lidar/crop/tfl6_blocks.laz \
     output/ground/tfl6_blocks \
     --crs EPSG:3156 --vertical-datum CGVD2013

Build a terrain-surface bundle::

   femic lidar ground-bundle-build data/lidar/crop/tfl6_blocks.laz \
     output/ground/tfl6_blocks \
     --crs EPSG:3156 --vertical-datum CGVD2013 \
     --no-sor --include-near-surface --near-surface-tolerance-m 0.15

Run the public-control guard::

   python -m pytest tests/test_lidar_ground_control_fixture.py -q

Detailed reports
----------------

- ``notes/reports/p135-tfl6-ground-e2e.md``
- ``notes/reports/p137-squamish-control-patch.md``
- ``notes/reports/p138-ptd-sensitivity.md``
- ``notes/reports/p139-candidate-settings.md``
- ``notes/reports/p140-ground-control-guard.md``
- ``notes/reports/p141-tfl6-false-negative-audit.md``
- ``notes/reports/p142-near-surface-ground.md``

Licence and attribution
-----------------------

The public control uses OGL-Squamish orthophoto and OGL-BC LidarBC point clouds. Retain the
source attribution and licence notices when reusing derived labels or metrics.
