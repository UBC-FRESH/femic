``femic.hydrology.response_bundle`` Module
===========================================

The :mod:`femic.hydrology.response_bundle` module owns P114.8 response and
flood-risk packaging. It builds deterministic consumer bundles, validates
manifest structure, audits artifact checksums, and exposes the pinned read
handshake for WS4 and FHOPS.

Use this page when you are packaging hydrology outputs or consuming a pinned
bundle without re-running FEMIC.

Start Here If...
----------------

Use this page first if you are trying to:

- build a versioned response bundle from a reproducible plan;
- create a receptor-level flood-risk table;
- inspect a bundle manifest and verify checksums;
- understand required artifact roles; or
- implement the WS4/FHOPS consumer read order.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.response_bundle import (
       audit_hydrology_response_bundle,
       build_hydrology_response_bundle,
       load_hydrology_response_manifest,
   )

   result = build_hydrology_response_bundle(
       Path("fixtures/response_plan.json"),
       Path("runtime/hydrology/response-bundles/2026.10.0"),
   )
   manifest = load_hydrology_response_manifest(result.manifest_path)
   audit = audit_hydrology_response_bundle(result.bundle_dir)
   assert audit.is_valid
   print(manifest.bundle_id, manifest.applicability_domain)

Key Entry Surfaces
------------------

- :func:`build_hydrology_response_bundle`
  Materialize artifacts, write checksums, and emit the manifest.
- :func:`audit_hydrology_response_bundle`
  Validate the manifest and verify local artifact sizes and checksums.
- :func:`validate_hydrology_response_bundle`
  Validate manifest structure and the consumer contract.
- :func:`load_hydrology_response_plan`
- :func:`write_hydrology_response_plan`
  Read and write build plans.
- :func:`load_hydrology_response_manifest`
  Load a consumer manifest.
- :func:`build_flood_risk_table`
- :func:`write_flood_risk_table`
- :func:`read_flood_risk_table`
  Build and persist receptor-level flood-risk rows.
- :class:`FloodRiskRow`
- :class:`FloodRiskTable`
  Flood-risk row and table contracts.
- :class:`HydrologyResponsePlan`
- :class:`HydrologyResponseManifest`
  Build-plan and consumer-manifest contracts.

Cross-References
----------------

- :doc:`../../guides/hydrology-response-bundles`
- :doc:`../contracts/hydrology-response-bundles`
- :doc:`femic-hydrology-flood`
- :doc:`femic-hydrology-surrogate`

.. toctree::
   :hidden:

   generated/femic.hydrology.response_bundle

.. automodule:: femic.hydrology.response_bundle
   :members:
   :undoc-members:
   :show-inheritance:
