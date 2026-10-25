LidarBC Data-Product Discovery
==============================

Purpose
-------

FEMIC is the upstream producer for open LiDAR data products used by WS4 and
FHOPS. This guide explains the first producer slice: how FEMIC discovers
LidarBC projects and tiles for a bounded area of interest, and how it records
the provenance that later materialization and product packaging rely on.

WS4 P43 and FHOPS P13 are consumers. They pin a FEMIC product manifest instead
of re-implementing LidarBC discovery or tile download.

Ownership Boundary
------------------

FEMIC owns:

- LidarBC source and tile-index contracts.
- AOI selection manifests.
- Resumable materialization (P79.2).
- Native terrain and canopy compilation (P79.3 and P79.7).
- Versioned product packaging and delivery (P79.8).

WS4 and FHOPS own only consumer-side schema, spatial, scenario, and cost
integration. The versioned FEMIC product manifest is the handoff boundary.

Source Catalog
--------------

LidarBC publishes an open tile index through a public ArcGIS feature service.
The source contract records:

- Portal: https://lidar.gov.bc.ca/pages/download-discovery
- Catalogue: https://catalogue.data.gov.bc.ca/dataset/lidarbc-open-lidar-data-portal
- Index item: https://www.arcgis.com/home/item.html?id=5f6a1f31212a4cb2826743d2e52ef02a
- Licence: OGL-BC
- Native CRS: BC Albers, ``EPSG:3005``

The BC Data Catalogue package wrapper records ``Access Only`` because that
record fronts the ArcGIS portal application. The LidarBC portal, the index
item, and the provincial open-data listing identify the data products
themselves as OGL-BC. FEMIC records ``OGL-BC`` as the product licence and keeps
the catalogue caveat in the source descriptor.

Direct Tile Layers
------------------

The feature service exposes these direct-download layers:

======================  ==============================  ==================
FEMIC product           Source layer                    Grid scale
======================  ==============================  ==================
``point_cloud``         LiDAR point cloud index         variable
``dem``                 LiDAR DEM index 1:2,500         1:2500
``dem``                 LiDAR DEM index 1:20,000        1:20000
``dsm``                 LiDAR DSM index 1:2,500         1:2500
``dsm``                 LiDAR DSM index 1:10,000        1:10000
``dsm``                 LiDAR DSM index 1:20,000        1:20000
======================  ==============================  ==================

CHM, canopy structure metrics, and individual-tree products are not separate
layers in this feature service. CHM and canopy metrics are FEMIC-derived
products added in P79.7. Individual-tree products are consumed from LidarBC
where a suitable public product exists.

AOI Selection Contract
----------------------

An AOI is a four-number BC Albers bounding box in
``minx,miny,maxx,maxy`` order. Selection is positive-area intersection:
tiles that only touch the AOI edge are excluded. The discovery helper performs
server-side envelope filtering and repeats the intersection test locally so a
malformed or unfiltered response cannot add unrelated tiles.

The selection manifest records:

- Source descriptor, portal/catalogue URLs, licence, and native CRS.
- AOI bounding box.
- Requested products, including derived-product warnings.
- Every paginated request URL.
- Per-tile identity, download URL, accuracy-report URL, acquisition year,
  projection token, spacing, point density, vertical datum, point classes,
  storage path, grid scale, and geometry bounds.

CLI Usage
---------

.. code-block:: bash

   femic lidar discover \
     --bbox 1148000,391900,1149900,393500 \
     --product point_cloud \
     --product dem \
     --product dsm \
     --manifest-path metadata/lidar/lidarbc_selection.json

Use ``--instance-root PATH`` to resolve the default manifest path under an
instance root. Discovery is metadata-only and does not download tile bytes.

Python Usage
------------

Discovery is metadata-only. It does not download tile bytes.

.. code-block:: python

   from pathlib import Path
   from femic.lidar import discover_lidarbc_tiles, write_lidar_selection_manifest

   selection = discover_lidarbc_tiles(
       (1148000, 391900, 1149900, 393500),
       ("point_cloud", "dem", "dsm"),
   )
   write_lidar_selection_manifest(
       selection,
       Path("metadata/lidar/lidarbc_selection.json"),
   )

The manifest uses schema version ``femic.lidar.selection.v1`` and is JSON with
``schema_version``, ``source``, ``aoi``, ``products``, ``summary``, ``tiles``,
``request_urls``, and ``warnings`` members.

Storage and Dependency Boundaries
---------------------------------

P79.1 discovery stores metadata only. It does not create a provincial mirror
and does not write tile payloads. P79.2 requires an explicit instance or
external-data root before materialization.

Discovery uses the Python standard library. Terrain and canopy processing
dependencies are selected in P79.3 and P79.7, and the product manifest in
P79.8 records the exact processing lineage.

Unsupported Sources
-------------------

This phase does not support private or restricted LiDAR, silent reprojection,
silent resampling, or silent vertical-datum transformation. A source integration
that cannot preserve native resolution, CRS, vertical datum, licence, and
provenance is rejected rather than normalized automatically.

Next Steps
----------

1. P79.8 packages the selection manifest into a versioned product bundle.
2. P79.2 adds resumable materialization under an explicit data root.
3. P79.3 and P79.7 compile terrain and canopy products without silent resampling.
4. P79.9 validates the packaged product with WS4 P43 and FHOPS P13.

See Also
--------

- :doc:`../reference/contracts/lidar-source-and-tile-index`
- :doc:`../reference/api/femic-lidar`
- :doc:`data-access-inventory`
