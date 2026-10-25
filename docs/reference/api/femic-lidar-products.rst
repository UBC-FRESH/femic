``femic.lidar.products`` Module
================================

The :mod:`femic.lidar.products` module owns FEMIC's versioned LiDAR product
bundle. It packages already-compiled artifacts against a P79.1 selection,
records source and processing lineage, writes per-product checksums, and
validates the bundle before delivery to WS4 P43 or FHOPS P13.

Use this page when you are building, inspecting, or debugging a product bundle
rather than the upstream LidarBC discovery contract.

Start Here If...
----------------

Use this page first if you are trying to:

- turn a P79.1 selection and a product plan into a consumer-ready bundle;
- inspect the manifest fields that travel with a terrain or canopy product;
- debug a checksum, CRS, resolution, licence, or lineage validation failure; or
- pin a bundle version for WS4 P43 or FHOPS P13.

Typical Usage
-------------

.. code-block:: bash

   femic lidar bundle \
     --selection-manifest metadata/lidar/lidarbc_selection.json \
     --product-plan config/lidar/product_plan.json \
     --output-dir data/lidar/products/lidarbc-2026.10.0

   femic lidar inspect data/lidar/products/lidarbc-2026.10.0
   femic lidar inspect data/lidar/products/lidarbc-2026.10.0 --json

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

Key Entry Surfaces
------------------

- :func:`load_lidar_product_plan`
  Load and validate a ``femic.lidar.product_plan.v1`` document, resolving
  artifact paths relative to the plan file.
- :func:`build_lidar_product_bundle`
  Copy compiled products into the deterministic bundle layout, compute
  checksums, and write the versioned manifest.
- :func:`validate_lidar_product_bundle`
  Verify manifest structure, selection provenance, checksums, native CRS,
  resolution, licence, and source-tile lineage.
- :class:`LidarProductManifest`
  Consumer-facing manifest with bundle identity, source, selection,
  processing, products, summary, and consumer contract.
- :class:`LidarProductValidation`
  Machine-readable validation report with errors, warnings, and counts.

Cross-References
----------------

- :doc:`../../guides/lidar-product-bundles`
- :doc:`../contracts/lidar-product-bundle`
- :doc:`femic-lidar`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.products

.. automodule:: femic.lidar.products
   :members:
   :undoc-members:
   :show-inheritance:
