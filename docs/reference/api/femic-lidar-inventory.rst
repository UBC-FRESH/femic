``femic.lidar.inventory`` Module
================================

The :mod:`femic.lidar.inventory` module applies a pinned area-based inventory
model card to a FEMIC LiDAR product bundle and writes the long
``inventory.als`` table.  It is a consumer seam: it does not fit ABA models or
invent coefficients.

Key Entry Surfaces
------------------

- :class:`InventoryAlsModel`
  Validated model card with coefficients, RMSE, training scope, and ranges.
- :func:`load_inventory_als_model`
  Load and validate a JSON model card.
- :func:`build_inventory_als`
  Apply the model to the bundle's ``canopy`` table and optionally validate
  against a plot table.
- :func:`write_inventory_als`
  Write ``inventory_als.csv`` and ``inventory_als.json``.
- :class:`InventoryAlsResult`
  Bundle/model provenance, long rows, warnings, and caveats.

Cross-References
----------------

- :doc:`../contracts/inventory-als`
- :doc:`../../guides/lidar-inventory`
- :doc:`../contracts/lidar-product-bundle`

.. automodule:: femic.lidar.inventory
   :members:
   :undoc-members:
   :show-inheritance:
