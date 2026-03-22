``femic.pipeline.siteprod`` Module
==================================

The :mod:`femic.pipeline.siteprod` module owns FEMIC's SiteProd raster
resolution and assignment seam. It handles the species-code mapping between VRI
and SiteProd layers, loads the canonical SiteProd band-map sidecar when a
pre-stacked multiband TIFF is available, falls back to ArcRasterRescue or
native ArcGIS Pro export when that canonical artifact is unavailable, and
computes per-stand mean site productivity values from the chosen raster.

If you are debugging why Stage 00 selected the wrong SiteProd band for a
species, why FEMIC is trying to export rasters from the FileGDB instead of
using the canonical ``siteprod.tif``, or why stand-level ``siteprod`` values
look wrong after raster masking, this is the first module to read. In practice
it owns:

- species-code normalization from VRI-style codes into the 22-layer SiteProd
  code space
- canonical ``siteprod.bandmap.json`` loading and validation
- ArcRasterRescue executable resolution plus Windows ArcGIS Pro fallback
- per-species raster export and multiband stacking when canonical artifacts are
  unavailable
- stand-level mean SiteProd assignment from the selected stacked raster

Start Here If...
----------------

Use this page first if you are trying to:

- understand why FEMIC prefers a published ``siteprod.tif`` +
  ``siteprod.bandmap.json`` pair over live FileGDB export
- debug whether SiteProd layer discovery should use ArcRasterRescue or Windows
  ArcGIS Pro fallback
- inspect how VRI species codes like ``FDI`` or ``PLI`` map onto SiteProd
  layer codes
- trace how one stand row gets its mean SiteProd value from the stacked raster
- figure out whether a SiteProd problem belongs here, in
  :mod:`femic.pipeline.io`, or in the broader geospatial bootstrap/runtime
  setup

Typical maintenance path:

1. Start with :func:`load_siteprod_bandmap` if the issue is about the canonical
   band-map sidecar or species-to-band indexing.
2. Move to :func:`list_siteprod_layers` and
   :func:`resolve_arc_raster_rescue_executable_path` if the failure involves
   FileGDB discovery, ArcRasterRescue, or Windows fallback behavior.
3. Read :func:`export_and_stack_siteprod_layers` if FEMIC is rebuilding the
   multiband TIFF from individual exports.
4. Finish with :func:`assign_siteprod_from_raster` and
   :func:`mean_siteprod_for_row` if the problem is in the stand-level raster
   masking or species-band selection itself.

Typical Usage
-------------

The preferred maintenance path is to load the canonical band map for a
published ``siteprod.tif`` pair rather than re-exporting from the FileGDB:

.. code-block:: python

   from pathlib import Path
   from femic.pipeline.siteprod import load_siteprod_bandmap

   layer_species, species_layer = load_siteprod_bandmap(
       bandmap_path=Path("external/femic-public-data/data/bc/siteprod/siteprod.bandmap.json")
   )

How This Fits Into The Pipeline
-------------------------------

This module sits inside the Stage 00 geospatial/data-prep path. Its job is to
turn the available SiteProd source artifacts into one reliable assignment
surface for stand records:

1. :mod:`femic.pipeline.io` decides whether FEMIC should use instance-local or
   canonical SiteProd artifacts
2. this module loads the canonical band map when a paired TIFF + JSON sidecar
   exists, or falls back to live layer discovery/export when it does not
3. the chosen stacked raster is masked per stand geometry to derive mean
   positive SiteProd values
4. downstream Stage 00/01a logic consumes those stand-level SiteProd values as
   part of inventory conditioning and yield-curve preparation

That means this module is the code-level owner of the SiteProd-specific logic,
not of overall instance-root artifact selection. If FEMIC picked the wrong data
root, inspect :mod:`femic.pipeline.io` first. If it picked the right SiteProd
artifacts but still mapped bands, species, or raster values incorrectly, the
bug usually lives here.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`siteprod_species_lookup`
  Normalize VRI-style species codes into SiteProd layer codes with explicit
  first-letter fallbacks.
- :func:`load_siteprod_bandmap`
  Load the canonical JSON sidecar describing SiteProd band ordering.
- :func:`resolve_arc_raster_rescue_executable_path`
  Find the effective ArcRasterRescue executable using config, env, instance
  root, and source-root fallbacks.
- :func:`list_siteprod_layers`
  Discover the available SiteProd layers from ArcRasterRescue or Windows
  ArcGIS Pro fallback.
- :func:`export_and_stack_siteprod_layers`
  Export per-species rasters and stack them into the multiband ``siteprod.tif``
  surface.
- :func:`assign_siteprod_from_raster`
  Compute stand-level mean SiteProd values from the chosen stacked raster.
- :func:`mean_siteprod_for_row`
  Core helper for per-row masking and positive-value averaging.

Canonical Artifact And Fallback Rules
-------------------------------------

The most important runtime contracts in this module are:

- the preferred runtime path is a canonical paired
  ``siteprod.tif`` + ``siteprod.bandmap.json`` artifact set
- the band-map sidecar may be expressed through ``bands_0_based``,
  ``bands_1_based``, or ``ordered_species``, and this module normalizes those
  representations into one species<->band mapping
- when canonical artifacts are unavailable, FEMIC falls back to live FileGDB
  layer discovery and per-species export
- ArcRasterRescue is the preferred live-export path when its executable is
  available; on Windows only, ArcGIS Pro Python is the documented fallback
- temporary per-species GeoTIFF exports are stacked into one multiband raster
  and then cleaned up

These rules are why SiteProd behavior is so environment-sensitive. A checkout
with published canonical artifacts should avoid heavyweight export work. A
checkout without them must have a usable ArcRasterRescue or Windows ArcGIS Pro
surface before Stage 00 can continue reliably.

Platform-Sensitive Runtime Behavior
-----------------------------------

One of the most important behaviors in this module is the split between the
preferred cross-platform helper and the Windows-only fallback:

- ArcRasterRescue is resolved from explicit env override, configured path, and
  source-root or instance-root-relative fallbacks
- FileGDB paths are normalized with a trailing ``.gdb/`` form when needed for
  ArcRasterRescue
- ``FEMIC_ARC_RASTER_RESCUE_TIMEOUT_SEC`` controls export timeout behavior and
  falls back to 900 seconds when unset or invalid
- if ArcRasterRescue is unavailable and the host is Windows, FEMIC falls back
  to ArcGIS Pro Python for layer listing and raster export
- if ArcRasterRescue is unavailable on non-Windows hosts, the export path fails
  fast instead of guessing a different geoprocessing stack

This is the code-level owner of the platform guidance documented in the Stage
00 and geospatial bootstrap guides.

Stand-Level Assignment Contract
-------------------------------

Once a stacked SiteProd raster exists, the assignment contract is:

- choose the species layer for each stand from ``SPECIES_CD_1`` or an explicit
  lookup fallback
- mask the raster by stand geometry
- keep only positive values from the selected species band
- write the mean of those values to the target output column, defaulting to
  ``siteprod``

If that output looks wrong, the likely failure modes are a bad species mapping,
an incorrect band map, geometry/masking issues, or all-positive values being
filtered away to ``NaN``.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- species-code drift
  unexpected VRI species codes can fall through the lookup table and raise
  ``ValueError`` if no first-letter fallback exists
- invalid or missing band-map sidecar
  malformed JSON or missing required band-order fields breaks the canonical
  pre-stacked path
- ArcRasterRescue resolution failures
  a configured relative path may resolve differently across source checkout,
  instance-root, and env-override contexts
- export/stack runtime failures
  ArcRasterRescue can time out or return stderr-only failures, and Windows
  ArcGIS Pro fallback depends on an explicit Pro Python installation
- raster masking surprises
  wrong geometry, wrong species-band mapping, or no positive values in the
  selected band can silently degrade stand-level SiteProd assignment

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/stage-00-data-prep`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../run-config`

Related API pages:

- :doc:`femic-pipeline-io`
- :doc:`femic-pipeline-vdyp-stage`
- :doc:`femic-workflows-legacy`

.. toctree::
   :hidden:

   generated/femic.pipeline.siteprod

.. automodule:: femic.pipeline.siteprod
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
