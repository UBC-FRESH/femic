``femic.lidar.hydrography`` Module
===================================

The :mod:`femic.lidar.hydrography` module derives screening-level stream
candidates from a native DEM. It fills depressions, routes D8 flow, thresholds
flow accumulation, compares candidates with aligned public hydrography, and
writes a JSON review manifest plus a Markdown caveat report.

Use this page when you are deriving, reviewing, or comparing terrain-derived
stream candidates rather than compiling general terrain products.

Start Here If...
----------------

Use this page first if you are trying to:

- derive screening stream candidates from a DEM;
- resume or tune a D8 flow-accumulation workflow;
- compare candidate streams with an aligned public-hydrography raster or
  vector;
- inspect comparison precision, recall, F1, or Jaccard; or
- review the mandatory caveats before operational use.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.lidar.hydrography import (
       compare_stream_candidates,
       derive_stream_candidates,
   )

   result = derive_stream_candidates(
       Path("data/lidar/dem.tif"),
       Path("data/lidar/stream_candidates"),
       accumulation_threshold=100,
       reference_path=Path("data/public/fwa_streams.geojson"),
   )
   metrics = compare_stream_candidates(candidate_mask, reference_mask)

Key Entry Surfaces
------------------

- :func:`fill_dem_depressions`
  Priority-flood depression filling with an isolation count.
- :func:`derive_d8_flow_direction`
  D8 direction codes and downstream flat indices.
- :func:`accumulate_d8_flow`
  Upstream-cell accumulation over the D8 network.
- :func:`compare_stream_candidates`
  Overlap and agreement metrics for candidate/reference masks.
- :func:`derive_stream_candidates`
  End-to-end candidate workflow with review manifest and caveat report.
- :func:`write_stream_candidate_manifest`
  Persist the JSON review manifest.
- :func:`write_stream_candidate_review`
  Persist the human-readable caveat and checklist report.

Cross-References
----------------

- :doc:`../../guides/lidar-stream-candidates`
- :doc:`../contracts/lidar-stream-candidates`
- :doc:`femic-lidar-terrain`
- :doc:`femic-lidar`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.hydrography

.. automodule:: femic.lidar.hydrography
   :members:
   :undoc-members:
   :show-inheritance:
