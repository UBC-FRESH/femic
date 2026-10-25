LidarBC Tile Materialization
============================

Purpose
-------

This guide explains P79.2: how FEMIC downloads selected LidarBC tiles into an
explicit managed data root, resumes interrupted transfers, and records an
auditable manifest. It does not compile terrain or canopy products; those are
P79.3 and P79.7.

Large tiles stay out of git. The output root is an instance or external-data
root that can be annexed through the lab's DataLad/Arbutus pattern.

Managed Layout
--------------

.. code-block:: text

   <output-root>/
     materialization.json
     lidarbc/<product>/layer_<layer-id>/<year>/<filename>
     lidarbc/<product>/layer_<layer-id>/<year>/<filename>.part

``materialization.json`` is the auditable control file. ``.part`` files are
resumable partial downloads. Relative paths are stable for a given selection
and source tile.

Plan Or Preflight
-----------------

Write the manifest without downloading any bytes:

.. code-block:: bash

   femic lidar materialize \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --output-root data/lidar \
     --plan-only

The manifest uses schema ``femic.lidar.materialization.v1`` and records every
selected tile with status ``pending``, its source URL, local relative path,
attempt count, and retry fields.

Materialize
-----------

.. code-block:: bash

   femic lidar materialize \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --output-root data/lidar

Useful bounded flags:

- ``--max-tiles N`` processes only the first N tiles in this run.
- ``--timeout-sec SECONDS`` sets the per-tile network timeout.
- ``--fail-fast`` stops after the first failed tile.
- ``--manifest-path PATH`` overrides the default
  ``<output-root>/materialization.json``.

The matching Python entry point is:

.. code-block:: python

   from pathlib import Path
   from femic.lidar.materialization import materialize_lidar_selection

   result = materialize_lidar_selection(
       selection_manifest_path=Path("metadata/lidar/lidarbc_selection.json"),
       output_root=Path("data/lidar"),
   )

Resume Rules
------------

- A verified file is skipped only when its size and SHA-256 still match the
  manifest.
- An existing ``.part`` file resumes with an HTTP ``Range`` request when the
  server returns ``206 Partial Content``.
- If the server ignores ``Range`` and returns ``200``, FEMIC restarts that tile
  from byte zero rather than appending an inconsistent body.
- The manifest is written before a download starts and after every tile, so a
  killed process leaves a resumable state.

Integrity And Completeness
--------------------------

On completion, FEMIC records the local size and ``sha256``. A manifest is
``complete`` only when every tile is ``verified``. Inspect it with:

.. code-block:: bash

   femic lidar materialization-status data/lidar
   femic lidar materialization-status data/lidar --json
   femic lidar materialization-status data/lidar --require-complete

``--require-complete`` exits non-zero when the manifest is structurally valid
but some tiles are pending, partial, or failed. Without it, an incomplete plan
is still reported as valid so it can be used for preflight.

Failure And Retry
-----------------

Tile status is one of ``pending``, ``downloading``, ``partial``, ``verified``,
or ``failed``. Each tile also records:

- ``attempts`` and ``last_attempt_utc``;
- ``last_error``;
- ``resumed_from_bytes``;
- ``expected_size_bytes`` and the observed remote ETag when available.

A failed tile with a non-empty ``.part`` file is left as ``partial``. Rerunning
the same command resumes it. A failed tile without a partial is marked
``failed`` and retried from zero on the next run.

Manifest Changes And Selection Pinning
--------------------------------------

An existing manifest must match the current selection digest and tile set. If
the selection changes, use a new output root or rebuild the manifest. This
prevents a run from silently mixing tiles from different AOIs or catalog
snapshots.

DataLad And Arbutus
-------------------

Use an explicit instance or external-data root. Commit the manifest and small
metadata; annex large tile payloads to the instance's Arbutus remote through
DataLad. Do not create a full-province mirror.

See Also
--------

- :doc:`lidar-data-products`
- :doc:`lidar-product-bundles`
- :doc:`../reference/contracts/lidar-materialization`
- :doc:`../reference/api/femic-lidar-materialization`
- :doc:`github-datalad-arbutus-pattern`
