LiDAR ground-bundle contract
============================

The optional ground bundle is a sidecar product. FEMIC is the canonical producer through
``femic lidar ground-bundle-build``; the earlier ``fresh-urban-forest-lab`` writer proved the
contract and is legacy. The bundle is independent of FEMIC's default LidarBC product path.

Layout
------

.. code-block:: text

   <bundle>/
     ground.laz
     manifest.json
     qa.json

Schema versions
---------------

- ``manifest.json``: ``femic.ground-bundle.v1``
- ``qa.json``: ``femic.ground-qa.v1``

Ground LAZ dimensions
---------------------

``ground.laz`` is a copy of the input LAZ with these extra dimensions:

- ``is_ground`` — uint8 predicted ground;
- ``hag`` — float32 height above the predicted surface;
- ``is_low`` — uint8 low-point flag;
- ``ref_class`` — uint8 original classification.

Manifest fields
---------------

Required:

- ``schema_version``;
- ``source``: path, SHA-256, CRS, vertical datum, point count;
- ``output``: relative path ``ground.laz``, SHA-256, point count;
- ``parameters`` and ``parameter_sha256``;
- ``method``: name, version, reference, clean-room statement;
- ``qa``: relative path ``qa.json`` and SHA-256;
- ``warnings``.

QA fields
---------

Required:

- ``schema_version``;
- ``point_count``, ``ground_count``, ``low_point_count``;
- ``sor_removed``, ``sor_removed_fraction``;
- ``seed_count``, ``iterations``, ``tin_warning``;
- ``hag_percentiles_m``;
- ``class_counts``, ``predicted_ground_by_class``;
- ``runtime_seconds``, ``parameter_sha256``, ``ground_truth_used``, ``warnings``.

Reader
------

``femic.lidar.ground_bundle.read_ground_bundle`` validates:

- required files and JSON objects;
- schema versions;
- output and QA SHA-256 hashes;
- parameter hash equality;
- source, output, and QA point-count equality;
- required QA fields.

With ``inspect_points=True`` and ``laspy`` installed, it also checks the LAZ point count and
the four required dimensions. Without ``laspy`` it records a warning and skips the LAZ
inspection. ``laspy`` is not a hard FEMIC dependency; install ``femic[lidar]`` to enable
inspection.

The reader never imports ``fresh-urban-forest-lab`` and never changes a default FEMIC
product.

Ground summary
--------------

The optional ``femic lidar ground-summary`` command reads a valid bundle and a polygon layer
with matching CRS. It writes a CSV and ``femic.ground-summary.v1`` manifest.

CSV fields:

- ``polygon_id``;
- ``point_count``, ``ground_count``, ``ground_fraction``;
- ``low_count``, ``low_fraction``;
- ``hag_mean``, ``hag_p50``, ``hag_p95``, ``hag_max``.

The manifest records the bundle schema/parameter/hash pin, polygon layer hash, id field,
feature count, output CSV hash, row count, CRS, warnings, and a statement that HAG statistics
describe the predicted surface, not field-validated ground accuracy.

LAZ crop
--------

``femic lidar crop`` writes ``femic.laz_crop.v1``. It records input/output hashes, input and
output point counts, bbox, source CRS, and warnings. It reads the source in chunks and writes
only in-bbox points. It is a local workflow after one materialization, not a COPC range-read
client.
