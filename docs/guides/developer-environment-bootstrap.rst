Developer Environment Bootstrap (Fresh Clone)
=============================================

Purpose
-------

This guide is the canonical bootstrap ritual for contributors and coding
agents working from a FEMIC source checkout.

Use this before running any FEMIC pipeline commands.

Copy-Paste Bootstrap Scripts
----------------------------

Linux/macOS:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip setuptools wheel
   python -m pip install -r requirements-dev.txt
   python -m femic --help
   ruff --version
   mypy --version
   pytest --version
   pre-commit --version
   sphinx-build --version
   git annex version
   datalad --version
   git submodule update --init --recursive
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
   python -m femic --help
   ruff --version
   mypy --version
   pytest --version
   pre-commit --version
   sphinx-build --version
   git annex version
   .venv\Scripts\datalad.exe --version
   git submodule update --init --recursive
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data
   $env:FEMIC_EXTERNAL_DATA_ROOT="$PWD\external\femic-public-data\data"
   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic prep geospatial-preflight

These scripts are the intended fresh-clone baseline for working against the
bundled example instances under ``external/`` in this checkout. If you are
bootstrapping the repo for K3Z or TSA29 maintenance, run one of these blocks
first instead of composing the environment from memory.

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

On Windows, prefer the `.venv`-scoped DataLad executable explicitly if
``datalad`` is not on ``PATH``:

.. code-block:: powershell

   .venv\Scripts\datalad.exe --version
   git -C external/femic-public-data annex enableremote arbutus-s3
   .venv\Scripts\datalad.exe get -r external/femic-public-data/data

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

If you are using the documented Windows local Arbutus auth-file workflow,
``femic prep validate-case`` now catches the most common low-cost failures
before they turn into noisy ``git-annex`` errors:

- quoted values in ``%USERPROFILE%\.config\femic\arbutus.env``;
- missing loaded Arbutus auth vars in the current PowerShell session; and
- inability to see the known Arbutus public-data bucket from the currently
  loaded Windows session.

For the exact maintainer/bootstrap sequence, including execution-policy-safe
loader usage and Arbutus remote publication order, see
``docs/guides/public-data-mirror-runbook.rst``.

Related Guides
--------------

- ``docs/guides/geospatial-runtime-bootstrap.rst``
- ``docs/guides/deployment-instances.rst``
- ``docs/guides/public-data-mirror-runbook.rst``
- ``docs/guides/cross-platform-runtime-smoke.rst``
- ``docs/guides/vscode-coding-agent-onboarding.rst``
