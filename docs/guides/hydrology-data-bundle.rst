Hydrology Data Bundles
======================

Purpose
-------

P114.2 packages a reviewed hydrology domain into a portable, versioned data
bundle. It records layer paths, licences, checksums, sizes, gaps, and the
source-registry version so later hydrology work does not depend on ad hoc local
downloads.

The bundle uses schema ``femic.hydrology.bundle.v1`` and layout
``layers/<layer_id>/<filename>``. It does not download public layers or run a
hydrology model.

Bundle Layout
-------------

.. code-block:: text

   <bundle>/
     bundle.json
     layers/<layer_id>/<filename>

``bundle.json`` is the audit and handoff surface. Layer payloads are copied
under ``layers/`` and may be DataLad annex objects. Materialize annex pointers
before auditing or using the bundle.

Build From A Domain
-------------------

The bundle is built from a P114.1 domain manifest plus local source files:
BCDC/WFS downloads, reviewed project layers, or DataLad-materialized public
data.

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.bundle import (
       audit_hydrology_bundle,
       build_hydrology_bundle,
   )

   result = build_hydrology_bundle(
       Path("metadata/hydrology/domain.json"),
       Path("data/hydrology/bundle-v1"),
       aoi_bbox_epsg3005=(1148000, 391900, 1149900, 393500),
       sources={
           "watersheds": Path("data/raw/watersheds.gpkg"),
           "streams": Path("data/raw/streams.gpkg"),
           "roads": Path("data/raw/roads.gpkg"),
           "dem": Path("data/raw/dem.tif"),
           "receptors": Path("data/raw/receptors.gpkg"),
       },
   )
   audit = audit_hydrology_bundle(result.bundle_dir)

The build is atomic. Existing output is replaced only when it is an existing
FEMIC hydrology bundle and ``overwrite=True`` is explicit.

Plan And Gaps
-------------

Use planning to audit what is missing before building:

.. code-block:: python

   from femic.hydrology.bundle import plan_hydrology_bundle

   plan = plan_hydrology_bundle(
       domain,
       bundle_dir=Path("data/hydrology/bundle-v1"),
       aoi_bbox_epsg3005=(1148000, 391900, 1149900, 393500),
       sources={"watersheds": Path("data/raw/watersheds.gpkg")},
   )
   for gap in plan.gaps:
       print(gap.layer_id, gap.reason)

A plan with gaps is valid and incomplete. A build refuses to proceed while gaps
remain, so an incomplete bundle cannot be mistaken for a finished input.

Audit
-----

``audit_hydrology_bundle`` checks:

- manifest schema and required layer roles;
- bundle and domain identifiers;
- AOI bounds;
- licence presence;
- layer existence, size, and SHA-256;
- path containment inside the bundle;
- gaps and incomplete state.

A bundle is ``valid`` when its manifest and materialized files are internally
consistent. Each materialized layer records ``checksum_sha256`` and the manifest
records a deterministic ``bundle_id``. It is ``complete`` only when every layer is materialized, every
checksum matches, and no gaps remain.

Public Acquisition
------------------

Acquisition stays outside the bundle builder:

.. code-block:: bash

   femic data bcdc-fetch "WHSE_BASEMAPPING.FWA_WATERSHEDS_POLY" \
     --bbox 1148000,391900,1149900,393500 \
     --download-root data/raw

   femic data bcdc-fetch "WHSE_BASEMAPPING.FWA_STREAM_NETWORKS_SP" \
     --bbox 1148000,391900,1149900,393500 \
     --download-root data/raw

LiDAR DEMs should come from the FEMIC P79 product pipeline where available.
Every source must carry its public licence and provenance.

Pilot Data Audit
----------------

A pilot bundle starts as a plan with no sources. The gap list is the data
audit:

- watershed and stream coverage;
- road and crossing coverage;
- DEM/DSM coverage and resolution;
- gauge availability and period of record;
- receptor and channel-capacity evidence;
- licence and redistribution status.

Do not commit private or restricted layers. No private data belongs in a tracked bundle. The pilot selection is not
committed until the public-data audit is reviewed.

DataLad And Arbutus
-------------------

Commit ``bundle.json`` and small metadata. Annex large layer payloads to the
instance's Arbutus remote. Audit the materialized bundle, not the annex pointer
stubs.

See Also
--------

- :doc:`hydrology-domain-contract`
- :doc:`../reference/contracts/hydrology-data-bundle`
- :doc:`../reference/api/femic-hydrology-bundle`
- :doc:`github-datalad-arbutus-pattern`
