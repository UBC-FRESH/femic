Terrain-Derived Stream Candidates
=================================

Purpose
-------

This guide explains P79.4: how FEMIC derives screening-level stream candidates
from a native DEM, compares them with public hydrography, and emits a review
manifest with explicit caveats.

Candidates are **not** an authoritative stream layer. They are a review aid for
steep-slope, operability, and riparian screening. Field verification and
public-hydrography adjudication are required before operational use.

Workflow
--------

1. Load a native projected-metre DEM.
2. Optionally fill depressions with a priority-flood pass.
3. Route D8 flow and accumulate upstream cells.
4. Threshold flow accumulation into candidate stream cells.
5. Optionally compare candidates with an aligned public-hydrography raster or
   vector.
6. Write candidate/accumulation rasters and a review manifest.

.. code-block:: python

   from pathlib import Path
   from femic.lidar.hydrography import derive_stream_candidates

   result = derive_stream_candidates(
       Path("data/lidar/dem/layer_5/2023/dem.tif"),
       Path("data/lidar/stream_candidates"),
       accumulation_threshold=100,
       reference_path=Path("data/public/fwa_streams.geojson"),
   )

Inputs
------

The DEM must satisfy the terrain contract:

- single band;
- projected CRS in metres;
- north-up, unrotated;
- positive pixel resolution.

Reference hydrography can be:

- a raster on exactly the same grid and CRS as the DEM; or
- a vector in exactly the same CRS.

Misaligned or different-CRS references are rejected. FEMIC never reprojects or
resamples the DEM or the reference.

Parameters
----------

- ``accumulation_threshold``: minimum upstream cell count for a candidate.
- ``fill_depressions``: priority-flood filling before flow routing.
- ``reference_path``: optional public-hydrography raster or vector.
- ``reference_all_touched``: rasterize vector cells touched by a feature.

The D8 codes are 1=E, 2=SE, 3=S, 4=SW, 5=W, 6=NW, 7=N, 8=NE. Sinks and invalid
cells receive no downstream target.

Outputs
-------

``derive_stream_candidates`` writes:

.. code-block:: text

   <output-dir>/
     stream_candidates.tif
     flow_accumulation.tif
     stream_candidates_manifest.json
     stream_candidates_review.md

``stream_candidates.tif`` is uint8: 1 = candidate, 0 = background, 255 =
nodata. ``flow_accumulation.tif`` is float32 upstream cell count.

Comparison Metrics
------------------

When a reference is supplied, the manifest records:

- candidate, reference, true-positive, false-positive, and false-negative
  cells;
- precision, recall, F1, and Jaccard;
- candidate, reference, and overlap hectares.

Metrics are descriptive. They do not prove hydrological correctness, and a
high overlap does not replace field review.

Review Manifest And Caveats
---------------------------

The manifest uses schema ``femic.lidar.stream_candidates.v1`` and records the
source DEM metadata, parameters, outputs, QA counts, comparison metrics,
caveats, and warnings.

``stream_candidates_review.md`` is the human-readable review surface. It
includes a checklist:

- compare candidates against current public hydrography;
- check DEM artefacts, culverts, bridges, and cutblocks;
- confirm the accumulation threshold for the AOI;
- record the reviewer and decision before operational use.

Caveats include:

- candidates are a screening aid, not an authoritative stream layer;
- D8 routing is sensitive to DEM artefacts, culverts, bridges, and resolution;
- depression filling changes local flow paths and may create synthetic
  channels;
- No reprojection or resampling was performed.

Limitations
-----------

- D8 is a single-flow-direction method; it does not model culverts or bridges.
- Depression filling can create synthetic gradients in flat or engineered
  terrain.
- The threshold is an AOI-specific screening choice, not a provincial
  standard.
- No stream classification, fish habitat, riparian reserve, or legal
  determination is made.

See Also
--------

- :doc:`lidar-terrain-products`
- :doc:`lidar-materialization`
- :doc:`../reference/contracts/lidar-stream-candidates`
- :doc:`../reference/api/femic-lidar-hydrography`
- :doc:`../reference/contracts/lidar-source-and-tile-index`
