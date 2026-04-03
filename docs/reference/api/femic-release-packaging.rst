``femic.release_packaging`` Module
==================================

The :mod:`femic.release_packaging` module owns FEMIC's student-facing release
bundle assembly path. It validates the minimum artifact set, copies bundle,
Patchworks, optional Woodstock, and selected log/manifest outputs into one
versioned release directory, and writes the manifest/handoff-note payloads that
make the package auditable.

If you are debugging why a release package is missing a required artifact, what
strict mode actually enforces, or how FEMIC decides which logs/manifests are
included in the handoff bundle, this is the first module to read. In practice
it owns:

- required release-artifact validation
- versioned release-id and output-directory creation
- package file copying and hashing
- release manifest and handoff-note generation

Start Here If...
----------------

Use this page first if you are trying to:

- build or audit a student-facing release bundle
- understand the contract for required model-input and Patchworks artifacts
- inspect what logs/manifests FEMIC copies into a release package

Typical maintenance path:

1. Start with :func:`build_release_package` for the end-to-end release flow.
2. Inspect :class:`ReleasePackageResult` for the returned package metadata.
3. Read the required-file constants when changing release minimums.

Typical Usage
-------------

The common operator-facing call is:

.. code-block:: bash

   femic export release --instance-root external/femic-k3z-instance --case-id k3z --run-id k3z_docs_example

The matching Python entrypoint is:

.. code-block:: python

   from pathlib import Path
   from femic.release_packaging import build_release_package

   result = build_release_package(
       case_id="k3z",
       output_root=Path("output/releases"),
       model_input_bundle_dir=Path("data/model_input_bundle"),
       patchworks_output_dir=Path("output/patchworks"),
       woodstock_output_dir=Path("output/woodstock"),
       logs_dir=Path("runtime/logs"),
       run_id="docs_example",
       strict=True,
   )

How This Fits Into The Pipeline
-------------------------------

This module sits after pipeline/export work has already finished:

1. FEMIC produces bundle tables, Patchworks outputs, optional Woodstock
   exports, and run logs
2. this module validates/copies the selected artifacts into a versioned release
   directory
3. maintainers review and distribute that release package

That means this module owns the *release-bundle contract*, not the upstream
scientific or export logic itself.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`build_release_package`
- :class:`ReleasePackageResult`

The main minimum-artifact constant is also useful:

- ``REQUIRED_MODEL_INPUT_FILES``

Core Contracts
--------------

The most important runtime contracts in this module are:

- model-input bundle releases require the canonical three bundle CSVs
- Patchworks releases require at least ``forestmodel.xml`` and the fragments
  shapefile
- release IDs combine normalized case ID with an explicit run ID or UTC stamp
- copied files are hashed into a machine-readable manifest
- only selected manifest/log families are copied from the logs directory

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- strict-mode surprises
  strict packaging raises immediately on missing required artifacts instead of
  silently skipping them
- release-directory collisions
  release IDs must be unique or packaging will fail
- partial optional outputs
  Woodstock or logs content may be absent without invalidating the whole
  package, depending on requested strictness and available artifacts

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/model-input-bundle-and-export`
- :doc:`../../guides/rebuild-repro-contract`
- :doc:`../cli`

Related API pages:

- :doc:`femic-pipeline-bundle`
- :doc:`femic-fmg-patchworks`

.. toctree::
   :hidden:

   generated/femic.release_packaging

.. automodule:: femic.release_packaging
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
