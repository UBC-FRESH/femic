INV-01 TSA 23 Validation and Gap Analysis
=========================================

This guide records the first independent-ish checks of the TSA 23 inventory
pilot: a VRI screening comparison and a priority map of point-cloud tiles omitted
from the full run.  Neither check turns the pilot into an operational inventory.

VRI screening
-------------

The VRI file is the TSA 23 checkpoint used by the instance
(``ria_vri_vclr1p_checkpoint8.feather``, 102,132 polygons, EPSG:3005).  Cell
centres are transformed from EPSG:3157, joined by point-in-polygon, and compared
at cell and VRI-polygon level.

VRI is an interpreted polygon inventory, not independent field data.  Its
``PROJ_HEIGHT_1`` is projected/top height rather than Lorey height, and
``LIVE_STAND_VOLUME_125`` is live volume for trees >= 12.5 cm rather than FEMIC
gross volume.  The comparison is a screening check, not an accuracy estimate.

.. list-table:: Cell-level VRI disagreement
   :header-rows: 1

   * - Attribute
     - Cells
     - Model mean
     - VRI mean
     - Bias
     - RMSE
     - r
   * - Lorey height (m)
     - 5,670,064
     - 16.18
     - 18.66
     - -2.48
     - 7.65
     - 0.398
   * - Basal area (m2/ha)
     - 2,745,339
     - 24.07
     - 19.46
     - +4.61
     - 11.49
     - 0.364
   * - Gross volume (m3/ha)
     - 2,711,451
     - 141.57
     - 112.11
     - +29.46
     - 92.83
     - 0.397

The pattern is compression: low-biomass VRI stands are overpredicted and
high-biomass stands are underpredicted.  IDF BA and volume are overpredicted;
ESSF is underpredicted.  The disagreement is much larger than the pilot LOOCV
errors (height 0.688 m, BA 4.414 m2/ha, volume 20.666 m3/ha).

.. figure:: /_static/inv01-tsa23-vri-reconciliation.png
   :alt: Model versus VRI density plots for height, basal area, and volume
   :width: 100%

   Model predictions versus VRI polygon attributes.  The red line is 1:1.

The full tables and method are in
``notes/reports/inv01-tsa23-vri-reconciliation.md``.


PSP holdout: use the archive now
--------------------------------

The 14-plot calibration is a subset of the public FAIB PSP archive.  The archive
contains 7,341 sites province-wide, 200 in TSA 23, 162 of them in IDF.  TSA 23
has 455 visits; 22 visits since 2017 have a LidarBC point cloud, 18 are in the
processed tiles, and four more are in the omitted tile ``lidarbc:4:117213``.

Those four omitted IDF plots (2018 measurements, 2019 point cloud) are a real
held-out set.  We processed them with the 2019 layer-6 1 m DEM and the same
first-return protocol.  They were not used in the 14-plot fit:

.. list-table:: Four-plot PSP holdout
   :header-rows: 1

   * - Attribute
     - Observed mean
     - Predicted mean
     - Bias
     - MAE
     - RMSE
   * - Lorey height (m)
     - 19.87
     - 20.87
     - +1.00
     - 1.07
     - 1.46
   * - Basal area (m2/ha)
     - 36.61
     - 37.55
     - +0.93
     - 6.97
     - 8.35
   * - Gross volume (m3/ha)
     - 263.71
     - 352.97
     - +89.27
     - 97.64
     - 118.21

The height and BA cards retain useful signal, but volume fails this small
external test.  The four plots are clustered in one tile, so this is not a
TSA-wide spatial validation; it is enough to reject "wait for data" as the next
step and to require a refit before any operational claim.

The fifth candidate, ``4025421``, has its plot support outside the actual point
cloud extent and is excluded.  The full evidence is in
``notes/reports/inv01-tsa23-psp-holdout.md``.

Omitted-tile gap
----------------

Of 6,806 TSA-intersecting point-cloud tiles, 5,899 were processed and 907 were
omitted because they have no matching fine 2.5 km, 1 m DEM tile.  The 907 tiles
cover 1,962 km2 inside TSA 23 (15.9%), including 1,778 km2 of VRI forest and
861 km2 of VRI THLB.

All 907 have some DEM candidate, usually a larger 1:20000 layer 6 tile; they do
not have the same fine layer 5 tile used by the run.  A separate layer 6
experiment would be needed to fill them.

.. figure:: /_static/inv01-tsa23-gap-priority.png
   :alt: Priority map of omitted point-cloud tiles in TSA 23
   :width: 100%

   Omitted tiles by priority.  Grey hatched areas have no public point cloud in
   the current selection.

Coverage arithmetic:

.. list-table::
   :header-rows: 1

   * - Item
     - Area
   * - TSA 23
     - 12,353.2 km2
   * - Processed footprint inside TSA
     - 7,949.0 km2 (64.3%)
   * - All selected point clouds inside TSA
     - 9,886.7 km2 (80.0%)
   * - No public point cloud
     - 2,466.5 km2 (20.0%)
   * - Omitted 907 tiles inside TSA
     - 1,962.0 km2 (15.9%)

The priority score is a heuristic combining VRI forest area, THLB area, distance
to the nearest c5 network vertex, and distance to the nearest mill.  It is not an
economic ranking.  See ``notes/reports/inv01-tsa23-gap-priority.md`` for the
score, top tiles, and tier tables.

Recommendation
--------------

Do not operationalize the current surface.  Validate/refit with independent field
plots and a true spatial holdout before spending the download/compute budget on
the 907 tiles.  If a coverage increment is needed, start with the 182 A tiles
(49,250 ha VRI forest, 30,333 ha THLB) as a separate experiment.  The 2,466 km2
with no selected public point cloud cannot be filled without new acquisition.

Reproduction
------------

The scripts are in ``examples/inv01_tsa23_validation``:

- ``vri_reconcile.py``
- ``gap_priority.py``
- ``make_validation_figures.py``
- ``psp_holdout.py``

See Also
--------

- :doc:`inv01-tsa23-full-run`
- :doc:`../reference/contracts/inventory-als`
