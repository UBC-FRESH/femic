LidarBC Product Bundles
=======================

Purpose
-------

This guide explains the P79.8 delivery boundary: how FEMIC packages a bounded
LidarBC selection and its compiled products into a versioned bundle that WS4
P43 and FHOPS P13 can consume without re-running discovery or materialization.

The bundle is the producer/consumer contract. Discovery is P79.1; raster and
canopy compilation is P79.3/P79.7. P79.8 only packages already-compiled
artifacts and records their provenance.

Bundle Layout
-------------

A product bundle has this layout:

.. code-block:: text

   <bundle>/
     manifest.json
     provenance/
       selection.json
     products/
       <product>__<index>__<filename>

``manifest.json`` is the consumer entry point. ``provenance/selection.json``
is the canonical P79.1 selection manifest used to build the bundle. Files under
``products/`` are copied artifacts, named by product and plan order so a bundle
is deterministic.

Build From A Selection
----------------------

A product plan describes the artifacts to package. Paths are resolved relative
to the plan file.

.. code-block:: json

   {
     "schema_version": "femic.lidar.product_plan.v1",
     "bundle_version": "2026.10.0",
     "processing_version": "femic-0.2.0a1",
     "processing_lineage": ["femic.lidar.selection.v1"],
     "parameters": {"resampling": "none"},
     "products": [
       {
         "product": "dem",
         "path": "products/dem.asc",
         "media_type": "text/plain",
         "crs": "EPSG:3005",
         "resolution_m": 1.0,
         "vertical_datum": "Canadian Geodetic Vertical Datum of 2013",
         "retrieved_utc": "2026-10-24T00:00:00+00:00",
         "source_tile_ids": ["lidarbc:5:1"],
         "source_layer_ids": [5],
         "derived": false,
         "lineage": ["LidarBC DEM 1:2,500"]
       }
     ]
   }

Build and inspect it:

.. code-block:: bash

   femic lidar bundle \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --product-plan config/lidar/product_plan.json \
     --output-dir data/lidar/products/lidarbc-2026.10.0

   femic lidar inspect data/lidar/products/lidarbc-2026.10.0

Use ``--overwrite`` only when replacing an existing FEMIC LiDAR bundle.
``femic lidar inspect <bundle> --json`` prints the validation report as JSON
and exits non-zero when the bundle is invalid.

The matching Python entry points are:

.. code-block:: python

   from pathlib import Path
   from femic.lidar.products import (
       build_lidar_product_bundle,
       validate_lidar_product_bundle,
   )

   result = build_lidar_product_bundle(
       selection_manifest_path=Path("metadata/lidar/lidarbc_selection.json"),
       product_plan_path=Path("config/lidar/product_plan.json"),
       output_dir=Path("data/lidar/products/lidarbc-2026.10.0"),
   )
   report = validate_lidar_product_bundle(result.bundle_dir)

Manifest Contract
-----------------

The manifest uses schema ``femic.lidar.product.v1`` and layout
``femic.lidar.bundle.v1``. It records:

- ``bundle_id``, ``bundle_name``, ``bundle_version``, and ``created_utc``.
- The FEMIC producer version.
- The full LidarBC source descriptor, including OGL-BC and native CRS.
- The selection digest, AOI, requested products, tile IDs, and source layers.
- The processing version, lineage, and parameters.
- Per-product identity, path, media type, size, SHA-256, CRS, native
  resolution, vertical datum, source retrieval date, source tiles/layers,
  licence, derived flag, and lineage.
- The consumer contract and pin rule.

Every raster product must declare a positive ``resolution_m``. Every product
must use the selection's native CRS and licence. A product that references a
tile outside the selection is rejected.

Reproducibility And Pinning
---------------------------

Rebuilding with the same selection, product plan, product bytes, and
``--generated-utc`` produces the same manifest bytes and ``bundle_id``. The
``bundle_id`` is derived from the selection digest, bundle/processing versions,
and packaged product metadata and checksums.

Consumers pin:

1. ``bundle_id`` and ``bundle_version``;
2. each product ``sha256``; and
3. the recorded CRS, resolution, and vertical datum.

A changed source catalog or processing version produces a new bundle version.
Do not silently rebuild over a pinned bundle.

Validation
----------

``femic lidar inspect`` checks:

- manifest schema and required sections;
- selection provenance digest;
- source licence, source ID, and native CRS;
- product existence, size, and SHA-256;
- product kind, resolution, vertical datum, and derived labelling;
- source-tile membership in the selection;
- consumer-contract fields and manifest summary.

Validation reads metadata and checksums only. It does not parse raster or
point-cloud payloads.

WS4 P43 And FHOPS P13 Consumer Contract
---------------------------------------

WS4 and FHOPS:

- read ``manifest.json`` first and pin a bundle version;
- verify each product checksum before use;
- use the recorded CRS, resolution, and vertical datum;
- select only the products they need (terrain, canopy, or point cloud);
- never re-run LidarBC discovery or materialization;
- never silently reproject or resample a delivered product.

WS4 owns its schema, compiled-dataset, and spatial integration. FHOPS owns its
scenario, operability, and harvest-cost integration. Consumer-side
reprojection, if required, is an explicit consumer decision recorded in the
consumer's own lineage.

Shared TFL 6 Bundle Validation
------------------------------

A shared TFL 6 bundle (`lidarbc-995fb1f771f4d7fe`,
`2026.10.0-tfl6-pilot`) packaged five products: DEM, DSM, slope, CHM, and
canopy. All checksums, sizes, CRS, 1 m resolution, CGVD2013, OGL-BC, source-tile
membership, and canopy schema checks passed.

Bundle slope/CHM values matched the pre-bundle source rasters exactly over seven
shared-AOI VRI polygons. WS4 P52.1 and FHOPS P14.1 consumer contracts were then
run independently against the bundle; both matched each other and the producer
reference exactly (maximum absolute difference `0.0`, tolerance `1e-9`).

See `planning/phase79_p79_9_shared_bundle_validation.md` in the parent FEMIC
repository for the evidence and the consumer pins.

Storage And Delivery
--------------------

Bundle payloads follow the lab's DataLad/Arbutus pattern. Commit the manifest,
selection provenance, and small fixtures to git; annex large product payloads
to the instance dataset's Arbutus remote. Do not create a full-province mirror.

Bounded AOI Fixture
-------------------

The repository includes a public-safe bounded AOI fixture under
``tests/fixtures/lidar``. It packages DEM, DSM, CHM, and canopy artifacts for a
two-tile selection and is used to verify reproducibility, checksums, path
safety, and consumer-contract fields. The canopy artifact is a packaging
fixture; real canopy compilation remains P79.7.

Next Steps
----------

1. P79.2 materializes selected tiles under an explicit DataLad/Arbutus root.
2. P79.3 and P79.7 compile terrain and canopy products for the same selection.
3. P79.9 validates a shared bundle with WS4 P43 and FHOPS P13.

See Also
--------

- :doc:`lidar-data-products`
- :doc:`../reference/contracts/lidar-product-bundle`
- :doc:`../reference/api/femic-lidar-products`
- :doc:`github-datalad-arbutus-pattern`
