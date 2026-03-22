Instance and Data Roots
=======================

Purpose
-------

This page is the source of truth for where FEMIC looks for case files,
generated outputs, and canonical public data.

Instance Root Resolution
------------------------

Operational commands resolve the active instance root in this order:

1. explicit ``--instance-root``
2. ``FEMIC_INSTANCE_ROOT``
3. current working directory

That precedence decides where FEMIC will look for:

- ``config/``
- ``data/``
- ``output/``
- ``vdyp_io/logs/``
- instance-local rebuild specs and runbooks

Interpretation rules:

- Use ``--instance-root`` when you want deterministic behavior from outside the
  instance directory.
- Use ``FEMIC_INSTANCE_ROOT`` only when you intentionally want environment-wide
  defaulting.
- If neither is supplied, FEMIC treats the current working directory as the
  instance root.

Bundled Example Instances
-------------------------

The bundled published example instances in this checkout are:

- ``external/femic-k3z-instance``
- ``external/femic-tsa29-instance``

Treat them as git submodules, not ordinary folders:

- change FEMIC code/docs/tooling in the parent repo
- change case-specific instance content in the submodule repo
- commit submodule changes in the instance repo first, then update the parent
  submodule pointer in FEMIC

External Data Root
------------------

``FEMIC_EXTERNAL_DATA_ROOT`` tells FEMIC where to look for canonical public
data artifacts when they are not present under the active instance root.

Typical value from this checkout:

- Linux/macOS:
  ``$PWD/external/femic-public-data/data``
- Windows PowerShell:
  ``$PWD\external\femic-public-data\data``

At minimum, materialize the mirror before depending on that path:

.. code-block:: bash

   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data

Fallback Behavior To Remember
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Seam
     - Contract
   * - Public-data mirror
     - FEMIC can use canonical mirrored artifacts only if
       ``FEMIC_EXTERNAL_DATA_ROOT`` points at materialized payloads.
   * - THLB raster
     - Prefer instance-local ``data/misc.thlb.tif``; otherwise FEMIC can fall
       back to ``FEMIC_EXTERNAL_DATA_ROOT/misc.thlb.tif``.
   * - SiteProd artifacts
     - Prefer paired canonical ``siteprod.tif`` +
       ``siteprod.bandmap.json`` when available; otherwise FEMIC may fall back
       to the legacy export/stack path.
   * - Legacy runtime assets
     - Isolated ``--instance-root`` runs can still borrow source-checkout
       runtime assets when the documented source-root fallback path is intact.

Common Mistakes
---------------

- Treating ``external/femic-public-data`` pointer files as real payloads before
  ``datalad get``.
- Editing the bundled instance as if it were ordinary parent-repo content.
- Forgetting that a command launched from repo root without ``--instance-root``
  is not the same as a command explicitly pinned to
  ``external/femic-k3z-instance``.
- Assuming ``FEMIC_EXTERNAL_DATA_ROOT`` replaces the instance root; it only
  supplies canonical external data fallback.

See Also
--------

- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/public-data-mirror-runbook`
- :doc:`../api/femic-instance-context`
- :doc:`../api/femic-pipeline-io`
