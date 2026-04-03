Repo and Runtime Invariants
===========================

Purpose
-------

This page is the compact source of truth for the invariants that should be
assumed before running or extending FEMIC from this checkout.

Quick Contract
--------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Seam
     - Contract
   * - Canonical repo root
     - Use the active checkout root as the canonical repository root for
       commands, patches, and file references. Prefer repo-relative examples in
       published docs rather than machine-specific absolute paths.
   * - Stale path mentions
     - Treat unexpected stale workspace paths in session or editor metadata as
       stale context only. Do not use them for execution; use the active
       checkout root instead.
   * - Python environment
     - Use a repo-local ``.venv`` and install ``requirements-dev.txt`` before
       FEMIC development or docs work.
   * - Submodules
     - Initialize submodules before relying on bundled example instances or the
       public-data mirror.
   * - Annex-backed public data
     - ``external/femic-public-data`` is not usable until ``git annex`` works,
       the ``arbutus-s3`` remote is enabled, and ``datalad get`` has
       materialized real payloads. For Windows-specific Arbutus bootstrap or
       publication work, the canonical maintainer runbook is
       :doc:`../../guides/public-data-mirror-runbook`.
   * - External data root
     - Export ``FEMIC_EXTERNAL_DATA_ROOT`` before case preflight and pipeline
       runs when using the linked public-data mirror.
   * - Preflight
     - Run ``femic prep validate-case`` and
       ``femic prep geospatial-preflight`` before long workflows. On Windows,
       ``validate-case`` is also the intended low-noise place to catch Arbutus
       auth-format and bucket-visibility failures before users fall into noisy
       ``git-annex`` diagnostics.
   * - External runtime boundaries
     - BatchTIPSY and Patchworks remain external/proprietary runtime seams;
       FEMIC documents and validates those boundaries but does not replace
       those tools.

Fresh-Clone Baseline
--------------------

Linux/macOS:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git annex version
   datalad --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data
   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic prep geospatial-preflight

Windows PowerShell:

.. code-block:: powershell

   python -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt
   git submodule update --init --recursive
   git annex version
   .venv\Scripts\datalad.exe --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data
   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic prep geospatial-preflight

Do Not Assume
-------------

- Do not treat symlinked annex pointers as usable data files before
  ``datalad get`` completes.
- Do not assume quoted values in a local Arbutus env file are harmless; for the
  documented Windows auth-file workflow, quoted ``KEY=VALUE`` lines are an
  input bug, not an accepted variant.
- Do not assume proprietary runtimes are vendored into the repo.
- Do not assume a Windows-only helper is available on Linux, or vice versa.
- Do not assume the current working directory is the intended instance root if
  ``--instance-root`` or ``FEMIC_INSTANCE_ROOT`` has been supplied.

See Also
--------

- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/public-data-mirror-runbook`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../api/femic-instance-context`
- :doc:`../api/femic-pipeline-io`
