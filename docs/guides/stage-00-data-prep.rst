Stage 00: Data Prep and Inventory Conditioning
==============================================

Scope
-----

Stage 00 prepares stand-level inputs used by all downstream FMU/code-targeted
runs.
It covers boundary masking, VRI cleanup, site productivity enrichment,
species-volume compilation, and intermediate checkpoints.

Inputs
------

- management-unit geometry (legacy TSA-boundary seam or custom boundary)
- VRI polygon/layer datasets
- Optional site productivity raster data (species-wise)
- Existing checkpoint feathers when resume paths are enabled
- THLB raster input (``misc.thlb.tif``), resolved from instance-local
  ``data/misc.thlb.tif`` first, then from ``FEMIC_EXTERNAL_DATA_ROOT/misc.thlb.tif``
  when running from tmp clones or other stripped instance copies

Core Processing Responsibilities
--------------------------------

- Normalize missing categorical/numeric inventory values to deterministic sentinels.
- Compute stratification fields (including lexmatch helpers and forest type classes).
- Build species-wise volume columns from VRI top species fields.
- Compile THLB signals for managed/unmanaged eligibility semantics.
- Persist intermediate checkpoints for restartable execution.

THLB interpretation note
------------------------

- FEMIC still computes stand-level THLB signal from the mean raster value over
  each stand footprint.
- The older binary/calibrated THLB snap is retained as a legacy path, but
  Patchworks-facing export now defaults to a proportional interpretation where
  the continuous THLB share is preserved and the complementary unmanaged share
  is carried through the fragments ``RETENTION`` field.
- THLB raster nodata is treated as ``0`` in the raster-mean seam unless a
  caller explicitly overrides the fallback.

Checkpoint Semantics
--------------------

- Checkpoints are for runtime efficiency and recovery; they are not a substitute
  for source-of-truth raw data.
- When the goal is to validate or rebuild GLB baseline geometry itself, start
  from raw source geometry, not from an existing checkpoint. FEMIC's clean
  user-facing path for that job is ``femic prep glb-build``.
- ``femic prep glb-build`` now also stashes a reusable zipped GLB snapshot into
  the local ``external/femic-public-data`` DataLad repo by default unless the
  caller explicitly disables that behavior. This stash is local only and does
  not auto-commit or auto-publish the public-data submodule.
- If a confirmed-valid stashed GLB already exists for the TSA/VRI combination,
  ``femic prep glb-build`` now reuses that snapshot by default. Use
  ``--force-rebuild-glb`` when you explicitly want to rerun the raw-source clip
  instead of consuming the stored baseline.
- Once the strict THLB ladder reaches the step-5 AFLB milestone, FEMIC now
  treats AFLB as a first-class downstream restart checkpoint.
  ``data/tsr/aflb_checkpoint.feather`` is the canonical restart artifact, and
  ``data/tsr/aflb_checkpoint.gpkg`` is written by default as the GIS-facing
  companion unless the caller explicitly disables it.
- Once the strict THLB ladder reaches the post-step-12 LHLB milestone, FEMIC
  also writes ``data/tsr/lhlb_checkpoint.feather`` as the canonical restart
  artifact and ``data/tsr/lhlb_checkpoint.gpkg`` by default as the GIS-facing
  companion unless the caller explicitly disables it.
- Users who want to experiment only with ``LHLB -> THLB`` logic should prefer
  restarting from ``data/tsr/lhlb_checkpoint.feather`` instead of rebuilding
  the settled upstream ladder.
- Resume behavior must never silently reuse stale artifacts when debug-mode
  constraints (for example ``--debug-rows``) change the effective data population.

Assumptions
-----------

- Stand records represent productive forest land after filtering logic.
- External BC datasets may vary by vintage; field names and join keys must be
  validated explicitly when changing source vintages.
- Raster-overlay logic can be expensive and should be treated as a controlled,
  cache-aware step.

Outputs Consumed by Stage 01a
-----------------------------

- Stand dataframe checkpoints with stratification + species attributes
- VDYP-ready polygon/layer extracts
- Supporting lookup tables for AU assignment and curve linkage

ArcRasterRescue Workflow Contract
---------------------------------

Do not reinvent SiteProd FileGDB extraction. FEMIC expects the existing
patched ArcRasterRescue workflow documented from the original notebook lineage.

- Preferred override: set ``FEMIC_ARC_RASTER_RESCUE_EXE`` to the compiled
  executable path.
- Default legacy configured path remains
  ``../ArcRasterRescue/build/arc_raster_rescue.exe``.
- When running from an instance root, FEMIC now resolves that relative path
  against ``FEMIC_SOURCE_ROOT`` / ``FEMIC_INSTANCE_ROOT`` so the established
  sibling-checkout layout still works.

Linux example (source checkout + sibling ArcRasterRescue checkout):

.. code-block:: bash

   export FEMIC_SOURCE_ROOT=$PWD
   export FEMIC_ARC_RASTER_RESCUE_EXE="$PWD/../ArcRasterRescue/build/arc_raster_rescue.exe"

If ArcRasterRescue is unavailable on Linux, Windows ArcGIS Pro fallback is the
documented alternative runtime boundary.

Primary Legacy Notebook Coverage
--------------------------------

See the traceability matrix page for exact mapping of Stage 00 guidance back to
markdown cells in ``00_data-prep.ipynb``.
