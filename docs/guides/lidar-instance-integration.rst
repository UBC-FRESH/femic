LiDAR Instance Integration
==========================

Purpose
-------

This guide shows how an instance repository uses the FEMIC LiDAR CLI without
copying discovery, materialization, terrain, or packaging helpers into the
instance.

Instance Layout
---------------

The default layout under an instance root is:

.. code-block:: text

   <instance>/
     metadata/lidar/lidarbc_selection.json
     data/lidar/
       materialization.json
       lidarbc/<product>/layer_<id>/<year>/<filename>
       terrain/
         slope_percent.tif
         terrain_qa.json
         terrain_qa.csv
       streams/
         stream_candidates.tif
         flow_accumulation.tif
         stream_candidates_manifest.json
         stream_candidates_review.md
       products/
         <bundle>/
           manifest.json
           provenance/selection.json
           products/

Commit the selection, materialization, QA, review, and product manifests.
Annex large tile, raster, and point-cloud payloads through DataLad to the
instance's Arbutus remote. Do not create a full-province mirror.

Instance Root Resolution
------------------------

The LiDAR commands accept ``--instance-root PATH`` and resolve relative default
paths under it. ``FEMIC_INSTANCE_ROOT`` is also honoured by the shared instance
context.

.. code-block:: bash

   export FEMIC_INSTANCE_ROOT="$PWD"

   femic lidar discover --bbox 1148000,391900,1149900,393500
   femic lidar materialize --selection-manifest metadata/lidar/lidarbc_selection.json
   femic lidar terrain --dem data/lidar/lidarbc/dem/layer_5/2023/dem.tif
   femic lidar streams --dem data/lidar/lidarbc/dem/layer_5/2023/dem.tif
   femic lidar bundle \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --product-plan config/lidar/product_plan.json

Explicit absolute paths still work. The instance root only supplies defaults;
it does not hide the source or output paths from the manifests.

Recommended Workflow
--------------------

1. **Discover** the bounded AOI and review the selection manifest.

   .. code-block:: bash

      femic lidar discover \
        --bbox 1148000,391900,1149900,393500 \
        --manifest-path metadata/lidar/lidarbc_selection.json

2. **Materialize** selected tiles and review the manifest.

   .. code-block:: bash

      femic lidar materialize \
        --selection-manifest metadata/lidar/lidarbc_selection.json \
        --output-root data/lidar

      femic lidar materialization-status data/lidar --require-complete

3. **Build terrain** products and QA.

   .. code-block:: bash

      femic lidar terrain \
        --dem data/lidar/lidarbc/dem/layer_5/2023/dem.tif \
        --output-dir data/lidar/terrain

4. **Derive stream candidates** and review caveats.

   .. code-block:: bash

      femic lidar streams \
        --dem data/lidar/lidarbc/dem/layer_5/2023/dem.tif \
        --output-dir data/lidar/streams \
        --reference data/public/fwa_streams.geojson

5. **Package** the reviewed products for WS4/FHOPS.

   .. code-block:: bash

      femic lidar bundle \
        --selection-manifest metadata/lidar/lidarbc_selection.json \
        --product-plan config/lidar/product_plan.json \
        --output-dir data/lidar/products/lidarbc-2026.10.0

      femic lidar inspect data/lidar/products/lidarbc-2026.10.0 --json

DataLad Boundary
----------------

- Track JSON manifests and small review artifacts in the instance repo.
- Annex large rasters, point clouds, and tile payloads.
- Pin the product ``bundle_id``, ``bundle_version``, and each product
  ``sha256``.
- Do not let an instance edit a delivered product in place; rebuild a new
  bundle version instead.

Instance Handoff Checklist
--------------------------

- [ ] The selection manifest records the AOI and requested products.
- [ ] The materialization manifest is complete and checksum-clean.
- [ ] Terrain QA reports are reviewed.
- [ ] Stream-candidate caveats and comparison metrics are reviewed.
- [ ] The product manifest is pinned for WS4/FHOPS.
- [ ] Large payloads are annex-managed, not committed to git.

See Also
--------

- :doc:`lidar-data-products`
- :doc:`lidar-materialization`
- :doc:`lidar-terrain-products`
- :doc:`lidar-stream-candidates`
- :doc:`lidar-product-bundles`
- :doc:`deployment-instances`
- :doc:`github-datalad-arbutus-pattern`
