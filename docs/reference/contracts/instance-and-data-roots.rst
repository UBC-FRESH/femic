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
- ``runtime/logs/`` for non-VDYP manifests and rebuild reports
- ``vdyp_io/logs/`` for VDYP-specific event/stdout logs
- ``vdyp_io/scratch/`` for disposable raw VDYP batch files
- instance-local rebuild specs and runbooks

Interpretation rules:

- Use ``--instance-root`` when you want deterministic behavior from outside the
  instance directory.
- Use ``FEMIC_INSTANCE_ROOT`` only when you intentionally want environment-wide
  defaulting.
- If neither is supplied, FEMIC treats the current working directory as the
  instance root.

Packaged Install User Roots
---------------------------

Packaged installs now carry a separate user-config contract for:

- managed built-in instance installs; and
- the visible user workspace root used by ``femic instance init --instance-name``.

That config lives at:

- Linux/macOS: ``~/.femic/user.yaml``
- Windows: ``%USERPROFILE%\.femic\user.yaml``

Recorded keys:

- ``paths.managed_external_root``
- ``paths.user_instance_root``

Default values:

- Linux/macOS:
  - managed built-ins: ``~/.femic/external``
  - visible user instances: ``~/femic/instances``
- Windows:
  - managed built-ins: ``%USERPROFILE%\.femic\external``
  - visible user instances: ``%USERPROFILE%\femic\instances``

Important boundary:

- these roots support packaged-install bootstrap and built-in instance
  discovery;
- they do **not** change the normal runtime precedence for operational
  commands, which remains
  ``--instance-root`` -> ``FEMIC_INSTANCE_ROOT`` -> current working directory.

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

VDYP runtime duplication rule:

- the FEMIC source tree can act as the canonical shared source for
  ``vdyp_io/VDYP.INI`` and ``vdyp_io/VDYP_CFG/**`` during normal source-checkout
  development;
- instance-local copies are still valid when a built-in or published instance
  is intentionally being made more self-contained;
- do not duplicate those assets casually across every instance without saying
  which copy is authoritative for maintenance.

Built-in packaged-install resolution now prefers:

1. repo-local ``external/...`` when present in a source checkout;
2. otherwise the configured managed built-in root from ``user.yaml``.

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

FMU Naming Policy
-----------------

FEMIC now prefers **FMU-first conceptual terminology** when describing generic
forest management units.

Compatibility note:

- several current runtime/schema/file seams still use legacy ``tsa`` naming
  and remain valid compatibility contracts:
  ``femic tsa``, ``--tsa``, ``selection.tsa``, ``tsa*.yaml``,
  ``FEMIC_TSA_LIST``, ``vdyp_prep-tsa*.pkl``, and
  ``vdyp_curves_smooth-tsa*.feather``
- those names remain valid compatibility contracts and are not being renamed in
  the current terminology sweep

For new generic examples and future built-ins, prefer the naming pattern:

- ``fmu-<flavour>-<identifier>``

Examples:

- ``fmu-tsa-29``
- ``fmu-cfa-k3z``
- ``fmu-tfl-26``
- ``fmu-ubc-mkrf``

This is guidance for future naming surfaces, not a migration of current
shipped IDs.

See Also
--------

- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/public-data-mirror-runbook`
- :doc:`../api/femic-instance-context`
- :doc:`../api/femic-pipeline-io`
