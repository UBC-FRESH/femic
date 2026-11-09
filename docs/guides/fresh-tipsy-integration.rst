fresh-tipsy integration
=======================

``fresh-tipsy`` is the public provenance-first package for BC TIPSY and FAN$IER
table access, growth queries, product recovery, and explicit-input economics.
FEMIC consumes it as an optional dependency. The package owns the tables,
queries, and formulas; FEMIC owns its pipelines, instances, and output schema.

Install
-------

.. code-block:: bash

   python -m pip install -e ".[fresh-tipsy]"

Or:

.. code-block:: bash

   python -m pip install "fresh-tipsy>=0.1.0"

If the package is absent, FEMIC keeps its existing TIPSY path. The integration
is additive.

Adapter call
------------

.. code-block:: python

   from pathlib import Path

   from fresh_tipsy.integrations import query_growth

   result = query_growth(
       Path(catalog_path),
       Path(tipsy_install),
       {
           "species_code": "PLI",
           "site_index": 20,
           "age": 80,
           "pnc": "N",
           "format": "tab",
       },
   )
   payload = result.as_dict()

The payload contains ``status``, ``result``, ``provenance``, ``evidence``,
``warnings``, ``error``, ``fresh_tipsy_version``, and
``data_manifest_sha256``.

Product recovery and economics use the same envelope:

.. code-block:: python

   from fresh_tipsy.integrations import recover_products, run_economics

   product = recover_products(
       Path(catalog_path), Path(tipsy_install), {"species_code": "PLI", "site_index": 20, "age": 80}
   ).as_dict()

   economics = run_economics(
       Path(catalog_path), Path(tipsy_install), scenario_payload
   ).as_dict()

FEMIC should store the package version, manifest hash, provenance, evidence,
and warnings with its output.

Data prerequisites
------------------

- A local TIPSY install exposed as ``TIPSY_INSTALL``.
- A validated ``fresh-tipsy`` catalog manifest.
- Source tables obtained under their own BC licence terms.

Raw TIPSY tables and normalized assets are not redistributed by
``fresh-tipsy``. Rebuild assets from the local licensed install.

Optional test
-------------

.. code-block:: python

   import pytest

   fresh_tipsy = pytest.importorskip("fresh_tipsy")

The test skips cleanly when the optional package is absent. A skip is not a
pass; the release checks live in the ``fresh-tipsy`` repository.

Boundary
--------

- No ``fresh-tipsy`` module is copied into FEMIC.
- Product values are TASS/SYLVER model output, not measured BC field grades.
- Economics is ``reimplemented`` and unvalidated against FAN$IER.
- Missing prices and unavailable checks are explicit gaps.
- The adapter does not claim full TIPSY, FAN$IER, or FEMIC parity.

Known limits
------------

- FAN$IER price/cost tables are not parsed.
- FEMIC TSR and TIPSY custom runtime outputs are unavailable.
- Product aggregate source totals and residue totals are absent.
- Carbon conversion is unavailable.

Links
-----

- Release: https://github.com/UBC-FRESH/fresh-tipsy/releases/tag/v0.1.0
- Release notes: https://github.com/UBC-FRESH/fresh-tipsy/blob/main/RELEASE_NOTES.md
- Known gaps: https://github.com/UBC-FRESH/fresh-tipsy/blob/main/notes/reference/known-gaps.md
