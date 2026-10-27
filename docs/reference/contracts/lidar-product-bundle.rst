LiDAR Product Bundle Contract
=============================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's versioned LiDAR
product bundle. It is the delivery boundary between FEMIC P79 and the consumer
phases WS4 P43 and FHOPS P13.

Use it when you need to know the bundle layout, the manifest fields that must
travel with a product, how versions are pinned, and what validation is
guaranteed before a bundle is handed to a consumer.

Quick Contract
--------------

- Manifest schema: ``femic.lidar.product.v1``.
- Bundle layout version: ``femic.lidar.bundle.v1``.
- Product plan schema: ``femic.lidar.product_plan.v1``.
- Source: LidarBC, native CRS ``EPSG:3005``, licence OGL-BC.
- Consumer phases: WS4 P43 and FHOPS P13.
- Pin rule: pin ``bundle_id`` and ``bundle_version``, then verify each product
  ``sha256``.
- P79.8 packages compiled products only. It does not compile rasters or
  download source tiles.

Bundle Layout
-------------

.. code-block:: text

   <bundle>/
     manifest.json
     provenance/selection.json
     products/<product>__<index>__<filename>

``manifest.json`` is the only consumer entry point. ``provenance/selection.json``
is the canonical P79.1 selection used to build the bundle. Product files are
copied under ``products/`` with a deterministic product/index prefix.

Manifest Schema
---------------

Top-level manifest fields:

- ``schema_version``, ``layout_version``.
- ``bundle_id``, ``bundle_name``, ``bundle_version``, ``created_utc``.
- ``producer``: FEMIC tool name and version.
- ``source``: the full LidarBC source descriptor from the selection.
- ``selection``: selection schema, digest, AOI, requested products, tile IDs,
  source layers, and tile count.
- ``processing``: processing version, lineage, and parameters.
- ``summary``: product count and total bytes.
- ``products``: per-artifact records.
- ``consumer_contract``: read order, pin rule, native-resolution rule, and
  consumer phases.

Each product record carries:

- ``product_id`` and ``product`` kind.
- ``relative_path``, ``media_type``, ``size_bytes``, and ``sha256``.
- ``crs``, ``resolution_m``, ``vertical_datum``, and ``retrieved_utc``.
- ``source_tile_ids`` and ``source_layer_ids``.
- ``licence_id``, ``derived``, and ``lineage``.

Raster products must declare a positive ``resolution_m`` and use the selection's
native CRS. Point-cloud products may carry their source UTM CRS, which is
recorded per product; they are never silently reprojected. All products use the
selection's licence and may only reference tiles inside the selection.

Versioning And Pinning
----------------------

The ``bundle_id`` is deterministic from:

- the selection digest;
- the bundle and processing versions;
- each packaged product's kind, path, checksum, CRS, resolution, vertical
  datum, retrieval date, source tiles/layers, derived flag, and lineage.

Rebuilding with the same inputs and a fixed ``created_utc`` produces identical
manifest bytes. A changed source catalog, product byte, or processing version
produces a new bundle. Consumers must not silently replace a pinned bundle.

Validation Rules
----------------

``validate_lidar_product_bundle`` checks:

- manifest schema, layout version, bundle identity, and consumer contract;
- selection provenance digest;
- source ID, licence, and native CRS;
- product existence, size, and SHA-256;
- product kind, raster resolution, vertical datum, and derived labelling;
- source-tile membership;
- manifest summary consistency.

Validation is metadata and checksum validation only. It does not parse raster
or point-cloud payloads.

Consumer Contract
-----------------

WS4 P43 and FHOPS P13:

- read ``manifest.json`` before any product file;
- pin ``bundle_id`` and ``bundle_version``;
- verify every product ``sha256``;
- honor the recorded CRS, native resolution, and vertical datum;
- never re-run discovery or materialization;
- never silently reproject or resample a delivered product.

WS4 owns schema, compiled-dataset, and spatial integration. FHOPS owns
scenario, operability, and harvest-cost integration. Consumer-side
reprojection, if needed, is an explicit consumer decision with its own
lineage.

Storage And Delivery
--------------------

Commit manifest and selection provenance to the instance dataset. Annex large
product payloads to the instance's Arbutus remote through DataLad. Do not
create a full-province mirror.

The bounded AOI fixture under ``tests/fixtures/lidar`` is the public-safe
reproducibility fixture. Its canopy artifact is a packaging fixture; real
canopy compilation remains P79.7.

See Also
--------

- :doc:`../../guides/lidar-product-bundles`
- :doc:`lidar-source-and-tile-index`
- :doc:`../api/femic-lidar-products`
- :doc:`instance-and-data-roots`
