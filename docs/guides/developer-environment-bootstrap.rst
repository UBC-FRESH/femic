Developer Environment Bootstrap (Fresh Clone)
=============================================

Purpose
-------

This guide is the canonical bootstrap ritual for contributors and coding
agents working from a FEMIC source checkout.

Use this before running any FEMIC pipeline commands.

1) Create and activate a local `.venv`
--------------------------------------

Linux/macOS:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate

Windows PowerShell:

.. code-block:: powershell

   python -m venv .venv
   .venv\Scripts\Activate.ps1

2) Install editable dev dependencies
------------------------------------

.. code-block:: bash

   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt

`requirements-dev.txt` installs `-e .[dev]`, which includes:

- editable FEMIC package install (`python -m femic`, `femic`)
- lint/type/test/docs tooling (`ruff`, `mypy`, `pytest`, `pre-commit`, `sphinx`)
- DataLad tooling (`datalad[full]`)

3) Verify runtime tools are available
-------------------------------------

.. code-block:: bash

   python -m femic --help
   ruff --version
   mypy --version
   pytest --version
   pre-commit --version
   sphinx-build --version
   git annex version
   datalad --version

If `git annex version` fails, install `git-annex` at the OS level and re-open
the shell before continuing.

4) Initialize submodules and materialize annex data
---------------------------------------------------

.. code-block:: bash

   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   datalad get -r external/femic-public-data/data

Do not run FEMIC against `external/femic-public-data` until `datalad get`
completes; symlink pointers alone are not usable input payloads.

5) Export the external data root and run preflight
--------------------------------------------------

Linux/macOS:

.. code-block:: bash

   export FEMIC_EXTERNAL_DATA_ROOT=$PWD/external/femic-public-data/data
   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic prep geospatial-preflight

Windows PowerShell:

.. code-block:: powershell

   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic prep geospatial-preflight

Related Guides
--------------

- ``docs/guides/geospatial-runtime-bootstrap.rst``
- ``docs/guides/public-data-mirror-runbook.rst``
- ``docs/guides/cross-platform-runtime-smoke.rst``
