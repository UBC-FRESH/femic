Hydrology Domain And Receptor Contract
======================================

Purpose
-------

P114.1 defines the public spatial domain that later forest-hydrology and
flood-risk work uses. It records watersheds, stream networks, roads, DEMs,
land cover, soils, climate, hydrometric gauges, downstream receptors, HRUs, and
provenance in one versioned manifest.

This is a data contract only. It does not download layers or run a hydrology
model.

Domain Manifest
---------------

The manifest uses schema ``femic.hydrology.domain.v1`` and the source
registry uses ``femic.hydrology.sources.v1``. It records:

- domain identity, creation time, CRS, and resolution;
- layer roles, paths, formats, CRS, geometry, source IDs, licence, checksums,
  sizes, and optional resolution;
- watershed records linked to a watershed layer;
- downstream receptors linked to a watershed and receptor layer;
- hydrometric gauges linked to a watershed and optional gauge layer;
- caveats and provenance, including the source-registry version.

Required layer roles are:

- ``watershed``
- ``stream``
- ``road``
- ``dem``

A domain must contain at least one watershed and at least one receptor. A gauge
is strongly recommended but optional; a domain without one is valid with a
calibration warning.

Source Registry
---------------

The default public registry covers:

- Freshwater Atlas watersheds and streams;
- Digital Road Atlas and forest-tenure road sections;
- LidarBC DEM/DSM products;
- VRI land cover;
- BC soil landscapes;
- PCIC climate data;
- Water Survey of Canada gauges;
- a reviewed receptor inventory.

Each source records a role, catalogue/service URL where available, licence,
native CRS, required fields, and notes. Climate, soil, gauge, and receptor
sources may require a reviewed local layer before use.

Python Usage
------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.domain import (
       HydrologyGauge,
       HydrologyLayerSpec,
       HydrologyReceptor,
       HydrologyWatershed,
       audit_hydrology_domain,
       build_hydrology_domain,
       write_hydrology_domain_manifest,
   )

   layers = (
       HydrologyLayerSpec(
           layer_id="watersheds",
           role="watershed",
           path="data/hydrology/watersheds.gpkg",
           format="gpkg",
           crs="EPSG:3005",
           source_id="fwa_watersheds",
       ),
       HydrologyLayerSpec(
           layer_id="streams",
           role="stream",
           path="data/hydrology/streams.gpkg",
           format="gpkg",
           crs="EPSG:3005",
           source_id="fwa_streams",
       ),
       HydrologyLayerSpec(
           layer_id="roads",
           role="road",
           path="data/hydrology/roads.gpkg",
           format="gpkg",
           crs="EPSG:3005",
           source_id="road_atlas",
       ),
       HydrologyLayerSpec(
           layer_id="dem",
           role="dem",
           path="data/hydrology/dem.tif",
           format="tif",
           crs="EPSG:3005",
           source_id="lidarbc_dem",
       ),
       HydrologyLayerSpec(
           layer_id="receptors",
           role="receptor",
           path="data/hydrology/receptors.gpkg",
           format="gpkg",
           crs="EPSG:3005",
           source_id="receptor_inventory",
       ),
   )

   domain = build_hydrology_domain(
       domain_id="example-watershed",
       name="Example public watershed",
       layers=layers,
       watersheds=(
           HydrologyWatershed("ws1", "Example Creek", 42.0, "watersheds"),
       ),
       receptors=(
           HydrologyReceptor(
               "r1",
               "Downstream community",
               "community",
               "ws1",
               "receptors",
               capacity_m3s=120.0,
           ),
       ),
       gauges=(
           HydrologyGauge("g1", "Example Creek gauge", "ws1"),
       ),
   )
   write_hydrology_domain_manifest(
       domain,
       Path("metadata/hydrology/domain.json"),
   )

   audit = audit_hydrology_domain(
       Path("metadata/hydrology/domain.json"),
       data_root=Path("."),
   )

Audit
-----

The local audit checks:

- structural validation and cross-references;
- layer file existence;
- declared size;
- optional SHA-256 checksums;
- relative path resolution against the declared data root;
- missing gauges as a warning, not an error.

The audit does not inspect every geospatial field. Field-level validation
belongs to P114.2 when the public data bundle is assembled.

Public-Data Boundary
--------------------

- Use public or reviewed sources only. No private data in tracked files.
- Record licence, source URL, and checksum for every layer.
- Keep relative layer paths portable.
- Do not add private, Indigenous, or licence-restricted data to tracked files.
- Do not create a provincial mirror.

See Also
--------

- :doc:`../reference/contracts/hydrology-domain`
- :doc:`../reference/api/femic-hydrology-domain`
- :doc:`deployment-instances`
- :doc:`data-access-inventory`
