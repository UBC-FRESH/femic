Terrain-Derived Stream Candidate Contract
=========================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's terrain-derived
stream candidates. It defines the candidate workflow, comparison metrics,
review manifest, caveats, and the no-silent-resampling boundary for P79.4.

Candidates are a screening and review aid. They are not an authoritative
stream, riparian, fish-habitat, or legal layer.

Quick Contract
--------------

- Manifest schema: ``femic.lidar.stream_candidates.v1``.
- Flow routing: D8.
- D8 codes: 1=E, 2=SE, 3=S, 4=SW, 5=W, 6=NW, 7=N, 8=NE.
- Candidate raster: uint8, 1 candidate, 0 background, 255 nodata.
- Accumulation raster: float32 upstream cell count.
- DEM contract: single band, projected metres, north-up, unrotated.
- No reprojection or resampling of the DEM or reference.
- Review manifest and Markdown caveat report are mandatory outputs.

Candidate Workflow
------------------

1. Load the native DEM.
2. Optionally fill depressions with priority flood and a small epsilon gradient.
3. Route D8 flow from each valid cell to its steepest lower neighbour.
4. Accumulate one upstream cell per valid cell.
5. Mark cells with accumulation greater than or equal to the threshold.

Sinks and invalid cells have no downstream target. Valid cells isolated from
the outer boundary are left unfilled and reported as a warning.

Comparison Contract
-------------------

A reference can be a raster on the same grid/CRS or a vector in the same CRS.
Misalignment is an error. FEMIC does not reproject or resample either side.

The comparison records:

- candidate, reference, true-positive, false-positive, and false-negative
  cells;
- precision, recall, F1, and Jaccard;
- candidate, reference, and overlap hectares.

A missing or empty reference produces descriptive metrics with undefined
ratios where the denominator is zero. Metrics do not prove hydrological
correctness.

Review Manifest
---------------

The build writes ``stream_candidates.tif``, ``flow_accumulation.tif``,
``stream_candidates_manifest.json``, and ``stream_candidates_review.md``.

The JSON manifest records:

- source DEM metadata;
- accumulation threshold, fill flag, epsilon, D8 code map, reference path,
  reference rasterization mode, and ``resampling: none``;
- output filenames;
- valid-cell, candidate-cell, candidate-area, and accumulation summaries;
- optional comparison metrics;
- caveats and warnings.

The Markdown review report mirrors the manifest and adds a review checklist.
Both files are required outputs.

Caveats
-------

- Candidates are a screening aid, not an authoritative stream layer.
- D8 is sensitive to DEM artefacts, culverts, bridges, and source resolution.
- Depression filling changes local flow paths and may create synthetic
  channels.
- A threshold is an AOI-specific screening choice, not a provincial standard.
- Field or public-hydrography review is required before operational use.
- No stream classification, fish habitat, riparian reserve, or legal
  determination is made.

No-Resampling Rule
------------------

The workflow rejects:

- geographic or non-metre DEM CRS;
- rotated DEM transforms;
- non-positive resolution;
- reference rasters that do not exactly match the DEM grid and CRS;
- reference vectors in a different CRS.

Consumer-side reprojection, if needed, is a separate explicit decision.

See Also
--------

- :doc:`../../guides/lidar-stream-candidates`
- :doc:`lidar-terrain-products`
- :doc:`../api/femic-lidar-hydrography`
- :doc:`stage-boundaries-and-canonical-artifacts`
