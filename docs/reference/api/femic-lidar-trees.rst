``femic.lidar.trees`` Module
=============================

The :mod:`femic.lidar.trees` module owns optional individual-tree product
ingestion and block summaries. It consumes existing point products; it does not
implement a new segmentation algorithm.

Start Here If...
----------------

Use this page first if you are trying to:

- inspect an existing individual-tree point product;
- check duplicate tree IDs or missing heights;
- summarize tree counts and heights by block; or
- decide whether a source tree product is complete enough to use.

Typical Usage
-------------

.. code-block:: bash

   femic lidar trees \
     --product data/lidar/trees/lidarbc_trees.gpkg \
     --output-dir data/lidar/trees

   femic lidar trees \
     --product data/lidar/trees/lidarbc_trees.gpkg \
     --blocks data/input/blocks.gpkg \
     --block-id-field block_id

.. code-block:: python

   from pathlib import Path
   from femic.lidar.trees import (
       inspect_individual_tree_product,
       summarize_individual_trees_by_block,
   )

   summary = inspect_individual_tree_product(
       Path("data/lidar/trees/lidarbc_trees.gpkg")
   )
   blocks = summarize_individual_trees_by_block(
       Path("data/lidar/trees/lidarbc_trees.gpkg"),
       Path("data/input/blocks.gpkg"),
   )

Key Entry Surfaces
------------------

- :func:`inspect_individual_tree_product`
  Validate point geometry, required fields, duplicates, missing heights, and
  distributions.
- :func:`summarize_individual_trees_by_block`
  Join points to blocks on matching CRS and summarize counts/heights.
- :func:`write_individual_tree_summary`
  Persist the product summary as JSON.
- :func:`write_tree_block_summary_csv`
  Persist block summaries as CSV.

Cross-References
----------------

- :doc:`../../guides/lidar-canopy-products`
- :doc:`../contracts/lidar-canopy-products`
- :doc:`femic-lidar-canopy`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.lidar.trees

.. automodule:: femic.lidar.trees
   :members:
   :undoc-members:
   :show-inheritance:
