LiDAR ground-bundle reader
==========================

The optional ground bundle is a sidecar product. FEMIC is now the canonical producer; the
earlier ``fresh-urban-forest-lab`` writer proved the same contract and is legacy.

Build a bundle
--------------

.. code-block:: bash

   femic lidar ground-bundle-build data/lidar/crop/tfl6_blocks.laz \
     output/ground/tfl6_blocks \
     --crs EPSG:3156 --vertical-datum CGVD2013

The command writes ``ground.laz``, ``manifest.json``, and ``qa.json`` and is opt-in. Without
``laspy``, install ``femic[lidar]``.

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

Large tiles and local crop
--------------------------

LidarBC LAZ tiles can be much larger than a block AOI. LAZ is not COPC, so an HTTP range
read does not avoid the full download. Acquire the tile once, then crop locally before
running the ground adapter:

.. code-block:: bash

   femic lidar crop \
     --laz data/lidar/bc_092l062_4_1_2.laz \
     --bbox 881700,627500,882700,628500 \
     --out data/lidar/crop/tfl6_blocks.laz

The bbox is in the source CRS. The command writes the cropped LAZ and
``tfl6_blocks.manifest.json`` with input/output hashes, counts, bbox, CRS, and warnings.

Use a COPC source and a bounds-aware reader when one is available. Do not treat this crop as
a range-read client.

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
