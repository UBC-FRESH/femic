GCBM walltowall Export
======================

``femic export gcbm`` prepares a GCBM 2.5.x walltowall project from a FEMIC
checkpoint and a static carbon package. The export is producer-side: it writes
the configuration, inventory vector, yield table, optional disturbance vector,
and AIDB. It does not run FLINT.

Prerequisites
-------------

- A FEMIC checkpoint feather with polygon geometry, ``au``, ``PROJ_AGE_1``, and
  ``FEATURE_AREA_SQM``. ``IFM_FLAG`` selects managed (``1``) or unmanaged
  (``0``).
- A carbon package from ``femic carbon export-package``. The package supplies
  the AU/IFM tracks, leading CBM species, and merchantable yield curves.
- A SQLite CBM defaults database (AIDB). Pass ``--aidb``, or install ``libcbm``
  so the exporter detects its bundled database. The exporter records the hash
  and refuses a mismatch with the package unless ``--allow-aidb-mismatch`` is
  explicit.
- For the external smoke: Windows Python 3.10 with GDAL, ``mojadata``,
  ``spatial_inventory_rollback``, ``gcbmwalltowall``, and the GCBM executable.
  The bundled GCBM training package contains these wheels and ``moja.cli.exe``.

Command
-------

.. code-block:: bash

   femic export gcbm \
     --checkpoint data/vri_vclr1p_checkpoint7.feather \
     --carbon-package output/carbon/tsa24 \
     --aidb /path/to/cbm_defaults_v1.2.9300.391.db \
     --output-dir output/gcbm/tsa24_2401005 \
     --au 2401005 \
     --max-fragments 500 \
     --resolution 0.005 \
     --start-year 2020 \
     --end-year 2030

``--au`` restricts the export to selected analysis units. ``--max-fragments``
caps a smoke export; omit it for the full selection. The default resolution is
``0.001`` degrees, which is coarse relative to the 25 m GCBM training example.
Use the resolution appropriate to the reporting question and host budget.

The command resolves paths through the active instance context. Use
``--instance-root`` when the current directory is not the instance root.

What it writes
--------------

.. code-block:: text

   output/gcbm/tsa24_2401005/
     walltowall_config.json
     inventory.gpkg
     yield.csv
     disturbances.gpkg          (when --disturbance is supplied)
     input_database/
       cbm_defaults_v1.2.9300.391.db
     manifest.json
     walltowall.log             (created by walltowall)

The manifest records the checkpoint, package, AIDB, and disturbance hashes;
the output hashes; the classifier mapping; the CRS and resolution; and any
warnings. ``walltowall_config.json`` is the input to the external
``walltowall prepare`` command.

Model choices
-------------

- **One baseline track per AU/IFM.** The package may contain several state
  tracks for the same AU and IFM. The exporter prefers the natural/baseline
  track and records the chosen track in the classifier map. If two equally
  preferred tracks have different leading species, the export fails rather than
  guessing.
- **Small classifier codes.** ``Classifier1`` is a dense 1..N track code, not
  the raw AU id, so the Float32 raster and GCBM growth-curve lookup cannot turn
  ``2401005`` into ``2.401005e+6``. ``Classifier2`` is ``1`` for managed and
  ``0`` for unmanaged. The manifest maps the codes back to AU/IFM.
- **Wide yield table.** Ages are the package grid (10 years to 300 by default);
  ``AIDBSPP`` is the package leading CBM species.
- **Mean annual temperature.** The checkpoint currently has no MAT column, so
  the exporter writes ``--mean-annual-temperature`` (default 3.0 C) for every
  polygon. This is a placeholder and must be replaced with a reviewed climate
  layer before interpreting absolute carbon stocks.
- **Initial age.** ``PROJ_AGE_1`` is clamped to the package maximum yield age
  or ``--initial-age-cap``.
- **CRS.** The checkpoint is assigned ``--checkpoint-crs`` (default
  ``EPSG:3005``) and reprojected to ``--epsg`` (default ``EPSG:4326``).

Disturbances
------------

``--disturbance`` accepts a vector readable by GeoPandas (GeoPackage,
Shapefile, or GeoJSON) with ``year``, ``disturbance_type``, and geometry. Rows
outside the start/end window are dropped with a warning. ``disturbance_type``
must be a CBM default disturbance type present in the chosen AIDB. The output is
``disturbances.gpkg`` and the walltowall config uses its ``year`` and
``disturbance_type`` attributes.

External smoke
--------------

On a supported Windows host, with the walltowall stack installed:

.. code-block:: bat

   cd output\gcbm\tsa24_2401005
   walltowall prepare walltowall_config.json

Then point ``gcbm_exe`` in the generated config at the local ``moja.cli.exe`` and
run:

.. code-block:: bat

   walltowall run local . --config_path walltowall_config.json

Alternatively run ``moja.cli.exe`` directly in ``gcbm_project``:

.. code-block:: bat

   moja.cli.exe --config_file gcbm_config.cfg --config_provider provider_config.json

The output database is ``gcbm_project\output\gcbm_output.db``. WS4 reads it with
``ws4 gcbm --results ...``.

On Linux, the walltowall Python stack needs GDAL and Windows is the normal host.
A Wine smoke was completed for this lane with the bundled Windows Python 3.10
and a **serial-pool workaround** for Wine's 63-handle multiprocessing limit;
that workaround is environmental, not part of the exporter. The generated config
was accepted by ``walltowall prepare`` and produced ``gcbm_input.db`` and
``gcbm_project``.

Caveats
-------

- MAT is a constant placeholder until the instance supplies a reviewed climate
  layer.
- One CBM species and one baseline curve per AU/IFM; species-resolved and
  state-resolved curves are a later extension.
- No retention or partial-harvest transition beyond the disturbance vector and
  the package disturbance map.
- One admin/eco boundary per package, matching the carbon package.
- CaMP, peatlands, and CBM4 are out of scope.
- Access ``.mdb`` AIDBs are rejected in this Linux export lane; use the SQLite
  AIDB.
- GCBM and walltowall are external dependencies and are not installed by FEMIC.

Related
-------

- ``docs/guides/carbon-export.rst`` — carbon package producer.
- ``docs/reference/contracts/carbon-domain.rst`` — package contract.
- WS4 ``docs/reference/carbon.rst`` — GCBM results reader.
