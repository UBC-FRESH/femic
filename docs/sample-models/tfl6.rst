TFL 6 Teaching Instance (Pointer)
=================================

Purpose
-------

FEMIC keeps this page as a short pointer for the TFL 6 teaching instance. The
canonical student-facing and maintainer-facing documentation lives in the
standalone TFL 6 instance repository.

Current Status
--------------

The TFL 6 instance has completed Phase 3 model-design assumptions and is ready
for Phase 4 model-input bundle work after the normal feature-branch lifecycle
is complete. Phase 3 did not build a Patchworks runtime package.

Canonical Student Docs
----------------------

- Public repository: ``https://github.com/UBC-FRESH/femic-tfl6-instance``
- Linked submodule path in FEMIC: ``external/femic-tfl6-instance``
- Standalone docs root:
  ``external/femic-tfl6-instance/docs/index.rst``
- Instance roadmap:
  ``external/femic-tfl6-instance/ROADMAP.md``

Use the standalone docs as source of truth for:

- Phase 2 THLB netdown design, validation, and reproducibility evidence;
- Phase 3 static AU definitions and TFL 6 yield-curve surfaces;
- MP10 TIPSY parameter extraction and crosswalk rationale;
- base treatment-option, harvesting-system, and transition contracts;
- cedar-signal and NICF embedded-identity scenario design; and
- student-facing teaching challenges.

Standalone TFL 6 Coverage Map
-----------------------------

The currently published standalone docs set is organized around:

- ``phase2-thlb-netdown``: THLB netdown steps, fallback assumptions, and the
  accepted validation gap against the scaled MP10 benchmark;
- ``phase3-au-yield-curves``: static AU identity, top-N stratum selection,
  VDYP first-growth curves, MP10 TIPSY parameter library, treated-curve
  handoff, and plot galleries;
- ``phase3-cedar-nicf-expansion``: cedar-signal and NICF identity contracts,
  including the boundary that expansion candidates come from proximal public
  forest outside the TFL 6 AOI;
- ``phase3-model-input-contract``: Phase 4 field-family and artifact handoff
  requirements; and
- ``teaching-challenges``: advanced student exercises such as replacing
  aspatial RMZ fallback logic with geometry-backed spatial overlays.

Submodule Sync Commands
-----------------------

From the FEMIC workspace top-level directory:

.. code-block:: bash

   git submodule update --init --recursive
   git submodule update --remote external/femic-tfl6-instance

FEMIC-Local Integration Notes
-----------------------------

- TFL 6 instance runtime root in this repository:
  ``external/femic-tfl6-instance``
- Active run profile:
  ``external/femic-tfl6-instance/config/run_profile.tfl6.yaml``
- TIPSY configuration:
  ``external/femic-tfl6-instance/config/tipsy/tfl6.yaml``
- Phase 3 AU and curve documentation:
  ``external/femic-tfl6-instance/docs/phase3-au-yield-curves.rst``
- Phase 3 model-input contract:
  ``external/femic-tfl6-instance/docs/phase3-model-input-contract.rst``

Publication Boundary
--------------------

This parent FEMIC page is intentionally a pointer page. It makes the TFL 6
instance discoverable from the published FEMIC documentation, while the
standalone instance repository remains the source of truth for detailed
figures, planning notes, run profiles, and future runtime-package evidence.
