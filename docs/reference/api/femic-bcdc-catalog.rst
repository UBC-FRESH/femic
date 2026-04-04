``femic.bcdc_catalog`` Module
=============================

The :mod:`femic.bcdc_catalog` module owns FEMIC's first BC Data Catalogue
resolver slice. It translates explicit layer names or keywords into ranked
catalogue package matches, classifies the discovered resource surfaces, and can
optionally download only the stable direct-access data resources from the
top-ranked package. It also exposes the WFS/OpenMaps service hints that the
separate :mod:`femic.bcdc_fetch` module uses for AOI-scoped acquisition.

Use this page when you are debugging the BCDC resolution logic itself rather
than the higher-level CLI surface.

Start Here If...
----------------

Use this page first if you are trying to:

- understand how FEMIC queries the public BC Data Catalogue API;
- inspect the exact-vs-keyword fallback lookup logic;
- debug why a resource was classified as direct download, service, indirect
  custom download, or supporting document; or
- inspect how the v1 direct-download helper chooses what to save; or
- inspect the WFS/OpenMaps service hints FEMIC now derives for later AOI-scoped
  fetch automation.

Typical Usage
-------------

The common operator-facing entrypoint is:

.. code-block:: bash

   femic data bcdc-resolve WHSE_FOREST_VEGETATION.F_OWN

The matching Python entrypoints are:

.. code-block:: python

   from pathlib import Path
   from femic.bcdc_catalog import (
       download_direct_bcdc_resources,
       resolve_bcdc_candidates,
       write_bcdc_manifest,
   )

   result = resolve_bcdc_candidates("WHSE_FOREST_VEGETATION.F_OWN")
   download_direct_bcdc_resources(result, destination_root=Path("downloads/bcdc"))
   write_bcdc_manifest(result, Path("runtime/logs/f_own_manifest.json"))

Key Entry Surfaces
------------------

- :func:`resolve_bcdc_candidates`
  Query the public catalogue, probe service-backed resources, and build a
  normalized ranked result.
- :func:`download_direct_bcdc_resources`
  Download only direct-access data resources from the chosen top match.
- :func:`write_bcdc_manifest`
  Persist the resolve/download result as JSON for later promotion/review,
  including any WFS service hints.

Cross-References
----------------

- :doc:`../../guides/bc-data-catalogue-discovery`
- :doc:`../../guides/data-access-inventory`
- :doc:`femic-bcdc-fetch`
- :doc:`femic-bcdc-dwds`
- :doc:`../cli`

.. toctree::
   :hidden:

   generated/femic.bcdc_catalog

.. automodule:: femic.bcdc_catalog
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
