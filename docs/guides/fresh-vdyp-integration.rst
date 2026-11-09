fresh-vdyp integration
======================

`fresh-vdyp` is the public package for the BC VDYP7 bundle catalog, console
runner, typed curve API, and validated Python equation families. FEMIC consumes
it as an optional dependency so the two projects share one data and provenance
contract.

Install
-------

Install the optional extra in a FEMIC environment:

.. code-block:: bash

   python -m pip install -e ".[fresh-vdyp]"

Or install the published package directly:

.. code-block:: bash

   python -m pip install "fresh-vdyp>=0.1.0"

If the package is absent, FEMIC keeps its existing VDYP path. The integration is
additive.

Curve query
-----------

.. code-block:: python

   import fresh_vdyp

   service = fresh_vdyp.load_service(csv_path, metadata_path)
   result = service.query(
       fresh_vdyp.CurveQuery(species="AT", age_start=100, age_end=100)
   )
   point = result.points[0]
   assert point.units["volume_ws"] == "m3/ha"

Every result carries provenance:

.. code-block:: python

   provenance = result.provenance.to_dict()
   # source_file, runtime, console_version, control_sequence, query

Bundle validation
-----------------

.. code-block:: python

   import os
   from pathlib import Path

   import fresh_vdyp

   findings = fresh_vdyp.validate_bundle(Path(os.environ["VDYP_CFG_DIR"]))

Data prerequisites
------------------

- A local VDYP installation for bundle commands: ``VDYP_INSTALL``,
  ``VDYP_CFG_DIR``, and ``VDYP_CONSOLE``.
- A parsed console output and its metadata for curve queries.
- The synthetic golden dataset is suitable for smoke tests; it is not BC data.

Boundary
--------

- FEMIC owns its pipeline, instances, and data.
- ``fresh-vdyp`` owns bundle parsing, the console adapter, typed curves, and the
  equation validation matrix.
- ``fresh-vdyp`` does not import FEMIC.
- The adapter passes provenance through and records the package version, console
  version, and bundle manifest hash.

Known limits
------------

- Only VTOTREG4 is validated; other families are experimental.
- The current golden dataset is synthetic and Wine-produced.
- The young-stand path is outside the validated VTOTREG4 domain.

Links
-----

- Package: https://pypi.org/project/fresh-vdyp/
- Release: https://github.com/UBC-FRESH/fresh-vdyp/releases/tag/v0.1.0
- Validation matrix:
  https://github.com/UBC-FRESH/fresh-vdyp/blob/main/notes/reference/vdyp-equation-matrix.json
