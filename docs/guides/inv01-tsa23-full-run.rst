INV-01 TSA 23 Full Run
======================

This guide reproduces the TSA 23 point-cloud feature run used for the INV-01
pilot.  It is a research runbook, not an operational scheduler.

Architecture
------------

Sockeye compute nodes have no public internet.  Public LidarBC point clouds are
downloaded to Sockeye scratch, processed there, and archived to Chinook through
Globus.  The compute phase reads scratch, not Chinook S3.

.. code-block:: text

   LidarBC HTTPS
     -> Sockeye scratch raw/laz + raw/dem
     -> per-batch Parquet parts
     -> local reduce + model cards
     -> GeoTIFF / inventory table

   Chinook (Globus):
     inv01/raw/laz
     inv01/raw/dem
     inv01/parts2
     inv01/products

Runbook
-------

The executable examples are in
``examples/inv01_tsa23_full``:

- ``build_manifest.py`` pairs LidarBC point-cloud and 1 m DEM tiles.
- ``split_manifest.py`` creates download shards and 64-tile batches.
- ``download_tiles.py`` downloads and resumes tiles.
- ``process_batch.py`` derives first-return metrics on the global grid.
- ``compute_batches.sbatch`` runs the batch array.
- ``reduce_full.py`` clips to the TSA boundary, applies the IDF cards, and
  optionally writes the 25 m GeoTIFF.

Build the manifest:

.. code-block:: bash

   python examples/inv01_tsa23_full/build_manifest.py \
     --selection lidarbc_selection_full.json \
     --boundary tsa23_boundary.gpkg \
     --output tile_manifest_full.csv

Split it:

.. code-block:: bash

   python examples/inv01_tsa23_full/split_manifest.py \
     --manifest tile_manifest_full.csv \
     --download-shards 2 \
     --batch-size 64 \
     --output-dir "$INV01_ROOT/manifests"

Download:

.. code-block:: bash

   python examples/inv01_tsa23_full/download_tiles.py \
     "$INV01_ROOT/manifests/download_a.csv" \
     "$INV01_ROOT/raw/laz" "$INV01_ROOT/raw/dem" 8

Process batches after setting ``INV01_ROOT``, ``PYTHON``, ``FEMIC_SRC``, and
``RUNBOOK_DIR``:

.. code-block:: bash

   export INV01_ROOT=/scratch/st-gep-1/gep/inv01
   export PYTHON=/arc/project/st-gep-1/gep/venv-inv01-312/bin/python
   export FEMIC_SRC=/arc/project/st-gep-1/gep/inv01/femic-src/src
   export RUNBOOK_DIR=$PWD/examples/inv01_tsa23_full
   cd "$INV01_ROOT"
   sbatch "$RUNBOOK_DIR/compute_batches.sbatch"

The global 25 m grid used for this run is in UTM zone 10N:

- origin ``(549275, 5784675)``
- cell size ``25 m``
- minimum ``10`` above-2 m first returns
- minimum cover ``10%``

Reduce locally:

.. code-block:: bash

   python examples/inv01_tsa23_full/reduce_full.py \
     --parts /srv/shared-data/gep/ws4/tmp/inv01-data/full-output/parts \
     --boundary tsa23_boundary.gpkg \
     --models config/inventory/models \
     --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/full-output \
     --raster

Results and limits
------------------

The 2026-10-30 run produced:

- 5,899 point-cloud/DEM tile pairs
- 93 batches
- 9,523,476 TSA-clipped cells
- 6,573,196 height cells
- 2,942,755 BA/volume cells
- mean height 16.09 m, BA 23.87 m2/ha, volume 139.33 m3/ha

Coverage was 64% of TSA 23 by tile footprint and 48% by modelled cell area.
907 point-cloud tiles had no matching 1 m DEM; 24 tiles had no usable first
returns.  The model cards are the 14-plot IDF pilot cards, not an operational
inventory.  No independent P48/P49 validation was available.

The detailed evidence, timings, hashes, and provenance are in
``notes/reports/inv01-tsa23-full-mosaic.md``.

See Also
--------

- :doc:`lidar-inventory`
- :doc:`../reference/contracts/inventory-als`
- :doc:`../reference/api/femic-lidar-inventory`
- :doc:`inv01-tsa23-validation`
