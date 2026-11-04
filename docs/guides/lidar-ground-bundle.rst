LiDAR ground-bundle reader
==========================

The optional ground bundle is a sidecar from ``fresh-urban-forest-lab``. FEMIC can validate
and inspect it without changing any default LidarBC product.

Validate a bundle
-----------------

.. code-block:: bash

   femic lidar ground-bundle data/lidar/ground/tile_001

The command prints the schema versions, point count, ground count, low-point count, optional
LAZ dimensions, and warnings. Use ``--json`` for the machine-readable summary.

Skip LAZ inspection
-------------------

.. code-block:: bash

   femic lidar ground-bundle data/lidar/ground/tile_001 --no-inspect-points

This validates the manifest, QA file, counts, parameter hash, and file hashes without opening
the LAZ. It is useful on a machine without ``laspy``.

Install optional inspection
---------------------------

.. code-block:: bash

   python -m pip install -e ".[lidar]"

``laspy[lazrs]`` is optional. Without it, the reader still validates the bundle and records a
warning that point inspection was skipped.

Summarize by polygon
--------------------

.. code-block:: bash

   femic lidar ground-summary data/lidar/ground/tile_001 \
     --polygons blocks.gpkg \
     --id-field block_id \
     --out reports/ground_by_block.csv

Each row reports point count, ground fraction, low-point fraction, and HAG mean/p50/p95/max.
The command writes a sidecar ``ground_by_block.manifest.json``. Point and polygon CRS must
match; there is no silent reprojection.

Python
------

.. code-block:: python

   from pathlib import Path

   from femic.lidar.ground_bundle import read_ground_bundle

   bundle = read_ground_bundle(Path("data/lidar/ground/tile_001"))
   print(bundle.point_count, bundle.ground_count, bundle.low_point_count)
   print(bundle.to_dict())

Limits
------

- The reader validates a sidecar; it does not create one.
- It does not validate ground-classification accuracy.
- It does not change FEMIC's default LidarBC products.
- A missing ``laspy`` skips point inspection, not manifest/QA validation.
