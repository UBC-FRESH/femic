LiDAR Source and Tile-Index Contract
====================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC's open LiDAR
discovery slice. Use it when you need to know which source is authoritative,
which fields travel with a tile, how AOI selection behaves, and what P79.1
does not own.

The producer/consumer boundary is the versioned FEMIC product manifest, added
in P79.8. WS4 P43 and FHOPS P13 consume that manifest and do not re-run
discovery or materialization.

Quick Contract
--------------

- Source family: LidarBC Open LiDAR Data Portal.
- Discovery surface: the public ``LiDAR_BC_S3_Public`` ArcGIS feature service.
- Native CRS: BC Albers, ``EPSG:3005``.
- Product licence: OGL-BC.
- Supported direct products: ``point_cloud``, ``dem``, ``dsm``.
- Derived products: ``chm`` and canopy metrics, added in P79.7.
- P79.1 scope: source and tile-index metadata only. No tile bytes, no
  reprojection, no resampling, and no provincial mirror.

Source Families
---------------

.. list-table::
   :header-rows: 1

   * - Field
     - Value
   * - Source ID
     - ``lidarbc``
   * - Portal
     - https://lidar.gov.bc.ca/pages/download-discovery
   * - Catalogue
     - https://catalogue.data.gov.bc.ca/dataset/lidarbc-open-lidar-data-portal
   * - Index item
     - https://www.arcgis.com/home/item.html?id=5f6a1f31212a4cb2826743d2e52ef02a
   * - Licence
     - OGL-BC,
       https://www2.gov.bc.ca/gov/content/data/open-data/open-government-licence-bc
   * - Native CRS
     - ``EPSG:3005``

The catalogue package wrapper records an ``Access Only`` licence because it
fronts the ArcGIS portal application. The data products themselves are
OGL-BC. FEMIC records the product licence and the wrapper caveat separately.

Private or restricted LiDAR is out of scope. A source that cannot preserve
native resolution, CRS, vertical datum, licence, and provenance is not
silently normalized into this contract.

Tile Index Contract
-------------------

The direct layers are:

- ``point_cloud``: LiDAR point cloud index.
- ``dem``: LiDAR DEM indexes at 1:2,500 and 1:20,000.
- ``dsm``: LiDAR DSM indexes at 1:2,500, 1:10,000, and 1:20,000.

Each normalized tile record carries:

- Stable ``source_id:layer_id:object_id`` identity.
- Source filename, BCGS map tile, and storage path.
- Product, source layer, and grid scale.
- Acquisition year, projection token, spacing, and point density.
- Contract, operator name, and operator number.
- Vertical datum, point format, and point classes.
- S3 download URL and accuracy-report URL.
- BC Albers bounding box and indexed tile area.

Null or blank source fields stay null; FEMIC does not invent values for them.
A tile with no usable geometry is rejected.

AOI Selection
-------------

An AOI is ``minx,miny,maxx,maxy`` in ``EPSG:3005``. The contract requires
finite numbers with ``minx < maxx`` and ``miny < maxy``.

Selection is positive-area intersection. Edge-touching tiles are excluded.
Discovery requests an envelope intersection from the feature service and
repeats the intersection test locally before accepting a feature. Pagination
is explicit: every request URL is recorded, and a page-limit overflow is an
error rather than a silent partial selection.

Manifest and Provenance
-----------------------

The selection manifest uses schema version ``femic.lidar.selection.v1``. It
contains:

- ``source``: portal, catalogue, index item, feature service, licence, native
  CRS, supported/derived products, caveat, storage boundary, and notes.
- ``aoi``: bounding box and CRS.
- ``products``: requested products, including derived-product requests.
- ``summary``: tile count and indexed area.
- ``tiles``: normalized provenance records.
- ``request_urls``: every paginated discovery request.
- ``warnings``: derived-product and empty-layer notices.

The manifest is an input to P79.8. It is not yet a delivery product.

Storage and Dependencies
------------------------

P79.1 has no storage payload boundary. Metadata may be written wherever the
caller chooses. Tile bytes require an explicit instance or external-data root
in P79.2, and no full-province mirror is created.

Discovery uses the Python standard library. Processing dependencies for
terrain and canopy products are selected in P79.3 and P79.7.

Unsupported Sources
-------------------

- Private, restricted, or credentialed LiDAR.
- A full provincial mirror.
- Automatic reprojection, resampling, or vertical-datum transformation.
- A new individual-tree segmentation algorithm; FEMIC consumes a suitable
  LidarBC product where one exists.
- WS4 or FHOPS schema/model implementation.

See Also
--------

- :doc:`../../guides/lidar-data-products`
- :doc:`../api/femic-lidar`
- :doc:`instance-and-data-roots`
- :doc:`stage-boundaries-and-canonical-artifacts`
