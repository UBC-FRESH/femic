LiDAR Materialization Contract
==============================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's resumable LidarBC
tile materialization. It defines the managed layout, manifest fields, resume
rules, integrity checks, retry state, and storage boundary for P79.2.

Quick Contract
--------------

- Manifest schema: ``femic.lidar.materialization.v1``.
- Default manifest: ``<output-root>/materialization.json``.
- Source: LidarBC, native CRS ``EPSG:3005``, licence OGL-BC.
- Output root: explicit instance or external-data root.
- Partial suffix: ``.part``.
- Status values: ``pending``, ``downloading``, ``partial``, ``verified``,
  ``failed``.
- Large tile payloads stay out of git.

Managed Layout
--------------

.. code-block:: text

   <output-root>/
     materialization.json
     lidarbc/<product>/layer_<layer-id>/<year>/<filename>
     lidarbc/<product>/layer_<layer-id>/<year>/<filename>.part

Relative paths are deterministic for a selection tile. The manifest never
stores the absolute output root, so it remains portable between checkout
locations and DataLad consumers.

Manifest Schema
---------------

Top-level fields:

- ``schema_version``, ``generated_utc``, ``updated_utc``.
- ``source``: full LidarBC source descriptor.
- ``selection``: selection schema, digest, generation time, products, AOI, and
  tile count.
- ``storage``: relative layout, manifest name, partial suffix, and root scope.
- ``summary``: tile, verified, pending, partial, failed, downloading, byte, and
  completeness counts.
- ``tiles``: per-tile records.

Each tile record carries:

- ``tile_id``, ``product``, ``layer_id``, ``filename``, ``download_url``, and
  ``relative_path``.
- ``status``, ``attempts``, ``last_attempt_utc``, and ``last_error``.
- ``expected_size_bytes``, ``size_bytes``, ``sha256``, and ``remote_etag``.
- ``resumed_from_bytes``.

Resume Rules
------------

- Verified files are skipped only when size and SHA-256 match the manifest.
- A partial file resumes with ``Range: bytes=<offset>-`` when the server
  returns ``206 Partial Content``.
- A ``200`` response to a ranged request restarts the tile from zero.
- The manifest is persisted before a download and after every completed or
  failed tile.

Integrity And Completeness
--------------------------

A tile becomes ``verified`` only after the local file is finalized, its size is
recorded, and its SHA-256 is computed. If an expected remote size is known and
does not match, the tile is marked ``failed``.

A manifest is complete only when every tile is ``verified``. Validation also
checks that verified files exist, sizes match, checksums match, and relative
paths stay inside the output root. Validation does not parse tile payloads.

Failure And Retry
-----------------

- A failed transfer with a non-empty ``.part`` file is ``partial`` and resumes
  on the next run.
- A failed transfer without a partial is ``failed`` and restarts from zero.
- ``attempts`` and ``last_attempt_utc`` are incremented per attempt.
- ``last_error`` is truncated to a short operator-readable message.

Selection Pinning
-----------------

An existing manifest must match the selection digest and tile set. A changed
selection requires a new output root or a rebuilt manifest. FEMIC does not
merge tiles from different AOIs or catalog snapshots into one manifest.

Storage Boundary
----------------

The output root is explicit. Commit the manifest and small metadata; annex
large tile payloads through DataLad to the instance's Arbutus remote. No
full-province mirror is created.

See Also
--------

- :doc:`../../guides/lidar-materialization`
- :doc:`lidar-source-and-tile-index`
- :doc:`../api/femic-lidar-materialization`
- :doc:`instance-and-data-roots`
