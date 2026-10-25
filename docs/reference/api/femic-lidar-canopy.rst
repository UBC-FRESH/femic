``femic.lidar.canopy`` Module
==============================

The :mod:`femic.lidar.canopy` module owns FEMIC's native CHM, canopy structure,
and VRI uncertainty comparison. It derives ``DSM - DEM`` on exactly aligned
grids, summarizes height and cover, and records VRI comparison metrics. It does
not reproject, resample, segment trees, or claim field-level inventory accuracy.

Use this page when you are building or reviewing canopy height and cover
products rather than terrain, hydrography, or product packaging.

Start Here If...
----------------

Use this page first if you are trying to:

- derive a CHM from aligned LidarBC DSM and DEM tiles;
- summarize canopy height percentiles and cover thresholds;
- compare CHM p95/cover with VRI height/closure;
- debug a grid-alignment, vertical-datum, or VRI-field failure; or
- inspect the canopy QA report.

Typical Usage
-------------

.. code-block:: bash

   femic lidar canopy \
     --dem data/lidar/dem.tif \
     --dsm data/lidar/dsm.tif \
     --output-dir data/lidar/canopy \
     --vri data/input/vri.gpkg \
     --vri-height-field proj_height_1 \
     --vri-cover-field crown_closure

.. code-block:: python

   from pathlib import Path
   from femic.lidar.canopy import (
       build_canopy_products,
       compare_canopy_to_vri,
       derive_canopy_height_model,
   )

   chm = derive_canopy_height_model(
       Path("data/lidar/dsm.tif"),
       Path("data/lidar/dem.tif"),
       Path("data/lidar/chm.tif"),
       vertical_datum="CGVD2013",
   )
   report = build_canopy_products(
       Path("data/lidar/dsm.tif"),
       Path("data/lidar/dem.tif"),
       Path("data/lidar/canopy"),
   )
   comparison = compare_canopy_to_vri(
       chm.path,
       Path("data/input/vri.gpkg"),
   )

Key Entry Surfaces
------------------

- :func:`derive_canopy_height_model`
  Derive and QA ``DSM - DEM`` on an aligned native grid.
- :func:`derive_canopy_structure`
  Summarize height percentiles and cover thresholds from a CHM.
- :func:`compare_canopy_to_vri`
  Compare polygon-level CHM p95/cover with VRI fields.
- :func:`build_canopy_products`
  Build the CHM, structure JSON, optional VRI comparison, and QA reports.
- :class:`CanopyQaReport`
  Review artifact with source grids, CHM, structure, VRI comparison, caveats,
  and warnings.

Cross-References
----------------

- :doc:`../../guides/lidar-canopy-products`
- :doc:`../contracts/lidar-canopy-products`
- :doc:`femic-lidar-trees`
- :doc:`femic-lidar-terrain`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.canopy

.. automodule:: femic.lidar.canopy
   :members:
   :undoc-members:
   :show-inheritance:
