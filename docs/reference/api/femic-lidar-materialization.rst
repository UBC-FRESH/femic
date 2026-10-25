``femic.lidar.materialization`` Module
=======================================

The :mod:`femic.lidar.materialization` module owns P79.2 resumable LidarBC tile
materialization. It plans a managed layout, downloads tile bytes into an
explicit root, resumes partial transfers, verifies size and SHA-256, and records
retry state in ``materialization.json``.

Use this page when you are planning, downloading, resuming, or auditing LiDAR
tile payloads rather than compiling products or packaging a consumer bundle.

Start Here If...
----------------

Use this page first if you are trying to:

- write a preflight manifest without downloading tile bytes;
- resume an interrupted LiDAR download;
- inspect why a tile is pending, partial, or failed; or
- verify that a managed materialization root is complete and checksum-clean.

Typical Usage
-------------

.. code-block:: bash

   femic lidar materialize \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --output-root data/lidar \
     --plan-only

   femic lidar materialize \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --output-root data/lidar

   femic lidar materialization-status data/lidar --json --require-complete

The matching Python entry points are:

.. code-block:: python

   from pathlib import Path
   from femic.lidar.materialization import (
       materialize_lidar_selection,
       validate_lidar_materialization,
   )

   result = materialize_lidar_selection(
       selection_manifest_path=Path("metadata/lidar/lidarbc_selection.json"),
       output_root=Path("data/lidar"),
   )
   report = validate_lidar_materialization(result.manifest_path)

Key Entry Surfaces
------------------

- :func:`plan_lidar_materialization`
  Build a pending manifest from a P79.1 selection without writing tile bytes.
- :func:`materialize_lidar_selection`
  Download or resume all selected tiles under an explicit root.
- :func:`validate_lidar_materialization`
  Check manifest structure, paths, sizes, checksums, and completeness.
- :func:`write_lidar_materialization_manifest`
  Persist a manifest atomically.
- :class:`LidarMaterializationManifest`
  Audit surface with source, selection, storage, summary, and per-tile state.
- :class:`LidarMaterializationTile`
  Per-tile source URL, local path, status, checksum, retry, and resume fields.

Cross-References
----------------

- :doc:`../../guides/lidar-materialization`
- :doc:`../contracts/lidar-materialization`
- :doc:`femic-lidar`
- :doc:`femic-lidar-products`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.materialization

.. automodule:: femic.lidar.materialization
   :members:
   :undoc-members:
   :show-inheritance:
